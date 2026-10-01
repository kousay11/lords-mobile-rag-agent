'use client'

import { FormEvent, useEffect, useState } from 'react'
import Link from 'next/link'
import Image from 'next/image'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { ArrowRight, BookOpen, Bot, Building2, CalendarDays, Castle, Crown, FlaskConical, Gem, Menu, Search, Send, Shield, Sparkles, Swords, Target, Trophy, Users, X, Zap } from 'lucide-react'
import { AtmosphericBackground } from '@/components/layout/atmospheric-background'
import { CategoryCard } from './category-card'
import { ShimmerButton } from '@/components/ui/shimmer-button'
import { isAuthenticated, getUsername, getRole } from '@/lib/auth'
import { useAuth } from '@/hooks/useAuth'

const categories = [
  { icon: Users, title: 'Héros', description: 'Compositions, rôles et synergies.', prompt: 'Quels héros choisir et comment créer une bonne composition ?' },
  { icon: Swords, title: 'Troupes', description: 'Types, contres et protection.', prompt: 'Explique-moi les types de troupes et leurs contres.' },
  { icon: FlaskConical, title: 'Recherche', description: 'Priorités selon votre progression.', prompt: 'Quelles recherches dois-je prioriser en premier ?' },
  { icon: Building2, title: 'Bâtiments', description: 'Développement efficace du territoire.', prompt: 'Quels bâtiments améliorer en priorité ?' },
  { icon: Target, title: 'Monstres', description: 'Équipes et stratégie de chasse.', prompt: 'Quelle est la meilleure stratégie de chasse aux monstres ?' },
  { icon: Castle, title: 'Guilde', description: 'Coopération, cadeaux et événements.', prompt: 'Comment progresser efficacement avec ma guilde ?' },
  { icon: CalendarDays, title: 'Événements', description: 'Préparation et optimisation.', prompt: 'Comment préparer les événements Lords Mobile ?' },
  { icon: Shield, title: 'Boucliers', description: 'Défense du territoire et sécurité.', prompt: 'Comment fonctionnent les boucliers et comment protéger mes troupes ?' },
]

const questions = ['Meilleurs héros pour le Colisée', 'Comment augmenter ma Puissance ?', 'Comment protéger mes troupes ?', 'Meilleure stratégie de chasse aux monstres']

const strategyPaths = [
  {
    icon: Crown,
    label: 'Développer',
    title: 'Faire grandir mon royaume',
    description: 'Construisez une progression cohérente sans disperser vos ressources.',
    steps: ['Priorités des bâtiments', 'Arbre de recherche adapté', 'Gestion des accélérateurs'],
    prompt: 'Crée un plan de progression pour développer efficacement mon royaume.',
    accent: 'text-primary',
  },
  {
    icon: Swords,
    label: 'Combattre',
    title: 'Préparer une offensive',
    description: 'Analysez les contres, les talents, les formations et la composition des troupes.',
    steps: ['Identifier la composition ennemie', 'Choisir le bon contre', 'Préparer héros et équipement'],
    prompt: 'Aide-moi à préparer une offensive et à choisir une composition de troupes.',
    accent: 'text-danger',
  },
  {
    icon: Target,
    label: 'Chasser',
    title: 'Optimiser la chasse aux monstres',
    description: 'Trouvez les bons héros et améliorez l’efficacité de votre énergie.',
    steps: ['Identifier le type de dégâts', 'Composer l’équipe de héros', 'Optimiser énergie et récompenses'],
    prompt: 'Aide-moi à choisir une équipe et une stratégie de chasse aux monstres.',
    accent: 'text-accent',
  },
  {
    icon: Users,
    label: 'Coopérer',
    title: 'Progresser avec ma guilde',
    description: 'Préparez les événements collectifs et coordonnez les objectifs de guilde.',
    steps: ['Planifier les objectifs', 'Coordonner les contributions', 'Maximiser les récompenses'],
    prompt: 'Donne-moi un plan pour progresser et participer efficacement avec ma guilde.',
    accent: 'text-gold-bright',
  },
]

const troopCounters = [
  { icon: Shield, name: 'Infanterie', beats: 'Distance', color: 'text-accent' },
  { icon: Target, name: 'Distance', beats: 'Cavalerie', color: 'text-primary' },
  { icon: Zap, name: 'Cavalerie', beats: 'Infanterie', color: 'text-danger' },
]

export function KingdomLanding() {
  const router = useRouter()
  const { logout } = useAuth()
  const [query, setQuery] = useState('')
  const [menu, setMenu] = useState(false)
  const [activeStrategy, setActiveStrategy] = useState(0)
  const [mounted, setMounted] = useState(false)
  const [authenticated, setAuthenticated] = useState(false)
  const [username, setUsername] = useState<string | null>(null)
  const [role, setRole] = useState<string | null>(null)

  useEffect(() => {
    setAuthenticated(isAuthenticated())
    setUsername(getUsername())
    setRole(getRole())
    setMounted(true)
  }, [])
  const ask = (prompt: string) => {
    if (!prompt.trim()) return
    localStorage.setItem('lords_mobile_pending_prompt', prompt.trim())
    router.push('/chat')
  }
  const submit = (event: FormEvent) => { event.preventDefault(); ask(query) }

  return (
    <main className="relative min-h-screen overflow-hidden">
      <AtmosphericBackground />
      <header className="relative z-40 border-b border-primary/20 bg-background/72 backdrop-blur-lg">
        <nav className="mx-auto flex h-20 max-w-7xl items-center justify-between px-5 lg:px-8">
          <Link href="/" className="flex items-center gap-3"><span className="relative flex h-10 w-10 items-center justify-center border border-primary/60 bg-primary/10 text-primary shadow-gold"><Castle className="h-5 w-5" /><span className="absolute -bottom-1 -right-1 h-2 w-2 bg-accent shadow-blue" /></span><span><strong className="block font-display text-sm tracking-[.18em] text-gold-bright">KINGDOM SAGE</strong><small className="text-[9px] uppercase tracking-[.24em] text-muted">Royal Archives</small></span></Link>
          <div className="hidden items-center gap-8 text-xs font-semibold uppercase tracking-[.16em] md:flex"><Link className="text-primary" href="/">Kingdom</Link><Link className="text-muted hover:text-gold-bright" href="/guides">Guides</Link>{!mounted || !authenticated ? (<><Link className="text-muted hover:text-gold-bright" href="/login">Login</Link><Link href="/register" className="border border-primary/60 px-4 py-2 text-primary hover:bg-primary/10">Join</Link></>) : (<><Link className="text-muted hover:text-gold-bright" href="/dashboard">Dashboard</Link>{role === 'ADMIN' && <Link className="text-muted hover:text-gold-bright" href="/admin">Users</Link>}<span className="text-gold-bright normal-case tracking-normal">{username}</span><button onClick={logout} className="border border-primary/60 px-4 py-2 text-primary hover:bg-primary/10">Logout</button></>)}</div>
          <button onClick={() => setMenu(!menu)} className="p-2 text-primary md:hidden" aria-label="Menu">{menu ? <X /> : <Menu />}</button>
        </nav>
        {menu && <div className="border-t border-border bg-background p-5 md:hidden"><div className="flex flex-col gap-4 text-sm"><Link href="/guides">Guides</Link>{!mounted || !authenticated ? (<Link href="/login">Login</Link>) : (<><Link href="/dashboard">Dashboard</Link>{role === 'ADMIN' && <Link href="/admin">Users</Link>}<button onClick={logout} className="text-left text-primary">Logout ({username})</button></>)}</div></div>}
      </header>

      <section className="relative flex min-h-[720px] items-center px-5 py-24">
        <div className="absolute inset-0 overflow-hidden" aria-hidden="true">
          <Image src="/images/kingdom-sage-hero.png" alt="" fill priority sizes="100vw" className="object-cover object-center opacity-55" />
          <div className="absolute inset-0 bg-gradient-to-b from-background/65 via-background/55 to-background" />
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(9,11,13,.28),rgba(9,11,13,.76)_72%)]" />
          <div className="absolute inset-x-0 bottom-0 h-[44%] opacity-50 [background:linear-gradient(150deg,transparent_25%,#080a0c_25%_31%,transparent_31%),linear-gradient(30deg,transparent_45%,#0c1014_45%_52%,transparent_52%)]" />
          {[12,27,44,65,82].map((left, index) => <i key={left} className="absolute bottom-24 h-1 w-1 rounded-full bg-gold-bright shadow-[0_0_10px_3px_rgba(255,215,106,.5)] motion-safe:animate-[ember_5s_ease-out_infinite]" style={{ left: `${left}%`, animationDelay: `${index * .8}s` }} />)}
        </div>
        <div className="relative mx-auto w-full max-w-6xl text-center">
          <motion.div initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .7 }}>
            <span className="inline-flex items-center gap-2 border-y border-primary/35 px-4 py-2 text-[10px] font-bold uppercase tracking-[.3em] text-primary"><Sparkles className="h-3 w-3" /> Intelligence des archives du royaume</span>
            <h1 className="kingdom-title mx-auto mt-8 max-w-5xl text-5xl font-extrabold leading-[.94] text-text-main sm:text-7xl lg:text-8xl">Kingdom <span className="text-gradient">Sage</span></h1>
            <p className="mx-auto mt-6 max-w-2xl text-base leading-7 text-muted sm:text-lg">Votre assistant intelligent pour Lords Mobile : héros, troupes, recherche, monstres, événements et progression du royaume, réunis dans un même conseil stratégique.</p>
          </motion.div>
          <motion.form onSubmit={submit} initial={{ opacity: 0, y: 22 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: .25, duration: .7 }} className="game-panel mx-auto mt-10 flex max-w-3xl items-center gap-3 p-2 shadow-gold"><Search className="ml-3 h-5 w-5 text-primary" /><input value={query} onChange={(event) => setQuery(event.target.value)} className="min-w-0 flex-1 bg-transparent px-2 py-4 text-sm outline-none placeholder:text-muted/60" placeholder="Demandez conseil au Sage du Royaume…" aria-label="Question Lords Mobile" /><ShimmerButton type="submit" className="flex items-center gap-2 px-4 py-3"><Send className="h-4 w-4" /><span className="hidden sm:inline">Consulter</span></ShimmerButton></motion.form>
          <div className="mt-6 flex flex-wrap justify-center gap-3"><Link href="/chat" className="inline-flex items-center gap-2 border border-primary/60 bg-primary/10 px-5 py-3 font-display text-xs font-bold uppercase tracking-wider text-primary hover:bg-primary/20"><Bot className="h-4 w-4" /> Interroger le conseiller</Link><Link href="/guides" className="inline-flex items-center gap-2 border border-secondary/60 bg-secondary/10 px-5 py-3 font-display text-xs font-bold uppercase tracking-wider text-accent hover:bg-secondary/20"><BookOpen className="h-4 w-4" /> Explorer les guides</Link></div>
        </div>
      </section>

      <section className="relative mx-auto max-w-7xl px-5 py-20 lg:px-8"><div className="mb-10 flex items-end justify-between gap-4"><div><p className="font-mono text-[10px] uppercase tracking-[.3em] text-primary">Archives stratégiques</p><h2 className="kingdom-title mt-3 text-3xl font-bold">Choisissez votre domaine</h2></div><div className="hidden h-px flex-1 bg-gradient-to-r from-border/70 to-transparent md:block" /></div><div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">{categories.map((category, index) => <motion.div key={category.title} initial={{ opacity: 0, y: 18 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: index * .05 }}><CategoryCard {...category} onClick={() => ask(category.prompt)} /></motion.div>)}</div></section>

      <section className="relative border-y border-primary/15 bg-[linear-gradient(135deg,rgba(23,31,40,.88),rgba(9,11,13,.94))] px-5 py-20">
        <div className="mx-auto grid max-w-7xl gap-10 lg:grid-cols-[.78fr_1.22fr] lg:px-3">
          <div>
            <p className="font-mono text-[10px] uppercase tracking-[.3em] text-accent">Table de commandement</p>
            <h2 className="kingdom-title mt-3 text-3xl font-bold">Quel est votre objectif ?</h2>
            <p className="mt-4 max-w-lg text-sm leading-6 text-muted">Sélectionnez une mission pour obtenir un itinéraire stratégique et poser directement la bonne question au conseiller.</p>
            <div className="mt-8 grid grid-cols-2 gap-3">
              {strategyPaths.map((path, index) => {
                const Icon = path.icon
                const selected = activeStrategy === index
                return <motion.button key={path.label} type="button" whileHover={{ y: -3 }} whileTap={{ scale: .98 }} onClick={() => setActiveStrategy(index)} className={`group relative overflow-hidden border p-4 text-left transition ${selected ? 'border-primary bg-primary/12 shadow-gold' : 'border-border/60 bg-background/50 hover:border-primary/50'}`} aria-pressed={selected}>
                  <span className={`mb-3 flex h-9 w-9 items-center justify-center border ${selected ? 'border-primary/60 bg-primary/15' : 'border-border bg-surface/60'} ${path.accent}`}><Icon className="h-4 w-4" /></span>
                  <strong className="font-display text-xs uppercase tracking-[.12em]">{path.label}</strong>
                  {selected && <motion.span layoutId="strategy-marker" className="absolute inset-x-0 bottom-0 h-0.5 bg-gradient-to-r from-transparent via-primary to-transparent" />}
                </motion.button>
              })}
            </div>
          </div>

          <motion.div key={activeStrategy} initial={{ opacity: 0, x: 18 }} animate={{ opacity: 1, x: 0 }} className="game-panel relative overflow-hidden p-6 shadow-blue sm:p-8">
            <div className="absolute right-0 top-0 h-44 w-44 rounded-full bg-accent/8 blur-3xl" />
            <div className="relative flex flex-col justify-between gap-8 sm:flex-row">
              <div>
                <span className="inline-flex items-center gap-2 text-[10px] font-bold uppercase tracking-[.24em] text-primary"><Trophy className="h-3.5 w-3.5" /> Mission recommandée</span>
                <h3 className="kingdom-title mt-4 text-2xl font-bold sm:text-3xl">{strategyPaths[activeStrategy].title}</h3>
                <p className="mt-3 max-w-xl text-sm leading-6 text-muted">{strategyPaths[activeStrategy].description}</p>
              </div>
              <span className="flex h-16 w-16 shrink-0 items-center justify-center border border-primary/40 bg-primary/10 text-primary shadow-gold"><Gem className="h-7 w-7" /></span>
            </div>
            <div className="relative mt-8 grid gap-3 sm:grid-cols-3">
              {strategyPaths[activeStrategy].steps.map((step, index) => <div key={step} className="border border-border/60 bg-background/55 p-4"><span className="font-mono text-[9px] uppercase tracking-[.2em] text-accent">Étape 0{index + 1}</span><p className="mt-2 text-xs font-semibold leading-5 text-text-main">{step}</p></div>)}
            </div>
            <button type="button" onClick={() => ask(strategyPaths[activeStrategy].prompt)} className="relative mt-6 inline-flex items-center gap-3 border border-primary/60 bg-primary/10 px-5 py-3 font-display text-xs font-bold uppercase tracking-[.12em] text-primary transition hover:bg-primary/20">Demander ce plan au Sage <ArrowRight className="h-4 w-4" /></button>
          </motion.div>
        </div>
      </section>

      <section className="relative mx-auto max-w-7xl px-5 py-20 lg:px-8">
        <div className="text-center"><p className="font-mono text-[10px] uppercase tracking-[.3em] text-primary">Boussole du combat</p><h2 className="kingdom-title mt-3 text-3xl font-bold">Maîtrisez le triangle des troupes</h2><p className="mx-auto mt-4 max-w-2xl text-sm leading-6 text-muted">Une lecture rapide des contres fondamentaux avant d’examiner les héros, les formations, l’équipement et les bonus de recherche.</p></div>
        <div className="mt-10 grid gap-4 md:grid-cols-3">
          {troopCounters.map((troop, index) => { const Icon = troop.icon; return <motion.button type="button" key={troop.name} onClick={() => ask(`Explique-moi comment utiliser ${troop.name} contre ${troop.beats} et quelles exceptions surveiller.`)} whileHover={{ y: -6, scale: 1.01 }} className="game-panel group relative p-6 text-left transition hover:border-primary/60 hover:shadow-gold"><div className="flex items-center justify-between"><span className={`flex h-12 w-12 items-center justify-center border border-current/40 bg-background/60 ${troop.color}`}><Icon className="h-6 w-6" /></span><span className="font-mono text-[9px] uppercase tracking-[.18em] text-muted">Contre 0{index + 1}</span></div><h3 className="mt-5 font-display text-lg font-bold uppercase tracking-wider">{troop.name}</h3><p className="mt-2 flex items-center gap-2 text-xs text-muted"><span className="text-primary">Avantage sur</span><ArrowRight className="h-3.5 w-3.5 transition group-hover:translate-x-1" />{troop.beats}</p></motion.button> })}
        </div>
      </section>

      <section className="border-y border-primary/15 bg-surface/30 px-5 py-20"><div className="mx-auto max-w-5xl text-center"><p className="font-mono text-[10px] uppercase tracking-[.3em] text-accent">Questions des commandants</p><h2 className="kingdom-title mt-3 text-3xl font-bold">Conseils fréquemment demandés</h2><div className="mt-9 flex flex-wrap justify-center gap-3">{questions.map((question) => <button onClick={() => ask(question)} key={question} className="border border-border/60 bg-background/70 px-4 py-3 text-sm text-muted transition hover:border-primary hover:text-gold-bright">{question}</button>)}</div></div></section>
      <footer className="px-5 py-8 text-center text-[10px] uppercase tracking-[.2em] text-muted">Kingdom Sage · L’assistant stratégique des joueurs de Lords Mobile</footer>
    </main>
  )
}
