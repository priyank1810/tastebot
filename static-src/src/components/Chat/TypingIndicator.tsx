export function TypingIndicator() {
  return (
    <div className="flex items-start">
      <div
        aria-label="Assistant is typing"
        className="flex items-center gap-1 rounded-2xl bg-slate-100 dark:bg-slate-800 px-4 py-3"
      >
        <span className="h-2 w-2 rounded-full bg-slate-400 dark:bg-slate-500 animate-bounce [animation-delay:0ms]" />
        <span className="h-2 w-2 rounded-full bg-slate-400 dark:bg-slate-500 animate-bounce [animation-delay:150ms]" />
        <span className="h-2 w-2 rounded-full bg-slate-400 dark:bg-slate-500 animate-bounce [animation-delay:300ms]" />
      </div>
    </div>
  )
}
