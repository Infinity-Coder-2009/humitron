import { useState, useCallback } from 'react'
import { AIProvider, ProviderConfig } from '../types/providers'
import { generateId } from '../utils/helpers'

const STORAGE_KEY = 'humitron-providers'

export function useProviders() {
  const [providers, setProviders] = useState<AIProvider[]>([])
  const [activeProviderId, setActiveProviderId] = useState<string | null>(null)
  const [editingId, setEditingId] = useState<string | null>(null)

  // Load providers from localStorage on mount
  const loadProviders = useCallback(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      if (stored) {
        const parsed = JSON.parse(stored)
        setProviders(parsed.providers || [])
        setActiveProviderId(parsed.activeProviderId || null)
      } else {
        // Initialize with default providers (disabled, no API keys)
        const defaults: AIProvider[] = [
          {
            id: generateId(),
            name: 'OpenAI',
            baseUrl: 'https://api.openai.com/v1',
            apiKey: '',
            modelId: 'gpt-4o-mini',
            enabled: false,
          },
          {
            id: generateId(),
            name: 'Claude',
            baseUrl: 'https://api.anthropic.com/v1',
            apiKey: '',
            modelId: 'claude-3-haiku-20240307',
            enabled: false,
          },
          {
            id: generateId(),
            name: 'Gemini',
            baseUrl: 'https://generativelanguage.googleapis.com/v1beta',
            apiKey: '',
            modelId: 'gemini-1.5-flash',
            enabled: false,
          },
          {
            id: generateId(),
            name: 'OpenRouter',
            baseUrl: 'https://openrouter.ai/api/v1',
            apiKey: '',
            modelId: 'meta-llama/llama-3.1-8b-instruct',
            enabled: false,
          },
          {
            id: generateId(),
            name: 'Ollama (Local)',
            baseUrl: 'http://localhost:11434',
            apiKey: '',
            modelId: 'llama3.2',
            enabled: false,
          },
        ]
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

  // Get active provider
  const getActiveProvider = useCallback(() => {
    if (!activeProviderId) return null
    return providers.find(p => p.id === activeProviderId) || null
  }, [activeProviderId, providers])

  return {
    providers,
    activeProviderId,
    setActiveProviderId,
    updateProvider,
    testConnection,
    deleteProvider,
    toggleEdit,
    addProvider,
    getActiveProvider,
    editingId,
    setEditingId,
  }
}