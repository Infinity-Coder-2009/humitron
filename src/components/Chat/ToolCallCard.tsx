import { ToolCall } from '../../types'
import { cn } from '../../utils/cn'
import { Terminal, CheckCircle, XCircle, Loader2 } from 'lucide-react'

const toolIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  read_file: () => <Terminal className="w-4 h-4" />,
  write_file: () => <Terminal className="w-4 h-4" />,
  bash_execute: () => <Terminal className="w-4 h-4" />,
  web_search: () => <Terminal className="w-4 h-4" />,
}

export function ToolCallCard({ toolCall }: { toolCall: ToolCall }) {
  const isRunning = toolCall.status === 'running'
  const isCompleted = toolCall.status === 'completed'
  const isFailed = toolCall.status === 'failed'

  const getStatusIcon = () => {
    if (isRunning) return <Loader2 className="w-4 h-4 text-primary-400 animate-spin" />
    if (isCompleted) return <CheckCircle className="w-4 h-4 text-green-500" />
    if (isFailed) return <XCircle className="w-4 h-4 text-red-500" />
    return <Loader2 className="w-4 h-4 text-gray-500" />
  }

  const getStatusText = () => {
    if (isRunning) return 'Running...'
    if (isCompleted) return 'Completed'
    if (isFailed) return 'Failed'
    return 'Pending'
  }

  return (
    <div className={cn('tool-card')}>
      <div className="flex items-start gap-3">
        <div className={cn('flex-shrink-0 w-8 h-8 rounded-lg bg-primary-500/20 flex items-center justify-center')}>
          {toolIcons[toolCall.name] || <Terminal className="w-4 h-4" />}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium text-gray-100 capitalize">{toolCall.name.replace(/_/g, ' ')}</span>
            <span className="text-xs text-gray-500">{getStatusText()}</span>
            {getStatusIcon()}
          </div>
          <div className="mt-1 font-mono text-xs text-gray-400 bg-dark-bg rounded p-2 max-h-32 overflow-auto">
            {JSON.stringify(toolCall.arguments, null, 2)}
          </div>
          
          {toolCall.result && (
            <details className="mt-2 group">
              <summary className="flex items-center gap-2 cursor-pointer list-none text-xs text-gray-500 hover:text-gray-300">
                <span>Output</span>
                <span className="ml-auto">▼</span>
              </summary>
              <div className="mt-2 p-2 bg-dark-bg rounded font-mono text-xs text-gray-300 whitespace-pre-wrap max-h-48 overflow-auto">
                {typeof toolCall.result === 'string' ? toolCall.result : JSON.stringify(toolCall.result, null, 2)}
              </div>
            </details>
          )}
          
          {toolCall.error && (
            <div className="mt-2 p-2 bg-red-500/10 border border-red-500/30 rounded text-red-400 text-xs">
              Error: {toolCall.error}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}