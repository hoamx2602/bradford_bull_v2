'use client'

import { useState } from 'react'
import type { LogoResult } from '@/lib/types'
import { formatSeconds, formatCurrency } from '@/lib/utils'

type SortKey = keyof Pick<LogoResult,
  'name' | 'totalExposureSeconds' | 'qualityExposureSeconds' | 'avgVisibilityScore' | 'segmentCount' | 'emvUsd'>
type Dir = 'asc' | 'desc'

interface Props {
  logos: LogoResult[]
  onHighlight?: (id: string | null) => void
}

const COLS: { key: SortKey; label: string; align: 'left' | 'right' }[] = [
  { key: 'name',                    label: 'Brand',             align: 'left' },
  { key: 'totalExposureSeconds',    label: 'Exposure',          align: 'right' },
  { key: 'qualityExposureSeconds',  label: 'Quality Exp.',      align: 'right' },
  { key: 'avgVisibilityScore',      label: 'Visibility',        align: 'right' },
  { key: 'segmentCount',            label: 'Segments',          align: 'right' },
  { key: 'emvUsd',                  label: 'EMV',               align: 'right' },
]

export default function LogoTable({ logos, onHighlight }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>('emvUsd')
  const [dir, setDir] = useState<Dir>('desc')
  const [hovered, setHovered] = useState<string | null>(null)

  const handleSort = (key: SortKey) => {
    if (key === sortKey) setDir(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortKey(key); setDir('desc') }
  }

  const sorted = [...logos].sort((a, b) => {
    const av = a[sortKey], bv = b[sortKey]
    if (typeof av === 'string' && typeof bv === 'string')
      return dir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av)
    return dir === 'asc' ? (av as number) - (bv as number) : (bv as number) - (av as number)
  })

  const maxEmv = Math.max(...logos.map(l => l.emvUsd))

  const thStyle = (key: SortKey, align: 'left' | 'right'): React.CSSProperties => ({
    padding: '10px 14px',
    textAlign: align,
    fontSize: 11,
    fontWeight: 600,
    letterSpacing: '0.08em',
    textTransform: 'uppercase',
    color: sortKey === key ? 'var(--c-ink)' : 'var(--c-dim)',
    cursor: 'pointer',
    whiteSpace: 'nowrap',
    userSelect: 'none',
    transition: 'color 0.15s',
    borderBottom: '1px solid var(--c-wire)',
  })

  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead>
          <tr>
            <th style={{ ...thStyle('name', 'left'), paddingLeft: 16, width: 40, textAlign: 'center', color: 'var(--c-ghost)' }}>#</th>
            {COLS.map(col => (
              <th
                key={col.key}
                style={thStyle(col.key, col.align)}
                onClick={() => handleSort(col.key)}
              >
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                  {col.label}
                  {sortKey === col.key && (
                    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                      {dir === 'desc'
                        ? <polyline points="6 9 12 15 18 9" />
                        : <polyline points="18 15 12 9 6 15" />}
                    </svg>
                  )}
                </span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((logo, i) => (
            <tr
              key={logo.id}
              onMouseEnter={() => { setHovered(logo.id); onHighlight?.(logo.id) }}
              onMouseLeave={() => { setHovered(null); onHighlight?.(null) }}
              style={{
                background: hovered === logo.id ? 'var(--c-panel)' : 'transparent',
                borderBottom: '1px solid var(--c-wire)',
                transition: 'background 0.12s',
                cursor: 'default',
              }}
            >
              {/* Rank */}
              <td style={{ padding: '12px 14px', textAlign: 'center', color: 'var(--c-ghost)', fontSize: 12 }} className="num">
                {i + 1}
              </td>

              {/* Brand name */}
              <td style={{ padding: '12px 14px', fontWeight: 500 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <div style={{
                    width: 28, height: 28, borderRadius: 6,
                    background: 'var(--c-spark-bg)',
                    border: '1px solid var(--c-wire)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    flexShrink: 0,
                    fontSize: 10, fontWeight: 700, color: 'var(--c-spark)',
                  }}>
                    {logo.name.slice(0, 2).toUpperCase()}
                  </div>
                  {logo.name}
                </div>
              </td>

              {/* Total exposure */}
              <td style={{ padding: '12px 14px', textAlign: 'right' }} className="num">
                {formatSeconds(logo.totalExposureSeconds)}
              </td>

              {/* Quality exposure */}
              <td style={{ padding: '12px 14px', textAlign: 'right' }} className="num">
                {formatSeconds(logo.qualityExposureSeconds)}
              </td>

              {/* Visibility */}
              <td style={{ padding: '12px 14px', textAlign: 'right' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 8 }}>
                  <div style={{ width: 48, height: 3, background: 'var(--c-wire)', borderRadius: 2, overflow: 'hidden' }}>
                    <div style={{
                      height: '100%',
                      width: `${logo.avgVisibilityScore * 100}%`,
                      background: 'var(--c-spark)',
                      borderRadius: 2,
                    }} />
                  </div>
                  <span className="num" style={{ fontSize: 12 }}>
                    {(logo.avgVisibilityScore * 100).toFixed(0)}%
                  </span>
                </div>
              </td>

              {/* Segments */}
              <td style={{ padding: '12px 14px', textAlign: 'right', color: 'var(--c-dim)' }} className="num">
                {logo.segmentCount}
              </td>

              {/* EMV */}
              <td style={{ padding: '12px 14px', textAlign: 'right' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 8 }}>
                  {/* Spark bar */}
                  <div style={{ width: 60, height: 3, background: 'var(--c-wire)', borderRadius: 2, overflow: 'hidden' }}>
                    <div style={{
                      height: '100%',
                      width: `${(logo.emvUsd / maxEmv) * 100}%`,
                      background: 'var(--c-spark)',
                      borderRadius: 2,
                    }} />
                  </div>
                  <span className="num" style={{ fontWeight: 600, color: 'var(--c-spark)', minWidth: 70, textAlign: 'right' }}>
                    {formatCurrency(logo.emvUsd)}
                  </span>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
