'use client'

// Per-crop team picker: every extracted player crop is shown; clicking cycles
// its label target -> other -> ignore. Shared by the Team References page and
// the inline upload team step.

import type { RefCrop } from '@/lib/api'

export type CropLabel = 'target' | 'other' | null

const STYLE: Record<string, { border: string; bg: string }> = {
  target: { border: '#FFBE0A', bg: 'rgba(255,190,10,0.14)' },
  other: { border: '#9aa0a6', bg: 'rgba(154,160,166,0.14)' },
  ignore: { border: 'var(--c-wire)', bg: 'transparent' },
}

// ── Helpers (one source of truth for both callers) ───────────────────────────

export function cycleCropLabel(l: CropLabel): CropLabel {
  return l === 'target' ? 'other' : l === 'other' ? null : 'target'
}

export function swapCropLabels(ls: CropLabel[]): CropLabel[] {
  return ls.map(l => (l === 'target' ? 'other' : l === 'other' ? 'target' : l))
}

export function cropCounts(ls: CropLabel[]): { target: number; other: number } {
  return {
    target: ls.filter(l => l === 'target').length,
    other: ls.filter(l => l === 'other').length,
  }
}

// ── Component ────────────────────────────────────────────────────────────────

interface Props {
  crops: RefCrop[]
  labels: CropLabel[]
  onCycle: (i: number) => void
  /** Tag shown on target crops (e.g. "BRADFORD" or "TARGET"). */
  targetTag?: string
}

export default function CropPicker({ crops, labels, onCycle, targetTag = 'TARGET' }: Props) {
  const tagOf = (l: CropLabel) => (l === 'target' ? targetTag : l === 'other' ? 'OTHER' : 'IGNORE')
  return (
    <div style={{
      display: 'grid', gap: 10,
      gridTemplateColumns: 'repeat(auto-fill, minmax(118px, 1fr))',
    }}>
      {crops.map((c, i) => {
        const st = STYLE[labels[i] ?? 'ignore']
        return (
          <button key={i} onClick={() => onCycle(i)} style={{
            position: 'relative', padding: 0, cursor: 'pointer',
            border: `2.5px solid ${st.border}`, borderRadius: 9,
            background: st.bg, overflow: 'hidden', lineHeight: 0,
          }}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={c.thumb} alt={`crop ${i}`} style={{ width: '100%', display: 'block' }} />
            <span style={{
              position: 'absolute', left: 4, bottom: 4, fontSize: 9.5, fontWeight: 700,
              letterSpacing: '0.06em', color: '#000', background: st.border,
              padding: '1.5px 6px', borderRadius: 5, lineHeight: 1.5,
            }}>
              {tagOf(labels[i] ?? null)}
            </span>
          </button>
        )
      })}
    </div>
  )
}
