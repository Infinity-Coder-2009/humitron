import React from 'react'
import { cn } from '../../utils/cn'
import { Brain } from 'lucide-react'

interface ThinkingPanelProps {
  thinking: string
}

export function ThinkingPanel({ thinking }: ThinkingPanelProps) {
  const [expanded, setExpanded] = React.useState(false)

  return (
    <details className="thinking-panel group">
      <summary className="flex items-center gap-2 cursor-pointer list-none">
        <Brain className="w-4 h-4 text-primary-400" />
        <span className="font-medium text-primary-300">Reasoning</span>
        <span className="text-xs text-gray-500">({thinking.length} chars)</span>
        <span className="ml-auto text-gray-400">
          {expanded ? '▲' : '▼'}
        </span>
      </summary>
      <div className={cn('mt-2 p-3 bg-dark-bg rounded-lg font-mono text-sm text-gray-300 whitespace-pre-wrap', expanded ? 'block' : 'hidden')}>
        {thinking}
      </div>
    </details>
  )
}