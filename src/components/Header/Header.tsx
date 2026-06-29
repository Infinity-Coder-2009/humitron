import React from 'react'
import { useConfig } from '../../context/ConfigContext'
import { useBackend } from '../../hooks/useBackend'
import { cn } from '../../utils/cn'
import { Brain, Zap, Server, Wifi, WifiOff, AlertCircle, CheckCircle } from 'lucide-react'

export function Header() {
  const { config, updateConfig } = useConfig()
  const { health, checkHealth, pullModel } = useBackend()
  const [showModelSelect, setShowModelSelect] = React.useState(false)
  const [pullingModel, setPullingModel] = React.useState<string | null>(null)

  const handleModelChange = async (model: string) => {
    updateConfig({ model })
    setShowModelSelect(false)
  }

  const handlePullModel = async (model: string) => {
    setPullingModel(model)
    await pullModel(model)
    setPullingModel(null)
  }

  return (
    <header className="h-16 bg-dark-surface border-b border-dark-border flex items-center justify-between px-4">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <Brain className="w-5 h-5 text-primary-500" />
          <span className="font-semibold text-lg">Humitron</span>
        </div>
        
        <div className="hidden md:flex items-center gap-2 px-3 py-1.5 bg-dark-elevated rounded-lg border border-dark-border">
          <select
            value={config.model}
            onChange={e => handleModelChange(e.target.value)}
            className="bg-transparent border-none text-white focus:outline-none text-sm"
          >
            <optgroup label="Local (Ollama)">
              <option value="llama3.2">Llama 3.2</option>
              <option value="mistral">Mistral</option>
              <option value="phi4">Phi-4</option>
              <option value="codellama">Code Llama</option>
            </optgroup>
            <optgroup label="Cloud">
              <option value="gpt-4">GPT-4</option>
              <option value="gpt-4-turbo">GPT-4 Turbo</option>
              <option value="claude-3-opus">Claude 3 Opus</option>
              <option value="claude-3-sonnet">Claude 3 Sonnet</option>
            </optgroup>
          </select>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <div className={cn('w-2 h-2 rounded-full', health.ollamaRunning ? 'status-online' : 'status-offline')} />
          <span className="text-sm text-gray-400">Ollama</span>
          {!health.ollamaRunning && health.models.length === 0 && (
            <button
              onClick={() => handlePullModel('llama3.2')}
              disabled={pullingModel === 'llama3.2'}
              className="btn-ghost p-1.5 text-xs"
            >
              {pullingModel === 'llama3.2' ? 'Pulling...' : 'Pull Llama 3.2'}
            </button>
          )}
        </div>

        <div className="flex items-center gap-2">
          <div className={cn('w-2 h-2 rounded-full', health.backendRunning ? 'status-online' : 'status-offline')} />
          <span className="text-sm text-gray-400">Backend</span>
        </div>

        <button
          onClick={checkHealth}
          className="btn-ghost p-2"
          aria-label="Refresh status"
        >
          <CheckCircle className="w-5 h-5" />
        </button>
      </div>
    </header>
  )
}