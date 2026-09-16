# Restaurant Chatbot — Frontend Rebuild Design Spec

Date: 2026-09-16
Status: Approved for planning

## Overview

Replace the current bare vanilla-JS chat widget (`static/index.html`,
`chat.js`, `style.css`) with a proper React + Vite + TypeScript
application. The rebuild adds three capabilities the current frontend
has no backend support for at all: structured filtering alongside
chat, persistent multi-session history, and a map view of recommended
restaurants. Each of these requires backend changes in addition to the
frontend rebuild; this spec covers all four pieces together since
they're being built as one project.

## Goals

- Rebuild the chat UI in React + Vite + TS with a polished,
  dark-mode-first visual design (light mode as a secondary toggle).
- Let users narrow chat-based recommendations with a filter sidebar
  (cuisine, budget, location, dietary tags) that combines with the
  existing semantic search rather than replacing it.
- Persist chat sessions server-side so history survives a backend
  restart and users can see/reopen past conversations.
- Show a map of the restaurants recommended in the current reply, when
  location data is available for them.
- Keep the app a single deployable service: FastAPI serves the built
  frontend, same as today.

## Non-goals

- No user accounts/login — sessions stay anonymous, identified by a
  client-generated UUID stored in `localStorage`. Carries forward the
  original spec's no-auth stance.
- No "browse all restaurants" map — the map only shows pins for the
  current chat reply's candidates, not the full catalog.
- No end-to-end/Playwright test suite — matches the project's existing
  test rigor (unit/integration only), avoided per YAGNI.
- No paid map/geocoding provider — Leaflet + OpenStreetMap +
  Nominatim only, to avoid introducing API keys/billing.
- No live restaurant API integration — still the static CSV catalog
  ingested into Postgres, per the original spec's non-goals.

## Architecture

Frontend: a React + Vite + TypeScript app, source under
`static-src/`, built to `static/dist/`. FastAPI keeps mounting the
built output as static files (`StaticFiles`) exactly as it does today
— no separate frontend server or CORS setup needed in production. In
development, the Vite dev server proxies `/api/*` requests to the
FastAPI process on `:8000`.

Backend gains three pieces of new surface area, each independent:

1. **Session persistence** — replaces the in-memory `_sessions` dict
   in `main.py` with two Postgres tables and two new read endpoints.
   `POST /api/chat` still does the same job, but now reads/writes
   history through Postgres instead of a process-local dict.
2. **Structured filtering** — `POST /api/chat` accepts an optional
   `filters` object; `retrieval.search()` turns whichever filter
   fields are present into SQL `WHERE` clauses, and vector similarity
   ranking still runs on top of that narrowed set. A new
   `GET /api/filters/options` endpoint returns the distinct values
   available for each filter field, for populating the sidebar.
3. **Geocoding for the map** — a one-time offline script adds
   latitude/longitude to existing restaurant rows via Nominatim. The
   `restaurants` table gains nullable `lat`/`lon` columns; `search()`
   returns them so `/api/chat` candidates carry coordinates when
   available.

## Data model changes

New tables:

| table | columns | notes |
|---|---|---|
| `chat_sessions` | `id uuid primary key`, `created_at timestamptz default now()`, `title text` | one row per session; `title` nullable, can be set later (e.g. from the first user message) |
| `chat_messages` | `id serial primary key`, `session_id uuid references chat_sessions(id)`, `role text`, `content text`, `created_at timestamptz default now()` | ordered by `id`/`created_at` per session |

`restaurants` table gains:

| column | type | notes |
|---|---|---|
| `lat` | double precision, nullable | populated by the geocoding script; null if geocoding failed or hasn't run for that row |
| `lon` | double precision, nullable | same |

## API changes

- `POST /api/chat`
  - Request body gains optional `filters: {cuisine?, budget?, location?, dietary_tags?}`.
  - History is now loaded from/persisted to `chat_messages` instead of
    the in-memory dict; a `chat_sessions` row is created on first use
    of a new `session_id`.
  - Response `candidates` gain nullable `lat`/`lon` fields.
- `GET /api/sessions` — list sessions (id, title, created_at), newest
  first, for the sidebar's session list.
- `GET /api/sessions/{id}` — full message history for one session, for
  resuming a past conversation.
- `GET /api/filters/options` — distinct `cuisine`, `budget`,
  `location`, and `dietary_tags` values currently in the `restaurants`
  table, for populating filter dropdowns.

## Data flow

**Filtering:** user selects filter values in the sidebar → held in
frontend `FiltersContext` → sent alongside the chat message on
`POST /api/chat` → `retrieval.search()` builds `WHERE cuisine = ANY(...)
AND budget = ANY(...) AND location = ANY(...) AND dietary_tags && ...`
for whichever filters are set, then still ranks the filtered set by
`embedding <=> query_embedding` → same LLM-grounded reply flow as
today, just over a narrower candidate pool. No filters set behaves
identically to today.

**Session history:** on first load, frontend checks `localStorage` for
a `session_id`; if absent, generates a UUID and stores it. Sidebar
calls `GET /api/sessions` to list past sessions; selecting one calls
`GET /api/sessions/{id}` and replaces the active chat view with that
history (further messages in that view still `POST` with that
session's id). Starting "New chat" generates a fresh UUID and clears
the visible history without deleting the old session's row.

**Geocoding (offline, one-time + rerun for new batches):**
`scripts/geocode_restaurants.py` selects restaurants where
`lat IS NULL`, queries Nominatim with `"{name}, {location},
Ahmedabad, India"`, rate-limited to Nominatim's usage policy (~1
request/second), and updates `lat`/`lon` on success. Failures are
logged and left `NULL` — never block the script or the app.

**Map rendering:** when a `/api/chat` response's `candidates` include
at least one row with non-null `lat`/`lon`, `MapView` renders a Leaflet
map with a pin per geocoded candidate; candidates without coordinates
just don't get a pin. No candidates geocoded → no map shown.

## Frontend structure

```
static-src/
  src/
    main.tsx, App.tsx
    api/client.ts          — typed fetch wrappers: postChat, getSessions, getSessionMessages, getFilterOptions
    state/
      SessionContext.tsx   — active session_id (localStorage-backed) + current message history
      FiltersContext.tsx   — selected cuisine/budget/location/dietary values
      ThemeContext.tsx     — dark/light, localStorage-backed, defaults dark
    components/
      Sidebar/SessionList.tsx, Sidebar/FilterPanel.tsx
      Chat/MessageList.tsx, Chat/MessageBubble.tsx, Chat/ChatInput.tsx
      RestaurantCard/RestaurantCard.tsx
      MapView/MapView.tsx   — react-leaflet; renders only when ≥1 candidate has lat/lon
    hooks/useChat.ts
```

State management is plain React Context + `useState`/`useReducer` —
no Redux/Zustand; the app's state (chat history, filter selections,
session list, theme) is small enough that an extra state library adds
weight without solving a real problem.

Layout: left sidebar (session list on top, filter panel below) + main
chat column (message bubbles, restaurant cards rendered inline under
assistant replies) + a map panel that appears below/beside the chat
only when the current reply has geocoded candidates.

Styling: Tailwind CSS, dark-mode-first via the `class` strategy
(defaults to dark; a toggle in the UI flips to light, persisted in
`localStorage`).

## Error handling

- **Frontend↔backend network failures** (fetch throws, 5xx): inline
  error banner in the chat pane ("Couldn't reach the recommendation
  service, try again") with a retry action that re-sends the last
  message. This is distinct from the existing server-side
  `FALLBACK_REPLY`, which covers Azure OpenAI call failures
  specifically.
- **Empty filtered results**: an assistant-style message ("No
  restaurants match those filters — try loosening them") instead of an
  empty candidate list.
- **Geocoding failures**: silent at the app level — the restaurant
  simply has no map pin; no user-facing error, no blocking.
- Existing error-handling behavior from the original spec (fail-fast
  on missing config/DB at boot, CSV validation skip-and-log, LLM
  call failure fallback) is unchanged.

## Testing plan

- **Backend**: pytest coverage for the new filter `WHERE`-clause
  logic in `retrieval.py`, session/message persistence (replacing the
  in-memory dict), and the geocoding script's skip-on-failure
  behavior. All run against the isolated `restaurants_test` database
  (see `TEST_DATABASE_URL` in `.env.example`), never the dev DB.
- **Frontend**: Vitest + React Testing Library for components with
  real logic — `ChatInput` submit behavior, `FilterPanel` selection,
  `RestaurantCard` rendering, and `MapView`'s "no geocoded candidates
  → no map" branch. No end-to-end suite (see Non-goals).

## Open assumptions

- Session identity is per-browser (`localStorage`), not per-person —
  acceptable since there's no login, consistent with the original
  spec's no-auth stance.
- Nominatim's usage policy (rate limit, attribution requirement) is
  acceptable for this app's scale (~262 restaurants, one-time batch
  plus occasional reruns for new data batches).
- Existing `retrieval.py`/`ingest.py`/`chat.py` behavior for the
  non-filtered, non-map path is unchanged — this spec only adds to it.
