import { ButtonHTMLAttributes } from 'react'
import { cn } from '@/lib/utils'

export function ShimmerButton({ className, children, ...props }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button className={cn('relative isolate overflow-hidden border border-gold-bright/70 bg-gradient-to-b from-gold-bright to-primary px-5 py-3 font-display text-sm font-bold uppercase tracking-wider text-[#201609] shadow-gold transition hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-45', className)} {...props}><span className="absolute inset-y-0 left-0 -z-0 w-1/3 animate-shimmer bg-gradient-to-r from-transparent via-white/55 to-transparent" /><span className="relative z-10">{children}</span></button>
}
