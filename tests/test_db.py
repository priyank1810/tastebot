from app.db import get_connection, init_schema

def test_init_schema_creates_table():
    conn = get_connection()
    init_schema(conn)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'restaurants'"
        )
        columns = {row[0] for row in cur.fetchall()}
    assert {"id", "name", "cuisine", "budget", "location", "dietary_tags",
            "description", "rating", "embedding"} <= columns
    conn.close()
