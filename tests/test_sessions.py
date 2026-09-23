from app.sessions import (
    append_message,
    ensure_session,
    get_messages,
    list_sessions,
    session_owner,
)


def test_ensure_session_is_idempotent(db_conn):
    ensure_session(db_conn, "s1", "owner-a")
    ensure_session(db_conn, "s1", "owner-a")  # must not raise on second call
    with db_conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM chat_sessions WHERE id = %s", ("s1",))
        assert cur.fetchone()[0] == 1


def test_ensure_session_does_not_transfer_ownership(db_conn):
    ensure_session(db_conn, "s1", "owner-a")
    ensure_session(db_conn, "s1", "owner-b")  # second caller can't hijack it
    assert session_owner(db_conn, "s1") == "owner-a"


def test_append_and_get_messages_round_trip(db_conn):
    ensure_session(db_conn, "s1", "owner-a")
    append_message(db_conn, "s1", "user", "hello")
    append_message(db_conn, "s1", "assistant", "hi there")

    messages = get_messages(db_conn, "s1")

    assert messages == [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi there"},
    ]


def test_get_messages_empty_for_unknown_session(db_conn):
    assert get_messages(db_conn, "does-not-exist") == []


def test_list_sessions_orders_newest_first(db_conn):
    ensure_session(db_conn, "older", "owner-a")
    ensure_session(db_conn, "newer", "owner-a")
    with db_conn.cursor() as cur:
        cur.execute(
            "UPDATE chat_sessions SET created_at = now() - interval '1 hour' WHERE id = %s",
            ("older",),
        )

    sessions = list_sessions(db_conn, "owner-a")

    ids = [s["id"] for s in sessions]
    assert ids.index("newer") < ids.index("older")
    assert set(sessions[0].keys()) == {"id", "title", "created_at"}


def test_list_sessions_scoped_to_owner(db_conn):
    ensure_session(db_conn, "mine", "owner-a")
    ensure_session(db_conn, "theirs", "owner-b")

    sessions = list_sessions(db_conn, "owner-a")

    assert [s["id"] for s in sessions] == ["mine"]
