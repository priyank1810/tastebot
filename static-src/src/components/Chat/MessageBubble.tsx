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
