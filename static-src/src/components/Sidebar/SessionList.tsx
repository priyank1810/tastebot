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
