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
