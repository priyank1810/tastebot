from app.sessions import append_message, ensure_session, get_messages, list_sessions


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
