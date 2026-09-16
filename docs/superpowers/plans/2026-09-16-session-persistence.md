# Session Persistence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the in-memory `_sessions` dict in `app/main.py` with Postgres-backed chat session/message storage, and expose it via two new read endpoints.

**Architecture:** Two new tables (`chat_sessions`, `chat_messages`) plus a new `app/sessions.py` module with plain functions (no ORM, matching the rest of the codebase's direct-psycopg2 style). `main.py`'s `/api/chat` handler calls these functions instead of touching a dict; two new `GET` routes expose session listing and per-session history.

**Tech Stack:** Python, psycopg2 (already a dependency), pytest, FastAPI TestClient.

**Spec:** `docs/superpowers/specs/2026-09-16-frontend-rebuild-design.md` (Data model changes, API changes — session persistence sections)

## Global Constraints

- Tests must never touch the dev database — always connect via `settings.test_database_url` (see `tests/conftest.py`'s `db_conn` fixture). Never call `get_connection()` with no argument inside a test.
- `conn.autocommit` is already `True` for every connection returned by `get_connection()` (see `app/db.py`) — explicit `conn.commit()` calls after writes are kept anyway for symmetry with `app/ingest.py`'s existing style, not because they're required.
- Match existing code style: `str | None` type hints, plain functions (no classes) for DB access, no ORM.
- `chat_sessions.id` is `TEXT`, not native Postgres `UUID` — the existing test suite and manual testing use arbitrary strings like `"s1"` as session ids, and a native `UUID` column would reject those. The frontend will still generate real UUID strings; the column just doesn't enforce that format.

---

### Task 1: Core session/message storage (`app/sessions.py`)

**Files:**
- Create: `app/sessions.py`
- Modify: `tests/conftest.py`
- Test: `tests/test_sessions.py`

**Interfaces:**
- Consumes: `app.config.settings.test_database_url` (already exists), `app.db.get_connection(database_url: str | None = None)` (already exists)
- Produces:
  - `init_session_schema(conn) -> None`
  - `ensure_session(conn, session_id: str) -> None`
  - `get_messages(conn, session_id: str) -> list[dict]` — each dict is `{"role": str, "content": str}`
  - `append_message(conn, session_id: str, role: str, content: str) -> None`

- [ ] **Step 1: Extend the `db_conn` fixture to also manage the session tables**

Edit `tests/conftest.py` to its full new content:

```python
import pytest
from app.config import settings
from app.db import get_connection, init_schema


@pytest.fixture
def db_conn():
    conn = get_connection(settings.test_database_url)
    init_schema(conn)
    from app.sessions import init_session_schema
    init_session_schema(conn)
    with conn.cursor() as cur:
        cur.execute(
            "TRUNCATE chat_messages, chat_sessions, restaurants RESTART IDENTITY CASCADE"
        )
    conn.commit()
    yield conn
    conn.close()
```

(The `import` is placed inside the fixture function, not at module top, because `app/sessions.py` doesn't exist yet at this point in the task — Step 4 creates it. Once Step 4 is done this still works fine either way; leave it as a top-level import after Step 4 for cleanliness — see Step 6.)

- [ ] **Step 2: Write the failing test**

Create `tests/test_sessions.py`:

```python
from app.sessions import append_message, ensure_session, get_messages


def test_ensure_session_is_idempotent(db_conn):
    ensure_session(db_conn, "s1")
    ensure_session(db_conn, "s1")  # must not raise on second call
    with db_conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM chat_sessions WHERE id = %s", ("s1",))
        assert cur.fetchone()[0] == 1


def test_append_and_get_messages_round_trip(db_conn):
    ensure_session(db_conn, "s1")
    append_message(db_conn, "s1", "user", "hello")
    append_message(db_conn, "s1", "assistant", "hi there")

    messages = get_messages(db_conn, "s1")

    assert messages == [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi there"},
    ]


def test_get_messages_empty_for_unknown_session(db_conn):
    assert get_messages(db_conn, "does-not-exist") == []
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/test_sessions.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.sessions'`

- [ ] **Step 4: Write minimal implementation**

Create `app/sessions.py`:

```python
SESSIONS_SQL = """
CREATE TABLE IF NOT EXISTS chat_sessions (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    title TEXT
);
"""

MESSAGES_SQL = """
CREATE TABLE IF NOT EXISTS chat_messages (
    id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES chat_sessions(id),
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


def init_session_schema(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(SESSIONS_SQL)
        cur.execute(MESSAGES_SQL)
    conn.commit()


def ensure_session(conn, session_id: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO chat_sessions (id) VALUES (%s) ON CONFLICT (id) DO NOTHING",
            (session_id,),
        )
    conn.commit()


def get_messages(conn, session_id: str) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT role, content FROM chat_messages WHERE session_id = %s ORDER BY id",
            (session_id,),
        )
        rows = cur.fetchall()
    return [{"role": r[0], "content": r[1]} for r in rows]


def append_message(conn, session_id: str, role: str, content: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO chat_messages (session_id, role, content) VALUES (%s, %s, %s)",
            (session_id, role, content),
        )
    conn.commit()
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_sessions.py -v`
Expected: PASS (3 tests)

- [ ] **Step 6: Move the `conftest.py` import to the top of the file**

Now that `app/sessions.py` exists, clean up `tests/conftest.py` to its final form:

```python
import pytest
from app.config import settings
from app.db import get_connection, init_schema
from app.sessions import init_session_schema


@pytest.fixture
def db_conn():
    conn = get_connection(settings.test_database_url)
    init_schema(conn)
    init_session_schema(conn)
    with conn.cursor() as cur:
        cur.execute(
            "TRUNCATE chat_messages, chat_sessions, restaurants RESTART IDENTITY CASCADE"
        )
    conn.commit()
    yield conn
    conn.close()
```

Run: `pytest -q`
Expected: all tests still pass (this only reorganizes an import, no behavior change)

- [ ] **Step 7: Commit**

```bash
git add app/sessions.py tests/conftest.py tests/test_sessions.py
git commit -m "feat: add Postgres-backed chat session/message storage"
```

---

### Task 2: List sessions (`list_sessions`)

**Files:**
- Modify: `app/sessions.py`
- Test: `tests/test_sessions.py`

**Interfaces:**
- Consumes: nothing new
- Produces: `list_sessions(conn) -> list[dict]` — each dict is `{"id": str, "title": str | None, "created_at": str}` (ISO 8601 string), ordered newest-first

- [ ] **Step 1: Write the failing test**

Append to `tests/test_sessions.py`:

```python
from app.sessions import list_sessions


def test_list_sessions_orders_newest_first(db_conn):
    ensure_session(db_conn, "older")
    ensure_session(db_conn, "newer")
    with db_conn.cursor() as cur:
        cur.execute(
            "UPDATE chat_sessions SET created_at = now() - interval '1 hour' WHERE id = %s",
            ("older",),
        )

    sessions = list_sessions(db_conn)

    ids = [s["id"] for s in sessions]
    assert ids.index("newer") < ids.index("older")
    assert set(sessions[0].keys()) == {"id", "title", "created_at"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_sessions.py::test_list_sessions_orders_newest_first -v`
Expected: FAIL — `ImportError: cannot import name 'list_sessions'`

- [ ] **Step 3: Write minimal implementation**

Append to `app/sessions.py`:

```python
def list_sessions(conn) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, title, created_at FROM chat_sessions ORDER BY created_at DESC"
        )
        rows = cur.fetchall()
    return [
        {"id": r[0], "title": r[1], "created_at": r[2].isoformat()}
        for r in rows
    ]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_sessions.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add app/sessions.py tests/test_sessions.py
git commit -m "feat: add list_sessions for session sidebar"
```

---

### Task 3: Wire `/api/chat` to use Postgres-backed sessions

**Files:**
- Modify: `app/main.py`
- Modify: `tests/test_main.py`

**Interfaces:**
- Consumes: `ensure_session`, `get_messages`, `append_message`, `init_session_schema` from `app.sessions` (Task 1)
- Produces: `main.py` no longer has a module-level `_sessions` dict; `chat_endpoint` reads/writes history via `app.sessions` functions

- [ ] **Step 1: Write the failing test**

Replace `tests/test_main.py` with this full content (adds a `fake_store` fixture replacing the old `main_module._sessions.clear()` pattern):

```python
import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.retrieval import RetrievedRestaurant


def fake_search(conn, message, top_k=6, filters=None):
    return [
        RetrievedRestaurant(
            name="Pasta Palace", cuisine="italian", budget="mid",
            location="downtown", dietary_tags=["vegetarian"],
            description="Fresh pasta", rating=4.5, distance=0.1,
        ),
    ]


def fake_get_reply(history, message, candidates, client=None):
    return f"reply to: {message} (history_len={len(history)})"


class FakeSessionStore:
    def __init__(self):
        self.messages: dict[str, list[dict]] = {}
        self.sessions: list[dict] = []

    def ensure_session(self, conn, session_id):
        if session_id not in self.messages:
            self.messages[session_id] = []
            self.sessions.insert(
                0, {"id": session_id, "title": None, "created_at": "2026-01-01T00:00:00"}
            )

    def get_messages(self, conn, session_id):
        return list(self.messages.get(session_id, []))

    def append_message(self, conn, session_id, role, content):
        self.messages.setdefault(session_id, []).append({"role": role, "content": content})

    def list_sessions(self, conn):
        return list(self.sessions)


@pytest.fixture
def fake_store(monkeypatch):
    store = FakeSessionStore()
    monkeypatch.setattr(main_module, "ensure_session", store.ensure_session)
    monkeypatch.setattr(main_module, "get_messages", store.get_messages)
    monkeypatch.setattr(main_module, "append_message", store.append_message)
    monkeypatch.setattr(main_module, "list_sessions", store.list_sessions)
    monkeypatch.setattr(main_module, "get_db_connection", lambda: None)
    return store


def test_chat_endpoint_returns_reply_and_candidates(monkeypatch, fake_store):
    monkeypatch.setattr(main_module, "search", fake_search)
    monkeypatch.setattr(main_module, "get_reply", fake_get_reply)

    client = TestClient(main_module.app)

    resp1 = client.post("/api/chat", json={"session_id": "s1", "message": "hi"})
    assert resp1.status_code == 200
    body1 = resp1.json()
    assert body1["reply"] == "reply to: hi (history_len=0)"
    assert body1["candidates"][0]["name"] == "Pasta Palace"

    resp2 = client.post("/api/chat", json={"session_id": "s1", "message": "again"})
    body2 = resp2.json()
    assert "history_len=2" in body2["reply"]


def fake_get_reply_raises(history, message, candidates, client=None):
    raise RuntimeError("simulated Claude API failure")


def test_chat_endpoint_falls_back_on_claude_error(monkeypatch, fake_store):
    monkeypatch.setattr(main_module, "search", fake_search)
    monkeypatch.setattr(main_module, "get_reply", fake_get_reply_raises)

    client = TestClient(main_module.app)
    resp = client.post("/api/chat", json={"session_id": "s2", "message": "hi"})

    assert resp.status_code == 200
    assert resp.json()["reply"] == main_module.FALLBACK_REPLY


def test_startup_fails_fast_without_api_key(monkeypatch):
    monkeypatch.setattr(main_module.settings, "azure_openai_api_key", None)
    monkeypatch.setattr(main_module, "get_db_connection", lambda: None)
    monkeypatch.setattr(main_module, "init_session_schema", lambda conn: None)

    with pytest.raises(RuntimeError, match="AZURE_OPENAI_API_KEY"):
        with TestClient(main_module.app):
            pass
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_main.py -v`
Expected: FAIL — `AttributeError: module 'app.main' has no attribute 'ensure_session'` (monkeypatch can't find the name to patch, since `main.py` hasn't imported it yet)

- [ ] **Step 3: Write minimal implementation**

Replace `app/main.py` with this full content:

```python
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
    yield


app = FastAPI(lifespan=lifespan)


@app.post("/api/chat")
async def chat_endpoint(request: Request):
    body = await request.json()
    session_id = body.get("session_id") or str(uuid.uuid4())
    message = body["message"]

    conn = get_db_connection()
    ensure_session(conn, session_id)
    history = get_messages(conn, session_id)
    candidates = search(conn, message)
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
            }
            for c in candidates
        ],
    })


app.mount("/", StaticFiles(directory="static", html=True), name="static")
```

Note: `list_sessions` is imported here but not used by a route yet — that's Task 4. Importing it now (rather than in Task 4) keeps this task's import block matching what `test_startup_fails_fast_without_api_key`'s `monkeypatch.setattr(main_module, "init_session_schema", ...)` needs to already resolve, and avoids a second edit to the same import block next task.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_main.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Run the full suite to check for regressions**

Run: `pytest -q`
Expected: all tests pass except the pre-existing unrelated failure in `tests/test_config.py::test_settings_validate_raises_without_key` (a known pre-existing issue with `importlib.reload` and env var isolation in the Azure migration work — not caused by this task, do not fix it as part of this plan)

- [ ] **Step 6: Commit**

```bash
git add app/main.py tests/test_main.py
git commit -m "feat: back /api/chat session history with Postgres instead of an in-memory dict"
```

---

### Task 4: `GET /api/sessions` and `GET /api/sessions/{session_id}` endpoints

**Files:**
- Modify: `app/main.py`
- Modify: `tests/test_main.py`

**Interfaces:**
- Consumes: `list_sessions`, `get_messages` from `app.sessions` (already imported in Task 3)
- Produces: two new HTTP routes, no new Python-level interfaces

- [ ] **Step 1: Write the failing test**

Append to `tests/test_main.py`:

```python
def test_sessions_endpoint_lists_sessions(monkeypatch, fake_store):
    monkeypatch.setattr(main_module, "search", fake_search)
    monkeypatch.setattr(main_module, "get_reply", fake_get_reply)

    client = TestClient(main_module.app)
    client.post("/api/chat", json={"session_id": "s3", "message": "hi"})

    resp = client.get("/api/sessions")
    assert resp.status_code == 200
    ids = [s["id"] for s in resp.json()]
    assert "s3" in ids


def test_session_messages_endpoint_returns_history(monkeypatch, fake_store):
    monkeypatch.setattr(main_module, "search", fake_search)
    monkeypatch.setattr(main_module, "get_reply", fake_get_reply)

    client = TestClient(main_module.app)
    client.post("/api/chat", json={"session_id": "s4", "message": "hi"})

    resp = client.get("/api/sessions/s4")
    assert resp.status_code == 200
    roles = [m["role"] for m in resp.json()]
    assert roles == ["user", "assistant"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_main.py::test_sessions_endpoint_lists_sessions -v`
Expected: FAIL — 404 Not Found (route doesn't exist yet)

- [ ] **Step 3: Write minimal implementation**

In `app/main.py`, insert these two routes right after `chat_endpoint` and before the `app.mount(...)` line at the bottom:

```python
@app.get("/api/sessions")
async def sessions_endpoint():
    conn = get_db_connection()
    return JSONResponse(list_sessions(conn))


@app.get("/api/sessions/{session_id}")
async def session_messages_endpoint(session_id: str):
    conn = get_db_connection()
    return JSONResponse(get_messages(conn, session_id))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_main.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Run the full suite**

Run: `pytest -q`
Expected: same pre-existing single failure as Task 3 Step 5, nothing new broken

- [ ] **Step 6: Commit**

```bash
git add app/main.py tests/test_main.py
git commit -m "feat: add GET /api/sessions and /api/sessions/{id} endpoints"
```
