# Restaurant Recommendation Bot

RAG-based chatbot that recommends restaurants by cuisine, budget, location,
and dietary preference. See `docs/superpowers/specs/2026-09-14-restaurant-rag-chatbot-design.md`
for the design.

## Setup

1. `cp .env.example .env` and fill in `ANTHROPIC_API_KEY`.
2. `docker compose up -d` — starts Postgres with pgvector on `localhost:5433`
   (5432 is left free in case a system Postgres is already using it).
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
