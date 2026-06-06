'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Nav from '@/components/nav'

const STEPS = [
  { label: 'Frame extraction',       detail: (n: string) => `${n} frames extracted` },
  { label: 'YOLO26 logo detection',  detail: () => '10 brands identified across frames' },
  { label: 'Computing exposure scores', detail: () => 'Quality-weighted segments calculated' },
  { label: 'Calculating media value',   detail: () => 'EMV computed per brand' },
]

export default function ProcessingPage() {
  const router = useRouter()
  const [meta, setMeta] = useState<{ videoName: string; eventName: string } | null>(null)
  const [step, setStep] = useState(-1)   // which step is complete (0-indexed)
  const [pct, setPct] = useState(0)
  const [done, setDone] = useState(false)

  useEffect(() => {
    try {
      const raw = localStorage.getItem('sl_meta')
      if (raw) setMeta(JSON.parse(raw))
    } catch {}
  }, [])

  // Animate progress bar
  useEffect(() => {
    const target = done ? 100 : step < 0 ? 0 : Math.round(((step + 1) / STEPS.length) * 95)
    const timer = setInterval(() => {
      setPct(prev => {
        if (prev >= target) { clearInterval(timer); return prev }
        return Math.min(target, prev + 1)
      })
    }, 18)
    return () => clearInterval(timer)
  }, [step, done])

  // Step sequence
  useEffect(() => {
    const delays = [400, 1800, 3400, 5000, 6400]
    const timers = delays.map((d, i) => setTimeout(() => {
      if (i < STEPS.length) setStep(i)
      else { setDone(true); setTimeout(() => router.push('/dashboard'), 900) }
    }, d))
    return () => timers.forEach(clearTimeout)
  }, [router])

  const videoName = meta?.videoName ?? 'broadcast_video.mp4'
  const eventName = meta?.eventName ?? 'Sports Event'
  const frameCount = '5,400'

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

          {/* Done state */}
          {done && (
            <div style={{ marginTop: 28, textAlign: 'center' }} className="slide-up">
              <div style={{ color: 'var(--c-dim)', fontSize: 13 }}>Redirecting to results…</div>
            </div>
          )}

          {!done && (
            <div style={{ marginTop: 28, color: 'var(--c-ghost)', fontSize: 12 }}>
              {step < 0 ? 'Initialising…' : `Step ${Math.min(step + 2, STEPS.length)} of ${STEPS.length}`}
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
