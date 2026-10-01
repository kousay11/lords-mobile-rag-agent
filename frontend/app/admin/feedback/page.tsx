'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { ArrowLeft, Copy, Download, ExternalLink, Loader2, RefreshCw, ThumbsDown, ThumbsUp, Users } from 'lucide-react'
import { toast } from 'sonner'
import { FeedbackStats, NegativeFeedbackPage, getApiErrorMessage, getFeedbackStats, getNegativeFeedback } from '@/lib/api'
import { getRole, isAuthenticated } from '@/lib/auth'

const PERIODS = [7, 14, 30] as const

function Chart({ stats }: { stats: FeedbackStats }) {
  const width = 640
  const height = 220
  const pad = { top: 12, right: 12, bottom: 26, left: 34 }
  const n = Math.max(1, stats.series.length)
  const max = Math.max(1, ...stats.series.map((d) => Math.max(d.helpful, d.notHelpful)))
  const ticks = max <= 10
    ? Array.from({ length: max + 1 }, (_, t) => t)
    : Array.from({ length: 6 }, (_, i) => Math.round((max * i) / 5))
  const y = (v: number) => pad.top + (height - pad.top - pad.bottom) * (1 - v / max)
  const group = (width - pad.left - pad.right) / n
  const barW = Math.max(4, Math.min(16, group * 0.22))
  const labelEvery = Math.max(1, Math.ceil(n / 8))
  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full" role="img" aria-label="Votes par jour en barres">
      {ticks.map((t) => (
        <g key={t}>
          <line x1={pad.left} x2={width - pad.right} y1={y(t)} y2={y(t)} stroke="currentColor" strokeOpacity="0.12" />
          <text x={pad.left - 6} y={y(t) + 4} textAnchor="end" fontSize="10" fill="currentColor" opacity="0.55">{t}</text>
        </g>
      ))}
      {stats.series.map((d, i) => {
        const cx = pad.left + group * (i + 0.5)
        const empty = d.helpful === 0 && d.notHelpful === 0
        return (
          <g key={d.date} opacity={empty ? 0.35 : 1}>
            <rect x={cx - barW - 1} y={y(d.helpful)} width={barW} height={Math.max(0, height - pad.bottom - y(d.helpful))} rx="1.5" className="fill-accent">
              <title>{`${d.date} · utiles : ${d.helpful}`}</title>
            </rect>
            <rect x={cx + 1} y={y(d.notHelpful)} width={barW} height={Math.max(0, height - pad.bottom - y(d.notHelpful))} rx="1.5" className="fill-danger">
              <title>{`${d.date} · non utiles : ${d.notHelpful}`}</title>
            </rect>
            {d.helpful > 0 && (
              <text x={cx - barW / 2 - 1} y={y(d.helpful) - 4} textAnchor="middle" fontSize="9" fill="currentColor" opacity="0.8">{d.helpful}</text>
            )}
            {d.notHelpful > 0 && (
              <text x={cx + barW / 2 + 1} y={y(d.notHelpful) - 4} textAnchor="middle" fontSize="9" fill="currentColor" opacity="0.8">{d.notHelpful}</text>
            )}
            {i % labelEvery === 0 && (
              <text x={cx} y={height - 8} textAnchor="middle" fontSize="9" fill="currentColor" opacity="0.55">
                {d.date.slice(5)}
              </text>
            )}
          </g>
        )
      })}
    </svg>
  )
}

export default function FeedbackStatsPage() {
  const router = useRouter()
  const [days, setDays] = useState<number>(30)
  const [stats, setStats] = useState<FeedbackStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [negative, setNegative] = useState<NegativeFeedbackPage | null>(null)
  const [negLoading, setNegLoading] = useState(false)
  const [negIntent, setNegIntent] = useState<string>('')
  const [negQuery, setNegQuery] = useState<string>('')
  const [negPage, setNegPage] = useState<number>(0)
  const negSize = 20

  const loadNegative = useCallback(async (page: number) => {
    setNegLoading(true)
    try {
      setNegative(await getNegativeFeedback({
        days,
        intent: negIntent || undefined,
        q: negQuery.trim() || undefined,
        page,
        size: negSize,
      }))
    } catch (error) {
      toast.error(getApiErrorMessage(error))
    } finally {
      setNegLoading(false)
    }
  }, [days, negIntent, negQuery])

  const load = useCallback(async () => {
    setLoading(true)
    try {
      setStats(await getFeedbackStats(days))
    } catch (error) {
      toast.error(getApiErrorMessage(error))
    } finally {
      setLoading(false)
    }
    await loadNegative(0)
    setNegPage(0)
  }, [days, loadNegative])

  useEffect(() => {
    if (!isAuthenticated()) { router.replace('/login'); return }
    if (getRole() !== 'ADMIN') { router.replace('/chat'); return }
    void load()
  }, [load, router])

  useEffect(() => {
    const timer = setTimeout(() => { void loadNegative(negPage) }, negQuery ? 400 : 0)
    return () => clearTimeout(timer)
  }, [loadNegative, negPage])

  const copyQuestion = async (question: string) => {
    try {
      await navigator.clipboard.writeText(question)
      toast.success('Question copiée — colle-la dans le Corpus pour enrichir la DB')
    } catch {
      toast.error('Copie impossible dans ce navigateur')
    }
  }

  const exportCsv = () => {
    if (!negative?.items.length) return
    const rows = [['date', 'intent', 'question', 'answer_excerpt', 'comment']]
    for (const item of negative.items) {
      const cell = (v: string | null | undefined) => `"${(v ?? '').replace(/"/g, '""')}"`
      rows.push([item.createdAt, item.intent, cell(item.question), cell(item.answerExcerpt), cell(item.comment)])
    }
    const blob = new Blob([rows.map((r) => r.join(',')).join('\n')], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'questions-non-utiles.csv'
    link.click()
    URL.revokeObjectURL(url)
  }

  const ratio = useMemo(() => (stats ? Math.round(stats.helpfulRatio * 100) : 0), [stats])
  const maxIntent = useMemo(
    () => Math.max(1, ...(stats?.byIntent.map((b) => b.helpful + b.notHelpful) ?? [1])),
    [stats]
  )

  return (
    <div className="scrollbar-thin h-full overflow-y-auto">
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
        <div className="mb-8 flex items-center justify-between">
          <div>
            <Link href="/chat" className="mb-3 inline-flex items-center gap-1 text-sm text-muted hover:text-text-main">
              <ArrowLeft className="h-4 w-4" /> Retour au chat
            </Link>
            <h1 className="flex items-center gap-3 text-2xl font-bold">
              <Users className="text-primary" /> Retours des commandants
            </h1>
            <p className="mt-2 text-sm text-muted">
              Agrégats anonymes des 👍 / 👎 sur les réponses du Sage. Aucune donnée par utilisateur.
            </p>
          </div>
          <button onClick={() => void load()} className="rounded-lg border border-border p-2 text-muted" title="Actualiser">
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>

        <div className="mb-6 flex gap-2">
          {PERIODS.map((p) => (
            <button
              key={p}
              onClick={() => setDays(p)}
              className={`rounded-lg border px-4 py-2 text-xs font-semibold uppercase tracking-wider transition ${
                days === p ? 'border-primary bg-primary/10 text-primary' : 'border-border text-muted hover:text-text-main'
              }`}
            >
              {p} jours
            </button>
          ))}
        </div>

        {loading && !stats ? (
          <div className="py-16 text-center"><Loader2 className="mx-auto h-6 w-6 animate-spin" /></div>
        ) : !stats || stats.total === 0 ? (
          <div className="glass rounded-2xl p-10 text-center text-muted">
            Aucun vote sur cette période. Les courbes apparaîtront dès les premiers 👍 / 👎.
          </div>
        ) : (
          <>
            <div className="grid gap-4 sm:grid-cols-3">
              <div className="glass rounded-2xl p-5">
                <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-muted"><ThumbsUp className="h-4 w-4 text-accent" /> Utiles</div>
                <p className="mt-2 text-3xl font-bold text-text-main">{stats.helpful}</p>
              </div>
              <div className="glass rounded-2xl p-5">
                <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-muted"><ThumbsDown className="h-4 w-4 text-danger" /> Non utiles</div>
                <p className="mt-2 text-3xl font-bold text-text-main">{stats.notHelpful}</p>
              </div>
              <div className="glass rounded-2xl p-5">
                <div className="text-xs uppercase tracking-wider text-muted">% utiles · {stats.total} votes</div>
                <p className="mt-2 text-3xl font-bold text-gradient">{ratio}%</p>
              </div>
            </div>

            <section className="glass mt-6 rounded-2xl p-5">
              <h2 className="font-semibold">Votes par jour</h2>
              <div className="mt-2 flex flex-wrap items-center gap-4 text-xs text-muted">
                <span className="inline-flex items-center gap-1"><span className="h-2 w-4 rounded bg-accent" /> Utiles ({stats.helpful})</span>
                <span className="inline-flex items-center gap-1"><span className="h-2 w-4 rounded bg-danger" /> Non utiles ({stats.notHelpful})</span>
                <span className="opacity-60">jours sans vote grisés</span>
              </div>
              <div className="mt-4 text-text-main"><Chart stats={stats} /></div>
            </section>

            <section className="glass mt-6 rounded-2xl p-5">
              <h2 className="font-semibold">Par intention de question</h2>
              <div className="mt-4 space-y-3">
                {stats.byIntent.map((b) => (
                  <div key={b.intent}>
                    <div className="flex items-center justify-between text-xs text-muted">
                      <span className="font-mono uppercase tracking-wider">{b.intent}</span>
                      <span>{b.helpful} 👍 · {b.notHelpful} 👎</span>
                    </div>
                    <div className="mt-1 flex h-2 overflow-hidden rounded bg-background">
                      <div className="bg-accent" style={{ width: `${((b.helpful / Math.max(1, b.helpful + b.notHelpful)) * 100).toFixed(1)}%` }} />
                      <div className="bg-danger/70" style={{ width: `${((b.notHelpful / Math.max(1, b.helpful + b.notHelpful)) * 100).toFixed(1)}%` }} />
                    </div>
                    <p className="mt-1 text-[11px] text-muted">{b.helpful + b.notHelpful} votes sur {maxIntent} max</p>
                  </div>
                ))}
              </div>
            </section>

            <section className="glass mt-6 rounded-2xl p-5">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h2 className="flex items-center gap-2 font-semibold"><ThumbsDown className="h-4 w-4 text-danger" /> Questions jugées non utiles</h2>
                  <p className="mt-1 text-xs text-muted">Récupère chaque question 👎 pour enrichir la DB — sans aucune donnée utilisateur.</p>
                </div>
                <div className="flex gap-2">
                  <button onClick={exportCsv} disabled={!negative?.items.length} className="flex items-center gap-1 rounded-lg border border-border px-3 py-1.5 text-xs text-muted hover:text-text-main disabled:opacity-40"><Download className="h-3.5 w-3.5" /> CSV</button>
                  <Link href="/chat/documents" className="flex items-center gap-1 rounded-lg bg-primary px-3 py-1.5 text-xs font-semibold text-white"><ExternalLink className="h-3.5 w-3.5" /> Corpus</Link>
                </div>
              </div>
              <div className="mt-4 flex flex-col gap-2 sm:flex-row">
                <input
                  value={negQuery}
                  onChange={(e) => { setNegQuery(e.target.value); setNegPage(0) }}
                  placeholder="Rechercher dans question / réponse / commentaire…"
                  className="flex-1 rounded-lg border border-border bg-background px-3 py-2 text-sm outline-none focus:border-primary"
                />
                <select
                  value={negIntent}
                  onChange={(e) => { setNegIntent(e.target.value); setNegPage(0) }}
                  className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
                >
                  <option value="">Toutes intentions</option>
                  {stats.byIntent.map((b) => <option key={b.intent} value={b.intent}>{b.intent}</option>)}
                </select>
              </div>
              <div className="mt-4 space-y-3">
                {negLoading && !negative ? (
                  <div className="py-10 text-center"><Loader2 className="mx-auto h-5 w-5 animate-spin" /></div>
                ) : !negative?.items.length ? (
                  <p className="rounded-xl border border-border/50 p-6 text-center text-sm text-muted">Aucune question 👎 sur cette période — la DB couvre les usages actuels.</p>
                ) : (
                  negative.items.map((item) => (
                    <article key={item.feedbackId} className="rounded-xl border border-border/60 bg-background/50 p-4">
                      <div className="flex flex-wrap items-center gap-2 text-[11px] text-muted">
                        <span className="rounded-full bg-danger/10 px-2 py-0.5 font-mono uppercase text-danger">{item.intent}</span>
                        <span>{new Date(item.createdAt).toLocaleString()}</span>
                        {item.confidence != null && <span>confiance {Math.round(Number(item.confidence) * 100)}%</span>}
                      </div>
                      <p className="mt-2 text-sm font-semibold text-text-main">Q : {item.question || '—'}</p>
                      {item.answerExcerpt && <p className="mt-1 line-clamp-3 text-xs leading-5 text-muted">R : {item.answerExcerpt}</p>}
                      {item.comment && <p className="mt-1 text-xs italic text-gold-bright">💬 {item.comment}</p>}
                      <div className="mt-3 flex flex-wrap gap-2">
                        <button onClick={() => void copyQuestion(item.question)} className="flex items-center gap-1 rounded-lg border border-primary/40 px-2.5 py-1.5 text-xs text-primary hover:bg-primary/10"><Copy className="h-3.5 w-3.5" /> Copier la question</button>
                        <Link href="/chat/documents" className="rounded-lg bg-primary px-2.5 py-1.5 text-xs font-semibold text-white">Enrichir le Corpus</Link>
                      </div>
                    </article>
                  ))
                )}
              </div>
              {negative && negative.total > negSize && (
                <div className="mt-4 flex items-center justify-between text-xs text-muted">
                  <span>{negative.total} questions 👎 · page {negPage + 1} / {Math.max(1, Math.ceil(negative.total / negSize))}</span>
                  <div className="flex gap-2">
                    <button disabled={negPage === 0 || negLoading} onClick={() => { const p = negPage - 1; setNegPage(p); void loadNegative(p) }} className="rounded-lg border border-border px-3 py-1.5 disabled:opacity-40">←</button>
                    <button disabled={(negPage + 1) * negSize >= negative.total || negLoading} onClick={() => { const p = negPage + 1; setNegPage(p); void loadNegative(p) }} className="rounded-lg border border-border px-3 py-1.5 disabled:opacity-40">→</button>
                  </div>
                </div>
              )}
            </section>
          </>
        )}
      </div>
    </div>
  )
}
