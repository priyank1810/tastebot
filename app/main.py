import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.chat import get_reply
from app.db import get_connection
from app.retrieval import search

app = FastAPI()

_sessions: dict[str, list[dict]] = {}
_conn = None


def get_db_connection():
    global _conn
    if _conn is None:
        _conn = get_connection()
    return _conn


@app.post("/api/chat")
async def chat_endpoint(request: Request):
    body = await request.json()
    session_id = body.get("session_id") or str(uuid.uuid4())
    message = body["message"]
    history = _sessions.setdefault(session_id, [])

    conn = get_db_connection()
    candidates = search(conn, message)
    reply = get_reply(history, message, candidates)

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
