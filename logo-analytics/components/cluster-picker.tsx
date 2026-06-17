'use client'

// Cluster-based team picker: auto-grouped kit clusters, each shown with a few
// representative crops and a Target / Opponent / Ignore selector. Shared by the
// Team References page and the inline upload team step.

import type { RefCluster, RefCrop } from '@/lib/api'

export type ClusterLabel = 'target' | 'other' | null

const STYLE: Record<string, { border: string; bg: string }> = {
  target: { border: '#FFBE0A', bg: 'rgba(255,190,10,0.14)' },
  other: { border: '#9aa0a6', bg: 'rgba(154,160,166,0.14)' },
  ignore: { border: 'var(--c-wire)', bg: 'transparent' },
}

// ── Helpers (kept here so both callers share one source of truth) ────────────

export function initClusterLabels(clusters: RefCluster[]): Record<number, ClusterLabel> {
  return Object.fromEntries(clusters.map(cl => [cl.id, cl.suggested] as [number, ClusterLabel]))
}

export function swapClusterLabels(
  m: Record<number, ClusterLabel>,
): Record<number, ClusterLabel> {
  return Object.fromEntries(Object.entries(m).map(([id, l]): [string, ClusterLabel] =>
    [id, l === 'target' ? 'other' : l === 'other' ? 'target' : l]))
}

export function clusterCounts(
  clusters: RefCluster[],
  labels: Record<number, ClusterLabel>,
): { target: number; other: number } {
  let target = 0
  let other = 0
  for (const cl of clusters) {
    if (labels[cl.id] === 'target') target += cl.size
    else if (labels[cl.id] === 'other') other += cl.size
  }
  return { target, other }
}

/** Expand the cluster -> team choice into a per-crop assignments array. */
export function expandClusterAssignments(
  clusters: RefCluster[],
  nCrops: number,
  labels: Record<number, ClusterLabel>,
): ClusterLabel[] {
  const out: ClusterLabel[] = new Array(nCrops).fill(null)
  for (const cl of clusters) {
    const team = labels[cl.id] ?? null
    for (const idx of cl.members) out[idx] = team
  }
  return out
}

// ── Component ────────────────────────────────────────────────────────────────

interface Props {
  clusters: RefCluster[]
  crops: RefCrop[] // index-aligned with cluster.members / cluster.samples
  labels: Record<number, ClusterLabel>
  onSet: (id: number, label: ClusterLabel) => void
}

export default function ClusterPicker({ clusters, crops, labels, onSet }: Props) {
  return (
    <div style={{
      display: 'grid', gap: 14,
      gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))',
    }}>
      {clusters.map((cl, n) => {
        const team = labels[cl.id] ?? null
        const st = STYLE[team ?? 'ignore']
        return (
          <div key={cl.id} style={{
            border: `2px solid ${st.border}`, borderRadius: 11, background: st.bg,
            padding: 12, display: 'flex', flexDirection: 'column', gap: 10,
          }}>
            <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between' }}>
              <span style={{ fontSize: 12.5, fontWeight: 700, color: 'var(--c-ink)' }}>
                Cluster {n + 1}
              </span>
              <span style={{ fontSize: 11.5, color: 'var(--c-dim)' }}>
                <span className="num">{cl.size}</span> crops
              </span>
            </div>
            <div style={{ display: 'grid', gap: 5, gridTemplateColumns: 'repeat(3, 1fr)' }}>
              {cl.samples.map(idx => (
                // eslint-disable-next-line @next/next/no-img-element
                <img key={idx} src={crops[idx]?.thumb} alt={`cluster ${n} crop ${idx}`}
                  style={{ width: '100%', display: 'block', borderRadius: 6 }} />
              ))}
            </div>
            <div style={{ display: 'flex', border: '1px solid var(--c-wire)', borderRadius: 8, overflow: 'hidden' }}>
              {([['target', 'Target'], ['other', 'Opponent'], [null, 'Ignore']] as const).map(([val, lbl]) => {
                const active = team === val
                const accent = val ? STYLE[val].border : 'var(--c-wire-s)'
                return (
                  <button key={lbl} onClick={() => onSet(cl.id, val)} style={{
                    flex: 1, fontSize: 11.5, padding: '6px 4px', cursor: 'pointer', border: 'none',
                    borderRight: lbl === 'Ignore' ? 'none' : '1px solid var(--c-wire)',
                    background: active ? accent : 'transparent',
                    color: active ? '#000' : 'var(--c-dim)', fontWeight: active ? 700 : 500,
                  }}>
                    {lbl}
                  </button>
                )
              })}
            </div>
          </div>
        )
      })}
    </div>
  )
}
