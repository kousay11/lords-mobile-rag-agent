'use client'

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Archive, BookOpen, Menu, ScrollText, Sparkles, X } from 'lucide-react'
import { toast } from 'sonner'
import { AdvisorMessage } from '@/components/advisor/advisor-message'
import { ChatComposer } from '@/components/advisor/chat-composer'
import { KnowledgeNavigation } from '@/components/advisor/knowledge-navigation'
import { SourcePanel } from '@/components/advisor/source-panel'
import { ThinkingState } from '@/components/advisor/thinking-state'
import { ChatMessage, ChatThread, SourceCitation, deleteThread, getApiErrorMessage, getThread, listThreads, sendChatMessage } from '@/lib/api'

const suggestions = ['Meilleurs héros pour le Colisée', 'Quelles recherches prioriser ?', 'Comment fonctionnent les boucliers ?', 'Comment augmenter ma Puissance ?', 'Comment protéger mes troupes ?', 'Stratégie de chasse aux monstres']

export default function ChatPage() {
  const [threads, setThreads] = useState<ChatThread[]>([])
  const [activeId, setActiveId] = useState<string>()
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [loadingThreads, setLoadingThreads] = useState(true)
  const [drawer, setDrawer] = useState<'knowledge' | 'sources'>()
  const bottomRef = useRef<HTMLDivElement>(null)
  const sources = useMemo<SourceCitation[]>(() => [...messages].reverse().find((message) => message.role === 'assistant')?.sources || [], [messages])

  const refreshThreads = useCallback(async () => { try { setThreads(await listThreads()) } catch (error) { toast.error(getApiErrorMessage(error)) } finally { setLoadingThreads(false) } }, [])
  useEffect(() => { void refreshThreads(); const pending = localStorage.getItem('lords_mobile_pending_prompt'); if (pending) { setInput(pending); localStorage.removeItem('lords_mobile_pending_prompt') } }, [refreshThreads])
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages, loading])

  const selectThread = async (id: string) => { setActiveId(id); setDrawer(undefined); try { setMessages((await getThread(id)).messages || []) } catch (error) { toast.error(getApiErrorMessage(error)) } }
  const newChat = () => { setActiveId(undefined); setMessages([]); setInput(''); setDrawer(undefined) }
  const removeThread = async (id: string) => { if (!window.confirm('Effacer cette chronique du royaume ?')) return; try { await deleteThread(id); if (activeId === id) newChat(); await refreshThreads() } catch (error) { toast.error(getApiErrorMessage(error)) } }
  const choosePrompt = (prompt: string) => { setInput(prompt); setDrawer(undefined) }

  const submit = async (event?: FormEvent) => {
    event?.preventDefault(); const text = input.trim(); if (!text || loading) return
    const optimistic: ChatMessage = { id: `local-${Date.now()}`, role: 'user', content: text, createdAt: new Date().toISOString() }
    setMessages((current) => [...current, optimistic]); setInput(''); setLoading(true)
    try {
      const result = await sendChatMessage({ message: text, threadId: activeId, searchType: 'hybrid', topK: 8 })
      setActiveId(result.threadId)
      setMessages((current) => [...current, { id: result.messageId, role: 'assistant', content: result.response, confidence: result.confidence, sources: result.sources || [], intent: result.intent, gameVersion: result.gameVersion, generationMode: result.generationMode, createdAt: new Date().toISOString() }])
      await refreshThreads()
    } catch (error) { setMessages((current) => current.filter((message) => message.id !== optimistic.id)); setInput(text); toast.error(getApiErrorMessage(error)) }
    finally { setLoading(false) }
  }

  const navigation = <KnowledgeNavigation threads={threads} activeId={activeId} loading={loadingThreads} onPrompt={choosePrompt} onThread={(id) => void selectThread(id)} onDelete={(id) => void removeThread(id)} onNew={newChat} />
  return <div className="mx-auto grid h-full max-w-[1600px] xl:grid-cols-[250px_minmax(0,1fr)_310px]"><div className="hidden border-r border-primary/20 xl:block">{navigation}</div><main className="flex min-h-0 flex-col bg-background/45"><div className="flex h-12 shrink-0 items-center justify-between border-b border-border/35 bg-surface/35 px-4 xl:hidden"><button onClick={() => setDrawer('knowledge')} className="flex items-center gap-2 text-xs text-muted"><Menu className="h-4 w-4 text-primary" /> Archives</button><button onClick={() => setDrawer('sources')} className="flex items-center gap-2 text-xs text-muted">Sources ({sources.length}) <ScrollText className="h-4 w-4 text-accent" /></button></div><div className="scrollbar-thin flex-1 overflow-y-auto px-4 py-7 sm:px-7"><div className="mx-auto max-w-3xl">{messages.length === 0 ? <section className="flex min-h-[65vh] flex-col items-center justify-center text-center"><span className="relative mb-7 flex h-20 w-20 items-center justify-center border border-primary/60 bg-primary/[.07] text-primary shadow-gold"><BookOpen className="h-9 w-9" /><Sparkles className="absolute -right-2 -top-2 h-5 w-5 text-accent" /></span><p className="font-mono text-[9px] uppercase tracking-[.3em] text-accent">Chambre du Conseil</p><h1 className="kingdom-title mt-3 text-3xl font-bold sm:text-4xl">Quel conseil recherchez-vous,<br /><span className="text-gradient">Commandant ?</span></h1><p className="mt-5 max-w-xl text-sm leading-6 text-muted">Le Sage analyse les archives du royaume et distingue les faits documentés des recommandations stratégiques.</p><div className="mt-9 grid w-full gap-2 sm:grid-cols-2">{suggestions.map((suggestion) => <button key={suggestion} onClick={() => setInput(suggestion)} className="border border-border/50 bg-surface/55 p-3 text-left text-xs text-muted transition hover:border-primary hover:bg-primary/[.06] hover:text-text-main">{suggestion}</button>)}</div></section> : <div className="space-y-8">{messages.map((message) => <AdvisorMessage key={message.id} message={message} />)}{loading && <ThinkingState />}<div ref={bottomRef} /></div>}</div></div><ChatComposer value={input} onChange={setInput} onSubmit={submit} onReset={newChat} loading={loading} /></main><div className="hidden border-l border-primary/20 xl:block"><SourcePanel sources={sources} /></div>{drawer && <div className="fixed inset-0 z-50 bg-black/75 xl:hidden" onClick={() => setDrawer(undefined)}><div onClick={(event) => event.stopPropagation()} className={`absolute inset-y-0 w-[min(88vw,340px)] border-primary/30 bg-background shadow-2xl ${drawer === 'knowledge' ? 'left-0 border-r' : 'right-0 border-l'}`}><button onClick={() => setDrawer(undefined)} className="absolute right-3 top-3 z-10 border border-border bg-background p-2 text-muted" aria-label="Fermer"><X className="h-4 w-4" /></button>{drawer === 'knowledge' ? navigation : <SourcePanel sources={sources} />}</div></div>}</div>
}
