import { useState, useEffect, useCallback } from 'react'
import { useConfig } from '../../context/ConfigContext'
import { useBackend } from '../../hooks/useBackend'
import { AIProvider, DEFAULT_PROVIDERS, ProviderConfig } from '../../types/providers'
import { cn } from '../../utils/cn'
import { SearchIcon, ProviderIcon, KeyIcon, GlobeIcon, ModelIcon, AlertIcon, CheckIcon } from '../Icons/ProviderIcons'
import { generateId } from '../../utils/helpers'
import { ProviderCard } from './ProviderCard'
import { AddProviderDialog } from './AddProviderDialog'

const STORAGE_KEY = 'humitron-providers'

export function ProvidersPage() {
  const { config, updateConfig } = useConfig()
  const { health } = useBackend()
  const [providers, setProviders] = useState<AIProvider[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [editingId, setEditingId] = useState<string | null>(null)
  const [showAddDialog, setShowAddDialog] = useState(false)
  const [activeProviderId, setActiveProviderId] = useState<string | null>(null)

  // Load providers from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      if (stored) {
        const parsed = JSON.parse(stored)
        setProviders(parsed.providers || [])
        setActiveProviderId(parsed.activeProviderId || null)
      } else {
        // Initialize with default providers (disabled, no API keys)
        const defaults: AIProvider[] = DEFAULT_PROVIDERS.map((p) => ({
          ...p,
          id: generateId(),
          enabled: false,
          apiKey: '',
        }))
        setProviders(defaults)
      }
    } catch (e) {
      console.error('Failed to load providers:', e)
    }
  }, [])

  // Save providers to localStorage
  const saveProviders = useCallback((newProviders: AIProvider[], newActiveId?: string | null) => {
    const config: ProviderConfig = {
      providers: newProviders,
      activeProviderId: newActiveId ?? activeProviderId,
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(config))
    setProviders(newProviders)
    if (newActiveId !== undefined) setActiveProviderId(newActiveId)
  }, [activeProviderId])

  // Update a provider
  const updateProvider = useCallback((id: string, updates: Partial<AIProvider>) => {
    setProviders(prev => {
      const updated = prev.map(p => p.id === id ? { ...p, ...updates } : p)
      saveProviders(updated)
      return updated
    })
  }, [saveProviders])

  // Test connection
  const testConnection = useCallback(async (id: string) => {
    const provider = providers.find(p => p.id === id)
    if (!provider) return

    updateProvider(id, { testStatus: 'pending', testMessage: '' })

    try {
      let success = false
      let message = ''

      if (provider.type === 'ollama') {
        const resp = await fetch(`${provider.baseUrl}/api/tags`)
        if (resp.ok) {
          const data = await resp.json()
          const modelExists = data.models?.some((m: any) => m.name.includes(provider.modelId))
          success = true
          message = modelExists 
            ? `Connected! Model "${provider.modelId}" available`
            : `Connected! Model "${provider.modelId}" not found locally`
        }
      } else if (provider.type === 'openai' || provider.type === 'openrouter' || provider.type === 'custom') {
        const headers: Record<string, string> = {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${provider.apiKey}`,
        }
        if (provider.type === 'openrouter') {
          headers['HTTP-Referer'] = 'https://humitron.app'
          headers['X-Title'] = 'Humitron'
        }

        const resp = await fetch(`${provider.baseUrl}/models`, { headers })
        if (resp.ok) {
          success = true
          message = 'Connection successful!'
        } else {
          const err = await resp.json().catch(() => ({}))
          message = err.error?.message || `HTTP ${resp.status}`
        }
      } else if (provider.type === 'anthropic') {
        const resp = await fetch(`${provider.baseUrl}/messages`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'x-api-key': provider.apiKey,
            'anthropic-version': '2023-06-01',
          },
          body: JSON.stringify({
            model: provider.modelId,
            max_tokens: 10,
            messages: [{ role: 'user', content: 'Hi' }],
          }),
        })
        if (resp.ok) {
          success = true
          message = 'Connection successful!'
        } else {
          const err = await resp.json().catch(() => ({}))
          message = err.error?.message || `HTTP ${resp.status}`
        }
      } else if (provider.type === 'gemini') {
        const resp = await fetch(`${provider.baseUrl}/models/${provider.modelId}?key=${provider.apiKey}`)
        if (resp.ok) {
          success = true
          message = 'Connection successful!'
        } else {
          const err = await resp.json().catch(() => ({}))
          message = err.error?.message || `HTTP ${resp.status}`
        }
      }

      updateProvider(id, { 
        testStatus: success ? 'success' : 'error', 
        testMessage: message,
        lastTested: new Date().toISOString(),
      })
    } catch (error) {
      updateProvider(id, { 
        testStatus: 'error', 
        testMessage: error instanceof Error ? error.message : 'Connection failed',
        lastTested: new Date().toISOString(),
      })
    }
  }, [providers, updateProvider])

  // Delete provider
  const deleteProvider = useCallback((id: string) => {
    setProviders(prev => {
      const filtered = prev.filter(p => p.id !== id)
      const newActiveId = activeProviderId === id ? (filtered[0]?.id || null) : activeProviderId
      saveProviders(filtered, newActiveId)
      return filtered
    })
  }, [activeProviderId, saveProviders])

  // Toggle edit mode
  const toggleEdit = useCallback((id: string) => {
    setEditingId(prev => prev === id ? null : id)
  }, [])

  // Add new provider
  const addProvider = useCallback((provider: Omit<AIProvider, 'id' | 'enabled' | 'lastTested' | 'testStatus' | 'testMessage'>) => {
    const newProvider: AIProvider = {
      ...provider,
      id: generateId(),
      enabled: true,
    }
    setProviders(prev => {
      const updated = [...prev, newProvider]
      saveProviders(updated, newProvider.id)
      return updated
    })
  }, [saveProviders])

  // Filter providers
  const filteredProviders = providers.filter(p => 
    p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    p.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
    p.type.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const enabledCount = providers.filter(p => p.enabled).length
  const configuredCount = providers.filter(p => p.apiKey || p.type === 'ollama').length

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden">
      <div className="p-6 border-b border-dark-border">
        <div className="max-w-4xl mx-auto space-y-6">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-3">
              <ProviderIcon type="custom" className="w-7 h-7 text-primary-500" />
              AI Providers
            </h1>
            <p className="text-gray-400 mt-1">
              Add your API keys to use cloud models. Your keys are stored locally and never sent anywhere else.
            </p>
          </div>

          {/* Status Bar */}
          <div className="flex items-center gap-4 flex-wrap text-sm">
            <span className="flex items-center gap-1 px-3 py-1 bg-dark-elevated rounded-lg">
              <span className="w-2 h-2 rounded-full bg-green-500" />
              {enabledCount} enabled
            </span>
            <span className="flex items-center gap-1 px-3 py-1 bg-dark-elevated rounded-lg">
              <KeyIcon className="w-3 h-3" />
              {configuredCount} configured
            </span>
            <span className="flex items-center gap-1 px-3 py-1 bg-dark-elevated rounded-lg">
              <ProviderIcon type="custom" className="w-3 h-3" />
              {providers.length} total
            </span>
            {activeProviderId && (
              <span className="flex items-center gap-1 px-3 py-1 bg-primary-500/20 text-primary-400 rounded-lg">
                <CheckIcon className="w-3 h-3" />
                Active: {providers.find(p => p.id === activeProviderId)?.name || activeProviderId}
              </span>
            )}
          </div>

          {/* Search */}
          <div className="relative max-w-md">
            <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
            <input
              type="text"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              placeholder="Search providers..."
              className="input pl-10"
            />
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-4xl mx-auto">
          {filteredProviders.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              {searchQuery ? 'No providers match your search' : 'No providers configured yet'}
              <button 
                onClick={() => setShowAddDialog(true)}
                className="btn-primary mt-4"
              >
                Add Your First Provider
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              {filteredProviders.map((provider, index) => (
                <ProviderCard
                  key={provider.id}
                  provider={provider}
                  index={index}
                  isEditing={editingId === provider.id}
                  onUpdate={updateProvider}
                  onTest={testConnection}
                  onDelete={deleteProvider}
                  onToggleEdit={toggleEdit}
                />
              ))}

              {/* Add New Provider Button */}
              <button
                onClick={() => setShowAddDialog(true)}
                className="w-full btn-secondary py-4 flex items-center justify-center gap-2 border-2 border-dashed border-dark-border hover:border-primary-500 transition-colors"
              >
                <span className="w-8 h-8 rounded-full border-2 border-dashed border-dark-border flex items-center justify-center">
                  <svg className="w-5 h-5 text-gray-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <line x1="12" y1="5" x2="12" y2="19"/>
                    <line x1="5" y1="12" x2="19" y2="12"/>
                  </svg>
                </span>
                <span>+ Add Provider</span>
              </button>
            </div>
          )}
        </div>
      </div>

      {showAddDialog && (
        <AddProviderDialog
          onClose={() => setShowAddDialog(false)}
          onAdd={addProvider}
        />
      )}
    </div>
  )
}