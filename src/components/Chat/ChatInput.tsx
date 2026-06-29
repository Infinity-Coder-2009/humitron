import React, { useRef, useState } from 'react'
import { cn } from '../../utils/cn'
import { Send, Mic, Paperclip, X } from 'lucide-react'

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  streaming?: boolean;
  onStop?: () => void;
}

export function ChatInput({ onSend, disabled, streaming, onStop }: ChatInputProps) {
  const [value, setValue] = useState('')
  const [showAttach, setShowAttach] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (value.trim() && !disabled) {
      onSend(value.trim())
      setValue('')
      textareaRef.current?.focus()
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  const adjustHeight = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const textarea = e.target
    textarea.style.height = 'auto'
    textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`
  }

  return (
    <form onSubmit={handleSubmit} className="w-full">
      <div className="flex items-end gap-2 p-4 bg-dark-surface border-t border-dark-border">
        <div className="flex-1 relative">
          <textarea
            ref={textareaRef}
            value={value}
            onChange={e => {
              setValue(e.target.value)
              adjustHeight(e)
            }}
            onKeyDown={handleKeyDown}
            placeholder={streaming ? 'Agent is thinking...' : 'Message Humitron... (Shift+Enter for new line)'}
            disabled={disabled || streaming}
            className={cn(
              'input pr-12 resize-none',
              'min-h-[52px] max-h-[200px]',
              disabled && 'opacity-50'
            )}
            rows={1}
            spellCheck={false}
          />
          <div className="absolute bottom-2 right-2 flex items-center gap-1">
            {!streaming ? (
              <button
                type="submit"
                disabled={!value.trim() || disabled}
                className="btn-primary p-2 rounded-full disabled:opacity-50"
                aria-label="Send message"
              >
                <Send className="w-5 h-5" />
              </button>
            ) : (
              <button
                type="button"
                onClick={onStop}
                className="btn-danger p-2 rounded-full"
                aria-label="Stop generation"
              >
                <X className="w-5 h-5" />
              </button>
            )}
          </div>
        </div>
      </div>
    </form>
  )
}