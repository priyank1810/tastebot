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
