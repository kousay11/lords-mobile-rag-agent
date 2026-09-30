'use client'

import { FormEvent, useEffect, useState } from 'react'
import Link from 'next/link'
import { ArrowLeft, Loader2, Save, UserRound } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { toast } from 'sonner'
import { getApiErrorMessage, getPlayerProfile, getProfileVersionOptions, ProfileVersionOption, PlayerProfile, updatePlayerProfile } from '@/lib/api'
import { isAuthenticated } from '@/lib/auth'
import { AtmosphericBackground } from '@/components/layout/atmospheric-background'
import { GamePanel } from '@/components/ui/game-panel'
import { ShimmerButton } from '@/components/ui/shimmer-button'

const initialProfile: PlayerProfile = { language: 'fr', gameVersion: '', playerLevel: '', playStyle: '', kingdom: '', responseLength: 'standard', versionMode: null, additionalContext: {} }
const fieldClass = 'mt-2 w-full border border-border/60 bg-background/80 px-4 py-3 text-sm outline-none focus:border-primary'

export default function SettingsPage() {
  const router = useRouter()
  const [profile, setProfile] = useState<PlayerProfile>(initialProfile)
  const [additionalContextText, setAdditionalContextText] = useState('{}')
  const [versions, setVersions] = useState<ProfileVersionOption[]>([])
  const [versionError, setVersionError] = useState(false)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState(false)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!isAuthenticated()) { router.replace('/login'); return }
    let cancelled = false
    getPlayerProfile().then((saved) => {
      if (!cancelled) {
        setProfile({ ...saved, responseLength: saved.responseLength || 'standard' })
        setAdditionalContextText(JSON.stringify(saved.additionalContext || {}, null, 2))
      }
    }).catch((error) => {
      if (!cancelled) { setLoadError(true); toast.error(getApiErrorMessage(error)) }
    }).finally(() => { if (!cancelled) setLoading(false) })
    getProfileVersionOptions().then((items) => {
      if (!cancelled) setVersions(items.sort((a, b) => {
        const order = { review: 0, release: 1, guide: 2, corpus: 3 }
        return order[a.kind] - order[b.kind] || b.value.localeCompare(a.value, undefined, { numeric: true })
      }))
    })
      .catch(() => { if (!cancelled) setVersionError(true) })
    return () => { cancelled = true }
  }, [router])

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    let additionalContext: Record<string, unknown>
    try {
      const parsed = JSON.parse(additionalContextText || '{}')
      if (!parsed || Array.isArray(parsed) || typeof parsed !== 'object') throw new Error()
      additionalContext = parsed as Record<string, unknown>
    } catch {
      toast.error('Le contexte complémentaire doit être un objet JSON valide.')
      return
    }
    setSaving(true)
    try {
      const saved = await updatePlayerProfile({ ...profile, additionalContext, gameVersion: profile.versionMode === 'specific' ? profile.gameVersion : null })
      setProfile(saved)
      setAdditionalContextText(JSON.stringify(saved.additionalContext || {}, null, 2))
      toast.success('Préférences enregistrées. Votre chat est prêt.')
      router.push('/chat')
    } catch (error) { toast.error(getApiErrorMessage(error)) }
    finally { setSaving(false) }
  }

  if (loading) return <div className="flex min-h-screen items-center justify-center"><Loader2 className="h-7 w-7 animate-spin text-primary" aria-label="Chargement du profil" /></div>
  if (loadError) return <main className="mx-auto max-w-xl p-8"><p role="alert">Impossible de charger votre profil. Vos préférences n’ont pas été modifiées.</p><button className="mt-4 text-primary" onClick={() => window.location.reload()}>Réessayer</button></main>

  const versionSelection = profile.versionMode === 'unknown' ? 'unknown' : profile.versionMode === 'specific' ? profile.gameVersion || '' : ''
  const selectedVersion = versions.find((item) => item.value === versionSelection)
  return <main className="relative min-h-screen px-4 py-10">
    <AtmosphericBackground />
    <div className="relative mx-auto max-w-3xl">
      {profile.setupCompleted && <Link href="/chat" className="mb-8 inline-flex items-center gap-2 text-xs text-muted hover:text-primary"><ArrowLeft className="h-4 w-4" /> Retour au chat</Link>}
      <header className="mb-9 text-center">
        <UserRound className="mx-auto h-10 w-10 text-primary" />
        <h1 className="kingdom-title mt-5 text-3xl font-bold">Vos préférences de conseil</h1>
        <p className="mt-3 text-sm text-muted">{profile.setupCompleted ? 'Ces préférences s’appliquent à vos prochaines questions, y compris dans les conversations existantes.' : 'Configurez votre profil avant votre première question. Vous pourrez le modifier à tout moment.'}</p>
      </header>
      <GamePanel className="p-6 sm:p-8">
        <p className="mb-6 text-xs text-muted">Préférences enregistrées dans votre compte. Les champs marqués * sont obligatoires.</p>
        <form onSubmit={submit} className="grid gap-5 sm:grid-cols-2">
          <label className="text-sm">Langue des réponses *
            <select required className={fieldClass} value={profile.language || ''} onChange={(e) => setProfile({ ...profile, language: e.target.value })}>
              <option value="fr">Français</option><option value="en">English</option><option value="ar">العربية</option>
            </select>
          </label>
          <label className="text-sm">Longueur des réponses *
            <select required className={fieldClass} value={profile.responseLength || ''} onChange={(e) => setProfile({ ...profile, responseLength: e.target.value as PlayerProfile['responseLength'] })}>
              <option value="short">Courte — l’essentiel</option><option value="standard">Standard — avec explications</option><option value="detailed">Détaillée — étapes et limites</option>
            </select>
          </label>
          <label className="text-sm sm:col-span-2">Version ou corpus documentaire *
            <select required className={fieldClass} value={versionSelection} onChange={(e) => setProfile({ ...profile, versionMode: e.target.value === 'unknown' ? 'unknown' : e.target.value ? 'specific' : null, gameVersion: e.target.value === 'unknown' ? null : e.target.value })}>
              <option value="" disabled>Choisissez une option</option>
              <option value="unknown">Sans version précise — sources validées</option>
              {versions.map((version) => <option key={version.value} value={version.value}>{version.label} ({version.documentCount} document{version.documentCount > 1 ? 's' : ''})</option>)}
              {profile.versionMode === 'specific' && profile.gameVersion && !versions.some((item) => item.value === profile.gameVersion) && <option value={profile.gameVersion} disabled>{profile.gameVersion} — à revalider</option>}
            </select>
            <span className="mt-2 block text-xs leading-5 text-muted">La liste contient tous les ensembles déjà indexés. « Corpus 2025/2026 » désigne un lot documentaire, pas un numéro de version du jeu ni une garantie de fraîcheur. Les archives peuvent décrire des règles anciennes.</span>
            {selectedVersion && selectedVersion.needsReviewCount > 0 && <span role="status" className="mt-2 block text-xs text-primary">{selectedVersion.needsReviewCount} document(s) avec réserves. En choisissant ce corpus, vous demandez une consultation prudente de ces sources ; leur contenu ne sera pas présenté comme une validation de la version actuelle.</span>}
            {versionError && <span role="status" className="mt-2 block text-xs text-primary">La liste des versions est indisponible. Vous pouvez choisir « Sans version précise ».</span>}
          </label>
          <label className="text-sm">Progression
            <input maxLength={100} className={fieldClass} value={profile.playerLevel || ''} onChange={(e) => setProfile({ ...profile, playerLevel: e.target.value })} placeholder="Ex. Château niveau 25" />
          </label>
          <label className="text-sm">Style de jeu
            <select className={fieldClass} value={profile.playStyle || ''} onChange={(e) => setProfile({ ...profile, playStyle: e.target.value })}>
              <option value="">Non précisé</option><option value="free_to_play">Free-to-play</option><option value="low_spender">Petit budget</option><option value="competitive">Compétitif</option>
            </select>
          </label>
          <label className="text-sm sm:col-span-2">Royaume
            <input maxLength={100} className={fieldClass} value={profile.kingdom || ''} onChange={(e) => setProfile({ ...profile, kingdom: e.target.value })} placeholder="Ex. K123" />
          </label>
          <label className="text-sm sm:col-span-2">Contexte complémentaire
            <textarea rows={6} className={`${fieldClass} font-mono text-xs`} value={additionalContextText} onChange={(e) => setAdditionalContextText(e.target.value)} placeholder={'{\n  "troupes": "T4",\n  "objectifs": "..."\n}'} />
            <span className="mt-2 block text-xs leading-5 text-muted">Objet JSON facultatif pour les informations de jeu supplémentaires utilisées par l’assistant. L’état de configuration du profil est géré automatiquement.</span>
          </label>
          <ShimmerButton disabled={saving || !profile.versionMode} className="flex items-center justify-center gap-2 sm:col-span-2">
            {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />} Enregistrer et ouvrir le chat
          </ShimmerButton>
        </form>
      </GamePanel>
    </div>
  </main>
}
