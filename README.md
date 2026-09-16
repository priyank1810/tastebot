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
6. `cd static-src && npm install && npm run build && cd ..` — builds the frontend
   into `static/dist/`, which `uvicorn` serves. Skip this if `static/dist/` already
   exists.
7. `uvicorn app.main:app --reload`
8. Open `http://localhost:8000` in a browser.

## Frontend development

The chat UI lives in `static-src/` (React + Vite + TypeScript) and builds
to `static/dist/`, which the FastAPI app serves directly.

- One-time setup: `cd static-src && npm install`
- Development (hot reload, proxies `/api/*` to `:8000`): `cd static-src && npm run dev`, then open the Vite dev server URL it prints
- Production build (required before running `uvicorn` if `static/dist/` doesn't exist yet): `cd static-src && npm run build`
- Frontend tests: `cd static-src && npm run test`

## Tests

- Python: `pytest` (requires `docker compose up -d` running for DB-backed tests)
- Frontend: `cd static-src && npm run test`

## Manual smoke test

With the server running and the sample dataset ingested, try:

- "cheap vegetarian Indian food downtown"
- "somewhere for a nice date night, not too expensive"
- "vegan options near uptown"

Confirm: reply text stays grounded in restaurants that exist in
`data/restaurants.csv`, and the recommended restaurants render as cards
under the assistant's reply.
