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
