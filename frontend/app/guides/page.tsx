import Link from 'next/link'
import { ArrowLeft, BookOpen, Building2, CalendarDays, Castle, FlaskConical, Shield, Swords, Target, Users } from 'lucide-react'
import { AtmosphericBackground } from '@/components/layout/atmospheric-background'
import { GamePanel } from '@/components/ui/game-panel'

const guides = [
  [Users, 'Héros & Colisée', 'Compositions, rôles et synergies documentées.'], [Swords, 'Troupes', 'Forces, faiblesses et sécurité de vos armées.'],
  [FlaskConical, 'Recherche', 'Chemins de recherche et priorités de progression.'], [Building2, 'Bâtiments', 'Développement du territoire et prérequis.'],
  [Target, 'Chasse aux monstres', 'Équipes, énergie et choix des héros.'], [Castle, 'Guilde', 'Coopération, cadeaux et activités collectives.'],
  [CalendarDays, 'Événements', 'Règles et préparation des événements.'], [Shield, 'Défense & boucliers', 'Protection du territoire et des troupes.'],
] as const

export default function GuidesPage() {
  return <main className="relative min-h-screen px-5 py-10"><AtmosphericBackground /><div className="mx-auto max-w-6xl"><Link href="/" className="inline-flex items-center gap-2 text-sm text-muted hover:text-primary"><ArrowLeft className="h-4 w-4" /> Retour au royaume</Link><header className="my-14 text-center"><BookOpen className="mx-auto h-9 w-9 text-primary" /><p className="mt-5 font-mono text-[10px] uppercase tracking-[.3em] text-primary">Bibliothèque royale</p><h1 className="kingdom-title mt-3 text-4xl font-bold">Guides du Royaume</h1><p className="mx-auto mt-4 max-w-2xl text-muted">Sélectionnez un domaine puis interrogez le conseiller. Chaque réponse est recherchée dans le corpus disponible.</p></header><div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">{guides.map(([Icon,title,text]) => <GamePanel key={title} className="p-5"><Icon className="h-5 w-5 text-primary" /><h2 className="mt-5 font-display text-sm font-bold uppercase tracking-wide">{title}</h2><p className="mt-2 text-xs leading-5 text-muted">{text}</p><Link href="/chat" className="mt-5 inline-block text-xs font-semibold uppercase tracking-wider text-accent hover:text-gold-bright">Consulter le Sage →</Link></GamePanel>)}</div></div></main>
}
