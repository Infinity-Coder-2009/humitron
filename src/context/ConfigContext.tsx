import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react'
import { Config } from '../types'

interface ConfigContextType {
  config: Config;
  updateConfig: (updates: Partial<Config>) => void;
  resetConfig: () => void;
}

const ConfigContext = createContext<ConfigContextType | undefined>(undefined)

const DEFAULT_CONFIG: Config = {
  model: 'llama3.2',
  temperature: 0.7,
  maxSteps: 20,
  workspace: '.',
  ollamaUrl: 'http://localhost:11434',
  theme: 'system',
  enableMcp: false,
}

export function ConfigProvider({ children }: { children: ReactNode }) {
  const [config, setConfig] = useState<Config>(() => {
    if (typeof window !== 'undefined') {
      try {
        const stored = localStorage.getItem('humitron-config')
        if (stored) {
          return { ...DEFAULT_CONFIG, ...JSON.parse(stored) }
        }
      } catch (e) {
        console.error('Failed to load config:', e)
      }
    }
    return DEFAULT_CONFIG
  })

  useEffect(() => {
    localStorage.setItem('humitron-config', JSON.stringify(config))
  }, [config])

  const updateConfig = useCallback((updates: Partial<Config>) => {
    setConfig(prev => ({ ...prev, ...updates }))
  }, [])

  const resetConfig = useCallback(() => {
    setConfig(DEFAULT_CONFIG)
  }, [])

  return (
    <ConfigContext.Provider value={{ config, updateConfig, resetConfig }}>
      {children}
    </ConfigContext.Provider>
  )
}

export function useConfig() {
  const context = useContext(ConfigContext)
  if (!context) {
    throw new Error('useConfig must be used within a ConfigProvider')
  }
  return context
}