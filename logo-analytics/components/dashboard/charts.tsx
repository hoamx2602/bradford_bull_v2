'use client'

// Compact SVG chart library — zero dependencies, shared dark-panel styling.
// All charts are interactive (hover tooltips, legend toggles) and scale to
// their container via viewBox.

import { useMemo, useState } from 'react'

// Stable palette used everywhere a brand needs a colour outside a single
// match (portfolio views). Index-based so the same brand keeps its colour
// across tabs as long as the brand list is sorted consistently.
export const PALETTE = [
  '#C5F000', '#00D4FF', '#FF6B6B', '#A78BFA', '#F59E0B',
  '#34D399', '#F472B6', '#60A5FA', '#FBBF24', '#A3E635',
  '#2DD4BF', '#FB923C', '#E879F9', '#94A3B8', '#FACC15', '#4ADE80',
]
export const colorAt = (i: number) => PALETTE[i % PALETTE.length]

const panelStyle: React.CSSProperties = {
  background: 'var(--c-panel)',
  border: '1px solid var(--c-wire)',
  borderRadius: 10,
  padding: '18px 18px 14px',
}

const tooltipStyle: React.CSSProperties = {
  position: 'absolute',
  pointerEvents: 'none',
  background: 'rgba(10,10,14,0.95)',
  border: '1px solid var(--c-wire-s)',
  borderRadius: 7,
  padding: '8px 11px',
  fontSize: 11,
  zIndex: 20,
  whiteSpace: 'nowrap',
}

// ── Donut chart — share-of-voice style ──────────────────────────────

export interface DonutDatum { label: string; value: number; color: string }

function arcPath(cx: number, cy: number, r0: number, r1: number, a0: number, a1: number): string {
  const large = a1 - a0 > Math.PI ? 1 : 0
  const x0o = cx + r1 * Math.cos(a0), y0o = cy + r1 * Math.sin(a0)
  const x1o = cx + r1 * Math.cos(a1), y1o = cy + r1 * Math.sin(a1)
  const x1i = cx + r0 * Math.cos(a1), y1i = cy + r0 * Math.sin(a1)
  const x0i = cx + r0 * Math.cos(a0), y0i = cy + r0 * Math.sin(a0)
  return `M ${x0o} ${y0o} A ${r1} ${r1} 0 ${large} 1 ${x1o} ${y1o} L ${x1i} ${y1i} A ${r0} ${r0} 0 ${large} 0 ${x0i} ${y0i} Z`
}

export function DonutChart({ data, format, centerLabel }: {
  data: DonutDatum[]
  format: (v: number) => string
  centerLabel?: string
}) {
  const [hovered, setHovered] = useState<number | null>(null)
  const total = data.reduce((s, d) => s + d.value, 0)

  const slices = useMemo(() => {
    let a = -Math.PI / 2
    return data.map(d => {
      const span = total ? (d.value / total) * Math.PI * 2 : 0
      const s = { ...d, a0: a, a1: a + span }
      a += span
      return s
    })
  }, [data, total])

  const active = hovered != null ? data[hovered] : null

  return (
    <div style={{ ...panelStyle, display: 'flex', alignItems: 'center', gap: 24, flexWrap: 'wrap' }}>
      <svg viewBox="0 0 220 220" style={{ width: 220, height: 220, flexShrink: 0 }}>
        {slices.map((s, i) => {
          const isH = hovered === i
          const grow = isH ? 4 : 0
          return s.a1 > s.a0 ? (
            <path
              key={s.label}
              d={arcPath(110, 110, 64 - grow / 2, 96 + grow, s.a0, s.a1)}
              fill={s.color}
              opacity={hovered == null || isH ? (isH ? 1 : 0.92) : 0.25}
              style={{ transition: 'opacity 0.15s', cursor: 'pointer' }}
              onMouseEnter={() => setHovered(i)}
              onMouseLeave={() => setHovered(null)}
            />
          ) : null
        })}
        <text x="110" y="103" textAnchor="middle" style={{ fill: 'var(--c-ink)', fontSize: 17, fontWeight: 700 }}>
          {active ? format(active.value) : format(total)}
        </text>
        <text x="110" y="123" textAnchor="middle" style={{ fill: 'var(--c-ghost)', fontSize: 10 }}>
          {active ? `${active.label} · ${total ? (active.value / total * 100).toFixed(1) : 0}%` : (centerLabel ?? 'Total')}
        </text>
      </svg>

      <div style={{ flex: 1, minWidth: 200, display: 'flex', flexDirection: 'column', gap: 4 }}>
        {data.map((d, i) => (
          <div
            key={d.label}
            onMouseEnter={() => setHovered(i)}
            onMouseLeave={() => setHovered(null)}
            style={{
              display: 'flex', alignItems: 'center', gap: 9,
              padding: '5px 9px', borderRadius: 6, cursor: 'pointer',
              background: hovered === i ? 'var(--c-hover)' : 'transparent',
              transition: 'background 0.15s',
            }}
          >
            <span style={{ width: 10, height: 10, borderRadius: 3, background: d.color, flexShrink: 0 }} />
            <span style={{ flex: 1, fontSize: 12, color: 'var(--c-dim)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {d.label}
            </span>
            <span className="num" style={{ fontSize: 12, fontWeight: 600, color: 'var(--c-ink)' }}>
              {format(d.value)}
            </span>
            <span className="num" style={{ fontSize: 11, color: 'var(--c-ghost)', width: 44, textAlign: 'right' }}>
              {total ? (d.value / total * 100).toFixed(1) : 0}%
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Trend chart — multi-series line across matches (categorical x) ──

export interface TrendSeries { name: string; color: string; values: (number | null)[] }

export function TrendChart({ series, xLabels, format, yLabel }: {
  series: TrendSeries[]
  xLabels: string[]
  format: (v: number) => string
  yLabel?: string
}) {
  const [hidden, setHidden] = useState<Set<string>>(new Set())
  const [hoverIdx, setHoverIdx] = useState<number | null>(null)

  const W = 900, H = 300
  const PAD = { top: 16, right: 24, bottom: 42, left: 70 }
  const IW = W - PAD.left - PAD.right
  const IH = H - PAD.top - PAD.bottom

  const visible = series.filter(s => !hidden.has(s.name))
  const maxV = Math.max(1, ...visible.flatMap(s => s.values.filter((v): v is number => v != null)))
  const n = xLabels.length
  const xAt = (i: number) => PAD.left + (n <= 1 ? IW / 2 : (i / (n - 1)) * IW)
  const yAt = (v: number) => PAD.top + IH - (v / maxV) * IH

  const toggle = (name: string) => setHidden(prev => {
    const next = new Set(prev)
    if (next.has(name)) next.delete(name); else next.add(name)
    return next
  })

  return (
    <div style={{ ...panelStyle, position: 'relative' }}>
      {/* Legend */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px 14px', marginBottom: 10 }}>
        {series.map(s => {
          const off = hidden.has(s.name)
          return (
            <button
              key={s.name}
              onClick={() => toggle(s.name)}
              style={{
                display: 'flex', alignItems: 'center', gap: 6,
                background: 'none', border: 'none', cursor: 'pointer',
                fontSize: 11, color: off ? 'var(--c-ghost)' : 'var(--c-dim)',
                opacity: off ? 0.5 : 1, padding: '2px 4px',
              }}
            >
              <span style={{ width: 16, height: 3, borderRadius: 2, background: s.color }} />
              {s.name}
            </button>
          )
        })}
      </div>

      <svg
        viewBox={`0 0 ${W} ${H}`}
        style={{ width: '100%', height: 'auto', display: 'block' }}
        onMouseMove={e => {
          const rect = e.currentTarget.getBoundingClientRect()
          const mx = ((e.clientX - rect.left) / rect.width) * W
          const idx = Math.round(((mx - PAD.left) / IW) * (n - 1))
          setHoverIdx(idx >= 0 && idx < n ? idx : null)
        }}
        onMouseLeave={() => setHoverIdx(null)}
      >
        {/* Grid + y ticks */}
        {Array.from({ length: 5 }, (_, i) => {
          const v = (maxV / 4) * i
          return (
            <g key={i}>
              <line x1={PAD.left} x2={W - PAD.right} y1={yAt(v)} y2={yAt(v)} stroke="var(--c-wire)" strokeWidth="1" />
              <text x={PAD.left - 9} y={yAt(v) + 3.5} textAnchor="end" style={{ fill: 'var(--c-ghost)', fontSize: 10 }}>
                {format(v)}
              </text>
            </g>
          )
        })}
        {/* X labels */}
        {xLabels.map((l, i) => (
          <text key={i} x={xAt(i)} y={H - PAD.bottom + 18} textAnchor="middle" style={{ fill: 'var(--c-ghost)', fontSize: 10 }}>
            {l}
          </text>
        ))}
        {yLabel && (
          <text x={14} y={PAD.top + IH / 2} textAnchor="middle" transform={`rotate(-90 14 ${PAD.top + IH / 2})`} style={{ fill: 'var(--c-ghost)', fontSize: 10 }}>
            {yLabel}
          </text>
        )}

        {/* Hover guide */}
        {hoverIdx != null && (
          <line x1={xAt(hoverIdx)} x2={xAt(hoverIdx)} y1={PAD.top} y2={PAD.top + IH} stroke="var(--c-wire-s)" strokeWidth="1" strokeDasharray="3 3" />
        )}

        {/* Series */}
        {visible.map(s => {
          const pts = s.values
            .map((v, i) => (v == null ? null : `${xAt(i).toFixed(1)},${yAt(v).toFixed(1)}`))
            .filter((p): p is string => p != null)
          return (
            <g key={s.name}>
              <polyline points={pts.join(' ')} fill="none" stroke={s.color} strokeWidth="2.2" strokeLinejoin="round" strokeLinecap="round" />
              {s.values.map((v, i) => v == null ? null : (
                <circle
                  key={i}
                  cx={xAt(i)} cy={yAt(v)}
                  r={hoverIdx === i ? 5 : 3}
                  fill={s.color}
                  stroke="var(--c-panel)" strokeWidth="1.5"
                  style={{ transition: 'r 0.1s' }}
                />
              ))}
            </g>
          )
        })}
      </svg>

      {/* Tooltip */}
      {hoverIdx != null && (
        <div style={{
          ...tooltipStyle,
          left: `${(xAt(hoverIdx) / W) * 100}%`,
          top: 40,
          transform: xAt(hoverIdx) > W * 0.6 ? 'translateX(-105%)' : 'translateX(12px)',
        }}>
          <div style={{ color: 'var(--c-ink)', fontWeight: 600, marginBottom: 5 }}>{xLabels[hoverIdx]}</div>
          {visible.map(s => s.values[hoverIdx] == null ? null : (
            <div key={s.name} style={{ display: 'flex', alignItems: 'center', gap: 7, marginTop: 2 }}>
              <span style={{ width: 8, height: 8, borderRadius: 2, background: s.color }} />
              <span style={{ color: 'var(--c-dim)' }}>{s.name}</span>
              <span className="num" style={{ color: 'var(--c-ink)', fontWeight: 600, marginLeft: 'auto', paddingLeft: 12 }}>
                {format(s.values[hoverIdx] as number)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Heatmap — brand × match matrix ──────────────────────────────────

export function HeatmapGrid({ rows, cols, values, format, onCellClick }: {
  rows: string[]                       // brand names
  cols: string[]                       // match labels
  values: number[][]                   // [row][col]
  format: (v: number) => string
  onCellClick?: (row: number, col: number) => void
}) {
  const [hover, setHover] = useState<{ r: number; c: number } | null>(null)
  const maxV = Math.max(1, ...values.flat())

  return (
    <div style={{ ...panelStyle, overflowX: 'auto' }}>
      <table style={{ borderCollapse: 'separate', borderSpacing: 3, width: '100%' }}>
        <thead>
          <tr>
            <th style={{ minWidth: 130 }} />
            {cols.map((c, i) => (
              <th key={i} style={{ fontSize: 10, fontWeight: 600, color: 'var(--c-ghost)', padding: '0 4px 6px', textAlign: 'center', letterSpacing: '0.03em', minWidth: 64 }}>
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, ri) => (
            <tr key={ri}>
              <td style={{ fontSize: 12, fontWeight: 600, color: 'var(--c-dim)', paddingRight: 10, whiteSpace: 'nowrap' }}>{r}</td>
              {cols.map((_, ci) => {
                const v = values[ri]?.[ci] ?? 0
                const t = v / maxV
                const isH = hover?.r === ri && hover?.c === ci
                return (
                  <td
                    key={ci}
                    onMouseEnter={() => setHover({ r: ri, c: ci })}
                    onMouseLeave={() => setHover(null)}
                    onClick={() => onCellClick?.(ri, ci)}
                    title={`${r} · ${cols[ci]}: ${format(v)}`}
                    style={{
                      background: v > 0 ? `rgba(197,240,0,${0.06 + t * 0.72})` : 'var(--c-hover)',
                      borderRadius: 5,
                      padding: '8px 6px',
                      textAlign: 'center',
                      fontSize: 11,
                      fontWeight: 600,
                      color: t > 0.45 ? '#000' : 'var(--c-dim)',
                      cursor: onCellClick ? 'pointer' : 'default',
                      outline: isH ? '1.5px solid var(--c-spark)' : 'none',
                      transition: 'outline 0.1s',
                    }}
                    className="num"
                  >
                    {v > 0 ? format(v) : '—'}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ── Radar chart — brand profile vs benchmark ────────────────────────

export interface RadarSeries { name: string; color: string; values: number[] }  // 0..1 per axis

export function RadarChart({ axes, series }: { axes: string[]; series: RadarSeries[] }) {
  const [hovered, setHovered] = useState<string | null>(null)
  const W = 360, H = 320, CX = W / 2, CY = H / 2 + 6, R = 108
  const n = axes.length
  const angle = (i: number) => -Math.PI / 2 + (i / n) * Math.PI * 2
  const pt = (i: number, v: number) => [CX + R * v * Math.cos(angle(i)), CY + R * v * Math.sin(angle(i))]

  return (
    <div style={{ ...panelStyle, display: 'flex', alignItems: 'center', gap: 18, flexWrap: 'wrap' }}>
      <svg viewBox={`0 0 ${W} ${H}`} style={{ width: 340, maxWidth: '100%', height: 'auto', flexShrink: 0 }}>
        {/* Rings */}
        {[0.25, 0.5, 0.75, 1].map(rv => (
          <polygon
            key={rv}
            points={axes.map((_, i) => pt(i, rv).join(',')).join(' ')}
            fill="none" stroke="var(--c-wire)" strokeWidth="1"
          />
        ))}
        {/* Spokes + labels */}
        {axes.map((a, i) => {
          const [x, y] = pt(i, 1)
          const [lx, ly] = pt(i, 1.22)
          return (
            <g key={a}>
              <line x1={CX} y1={CY} x2={x} y2={y} stroke="var(--c-wire)" strokeWidth="1" />
              <text x={lx} y={ly + 3} textAnchor="middle" style={{ fill: 'var(--c-ghost)', fontSize: 9.5 }}>{a}</text>
            </g>
          )
        })}
        {/* Series polygons */}
        {series.map(s => {
          const dim = hovered != null && hovered !== s.name
          return (
            <polygon
              key={s.name}
              points={s.values.map((v, i) => pt(i, Math.max(0.02, Math.min(1, v))).join(',')).join(' ')}
              fill={s.color}
              fillOpacity={dim ? 0.04 : 0.16}
              stroke={s.color}
              strokeWidth={dim ? 1 : 2}
              strokeOpacity={dim ? 0.35 : 1}
              style={{ transition: 'all 0.15s' }}
            />
          )
        })}
      </svg>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6, minWidth: 140 }}>
        {series.map(s => (
          <div
            key={s.name}
            onMouseEnter={() => setHovered(s.name)}
            onMouseLeave={() => setHovered(null)}
            style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: 'var(--c-dim)', cursor: 'default' }}
          >
            <span style={{ width: 11, height: 11, borderRadius: 3, background: s.color }} />
            {s.name}
          </div>
        ))}
        <div style={{ fontSize: 10.5, color: 'var(--c-ghost)', marginTop: 8, lineHeight: 1.6 }}>
          Each axis normalised to the best performer in scope.
        </div>
      </div>
    </div>
  )
}

// ── Scatter — segment quality map (duration × visibility) ───────────

export interface ScatterPoint { x: number; y: number; color: string; label: string; sub?: string }

export function ScatterChart({ points, xLabel, yLabel, formatX, formatY }: {
  points: ScatterPoint[]
  xLabel: string
  yLabel: string
  formatX: (v: number) => string
  formatY: (v: number) => string
}) {
  const [hover, setHover] = useState<number | null>(null)
  const W = 900, H = 320
  const PAD = { top: 16, right: 24, bottom: 46, left: 64 }
  const IW = W - PAD.left - PAD.right
  const IH = H - PAD.top - PAD.bottom

  const maxX = Math.max(1e-6, ...points.map(p => p.x)) * 1.06
  const maxY = Math.max(1e-6, ...points.map(p => p.y)) * 1.08
  const xAt = (v: number) => PAD.left + (v / maxX) * IW
  const yAt = (v: number) => PAD.top + IH - (v / maxY) * IH
  const hp = hover != null ? points[hover] : null

  return (
    <div style={{ ...panelStyle, position: 'relative' }}>
      <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height: 'auto', display: 'block' }}>
        {Array.from({ length: 5 }, (_, i) => {
          const v = (maxY / 4) * i
          return (
            <g key={`y${i}`}>
              <line x1={PAD.left} x2={W - PAD.right} y1={yAt(v)} y2={yAt(v)} stroke="var(--c-wire)" strokeWidth="1" />
              <text x={PAD.left - 9} y={yAt(v) + 3.5} textAnchor="end" style={{ fill: 'var(--c-ghost)', fontSize: 10 }}>{formatY(v)}</text>
            </g>
          )
        })}
        {Array.from({ length: 6 }, (_, i) => {
          const v = (maxX / 5) * i
          return (
            <text key={`x${i}`} x={xAt(v)} y={H - PAD.bottom + 18} textAnchor="middle" style={{ fill: 'var(--c-ghost)', fontSize: 10 }}>
              {formatX(v)}
            </text>
          )
        })}
        <text x={PAD.left + IW / 2} y={H - 6} textAnchor="middle" style={{ fill: 'var(--c-ghost)', fontSize: 10 }}>{xLabel}</text>
        <text x={14} y={PAD.top + IH / 2} textAnchor="middle" transform={`rotate(-90 14 ${PAD.top + IH / 2})`} style={{ fill: 'var(--c-ghost)', fontSize: 10 }}>
          {yLabel}
        </text>

        {points.map((p, i) => (
          <circle
            key={i}
            cx={xAt(p.x)} cy={yAt(p.y)}
            r={hover === i ? 7 : 4.5}
            fill={p.color}
            fillOpacity={hover == null || hover === i ? 0.85 : 0.25}
            stroke={hover === i ? '#fff' : 'transparent'}
            strokeWidth="1"
            style={{ cursor: 'pointer', transition: 'fill-opacity 0.12s, r 0.12s' }}
            onMouseEnter={() => setHover(i)}
            onMouseLeave={() => setHover(null)}
          />
        ))}
      </svg>

      {hp && (
        <div style={{
          ...tooltipStyle,
          left: `${(xAt(hp.x) / W) * 100}%`,
          top: `${(yAt(hp.y) / H) * 100}%`,
          transform: `translate(${xAt(hp.x) > W * 0.6 ? '-105%' : '12px'}, -50%)`,
        }}>
          <div style={{ color: 'var(--c-ink)', fontWeight: 600 }}>{hp.label}</div>
          {hp.sub && <div style={{ color: 'var(--c-ghost)', marginTop: 2 }}>{hp.sub}</div>}
          <div style={{ color: 'var(--c-dim)', marginTop: 2 }}>
            {formatX(hp.x)} · {formatY(hp.y)}
          </div>
        </div>
      )}
    </div>
  )
}
