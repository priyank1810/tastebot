import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.chat import get_reply
from app.config import settings
from app.db import get_connection, init_geocoding_schema
from app.retrieval import get_filter_options, search
from app.sessions import (
    append_message,
    ensure_session,
    get_messages,
    init_session_schema,
    list_sessions,
    session_owner,
)

OWNER_COOKIE = "uid"


def get_owner_id(request: Request) -> str:
    return request.cookies.get(OWNER_COOKIE) or str(uuid.uuid4())


def set_owner_cookie(response: JSONResponse, owner_id: str) -> None:
    response.set_cookie(
        OWNER_COOKIE,
        owner_id,
        max_age=60 * 60 * 24 * 365,
        httponly=True,
        samesite="lax",
    )

logger = logging.getLogger(__name__)

FALLBACK_REPLY = (
    "Sorry, I couldn't reach the recommendation service just now. Please try again."
)

_conn = None


def get_db_connection():
    global _conn
    if _conn is None:
        _conn = get_connection()
    return _conn


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Fail fast if Azure OpenAI env vars are missing, per spec Error handling.
    settings.validate()
    # Fail fast if Postgres/pgvector is unreachable, per spec Error handling.
    conn = get_db_connection()
    init_session_schema(conn)
    init_geocoding_schema(conn)
    yield


app = FastAPI(lifespan=lifespan)


@app.post("/api/chat")
async def chat_endpoint(request: Request):
    body = await request.json()
    session_id = body.get("session_id") or str(uuid.uuid4())
    message = body.get("message")
    if not message:
        raise HTTPException(status_code=400, detail="message is required")
    filters = body.get("filters")
    owner_id = get_owner_id(request)

    conn = get_db_connection()
    existing_owner = session_owner(conn, session_id)
    if existing_owner is not None and existing_owner != owner_id:
        raise HTTPException(status_code=404, detail="session not found")
    ensure_session(conn, session_id, owner_id)
    history = get_messages(conn, session_id)
    candidates = search(conn, message, filters=filters)
    try:
        reply = get_reply(history, message, candidates)
    except Exception:
        # %r (not %s) so a crafted session_id containing newlines/control
        # characters can't forge extra log lines.
        logger.exception("Azure OpenAI call failed for session %r", session_id)
        reply = FALLBACK_REPLY

    append_message(conn, session_id, "user", message)
    append_message(conn, session_id, "assistant", reply)

    response = JSONResponse({
        "session_id": session_id,
        "reply": reply,
        "candidates": [
            {
                "name": c.name,
                "cuisine": c.cuisine,
                "budget": c.budget,
                "location": c.location,
                "rating": c.rating,
                "lat": c.lat,
                "lon": c.lon,
            }
            for c in candidates
        ],
    })
    set_owner_cookie(response, owner_id)
    return response


@app.get("/api/filters/options")
async def filters_options_endpoint():
    conn = get_db_connection()
    return JSONResponse(get_filter_options(conn))


@app.get("/api/sessions")
async def sessions_endpoint(request: Request):
    owner_id = request.cookies.get(OWNER_COOKIE)
    if owner_id is None:
        return JSONResponse([])
    conn = get_db_connection()
    return JSONResponse(list_sessions(conn, owner_id))


@app.get("/api/sessions/{session_id}")
async def session_messages_endpoint(session_id: str, request: Request):
    owner_id = request.cookies.get(OWNER_COOKIE)
    conn = get_db_connection()
    if owner_id is None or session_owner(conn, session_id) != owner_id:
        raise HTTPException(status_code=404, detail="session not found")
    return JSONResponse(get_messages(conn, session_id))


app.mount("/", StaticFiles(directory="static/dist", html=True), name="static")
