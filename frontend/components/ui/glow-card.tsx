'use client'

import { MouseEvent, HTMLAttributes } from 'react'
import { cn } from '@/lib/utils'

export function GlowCard({ className, children, ...props }: HTMLAttributes<HTMLDivElement>) {
  const move = (event: MouseEvent<HTMLDivElement>) => {
    const rect = event.currentTarget.getBoundingClientRect()
    event.currentTarget.style.setProperty('--glow-x', `${event.clientX - rect.left}px`)
    event.currentTarget.style.setProperty('--glow-y', `${event.clientY - rect.top}px`)
  }
  return (
    <div onMouseMove={move} className={cn('group relative overflow-hidden border border-border/45 bg-surface/80 transition duration-300 hover:-translate-y-1 hover:border-primary/80 hover:shadow-gold', className)} {...props}>
      <div className="pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-300 group-hover:opacity-100" style={{ background: 'radial-gradient(240px circle at var(--glow-x) var(--glow-y), rgba(255,215,106,.13), transparent 68%)' }} />
      <div className="relative">{children}</div>
    </div>
  )
}
