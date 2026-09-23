SESSIONS_SQL = """
CREATE TABLE IF NOT EXISTS chat_sessions (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    title TEXT,
    owner_id TEXT
);
"""

MESSAGES_SQL = """
CREATE TABLE IF NOT EXISTS chat_messages (
    id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES chat_sessions(id),
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


def init_session_schema(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(SESSIONS_SQL)
        cur.execute(MESSAGES_SQL)
        cur.execute("ALTER TABLE chat_sessions ADD COLUMN IF NOT EXISTS owner_id TEXT")
    conn.commit()


def ensure_session(conn, session_id: str, owner_id: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO chat_sessions (id, owner_id) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING",
            (session_id, owner_id),
        )
    conn.commit()


def session_owner(conn, session_id: str) -> str | None:
    with conn.cursor() as cur:
        cur.execute("SELECT owner_id FROM chat_sessions WHERE id = %s", (session_id,))
        row = cur.fetchone()
    return row[0] if row else None


def get_messages(conn, session_id: str) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT role, content FROM chat_messages WHERE session_id = %s ORDER BY id",
            (session_id,),
        )
        rows = cur.fetchall()
    return [{"role": r[0], "content": r[1]} for r in rows]


def append_message(conn, session_id: str, role: str, content: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO chat_messages (session_id, role, content) VALUES (%s, %s, %s)",
            (session_id, role, content),
        )
    conn.commit()


def list_sessions(conn, owner_id: str) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, title, created_at FROM chat_sessions "
            "WHERE owner_id = %s ORDER BY created_at DESC",
            (owner_id,),
        )
        rows = cur.fetchall()
    return [
        {"id": r[0], "title": r[1], "created_at": r[2].isoformat()}
        for r in rows
    ]
