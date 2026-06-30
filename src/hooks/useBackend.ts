import { useState, useEffect, useCallback } from 'react'
import { apiClient } from '../api/client'
import { HealthStatus } from '../types'
import type { OllamaModel } from '../types'

export function useBackend() {
  const [health, setHealth] = useState<HealthStatus>({
    ollamaRunning: false,
    models: [],
    backendRunning: false,
  })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const checkHealth = useCallback(async () => {
    try {
      const status = await apiClient.healthCheck()
      setHealth(status)
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Health check failed')
      setHealth({
        ollamaRunning: false,
        models: [],
        backendRunning: false,
        error: e instanceof Error ? e.message : 'Unknown error',
      })
    } finally {
      setLoading(false)
    }
  }, [])

  const pullModel = useCallback(async (model: string): Promise<boolean> => {
    try {
      await apiClient.pullModel(model)
      await checkHealth()
      return true
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to pull model')
      return false
    }
  }, [checkHealth])

  useEffect(() => {
    checkHealth()
    const interval = setInterval(checkHealth, 30000)
    return () => clearInterval(interval)
  }, [checkHealth])

  return { health, loading, error, checkHealth, pullModel }
}