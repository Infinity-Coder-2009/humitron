import { useState, useRef, useEffect } from 'react'
import { cn } from '../../utils/cn'
import { Send, Mic, MicOff, Paperclip, X } from 'lucide-react'

interface ChatInputProps {
  onSend: (text: string) => void
  streaming: boolean
  onStop: () => void
  disabled?: boolean
}

export function ChatInput({ onSend, streaming, onStop, disabled }: ChatInputProps) {
  const [text, setText] = useState('')
  const [isRecording, setIsRecording] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    textareaRef.current?.focus()
  }, [])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (text.trim() && !streaming) {
      onSend(text.trim())
      setText('')
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (text.trim() && !streaming) {
        onSend(text.trim())
        setText('')
      }
    }
  }

  const adjustHeight = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const textarea = e.target
    textarea.style.height = 'auto'
    textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px'
  }

  if (streaming) {
    return (
      <form onSubmit={handleSubmit} className="border-t border-dark-border p-4">
        <div className="flex items-end gap-3">
          <div className="flex-1">
            <div className="bg-dark-elevated rounded-lg p-3 text-gray-500 text-sm animate-pulse">
              AI is responding...
            </div>
          </div>
          <button
            type="button"
            onClick={onStop}
            className="btn-secondary flex items-center gap-2"
            disabled={disabled}
          >
            <X className="w-4 h-4" />
            Stop
          </button>
        </div>
      </form>
    )
  }

  return (
    <form onSubmit={handleSubmit} className="border-t border-dark-border p-4">
      <div className="flex items-end gap-3">
        <div className="relative flex-1">
          <textarea
            ref={textareaRef}
            value={text}
            onChange={e => {
              setText(e.target.value)
              adjustHeight(e)
            }}
            onKeyDown={handleKeyDown}
            placeholder="Type a message... (Shift+Enter for new line)"
            className="input resize-none min-h-[44px] max-h-[200px] pr-12"
            disabled={disabled}
            rows={1}
          />
          <div className="absolute bottom-2 right-2 flex items-center gap-1">
            <button
              type="button"
              onClick={() => setIsRecording(!isRecording)}
              className={cn(
                'p-2 rounded-lg transition-colors',
                isRecording ? 'bg-red-500/20 text-red-500' : 'text-gray-500 hover:text-white'
              )}
              aria-label={isRecording ? 'Stop recording' : 'Start recording'}
            >
              {isRecording ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
            </button>
            <button
              type="button"
              className="p-2 text-gray-500 hover:text-white transition-colors"
              aria-label="Attach file"
            >
              <Paperclip className="w-5 h-5" />
            </button>
          </div>
        </div>
        <button
          type="submit"
          disabled={!text.trim() || disabled}
          className={cn(
            'btn-primary flex items-center justify-center gap-2 h-[44px] px-4 transition-all',
            !text.trim() && 'opacity-50 cursor-not-allowed'
          )}
          aria-label="Send message"
        >
          <Send className="w-5 h-5" />
        </button>
      </div>
    </form>
  )
}