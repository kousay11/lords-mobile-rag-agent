'use client'

import { LucideIcon, ArrowUpRight } from 'lucide-react'
import { GlowCard } from '@/components/ui/glow-card'
import { TiltCard } from '@/components/ui/tilt-card'

export function CategoryCard({ icon: Icon, title, description, onClick }: { icon: LucideIcon; title: string; description: string; onClick: () => void }) {
  return <TiltCard><GlowCard onClick={onClick} role="button" tabIndex={0} onKeyDown={(event) => { if (event.key === 'Enter') onClick() }} className="min-h-40 cursor-pointer p-5 [clip-path:polygon(10px_0,100%_0,100%_calc(100%-10px),calc(100%-10px)_100%,0_100%,0_10px)]"><div className="mb-6 flex items-start justify-between"><span className="border border-primary/35 bg-primary/10 p-2.5 text-primary"><Icon className="h-5 w-5" /></span><ArrowUpRight className="h-4 w-4 text-muted transition group-hover:text-gold-bright" /></div><h3 className="font-display text-sm font-bold uppercase tracking-wider">{title}</h3><p className="mt-2 text-xs leading-5 text-muted">{description}</p></GlowCard></TiltCard>
}
