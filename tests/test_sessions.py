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
