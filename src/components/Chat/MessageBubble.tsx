import { cn } from '../../utils/cn'
import { Message } from '../../types'
import { Copy, Loader2 } from 'lucide-react'
import { ToolCallCard } from './ToolCallCard'
import { ThinkingPanel } from './ThinkingPanel'
import { useState } from 'react'

interface MessageBubbleProps {
  message: Message
  isStreaming?: boolean
}

export function MessageBubble({ message, isStreaming }: MessageBubbleProps) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const isAssistant = message.role === 'assistant'
  const isUser = message.role === 'user'
  const isSystem = message.role === 'system'

  return (
    <div className={cn(
      'flex gap-3 animate-slide-up',
      isUser && 'flex-row-reverse',
      isSystem && 'justify-center'
    )}>
      {!isUser && (
        <div className="w-8 h-8 rounded-full bg-primary-500 flex items-center justify-center flex-shrink-0">
          <span className="text-white text-xs font-bold">H</span>
        </div>
      )}
      <div className={cn(
        'max-w-[75%] flex flex-col gap-2',
        isUser ? 'items-end' : 'items-start'
      )}>
        <div className={cn(
          'relative rounded-2xl px-4 py-3',
          isUser ? 'bg-primary-500 text-white rounded-tr-none' :
          isAssistant ? 'bg-dark-elevated text-gray-100 rounded-tl-none' :
          'bg-yellow-500/20 text-yellow-300 rounded'
        )}>
          {isStreaming && (
            <div className="absolute top-2 right-2 flex items-center gap-1 text-xs text-gray-500">
              <Loader2 className="w-4 h-4 animate-spin" />
              Streaming...
            </div>
          )}
          <div className="whitespace-pre-wrap break-words">
            {message.content}
          </div>
          {!isStreaming && message.content && (
            <button
              onClick={handleCopy}
              className="absolute top-2 right-2 opacity-0 hover:opacity-100 transition-opacity text-xs p-1 text-gray-500 hover:text-white"
              aria-label="Copy message"
            >
              {copied ? 'Copied!' : 'Copy'}
            </button>
          )}
        </div>
        {message.thinking && (
          <ThinkingPanel thinking={message.thinking} />
        )}
        {message.toolCalls && message.toolCalls.length > 0 && (
          <div className={cn('mt-2 space-y-2', isUser ? 'items-end' : 'items-start')}>
            {message.toolCalls.map((toolCall, index) => (
              <ToolCallCard key={index} toolCall={toolCall} />
            ))}
          </div>
        )}
        {message.metadata && (
          <div className={cn('mt-2 text-xs text-gray-500 flex items-center gap-2', isUser ? 'justify-end' : '')}>
            <span>{message.metadata.model}</span>
            <span>•</span>
            <span>{message.metadata.tokens} tokens</span>
            <span>•</span>
            <span>{(message.metadata.latency / 1000).toFixed(1)}s</span>
          </div>
        )}
      </div>
      {isUser && (
        <div className="w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center flex-shrink-0">
          <span className="text-white text-xs font-bold">U</span>
        </div>
      )}
    </div>
  )
}