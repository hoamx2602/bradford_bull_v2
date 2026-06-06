'use client'

import { useState } from 'react'
import type { LogoResult, Segment } from '@/lib/types'
import { formatSeconds, visibilityOpacity } from '@/lib/utils'

interface Tooltip {
  seg: Segment
  logoName: string
  x: number
  y: number
}

interface TimelineProps {
  logos: LogoResult[]
  videoDuration: number
}

const ROW_H = 38
const ROW_GAP = 6
const LABEL_W = 148
const TICK_COUNT = 7  // 0, 15m, 30m, 45m, 60m, 75m, 90m
const MIN_SEG_W = 3  // min px width so tiny segments stay visible

export default function Timeline({ logos, videoDuration }: TimelineProps) {
  const [tooltip, setTooltip] = useState<Tooltip | null>(null)
  const [hoveredLogo, setHoveredLogo] = useState<string | null>(null)

  const toPct = (t: number) => (t / videoDuration) * 100

  const ticks = Array.from({ length: TICK_COUNT }, (_, i) => ({
    pct: (i / (TICK_COUNT - 1)) * 100,
    label: formatSeconds(Math.round((i / (TICK_COUNT - 1)) * videoDuration)),
  }))

  return (
    <div style={{ position: 'relative', userSelect: 'none' }}>
      {/* Time axis */}
      <div style={{ display: 'flex', paddingLeft: LABEL_W, marginBottom: 8 }}>
        <div style={{ flex: 1, position: 'relative', height: 18 }}>
          {ticks.map((t, i) => (
            <div
              key={i}
              style={{
                position: 'absolute',
                left: `${t.pct}%`,
                transform: i === TICK_COUNT - 1 ? 'translateX(-100%)' : i === 0 ? 'none' : 'translateX(-50%)',
                fontSize: 10,
                color: 'var(--c-ghost)',
                fontFamily: 'monospace',
                whiteSpace: 'nowrap',
              }}
            >
              {t.label}
            </div>
          ))}
        </div>
      </div>

      {/* Rows */}
      <div style={{ position: 'relative' }}>
        {logos.map((logo, li) => (
          <div
            key={logo.id}
            style={{
              display: 'flex',
              alignItems: 'center',
              marginBottom: li < logos.length - 1 ? ROW_GAP : 0,
            }}
            onMouseEnter={() => setHoveredLogo(logo.id)}
            onMouseLeave={() => { setHoveredLogo(null); setTooltip(null) }}
          >
            {/* Label */}
            <div
              style={{
                width: LABEL_W,
                flexShrink: 0,
                paddingRight: 14,
                fontSize: 12,
                color: hoveredLogo === logo.id ? 'var(--c-ink)' : 'var(--c-dim)',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                transition: 'color 0.15s',
                fontWeight: hoveredLogo === logo.id ? 500 : 400,
              }}
              title={logo.name}
            >
              {logo.name}
            </div>

            {/* Track */}
            <div
              style={{
                flex: 1,
                height: ROW_H,
                background: hoveredLogo === logo.id ? 'var(--c-panel)' : 'transparent',
                border: `1px solid ${hoveredLogo === logo.id ? 'var(--c-wire)' : 'transparent'}`,
                borderRadius: 5,
                position: 'relative',
                transition: 'background 0.15s, border-color 0.15s',
                overflow: 'hidden',
              }}
            >
              {/* Tick grid lines */}
              {ticks.slice(1, -1).map((t, i) => (
                <div key={i} style={{
                  position: 'absolute',
                  left: `${t.pct}%`,
                  top: 0,
                  width: 1,
                  height: '100%',
                  background: 'var(--c-wire)',
                  opacity: 0.4,
                }} />
              ))}

              {/* Segments */}
              {logo.segments.map((seg, si) => {
                const left = toPct(seg.startTime)
                const width = Math.max(
                  (MIN_SEG_W / 8) * 0.1,  // relative min - will be enforced by minWidth
                  toPct(seg.endTime - seg.startTime)
                )
                const opacity = visibilityOpacity(seg.avgVisibility)

                return (
                  <div
                    key={si}
                    style={{
                      position: 'absolute',
                      left: `${left}%`,
                      width: `${width}%`,
                      minWidth: MIN_SEG_W,
                      top: '50%',
                      transform: 'translateY(-50%)',
                      height: 22,
                      background: `rgba(197,240,0,${opacity})`,
                      borderRadius: 3,
                      cursor: 'pointer',
                      transition: 'height 0.1s',
                    }}
                    onMouseEnter={e => {
                      const rect = (e.target as HTMLElement).getBoundingClientRect()
                      setTooltip({ seg, logoName: logo.name, x: rect.left + rect.width / 2, y: rect.top })
                    }}
                    onMouseLeave={() => setTooltip(null)}
                  />
                )
              })}
            </div>
          </div>
        ))}
      </div>

      {/* Tooltip */}
      {tooltip && (
        <div
          style={{
            position: 'fixed',
            left: tooltip.x,
            top: tooltip.y - 10,
            transform: 'translate(-50%, -100%)',
            background: 'var(--c-panel)',
            border: '1px solid var(--c-wire-s)',
            borderRadius: 7,
            padding: '10px 14px',
            fontSize: 12,
            zIndex: 1000,
            pointerEvents: 'none',
            minWidth: 170,
            boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
          }}
        >
          <div style={{ fontWeight: 600, marginBottom: 6, color: 'var(--c-spark)' }}>{tooltip.logoName}</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '3px 12px', color: 'var(--c-dim)' }}>
            <span>Start</span>
            <span className="num" style={{ color: 'var(--c-ink)' }}>{formatSeconds(tooltip.seg.startTime)}</span>
            <span>End</span>
            <span className="num" style={{ color: 'var(--c-ink)' }}>{formatSeconds(tooltip.seg.endTime)}</span>
            <span>Duration</span>
            <span className="num" style={{ color: 'var(--c-ink)' }}>{formatSeconds(tooltip.seg.endTime - tooltip.seg.startTime)}</span>
            <span>Visibility</span>
            <span className="num" style={{ color: 'var(--c-spark)' }}>{(tooltip.seg.avgVisibility * 100).toFixed(0)}%</span>
          </div>
        </div>
      )}
    </div>
  )
}
