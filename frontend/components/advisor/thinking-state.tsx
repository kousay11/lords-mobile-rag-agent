'use client'

import { useEffect, useState } from 'react'
import { BookOpen, Search, Sparkles } from 'lucide-react'

const stages = ['Recherche dans les archives du royaume…', 'Analyse des guides pertinents…', 'Comparaison des stratégies…', 'Préparation de la recommandation…']

export function ThinkingState() {
  const [stage, setStage] = useState(0)
  useEffect(() => { const timer = window.setInterval(() => setStage((value) => Math.min(value + 1, stages.length - 1)), 1800); return () => window.clearInterval(timer) }, [])
  return <div className="game-panel mr-auto max-w-md p-4" role="status" aria-live="polite"><div className="flex items-center gap-3"><span className="relative flex h-10 w-10 items-center justify-center border border-secondary/60 bg-secondary/15 text-accent"><Search className="h-4 w-4 motion-safe:animate-pulse" /><Sparkles className="absolute -right-1 -top-1 h-3 w-3 text-primary" /></span><div><p className="font-display text-xs font-bold uppercase tracking-wider text-accent">Le Sage consulte ses archives</p><p className="mt-1 text-xs text-muted">{stages[stage]}</p></div></div><div className="mt-4 flex gap-1">{stages.map((_, index) => <i key={index} className={`h-1 flex-1 transition-colors ${index <= stage ? 'bg-primary shadow-gold' : 'bg-stone-light'}`} />)}</div><BookOpen className="absolute bottom-3 right-3 h-10 w-10 text-primary/[.04]" /></div>
}
