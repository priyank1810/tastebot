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
    # Autocommit: a connection that runs a single SELECT/INSERT per call
    # (retrieval, ingestion) should never sit idle-in-transaction holding
    # locks between requests. Without this, a long-lived connection (e.g.
    # the FastAPI app's shared _conn) blocks DDL like TRUNCATE indefinitely.
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
    register_vector(conn)
    return conn


def init_schema(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(TABLE_SQL)
    conn.commit()


def init_geocoding_schema(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("ALTER TABLE restaurants ADD COLUMN IF NOT EXISTS lat DOUBLE PRECISION")
        cur.execute("ALTER TABLE restaurants ADD COLUMN IF NOT EXISTS lon DOUBLE PRECISION")
    conn.commit()
