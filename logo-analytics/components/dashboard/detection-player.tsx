'use client'

import { useRef, useState, useEffect, useMemo } from 'react'
import type { AnalysisResult } from '@/lib/types'
import { videoUrl } from '@/lib/api'

const LABEL_W = 150
const ROW_H = 28
const RULER_H = 30

function fmt(t: number) {
  const m = Math.floor(t / 60)
  const s = Math.floor(t % 60)
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

// "Nice" tick spacing so the ruler shows round time marks.
const TICK_STEPS = [1, 2, 5, 10, 15, 30, 60, 120, 300, 600]

export default function DetectionPlayer({ result }: { result: AnalysisResult }) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const trackRef = useRef<HTMLDivElement>(null)
  const [current, setCurrent] = useState(0)
  const [duration, setDuration] = useState(result.videoDurationSeconds || 0)

  // Smooth playhead: drive from rAF while playing (onTimeUpdate only fires ~4/s).
  useEffect(() => {
    const v = videoRef.current
    if (!v) return
    let raf = 0
    const loop = () => { setCurrent(v.currentTime); raf = requestAnimationFrame(loop) }
    const onPlay = () => { raf = requestAnimationFrame(loop) }
    const onStop = () => cancelAnimationFrame(raf)
    v.addEventListener('play', onPlay)
    v.addEventListener('pause', onStop)
    v.addEventListener('ended', onStop)
    return () => {
      cancelAnimationFrame(raf)
      v.removeEventListener('play', onPlay)
      v.removeEventListener('pause', onStop)
      v.removeEventListener('ended', onStop)
    }
  }, [])

  const ticks = useMemo(() => {
    const d = duration || 1
    const stepRaw = d / 12
    const step = TICK_STEPS.find(s => s >= stepRaw) ?? stepRaw
    const arr: number[] = []
    for (let t = 0; t <= d + 1e-6; t += step) arr.push(t)
    return arr
  }, [duration])

  const seek = (clientX: number) => {
    const el = trackRef.current
    const v = videoRef.current
    if (!el || !v || !duration) return
    const rect = el.getBoundingClientRect()
    const frac = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width))
    v.currentTime = frac * duration
    setCurrent(v.currentTime)
  }

  const pct = duration ? (current / duration) * 100 : 0

  // Per-brand on-screen intervals, matching the boxes drawn on the video.
  const tracks = result.detectionTimeline ?? []

  return (
    <div>
      <video
        ref={videoRef}
        key={result.id}
        src={videoUrl(result.id)}
        controls
        playsInline
        onTimeUpdate={e => setCurrent(e.currentTarget.currentTime)}
        onLoadedMetadata={e => setDuration(e.currentTarget.duration || result.videoDurationSeconds)}
        style={{ width: '100%', borderRadius: 8, display: 'block', background: '#000' }}
      />

      {/* Per-brand detection timeline, synced to the player */}
      <div style={{ display: 'flex', marginTop: 14, userSelect: 'none' }}>
        {/* Brand labels */}
        <div style={{ width: LABEL_W, flexShrink: 0 }}>
          <div style={{ height: RULER_H }} />
          {tracks.map(tr => (
            <div
              key={tr.class}
              style={{
                height: ROW_H, display: 'flex', alignItems: 'center', justifyContent: 'flex-end',
                gap: 7, paddingRight: 10, fontSize: 12, color: 'var(--c-dim)',
                overflow: 'hidden', whiteSpace: 'nowrap', textOverflow: 'ellipsis',
              }}
            >
              <span style={{ width: 8, height: 8, borderRadius: 2, background: tr.color, flexShrink: 0 }} />
              <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{tr.name}</span>
            </div>
          ))}
        </div>

        {/* Track area (ruler + rows + playhead) */}
        <div
          ref={trackRef}
          onClick={e => seek(e.clientX)}
          style={{ position: 'relative', flex: 1, cursor: 'pointer', borderLeft: '1px solid var(--c-wire)' }}
        >
          {/* Ruler */}
          <div style={{ height: RULER_H, position: 'relative', borderBottom: '1px solid var(--c-wire)' }}>
            {ticks.map((t, i) => (
              <div
                key={i}
                style={{
                  position: 'absolute', left: `${duration ? (t / duration) * 100 : 0}%`, bottom: 4,
                  transform: 'translateX(-50%)', fontSize: 10, color: 'var(--c-ghost)',
                  fontFamily: 'monospace', whiteSpace: 'nowrap',
                }}
              >
                {fmt(t)}
              </div>
            ))}
          </div>

          {/* Brand rows */}
          {tracks.map((tr, ri) => (
            <div
              key={tr.class}
              style={{
                height: ROW_H, position: 'relative',
                background: ri % 2 ? 'transparent' : 'rgba(255,255,255,0.02)',
              }}
            >
              {tr.intervals.map((iv, si) => {
                const left = duration ? (iv.start / duration) * 100 : 0
                const w = duration ? ((iv.end - iv.start) / duration) * 100 : 0
                if (left > 100) return null
                return (
                  <div
                    key={si}
                    title={`${tr.name}: ${fmt(iv.start)}–${fmt(iv.end)}`}
                    style={{
                      position: 'absolute', left: `${left}%`, width: `${Math.max(w, 0.4)}%`,
                      top: '50%', transform: 'translateY(-50%)', height: 11, borderRadius: 3,
                      background: tr.color, opacity: 0.9,
                    }}
                  />
                )
              })}
            </div>
          ))}

          {/* Playhead */}
          <div style={{
            position: 'absolute', top: 0, bottom: 0, left: `${pct}%`,
            width: 2, marginLeft: -1, background: '#FF3B3B', pointerEvents: 'none',
            boxShadow: '0 0 4px rgba(255,59,59,0.6)',
          }} />
        </div>
      </div>
    </div>
  )
}
