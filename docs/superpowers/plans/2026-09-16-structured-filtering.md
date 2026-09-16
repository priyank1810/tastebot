# Structured Filtering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let `POST /api/chat` narrow its candidate pool with structured filters (cuisine/budget/location/dietary tags) before ranking by semantic similarity, and expose the available filter values for the frontend sidebar.

**Architecture:** `retrieval.search()` gains an optional `filters` parameter that adds SQL `WHERE` clauses ahead of the existing `ORDER BY embedding <=> ...` ranking. A new `get_filter_options()` function queries distinct column values for the sidebar dropdowns. `main.py` forwards a `filters` field from the request body and exposes a new `GET /api/filters/options` route.

**Tech Stack:** Python, psycopg2, pytest.

**Spec:** `docs/superpowers/specs/2026-09-16-frontend-rebuild-design.md` (Structured filtering sections of Architecture, API changes, Data flow)

**Depends on:** `2026-09-16-session-persistence.md` should land first — Task 3 of this plan extends the `fake_store`/`test_main.py` fixtures that plan introduces. If it hasn't landed, first check whether `tests/test_main.py` has a `fake_store` fixture and a `_sessions`-free `app/main.py`; if not, apply that plan's Task 3 first.

## Global Constraints

- Tests must never touch the dev database — always connect via `settings.test_database_url` (see `tests/conftest.py`'s `db_conn` fixture).
- All filter values are lists (even for single selections) so the sidebar can support multi-select per field: `filters = {"cuisine": [...], "budget": [...], "location": [...], "dietary_tags": [...]}`. Any key can be omitted or empty, meaning "no filter on that field."
- `dietary_tags` filtering uses the Postgres array-overlap operator (`&&`) — a restaurant matches if it has *any* of the requested tags, not all of them.
- This plan can be implemented independently of and in parallel with the session-persistence plan (`2026-09-16-session-persistence.md`) — they touch different parts of `main.py` and don't conflict except both editing the same file, so land whichever merges second by re-reading `main.py` first.

---

### Task 1: `search()` accepts structured filters

**Files:**
- Modify: `app/retrieval.py`
- Test: `tests/test_retrieval.py`

**Interfaces:**
- Consumes: `app.embeddings.embed(text: str) -> list[float]` (already exists), `app.ingest.ingest_csv` (already exists, used by tests)
- Produces: `search(conn, query: str, top_k: int = 6, filters: dict | None = None) -> list[RetrievedRestaurant]` (extends the existing signature — the new `filters` parameter is optional and defaults to no filtering, so every existing caller keeps working unchanged)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_retrieval.py`:

```python
def test_search_filters_by_cuisine(db_conn, tmp_path):
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text(CSV_CONTENT)
    ingest_csv(str(csv_path), conn=db_conn)

    results = search(db_conn, "something tasty", top_k=6, filters={"cuisine": ["mexican"]})

    assert len(results) == 1
    assert results[0].name == "Taco Town"


def test_search_filters_by_budget_and_dietary_tags(db_conn, tmp_path):
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text(CSV_CONTENT)
    ingest_csv(str(csv_path), conn=db_conn)

    results = search(
        db_conn, "something tasty", top_k=6,
        filters={"budget": ["mid"], "dietary_tags": ["vegan"]},
    )

    names = {r.name for r in results}
    assert names == {"Curry Corner", "Vegan Bowl"}


def test_search_with_no_matching_filters_returns_empty(db_conn, tmp_path):
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text(CSV_CONTENT)
    ingest_csv(str(csv_path), conn=db_conn)

    results = search(db_conn, "anything", top_k=6, filters={"cuisine": ["klingon"]})

    assert results == []


def test_search_with_no_filters_arg_behaves_as_before(db_conn, tmp_path):
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text(CSV_CONTENT)
    ingest_csv(str(csv_path), conn=db_conn)

    results = search(db_conn, "cheap italian pizza", top_k=6)

    assert len(results) == 6
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_retrieval.py::test_search_filters_by_cuisine -v`
Expected: FAIL — `TypeError: search() got an unexpected keyword argument 'filters'`

- [ ] **Step 3: Write minimal implementation**

Replace `app/retrieval.py` with this full content:

```python
from dataclasses import dataclass

from pgvector.utils import Vector

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


def search(
    conn, query: str, top_k: int = 6, filters: dict | None = None
) -> list[RetrievedRestaurant]:
    filters = filters or {}
    query_vector = Vector(embed(query)).to_numpy()

    where_clauses = []
    where_params = []
    if filters.get("cuisine"):
        where_clauses.append("cuisine = ANY(%s)")
        where_params.append(filters["cuisine"])
    if filters.get("budget"):
        where_clauses.append("budget = ANY(%s)")
        where_params.append(filters["budget"])
    if filters.get("location"):
        where_clauses.append("location = ANY(%s)")
        where_params.append(filters["location"])
    if filters.get("dietary_tags"):
        where_clauses.append("dietary_tags && %s")
        where_params.append(filters["dietary_tags"])

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT name, cuisine, budget, location, dietary_tags, description, rating,
                   embedding <=> %s AS distance
            FROM restaurants
            {where_sql}
            ORDER BY embedding <=> %s
            LIMIT %s
            """,
            [query_vector, *where_params, query_vector, top_k],
        )
        rows = cur.fetchall()

    return [
        RetrievedRestaurant(
            name=row[0], cuisine=row[1], budget=row[2], location=row[3],
            dietary_tags=row[4] or [], description=row[5],
            rating=float(row[6]) if row[6] is not None else None,
            distance=float(row[7]),
        )
        for row in rows
    ]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_retrieval.py -v`
Expected: PASS (all tests in the file)

- [ ] **Step 5: Commit**

```bash
git add app/retrieval.py tests/test_retrieval.py
git commit -m "feat: support structured cuisine/budget/location/dietary filters in search()"
```

---

### Task 2: `get_filter_options()` for the sidebar

**Files:**
- Modify: `app/retrieval.py`
- Test: `tests/test_retrieval.py`

**Interfaces:**
- Consumes: nothing new
- Produces: `get_filter_options(conn) -> dict` returning `{"cuisine": list[str], "budget": list[str], "location": list[str], "dietary_tags": list[str]}`, each list sorted and deduplicated

- [ ] **Step 1: Write the failing test**

Append to `tests/test_retrieval.py`:

```python
from app.retrieval import get_filter_options


def test_get_filter_options_returns_distinct_values(db_conn, tmp_path):
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text(CSV_CONTENT)
    ingest_csv(str(csv_path), conn=db_conn)

    options = get_filter_options(db_conn)

    assert set(options.keys()) == {"cuisine", "budget", "location", "dietary_tags"}
    assert "italian" in options["cuisine"]
    assert "mexican" in options["cuisine"]
    assert "mid" in options["budget"]
    assert "downtown" in options["location"]
    assert "vegetarian" in options["dietary_tags"]
    assert "vegan" in options["dietary_tags"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_retrieval.py::test_get_filter_options_returns_distinct_values -v`
Expected: FAIL — `ImportError: cannot import name 'get_filter_options'`

- [ ] **Step 3: Write minimal implementation**

Append to `app/retrieval.py`:

```python
def get_filter_options(conn) -> dict:
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT cuisine FROM restaurants ORDER BY cuisine")
        cuisines = [r[0] for r in cur.fetchall()]
        cur.execute("SELECT DISTINCT budget FROM restaurants ORDER BY budget")
        budgets = [r[0] for r in cur.fetchall()]
        cur.execute("SELECT DISTINCT location FROM restaurants ORDER BY location")
        locations = [r[0] for r in cur.fetchall()]
        cur.execute(
            "SELECT DISTINCT unnest(dietary_tags) AS tag FROM restaurants ORDER BY tag"
        )
        dietary_tags = [r[0] for r in cur.fetchall()]
    return {
        "cuisine": cuisines,
        "budget": budgets,
        "location": locations,
        "dietary_tags": dietary_tags,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_retrieval.py -v`
Expected: PASS (all tests in the file)

- [ ] **Step 5: Commit**

```bash
git add app/retrieval.py tests/test_retrieval.py
git commit -m "feat: add get_filter_options for the filter sidebar"
```

---

### Task 3: Wire filters and filter options into the API

**Files:**
- Modify: `app/main.py`
- Modify: `tests/test_main.py`

**Interfaces:**
- Consumes: `search(conn, query, top_k=6, filters=None)` (Task 1), `get_filter_options(conn)` (Task 2)
- Produces: `POST /api/chat` accepts an optional `filters` field in its JSON body; new `GET /api/filters/options` route

- [ ] **Step 1: Write the failing test**

Append to `tests/test_main.py` (this file already has `fake_store`, `client`, etc. from the session-persistence plan — if that plan hasn't landed yet, adapt these tests to whatever fixtures currently exist for mocking `search`/`get_db_connection` in this file):

```python
def test_chat_endpoint_forwards_filters_to_search(monkeypatch, fake_store):
    captured = {}

    def capturing_search(conn, message, top_k=6, filters=None):
        captured["filters"] = filters
        return fake_search(conn, message, top_k, filters)

    monkeypatch.setattr(main_module, "search", capturing_search)
    monkeypatch.setattr(main_module, "get_reply", fake_get_reply)

    client = TestClient(main_module.app)
    client.post(
        "/api/chat",
        json={"session_id": "s5", "message": "hi", "filters": {"cuisine": ["italian"]}},
    )

    assert captured["filters"] == {"cuisine": ["italian"]}


def test_filters_options_endpoint(monkeypatch, fake_store):
    def fake_get_filter_options(conn):
        return {"cuisine": ["italian"], "budget": ["mid"], "location": ["downtown"], "dietary_tags": ["vegan"]}

    monkeypatch.setattr(main_module, "get_filter_options", fake_get_filter_options)

    client = TestClient(main_module.app)
    resp = client.get("/api/filters/options")

    assert resp.status_code == 200
    assert resp.json() == {
        "cuisine": ["italian"], "budget": ["mid"], "location": ["downtown"], "dietary_tags": ["vegan"],
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_main.py::test_chat_endpoint_forwards_filters_to_search -v`
Expected: FAIL — `TypeError: fake_search() takes from 2 to 3 positional arguments but 4 were given` or `AttributeError: module 'app.main' has no attribute 'get_filter_options'`, depending which test runs first

- [ ] **Step 3: Write minimal implementation**

In `app/main.py`:

1. Add to the imports:

```python
from app.retrieval import get_filter_options, search
```

(replacing the existing `from app.retrieval import search` line)

2. In `chat_endpoint`, change:

```python
    message = body["message"]
```

to:

```python
    message = body["message"]
    filters = body.get("filters")
```

and change:

```python
    candidates = search(conn, message)
```

to:

```python
    candidates = search(conn, message, filters=filters)
```

3. Add a new route, next to the other `/api/...` routes:

```python
@app.get("/api/filters/options")
async def filters_options_endpoint():
    conn = get_db_connection()
    return JSONResponse(get_filter_options(conn))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_main.py -v`
Expected: PASS (all tests in the file)

- [ ] **Step 5: Run the full suite**

Run: `pytest -q`
Expected: only the pre-existing unrelated `test_settings_validate_raises_without_key` failure (see the session-persistence plan's Task 3 note), nothing new broken

- [ ] **Step 6: Commit**

```bash
git add app/main.py tests/test_main.py
git commit -m "feat: accept chat filters and expose GET /api/filters/options"
```
