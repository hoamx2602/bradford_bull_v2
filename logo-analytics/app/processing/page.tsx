'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Nav from '@/components/nav'
import { getJob } from '@/lib/api'

const STEPS = [
  { label: 'Frame extraction',       detail: (n: string) => n || 'Frames extracted' },
  { label: 'Target-team identification', detail: (n: string) => n || 'Kit references + player tracking' },
  { label: 'YOLO26 logo detection',  detail: (n: string) => n || 'Brands identified across frames' },
  { label: 'Computing exposure scores', detail: (n: string) => n || 'Quality-weighted segments calculated' },
  { label: 'Calculating media value',   detail: (n: string) => n || 'EMV computed per brand' },
]

// Backend pipeline stage -> index of the last COMPLETED step (0-indexed).
// `team` only appears when the kit-reference bootstrap runs; the `detect`
// stage marks both step 0 and 1 complete either way.
const STAGE_TO_STEP: Record<string, number> = {
  queued: -1, frames: -1, team: 0, detect: 1, exposure: 2, pricing: 3,
  preview: 3, bodyseg: 3, done: 4,
}

export default function ProcessingPage() {
  const router = useRouter()
  const [meta, setMeta] = useState<{ videoName: string; eventName: string } | null>(null)
  const [step, setStep] = useState(-1)   // which step is complete (0-indexed)
  const [pct, setPct] = useState(0)
  const [done, setDone] = useState(false)
  const [detail, setDetail] = useState('')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    try {
      const raw = localStorage.getItem('sl_meta')
      if (raw) setMeta(JSON.parse(raw))
    } catch {}
  }, [])

  // Poll the backend job and drive the UI from real progress.
  useEffect(() => {
    const jobId = typeof window !== 'undefined' ? localStorage.getItem('sl_job') : null
    if (!jobId) {
      // No job (e.g. opened directly) — fall back to the demo dashboard.
      router.push('/dashboard')
      return
    }

    let cancelled = false
    const tick = async () => {
      try {
        const job = await getJob(jobId)
        if (cancelled) return
        setPct(job.progress)
        setDetail(job.stageDetail || '')
        setStep(STAGE_TO_STEP[job.stage] ?? -1)

        if (job.status === 'done' && job.analysisId) {
          setDone(true)
          setPct(100)
          setStep(STEPS.length - 1)
          localStorage.setItem('sl_analysis', job.analysisId)
          setTimeout(() => router.push(`/dashboard?analysis=${job.analysisId}`), 700)
          return
        }
        if (job.status === 'error') {
          setError(job.error || 'Analysis failed')
          return
        }
        timer = setTimeout(tick, 1500)
      } catch (e) {
        if (cancelled) return
        setError(e instanceof Error ? e.message : 'Could not reach the analysis backend')
      }
    }
    let timer = setTimeout(tick, 300)
    return () => { cancelled = true; clearTimeout(timer) }
  }, [router])

  const videoName = meta?.videoName ?? 'broadcast_video.mp4'
  const eventName = meta?.eventName ?? 'Sports Event'
  const frameCount = detail

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Nav />
      <main style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '48px 24px' }}>
        <div style={{ width: '100%', maxWidth: 520 }} className="slide-up">

          {/* Header */}
          <div style={{ marginBottom: 36 }}>
            <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--c-spark)', marginBottom: 10 }}>
              Analysing
            </div>
            <h2 style={{ fontSize: 22, fontWeight: 600, margin: 0, letterSpacing: '-0.01em', wordBreak: 'break-all' }}>
              {eventName}
            </h2>
            <div style={{ color: 'var(--c-dim)', fontSize: 13, marginTop: 6, fontFamily: 'monospace', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {videoName}
            </div>
          </div>

          {/* Progress bar */}
          <div style={{ marginBottom: 36 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
              <span style={{ color: 'var(--c-dim)', fontSize: 12 }}>
                {done ? 'Complete' : step < 0 ? 'Starting…' : STEPS[step].label}
              </span>
              <span className="num" style={{ fontSize: 12, color: done ? 'var(--c-spark)' : 'var(--c-dim)' }}>
                {pct}%
              </span>
            </div>
            <div style={{ height: 3, background: 'var(--c-wire)', borderRadius: 2, overflow: 'hidden' }}>
              <div style={{
                height: '100%',
                width: `${pct}%`,
                background: 'var(--c-spark)',
                borderRadius: 2,
                transition: 'width 0.08s linear',
              }} />
            </div>
          </div>

          {/* Steps */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
            {STEPS.map((s, i) => {
              const isComplete = step >= i
              const isActive = step === i - 1 && !done
              const isPending = step < i - 1

              return (
                <div
                  key={i}
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: 16,
                    padding: '14px 0',
                    borderBottom: i < STEPS.length - 1 ? '1px solid var(--c-wire)' : 'none',
                    opacity: isPending ? 0.35 : 1,
                    transition: 'opacity 0.3s',
                  }}
                >
                  {/* Icon */}
                  <div style={{ width: 22, height: 22, flexShrink: 0, marginTop: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    {isComplete ? (
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                        <circle cx="12" cy="12" r="10" fill="var(--c-spark)" />
                        <polyline points="8 12 11 15 16 9" stroke="#000" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    ) : isActive ? (
                      <div style={{ width: 16, height: 16, border: '2px solid var(--c-spark)', borderTopColor: 'transparent', borderRadius: '50%' }} className="spin" />
                    ) : (
                      <div style={{ width: 16, height: 16, border: '1.5px solid var(--c-wire-s)', borderRadius: '50%' }} />
                    )}
                  </div>

                  {/* Text */}
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: isComplete || isActive ? 500 : 400, color: isComplete ? 'var(--c-ink)' : isActive ? 'var(--c-ink)' : 'var(--c-dim)' }}>
                      {s.label}
                    </div>
                    {isComplete && (
                      <div style={{ color: 'var(--c-dim)', fontSize: 12, marginTop: 2 }}>
                        {s.detail(frameCount)}
                      </div>
                    )}
                    {isActive && (
                      <div style={{ color: 'var(--c-spark)', fontSize: 12, marginTop: 2 }}>
                        In progress…
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>

          {/* Error state */}
          {error && (
            <div style={{ marginTop: 28, textAlign: 'center' }} className="slide-up">
              <div style={{ color: '#FF6B6B', fontSize: 13, marginBottom: 12 }}>{error}</div>
              <button
                onClick={() => router.push('/')}
                style={{
                  background: 'none', border: '1px solid var(--c-wire)', borderRadius: 6,
                  color: 'var(--c-dim)', padding: '8px 16px', fontSize: 12,
                }}
              >
                Back to upload
              </button>
            </div>
          )}

          {/* Done state */}
          {done && !error && (
            <div style={{ marginTop: 28, textAlign: 'center' }} className="slide-up">
              <div style={{ color: 'var(--c-dim)', fontSize: 13 }}>Redirecting to results…</div>
            </div>
          )}

          {!done && !error && (
            <div style={{ marginTop: 28, color: 'var(--c-ghost)', fontSize: 12 }}>
              {step < 0 ? 'Initialising…' : `Step ${Math.min(step + 2, STEPS.length)} of ${STEPS.length}`}
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
