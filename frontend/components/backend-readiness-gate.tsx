'use client'

import { AlertTriangle, LoaderCircle, RefreshCw } from 'lucide-react'
import { useBackendReadiness } from '@/hooks/useBackendReadiness'

export function BackendReadinessGate({ children }: { children: React.ReactNode }) {
  const state = useBackendReadiness()

  if (state.isChecking) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background p-6">
        <div className="glass w-full max-w-md rounded-2xl p-6 text-center">
          <LoaderCircle className="mx-auto mb-3 h-7 w-7 animate-spin text-primary" />
          <h1 className="font-semibold">Connexion au guide</h1>
          <p className="mt-2 text-sm text-muted">Vérification du backend, de l’agent et du RAG…</p>
        </div>
      </div>
    )
  }

  return (
    <>
      {!state.isReady && (
        <div className="border-b border-danger/40 bg-danger/10 px-4 py-3">
          <div className="mx-auto flex max-w-7xl items-center justify-between gap-4">
            <div className="flex items-center gap-2 text-sm">
              <AlertTriangle className="h-4 w-4 text-danger" />
              <span>{state.error || 'Service dégradé'}</span>
              <span className="text-muted">Agent: {state.agentReady ? 'en ligne' : 'hors ligne'} · RAG: {state.ragReady ? 'en ligne' : 'hors ligne'}</span>
            </div>
            <button onClick={state.retry} className="flex items-center gap-2 rounded-lg border border-border px-3 py-1.5 text-xs">
              <RefreshCw className="h-3.5 w-3.5" /> Réessayer
            </button>
          </div>
        </div>
      )}
      {children}
    </>
  )
}
