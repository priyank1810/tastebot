import { useEffect, useState } from 'react'
import { ErrorBanner } from './components/Chat/ErrorBanner'
import { ChatInput } from './components/Chat/ChatInput'
import { MessageList } from './components/Chat/MessageList'
import { TypingIndicator } from './components/Chat/TypingIndicator'
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
  const [mapClosed, setMapClosed] = useState(false)

  // A new answer with its own candidates should show its map again,
  // even if the user closed the map for a previous answer.
  useEffect(() => {
    setMapClosed(false)
  }, [lastWithCandidates])

  return (
    <div className="flex flex-col flex-1 h-screen">
      <header className="flex items-center justify-between p-4 border-b border-slate-200 dark:border-slate-700">
        <span className="font-semibold">🍽️ Restaurant Recommendation Bot</span>
        <button onClick={toggleTheme} className="text-sm underline">
          {theme === 'dark' ? 'Light mode' : 'Dark mode'}
        </button>
      </header>
      <MessageList messages={messages} />
      {sending && (
        <div className="px-4 pb-4">
          <TypingIndicator />
        </div>
      )}
      {lastWithCandidates?.candidates && !mapClosed && (
        <MapView candidates={lastWithCandidates.candidates} onClose={() => setMapClosed(true)} />
      )}
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
            <aside className="w-64 h-screen overflow-y-auto border-r border-slate-200 dark:border-slate-700 flex flex-col">
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
