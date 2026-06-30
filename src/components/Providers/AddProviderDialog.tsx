import { useState, useEffect, useRef } from 'react'
import { AIProvider } from '../../types/providers'
import { cn } from '../../utils/cn'
import { X, CheckIcon, ProviderIcon, KeyIcon, GlobeIcon, ModelIcon } from '../Icons/ProviderIcons'

interface AddProviderDialogProps {
  onClose: () => void
  onAdd: (provider: Omit<AIProvider, 'id' | 'enabled' | 'lastTested' | 'testStatus' | 'testMessage'>) => void
}

const PROVIDER_TEMPLATES = {
  openai: { name: 'OpenAI', baseUrl: 'https://api.openai.com/v1', modelId: 'gpt-4o-mini', type: 'openai' as const },
  anthropic: { name: 'Claude', baseUrl: 'https://api.anthropic.com/v1', modelId: 'claude-3-haiku-20240307', type: 'anthropic' as const },
  gemini: { name: 'Gemini', baseUrl: 'https://generativelanguage.googleapis.com/v1beta', modelId: 'gemini-1.5-flash', type: 'gemini' as const },
  openrouter: { name: 'OpenRouter', baseUrl: 'https://openrouter.ai/api/v1', modelId: 'meta-llama/llama-3.1-8b-instruct', type: 'openrouter' as const },
  ollama: { name: 'Ollama', baseUrl: 'http://localhost:11434', modelId: 'llama3.2', type: 'ollama' as const },
  custom: { name: 'Custom Provider', baseUrl: 'https://api.example.com/v1', modelId: 'my-model', type: 'custom' as const },
}

export function AddProviderDialog({ onClose, onAdd }: AddProviderDialogProps) {
  const [selectedType, setSelectedType] = useState<'openai' | 'anthropic' | 'gemini' | 'openrouter' | 'ollama' | 'custom'>('openai')
  const [name, setName] = useState('')
  const [baseUrl, setBaseUrl] = useState('')
  const [modelId, setModelId] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [showKey, setShowKey] = useState(false)
  const nameRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    const template = PROVIDER_TEMPLATES[selectedType]
    setName(template.name)
    setBaseUrl(template.baseUrl)
    setModelId(template.modelId)
    setApiKey('')
    nameRef.current?.focus()
  }, [selectedType])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (name.trim() && baseUrl.trim() && modelId.trim()) {
      onAdd({
        name: name.trim(),
        baseUrl: baseUrl.trim(),
        modelId: modelId.trim(),
        apiKey: apiKey.trim(),
        type: selectedType,
      })
      onClose()
    }
  }

  return (
    <>
      <div className="fixed inset-0 bg-black/50 z-40" onClick={onClose} />
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="card w-full max-w-lg max-h-[90vh] overflow-y-auto animate-slide-up">
          <div className="flex items-center justify-between mb-6 pb-4 border-b border-dark-border">
            <h3 className="font-semibold">Add New Provider</h3>
            <button onClick={onClose} className="btn-ghost p-1">
              <X className="w-5 h-5" />
            </button>
          </div>

          <form onSubmit={handleSubmit}>
            <div className="space-y-4 mb-6">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Provider Type</label>
                <div className="grid grid-cols-3 gap-2">
                  {Object.entries(PROVIDER_TEMPLATES).map(([key, template]) => (
                    <button
                      key={key}
                      type="button"
                      onClick={() => setSelectedType(key as typeof selectedType)}
                      className={cn(
                        'p-3 rounded-lg border-2 transition-all text-left',
                        selectedType === key 
                          ? 'border-primary-500 bg-primary-500/10' 
                          : 'border-dark-border hover:border-primary-500/50'
                      )}
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <ProviderIcon type={key} className="w-5 h-5 text-primary-500" />
                        <span className="font-medium text-sm">{template.name}</span>
                      </div>
                      <span className="text-xs text-gray-500 font-mono">{template.modelId}</span>
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Provider Name</label>
                <input
                  ref={nameRef}
                  type="text"
                  value={name}
                  onChange={e => setName(e.target.value)}
                  className="input"
                  placeholder="My OpenAI"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2 flex items-center gap-1">
                  <GlobeIcon className="w-4 h-4" /> Base URL
                </label>
                <input
                  type="url"
                  value={baseUrl}
                  onChange={e => setBaseUrl(e.target.value)}
                  className="input"
                  placeholder="https://api.example.com/v1"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2 flex items-center gap-1">
                  <ModelIcon className="w-4 h-4" /> Model ID
                </label>
                <input
                  type="text"
                  value={modelId}
                  onChange={e => setModelId(e.target.value)}
                  className="input"
                  placeholder="gpt-4o-mini"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2 flex items-center gap-1">
                  <KeyIcon className="w-4 h-4" /> API Key
                </label>
                <div className="relative">
                  <input
                    type={showKey ? 'text' : 'password'}
                    value={apiKey}
                    onChange={e => setApiKey(e.target.value)}
                    className="input pr-12"
                    placeholder={selectedType === 'ollama' ? 'Not required for Ollama' : 'sk-...'}
                    disabled={selectedType === 'ollama'}
                  />
                  {selectedType !== 'ollama' && (
                    <button
                      type="button"
                      onClick={() => setShowKey(!showKey)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-white text-sm"
                    >
                      {showKey ? '🙈' : '👁️'}
                    </button>
                  )}
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  {selectedType === 'ollama' ? 'Ollama runs locally without an API key' : 'Your API key is stored locally and never shared'}
                </p>
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-4 border-t border-dark-border">
              <button type="button" onClick={onClose} className="btn-secondary">Cancel</button>
              <button type="submit" className="btn-primary" disabled={!name.trim() || !baseUrl.trim() || !modelId.trim()}>
                <CheckIcon className="w-4 h-4" />
                Add Provider
              </button>
            </div>
          </form>
        </div>
      </div>
    </>
  )
}