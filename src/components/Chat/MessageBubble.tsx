import React from 'react'
import { Message } from '../../types'
import { formatRelativeTime } from '../../utils/helpers'
import { cn } from '../../utils/cn'
import { ToolCallCard } from './ToolCallCard'
import { ThinkingPanel } from './ThinkingPanel'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeHighlight from 'rehype-highlight'
import { Copy, Check } from 'lucide-react'

interface MessageBubbleProps {
  message: Message;
  isStreaming?: boolean;
}

export function MessageBubble({ message, isStreaming }: MessageBubbleProps) {
  const isUser = message.role === 'user'
  const [copied, setCopied] = React.useState(false)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className={cn(
      'message-bubble relative group',
      isUser ? 'message-user' : 'message-assistant'
    )}>
      <div className="flex flex-col gap-2">
        {!isUser && (
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <span className="font-mono text-primary-400">ASSISTANT</span>
            <span className="text-gray-600">{formatRelativeTime(message.timestamp)}</span>
          </div>
        )}
        
        <div className="prose prose-invert dark:prose-dark max-w-none">
          <ReactMarkdown 
            remarkPlugins={[remarkGfm]} 
            rehypePlugins={[[rehypeHighlight, { ignoreMissing: true }]]}
            components={{
              code: ({ children, ...props }) => (
                <pre className="bg-black/50 rounded-lg p-4 overflow-x-auto"><code {...props}>{children}</code></pre>
              ),
            }}
          >
            {message.content}
          </ReactMarkdown>
        </div>

        {message.thinking && (
          <ThinkingPanel thinking={message.thinking} />
        )}

        {message.toolCalls && message.toolCalls.length > 0 && (
          <div className="space-y-2 mt-2 border-t border-dark-border pt-2">
            {message.toolCalls.map((toolCall) => (
              <ToolCallCard key={toolCall.id} toolCall={toolCall} />
            ))}
          </div>
        )}

        <div className="flex items-center gap-2 mt-2 opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            onClick={handleCopy}
            className="btn-ghost p-1.5 text-xs hover:bg-dark-elevated"
            title="Copy message"
          >
            {copied ? <Check className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4" />}
          </button>
          {isUser && (
            <span className="text-xs text-gray-500">{formatRelativeTime(message.timestamp)}</span>
          )}
        </div>
      </div>
    </div>
  )
}