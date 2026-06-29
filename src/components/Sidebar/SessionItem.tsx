import React from 'react'
import { Session } from '../../types'
import { cn } from '../../utils/cn'
import { MoreVertical, Edit, Trash2 } from 'lucide-react'
import { formatRelativeTime } from '../../utils/helpers'

interface SessionItemProps {
  session: Session;
  isActive: boolean;
  onClick: () => void;
  onRename: () => void;
  onDelete: () => void;
}

export function SessionItem({ session, isActive, onClick, onRename, onDelete }: SessionItemProps) {
  const [showMenu, setShowMenu] = React.useState(false)

  return (
    <div className="relative group">
      <button
        onClick={onClick}
        className={cn(
          'sidebar-item w-full justify-start text-left',
          isActive && 'sidebar-item-active'
        )}
      >
        <div className="flex-1 min-w-0 flex items-center gap-2">
          <div className={cn(
            'w-2 h-2 rounded-full flex-shrink-0',
            isActive ? 'bg-primary-400' : 'bg-gray-600'
          )} />
          <div className="min-w-0 flex-1 flex flex-col">
            <span className="text-sm font-medium truncate">{session.name}</span>
            <span className="text-xs text-gray-500 truncate">
              {session.messages.length} messages • {formatRelativeTime(session.updatedAt)}
            </span>
          </div>
        </div>
        <button
          onClick={(e) => { e.stopPropagation(); setShowMenu(!showMenu) }}
          className="opacity-0 group-hover:opacity-100 p-1 text-gray-500 hover:text-white transition-opacity"
          aria-label="Session options"
        >
          <MoreVertical className="w-4 h-4" />
        </button>
      </button>

      {showMenu && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setShowMenu(false)} />
          <div className="absolute right-2 top-full z-20 card min-w-[160px] shadow-lg animate-slide-down">
            <button onClick={(e) => { e.stopPropagation(); onRename(); setShowMenu(false) }} className="flex items-center gap-2 w-full px-3 py-2 text-left text-sm hover:bg-dark-elevated rounded">
              <Edit className="w-4 h-4" />
              Rename
            </button>
            <button onClick={(e) => { e.stopPropagation(); onDelete(); setShowMenu(false) }} className="flex items-center gap-2 w-full px-3 py-2 text-left text-sm text-red-400 hover:bg-dark-elevated rounded">
              <Trash2 className="w-4 h-4" />
              Delete
            </button>
          </div>
        </>
      )}
    </div>
  )
}