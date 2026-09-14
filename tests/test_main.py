from fastapi.testclient import TestClient

import app.main as main_module
from app.retrieval import RetrievedRestaurant


def fake_search(conn, message, top_k=6):
    return [
        RetrievedRestaurant(
            name="Pasta Palace", cuisine="italian", budget="mid",
            location="downtown", dietary_tags=["vegetarian"],
            description="Fresh pasta", rating=4.5, distance=0.1,
        ),
    ]


def fake_get_reply(history, message, candidates, client=None):
    return f"reply to: {message} (history_len={len(history)})"


def test_chat_endpoint_returns_reply_and_candidates(monkeypatch):
    monkeypatch.setattr(main_module, "search", fake_search)
    monkeypatch.setattr(main_module, "get_reply", fake_get_reply)
    monkeypatch.setattr(main_module, "get_db_connection", lambda: None)
    main_module._sessions.clear()

    client = TestClient(main_module.app)

    resp1 = client.post("/api/chat", json={"session_id": "s1", "message": "hi"})
    assert resp1.status_code == 200
    body1 = resp1.json()
    assert body1["reply"] == "reply to: hi (history_len=0)"
    assert body1["candidates"][0]["name"] == "Pasta Palace"

    resp2 = client.post("/api/chat", json={"session_id": "s1", "message": "again"})
    body2 = resp2.json()
    assert "history_len=2" in body2["reply"]
