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
