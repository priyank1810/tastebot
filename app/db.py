import psycopg2
from pgvector.psycopg2 import register_vector

from app.config import settings

TABLE_SQL = """
CREATE TABLE IF NOT EXISTS restaurants (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    cuisine TEXT NOT NULL,
    budget TEXT NOT NULL,
    location TEXT NOT NULL,
    dietary_tags TEXT[] NOT NULL DEFAULT '{}',
    description TEXT NOT NULL DEFAULT '',
    rating NUMERIC,
    embedding VECTOR(384)
);
"""


def get_connection(database_url: str | None = None):
    conn = psycopg2.connect(database_url or settings.database_url)
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
    conn.commit()
    register_vector(conn)
    return conn


def init_schema(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(TABLE_SQL)
    conn.commit()
