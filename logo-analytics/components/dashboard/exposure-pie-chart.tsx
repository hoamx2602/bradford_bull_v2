'use client'

import { useMemo, useState } from 'react'
import type { AnalysisResult } from '@/lib/types'
import { getBrandColor } from '@/lib/mock-data'
import { formatCurrency } from '@/lib/utils'

interface Props {
  result: AnalysisResult
}

const SIZE = 320
const CENTER = SIZE / 2
const RADIUS = 120
const INNER_RADIUS = 72

export default function ExposurePieChart({ result }: Props) {
  const [hoveredId, setHoveredId] = useState<string | null>(null)

  const totalExposure = useMemo(
    () => result.logos.reduce((s, l) => s + l.totalExposureSeconds, 0),
    [result]
  )

  const slices = useMemo(() => {
    let startAngle = 0
    return result.logos.map(logo => {
      const fraction = logo.totalExposureSeconds / totalExposure
      const angle = fraction * 360
      const slice = {
        id: logo.id,
        name: logo.name,
        fraction,
        percentage: (fraction * 100).toFixed(1),
        startAngle,
        endAngle: startAngle + angle,
        color: getBrandColor(logo.id),
        emv: logo.emvUsd,
        exposure: logo.totalExposureSeconds,
      }
      startAngle += angle
      return slice
    })
  }, [result, totalExposure])

  // SVG arc path helper
  const arcPath = (startAngle: number, endAngle: number, outerR: number, innerR: number, explode = false) => {
    const toRad = (deg: number) => ((deg - 90) * Math.PI) / 180
    const midAngle = (startAngle + endAngle) / 2
    const offset = explode ? 6 : 0
    const dx = offset * Math.cos(toRad(midAngle))
    const dy = offset * Math.sin(toRad(midAngle))

    const outerStart = {
      x: CENTER + dx + outerR * Math.cos(toRad(startAngle)),
      y: CENTER + dy + outerR * Math.sin(toRad(startAngle)),
    }
    const outerEnd = {
      x: CENTER + dx + outerR * Math.cos(toRad(endAngle)),
      y: CENTER + dy + outerR * Math.sin(toRad(endAngle)),
    }
    const innerStart = {
      x: CENTER + dx + innerR * Math.cos(toRad(endAngle)),
      y: CENTER + dy + innerR * Math.sin(toRad(endAngle)),
    }
    const innerEnd = {
      x: CENTER + dx + innerR * Math.cos(toRad(startAngle)),
      y: CENTER + dy + innerR * Math.sin(toRad(startAngle)),
    }

    const largeArc = endAngle - startAngle > 180 ? 1 : 0

    return [
      `M ${outerStart.x.toFixed(2)} ${outerStart.y.toFixed(2)}`,
      `A ${outerR} ${outerR} 0 ${largeArc} 1 ${outerEnd.x.toFixed(2)} ${outerEnd.y.toFixed(2)}`,
      `L ${innerStart.x.toFixed(2)} ${innerStart.y.toFixed(2)}`,
      `A ${innerR} ${innerR} 0 ${largeArc} 0 ${innerEnd.x.toFixed(2)} ${innerEnd.y.toFixed(2)}`,
      'Z',
    ].join(' ')
  }

  const topBrand = slices.reduce((a, b) => (a.fraction > b.fraction ? a : b))

  return (
    <div style={{
      background: 'var(--c-panel)',
      border: '1px solid var(--c-wire)',
      borderRadius: 10,
      padding: '20px 16px',
    }}>
      <div style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--c-ink)', marginBottom: 2 }}>
          Exposure Share
        </div>
        <div style={{ fontSize: 12, color: 'var(--c-ghost)' }}>
          Proportion of total screen time per brand
        </div>
      </div>

      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 32,
        flexWrap: 'wrap',
        justifyContent: 'center',
      }}>
        {/* Doughnut */}
        <div style={{ position: 'relative', flexShrink: 0 }}>
          <svg width={SIZE} height={SIZE} viewBox={`0 0 ${SIZE} ${SIZE}`}>
            {/* Background ring */}
            <circle
              cx={CENTER} cy={CENTER} r={(RADIUS + INNER_RADIUS) / 2}
              fill="none" stroke="var(--c-wire)" strokeWidth={RADIUS - INNER_RADIUS}
              opacity="0.3"
            />

            {/* Slices */}
            {slices.map(slice => {
              const isHovered = hoveredId === slice.id
              const dimmed = hoveredId && !isHovered

              return (
                <path
                  key={slice.id}
                  d={arcPath(
                    slice.startAngle,
                    slice.endAngle,
                    isHovered ? RADIUS + 4 : RADIUS,
                    isHovered ? INNER_RADIUS - 2 : INNER_RADIUS,
                    isHovered,
                  )}
                  fill={slice.color}
                  opacity={dimmed ? 0.2 : 1}
                  style={{
                    transition: 'opacity 0.2s ease, d 0.2s ease',
                    cursor: 'pointer',
                    filter: isHovered ? `drop-shadow(0 0 12px ${slice.color}40)` : 'none',
                  }}
                  onMouseEnter={() => setHoveredId(slice.id)}
                  onMouseLeave={() => setHoveredId(null)}
                />
              )
            })}

            {/* Center text */}
            <text x={CENTER} y={CENTER - 8} textAnchor="middle" fill="var(--c-dim)" fontSize="10" fontWeight="500" letterSpacing="0.06em">
              TOP BRAND
            </text>
            <text x={CENTER} y={CENTER + 12} textAnchor="middle" fill="var(--c-spark)" fontSize="20" fontWeight="700">
              {topBrand.percentage}%
            </text>
            <text x={CENTER} y={CENTER + 28} textAnchor="middle" fill="var(--c-ghost)" fontSize="10">
              {topBrand.name}
            </text>
          </svg>
        </div>

        {/* Legend list */}
        <div style={{
          flex: 1,
          minWidth: 200,
          display: 'flex',
          flexDirection: 'column',
          gap: 4,
        }}>
          {slices.map(slice => {
            const isHovered = hoveredId === slice.id

            return (
              <div
                key={slice.id}
                onMouseEnter={() => setHoveredId(slice.id)}
                onMouseLeave={() => setHoveredId(null)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  padding: '7px 10px',
                  borderRadius: 6,
                  background: isHovered ? 'var(--c-hover)' : 'transparent',
                  transition: 'background 0.15s',
                  cursor: 'default',
                }}
              >
                <div style={{
                  width: 10,
                  height: 10,
                  borderRadius: 3,
                  background: slice.color,
                  flexShrink: 0,
                }} />

                <div style={{ flex: 1, fontSize: 12, color: isHovered ? 'var(--c-ink)' : 'var(--c-dim)', transition: 'color 0.15s' }}>
                  {slice.name}
                </div>

                <div className="num" style={{
                  fontSize: 12,
                  fontWeight: 600,
                  color: isHovered ? slice.color : 'var(--c-dim)',
                  minWidth: 44,
                  textAlign: 'right',
                  transition: 'color 0.15s',
                }}>
                  {slice.percentage}%
                </div>

                <div className="num" style={{
                  fontSize: 11,
                  color: 'var(--c-ghost)',
                  minWidth: 60,
                  textAlign: 'right',
                }}>
                  {formatCurrency(slice.emv)}
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
