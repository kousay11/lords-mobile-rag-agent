'use client'

import { FormEvent, useCallback, useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { ArrowLeft, Database, FileUp, Loader2, Plus, RefreshCw, Trash2 } from 'lucide-react'
import { toast } from 'sonner'
import { deleteKnowledgeDocument, getApiErrorMessage, indexKnowledgeDocument, KnowledgeDocument, listKnowledgeDocuments, uploadKnowledgeDocument } from '@/lib/api'
import { getRole } from '@/lib/auth'

const ACCEPTED_EXTENSIONS = ['.pdf', '.md', '.markdown', '.txt'] as const
const MAX_UPLOAD_BYTES = 20 * 1024 * 1024

const emptyForm = { title: '', source: '', url: '', sourceType: 'official' as const, language: 'fr', gameVersion: '', reliability: 5, topics: '' }

export default function KnowledgePage() {
  const router = useRouter()
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([])
  const [form, setForm] = useState(emptyForm)
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [workingId, setWorkingId] = useState<string>()

  const load = useCallback(async () => {
    setLoading(true)
    try { setDocuments(await listKnowledgeDocuments()) }
    catch (error) { toast.error(getApiErrorMessage(error)) }
    finally { setLoading(false) }
  }, [])

  useEffect(() => {
    if (getRole() !== 'ADMIN') { router.replace('/chat'); return }
    void load()
  }, [load, router])

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (!file) { toast.error('Choisis un fichier .pdf ou .md'); return }
    const extension = `.${file.name.split('.').pop()?.toLowerCase() ?? ''}`
    if (!(ACCEPTED_EXTENSIONS as readonly string[]).includes(extension)) {
      toast.error('Seuls les fichiers .pdf et .md sont acceptés')
      return
    }
    if (file.size > MAX_UPLOAD_BYTES) { toast.error('Fichier trop volumineux (max 20 Mo)'); return }
    setSaving(true)
    try {
      const data = new FormData()
      data.append('file', file)
      data.append('title', form.title)
      data.append('source', form.source)
      if (form.url) data.append('url', form.url)
      data.append('sourceType', form.sourceType)
      data.append('language', form.language)
      data.append('gameVersion', form.gameVersion)
      data.append('reliability', String(form.reliability))
      data.append('topics', form.topics)
      await uploadKnowledgeDocument(data)
      setForm(emptyForm)
      setFile(null)
      toast.success('Fichier enregistré dans PostgreSQL')
      await load()
    } catch (error) { toast.error(getApiErrorMessage(error)) }
    finally { setSaving(false) }
  }

  const index = async (id: string) => {
    setWorkingId(id)
    try { await indexKnowledgeDocument(id); toast.success('Document indexé dans Qdrant'); await load() }
    catch (error) { toast.error(getApiErrorMessage(error)) }
    finally { setWorkingId(undefined) }
  }

  const remove = async (id: string) => {
    if (!window.confirm('Retirer ce document du catalogue et de l’index ?')) return
    setWorkingId(id)
    try { await deleteKnowledgeDocument(id); await load() }
    catch (error) { toast.error(getApiErrorMessage(error)) }
    finally { setWorkingId(undefined) }
  }

  const fieldClass = 'w-full rounded-lg border border-border bg-background px-3 py-2 text-sm outline-none focus:border-primary'

  return (
    <div className="scrollbar-thin h-full overflow-y-auto">
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
      <div className="mb-8 flex items-center justify-between">
        <div><Link href="/chat" className="mb-3 inline-flex items-center gap-1 text-sm text-muted hover:text-text-main"><ArrowLeft className="h-4 w-4" /> Retour au chat</Link><h1 className="flex items-center gap-3 text-2xl font-bold"><Database className="text-primary" /> Corpus documentaire</h1><p className="mt-2 text-sm text-muted">Validation PostgreSQL puis indexation contrôlée dans Qdrant.</p></div>
        <button onClick={() => void load()} className="rounded-lg border border-border p-2 text-muted" title="Actualiser"><RefreshCw className="h-4 w-4" /></button>
      </div>

      <div className="grid gap-6 lg:grid-cols-[380px_1fr]">
        <form onSubmit={submit} className="glass scrollbar-thin h-fit space-y-4 rounded-2xl p-5 lg:sticky lg:top-0 lg:max-h-[calc(100vh-8rem)] lg:overflow-y-auto">
          <h2 className="flex items-center gap-2 font-semibold"><Plus className="h-4 w-4" /> Ajouter une source</h2>
          <input required maxLength={255} className={fieldClass} placeholder="Titre" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
          <input required maxLength={500} className={fieldClass} placeholder="Identifiant source (ex. guide-chasse-2026)" value={form.source} onChange={(e) => setForm({ ...form, source: e.target.value })} />
          <input type="url" className={fieldClass} placeholder="URL (optionnelle)" value={form.url} onChange={(e) => setForm({ ...form, url: e.target.value })} />
          <div className="grid grid-cols-2 gap-3">
            <select className={fieldClass} value={form.sourceType} onChange={(e) => setForm({ ...form, sourceType: e.target.value as typeof form.sourceType })}><option value="official">Officielle</option><option value="verified_community">Communauté vérifiée</option><option value="community">Communauté</option><option value="reference">Référence</option></select>
            <input required className={fieldClass} placeholder="Version" value={form.gameVersion} onChange={(e) => setForm({ ...form, gameVersion: e.target.value })} />
            <input required pattern="[a-z]{2,3}(-[A-Z]{2})?" className={fieldClass} placeholder="Langue" value={form.language} onChange={(e) => setForm({ ...form, language: e.target.value })} />
            <select className={fieldClass} value={form.reliability} onChange={(e) => setForm({ ...form, reliability: Number(e.target.value) })}>{[5,4,3,2,1].map((n) => <option key={n} value={n}>Fiabilité {n}/5</option>)}</select>
          </div>
          <input required className={fieldClass} placeholder="Sujets séparés par des virgules" value={form.topics} onChange={(e) => setForm({ ...form, topics: e.target.value })} />
          <label className="block space-y-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-muted">Fichier du document (.pdf, .md)</span>
            <span className={`${fieldClass} flex cursor-pointer items-center gap-2`}>
              <FileUp className="h-4 w-4 shrink-0 text-primary" />
              <span className="truncate text-muted">{file ? `${file.name} (${(file.size / 1024).toFixed(0)} Ko)` : 'Choisir un fichier PDF ou Markdown…'}</span>
              <input required type="file" accept=".pdf,.md,.markdown,.txt" className="hidden" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
            </span>
            <span className="block text-[11px] text-muted">Le texte sera extrait puis découpé et indexé dans Qdrant après validation.</span>
          </label>
          <button disabled={saving} className="flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 font-semibold text-white disabled:opacity-50">{saving && <Loader2 className="h-4 w-4 animate-spin" />} Enregistrer</button>
        </form>

        <section className="space-y-3">
          {loading && <div className="py-16 text-center"><Loader2 className="mx-auto h-6 w-6 animate-spin" /></div>}
          {!loading && documents.length === 0 && <div className="glass rounded-2xl p-10 text-center text-muted">Aucun document enregistré.</div>}
          {documents.map((document) => (
            <article key={document.id} className="glass rounded-2xl p-5">
              <div className="flex items-start justify-between gap-4">
                <div><h3 className="font-semibold">{document.title}</h3><p className="mt-1 text-xs text-muted">{document.source} · {document.language} · version {document.gameVersion}</p></div>
                <span className={`rounded-full px-2 py-1 text-[11px] font-semibold ${document.status === 'active' ? 'bg-accent/10 text-accent' : document.status === 'needs_review' ? 'bg-danger/10 text-danger' : 'bg-primary/10 text-primary'}`}>{document.status}</span>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">{document.topics.map((topic) => <span key={topic} className="rounded bg-background px-2 py-1 text-xs text-muted">{topic}</span>)}</div>
              <p className="mt-3 text-xs text-muted">Fiabilité {document.reliability}/5 · {document.qdrantChunks} chunks · hash {document.contentHash.slice(0, 12)}…</p>
              {document.lastError && <p className="mt-2 text-xs text-danger">{document.lastError}</p>}
              <div className="mt-4 flex gap-2">
                {document.status !== 'active' && <button disabled={workingId === document.id} onClick={() => void index(document.id)} className="rounded-lg bg-primary px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-50">Indexer</button>}
                <button disabled={workingId === document.id} onClick={() => void remove(document.id)} className="rounded-lg border border-danger/30 p-1.5 text-danger disabled:opacity-50" title="Supprimer"><Trash2 className="h-4 w-4" /></button>
              </div>
            </article>
          ))}
        </section>
      </div>
      </div>
    </div>
  )
}
