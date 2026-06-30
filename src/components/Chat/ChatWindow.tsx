import React, { useRef, useEffect } from 'react'
import { Message } from '../../types'
import { cn } from '../../utils/cn'
import { MessageBubble } from './MessageBubble'

interface ChatWindowProps {
  messages: Message[];
  streaming: boolean;
  currentMessageId: string | null;
  onScrollToBottom: () => void;
}

export function ChatWindow({ messages, streaming, currentMessageId }: ChatWindowProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streaming])

  const handleWheel = (e: React.WheelEvent) => {
    if (containerRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = containerRef.current
      const atBottom = scrollHeight - scrollTop - clientHeight < 50
      if (atBottom && e.deltaY > 0) {
        e.preventDefault()
      }
    }
  }

  return (
    <div 
      ref={containerRef}
      className="flex-1 overflow-y-auto p-4 space-y-4"
      onWheel={handleWheel}
    >
      {messages.map((message) => (
        <div key={message.id} className={cn('flex', message.role === 'user' ? 'justify-end' : 'justify-start')}>
          <MessageBubble message={message} />
        </div>
      ))}
      
      {currentMessageId && (
        <div className="flex justify-start">
          <MessageBubble 
            message={{ 
              id: currentMessageId, 
              role: 'assistant', 
              content: '', 
              timestamp: new Date(),
              toolCalls: [],
            }} 
            isStreaming 
          />
        </div>
      )}

      {streaming && (
        <div className="flex justify-start animate-pulse-soft">
          <div className="message-bubble bg-dark-elevated border border-dark-border flex items-center gap-2 px-4 py-2">
            <div className="flex gap-1">
              <div className="w-2 h-2 bg-primary-500 rounded-full animate-bounce" style={{animationDelay: '0ms'}}></div>
              <div className="w-2 h-2 bg-primary-500 rounded-full animate-bounce" style={{animationDelay: '100ms'}}></div>
              <div className="w-2 h-2 bg-primary-500 rounded-full animate-bounce" style={{animationDelay: '200ms'}}></div>
            </div>
            <span className="text-gray-400 text-sm">Thinking...</span>
          </div>
        </div>
      )}

      <div ref={messagesEndRef} />
    </div>
  )
}