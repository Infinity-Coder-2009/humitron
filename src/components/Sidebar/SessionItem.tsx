import { cn } from '../../utils/cn'
import { Session } from '../../types'
import { MoreVertical, Edit, Trash2, X } from 'lucide-react'
import { useState, useRef, useEffect } from 'react'
import { formatRelativeTime } from '../../utils/helpers'

interface SessionItemProps {
  session: Session
  isActive: boolean
  onClick: () => void
  onRename: () => void
  onDelete: () => void
}

export function SessionItem({ session, isActive, onClick, onRename, onDelete }: SessionItemProps) {
  const [showMenu, setShowMenu] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setShowMenu(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  return (
    <div className="relative">
      <button
        onClick={onClick}
        className={cn(
          'sidebar-item w-full justify-start text-left',
          isActive && 'sidebar-item-active'
        )}
      >
        <div className="flex-1 min-w-0 flex flex-col">
          <span className="text-sm font-medium truncate">{session.name}</span>
          <span className="text-xs text-gray-500 truncate">
            {session.messages.length} messages • {formatRelativeTime(session.updatedAt)}
          </span>
        </div>
        <div className="relative">
          <button
            onClick={(e) => { e.stopPropagation(); setShowMenu(!showMenu) }}
            className="p-1.5 rounded hover:bg-dark-elevated text-gray-500 hover:text-white"
            aria-label="More options"
          >
            <MoreVertical className="w-4 h-4" />
          </button>
          {showMenu && (
  <>
    <div className="relative inset-0 z-10" onClick={() => setShowMenu(false)} />
    <div className="absolute right-2 top-full z-20 card min-w-[160px] shadow-lg animate-slide-down">
      <button onClick={(e) => { e.stopPropagation(); onRename(); setShowMenu(false) }} className="flex items-center gap-2 w-full px-3 py-2 text-left text-sm hover:bg-dark-elevated rounded">
        <Edit className="w-4 h-4" />
        Rename
      </button>
      {/* other buttons... */}
    </div>
  </>
)}
        </div>
      </div>
    </div>
  )
}
