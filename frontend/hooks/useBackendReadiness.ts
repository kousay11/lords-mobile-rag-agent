import { useCallback, useEffect, useState } from 'react'
import { getBackendHealth } from '@/lib/api'

export function useBackendReadiness() {
  const [isChecking, setChecking] = useState(true)
  const [isReady, setReady] = useState(false)
  const [agentReady, setAgentReady] = useState(false)
  const [ragReady, setRagReady] = useState(false)
  const [error, setError] = useState<string>()

  const check = useCallback(async (background = false) => {
    if (!background) setChecking(true)
    setError(undefined)
    try {
      const health = await getBackendHealth()
      const agent = health.agent === 'online'
      const rag = health.rag === 'online'
      setAgentReady(agent)
      setRagReady(rag)
      setReady(health.status === 'ok' && agent && rag && health.read_only)
    } catch {
      setReady(false)
      setAgentReady(false)
      setRagReady(false)
      setError('Le backend Lords Mobile est indisponible.')
    } finally {
      if (!background) setChecking(false)
    }
  }, [])

  useEffect(() => {
    void check()
    const interval = window.setInterval(() => { void check(true) }, 10_000)
    return () => window.clearInterval(interval)
  }, [check])

  return {
    isChecking,
    isReady,
    agentReady,
    ragReady,
    error,
    retry: () => check(false),
  }
}
