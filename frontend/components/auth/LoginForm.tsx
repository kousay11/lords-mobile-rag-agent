'use client'

import { FormEvent, useState } from 'react'
import Link from 'next/link'
import { Castle, Loader2 } from 'lucide-react'
import { loginApi, getApiErrorMessage } from '@/lib/api'
import { useAuth } from '@/hooks/useAuth'
import { GamePanel } from '@/components/ui/game-panel'
import { ShimmerButton } from '@/components/ui/shimmer-button'

export default function LoginForm() {
  const { login } = useAuth(); const [username,setUsername]=useState(''); const [password,setPassword]=useState(''); const [loading,setLoading]=useState(false); const [error,setError]=useState('')
  const submit=async(event:FormEvent)=>{event.preventDefault();setLoading(true);setError('');try{const result=await loginApi({username,password});login(result.token,result.username,result.role,result.profileRole)}catch(cause){setError(getApiErrorMessage(cause))}finally{setLoading(false)}}
  const input='mt-2 w-full border border-border/60 bg-background/75 px-4 py-3 text-sm outline-none transition focus:border-primary'
  return <div className="relative z-10 w-full max-w-md"><div className="mb-8 text-center"><span className="mx-auto mb-4 flex h-14 w-14 items-center justify-center border border-primary/60 bg-primary/10 text-primary shadow-gold"><Castle className="h-7 w-7" /></span><p className="font-mono text-[9px] uppercase tracking-[.3em] text-primary">Accès aux archives royales</p><h1 className="kingdom-title mt-3 text-2xl font-bold">Retour du Commandant</h1><p className="mt-2 text-sm text-muted">Connectez-vous au Sage du Royaume</p></div><GamePanel className="p-7 sm:p-8"><form onSubmit={submit} className="space-y-5">{error&&<p className="border border-danger/40 bg-danger/10 p-3 text-sm text-[#ff9188]">{error}</p>}<label className="block text-xs font-semibold uppercase tracking-wider text-muted">Nom d’utilisateur<input required minLength={3} autoComplete="username" value={username} onChange={(e)=>setUsername(e.target.value)} className={input}/></label><label className="block text-xs font-semibold uppercase tracking-wider text-muted">Mot de passe<input required minLength={8} type="password" autoComplete="current-password" value={password} onChange={(e)=>setPassword(e.target.value)} className={input}/></label><ShimmerButton disabled={loading} className="flex w-full items-center justify-center gap-2">{loading&&<Loader2 className="h-4 w-4 animate-spin"/>} Entrer dans le royaume</ShimmerButton><div className="metal-divider"/><p className="text-center text-xs text-muted">Nouveau commandant ? <Link href="/register" className="text-primary hover:text-gold-bright">Créer votre sceau</Link></p></form></GamePanel><Link href="/" className="mt-5 block text-center text-[10px] uppercase tracking-wider text-muted hover:text-primary">← Retour au royaume</Link></div>
}
