import { useState, useEffect, useCallback } from 'react';
import { AIProvider, ProviderConfig } from '../types/providers';
import { generateId } from '../utils/helpers';

const STORAGE_KEY = 'humitron-providers';

export function useProviders() {
  const [providers, setProviders] = useState<AIProvider[]>([]);
  const [activeProviderId, setActiveProviderId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // Load providers from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        setProviders(parsed.providers || []);
        setActiveProviderId(parsed.activeProviderId || null);
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
            type: 'openai',
          },
          {
            id: generateId(),
            name: 'Claude',
            baseUrl: 'https://api.anthropic.com/v1',
            apiKey: '',
            modelId: 'claude-3-haiku-20240307',
            enabled: false,
            type: 'anthropic',
          },
          {
            id: generateId(),
            name: 'Gemini',
            baseUrl: 'https://generativelanguage.googleapis.com/v1beta',
            apiKey: '',
            modelId: 'gemini-1.5-flash',
            enabled: false,
            type: 'gemini',
          },
          {
            id: generateId(),
            name: 'OpenRouter',
            baseUrl: 'https://openrouter.ai/api/v1',
            apiKey: '',
            modelId: 'meta-llama/llama-3.1-8b-instruct',
            enabled: false,
            type: 'openrouter',
          },
          {
            id: generateId(),
            name: 'Ollama (Local)',
            baseUrl: 'http://localhost:11434',
            apiKey: '',
            modelId: 'llama3.2',
            enabled: false,
            type: 'ollama',
          },
        ];
        setProviders(defaults);
      }
    } catch (e) {
      console.error('Failed to load providers:', e);
      // Fallback to defaults
      const defaults: AIProvider[] = [
        {
          id: generateId(),
          name: 'OpenAI',
          baseUrl: 'https://api.openai.com/v1',
          apiKey: '',
          modelId: 'gpt-4o-mini',
          enabled: false,
          type: 'openai',
        },
        {
          id: generateId(),
          name: 'Claude',
          baseUrl: 'https://api.anthropic.com/v1',
          apiKey: '',
          modelId: 'claude-3-haiku-20240307',
          enabled: false,
          type: 'anthropic',
        },
        {
          id: generateId(),
          name: 'Gemini',
          baseUrl: 'https://generativelanguage.googleapis.com/v1beta',
          apiKey: '',
          modelId: 'gemini-1.5-flash',
          enabled: false,
          type: 'gemini',
        },
        {
          id: generateId(),
          name: 'OpenRouter',
          baseUrl: 'https://openrouter.ai/api/v1',
          apiKey: '',
          modelId: 'meta-llama/llama-3.1-8b-instruct',
          enabled: false,
          type: 'openrouter',
        },
        {
          id: generateId(),
          name: 'Ollama (Local)',
          baseUrl: 'http://localhost:11434',
          apiKey: '',
          modelId: 'llama3.2',
          enabled: false,
          type: 'ollama',
        },
      ];
      setProviders(defaults);
    } finally {
      setLoading(false);
    }
  }, []);

  // Save providers to localStorage
    const saveProviders = useCallback((newProviders: AIProvider[], newActiveId?: string | null) => {
      const config: ProviderConfig = {
        providers: newProviders,
        activeProviderId: newActiveId ?? activeProviderId,
      };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(config));
      setProviders(newProviders);
      if (newActiveId !== undefined) setActiveProviderId(newActiveId);
    }, [activeProviderId]);

  const updateProvider = useCallback((id: string, updates: Partial<AIProvider>) => {
    setProviders(prev => {
      const updated = prev.map(p => p.id === id ? { ...p, ...updates } : p);
      saveProviders(updated);
      return updated;
    });
  }, [saveProviders]);

  const addProvider = useCallback((provider: Omit<AIProvider, 'id' | 'enabled' | 'lastTested' | 'testStatus' | 'testMessage'>) => {
    const newProvider: AIProvider = {
      ...provider,
      id: generateId(),
      enabled: true,
    };
    setProviders(prev => {
      const updated = [...prev, newProvider];
      saveProviders(updated, newProvider.id);
      return updated;
    });
    return newProvider;
  }, [saveProviders]);

  const deleteProvider = useCallback((id: string) => {
    setProviders(prev => {
      const filtered = prev.filter(p => p.id !== id);
      const newActiveId = activeProviderId === id ? (filtered[0]?.id || activeProviderId) : activeProviderId;
      saveProviders(filtered, newActiveId);
      return filtered;
    });
  }, [activeProviderId, saveProviders]);

  const setActiveProvider = useCallback((id: string | null) => {
    setActiveProviderId(id);
    saveProviders(providers, id);
  }, [providers, saveProviders]);

  const getActiveProvider = useCallback((): AIProvider | null => {
    return providers.find(p => p.id === activeProviderId) || null;
  }, [providers, activeProviderId]);

  const getEnabledProviders = useCallback((): AIProvider[] => {
    return providers.filter(p => p.enabled);
  }, [providers]);

  return {
    providers,
    activeProviderId,
    loading,
    updateProvider,
    addProvider,
    deleteProvider,
    setActiveProvider,
    getActiveProvider,
    getEnabledProviders,
    setProviders,
    saveProviders,
  };
}