'use client'

import { useState } from 'react'
import type { AnalysisResult } from '@/lib/types'
import { formatSeconds, formatCurrency, formatNumber } from '@/lib/utils'

// ── Icons (inline SVG, no extra dep) ────────────────────────────────────────
const Icon = {
  video: (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/>
    </svg>
  ),
  layers: (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>
    </svg>
  ),
  scan: (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2"/>
      <rect x="7" y="7" width="10" height="10" rx="1"/>
    </svg>
  ),
  chart: (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/>
      <line x1="6" y1="20" x2="6" y2="14"/><line x1="2" y1="20" x2="22" y2="20"/>
    </svg>
  ),
  trending: (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/>
    </svg>
  ),
}

interface Stat { key: string; value: string; accent?: boolean }

interface Stage {
  id: string
  step: string
  label: string
  icon: React.ReactNode
  processingMs: number  // 0 = no processing (input node)
  stats: Stat[]
}

interface Props {
  result: AnalysisResult
}

export default function PipelineView({ result }: Props) {
  const [active, setActive] = useState<string | null>(null)

  const totalSegments = result.logos.reduce((s, l) => s + l.segmentCount, 0)
  // Mock pipeline metrics (in production these come from the AI pipeline runner)
  const frameCount    = result.videoDurationSeconds  // 1 fps sampling
  const detections    = totalSegments * 11 + 42      // approx raw detections before NMS
  const flickers      = Math.round(totalSegments * 0.17)

  const STAGES: Stage[] = [
    {
      id: 'input',
      step: '01',
      label: 'Video Input',
      icon: Icon.video,
      processingMs: 0,
      stats: [
        { key: 'File',      value: result.videoName.length > 22 ? result.videoName.slice(0, 20) + '…' : result.videoName },
        { key: 'Duration',  value: formatSeconds(result.videoDurationSeconds) },
        { key: 'Placement', value: result.metadata.placementType },
      ],
    },
    {
      id: 'frames',
      step: '02',
      label: 'Frame Extraction',
      icon: Icon.layers,
      processingMs: 12_400,
      stats: [
        { key: 'Frames',      value: formatNumber(frameCount) },
        { key: 'Sample rate', value: '1 fps' },
        { key: 'Resolution',  value: '1920 × 1080' },
      ],
    },
    {
      id: 'detection',
      step: '03',
      label: 'YOLO26 Detection',
      icon: Icon.scan,
      processingMs: 38_700,
      stats: [
        { key: 'Model',         value: 'yolo26s.pt' },
        { key: 'Raw detections',value: formatNumber(detections) },
        { key: 'Brands found',  value: `${result.logos.length} of 15`, accent: true },
      ],
    },
    {
      id: 'exposure',
      step: '04',
      label: 'Exposure Scoring',
      icon: Icon.chart,
      processingMs: 2_100,
      stats: [
        { key: 'Valid segments',    value: formatNumber(totalSegments) },
        { key: 'Filtered (flicker)', value: formatNumber(flickers) },
        { key: 'Quality exposure',  value: formatSeconds(result.totalQualityExposureSeconds), accent: true },
      ],
    },
    {
      id: 'emv',
      step: '05',
      label: 'Media Value',
      icon: Icon.trending,
      processingMs: 300,
      stats: [
        { key: 'CPM base',    value: `$${result.metadata.cpmBase}` },
        { key: 'Audience',    value: formatNumber(result.metadata.audienceSize) },
        { key: 'Total EMV',   value: formatCurrency(result.totalEmvUsd), accent: true },
      ],
    },
  ]

  const maxMs = Math.max(...STAGES.map(s => s.processingMs))
  const totalMs = STAGES.reduce((s, st) => s + st.processingMs, 0)

  const fmtMs = (ms: number) => {
    if (ms === 0) return null
    if (ms < 1000) return `${ms}ms`
    return `${(ms / 1000).toFixed(1)}s`
  }

  return (
    <div>
      {/* Header bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <div style={{ fontSize: 12, color: 'var(--c-dim)' }}>
          5-stage AI pipeline · end-to-end
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: 'var(--c-dim)' }}>
          <span>Total processing time</span>
          <span className="num" style={{ color: 'var(--c-ink)', fontWeight: 600 }}>
            {(totalMs / 1000).toFixed(1)}s
          </span>
        </div>
      </div>

      {/* Pipeline row */}
      <div style={{ overflowX: 'auto', paddingBottom: 4 }}>
        <div style={{ display: 'flex', alignItems: 'stretch', minWidth: 'max-content', gap: 0 }}>
          {STAGES.map((stage, i) => (
            <div key={stage.id} style={{ display: 'flex', alignItems: 'center' }}>

              {/* Stage card */}
              <div
                onMouseEnter={() => setActive(stage.id)}
                onMouseLeave={() => setActive(null)}
                style={{
                  width: 185,
                  background: active === stage.id ? 'var(--c-hover)' : 'var(--c-panel)',
                  border: `1px solid ${active === stage.id ? 'var(--c-wire-s)' : 'var(--c-wire)'}`,
                  borderRadius: 9,
                  padding: '14px 16px',
                  transition: 'background 0.15s, border-color 0.15s',
                  cursor: 'default',
                }}
              >
                {/* Card header */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 9, marginBottom: 13 }}>
                  <div style={{
                    width: 28, height: 28, borderRadius: 6,
                    background: active === stage.id ? 'var(--c-spark-bg)' : 'rgba(255,255,255,0.03)',
                    border: '1px solid var(--c-wire)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                    color: active === stage.id ? 'var(--c-spark)' : 'var(--c-dim)',
                    transition: 'color 0.15s, background 0.15s',
                  }}>
                    {stage.icon}
                  </div>
                  <div>
                    <div style={{ fontSize: 10, color: 'var(--c-ghost)', letterSpacing: '0.06em', marginBottom: 1 }}>
                      Step {stage.step}
                    </div>
                    <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--c-ink)', lineHeight: 1.2 }}>
                      {stage.label}
                    </div>
                  </div>
                </div>

                {/* Divider */}
                <div style={{ height: 1, background: 'var(--c-wire)', marginBottom: 12 }} />

                {/* Stats */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
                  {stage.stats.map((stat, si) => (
                    <div key={si} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 8 }}>
                      <span style={{ fontSize: 11, color: 'var(--c-ghost)', flexShrink: 0 }}>
                        {stat.key}
                      </span>
                      <span className="num" style={{
                        fontSize: 11,
                        color: stat.accent ? 'var(--c-spark)' : 'var(--c-dim)',
                        fontWeight: stat.accent ? 600 : 400,
                        textAlign: 'right',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                        maxWidth: 100,
                      }}>
                        {stat.value}
                      </span>
                    </div>
                  ))}
                </div>

                {/* Timing bar */}
                <div style={{ marginTop: 14 }}>
                  {fmtMs(stage.processingMs) ? (
                    <>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5 }}>
                        <span style={{ fontSize: 10, color: 'var(--c-ghost)' }}>Processing</span>
                        <span className="num" style={{ fontSize: 10, color: 'var(--c-dim)' }}>
                          {fmtMs(stage.processingMs)}
                        </span>
                      </div>
                      <div style={{ height: 2, background: 'var(--c-wire)', borderRadius: 2, overflow: 'hidden' }}>
                        <div style={{
                          height: '100%',
                          width: `${(stage.processingMs / maxMs) * 100}%`,
                          background: stage.id === 'detection'
                            ? 'var(--c-spark)'
                            : 'var(--c-wire-s)',
                          borderRadius: 2,
                          transition: 'width 0.6s ease',
                        }} />
                      </div>
                    </>
                  ) : (
                    <div style={{ height: 22 }} />
                  )}
                </div>
              </div>

              {/* Arrow connector */}
              {i < STAGES.length - 1 && (
                <div style={{
                  width: 36,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0,
                  color: 'var(--c-ghost)',
                }}>
                  <svg width="20" height="12" viewBox="0 0 20 12" fill="none">
                    <path d="M0 6h16M11 1l5 5-5 5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Bottom: cumulative timeline bar */}
      <div style={{ marginTop: 16, paddingTop: 14, borderTop: '1px solid var(--c-wire)' }}>
        <div style={{ fontSize: 10, color: 'var(--c-ghost)', marginBottom: 7, letterSpacing: '0.06em' }}>
          CUMULATIVE PROCESSING TIME
        </div>
        <div style={{ display: 'flex', height: 6, borderRadius: 3, overflow: 'hidden', gap: 1 }}>
          {STAGES.filter(s => s.processingMs > 0).map(stage => {
            const w = (stage.processingMs / totalMs) * 100
            return (
              <div
                key={stage.id}
                title={`${stage.label}: ${fmtMs(stage.processingMs)}`}
                style={{
                  width: `${w}%`,
                  background: stage.id === 'detection'
                    ? 'var(--c-spark)'
                    : active === stage.id
                    ? 'var(--c-wire-s)'
                    : 'var(--c-wire)',
                  minWidth: 2,
                  transition: 'background 0.15s',
                  cursor: 'default',
                  borderRadius: 2,
                }}
              />
            )
          })}
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 5, fontSize: 10, color: 'var(--c-ghost)' }}>
          <span>0s</span>
          <span className="num" style={{ color: 'var(--c-dim)' }}>
            YOLO26 {((38700 / totalMs) * 100).toFixed(0)}% of pipeline
          </span>
          <span>{(totalMs / 1000).toFixed(1)}s</span>
        </div>
      </div>
    </div>
  )
}
