# Restaurant Recommendation Bot — Design Spec

Date: 2026-09-14
Status: Approved for planning

## Overview

A chatbot that recommends restaurants based on cuisine, budget, location,
dietary preferences, and free-text queries. Uses a retrieval-augmented
generation (RAG) pipeline: a CSV restaurant catalog is embedded and stored
in PostgreSQL/pgvector; at query time the user's message is embedded and
matched against the catalog via vector similarity search; the top 6
candidates are handed to Claude, which writes the final recommendation.
Served through a FastAPI backend and a custom-designed web chat frontend.

## Goals

- Answer natural-language restaurant requests ("cheap spicy vegetarian
  place downtown") with grounded recommendations from a real catalog.
- Support filtering signals: cuisine, budget tier, location/area, dietary
  tags (veg/vegan/gluten-free/halal/etc.).
- Present results as rich restaurant cards inside a chat conversation,
  not just prose.
- Keep the stack simple enough for one developer to run locally
  (Docker Postgres + local Python process).

## Non-goals

- No live reservation booking or real-time inventory.
- No multi-tenant/user-account system — single shared session model is
  enough for v1.
- No live external restaurant API (Google Places/Yelp) — catalog is a
  static CSV for v1; swapping in a live source is a future extension,
  not part of this spec.
- No production auth/rate-limiting hardening — dev/demo-grade scope.

## Architecture

FastAPI application with two flows:

1. **Ingestion** (offline, run via script/CLI, not a web request): reads
   `data/restaurants.csv`, validates rows, builds one text chunk per
   restaurant, embeds each chunk locally, and upserts rows (including
   the embedding vector) into a `restaurants` table in Postgres
   (pgvector extension enabled).
2. **Runtime chat**: `POST /api/chat` embeds the incoming user message
   with the same local embedding model, runs a pgvector cosine
   similarity search (`ORDER BY embedding <=> query_embedding LIMIT 6`),
   formats the top 6 rows as context, and sends that context plus
   conversation history to Claude. Claude's system prompt restricts it
   to recommending only from the supplied candidates. The reply (plus
   structured candidate data for cards) is returned to the frontend.

Postgres runs in Docker (pgvector image) for local dev. The FastAPI
process serves the static frontend directly (`StaticFiles`) so the
whole app is one process to run.

## Components

| Component | Responsibility |
|---|---|
| `data/restaurants.csv` | Raw catalog: name, cuisine, budget, location, dietary_tags, description, rating |
| `ingest.py` | Parse CSV (pandas) → validate rows → build per-row text blob → embed → upsert into Postgres |
| `db.py` | Postgres connection, pgvector extension + schema setup |
| `retrieval.py` | Embed a query string, run top-6 pgvector similarity search |
| `chat.py` | Build Claude prompt from retrieved candidates + history, call Anthropic API, return reply + structured candidates |
| `main.py` | FastAPI app: `/api/chat` route, session store (in-memory dict keyed by session id), mounts `static/` |
| `static/` | Chat frontend: modern chat UI, restaurant result rendered as rich cards (name, cuisine, budget, rating, location) |
| `docker-compose.yml` | Postgres + pgvector container for local dev |
| `requirements.txt` | fastapi, uvicorn, sentence-transformers, psycopg2-binary, pgvector, pandas, anthropic, python-dotenv |

Embedding model: `sentence-transformers` `all-MiniLM-L6-v2` (384-dim,
local, no external embedding API/cost). Chat model: Claude (Anthropic
API), used for generation only — no tool-use needed since retrieval
already narrows candidates before Claude sees them.

## Data model

`restaurants` table (Postgres, pgvector extension):

| column | type | notes |
|---|---|---|
| id | serial primary key | |
| name | text | |
| cuisine | text | |
| budget | text | enum-like: budget / mid / premium |
| location | text | area/neighborhood |
| dietary_tags | text[] | e.g. {vegetarian, vegan, gluten_free} |
| description | text | free text, source for embedding |
| rating | numeric | |
| embedding | vector(384) | pgvector column, cosine distance ops |

## Data flow

**Ingestion (offline):**
CSV → pandas read → validate (required fields present, budget in allowed
set, drop + log bad rows) → build text per row (e.g. "`{name}` serves
`{cuisine}` cuisine in `{location}`. Budget: `{budget}`. Dietary:
`{dietary_tags}`. `{description}`") → encode with sentence-transformers
→ batch insert/upsert into `restaurants`.

**Runtime query:**
User message → `POST /api/chat {session_id, message}` → append to
session history → embed message (same model) → pgvector similarity
search, top 6 rows → format as context block → call Claude with system
prompt ("recommend only using the candidates given; if none fit well,
say so and offer closest options") + context + history → Claude reply
→ response includes reply text + the top-6 candidate rows (for card
rendering) → frontend renders reply bubble + restaurant cards.

## Frontend

Modern chat-app look: message bubbles, subtle color accent, light
food/restaurant theming touches. Restaurant recommendations render as
rich cards inline in the conversation (name, cuisine, budget tier,
rating, location) rather than as plain text. Built with the
`frontend-design` skill's guidance for visual polish rather than
default/templated styling. Plain HTML/CSS/JS (no frontend framework
needed for this scope), served as static files by FastAPI.

## Error handling

- No `ANTHROPIC_API_KEY` or no DB connection at boot → fail fast with a
  clear startup error.
- CSV validation errors during ingestion → skip the bad row, log the
  reason, continue (ingestion never crashes on one bad row).
- Embedding model fails to load → fail fast at ingestion/startup.
- Weak similarity matches (low relevance) → still return the top 6;
  the system prompt tells Claude to hedge ("closest matches, may not
  fully fit") rather than presenting them as certain fits.
- Claude API error/timeout → catch, return a friendly fallback chat
  message to the user, log the detailed error server-side.

## Testing plan

- Unit tests for CSV validation logic (missing required field, invalid
  budget enum value, etc.).
- Unit tests for `retrieval.py` — given a small mock/seeded dataset,
  confirm exactly 6 results returned, ordered by similarity distance.
- Manual smoke test: run ingestion on the sample CSV, ask a handful of
  representative queries through `/api/chat`, confirm top-6 candidates
  are sane and Claude's reply stays grounded in them.

## Open assumptions

- Single shared/anonymous session model (session id via cookie), no
  login — acceptable for v1 scope per Non-goals.
- Sample catalog size: ~30-50 restaurants, enough to demo filtering
  and similarity search meaningfully without needing a large dataset.
