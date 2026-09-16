import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
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
    message = body["message"]
    filters = body.get("filters")

    conn = get_db_connection()
    ensure_session(conn, session_id)
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

    return JSONResponse({
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


@app.get("/api/filters/options")
async def filters_options_endpoint():
    conn = get_db_connection()
    return JSONResponse(get_filter_options(conn))


@app.get("/api/sessions")
async def sessions_endpoint():
    conn = get_db_connection()
    return JSONResponse(list_sessions(conn))


@app.get("/api/sessions/{session_id}")
async def session_messages_endpoint(session_id: str):
    conn = get_db_connection()
    return JSONResponse(get_messages(conn, session_id))


app.mount("/", StaticFiles(directory="static/dist", html=True), name="static")
