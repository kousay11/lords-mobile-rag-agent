'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { getPlayerProfile } from '@/lib/api'
import { Archive, BarChart3, Castle, LogOut, Settings, ShieldCheck } from 'lucide-react'
import { BackendReadinessGate } from '@/components/backend-readiness-gate'
import { AtmosphericBackground } from '@/components/layout/atmospheric-background'
import { getRole, isAuthenticated } from '@/lib/auth'
import { useAuth } from '@/hooks/useAuth'
import './chat-theme.css'

export default function ChatLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()
  const { logout } = useAuth()
  const [profileReady, setProfileReady] = useState(false)
  const [profileError, setProfileError] = useState(false)
  useEffect(() => {
    if (pathname !== '/chat' || !isAuthenticated()) return
    let cancelled = false
    setProfileReady(false)
    setProfileError(false)
    getPlayerProfile().then((profile) => {
      if (cancelled) return
      if (!profile.setupCompleted) router.replace('/settings')
      else setProfileReady(true)
    }).catch(() => { if (!cancelled) setProfileError(true) })
    return () => { cancelled = true }
  }, [pathname, router])
  const [mounted, setMounted] = useState(false)
  useEffect(() => { if (!isAuthenticated()) router.replace('/login'); else setMounted(true) }, [router])
  if (mounted && pathname === '/chat' && profileError) return <div className="p-8"><p role="alert">Impossible de vérifier votre profil.</p><button onClick={() => window.location.reload()} className="mt-4 text-primary">Réessayer</button></div>
  if (mounted && pathname === '/chat' && !profileReady) return <div className="flex min-h-dvh items-center justify-center text-muted">Vérification de votre profil…</div>
  if (!mounted) return <div className="min-h-screen bg-background" />

  return <BackendReadinessGate><div className="relative flex h-dvh flex-col overflow-hidden bg-background text-text-main"><AtmosphericBackground /><header className="relative z-40 shrink-0 border-b border-primary/30 bg-[#0b0e11]/95 shadow-[0_8px_30px_rgba(0,0,0,.4)]"><div className="mx-auto flex h-16 w-full max-w-[1600px] items-center justify-between px-4 lg:px-6"><Link href="/" className="flex items-center gap-3"><span className="flex h-9 w-9 items-center justify-center border border-primary/60 bg-primary/10 text-primary"><Castle className="h-5 w-5" /></span><span><strong className="block font-display text-xs tracking-[.16em] text-gold-bright">KINGDOM SAGE</strong><small className="text-[8px] uppercase tracking-[.2em] text-muted">Strategy Command</small></span></Link><div className="hidden items-center gap-2 border-x border-border/40 px-4 text-[9px] uppercase tracking-[.18em] text-muted sm:flex"><ShieldCheck className="h-3.5 w-3.5 text-accent" /><span>Assistant Lords Mobile</span><span className="h-1 w-1 rounded-full bg-accent shadow-blue" /><span>Réponses sourcées</span></div><nav className="flex items-center gap-1"><Link href="/guides" className="hidden px-3 py-2 text-[10px] uppercase tracking-wider text-muted hover:text-primary md:block">Guides</Link><Link href="/settings" className="p-2 text-muted hover:text-primary" title="Profil joueur"><Settings className="h-4 w-4" /></Link>{getRole() === 'ADMIN' && <Link href="/chat/documents" className="p-2 text-muted hover:text-primary" title="Archives administrateur"><Archive className="h-4 w-4" /></Link>}{getRole() === 'ADMIN' && <Link href="/admin/feedback" className="p-2 text-muted hover:text-primary" title="Retours des commandants"><BarChart3 className="h-4 w-4" /></Link>}<button onClick={logout} className="p-2 text-muted hover:text-danger" title="Déconnexion" aria-label="Déconnexion"><LogOut className="h-4 w-4" /></button></nav></div></header><div className="relative min-h-0 flex-1">{children}</div></div></BackendReadinessGate>
}
