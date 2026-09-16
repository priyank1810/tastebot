# Frontend Rebuild Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the vanilla-JS chat widget with a React + Vite + TypeScript app: dark-mode-first, with restaurant cards, a filter sidebar, session history, and a map for geocoded candidates.

**Architecture:** A new `static-src/` React app builds to `static/dist/`, which FastAPI serves exactly as it serves `static/` today (single deployable service). State is plain React Context (no Redux/Zustand — the app's state is small). Backend contracts for filters, sessions, and geocoding come from the other three plans (`2026-09-16-session-persistence.md`, `2026-09-16-structured-filtering.md`, `2026-09-16-restaurant-geocoding.md`) — this plan's components call those endpoints but tolerate them not existing yet (empty options, empty session list) so frontend and backend work can proceed in parallel.

**Tech Stack:** React 18, Vite, TypeScript, Tailwind CSS (dark mode via `class` strategy), react-leaflet + Leaflet, Vitest + React Testing Library.

**Spec:** `docs/superpowers/specs/2026-09-16-frontend-rebuild-design.md` (Frontend structure, Error handling, Testing plan sections)

## Global Constraints

- The built app must end up at `static/dist/` — FastAPI's `StaticFiles(directory="static/dist", html=True)` mount depends on that exact path.
- No state management library — plain `useState`/`useContext`/`useReducer` only.
- Dark mode is the default; light mode is a toggle persisted to `localStorage`. Use Tailwind's `class` strategy (`darkMode: 'class'` in `tailwind.config.js`), never the OS-preference (`media`) strategy.
- Every `localStorage` read/write must be wrapped in `try/catch` — private browsing or storage-disabled environments must not crash the app.
- No end-to-end/Playwright tests — component-level Vitest + RTL only, per the spec's Non-goals.
- All new frontend source lives under `static-src/`; nothing is added directly under `static/` except the generated `dist/` output (which is gitignored, matching how build output is normally handled — add `static/dist` to `.gitignore` if not already covered).

---

### Task 1: Scaffold the Vite + React + TS project and retire the old frontend

**Files:**
- Create: `static-src/package.json`, `static-src/vite.config.ts`, `static-src/tsconfig.json`, `static-src/tsconfig.node.json`, `static-src/tailwind.config.js`, `static-src/postcss.config.js`, `static-src/index.html`, `static-src/src/main.tsx`, `static-src/src/App.tsx`, `static-src/src/index.css`, `static-src/src/setupTests.ts`
- Delete: `static/index.html`, `static/chat.js`, `static/style.css`, `static/package.json`, `tests/test_chat_js.mjs`
- Modify: `app/main.py`, `.gitignore`

**Interfaces:**
- Consumes: nothing
- Produces: a buildable Vite project at `static-src/` whose `npm run build` output lands in `static/dist/`; a placeholder `App` component that later tasks replace piece by piece

- [ ] **Step 1: Create the placeholder React app**

Create `static-src/src/App.tsx`:

```tsx
export default function App() {
  return <div>Restaurant Recommendation Bot</div>
}
```

Create `static-src/src/main.tsx`:

```tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
```

Create `static-src/src/index.css`:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

Create `static-src/src/setupTests.ts`:

```ts
import '@testing-library/jest-dom'
```

Create `static-src/index.html`:

```html
<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Restaurant Recommendation Bot</title>
</head>
<body class="bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100">
  <div id="root"></div>
  <script type="module" src="/src/main.tsx"></script>
</body>
</html>
```

- [ ] **Step 2: Add build tooling config**

Create `static-src/vite.config.ts`:

```ts
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: '../static/dist',
    emptyOutDir: true,
  },
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: './src/setupTests.ts',
    globals: false,
  },
})
```

Create `static-src/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

Create `static-src/tsconfig.node.json`:

```json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true
  },
  "include": ["vite.config.ts"]
}
```

Create `static-src/tailwind.config.js`:

```js
/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: { extend: {} },
  plugins: [],
}
```

Create `static-src/postcss.config.js`:

```js
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```

Create `static-src/package.json`:

```json
{
  "name": "restaurant-chatbot-frontend",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "test": "vitest run"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-leaflet": "^4.2.1",
    "leaflet": "^1.9.4"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^6.6.2",
    "@testing-library/react": "^16.0.1",
    "@types/leaflet": "^1.9.12",
    "@types/react": "^18.3.12",
    "@types/react-dom": "^18.3.1",
    "@vitejs/plugin-react": "^4.3.3",
    "autoprefixer": "^10.4.20",
    "jsdom": "^25.0.1",
    "postcss": "^8.4.47",
    "tailwindcss": "^3.4.14",
    "typescript": "^5.6.3",
    "vite": "^5.4.10",
    "vitest": "^2.1.4"
  }
}
```

- [ ] **Step 3: Install dependencies and produce a first build**

Run: `cd static-src && npm install`
Expected: installs cleanly, creates `static-src/node_modules` and `static-src/package-lock.json`

Run: `cd static-src && npm run build`
Expected: builds cleanly, produces `static/dist/index.html` and hashed JS/CSS assets under `static/dist/assets/`

- [ ] **Step 4: Point FastAPI at the built app**

In `app/main.py`, change the last line from:

```python
app.mount("/", StaticFiles(directory="static", html=True), name="static")
```

to:

```python
app.mount("/", StaticFiles(directory="static/dist", html=True), name="static")
```

- [ ] **Step 5: Retire the old vanilla frontend**

```bash
git rm static/index.html static/chat.js static/style.css static/package.json tests/test_chat_js.mjs
```

- [ ] **Step 6: Ignore build output and installed packages**

Add to `.gitignore` (create the file if it doesn't exist, or append if it does):

```
static/dist/
static-src/node_modules/
```

- [ ] **Step 7: Verify the server starts and serves the placeholder app**

Run: `source .venv/bin/activate && uvicorn app.main:app --port 8000 &`
Run: `curl -s http://localhost:8000/ | grep -o 'Restaurant Recommendation Bot'`
Expected: prints `Restaurant Recommendation Bot` (confirms `static/dist/index.html` is being served)

Stop the server: `kill %1` (or find and kill the uvicorn process another way)

- [ ] **Step 8: Run the Python test suite to confirm nothing broke**

Run: `pytest -q`
Expected: only the pre-existing unrelated `test_settings_validate_raises_without_key` failure (see the session-persistence plan's Task 3 note), nothing new broken

- [ ] **Step 9: Commit**

```bash
git add static-src .gitignore app/main.py
git commit -m "feat: scaffold React/Vite/TS frontend, retire vanilla JS chat widget"
```

---

### Task 2: Typed API client

**Files:**
- Create: `static-src/src/api/client.ts`
- Test: `static-src/src/api/client.test.ts`

**Interfaces:**
- Consumes: the backend endpoints from the other three plans (`POST /api/chat`, `GET /api/sessions`, `GET /api/sessions/{id}`, `GET /api/filters/options`)
- Produces:
  - `interface RestaurantCandidate { name, cuisine, budget, location, rating: number | null, lat: number | null, lon: number | null }`
  - `interface ChatFilters { cuisine?: string[], budget?: string[], location?: string[], dietary_tags?: string[] }`
  - `interface ChatResponse { session_id: string, reply: string, candidates: RestaurantCandidate[] }`
  - `interface SessionSummary { id: string, title: string | null, created_at: string }`
  - `interface SessionMessage { role: string, content: string }`
  - `interface FilterOptions { cuisine: string[], budget: string[], location: string[], dietary_tags: string[] }`
  - `postChat(sessionId: string | null, message: string, filters?: ChatFilters): Promise<ChatResponse>`
  - `getSessions(): Promise<SessionSummary[]>`
  - `getSessionMessages(sessionId: string): Promise<SessionMessage[]>`
  - `getFilterOptions(): Promise<FilterOptions>`

- [ ] **Step 1: Write the failing test**

Create `static-src/src/api/client.test.ts`:

```ts
import { afterEach, describe, expect, it, vi } from 'vitest'
import { getFilterOptions, postChat } from './client'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('postChat', () => {
  it('sends session id, message, and filters in the request body', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ session_id: 's1', reply: 'hi', candidates: [] }),
    })
    vi.stubGlobal('fetch', fetchMock)

    const result = await postChat('s1', 'hello', { cuisine: ['italian'] })

    expect(fetchMock).toHaveBeenCalledWith('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: 's1', message: 'hello', filters: { cuisine: ['italian'] } }),
    })
    expect(result.reply).toBe('hi')
  })

  it('throws when the response is not ok', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 500 }))
    await expect(postChat('s1', 'hello')).rejects.toThrow('request failed with status 500')
  })
})

describe('getFilterOptions', () => {
  it('fetches from /api/filters/options', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ cuisine: [], budget: [], location: [], dietary_tags: [] }),
    })
    vi.stubGlobal('fetch', fetchMock)

    await getFilterOptions()

    expect(fetchMock).toHaveBeenCalledWith('/api/filters/options')
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd static-src && npm run test -- src/api/client.test.ts`
Expected: FAIL — cannot find module `./client`

- [ ] **Step 3: Write minimal implementation**

Create `static-src/src/api/client.ts`:

```ts
export interface RestaurantCandidate {
  name: string
  cuisine: string
  budget: string
  location: string
  rating: number | null
  lat: number | null
  lon: number | null
}

export interface ChatFilters {
  cuisine?: string[]
  budget?: string[]
  location?: string[]
  dietary_tags?: string[]
}

export interface ChatResponse {
  session_id: string
  reply: string
  candidates: RestaurantCandidate[]
}

export interface SessionSummary {
  id: string
  title: string | null
  created_at: string
}

export interface SessionMessage {
  role: string
  content: string
}

export interface FilterOptions {
  cuisine: string[]
  budget: string[]
  location: string[]
  dietary_tags: string[]
}

async function jsonOrThrow<T>(res: Response): Promise<T> {
  if (!res.ok) {
    throw new Error(`request failed with status ${res.status}`)
  }
  return res.json() as Promise<T>
}

export async function postChat(
  sessionId: string | null,
  message: string,
  filters?: ChatFilters,
): Promise<ChatResponse> {
  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, message, filters }),
  })
  return jsonOrThrow<ChatResponse>(res)
}

export async function getSessions(): Promise<SessionSummary[]> {
  const res = await fetch('/api/sessions')
  return jsonOrThrow<SessionSummary[]>(res)
}

export async function getSessionMessages(sessionId: string): Promise<SessionMessage[]> {
  const res = await fetch(`/api/sessions/${encodeURIComponent(sessionId)}`)
  return jsonOrThrow<SessionMessage[]>(res)
}

export async function getFilterOptions(): Promise<FilterOptions> {
  const res = await fetch('/api/filters/options')
  return jsonOrThrow<FilterOptions>(res)
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd static-src && npm run test -- src/api/client.test.ts`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add static-src/src/api
git commit -m "feat: add typed API client for chat/sessions/filters endpoints"
```

---

### Task 3: Theme (dark/light) context

**Files:**
- Create: `static-src/src/state/ThemeContext.tsx`
- Test: `static-src/src/state/ThemeContext.test.tsx`

**Interfaces:**
- Consumes: nothing
- Produces: `ThemeProvider`, `useTheme(): { theme: 'dark' | 'light', toggleTheme: () => void }`. Toggling flips the `dark` class on `document.documentElement` and persists to `localStorage['theme']`.

- [ ] **Step 1: Write the failing test**

Create `static-src/src/state/ThemeContext.test.tsx`:

```tsx
import { afterEach, expect, it } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { ThemeProvider, useTheme } from './ThemeContext'

afterEach(() => {
  cleanup()
  localStorage.clear()
  document.documentElement.className = ''
})

function Consumer() {
  const { theme, toggleTheme } = useTheme()
  return (
    <div>
      <span data-testid="theme">{theme}</span>
      <button onClick={toggleTheme}>toggle</button>
    </div>
  )
}

it('defaults to dark and toggles to light', () => {
  render(
    <ThemeProvider>
      <Consumer />
    </ThemeProvider>,
  )
  expect(screen.getByTestId('theme').textContent).toBe('dark')
  expect(document.documentElement.classList.contains('dark')).toBe(true)

  fireEvent.click(screen.getByText('toggle'))

  expect(screen.getByTestId('theme').textContent).toBe('light')
  expect(document.documentElement.classList.contains('dark')).toBe(false)
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd static-src && npm run test -- src/state/ThemeContext.test.tsx`
Expected: FAIL — cannot find module `./ThemeContext`

- [ ] **Step 3: Write minimal implementation**

Create `static-src/src/state/ThemeContext.tsx`:

```tsx
import { createContext, ReactNode, useContext, useEffect, useState } from 'react'

type Theme = 'dark' | 'light'

interface ThemeContextValue {
  theme: Theme
  toggleTheme: () => void
}

const ThemeContext = createContext<ThemeContextValue | null>(null)

function readStoredTheme(): Theme {
  try {
    return localStorage.getItem('theme') === 'light' ? 'light' : 'dark'
  } catch {
    return 'dark'
  }
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>(readStoredTheme)

  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark')
    try {
      localStorage.setItem('theme', theme)
    } catch {
      // storage unavailable (private browsing, etc.) — theme just won't persist
    }
  }, [theme])

  function toggleTheme() {
    setTheme((t) => (t === 'dark' ? 'light' : 'dark'))
  }

  return <ThemeContext.Provider value={{ theme, toggleTheme }}>{children}</ThemeContext.Provider>
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error('useTheme must be used within a ThemeProvider')
  return ctx
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd static-src && npm run test -- src/state/ThemeContext.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add static-src/src/state/ThemeContext.tsx static-src/src/state/ThemeContext.test.tsx
git commit -m "feat: add dark/light ThemeContext"
```

---

### Task 4: Session/chat context (messages, send, retry, session switching)

**Files:**
- Create: `static-src/src/state/SessionContext.tsx`
- Test: `static-src/src/state/SessionContext.test.tsx`

**Interfaces:**
- Consumes: `postChat`, `getSessionMessages`, `ChatFilters`, `RestaurantCandidate` from `../api/client` (Task 2)
- Produces:
  - `interface ChatMessage { role: string, content: string, candidates?: RestaurantCandidate[] }`
  - `SessionProvider`, `useSession(): { sessionId: string, messages: ChatMessage[], sending: boolean, error: string | null, sendMessage: (text: string, filters?: ChatFilters) => Promise<void>, retryLast: () => Promise<void>, startNewSession: () => void, openSession: (id: string) => Promise<void> }`

- [ ] **Step 1: Write the failing test**

Create `static-src/src/state/SessionContext.test.tsx`:

```tsx
import { afterEach, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { SessionProvider, useSession } from './SessionContext'
import * as client from '../api/client'

afterEach(() => {
  cleanup()
  localStorage.clear()
  vi.restoreAllMocks()
})

function Consumer() {
  const { messages, sendMessage, error, retryLast } = useSession()
  return (
    <div>
      <ul>
        {messages.map((m, i) => (
          <li key={i}>{m.role}: {m.content}</li>
        ))}
      </ul>
      {error && <div data-testid="error">{error}</div>}
      <button onClick={() => sendMessage('hello')}>send</button>
      <button onClick={() => retryLast()}>retry</button>
    </div>
  )
}

it('appends user and assistant messages on a successful send', async () => {
  vi.spyOn(client, 'postChat').mockResolvedValue({
    session_id: 's1', reply: 'hi there', candidates: [],
  })

  render(
    <SessionProvider>
      <Consumer />
    </SessionProvider>,
  )
  fireEvent.click(screen.getByText('send'))

  await waitFor(() => expect(screen.getByText('assistant: hi there')).toBeTruthy())
  expect(screen.getByText('user: hello')).toBeTruthy()
})

it('shows an error on failure and lets retryLast recover without duplicating the user message', async () => {
  vi.spyOn(client, 'postChat')
    .mockRejectedValueOnce(new Error('boom'))
    .mockResolvedValueOnce({ session_id: 's1', reply: 'recovered', candidates: [] })

  render(
    <SessionProvider>
      <Consumer />
    </SessionProvider>,
  )
  fireEvent.click(screen.getByText('send'))

  await waitFor(() => expect(screen.getByTestId('error')).toBeTruthy())
  expect(screen.getAllByText('user: hello')).toHaveLength(1)

  fireEvent.click(screen.getByText('retry'))

  await waitFor(() => expect(screen.getByText('assistant: recovered')).toBeTruthy())
  expect(screen.getAllByText('user: hello')).toHaveLength(1)
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd static-src && npm run test -- src/state/SessionContext.test.tsx`
Expected: FAIL — cannot find module `./SessionContext`

- [ ] **Step 3: Write minimal implementation**

Create `static-src/src/state/SessionContext.tsx`:

```tsx
import { createContext, ReactNode, useContext, useState } from 'react'
import { ChatFilters, RestaurantCandidate, getSessionMessages, postChat } from '../api/client'

export interface ChatMessage {
  role: string
  content: string
  candidates?: RestaurantCandidate[]
}

interface LastAttempt {
  text: string
  filters?: ChatFilters
}

interface SessionContextValue {
  sessionId: string
  messages: ChatMessage[]
  sending: boolean
  error: string | null
  sendMessage: (text: string, filters?: ChatFilters) => Promise<void>
  retryLast: () => Promise<void>
  startNewSession: () => void
  openSession: (id: string) => Promise<void>
}

const SessionContext = createContext<SessionContextValue | null>(null)

const NETWORK_ERROR_MESSAGE = "Couldn't reach the recommendation service, try again."

function readOrCreateSessionId(): string {
  try {
    const stored = localStorage.getItem('session_id')
    if (stored) return stored
  } catch {
    // fall through to generating a fresh one
  }
  const fresh = crypto.randomUUID()
  try {
    localStorage.setItem('session_id', fresh)
  } catch {
    // storage unavailable — session id just won't survive a reload
  }
  return fresh
}

function storeSessionId(id: string) {
  try {
    localStorage.setItem('session_id', id)
  } catch {
    // storage unavailable — non-fatal
  }
}

export function SessionProvider({ children }: { children: ReactNode }) {
  const [sessionId, setSessionId] = useState<string>(readOrCreateSessionId)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastAttempt, setLastAttempt] = useState<LastAttempt | null>(null)

  async function attemptReply(currentSessionId: string, text: string, filters?: ChatFilters) {
    setError(null)
    setSending(true)
    try {
      const response = await postChat(currentSessionId, text, filters)
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: response.reply, candidates: response.candidates },
      ])
    } catch {
      setError(NETWORK_ERROR_MESSAGE)
    } finally {
      setSending(false)
    }
  }

  async function sendMessage(text: string, filters?: ChatFilters) {
    setMessages((prev) => [...prev, { role: 'user', content: text }])
    setLastAttempt({ text, filters })
    await attemptReply(sessionId, text, filters)
  }

  async function retryLast() {
    if (!lastAttempt) return
    await attemptReply(sessionId, lastAttempt.text, lastAttempt.filters)
  }

  function startNewSession() {
    const fresh = crypto.randomUUID()
    storeSessionId(fresh)
    setSessionId(fresh)
    setMessages([])
    setError(null)
    setLastAttempt(null)
  }

  async function openSession(id: string) {
    const history = await getSessionMessages(id)
    storeSessionId(id)
    setSessionId(id)
    setMessages(history.map((m) => ({ role: m.role, content: m.content })))
    setError(null)
    setLastAttempt(null)
  }

  return (
    <SessionContext.Provider
      value={{ sessionId, messages, sending, error, sendMessage, retryLast, startNewSession, openSession }}
    >
      {children}
    </SessionContext.Provider>
  )
}

export function useSession(): SessionContextValue {
  const ctx = useContext(SessionContext)
  if (!ctx) throw new Error('useSession must be used within a SessionProvider')
  return ctx
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd static-src && npm run test -- src/state/SessionContext.test.tsx`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add static-src/src/state/SessionContext.tsx static-src/src/state/SessionContext.test.tsx
git commit -m "feat: add SessionContext for chat state, retry, and session switching"
```

---

### Task 5: Chat display components (cards, bubbles, input, error banner)

**Files:**
- Create: `static-src/src/components/RestaurantCard/RestaurantCard.tsx`, `static-src/src/components/RestaurantCard/RestaurantCard.test.tsx`
- Create: `static-src/src/components/Chat/MessageBubble.tsx`
- Create: `static-src/src/components/Chat/MessageList.tsx`
- Create: `static-src/src/components/Chat/ChatInput.tsx`, `static-src/src/components/Chat/ChatInput.test.tsx`
- Create: `static-src/src/components/Chat/ErrorBanner.tsx`

**Interfaces:**
- Consumes: `RestaurantCandidate` from `../../api/client` (Task 2), `ChatMessage` from `../../state/SessionContext` (Task 4)
- Produces:
  - `RestaurantCard({ restaurant: RestaurantCandidate })`
  - `MessageBubble({ message: ChatMessage })`
  - `MessageList({ messages: ChatMessage[] })`
  - `ChatInput({ onSend: (text: string) => void, disabled?: boolean })`
  - `ErrorBanner({ message: string, onRetry: () => void })`

- [ ] **Step 1: Write the failing test for RestaurantCard**

Create `static-src/src/components/RestaurantCard/RestaurantCard.test.tsx`:

```tsx
import { expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { RestaurantCard } from './RestaurantCard'

it('renders name, cuisine, budget, and location', () => {
  render(
    <RestaurantCard
      restaurant={{
        name: 'Pasta Palace', cuisine: 'italian', budget: 'mid',
        location: 'downtown', rating: 4.5, lat: null, lon: null,
      }}
    />,
  )
  expect(screen.getByText('Pasta Palace')).toBeTruthy()
  expect(screen.getByText(/italian/)).toBeTruthy()
  expect(screen.getByText(/mid/)).toBeTruthy()
  expect(screen.getByText(/downtown/)).toBeTruthy()
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd static-src && npm run test -- src/components/RestaurantCard`
Expected: FAIL — cannot find module `./RestaurantCard`

- [ ] **Step 3: Write minimal implementation for RestaurantCard**

Create `static-src/src/components/RestaurantCard/RestaurantCard.tsx`:

```tsx
import { RestaurantCandidate } from '../../api/client'

export function RestaurantCard({ restaurant }: { restaurant: RestaurantCandidate }) {
  const stars = restaurant.rating ? '★'.repeat(Math.round(restaurant.rating)) : ''
  return (
    <div className="rounded-lg border border-slate-200 dark:border-slate-700 p-3 bg-white dark:bg-slate-800">
      <div className="font-semibold">{restaurant.name}</div>
      <div className="text-sm text-slate-500 dark:text-slate-400">
        {restaurant.cuisine} · {restaurant.budget} · {restaurant.location}
      </div>
      {stars && (
        <div className="text-amber-500 text-sm">
          {stars} {restaurant.rating}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd static-src && npm run test -- src/components/RestaurantCard`
Expected: PASS

- [ ] **Step 5: Write MessageBubble and MessageList (no separate test — covered by the App-level test in Task 9)**

Create `static-src/src/components/Chat/MessageBubble.tsx`:

```tsx
import { ChatMessage } from '../../state/SessionContext'
import { RestaurantCard } from '../RestaurantCard/RestaurantCard'

export function MessageBubble({ message }: { message: ChatMessage }) {
  return (
    <div className={`flex flex-col gap-2 ${message.role === 'user' ? 'items-end' : 'items-start'}`}>
      <div
        className={`max-w-lg rounded-2xl px-4 py-2 ${
          message.role === 'user'
            ? 'bg-blue-600 text-white'
            : 'bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-slate-100'
        }`}
      >
        {message.content}
      </div>
      {message.candidates && message.candidates.length > 0 && (
        <div className="grid gap-2 w-full">
          {message.candidates.map((c) => (
            <RestaurantCard key={c.name} restaurant={c} />
          ))}
        </div>
      )}
    </div>
  )
}
```

Create `static-src/src/components/Chat/MessageList.tsx`:

```tsx
import { ChatMessage } from '../../state/SessionContext'
import { MessageBubble } from './MessageBubble'

export function MessageList({ messages }: { messages: ChatMessage[] }) {
  return (
    <div className="flex flex-col gap-4 p-4 overflow-y-auto flex-1">
      {messages.map((m, i) => (
        <MessageBubble key={i} message={m} />
      ))}
    </div>
  )
}
```

- [ ] **Step 6: Write the failing test for ChatInput**

Create `static-src/src/components/Chat/ChatInput.test.tsx`:

```tsx
import { expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { ChatInput } from './ChatInput'

it('calls onSend with the trimmed input and clears the field', () => {
  const onSend = vi.fn()
  render(<ChatInput onSend={onSend} />)

  const input = screen.getByPlaceholderText('Ask for a restaurant...') as HTMLInputElement
  fireEvent.change(input, { target: { value: '  cheap pizza  ' } })
  fireEvent.click(screen.getByText('Send'))

  expect(onSend).toHaveBeenCalledWith('cheap pizza')
  expect(input.value).toBe('')
})

it('does not call onSend for empty/whitespace-only input', () => {
  const onSend = vi.fn()
  render(<ChatInput onSend={onSend} />)

  fireEvent.click(screen.getByText('Send'))

  expect(onSend).not.toHaveBeenCalled()
})
```

- [ ] **Step 7: Run test to verify it fails**

Run: `cd static-src && npm run test -- src/components/Chat/ChatInput.test.tsx`
Expected: FAIL — cannot find module `./ChatInput`

- [ ] **Step 8: Write minimal implementation for ChatInput and ErrorBanner**

Create `static-src/src/components/Chat/ChatInput.tsx`:

```tsx
import { FormEvent, useState } from 'react'

interface ChatInputProps {
  onSend: (text: string) => void
  disabled?: boolean
}

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [text, setText] = useState('')

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    const trimmed = text.trim()
    if (!trimmed) return
    onSend(trimmed)
    setText('')
  }

  return (
    <form onSubmit={handleSubmit} className="flex gap-2 p-4 border-t border-slate-200 dark:border-slate-700">
      <input
        value={text}
        onChange={(e) => setText(e.target.value)}
        disabled={disabled}
        placeholder="Ask for a restaurant..."
        className="flex-1 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2"
      />
      <button
        type="submit"
        disabled={disabled}
        className="rounded-lg bg-blue-600 text-white px-4 py-2 disabled:opacity-50"
      >
        Send
      </button>
    </form>
  )
}
```

Create `static-src/src/components/Chat/ErrorBanner.tsx`:

```tsx
export function ErrorBanner({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="mx-4 mb-2 flex items-center justify-between rounded-lg bg-red-100 dark:bg-red-900/40 text-red-800 dark:text-red-200 px-4 py-2">
      <span>{message}</span>
      <button onClick={onRetry} className="underline font-medium">
        Retry
      </button>
    </div>
  )
}
```

- [ ] **Step 9: Run test to verify it passes**

Run: `cd static-src && npm run test -- src/components/Chat/ChatInput.test.tsx`
Expected: PASS (2 tests)

- [ ] **Step 10: Commit**

```bash
git add static-src/src/components/RestaurantCard static-src/src/components/Chat
git commit -m "feat: add chat display components (cards, bubbles, input, error banner)"
```

---

### Task 6: Filters context and panel

**Files:**
- Create: `static-src/src/state/FiltersContext.tsx`, `static-src/src/state/FiltersContext.test.tsx`
- Create: `static-src/src/components/Sidebar/FilterPanel.tsx`

**Interfaces:**
- Consumes: `getFilterOptions`, `ChatFilters`, `FilterOptions` from `../api/client` (Task 2)
- Produces: `FiltersProvider`, `useFilters(): { options: FilterOptions, selected: ChatFilters, toggleValue: (field: keyof ChatFilters, value: string) => void, clearFilters: () => void }`; `FilterPanel()` component

- [ ] **Step 1: Write the failing test**

Create `static-src/src/state/FiltersContext.test.tsx`:

```tsx
import { afterEach, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { FiltersProvider, useFilters } from './FiltersContext'
import * as client from '../api/client'

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

function Consumer() {
  const { options, selected, toggleValue } = useFilters()
  return (
    <div>
      <div data-testid="cuisines">{options.cuisine.join(',')}</div>
      <div data-testid="selected">{(selected.cuisine ?? []).join(',')}</div>
      <button onClick={() => toggleValue('cuisine', 'italian')}>toggle italian</button>
    </div>
  )
}

it('loads options on mount and toggles a selection on and off', async () => {
  vi.spyOn(client, 'getFilterOptions').mockResolvedValue({
    cuisine: ['italian', 'gujarati'], budget: [], location: [], dietary_tags: [],
  })

  render(
    <FiltersProvider>
      <Consumer />
    </FiltersProvider>,
  )

  await waitFor(() => expect(screen.getByTestId('cuisines').textContent).toBe('italian,gujarati'))

  fireEvent.click(screen.getByText('toggle italian'))
  expect(screen.getByTestId('selected').textContent).toBe('italian')

  fireEvent.click(screen.getByText('toggle italian'))
  expect(screen.getByTestId('selected').textContent).toBe('')
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd static-src && npm run test -- src/state/FiltersContext.test.tsx`
Expected: FAIL — cannot find module `./FiltersContext`

- [ ] **Step 3: Write minimal implementation**

Create `static-src/src/state/FiltersContext.tsx`:

```tsx
import { createContext, ReactNode, useContext, useEffect, useState } from 'react'
import { ChatFilters, FilterOptions, getFilterOptions } from '../api/client'

interface FiltersContextValue {
  options: FilterOptions
  selected: ChatFilters
  toggleValue: (field: keyof ChatFilters, value: string) => void
  clearFilters: () => void
}

const EMPTY_OPTIONS: FilterOptions = { cuisine: [], budget: [], location: [], dietary_tags: [] }

const FiltersContext = createContext<FiltersContextValue | null>(null)

export function FiltersProvider({ children }: { children: ReactNode }) {
  const [options, setOptions] = useState<FilterOptions>(EMPTY_OPTIONS)
  const [selected, setSelected] = useState<ChatFilters>({})

  useEffect(() => {
    getFilterOptions()
      .then(setOptions)
      .catch(() => setOptions(EMPTY_OPTIONS))
  }, [])

  function toggleValue(field: keyof ChatFilters, value: string) {
    setSelected((prev) => {
      const current = prev[field] ?? []
      const next = current.includes(value) ? current.filter((v) => v !== value) : [...current, value]
      return { ...prev, [field]: next.length > 0 ? next : undefined }
    })
  }

  function clearFilters() {
    setSelected({})
  }

  return (
    <FiltersContext.Provider value={{ options, selected, toggleValue, clearFilters }}>
      {children}
    </FiltersContext.Provider>
  )
}

export function useFilters(): FiltersContextValue {
  const ctx = useContext(FiltersContext)
  if (!ctx) throw new Error('useFilters must be used within a FiltersProvider')
  return ctx
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd static-src && npm run test -- src/state/FiltersContext.test.tsx`
Expected: PASS

- [ ] **Step 5: Add the FilterPanel component (no separate test — covered by the App-level test in Task 9)**

Create `static-src/src/components/Sidebar/FilterPanel.tsx`:

```tsx
import { ChatFilters } from '../../api/client'
import { useFilters } from '../../state/FiltersContext'

const FIELDS: { key: keyof ChatFilters; label: string }[] = [
  { key: 'cuisine', label: 'Cuisine' },
  { key: 'budget', label: 'Budget' },
  { key: 'location', label: 'Location' },
  { key: 'dietary_tags', label: 'Dietary' },
]

export function FilterPanel() {
  const { options, selected, toggleValue, clearFilters } = useFilters()

  return (
    <div className="flex flex-col gap-4 p-4 border-t border-slate-200 dark:border-slate-700">
      <div className="flex items-center justify-between">
        <span className="font-semibold">Filters</span>
        <button onClick={clearFilters} className="text-sm underline">
          Clear
        </button>
      </div>
      {FIELDS.map(({ key, label }) => (
        <div key={key}>
          <div className="text-sm font-medium mb-1">{label}</div>
          <div className="flex flex-wrap gap-1">
            {options[key].map((value) => (
              <button
                key={value}
                onClick={() => toggleValue(key, value)}
                className={`text-xs rounded-full px-2 py-1 border ${
                  (selected[key] ?? []).includes(value)
                    ? 'bg-blue-600 text-white border-blue-600'
                    : 'border-slate-300 dark:border-slate-600'
                }`}
              >
                {value}
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
```

- [ ] **Step 6: Commit**

```bash
git add static-src/src/state/FiltersContext.tsx static-src/src/state/FiltersContext.test.tsx static-src/src/components/Sidebar/FilterPanel.tsx
git commit -m "feat: add filter sidebar wired to /api/filters/options"
```

---

### Task 7: Session list sidebar

**Files:**
- Create: `static-src/src/components/Sidebar/SessionList.tsx`, `static-src/src/components/Sidebar/SessionList.test.tsx`

**Interfaces:**
- Consumes: `getSessions` from `../../api/client` (Task 2), `useSession` from `../../state/SessionContext` (Task 4)
- Produces: `SessionList()` component

- [ ] **Step 1: Write the failing test**

Create `static-src/src/components/Sidebar/SessionList.test.tsx`:

```tsx
import { afterEach, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { SessionList } from './SessionList'
import { SessionProvider } from '../../state/SessionContext'
import * as client from '../../api/client'

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
  localStorage.clear()
})

it('lists sessions and opens one on click', async () => {
  vi.spyOn(client, 'getSessions').mockResolvedValue([
    { id: 'abc', title: 'Cheap pizza', created_at: '2026-01-01T00:00:00' },
  ])
  vi.spyOn(client, 'getSessionMessages').mockResolvedValue([{ role: 'user', content: 'hi' }])

  render(
    <SessionProvider>
      <SessionList />
    </SessionProvider>,
  )

  await waitFor(() => expect(screen.getByText('Cheap pizza')).toBeTruthy())

  fireEvent.click(screen.getByText('Cheap pizza'))

  await waitFor(() => expect(client.getSessionMessages).toHaveBeenCalledWith('abc'))
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd static-src && npm run test -- src/components/Sidebar/SessionList.test.tsx`
Expected: FAIL — cannot find module `./SessionList`

- [ ] **Step 3: Write minimal implementation**

Create `static-src/src/components/Sidebar/SessionList.tsx`:

```tsx
import { useEffect, useState } from 'react'
import { SessionSummary, getSessions } from '../../api/client'
import { useSession } from '../../state/SessionContext'

export function SessionList() {
  const [sessions, setSessions] = useState<SessionSummary[]>([])
  const { sessionId, openSession, startNewSession } = useSession()

  useEffect(() => {
    getSessions()
      .then(setSessions)
      .catch(() => setSessions([]))
  }, [sessionId])

  return (
    <div className="flex flex-col gap-2 p-4">
      <button onClick={startNewSession} className="rounded-lg bg-blue-600 text-white px-3 py-2 text-sm">
        New chat
      </button>
      <ul className="flex flex-col gap-1">
        {sessions.map((s) => (
          <li key={s.id}>
            <button
              onClick={() => openSession(s.id)}
              className={`w-full text-left text-sm rounded-lg px-2 py-1 truncate ${
                s.id === sessionId ? 'bg-slate-200 dark:bg-slate-700' : ''
              }`}
            >
              {s.title ?? s.id}
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd static-src && npm run test -- src/components/Sidebar/SessionList.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add static-src/src/components/Sidebar/SessionList.tsx static-src/src/components/Sidebar/SessionList.test.tsx
git commit -m "feat: add session list sidebar wired to GET /api/sessions"
```

---

### Task 8: Map view

**Files:**
- Create: `static-src/src/components/MapView/MapView.tsx`, `static-src/src/components/MapView/MapView.test.tsx`

**Interfaces:**
- Consumes: `RestaurantCandidate` from `../../api/client` (Task 2)
- Produces: `MapView({ candidates: RestaurantCandidate[] })` — renders `null` when no candidate has both `lat` and `lon` set, otherwise a Leaflet map with one marker per geocoded candidate

- [ ] **Step 1: Write the failing test**

Create `static-src/src/components/MapView/MapView.test.tsx`:

```tsx
import { ReactNode } from 'react'
import { expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MapView } from './MapView'

vi.mock('react-leaflet', () => ({
  MapContainer: ({ children }: { children: ReactNode }) => <div data-testid="map">{children}</div>,
  TileLayer: () => null,
  Marker: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  Popup: ({ children }: { children: ReactNode }) => <div>{children}</div>,
}))

it('renders nothing when no candidates have coordinates', () => {
  const { container } = render(
    <MapView
      candidates={[
        { name: 'A', cuisine: 'x', budget: 'mid', location: 'y', rating: null, lat: null, lon: null },
      ]}
    />,
  )
  expect(container.firstChild).toBeNull()
})

it('renders a map with a marker per geocoded candidate', () => {
  render(
    <MapView
      candidates={[
        { name: 'A', cuisine: 'x', budget: 'mid', location: 'y', rating: null, lat: null, lon: null },
        { name: 'B', cuisine: 'x', budget: 'mid', location: 'y', rating: null, lat: 23.03, lon: 72.56 },
      ]}
    />,
  )
  expect(screen.getByTestId('map')).toBeTruthy()
  expect(screen.getByText('B')).toBeTruthy()
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd static-src && npm run test -- src/components/MapView/MapView.test.tsx`
Expected: FAIL — cannot find module `./MapView`

- [ ] **Step 3: Write minimal implementation**

Create `static-src/src/components/MapView/MapView.tsx`:

```tsx
import { MapContainer, Marker, Popup, TileLayer } from 'react-leaflet'
import { RestaurantCandidate } from '../../api/client'

type GeocodedCandidate = RestaurantCandidate & { lat: number; lon: number }

export function MapView({ candidates }: { candidates: RestaurantCandidate[] }) {
  const pins = candidates.filter(
    (c): c is GeocodedCandidate => c.lat != null && c.lon != null,
  )

  if (pins.length === 0) return null

  const center: [number, number] = [pins[0].lat, pins[0].lon]

  return (
    <div className="h-64 rounded-lg overflow-hidden border border-slate-200 dark:border-slate-700">
      <MapContainer center={center} zoom={13} style={{ height: '100%', width: '100%' }}>
        <TileLayer
          attribution="&copy; OpenStreetMap contributors"
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {pins.map((p) => (
          <Marker key={p.name} position={[p.lat, p.lon]}>
            <Popup>{p.name}</Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd static-src && npm run test -- src/components/MapView/MapView.test.tsx`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add static-src/src/components/MapView
git commit -m "feat: add MapView for geocoded chat candidates"
```

---

### Task 9: Assemble the app, final build, manual smoke test

**Files:**
- Modify: `static-src/src/App.tsx`
- Create: `static-src/src/App.test.tsx`
- Modify: `README.md`

**Interfaces:**
- Consumes: everything from Tasks 2-8
- Produces: the final `App` component that composes sidebar (SessionList + FilterPanel), chat column (MessageList + ErrorBanner + ChatInput), and MapView

- [ ] **Step 1: Write the failing test**

Create `static-src/src/App.test.tsx`:

```tsx
import { afterEach, expect, it, vi } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import App from './App'
import * as client from './api/client'

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
  localStorage.clear()
})

it('renders the chat shell without crashing', async () => {
  vi.spyOn(client, 'getSessions').mockResolvedValue([])
  vi.spyOn(client, 'getFilterOptions').mockResolvedValue({
    cuisine: [], budget: [], location: [], dietary_tags: [],
  })

  render(<App />)

  expect(screen.getByText('🍽️ Restaurant Recommendation Bot')).toBeTruthy()
  expect(screen.getByPlaceholderText('Ask for a restaurant...')).toBeTruthy()
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd static-src && npm run test -- src/App.test.tsx`
Expected: FAIL — the placeholder `App` from Task 1 doesn't render this text/input

- [ ] **Step 3: Write the final implementation**

Replace `static-src/src/App.tsx` with:

```tsx
import { ErrorBanner } from './components/Chat/ErrorBanner'
import { ChatInput } from './components/Chat/ChatInput'
import { MessageList } from './components/Chat/MessageList'
import { MapView } from './components/MapView/MapView'
import { FilterPanel } from './components/Sidebar/FilterPanel'
import { SessionList } from './components/Sidebar/SessionList'
import { FiltersProvider, useFilters } from './state/FiltersContext'
import { SessionProvider, useSession } from './state/SessionContext'
import { ThemeProvider, useTheme } from './state/ThemeContext'

function ChatArea() {
  const { messages, sending, error, sendMessage, retryLast } = useSession()
  const { selected } = useFilters()
  const { theme, toggleTheme } = useTheme()

  const lastWithCandidates = [...messages].reverse().find((m) => m.candidates && m.candidates.length > 0)

  return (
    <div className="flex flex-col flex-1 h-screen">
      <header className="flex items-center justify-between p-4 border-b border-slate-200 dark:border-slate-700">
        <span className="font-semibold">🍽️ Restaurant Recommendation Bot</span>
        <button onClick={toggleTheme} className="text-sm underline">
          {theme === 'dark' ? 'Light mode' : 'Dark mode'}
        </button>
      </header>
      <MessageList messages={messages} />
      {lastWithCandidates?.candidates && <MapView candidates={lastWithCandidates.candidates} />}
      {error && <ErrorBanner message={error} onRetry={retryLast} />}
      <ChatInput onSend={(text) => sendMessage(text, selected)} disabled={sending} />
    </div>
  )
}

export default function App() {
  return (
    <ThemeProvider>
      <SessionProvider>
        <FiltersProvider>
          <div className="flex h-screen bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100">
            <aside className="w-64 border-r border-slate-200 dark:border-slate-700 flex flex-col">
              <SessionList />
              <FilterPanel />
            </aside>
            <ChatArea />
          </div>
        </FiltersProvider>
      </SessionProvider>
    </ThemeProvider>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd static-src && npm run test -- src/App.test.tsx`
Expected: PASS

- [ ] **Step 5: Run the full frontend test suite**

Run: `cd static-src && npm run test`
Expected: all frontend tests pass

- [ ] **Step 6: Final production build**

Run: `cd static-src && npm run build`
Expected: builds cleanly with no TypeScript errors, produces the final `static/dist/`

- [ ] **Step 7: Manual smoke test against the real backend**

This requires the backend plans (`2026-09-16-session-persistence.md`, `2026-09-16-structured-filtering.md`, `2026-09-16-restaurant-geocoding.md`) to have landed for full functionality — filters/sessions/map will just show empty/no-op states otherwise, not crash.

Run: `docker start restaurant-rag-chatbot-postgres-1` (or `docker-compose up -d` if not already running)
Run: `source .venv/bin/activate && uvicorn app.main:app --port 8000`
Open `http://localhost:8000` in a browser and verify:
- Dark mode is on by default; the toggle switches to light and persists across a reload.
- Sending "cheap vegetarian gujarati food in navrangpura" returns a reply with restaurant cards.
- If the geocoding plan has run, at least one card's restaurant shows a pin on the map.
- The filter sidebar lists real cuisine/budget/location/dietary values and narrows results when selected.
- "New chat" clears the view; the session appears in the sidebar after the first message; clicking a past session reloads its history.

- [ ] **Step 8: Update README with the new frontend dev workflow**

In `README.md`, find the existing numbered setup steps (currently ending around step 7, "Open `http://localhost:8000` in a browser") and add after them:

```markdown
## Frontend development

The chat UI lives in `static-src/` (React + Vite + TypeScript) and builds
to `static/dist/`, which the FastAPI app serves directly.

- One-time setup: `cd static-src && npm install`
- Development (hot reload, proxies `/api/*` to `:8000`): `cd static-src && npm run dev`, then open the Vite dev server URL it prints
- Production build (required before running `uvicorn` if `static/dist/` doesn't exist yet): `cd static-src && npm run build`
- Frontend tests: `cd static-src && npm run test`
```

- [ ] **Step 9: Commit**

```bash
git add static-src/src/App.tsx static-src/src/App.test.tsx README.md
git commit -m "feat: assemble final chat app layout (sidebar, chat, map)"
```
