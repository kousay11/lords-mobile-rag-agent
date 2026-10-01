'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { ArrowLeft, Loader2, RefreshCw, ThumbsDown, ThumbsUp, Users } from 'lucide-react'
import { toast } from 'sonner'
import { FeedbackStats, getApiErrorMessage, getFeedbackStats } from '@/lib/api'
import { getRole, isAuthenticated } from '@/lib/auth'

const PERIODS = [7, 14, 30] as const

function Chart({ stats }: { stats: FeedbackStats }) {
  const width = 640
  const height = 220
  const pad = { top: 12, right: 12, bottom: 26, left: 34 }
  const max = Math.max(1, ...stats.series.map((d) => Math.max(d.helpful, d.notHelpful)))
  const x = (i: number) => pad.left + (i * (width - pad.left - pad.right)) / Math.max(1, stats.series.length - 1)
  const y = (v: number) => pad.top + (height - pad.top - pad.bottom) * (1 - v / max)
  const line = (pick: (d: FeedbackStats['series'][number]) => number) =>
    stats.series.map((d, i) => `${i === 0 ? 'M' : 'L'}${x(i).toFixed(1)},${y(pick(d)).toFixed(1)}`).join(' ')
  const ticks = [0, 0.5, 1].map((f) => Math.round(max * f))
  const labelEvery = Math.max(1, Math.ceil(stats.series.length / 8))
  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full" role="img" aria-label="Courbes des votes par jour">
      {ticks.map((t) => (
        <g key={t}>
          <line x1={pad.left} x2={width - pad.right} y1={y(t)} y2={y(t)} stroke="currentColor" strokeOpacity="0.12" />
          <text x={pad.left - 6} y={y(t) + 4} textAnchor="end" fontSize="10" fill="currentColor" opacity="0.55">{t}</text>
        </g>
      ))}
      {stats.series.map((d, i) =>
        i % labelEvery === 0 ? (
          <text key={d.date} x={x(i)} y={height - 8} textAnchor="middle" fontSize="9" fill="currentColor" opacity="0.55">
            {d.date.slice(5)}
          </text>
        ) : null
      )}
      <path d={line((d) => d.notHelpful)} fill="none" strokeWidth="2" className="stroke-danger" />
      <path d={line((d) => d.helpful)} fill="none" strokeWidth="2" className="stroke-accent" />
      {stats.series.map((d, i) => (
        <g key={d.date}>
          <circle cx={x(i)} cy={y(d.helpful)} r="2.5" className="fill-accent" />
          <circle cx={x(i)} cy={y(d.notHelpful)} r="2.5" className="fill-danger" />
        </g>
      ))}
    </svg>
  )
}

export default function FeedbackStatsPage() {
  const router = useRouter()
  const [days, setDays] = useState<number>(30)
  const [stats, setStats] = useState<FeedbackStats | null>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      setStats(await getFeedbackStats(days))
    } catch (error) {
      toast.error(getApiErrorMessage(error))
    } finally {
      setLoading(false)
    }
  }, [days])

  useEffect(() => {
    if (!isAuthenticated()) { router.replace('/login'); return }
    if (getRole() !== 'ADMIN') { router.replace('/chat'); return }
    void load()
  }, [load, router])

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
              <div className="mt-2 flex items-center gap-4 text-xs text-muted">
                <span className="inline-flex items-center gap-1"><span className="h-2 w-4 rounded bg-accent" /> Utiles</span>
                <span className="inline-flex items-center gap-1"><span className="h-2 w-4 rounded bg-danger" /> Non utiles</span>
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
          </>
        )}
      </div>
    </div>
  )
}
