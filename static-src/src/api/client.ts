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
