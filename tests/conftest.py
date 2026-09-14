import pytest
from app.db import get_connection, init_schema


@pytest.fixture
def db_conn():
    conn = get_connection()
    init_schema(conn)
    with conn.cursor() as cur:
        cur.execute("TRUNCATE restaurants RESTART IDENTITY")
    conn.commit()
    yield conn
    conn.close()
