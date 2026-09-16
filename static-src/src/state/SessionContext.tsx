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
