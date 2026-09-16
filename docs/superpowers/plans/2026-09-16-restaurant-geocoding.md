# Restaurant Geocoding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add nullable `lat`/`lon` coordinates to the `restaurants` table, a one-time (rerunnable) script to populate them via Nominatim, and surface them through `search()` and `/api/chat` so the frontend can drop map pins.

**Architecture:** A schema migration function adds the columns idempotently at startup. A geocoding module queries Nominatim per un-geocoded restaurant, rate-limited, writing results back; failures are left `NULL` and never block the run. `retrieval.py` and `main.py` pass `lat`/`lon` straight through to the API response.

**Tech Stack:** Python standard library only for the geocoding HTTP call (`urllib.request`) — no new dependency, since this is a low-volume one-off script, not a hot path.

**Spec:** `docs/superpowers/specs/2026-09-16-frontend-rebuild-design.md` (Geocoding sections of Data model changes, API changes, Data flow)

**Depends on:** `2026-09-16-session-persistence.md` should land first — Task 2 of this plan extends the `fake_store` fixture in `tests/test_main.py` that plan introduces. If it hasn't landed, apply that plan's Task 3 first (or adapt Task 2 Step 5 here to whatever mocking pattern `test_main.py` currently uses).

## Global Constraints

- Tests must never touch the dev database, and must never make real network calls to Nominatim — always fake the `geocode()` function in tests.
- Failures (no result, network error, timeout) must never raise out of the batch run — only that one restaurant stays un-geocoded (`lat`/`lon` remain `NULL`), and the run continues.
- Respect Nominatim's usage policy: one request at a time, at least ~1 second apart, and a descriptive `User-Agent` header (no default `urllib`/`python-requests` UA).
- This plan follows the existing `app/ingest.py` convention of "a module in `app/` runnable via `python -m app.<name>`" rather than introducing a separate `scripts/` directory, to match the codebase's established pattern.

---

### Task 1: Schema migration for `lat`/`lon`

**Files:**
- Modify: `app/db.py`
- Modify: `app/main.py`
- Test: `tests/test_db.py`

**Interfaces:**
- Consumes: nothing new
- Produces: `init_geocoding_schema(conn) -> None` — idempotent, safe to call every startup even if the columns already exist

- [ ] **Step 1: Write the failing test**

Append to `tests/test_db.py`:

```python
from app.db import init_geocoding_schema


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
```

Also update the top of `tests/test_db.py` to import `settings`:

```python
from app.config import settings
from app.db import get_connection, init_schema
```

(keep the existing `test_init_schema_creates_table` function as-is other than this shared import line)

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_db.py::test_init_geocoding_schema_adds_lat_lon_columns -v`
Expected: FAIL — `ImportError: cannot import name 'init_geocoding_schema'`

- [ ] **Step 3: Write minimal implementation**

Append to `app/db.py`:

```python
def init_geocoding_schema(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("ALTER TABLE restaurants ADD COLUMN IF NOT EXISTS lat DOUBLE PRECISION")
        cur.execute("ALTER TABLE restaurants ADD COLUMN IF NOT EXISTS lon DOUBLE PRECISION")
    conn.commit()
```

Then in `app/main.py`, add `init_geocoding_schema` to the `from app.db import ...` line and call it in `lifespan` right after `init_session_schema(conn)`:

```python
from app.db import get_connection, init_geocoding_schema
```

```python
    conn = get_db_connection()
    init_session_schema(conn)
    init_geocoding_schema(conn)
    yield
```

(If the session-persistence plan hasn't landed yet and `init_session_schema` isn't present, just add the `init_geocoding_schema(conn)` call after `get_db_connection()` instead.)

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_db.py -v`
Expected: PASS (both tests in the file)

- [ ] **Step 5: Commit**

```bash
git add app/db.py app/main.py tests/test_db.py
git commit -m "feat: add lat/lon columns to restaurants for map view"
```

---

### Task 2: `RetrievedRestaurant` and `search()` return coordinates

**Files:**
- Modify: `app/retrieval.py`
- Modify: `app/main.py`
- Test: `tests/test_retrieval.py`
- Test: `tests/test_main.py`

**Interfaces:**
- Consumes: `lat`/`lon` columns (Task 1)
- Produces: `RetrievedRestaurant` gains `lat: float | None = None` and `lon: float | None = None` fields (defaulted, so every existing call site that constructs `RetrievedRestaurant(...)` without them keeps working); `/api/chat` response candidates include `"lat"` and `"lon"` keys

- [ ] **Step 1: Write the failing test**

Append to `tests/test_retrieval.py`:

```python
def test_search_returns_lat_lon_when_present(db_conn, tmp_path):
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text(CSV_CONTENT)
    ingest_csv(str(csv_path), conn=db_conn)
    with db_conn.cursor() as cur:
        cur.execute(
            "ALTER TABLE restaurants ADD COLUMN IF NOT EXISTS lat DOUBLE PRECISION"
        )
        cur.execute(
            "ALTER TABLE restaurants ADD COLUMN IF NOT EXISTS lon DOUBLE PRECISION"
        )
        cur.execute(
            "UPDATE restaurants SET lat = 23.03, lon = 72.56 WHERE name = 'Pasta Palace'"
        )

    results = search(db_conn, "cheap italian pizza", top_k=6)

    by_name = {r.name: r for r in results}
    assert by_name["Pasta Palace"].lat == 23.03
    assert by_name["Pasta Palace"].lon == 72.56
    other = [r for r in results if r.name != "Pasta Palace"][0]
    assert other.lat is None
    assert other.lon is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_retrieval.py::test_search_returns_lat_lon_when_present -v`
Expected: FAIL — `AttributeError: 'RetrievedRestaurant' object has no attribute 'lat'`

- [ ] **Step 3: Write minimal implementation**

In `app/retrieval.py`, change the dataclass to:

```python
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
    lat: float | None = None
    lon: float | None = None
```

Change the `SELECT` in `search()` from:

```python
            SELECT name, cuisine, budget, location, dietary_tags, description, rating,
                   embedding <=> %s AS distance
```

to:

```python
            SELECT name, cuisine, budget, location, dietary_tags, description, rating,
                   embedding <=> %s AS distance, lat, lon
```

and change the row-unpacking loop from:

```python
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

to:

```python
    return [
        RetrievedRestaurant(
            name=row[0], cuisine=row[1], budget=row[2], location=row[3],
            dietary_tags=row[4] or [], description=row[5],
            rating=float(row[6]) if row[6] is not None else None,
            distance=float(row[7]),
            lat=row[8], lon=row[9],
        )
        for row in rows
    ]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_retrieval.py -v`
Expected: PASS. Note: this will fail with `UndefinedColumn: column "lat" does not exist` if Task 1 hasn't landed in this environment yet — Task 1 must land first since this task's `search()` query now selects those columns unconditionally.

- [ ] **Step 5: Include lat/lon in the API response**

Append to `tests/test_main.py`:

```python
def test_chat_endpoint_includes_lat_lon_in_candidates(monkeypatch, fake_store):
    def fake_search_with_coords(conn, message, top_k=6, filters=None):
        return [
            RetrievedRestaurant(
                name="Pasta Palace", cuisine="italian", budget="mid",
                location="downtown", dietary_tags=["vegetarian"],
                description="Fresh pasta", rating=4.5, distance=0.1,
                lat=23.03, lon=72.56,
            ),
        ]

    monkeypatch.setattr(main_module, "search", fake_search_with_coords)
    monkeypatch.setattr(main_module, "get_reply", fake_get_reply)

    client = TestClient(main_module.app)
    resp = client.post("/api/chat", json={"session_id": "s6", "message": "hi"})

    candidate = resp.json()["candidates"][0]
    assert candidate["lat"] == 23.03
    assert candidate["lon"] == 72.56
```

Run: `pytest tests/test_main.py::test_chat_endpoint_includes_lat_lon_in_candidates -v`
Expected: FAIL — `KeyError: 'lat'`

In `app/main.py`, change the candidate dict comprehension in `chat_endpoint` from:

```python
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
```

to:

```python
        "candidates": [
            {
                "name": c.name,
                "cuisine": c.cuisine,
                "budget": c.budget,
                "location": c.location,
                "rating": c.rating,
                "lat": c.lat,
                "lon": c.lon,
            }
            for c in candidates
        ],
```

Run: `pytest tests/test_main.py -v`
Expected: PASS (all tests in the file)

- [ ] **Step 6: Run the full suite**

Run: `pytest -q`
Expected: only the pre-existing unrelated `test_settings_validate_raises_without_key` failure, nothing new broken

- [ ] **Step 7: Commit**

```bash
git add app/retrieval.py app/main.py tests/test_retrieval.py tests/test_main.py
git commit -m "feat: surface restaurant lat/lon through search and /api/chat"
```

---

### Task 3: Geocoding script (`app/geocode.py`)

**Files:**
- Create: `app/geocode.py`
- Test: `tests/test_geocode.py`

**Interfaces:**
- Consumes: `init_geocoding_schema(conn)` (Task 1)
- Produces:
  - `geocode(name: str, location: str) -> tuple[float, float] | None`
  - `run(conn) -> dict` returning `{"geocoded": int, "failed": int}`
  - `RATE_LIMIT_SECONDS` module-level constant (tests override it to `0` to run fast)

- [ ] **Step 1: Write the failing test**

Create `tests/test_geocode.py`:

```python
from app import geocode
from app.ingest import ingest_csv

CSV_CONTENT = """name,cuisine,budget,location,dietary_tags,description,rating
Test Cafe,cafe,mid,navrangpura,vegetarian,A cafe.,
Unfindable Place,cafe,mid,nowhereville,vegetarian,Will not geocode.,
"""


def fake_geocode(name, location):
    if name == "Test Cafe":
        return (23.03, 72.56)
    return None


def test_run_updates_lat_lon_and_skips_failures(db_conn, tmp_path, monkeypatch):
    monkeypatch.setattr(geocode, "geocode", fake_geocode)
    monkeypatch.setattr(geocode, "RATE_LIMIT_SECONDS", 0)
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text(CSV_CONTENT)
    ingest_csv(str(csv_path), conn=db_conn)

    result = geocode.run(db_conn)

    assert result == {"geocoded": 1, "failed": 1}
    with db_conn.cursor() as cur:
        cur.execute("SELECT name, lat, lon FROM restaurants ORDER BY name")
        rows = cur.fetchall()
    assert rows == [
        ("Test Cafe", 23.03, 72.56),
        ("Unfindable Place", None, None),
    ]


def test_run_skips_already_geocoded_rows(db_conn, tmp_path, monkeypatch):
    calls = []

    def counting_geocode(name, location):
        calls.append(name)
        return (1.0, 2.0)

    monkeypatch.setattr(geocode, "geocode", counting_geocode)
    monkeypatch.setattr(geocode, "RATE_LIMIT_SECONDS", 0)
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text(CSV_CONTENT)
    ingest_csv(str(csv_path), conn=db_conn)

    geocode.run(db_conn)
    calls.clear()
    result = geocode.run(db_conn)

    assert result == {"geocoded": 0, "failed": 0}
    assert calls == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_geocode.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.geocode'`

- [ ] **Step 3: Write minimal implementation**

Create `app/geocode.py`:

```python
import json
import time
import urllib.parse
import urllib.request

from app.db import get_connection, init_geocoding_schema

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "restaurant-rag-chatbot/1.0 (internal tool, not for redistribution)"
RATE_LIMIT_SECONDS = 1.1


def geocode(name: str, location: str) -> tuple[float, float] | None:
    query = f"{name}, {location}, Ahmedabad, India"
    url = f"{NOMINATIM_URL}?{urllib.parse.urlencode({'q': query, 'format': 'json', 'limit': 1})}"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            results = json.loads(response.read())
    except Exception:
        return None
    if not results:
        return None
    return float(results[0]["lat"]), float(results[0]["lon"])


def run(conn) -> dict:
    init_geocoding_schema(conn)
    with conn.cursor() as cur:
        cur.execute("SELECT id, name, location FROM restaurants WHERE lat IS NULL")
        rows = cur.fetchall()

    geocoded = 0
    failed = 0
    for row_id, name, location in rows:
        coords = geocode(name, location)
        if coords is None:
            failed += 1
            time.sleep(RATE_LIMIT_SECONDS)
            continue
        lat, lon = coords
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE restaurants SET lat = %s, lon = %s WHERE id = %s",
                (lat, lon, row_id),
            )
        geocoded += 1
        time.sleep(RATE_LIMIT_SECONDS)

    conn.commit()
    return {"geocoded": geocoded, "failed": failed}


if __name__ == "__main__":
    conn = get_connection()
    result = run(conn)
    print(f"geocoded {result['geocoded']} rows, failed {result['failed']}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_geocode.py -v`
Expected: PASS (both tests)

- [ ] **Step 5: Run the full suite**

Run: `pytest -q`
Expected: only the pre-existing unrelated `test_settings_validate_raises_without_key` failure, nothing new broken

- [ ] **Step 6: Commit**

```bash
git add app/geocode.py tests/test_geocode.py
git commit -m "feat: add Nominatim-based geocoding script for restaurant map pins"
```

- [ ] **Step 7: Run the script against the real dev database**

This step is manual, not automated — it populates real coordinates for the live catalog:

Run: `python -m app.geocode`
Expected: prints `geocoded N rows, failed M rows` where N+M equals however many restaurants don't yet have coordinates. Re-running it later (e.g. after adding new restaurant batches) only geocodes the new rows, since `run()` only selects `WHERE lat IS NULL`.
