import { useState, useRef, useEffect } from 'react'
import { X, CheckIcon } from 'lucide-react'
import { cn } from '../../utils/cn'

interface NewSessionDialogProps {
  onClose: () => void
  onCreate: (name: string) => void
}

export function NewSessionDialog({ onClose, onCreate }: NewSessionDialogProps) {
  const [name, setName] = useState('')
  const nameRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    nameRef.current?.focus()
  }, [])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (name.trim()) {
      onCreate(name.trim())
    }
  }

  return (
    <>
      <div className="fixed inset-0 bg-black/50 z-40" onClick={onClose} />
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="card w-full max-w-md animate-slide-up">
          <div className="flex items-center justify-between mb-6 pb-4 border-b border-dark-border">
            <h3 className="font-semibold">New Session</h3>
            <button onClick={onClose} className="btn-ghost p-1">
              <X className="w-5 h-5" />
            </button>
          </div>

          <form onSubmit={handleSubmit}>
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-300 mb-2">Session Name</label>
              <input
                ref={nameRef}
                type="text"
                value={name}
                onChange={e => setName(e.target.value)}
                className="input"
                placeholder="My new session"
                autoFocus
              />
            </div>
            <div className="flex justify-end gap-2">
              <button type="button" onClick={onClose} className="btn-secondary">Cancel</button>
              <button type="submit" className="btn-primary" disabled={!name.trim()}>
                <CheckIcon className="w-4 h-4" />
                Create Session
              </button>
            </div>
          </form>
        </div>
      </div>
    </>
  )
}