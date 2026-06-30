import React from 'react'
import { useSessions } from '../../context/SessionContext'
import { useConfig } from '../../context/ConfigContext'
import { cn } from '../../utils/cn'
import { Plus, Sun, Moon, Monitor } from 'lucide-react'
import { formatRelativeTime } from '../../utils/helpers'
import { SessionItem } from './SessionItem'
import { NewSessionDialog } from './NewSessionDialog'

export function Sidebar() {
  const { sessions, currentSession, createSession, deleteSession, setCurrentSession, renameSession } = useSessions()
  const { config, updateConfig } = useConfig()
  const [showNewSession, setShowNewSession] = React.useState(false)
  const [editingSession, setEditingSession] = React.useState<string | null>(null)
  const [editName, setEditName] = React.useState('')

  const handleThemeToggle = () => {
    const themes: ('dark' | 'light' | 'system')[] = ['dark', 'light', 'system']
    const currentIndex = themes.indexOf(config.theme)
    const nextTheme = themes[(currentIndex + 1) % themes.length]
    updateConfig({ theme: nextTheme })
  }

  const getThemeIcon = () => {
    switch (config.theme) {
      case 'dark': return <Moon className="w-5 h-5" />
      case 'light': return <Sun className="w-5 h-5" />
      default: return <Monitor className="w-5 h-5" />
    }
  }

  return (
    <div className="w-flex flex flex-col h-full bg-dark-surface border-r border-dark-border">
      <div className="p-4 border-b border-dark-border">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-primary-500 flex items-center justify-center">
            <span className="text-white font-bold text-lg">H</span>
          </div>
          <span className="font-semibold text-lg">Humitron</span>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-2">
        <div className="flex items-center justify-between mb-2 px-2">
          <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wider">Sessions</h3>
          <button
            onClick={() => setShowNewSession(true)}
            className="btn-ghost p-1.5 text-xs"
            aria-label="New session"
          >
            <Plus className="w-4 h-4" />
          </button>
        </div>

        {sessions.length === 0 ? (
          <div className="text-center py-8 text-gray-500 text-sm">
            No sessions yet. Create one to get started!
          </div>
        ) : (
          <div className="space-y-1">
            {sessions.map(session => (
              <SessionItem
                key={session.id}
                session={session}
                isActive={currentSession?.id === session.id}
                onClick={() => setCurrentSession(session.id)}
                onRename={() => {
                  setEditingSession(session.id)
                  setEditName(session.name)
                }}
                onDelete={() => deleteSession(session.id)}
              />
            ))}
          </div>
        )}
      </div>

      <div className="p-4 border-t border-dark-border space-y-2">
        <button
          onClick={handleThemeToggle}
          className="sidebar-item w-full justify-start"
          aria-label={`Switch to ${config.theme === 'dark' ? 'light' : config.theme === 'light' ? 'system' : 'dark'} mode`}
        >
          {getThemeIcon()}
          <span>Theme: {config.theme.charAt(0).toUpperCase() + config.theme.slice(1)}</span>
        </button>

        <button
          onClick={() => setShowNewSession(true)}
          className="sidebar-item w-full justify-start"
        >
          <Plus className="w-5 h-5" />
          <span>New Session</span>
        </button>

        <button
          className="sidebar-item w-full justify-start"
        >
          <span>Settings</span>
        </button>
      </div>

      {showNewSession && (
        <NewSessionDialog
          onClose={() => setShowNewSession(false)}
          onCreate={(name) => {
            createSession(name)
            setShowNewSession(false)
          }}
        />
      )}

      {editingSession && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="card w-full max-w-md">
            <h3 className="font-semibold mb-4">Rename Session</h3>
            <input
              value={editName}
              onChange={e => setEditName(e.target.value)}
              className="input mb-4"
              autoFocus
            />
            <div className="flex justify-end gap-2">
              <button onClick={() => { setEditingSession(null); setEditName('') }} className="btn-secondary">Cancel</button>
              <button 
                onClick={() => { renameSession(editingSession, editName); setEditingSession(null); setEditName('') }}
                className="btn-primary"
              >Save</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}