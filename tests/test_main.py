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
        self.owners: dict[str, str] = {}
        self.sessions: list[dict] = []

    def ensure_session(self, conn, session_id, owner_id):
        if session_id not in self.messages:
            self.messages[session_id] = []
            self.owners[session_id] = owner_id
            self.sessions.insert(
                0, {"id": session_id, "title": None, "created_at": "2026-01-01T00:00:00"}
            )

    def session_owner(self, conn, session_id):
        return self.owners.get(session_id)

    def get_messages(self, conn, session_id):
        return list(self.messages.get(session_id, []))

    def append_message(self, conn, session_id, role, content):
        self.messages.setdefault(session_id, []).append({"role": role, "content": content})

    def list_sessions(self, conn, owner_id):
        return [s for s in self.sessions if self.owners.get(s["id"]) == owner_id]


@pytest.fixture
def fake_store(monkeypatch):
    store = FakeSessionStore()
    monkeypatch.setattr(main_module, "ensure_session", store.ensure_session)
    monkeypatch.setattr(main_module, "session_owner", store.session_owner)
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


def test_chat_endpoint_forwards_filters_to_search(monkeypatch, fake_store):
    captured = {}

    def capturing_search(conn, message, top_k=6, filters=None):
        captured["filters"] = filters
        return fake_search(conn, message, top_k, filters)

    monkeypatch.setattr(main_module, "search", capturing_search)
    monkeypatch.setattr(main_module, "get_reply", fake_get_reply)

    client = TestClient(main_module.app)
    client.post(
        "/api/chat",
        json={"session_id": "s5", "message": "hi", "filters": {"cuisine": ["italian"]}},
    )

    assert captured["filters"] == {"cuisine": ["italian"]}


def test_filters_options_endpoint(monkeypatch, fake_store):
    def fake_get_filter_options(conn):
        return {"cuisine": ["italian"], "budget": ["mid"], "location": ["downtown"], "dietary_tags": ["vegan"]}

    monkeypatch.setattr(main_module, "get_filter_options", fake_get_filter_options)

    client = TestClient(main_module.app)
    resp = client.get("/api/filters/options")

    assert resp.status_code == 200
    assert resp.json() == {
        "cuisine": ["italian"], "budget": ["mid"], "location": ["downtown"], "dietary_tags": ["vegan"],
    }


def test_chat_endpoint_includes_lat_lon_in_candidates(monkeypatch, fake_store):
    def fake_search_with_coords(conn, message, top_k=6, filters=None):
        return [
            RetrievedRestaurant(
                name="Pasta Palace", cuisine="italian", budget="mid",
                location="downtown", dietary_tags=["vegetarian"],
                description="Fresh pasta", rating=4.5, distance=0.1,
                lat=23.03, lon=72.56,
            ),
        ]

    monkeypatch.setattr(main_module, "search", fake_search_with_coords)
    monkeypatch.setattr(main_module, "get_reply", fake_get_reply)

    client = TestClient(main_module.app)
    resp = client.post("/api/chat", json={"session_id": "s6", "message": "hi"})

    candidate = resp.json()["candidates"][0]
    assert candidate["lat"] == 23.03
    assert candidate["lon"] == 72.56


def test_chat_endpoint_rejects_missing_message(monkeypatch, fake_store):
    monkeypatch.setattr(main_module, "search", fake_search)
    monkeypatch.setattr(main_module, "get_reply", fake_get_reply)

    client = TestClient(main_module.app)
    resp = client.post("/api/chat", json={"session_id": "s7"})

    assert resp.status_code == 400


def test_sessions_endpoint_does_not_leak_other_owners_sessions(monkeypatch, fake_store):
    monkeypatch.setattr(main_module, "search", fake_search)
    monkeypatch.setattr(main_module, "get_reply", fake_get_reply)

    owner_a = TestClient(main_module.app)
    owner_a.post("/api/chat", json={"session_id": "s-a", "message": "hi"})

    owner_b = TestClient(main_module.app)
    owner_b.post("/api/chat", json={"session_id": "s-b", "message": "hi"})

    resp = owner_b.get("/api/sessions")
    ids = [s["id"] for s in resp.json()]
    assert ids == ["s-b"]

    resp = owner_b.get("/api/sessions/s-a")
    assert resp.status_code == 404


def test_startup_fails_fast_without_api_key(monkeypatch):
    monkeypatch.setattr(main_module.settings, "azure_openai_api_key", None)
    monkeypatch.setattr(main_module, "get_db_connection", lambda: None)
    monkeypatch.setattr(main_module, "init_session_schema", lambda conn: None)

    with pytest.raises(RuntimeError, match="AZURE_OPENAI_API_KEY"):
        with TestClient(main_module.app):
            pass
