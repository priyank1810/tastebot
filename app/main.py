import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.chat import get_reply
from app.config import settings
from app.db import get_connection
from app.retrieval import search

logger = logging.getLogger(__name__)

FALLBACK_REPLY = (
    "Sorry, I couldn't reach the recommendation service just now. Please try again."
)

_sessions: dict[str, list[dict]] = {}
_conn = None


def get_db_connection():
    global _conn
    if _conn is None:
        _conn = get_connection()
    return _conn


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Fail fast if ANTHROPIC_API_KEY is missing, per spec Error handling.
    settings.validate()
    # Fail fast if Postgres/pgvector is unreachable, per spec Error handling.
    get_db_connection()
    yield


app = FastAPI(lifespan=lifespan)


@app.post("/api/chat")
async def chat_endpoint(request: Request):
    body = await request.json()
    session_id = body.get("session_id") or str(uuid.uuid4())
    message = body["message"]
    history = _sessions.setdefault(session_id, [])

    conn = get_db_connection()
    candidates = search(conn, message)
    try:
        reply = get_reply(history, message, candidates)
    except Exception:
        # %r (not %s) so a crafted session_id containing newlines/control
        # characters can't forge extra log lines.
        logger.exception("Claude API call failed for session %r", session_id)
        reply = FALLBACK_REPLY

    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": reply})

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
            }
            for c in candidates
        ],
    })


app.mount("/", StaticFiles(directory="static", html=True), name="static")
