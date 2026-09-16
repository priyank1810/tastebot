from app.config import settings
from app.db import get_connection, init_geocoding_schema, init_schema

def test_init_schema_creates_table():
    conn = get_connection(settings.test_database_url)
    init_schema(conn)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'restaurants'"
        )
        columns = {row[0] for row in cur.fetchall()}
    assert {"id", "name", "cuisine", "budget", "location", "dietary_tags",
            "description", "rating", "embedding"} <= columns
    conn.close()


def test_init_geocoding_schema_adds_lat_lon_columns():
    conn = get_connection(settings.test_database_url)
    init_schema(conn)
    init_geocoding_schema(conn)
    init_geocoding_schema(conn)  # must be safe to call twice
    with conn.cursor() as cur:
        cur.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'restaurants'"
        )
        columns = {row[0] for row in cur.fetchall()}
    assert {"lat", "lon"} <= columns
    conn.close()
