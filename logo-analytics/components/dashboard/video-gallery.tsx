'use client'

import { useState } from 'react'
import type { MatchEntry } from '@/lib/types'
import { formatCurrency, formatSeconds, formatDate } from '@/lib/utils'

interface Props {
  matches: MatchEntry[]
  selectedId: string
  onSelect: (id: string) => void
}

// Generate gradient backgrounds for video thumbnails
const GRADIENTS = [
  'linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)',
  'linear-gradient(135deg, #0d1117 0%, #161b22 50%, #21262d 100%)',
  'linear-gradient(135deg, #1b1b2f 0%, #162447 50%, #1f4068 100%)',
  'linear-gradient(135deg, #0c0c1d 0%, #1a1a3e 50%, #2d2d5e 100%)',
]

export default function VideoGallery({ matches, selectedId, onSelect }: Props) {
  const [hoveredId, setHoveredId] = useState<string | null>(null)

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
      gap: 20,
    }}>
      {matches.map((match, i) => {
        const isSelected = match.id === selectedId
        const isHovered = match.id === hoveredId

        return (
          <div
            key={match.id}
            className="video-card"
            onClick={() => onSelect(match.id)}
            onMouseEnter={() => setHoveredId(match.id)}
            onMouseLeave={() => setHoveredId(null)}
            style={{
              background: 'var(--c-panel)',
              border: `1px solid ${isSelected ? 'var(--c-spark)' : 'var(--c-wire)'}`,
              borderRadius: 12,
              overflow: 'hidden',
              cursor: 'pointer',
              position: 'relative',
            }}
          >
            {/* Selected indicator */}
            {isSelected && (
              <div style={{
                position: 'absolute',
                top: 12,
                right: 12,
                width: 24,
                height: 24,
                borderRadius: '50%',
                background: 'var(--c-spark)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                zIndex: 10,
              }}>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#000" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              </div>
            )}

            {/* Thumbnail */}
            <div style={{
              height: 160,
              background: GRADIENTS[i % GRADIENTS.length],
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              position: 'relative',
              overflow: 'hidden',
            }}>
              {/* Decorative grid lines */}
              <div style={{
                position: 'absolute',
                inset: 0,
                backgroundImage: `
                  linear-gradient(rgba(197,240,0,0.03) 1px, transparent 1px),
                  linear-gradient(90deg, rgba(197,240,0,0.03) 1px, transparent 1px)
                `,
                backgroundSize: '24px 24px',
              }} />

              {/* Play button */}
              <div style={{
                width: 52,
                height: 52,
                borderRadius: '50%',
                background: isHovered ? 'rgba(197,240,0,0.2)' : 'rgba(255,255,255,0.08)',
                border: `1.5px solid ${isHovered ? 'var(--c-spark)' : 'rgba(255,255,255,0.15)'}`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                transition: 'all 0.2s ease',
                backdropFilter: 'blur(8px)',
              }}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill={isHovered ? 'var(--c-spark)' : 'rgba(255,255,255,0.6)'} stroke="none">
                  <polygon points="8 5 19 12 8 19 8 5" />
                </svg>
              </div>

              {/* Duration badge */}
              <div style={{
                position: 'absolute',
                bottom: 10,
                right: 10,
                background: 'rgba(0,0,0,0.7)',
                backdropFilter: 'blur(4px)',
                borderRadius: 5,
                padding: '3px 8px',
                fontSize: 11,
                fontFamily: 'monospace',
                color: 'var(--c-dim)',
                letterSpacing: '0.02em',
              }}>
                {formatSeconds(match.durationSeconds)}
              </div>
            </div>

            {/* Info */}
            <div style={{ padding: '14px 16px 16px' }}>
              <div style={{
                fontSize: 13,
                fontWeight: 600,
                color: 'var(--c-ink)',
                marginBottom: 6,
                lineHeight: 1.4,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                display: '-webkit-box',
                WebkitLineClamp: 2,
                WebkitBoxOrient: 'vertical',
              }}>
                {match.eventName}
              </div>

              <div style={{
                fontSize: 11,
                color: 'var(--c-ghost)',
                marginBottom: 12,
              }}>
                {formatDate(match.date)}
              </div>

              {/* Stats row */}
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                padding: '10px 0 0',
                borderTop: '1px solid var(--c-wire)',
              }}>
                <div>
                  <div style={{ fontSize: 10, color: 'var(--c-ghost)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 2 }}>
                    Logos
                  </div>
                  <div className="num" style={{ fontSize: 14, fontWeight: 600, color: 'var(--c-dim)' }}>
                    {match.logoCount}
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: 10, color: 'var(--c-ghost)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 2 }}>
                    Total EMV
                  </div>
                  <div className="num" style={{ fontSize: 14, fontWeight: 600, color: 'var(--c-spark)' }}>
                    {formatCurrency(match.totalEmv)}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
