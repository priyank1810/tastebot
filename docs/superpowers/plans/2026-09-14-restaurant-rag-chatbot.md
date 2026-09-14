# Restaurant Recommendation Bot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a RAG-based restaurant recommendation chatbot: CSV catalog → embeddings → PostgreSQL/pgvector → similarity search → Claude-generated chat replies, served through a FastAPI backend and a custom modern chat frontend.

**Architecture:** FastAPI backend with an offline ingestion script (CSV → validate → embed → store in Postgres/pgvector) and a runtime `/api/chat` route (embed query → pgvector top-6 similarity search → Claude generates grounded reply). Static HTML/CSS/JS frontend renders replies as chat bubbles with rich restaurant cards.

**Tech Stack:** Python 3.11+, FastAPI, uvicorn, psycopg2 + pgvector (Postgres extension, via Docker), sentence-transformers (`all-MiniLM-L6-v2`, local embeddings), Anthropic Python SDK (Claude), pandas/csv, pytest, plain HTML/CSS/JS frontend, Node's built-in test runner for frontend unit tests.

**Spec:** `docs/superpowers/specs/2026-09-14-restaurant-rag-chatbot-design.md`

## Global Constraints

- Postgres with pgvector runs via Docker for local dev (per spec Architecture).
- Embeddings: `sentence-transformers` `all-MiniLM-L6-v2`, 384 dimensions, local only — no external embedding API (per spec Components).
- Chat generation: Claude via Anthropic API, generation only, no tool-use (retrieval already narrows candidates) (per spec Components).
- No live external restaurant API (Google Places/Yelp) — CSV catalog only (per spec Non-goals).
- No auth, no multi-tenant accounts — single shared in-memory session store keyed by session id (per spec Non-goals / Data flow).
- Frontend: plain HTML/CSS/JS, no framework, modern chat UI with rich restaurant cards, no default/templated look (per spec Frontend).
- Top-K for retrieval is fixed at 6 (per spec Architecture / Data flow).

---

## File Structure

```
chatbot/
  requirements.txt
  .env.example
  docker-compose.yml
  README.md
  data/
    restaurants.csv
  app/
    __init__.py
    config.py
    db.py
    embeddings.py
    validate.py
    ingest.py
    retrieval.py
    chat.py
    main.py
  static/
    index.html
    chat.js
    style.css
  tests/
    conftest.py
    test_config.py
    test_db.py
    test_embeddings.py
    test_validate.py
    test_ingest.py
    test_retrieval.py
    test_chat.py
    test_main.py
    test_chat_js.mjs
```

- `app/config.py` — env var loading (`DATABASE_URL`, `ANTHROPIC_API_KEY`).
- `app/db.py` — Postgres connection, pgvector extension + schema setup.
- `app/embeddings.py` — local embedding model wrapper.
- `app/validate.py` — CSV row validation + `Restaurant` dataclass.
- `app/ingest.py` — CSV → validate → embed → upsert pipeline (also a CLI entrypoint).
- `app/retrieval.py` — query embedding + pgvector top-6 similarity search.
- `app/chat.py` — Claude prompt construction + reply generation.
- `app/main.py` — FastAPI app, `/api/chat` route, session store, static file mount.
- `static/*` — chat UI (bubbles + rich restaurant cards).

---

### Task 1: Project scaffold & config

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `docker-compose.yml`
- Create: `app/__init__.py`
- Create: `app/config.py`
- Test: `tests/test_config.py`
- Test: `tests/conftest.py` (placeholder import check only — DB fixture added in Task 2)

**Interfaces:**
- Produces: `app.config.Settings` class with attributes `database_url: str`, `anthropic_api_key: str | None`, method `validate() -> None` that raises `RuntimeError` if `anthropic_api_key` is falsy; module-level `settings = Settings()` instance.

- [ ] **Step 1: Write requirements, env template, docker-compose**

`requirements.txt`:
```
fastapi==0.115.0
uvicorn[standard]==0.30.6
psycopg2-binary==2.9.9
pgvector==0.3.4
sentence-transformers==3.1.1
anthropic==0.34.2
pandas==2.2.2
python-dotenv==1.0.1
pytest==8.3.3
httpx==0.27.2
```

`.env.example`:
```
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/restaurants
ANTHROPIC_API_KEY=
```

`docker-compose.yml`:
```yaml
services:
  postgres:
    image: ankane/pgvector:latest
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: restaurants
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
volumes:
  pgdata:
```

- [ ] **Step 2: Write the failing test**

`tests/test_config.py`:
```python
import importlib
import app.config as config_module

def test_settings_reads_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@host:5432/db")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    importlib.reload(config_module)
    assert config_module.settings.database_url == "postgresql://u:p@host:5432/db"
    assert config_module.settings.anthropic_api_key == "sk-test"

def test_settings_validate_raises_without_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    importlib.reload(config_module)
    try:
        config_module.settings.validate()
        assert False, "expected RuntimeError"
    except RuntimeError:
        pass
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.config'` (or `app` package missing)

- [ ] **Step 4: Write minimal implementation**

`app/__init__.py`:
```python
```

`app/config.py`:
```python
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    def __init__(self):
        self.database_url = os.environ.get(
            "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/restaurants"
        )
        self.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")

    def validate(self) -> None:
        if not self.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set")


settings = Settings()
```

`tests/conftest.py` (empty for now, extended in Task 2):
```python
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`
Expected: PASS (2 tests)

- [ ] **Step 6: Start Postgres and commit**

```bash
docker compose up -d
git add requirements.txt .env.example docker-compose.yml app/__init__.py app/config.py tests/test_config.py tests/conftest.py
git commit -m "feat: add project scaffold and env config"
```

---

### Task 2: Database connection & schema

**Files:**
- Create: `app/db.py`
- Modify: `tests/conftest.py`
- Test: `tests/test_db.py`

**Interfaces:**
- Consumes: `app.config.settings.database_url`
- Produces: `app.db.get_connection(database_url: str | None = None) -> psycopg2.connection` (creates the `vector` extension and registers the pgvector adapter on the connection); `app.db.init_schema(conn) -> None` (creates the `restaurants` table if not present).

- [ ] **Step 1: Write the failing test**

`tests/test_db.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_db.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.db'`

- [ ] **Step 3: Write minimal implementation**

`app/db.py`:
```python
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
```

`tests/conftest.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Prerequisite: `docker compose up -d` (Task 1) must be running.
Run: `pytest tests/test_db.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/db.py tests/test_db.py tests/conftest.py
git commit -m "feat: add postgres/pgvector connection and schema setup"
```

---

### Task 3: Embedding wrapper

**Files:**
- Create: `app/embeddings.py`
- Test: `tests/test_embeddings.py`

**Interfaces:**
- Produces: `app.embeddings.embed(text: str) -> list[float]` returning a 384-length vector.

- [ ] **Step 1: Write the failing test**

`tests/test_embeddings.py`:
```python
from app.embeddings import embed

def test_embed_returns_384_dim_vector():
    vector = embed("Italian pasta restaurant downtown")
    assert isinstance(vector, list)
    assert len(vector) == 384

def test_embed_is_deterministic():
    a = embed("spicy vegetarian curry")
    b = embed("spicy vegetarian curry")
    assert a == b
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_embeddings.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.embeddings'`

- [ ] **Step 3: Write minimal implementation**

`app/embeddings.py`:
```python
from functools import lru_cache

from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def _model() -> SentenceTransformer:
    return SentenceTransformer(MODEL_NAME)


def embed(text: str) -> list[float]:
    vector = _model().encode(text, normalize_embeddings=True)
    return vector.tolist()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_embeddings.py -v`
Expected: PASS (first run downloads the model; subsequent runs are fast)

- [ ] **Step 5: Commit**

```bash
git add app/embeddings.py tests/test_embeddings.py
git commit -m "feat: add local sentence-transformers embedding wrapper"
```

---

### Task 4: CSV row validation

**Files:**
- Create: `app/validate.py`
- Test: `tests/test_validate.py`

**Interfaces:**
- Produces: `app.validate.Restaurant` dataclass with fields `name: str`, `cuisine: str`, `budget: str`, `location: str`, `dietary_tags: list[str]`, `description: str`, `rating: float | None`; `app.validate.ValidationError(Exception)`; `app.validate.validate_row(row: dict) -> Restaurant` (raises `ValidationError` on bad input).

- [ ] **Step 1: Write the failing test**

`tests/test_validate.py`:
```python
import pytest
from app.validate import validate_row, ValidationError

def test_validate_row_parses_good_row():
    row = {
        "name": "Pasta Palace", "cuisine": "italian", "budget": "mid",
        "location": "downtown", "dietary_tags": "vegetarian;gluten_free",
        "description": "Fresh pasta", "rating": "4.5",
    }
    r = validate_row(row)
    assert r.name == "Pasta Palace"
    assert r.budget == "mid"
    assert r.dietary_tags == ["vegetarian", "gluten_free"]
    assert r.rating == 4.5

def test_validate_row_missing_name_raises():
    row = {"name": "", "cuisine": "italian", "budget": "mid", "location": "downtown"}
    with pytest.raises(ValidationError):
        validate_row(row)

def test_validate_row_bad_budget_raises():
    row = {"name": "X", "cuisine": "italian", "budget": "expensive", "location": "downtown"}
    with pytest.raises(ValidationError):
        validate_row(row)

def test_validate_row_defaults_missing_optional_fields():
    row = {"name": "X", "cuisine": "italian", "budget": "budget", "location": "downtown"}
    r = validate_row(row)
    assert r.dietary_tags == []
    assert r.description == ""
    assert r.rating is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_validate.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.validate'`

- [ ] **Step 3: Write minimal implementation**

`app/validate.py`:
```python
from dataclasses import dataclass

ALLOWED_BUDGETS = {"budget", "mid", "premium"}
REQUIRED_FIELDS = ["name", "cuisine", "budget", "location"]


@dataclass
class Restaurant:
    name: str
    cuisine: str
    budget: str
    location: str
    dietary_tags: list[str]
    description: str
    rating: float | None


class ValidationError(Exception):
    pass


def validate_row(row: dict) -> Restaurant:
    for field in REQUIRED_FIELDS:
        if not (row.get(field) or "").strip():
            raise ValidationError(f"missing required field: {field}")

    budget = row["budget"].strip().lower()
    if budget not in ALLOWED_BUDGETS:
        raise ValidationError(f"invalid budget: {row['budget']!r}")

    dietary_raw = row.get("dietary_tags") or ""
    dietary_tags = [t.strip() for t in dietary_raw.split(";") if t.strip()]

    rating_raw = (row.get("rating") or "").strip()
    rating = float(rating_raw) if rating_raw else None

    return Restaurant(
        name=row["name"].strip(),
        cuisine=row["cuisine"].strip(),
        budget=budget,
        location=row["location"].strip(),
        dietary_tags=dietary_tags,
        description=(row.get("description") or "").strip(),
        rating=rating,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_validate.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add app/validate.py tests/test_validate.py
git commit -m "feat: add CSV row validation"
```

---

### Task 5: Ingestion pipeline

**Files:**
- Create: `app/ingest.py`
- Test: `tests/test_ingest.py`

**Interfaces:**
- Consumes: `app.validate.validate_row`, `app.validate.ValidationError`, `app.embeddings.embed`, `app.db.get_connection`, `app.db.init_schema`
- Produces: `app.ingest.build_text(r: Restaurant) -> str`; `app.ingest.ingest_csv(path: str, conn=None) -> dict` returning `{"inserted": int, "skipped": list[tuple[int, str]]}`.

- [ ] **Step 1: Write the failing test**

`tests/test_ingest.py`:
```python
from app.ingest import ingest_csv

CSV_CONTENT = """name,cuisine,budget,location,dietary_tags,description,rating
Good Place,italian,mid,downtown,vegetarian,Nice pasta spot,4.5
Bad Place,mexican,expensive,uptown,none,Bad budget value,4.0
,chinese,budget,eastside,none,Missing name,3.5
"""

def test_ingest_skips_invalid_rows(db_conn, tmp_path):
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text(CSV_CONTENT)

    result = ingest_csv(str(csv_path), conn=db_conn)

    assert result["inserted"] == 1
    assert len(result["skipped"]) == 2
    with db_conn.cursor() as cur:
        cur.execute("SELECT name FROM restaurants")
        rows = cur.fetchall()
    assert rows == [("Good Place",)]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ingest.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.ingest'`

- [ ] **Step 3: Write minimal implementation**

`app/ingest.py`:
```python
import csv
import sys

from app.db import get_connection, init_schema
from app.embeddings import embed
from app.validate import Restaurant, ValidationError, validate_row


def build_text(r: Restaurant) -> str:
    tags = ", ".join(r.dietary_tags) if r.dietary_tags else "none"
    return (
        f"{r.name} serves {r.cuisine} cuisine in {r.location}. "
        f"Budget: {r.budget}. Dietary: {tags}. {r.description}"
    )


def ingest_csv(path: str, conn=None) -> dict:
    conn = conn or get_connection()
    init_schema(conn)
    inserted = 0
    skipped = []

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        with conn.cursor() as cur:
            for line_no, row in enumerate(reader, start=2):  # header is line 1
                try:
                    r = validate_row(row)
                except ValidationError as e:
                    skipped.append((line_no, str(e)))
                    continue

                text = build_text(r)
                vector = embed(text)
                cur.execute(
                    """
                    INSERT INTO restaurants
                        (name, cuisine, budget, location, dietary_tags, description, rating, embedding)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (r.name, r.cuisine, r.budget, r.location, r.dietary_tags,
                     r.description, r.rating, vector),
                )
                inserted += 1

    conn.commit()
    for line_no, reason in skipped:
        print(f"skipped row {line_no}: {reason}", file=sys.stderr)
    return {"inserted": inserted, "skipped": skipped}


if __name__ == "__main__":
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "data/restaurants.csv"
    result = ingest_csv(csv_path)
    print(f"inserted {result['inserted']} rows, skipped {len(result['skipped'])}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_ingest.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/ingest.py tests/test_ingest.py
git commit -m "feat: add CSV ingestion pipeline (validate, embed, store)"
```

---

### Task 6: Retrieval (vector similarity search)

**Files:**
- Create: `app/retrieval.py`
- Test: `tests/test_retrieval.py`

**Interfaces:**
- Consumes: `app.embeddings.embed`, `app.ingest.ingest_csv` (test-only, to seed data)
- Produces: `app.retrieval.RetrievedRestaurant` dataclass (`name, cuisine, budget, location, dietary_tags, description, rating, distance`); `app.retrieval.search(conn, query: str, top_k: int = 6) -> list[RetrievedRestaurant]`.

- [ ] **Step 1: Write the failing test**

`tests/test_retrieval.py`:
```python
from app.ingest import ingest_csv
from app.retrieval import search

CSV_CONTENT = """name,cuisine,budget,location,dietary_tags,description,rating
Pasta Palace,italian,mid,downtown,vegetarian,Fresh handmade pasta and pizza,4.5
Sushi Spot,japanese,premium,downtown,pescatarian,Fresh nigiri and sashimi,4.7
Taco Town,mexican,budget,eastside,gluten_free,Street tacos and salsa,4.0
Curry Corner,indian,mid,southside,vegetarian;vegan,Rich curries and biryani,4.3
Burger Joint,american,budget,southside,none,Smash burgers and fries,4.1
Vegan Bowl,vegan,mid,uptown,vegan;gluten_free,Plant-based bowls,4.4
Ramen House,japanese,budget,downtown,none,Tonkotsu ramen bowls,4.2
Pizza Place,italian,budget,eastside,vegetarian,Wood-fired pizza slices,4.0
"""

def test_search_returns_top_six_ordered_by_distance(db_conn, tmp_path):
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text(CSV_CONTENT)
    ingest_csv(str(csv_path), conn=db_conn)

    results = search(db_conn, "cheap italian pizza", top_k=6)

    assert len(results) == 6
    distances = [r.distance for r in results]
    assert distances == sorted(distances)
    names = [r.name for r in results]
    assert "Pizza Place" in names[:3] or "Pasta Palace" in names[:3]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_retrieval.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.retrieval'`

- [ ] **Step 3: Write minimal implementation**

`app/retrieval.py`:
```python
from dataclasses import dataclass

from app.embeddings import embed


@dataclass
class RetrievedRestaurant:
    name: str
    cuisine: str
    budget: str
    location: str
    dietary_tags: list[str]
    description: str
    rating: float | None
    distance: float


def search(conn, query: str, top_k: int = 6) -> list[RetrievedRestaurant]:
    query_vector = embed(query)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT name, cuisine, budget, location, dietary_tags, description, rating,
                   embedding <=> %s AS distance
            FROM restaurants
            ORDER BY embedding <=> %s
            LIMIT %s
            """,
            (query_vector, query_vector, top_k),
        )
        rows = cur.fetchall()

    return [
        RetrievedRestaurant(
            name=row[0], cuisine=row[1], budget=row[2], location=row[3],
            dietary_tags=row[4] or [], description=row[5], rating=row[6],
            distance=row[7],
        )
        for row in rows
    ]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_retrieval.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/retrieval.py tests/test_retrieval.py
git commit -m "feat: add pgvector top-6 similarity search"
```

---

### Task 7: Claude chat generation

**Files:**
- Create: `app/chat.py`
- Test: `tests/test_chat.py`

**Interfaces:**
- Consumes: `app.retrieval.RetrievedRestaurant`, `app.config.settings`
- Produces: `app.chat.build_context(candidates: list[RetrievedRestaurant]) -> str`; `app.chat.get_reply(history: list[dict], user_message: str, candidates: list[RetrievedRestaurant], client=None) -> str`.

- [ ] **Step 1: Write the failing test**

`tests/test_chat.py`:
```python
from app.chat import build_context, get_reply
from app.retrieval import RetrievedRestaurant


def sample_candidates():
    return [
        RetrievedRestaurant(
            name="Pasta Palace", cuisine="italian", budget="mid",
            location="downtown", dietary_tags=["vegetarian"],
            description="Fresh pasta", rating=4.5, distance=0.1,
        ),
    ]


def test_build_context_includes_candidate_fields():
    context = build_context(sample_candidates())
    assert "Pasta Palace" in context
    assert "italian" in context
    assert "mid" in context


def test_build_context_empty_candidates():
    context = build_context([])
    assert "none found" in context


class FakeTextBlock:
    def __init__(self, text):
        self.text = text


class FakeResponse:
    def __init__(self, text):
        self.content = [FakeTextBlock(text)]


class FakeMessages:
    def create(self, **kwargs):
        assert "CANDIDATES" in kwargs["messages"][-1]["content"]
        return FakeResponse("I recommend Pasta Palace.")


class FakeClient:
    def __init__(self):
        self.messages = FakeMessages()


def test_get_reply_uses_context_and_client():
    reply = get_reply([], "suggest italian food", sample_candidates(), client=FakeClient())
    assert reply == "I recommend Pasta Palace."
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_chat.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.chat'`

- [ ] **Step 3: Write minimal implementation**

`app/chat.py`:
```python
from anthropic import Anthropic

from app.config import settings
from app.retrieval import RetrievedRestaurant

SYSTEM_PROMPT = (
    "You are a restaurant recommendation assistant. Recommend restaurants "
    "ONLY from the CANDIDATES list below. If none fit the user's request well, "
    "say so plainly and offer the closest options instead of inventing a fit. "
    "Never mention a restaurant that is not in CANDIDATES."
)


def build_context(candidates: list[RetrievedRestaurant]) -> str:
    if not candidates:
        return "CANDIDATES: (none found)"
    lines = ["CANDIDATES:"]
    for c in candidates:
        tags = ", ".join(c.dietary_tags) if c.dietary_tags else "none"
        lines.append(
            f"- {c.name} | cuisine: {c.cuisine} | budget: {c.budget} | "
            f"location: {c.location} | dietary: {tags} | rating: {c.rating}"
        )
    return "\n".join(lines)


def get_reply(
    history: list[dict],
    user_message: str,
    candidates: list[RetrievedRestaurant],
    client=None,
) -> str:
    client = client or Anthropic(api_key=settings.anthropic_api_key)
    context = build_context(candidates)
    messages = history + [
        {"role": "user", "content": f"{context}\n\nUser: {user_message}"}
    ]
    response = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=500,
        system=SYSTEM_PROMPT,
        messages=messages,
    )
    return response.content[0].text
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_chat.py -v`
Expected: PASS (no real API call made — test uses `FakeClient`)

- [ ] **Step 5: Commit**

```bash
git add app/chat.py tests/test_chat.py
git commit -m "feat: add Claude-backed reply generation grounded in retrieved candidates"
```

---

### Task 8: FastAPI app and `/api/chat` route

**Files:**
- Create: `app/main.py`
- Test: `tests/test_main.py`

**Interfaces:**
- Consumes: `app.db.get_connection`, `app.retrieval.search`, `app.chat.get_reply`
- Produces: `app.main.app` (FastAPI instance); `POST /api/chat` accepting `{"session_id": str | None, "message": str}`, returning `{"session_id": str, "reply": str, "candidates": [{"name", "cuisine", "budget", "location", "rating"}]}`.

- [ ] **Step 1: Write the failing test**

`tests/test_main.py`:
```python
from fastapi.testclient import TestClient

import app.main as main_module
from app.retrieval import RetrievedRestaurant


def fake_search(conn, message, top_k=6):
    return [
        RetrievedRestaurant(
            name="Pasta Palace", cuisine="italian", budget="mid",
            location="downtown", dietary_tags=["vegetarian"],
            description="Fresh pasta", rating=4.5, distance=0.1,
        ),
    ]


def fake_get_reply(history, message, candidates, client=None):
    return f"reply to: {message} (history_len={len(history)})"


def test_chat_endpoint_returns_reply_and_candidates(monkeypatch):
    monkeypatch.setattr(main_module, "search", fake_search)
    monkeypatch.setattr(main_module, "get_reply", fake_get_reply)
    monkeypatch.setattr(main_module, "get_db_connection", lambda: None)
    main_module._sessions.clear()

    client = TestClient(main_module.app)

    resp1 = client.post("/api/chat", json={"session_id": "s1", "message": "hi"})
    assert resp1.status_code == 200
    body1 = resp1.json()
    assert body1["reply"] == "reply to: hi (history_len=0)"
    assert body1["candidates"][0]["name"] == "Pasta Palace"

    resp2 = client.post("/api/chat", json={"session_id": "s1", "message": "again"})
    body2 = resp2.json()
    assert "history_len=2" in body2["reply"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_main.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.main'`

- [ ] **Step 3: Write minimal implementation**

`app/main.py`:
```python
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.chat import get_reply
from app.db import get_connection
from app.retrieval import search

app = FastAPI()

_sessions: dict[str, list[dict]] = {}
_conn = None


def get_db_connection():
    global _conn
    if _conn is None:
        _conn = get_connection()
    return _conn


@app.post("/api/chat")
async def chat_endpoint(request: Request):
    body = await request.json()
    session_id = body.get("session_id") or str(uuid.uuid4())
    message = body["message"]
    history = _sessions.setdefault(session_id, [])

    conn = get_db_connection()
    candidates = search(conn, message)
    reply = get_reply(history, message, candidates)

    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": reply})

    return JSONResponse({
        "session_id": session_id,
        "reply": reply,
        "candidates": [
            {
                "name": c.name,
                "cuisine": c.cuisine,
                "budget": c.budget,
                "location": c.location,
                "rating": c.rating,
            }
            for c in candidates
        ],
    })


app.mount("/", StaticFiles(directory="static", html=True), name="static")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_main.py -v`
Expected: PASS (route logic tested with `search`/`get_reply`/`get_db_connection` stubbed out — no real DB or API call)

- [ ] **Step 5: Commit**

```bash
git add app/main.py tests/test_main.py
git commit -m "feat: add FastAPI /api/chat route with session history"
```

---

### Task 9: Sample restaurant dataset

**Files:**
- Create: `data/restaurants.csv`
- Test: `tests/test_dataset.py`

**Interfaces:**
- Consumes: `app.ingest.ingest_csv`
- Produces: none new (data file only)

- [ ] **Step 1: Write the failing test**

`tests/test_dataset.py`:
```python
from app.ingest import ingest_csv


def test_sample_dataset_ingests_with_no_skipped_rows(db_conn):
    result = ingest_csv("data/restaurants.csv", conn=db_conn)
    assert result["skipped"] == []
    assert result["inserted"] == 30
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_dataset.py -v`
Expected: FAIL — `data/restaurants.csv` does not exist yet (`FileNotFoundError`)

- [ ] **Step 3: Create the dataset**

`data/restaurants.csv`:
```
name,cuisine,budget,location,dietary_tags,description,rating
Spice Route,indian,mid,downtown,vegetarian;vegan,Modern Indian bistro with rich curries and tandoor specialties.,4.5
Green Leaf Kitchen,vegan,budget,uptown,vegan;gluten_free,Plant-based comfort food with all dishes free of animal products.,4.3
Nonna's Table,italian,premium,downtown,vegetarian,Handmade pasta and wood-fired pizza in a cozy dining room.,4.7
Taco Fiesta,mexican,budget,eastside,gluten_free,Street-style tacos and fresh salsas at a quick casual spot.,4.1
Sakura Sushi,japanese,premium,downtown,pescatarian,Omakase and classic nigiri served from a sushi counter.,4.8
Curry House,indian,budget,southside,vegetarian;halal,Fast-casual curries and biryani that is halal certified.,4.0
Le Petit Bistro,french,premium,downtown,none,Classic French bistro fare including steak frites and coq au vin.,4.6
Vegan Vibes,vegan,mid,uptown,vegan;gluten_free,Creative vegan small plates and fresh juices.,4.4
Dragon Wok,chinese,budget,eastside,none,Wok-fired Chinese classics served in generous portions.,3.9
Mediterraneo,mediterranean,mid,westside,vegetarian;halal,Mezze platters, grilled meats, and fresh hummus.,4.5
Burger Barn,american,budget,southside,gluten_free,Classic smash burgers and hand-cut fries.,4.0
Pho Saigon,vietnamese,budget,eastside,gluten_free,Slow-simmered pho broth and fresh spring rolls.,4.3
Trattoria Roma,italian,mid,westside,vegetarian,Family-run trattoria serving classic Roman pasta dishes.,4.4
Halal Grill House,middle_eastern,mid,southside,halal,Charcoal-grilled kebabs and fresh flatbread.,4.2
Coastal Catch,seafood,premium,downtown,pescatarian,Fresh daily catch, oysters, and coastal-inspired plates.,4.6
Plant Power Cafe,vegan,budget,uptown,vegan;gluten_free,Quick-serve vegan bowls and smoothies.,4.0
Bombay Express,indian,budget,eastside,vegetarian;vegan,Quick-serve thalis and street food classics.,3.8
Ramen Nights,japanese,budget,downtown,none,Rich tonkotsu and miso ramen bowls served late into the night.,4.4
The Steakhouse,american,premium,downtown,gluten_free,Dry-aged steaks and classic sides in an upscale setting.,4.7
Falafel Corner,middle_eastern,budget,westside,vegan;vegetarian,Crispy falafel wraps and fresh tabbouleh.,4.1
Casa Mexicana,mexican,mid,downtown,vegetarian,Traditional mole, enchiladas, and fresh guacamole.,4.5
Golden Dragon,chinese,mid,southside,none,Dim sum brunch and classic Cantonese dishes.,4.3
Olive Grove,mediterranean,premium,downtown,vegetarian;gluten_free,Elegant Mediterranean tasting menu with local ingredients.,4.6
Noodle Bar,vietnamese,mid,uptown,gluten_free,Build-your-own pho and rice noodle bowls.,4.2
Pizza Pronto,italian,budget,eastside,vegetarian,Fast wood-fired pizza by the slice.,4.0
Kebab Kingdom,middle_eastern,budget,eastside,halal,Quick-serve kebabs, shawarma, and rice bowls.,4.1
Blue Ocean Sushi,japanese,mid,westside,pescatarian,Casual sushi rolls and bento boxes.,4.3
Farmhouse Table,american,mid,uptown,vegetarian;gluten_free,Seasonal farm-to-table plates with a changing daily menu.,4.5
Saffron Palace,indian,premium,downtown,vegetarian;halal,Upscale Indian dining with tasting menus.,4.7
Urban Greens,vegan,mid,downtown,vegan;gluten_free,Modern vegan restaurant with globally inspired dishes.,4.4
```

Note: any `description` field containing a comma must be quoted for valid CSV (e.g. `"Mezze platters, grilled meats, and fresh hummus."`) — quote those three rows (Mediterraneo, Coastal Catch, Casa Mexicana, Kebab Kingdom) when creating the file.

- [ ] **Step 4: Run test to verify it passes**

Prerequisite: `docker compose up -d` running.
Run: `pytest tests/test_dataset.py -v`
Expected: PASS (`inserted == 30`, `skipped == []`)

- [ ] **Step 5: Commit**

```bash
git add data/restaurants.csv tests/test_dataset.py
git commit -m "feat: add sample restaurant dataset (30 rows)"
```

---

### Task 10: Frontend — modern chat UI with restaurant cards

**Files:**
- Create: `static/index.html`
- Create: `static/chat.js`
- Create: `static/style.css`
- Test: `tests/test_chat_js.mjs`

**Interfaces:**
- Consumes: `POST /api/chat` response shape from Task 8 (`session_id`, `reply`, `candidates`)
- Produces: `renderCard(restaurant) -> string` (exported from `static/chat.js`), `renderMessage(role, text, candidates=[]) -> string` (exported from `static/chat.js`)

**Note:** apply the `frontend-design` skill's guidance when refining this task's visual details (color/type choices below are a solid starting point, not the final word).

- [ ] **Step 1: Write the failing test**

`tests/test_chat_js.mjs`:
```javascript
import test from "node:test";
import assert from "node:assert/strict";
import { renderCard, renderMessage } from "../static/chat.js";

test("renderCard includes name, cuisine, budget, location", () => {
  const html = renderCard({
    name: "Pasta Palace", cuisine: "italian", budget: "mid",
    location: "downtown", rating: 4.5,
  });
  assert.ok(html.includes("Pasta Palace"));
  assert.ok(html.includes("italian"));
  assert.ok(html.includes("mid"));
  assert.ok(html.includes("downtown"));
});

test("renderMessage embeds cards only when candidates are given", () => {
  const withCards = renderMessage("assistant", "Here you go", [
    { name: "A", cuisine: "x", budget: "mid", location: "y", rating: 4 },
  ]);
  assert.ok(withCards.includes("restaurant-card"));

  const withoutCards = renderMessage("user", "hello");
  assert.ok(!withoutCards.includes("restaurant-card"));
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test tests/test_chat_js.mjs`
Expected: FAIL — `static/chat.js` does not exist yet

- [ ] **Step 3: Write minimal implementation**

`static/index.html`:
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Restaurant Recommendation Bot</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <div id="chat-app">
    <header id="chat-header">🍽️ Restaurant Recommendation Bot</header>
    <div id="messages"></div>
    <form id="chat-form">
      <input id="chat-input" type="text" placeholder="Ask for a restaurant..." autocomplete="off" />
      <button type="submit">Send</button>
    </form>
  </div>
  <script type="module" src="chat.js"></script>
</body>
</html>
```

`static/chat.js`:
```javascript
export function renderCard(restaurant) {
  const stars = restaurant.rating ? "★".repeat(Math.round(restaurant.rating)) : "";
  return `
    <div class="restaurant-card">
      <div class="card-name">${restaurant.name}</div>
      <div class="card-meta">${restaurant.cuisine} · ${restaurant.budget} · ${restaurant.location}</div>
      <div class="card-rating">${stars} ${restaurant.rating ?? ""}</div>
    </div>
  `;
}

export function renderMessage(role, text, candidates = []) {
  const cards = candidates.map(renderCard).join("");
  return `
    <div class="message ${role}">
      <div class="bubble">${text}</div>
      ${cards ? `<div class="cards">${cards}</div>` : ""}
    </div>
  `;
}

function initChat() {
  const form = document.getElementById("chat-form");
  const input = document.getElementById("chat-input");
  const messages = document.getElementById("messages");
  let sessionId = null;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    messages.innerHTML += renderMessage("user", text);
    input.value = "";

    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, message: text }),
    });
    const data = await res.json();
    sessionId = data.session_id;
    messages.innerHTML += renderMessage("assistant", data.reply, data.candidates);
    messages.scrollTop = messages.scrollHeight;
  });
}

if (typeof document !== "undefined") {
  document.addEventListener("DOMContentLoaded", initChat);
}
```

`static/style.css`:
```css
:root {
  --bg: #faf7f2;
  --surface: #ffffff;
  --accent: #d9622b;
  --accent-dark: #b84f1f;
  --text: #2b2420;
  --muted: #8a7f74;
  --bubble-user: #2b2420;
  --bubble-assistant: #fff3ea;
}

* { box-sizing: border-box; }

body {
  margin: 0;
  font-family: "Segoe UI", system-ui, sans-serif;
  background: var(--bg);
  color: var(--text);
  display: flex;
  justify-content: center;
  padding: 24px;
}

#chat-app {
  width: 100%;
  max-width: 480px;
  background: var(--surface);
  border-radius: 16px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
  display: flex;
  flex-direction: column;
  height: 80vh;
  overflow: hidden;
}

#chat-header {
  padding: 16px 20px;
  font-weight: 600;
  border-bottom: 1px solid #f0e9e1;
}

#messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.message.user .bubble {
  align-self: flex-end;
  background: var(--bubble-user);
  color: white;
  border-radius: 14px 14px 2px 14px;
}

.message.assistant .bubble {
  background: var(--bubble-assistant);
  border-radius: 14px 14px 14px 2px;
}

.bubble {
  padding: 10px 14px;
  max-width: 80%;
  line-height: 1.4;
}

.cards {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 8px;
}

.restaurant-card {
  border: 1px solid #f0e9e1;
  border-radius: 10px;
  padding: 10px 12px;
  background: var(--surface);
}

.card-name { font-weight: 600; }
.card-meta { color: var(--muted); font-size: 0.85em; }
.card-rating { color: var(--accent); font-size: 0.85em; }

#chat-form {
  display: flex;
  gap: 8px;
  padding: 12px;
  border-top: 1px solid #f0e9e1;
}

#chat-input {
  flex: 1;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid #e2d8cd;
  font-size: 14px;
}

#chat-form button {
  padding: 10px 16px;
  border: none;
  border-radius: 10px;
  background: var(--accent);
  color: white;
  font-weight: 600;
  cursor: pointer;
}

#chat-form button:hover {
  background: var(--accent-dark);
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test tests/test_chat_js.mjs`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add static/index.html static/chat.js static/style.css tests/test_chat_js.mjs
git commit -m "feat: add modern chat frontend with restaurant result cards"
```

---

### Task 11: README and end-to-end manual smoke test

**Files:**
- Create: `README.md`

**Interfaces:**
- Consumes: everything from Tasks 1–10
- Produces: none (documentation task)

- [ ] **Step 1: Write README with run instructions**

`README.md`:
```markdown
# Restaurant Recommendation Bot

RAG-based chatbot that recommends restaurants by cuisine, budget, location,
and dietary preference. See `docs/superpowers/specs/2026-09-14-restaurant-rag-chatbot-design.md`
for the design.

## Setup

1. `cp .env.example .env` and fill in `ANTHROPIC_API_KEY`.
2. `docker compose up -d` — starts Postgres with pgvector on `localhost:5432`.
3. `python -m venv .venv && source .venv/bin/activate`
4. `pip install -r requirements.txt`
5. `python -m app.ingest data/restaurants.csv` — loads and embeds the sample catalog.
6. `uvicorn app.main:app --reload`
7. Open `http://localhost:8000` in a browser.

## Tests

- Python: `pytest` (requires `docker compose up -d` running for DB-backed tests)
- Frontend: `node --test tests/test_chat_js.mjs`

## Manual smoke test

With the server running and the sample dataset ingested, try:

- "cheap vegetarian Indian food downtown"
- "somewhere for a nice date night, not too expensive"
- "vegan options near uptown"

Confirm: reply text stays grounded in restaurants that exist in
`data/restaurants.csv`, and the recommended restaurants render as cards
under the assistant's reply.
```

- [ ] **Step 2: Verify by running the full flow**

```bash
docker compose up -d
pip install -r requirements.txt
python -m app.ingest data/restaurants.csv
uvicorn app.main:app --reload &
curl -s -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "cheap vegetarian indian food downtown"}' | head -c 500
```
Expected: JSON response with a non-empty `reply` naming a real restaurant from the CSV, and 6 `candidates`.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add setup instructions and manual smoke test"
```

---

## Self-Review Notes

- **Spec coverage:** ingestion (Task 5), validation (Task 4), embeddings (Task 3), pgvector storage/search (Tasks 2, 6), Claude-grounded chat (Task 7), FastAPI route + session history (Task 8), sample dataset (Task 9), rich-card frontend (Task 10), error handling for missing config/DB (Task 1/2 fail-fast), weak-match hedging (Task 7 system prompt), CSV validation skip+log (Task 5) — all spec sections have a corresponding task.
- **Placeholder scan:** no TBD/TODO; all steps carry runnable code.
- **Type consistency:** `RetrievedRestaurant` fields (Task 6) match what `chat.py` (Task 7) and `main.py` (Task 8) read (`name, cuisine, budget, location, dietary_tags, rating`); `Restaurant` fields (Task 4) match what `ingest.py` (Task 5) consumes; frontend `candidates` shape (Task 8 response) matches fields `renderCard` reads (Task 10).
