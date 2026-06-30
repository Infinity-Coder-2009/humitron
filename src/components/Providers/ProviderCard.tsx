import { useState } from 'react'
import { AIProvider } from '../../types/providers'
import { cn } from '../../utils/cn'
import { ProviderIcon, KeyIcon, GlobeIcon, ModelIcon, AlertIcon, CheckIcon, DeleteIcon, TestIcon, ToggleIcon } from '../Icons/ProviderIcons'

interface ProviderCardProps {
  provider: AIProvider
  index: number
  isEditing: boolean
  onUpdate: (id: string, updates: Partial<AIProvider>) => void
  onTest: (id: string) => Promise<void>
  onDelete: (id: string) => void
  onToggleEdit: (id: string) => void
}

export function ProviderCard({ provider, index, isEditing, onUpdate, onTest, onDelete, onToggleEdit }: ProviderCardProps) {
  const [testing, setTesting] = useState(false)
  const [showKey, setShowKey] = useState(false)

  const handleTest = async () => {
    setTesting(true)
    await onTest(provider.id)
    setTesting(false)
  }

  if (isEditing) {
    return (
      <div className="card animate-slide-up">
        <div className="flex items-center gap-3 mb-4">
          <ProviderIcon type={provider.type} className="w-6 h-6 text-primary-500" />
          <input
            type="text"
            value={provider.name}
            onChange={e => onUpdate(provider.id, { name: e.target.value })}
            className="input flex-1 max-w-xs"
            placeholder="Provider name"
          />
          <select
            value={provider.type}
            onChange={e => onUpdate(provider.id, { type: e.target.value as AIProvider['type'] })}
            className="input w-auto"
          >
            <option value="openai">OpenAI</option>
            <option value="anthropic">Claude</option>
            <option value="gemini">Gemini</option>
            <option value="openrouter">OpenRouter</option>
            <option value="ollama">Ollama</option>
            <option value="custom">Custom</option>
          </select>
          <div className="flex-1" />
          <button onClick={() => onToggleEdit(provider.id)} className="btn-ghost p-2">
            <CheckIcon className="w-5 h-5 text-green-500" />
          </button>
          <button onClick={() => onDelete(provider.id)} className="btn-ghost p-2 text-red-400 hover:text-red-300">
            <DeleteIcon className="w-5 h-5" />
          </button>
        </div>

        <div className="space-y-3">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-gray-500 mb-1 flex items-center gap-1">
                <GlobeIcon className="w-3 h-3" /> Base URL
              </label>
              <input
                type="url"
                value={provider.baseUrl}
                onChange={e => onUpdate(provider.id, { baseUrl: e.target.value })}
                className="input"
                placeholder="https://api.example.com/v1"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1 flex items-center gap-1">
                <ModelIcon className="w-3 h-3" /> Model ID
              </label>
              <input
                type="text"
                value={provider.modelId}
                onChange={e => onUpdate(provider.id, { modelId: e.target.value })}
                className="input"
                placeholder="gpt-4o-mini"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs text-gray-500 mb-1 flex items-center gap-1">
              <KeyIcon className="w-3 h-3" /> API Key
            </label>
            <div className="relative">
              <input
                type={showKey ? 'text' : 'password'}
                value={provider.apiKey}
                onChange={e => onUpdate(provider.id, { apiKey: e.target.value })}
                className="input pr-12"
                placeholder={provider.type === 'ollama' ? 'Not required for Ollama' : 'sk-...'}
                disabled={provider.type === 'ollama'}
              />
              {provider.type !== 'ollama' && (
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
              {provider.type === 'ollama' ? 'Ollama runs locally without an API key' : 'Your API key is stored locally and never shared'}
            </p>
          </div>

          <div className="flex items-center gap-4 pt-2 border-t border-dark-border">
            <label className="flex items-center gap-2 cursor-pointer">
              <ToggleIcon on={provider.enabled} className="w-10 h-6" />
              <span className="text-sm">Enabled</span>
            </label>
            <span className="text-xs text-gray-500">Providers must be enabled to be used</span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleTest}
              disabled={testing || !provider.apiKey || provider.type === 'ollama'}
              className={cn(
                'btn-primary flex items-center gap-2 text-sm',
                testing && 'opacity-50 cursor-not-allowed',
                (!provider.apiKey || provider.type === 'ollama') && 'opacity-30 cursor-not-allowed'
              )}
            >
              <TestIcon className={cn('w-4 h-4', testing && 'animate-spin')} />
              {testing ? 'Testing...' : 'Test Connection'}
            </button>

            {provider.testStatus === 'success' && (
              <span className="flex items-center gap-1 text-green-500 text-sm">
                <CheckIcon className="w-4 h-4" />
                Connected
              </span>
            )}

            {provider.testStatus === 'error' && (
              <span className="flex items-center gap-1 text-red-500 text-sm">
                <AlertIcon className="w-4 h-4" />
                {provider.testMessage}
              </span>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="card animate-slide-up">
      <div className="flex items-center gap-3 mb-3">
        <ProviderIcon type={provider.type} className="w-8 h-8 text-primary-500" />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium text-gray-100 truncate">{provider.name}</span>
            <span className="text-xs px-2 py-0.5 bg-dark-bg rounded text-gray-400 font-mono">{provider.type.toUpperCase()}</span>
          </div>
          <div className="text-xs text-gray-500 flex items-center gap-2">
            <GlobeIcon className="w-3 h-3" />
            <span className="truncate font-mono">{provider.baseUrl}</span>
            <ModelIcon className="w-3 h-3" />
            <span className="font-mono">{provider.modelId}</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {provider.testStatus === 'success' && (
            <span className="flex items-center gap-1 text-green-500 text-xs">
              <CheckIcon className="w-3 h-3" /> Connected
            </span>
          )}
          {provider.testStatus === 'error' && (
            <span className="flex items-center gap-1 text-red-500 text-xs">
              <AlertIcon className="w-3 h-3" /> Error
            </span>
          )}
          <button
            onClick={() => onToggleEdit(provider.id)}
            className="btn-ghost p-1.5"
            aria-label="Edit provider"
          >
            <TestIcon className="w-4 h-4" />
          </button>
          <button
            onClick={() => onDelete(provider.id)}
            className="btn-ghost p-1.5 text-red-400 hover:text-red-300"
            aria-label="Delete provider"
          >
            <DeleteIcon className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="pt-3 border-t border-dark-border flex items-center justify-between">
        <label className="flex items-center gap-2 cursor-pointer">
          <ToggleIcon on={provider.enabled} className="w-10 h-6" />
          <span className="text-sm">Enabled</span>
        </label>
        <button
          onClick={handleTest}
          disabled={testing || !provider.apiKey || provider.type === 'ollama'}
          className={cn(
            'btn-primary flex items-center gap-2 text-sm',
            testing && 'opacity-50',
            (!provider.apiKey || provider.type === 'ollama') && 'opacity-30'
          )}
        >
          <TestIcon className={cn('w-4 h-4', testing && 'animate-spin')} />
          {testing ? 'Testing...' : 'Test Connection'}
        </button>
      </div>
    </div>
  );
}