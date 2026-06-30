import { cn } from '../../utils/cn'
import { Message } from '../../types'
import { MessageBubble } from './MessageBubble'

interface ChatWindowProps {
  messages: Message[]
  streaming: boolean
  currentMessageId: string | null
  onScrollToBottom: () => void
}

export function ChatWindow({ messages, streaming, currentMessageId, onScrollToBottom }: ChatWindowProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const [scrolledUp, setScrolledUp] = useState(false)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streaming])

  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const { scrollTop, scrollHeight, clientHeight } = e.currentTarget
    const atBottom = scrollHeight - scrollTop - clientHeight < 50
    setScrolledUp(!atBottom)
  }

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center text-gray-500">
          <p className="text-lg mb-2">Start a conversation</p>
          <p className="text-sm">Send a message to begin</p>
        </div>
      </div>
    )
  }

  return (
    <div
      className="flex-1 overflow-y-auto p-4 space-y-4"
      onScroll={handleScroll}
    >
      {messages.map((message) => (
        <MessageBubble
          key={message.id}
          message={message}
          isStreaming={streaming && message.id === currentMessageId}
        />
      ))}
      <div ref={messagesEndRef} />
      {scrolledUp && (
        <button
          onClick={onScrollToBottom}
          className="fixed bottom-20 right-4 btn-primary rounded-full p-3 shadow-lg animate-bounce-in"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
          </svg>
        </button>
      )}
    </div>
  )
}