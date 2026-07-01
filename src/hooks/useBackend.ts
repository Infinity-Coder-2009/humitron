import { useState, useEffect, useCallback } from 'react'
import { apiClient } from '../api/client'
import { HealthStatus } from '../types'

export function useBackend() {
  const [health, setHealth] = useState<HealthStatus>({
    ollamaRunning: false,
    models: [],
    backendRunning: false,
  })
  const [loading, setLoading] = useState(false)

  const checkHealth = useCallback(async () => {
    try {
      const result = await apiClient.healthCheck()
      setHealth(result)
    } catch (error) {
      setHealth({
        ollamaRunning: false,
        models: [],
        backendRunning: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      })
    }
  }, [])

  const pullModel = useCallback(async (name: string) => {
    setLoading(true)
    try {
      await apiClient.pullModel(name)
      await checkHealth()
    } finally {
      setLoading(false)
    }
  }, [checkHealth])

  useEffect(() => {
    checkHealth()
    const interval = setInterval(checkHealth, 30000)
    return () => clearInterval(interval)
  }, [checkHealth])

  return { health, loading, checkHealth, pullModel }
}