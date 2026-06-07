'use client'

import { useMemo, useState, useCallback } from 'react'
import type { AnalysisResult } from '@/lib/types'
import { getBrandColor } from '@/lib/mock-data'
import { formatSeconds } from '@/lib/utils'

interface Props {
  result: AnalysisResult
}

interface TooltipData {
  x: number
  y: number
  minute: number
  values: { name: string; color: string; value: number }[]
}

const CHART_W = 900
const CHART_H = 340
const PAD = { top: 20, right: 30, bottom: 50, left: 65 }
const INNER_W = CHART_W - PAD.left - PAD.right
const INNER_H = CHART_H - PAD.top - PAD.bottom

export default function ExposureLineChart({ result }: Props) {
  const [hoveredLogo, setHoveredLogo] = useState<string | null>(null)
  const [hiddenLogos, setHiddenLogos] = useState<Set<string>>(new Set())
  const [tooltip, setTooltip] = useState<TooltipData | null>(null)

  const toggleLogo = (id: string) => {
    setHiddenLogos(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  // Build time-series data
  const { series, maxExposure, timeSteps } = useMemo(() => {
    const interval = 300 // 5 minutes
    const steps = Math.ceil(result.videoDurationSeconds / interval) + 1
    const timeSteps = Array.from({ length: steps }, (_, i) => i * interval)

    const logoSeries: Record<string, number[]> = {}
    let maxExp = 0

    for (const logo of result.logos) {
      const values: number[] = []

      for (const t of timeSteps) {
        const cumulative = logo.segments
          .filter(seg => seg.startTime < t)
          .reduce((sum, seg) => {
            const effectiveEnd = Math.min(seg.endTime, t)
            return sum + Math.max(0, effectiveEnd - seg.startTime) * seg.avgVisibility
          }, 0)

        values.push(Math.round(cumulative * 10) / 10)
        if (cumulative > maxExp) maxExp = cumulative
      }

      logoSeries[logo.id] = values
    }

    return { series: logoSeries, maxExposure: maxExp, timeSteps }
  }, [result])

  // Scale functions
  const xScale = useCallback((t: number) => PAD.left + (t / result.videoDurationSeconds) * INNER_W, [result.videoDurationSeconds])
  const yScale = useCallback((v: number) => PAD.top + INNER_H - (v / maxExposure) * INNER_H, [maxExposure])

  // Build SVG path
  const buildPath = useCallback((values: number[]) => {
    return values.map((v, i) => {
      const x = xScale(timeSteps[i])
      const y = yScale(v)
      return `${i === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`
    }).join(' ')
  }, [xScale, yScale, timeSteps])

  // X-axis ticks (every 15 min)
  const xTicks = useMemo(() => {
    const ticks: { x: number; label: string }[] = []
    for (let min = 0; min <= result.videoDurationSeconds / 60; min += 15) {
      ticks.push({
        x: xScale(min * 60),
        label: `${min}m`,
      })
    }
    return ticks
  }, [result.videoDurationSeconds, xScale])

  // Y-axis ticks
  const yTicks = useMemo(() => {
    const tickCount = 5
    const step = maxExposure / tickCount
    return Array.from({ length: tickCount + 1 }, (_, i) => ({
      y: yScale(i * step),
      label: formatSeconds(Math.round(i * step)),
    }))
  }, [maxExposure, yScale])

  // Handle mouse hover for tooltip
  const handleMouseMove = useCallback((e: React.MouseEvent<SVGSVGElement>) => {
    const svg = e.currentTarget
    const rect = svg.getBoundingClientRect()
    const mouseX = ((e.clientX - rect.left) / rect.width) * CHART_W
    const mouseY = ((e.clientY - rect.top) / rect.height) * CHART_H

    // Find the closest time step
    const time = ((mouseX - PAD.left) / INNER_W) * result.videoDurationSeconds
    if (time < 0 || time > result.videoDurationSeconds) {
      setTooltip(null)
      return
    }

    const stepIdx = Math.round(time / 300)
    if (stepIdx < 0 || stepIdx >= timeSteps.length) {
      setTooltip(null)
      return
    }

    const minute = timeSteps[stepIdx] / 60

    const values = result.logos
      .filter(l => !hiddenLogos.has(l.id))
      .map(l => ({
        name: l.name,
        color: getBrandColor(l.id),
        value: series[l.id]?.[stepIdx] ?? 0,
      }))
      .sort((a, b) => b.value - a.value)

    setTooltip({
      x: e.clientX,
      y: e.clientY,
      minute,
      values: values.slice(0, 5),
    })
  }, [result, series, timeSteps, hiddenLogos])

  return (
    <div>
      {/* Chart */}
      <div style={{
        background: 'var(--c-panel)',
        border: '1px solid var(--c-wire)',
        borderRadius: 10,
        padding: '20px 16px',
        overflow: 'hidden',
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 16,
        }}>
          <div>
            <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--c-ink)', marginBottom: 2 }}>
              Logo Exposure Over Time
            </div>
            <div style={{ fontSize: 12, color: 'var(--c-ghost)' }}>
              Cumulative visibility-weighted exposure per brand
            </div>
          </div>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <svg
            viewBox={`0 0 ${CHART_W} ${CHART_H}`}
            style={{ width: '100%', maxWidth: CHART_W, height: 'auto', display: 'block' }}
            onMouseMove={handleMouseMove}
            onMouseLeave={() => setTooltip(null)}
          >
            {/* Grid lines */}
            {yTicks.map((tick, i) => (
              <g key={`y-${i}`}>
                <line
                  x1={PAD.left} y1={tick.y}
                  x2={CHART_W - PAD.right} y2={tick.y}
                  stroke="var(--c-wire)" strokeWidth="0.5" strokeDasharray="4 4"
                />
                <text
                  x={PAD.left - 10} y={tick.y + 4}
                  textAnchor="end" fill="var(--c-ghost)" fontSize="10"
                  fontFamily="monospace"
                >
                  {tick.label}
                </text>
              </g>
            ))}

            {/* X-axis ticks */}
            {xTicks.map((tick, i) => (
              <g key={`x-${i}`}>
                <line
                  x1={tick.x} y1={PAD.top}
                  x2={tick.x} y2={CHART_H - PAD.bottom}
                  stroke="var(--c-wire)" strokeWidth="0.5" strokeDasharray="4 4"
                  opacity="0.5"
                />
                <text
                  x={tick.x} y={CHART_H - PAD.bottom + 20}
                  textAnchor="middle" fill="var(--c-ghost)" fontSize="10"
                  fontFamily="monospace"
                >
                  {tick.label}
                </text>
              </g>
            ))}

            {/* Axis labels */}
            <text
              x={CHART_W / 2} y={CHART_H - 8}
              textAnchor="middle" fill="var(--c-ghost)" fontSize="10"
              letterSpacing="0.06em"
            >
              TIME (MINUTES)
            </text>
            <text
              x={12} y={CHART_H / 2}
              textAnchor="middle" fill="var(--c-ghost)" fontSize="10"
              letterSpacing="0.06em"
              transform={`rotate(-90, 12, ${CHART_H / 2})`}
            >
              EXPOSURE
            </text>

            {/* Data lines */}
            {result.logos.map(logo => {
              if (hiddenLogos.has(logo.id)) return null
              const values = series[logo.id]
              if (!values) return null
              const color = getBrandColor(logo.id)
              const path = buildPath(values)
              const isHovered = hoveredLogo === logo.id
              const dimmed = hoveredLogo && !isHovered

              return (
                <path
                  key={logo.id}
                  d={path}
                  fill="none"
                  stroke={color}
                  strokeWidth={isHovered ? 3 : 1.8}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  opacity={dimmed ? 0.15 : 1}
                  style={{ transition: 'opacity 0.2s, stroke-width 0.2s' }}
                />
              )
            })}
          </svg>
        </div>

        {/* Legend */}
        <div style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: '6px 16px',
          marginTop: 16,
          paddingTop: 14,
          borderTop: '1px solid var(--c-wire)',
        }}>
          {result.logos.map(logo => {
            const color = getBrandColor(logo.id)
            const isHidden = hiddenLogos.has(logo.id)

            return (
              <button
                key={logo.id}
                onClick={() => toggleLogo(logo.id)}
                onMouseEnter={() => setHoveredLogo(logo.id)}
                onMouseLeave={() => setHoveredLogo(null)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  background: 'none',
                  border: 'none',
                  padding: '4px 6px',
                  borderRadius: 4,
                  fontSize: 11,
                  color: isHidden ? 'var(--c-ghost)' : 'var(--c-dim)',
                  cursor: 'pointer',
                  transition: 'color 0.15s',
                  textDecoration: isHidden ? 'line-through' : 'none',
                }}
              >
                <div style={{
                  width: 10,
                  height: 3,
                  borderRadius: 2,
                  background: isHidden ? 'var(--c-ghost)' : color,
                  transition: 'background 0.15s',
                }} />
                {logo.name}
              </button>
            )
          })}
        </div>
      </div>

      {/* Floating tooltip */}
      {tooltip && (
        <div style={{
          position: 'fixed',
          left: tooltip.x + 16,
          top: tooltip.y - 10,
          background: 'var(--c-panel)',
          border: '1px solid var(--c-wire-s)',
          borderRadius: 8,
          padding: '10px 14px',
          fontSize: 12,
          zIndex: 1000,
          pointerEvents: 'none',
          minWidth: 180,
          boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
        }}>
          <div style={{
            fontSize: 10,
            fontWeight: 600,
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
            color: 'var(--c-ghost)',
            marginBottom: 8,
          }}>
            {tooltip.minute.toFixed(0)} min
          </div>
          {tooltip.values.map((v, i) => (
            <div key={i} style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: 12,
              padding: '2px 0',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <div style={{
                  width: 8,
                  height: 8,
                  borderRadius: '50%',
                  background: v.color,
                  flexShrink: 0,
                }} />
                <span style={{ color: 'var(--c-dim)' }}>{v.name}</span>
              </div>
              <span className="num" style={{ color: 'var(--c-ink)', fontWeight: 500 }}>
                {formatSeconds(v.value)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
