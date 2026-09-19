import { cn } from '@/lib/utils'

export function PriorityBadge({ level = 'medium' }: { level?: 'high' | 'medium' | 'low' }) {
  const styles = { high: 'border-danger/60 bg-danger/15 text-[#ff8277]', medium: 'border-primary/60 bg-primary/10 text-gold-bright', low: 'border-secondary/60 bg-secondary/15 text-accent' }
  return <span className={cn('inline-flex border px-2 py-1 font-mono text-[10px] font-semibold uppercase tracking-widest', styles[level])}>Priorité {level === 'high' ? 'haute' : level === 'medium' ? 'moyenne' : 'basse'}</span>
}
