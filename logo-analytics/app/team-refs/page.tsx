'use client'

// Manual team selection — web port of team_detection/ref_build.py.
// Extract isolated player crops from an uploaded video, verify/fix the
// auto-suggested team per crop, save as the global refs used by every
// subsequent analysis (overrides the per-video auto bootstrap).

import { useCallback, useEffect, useState } from 'react'
import Nav from '@/components/nav'
import ClusterPicker, {
  clusterCounts, expandClusterAssignments, initClusterLabels, swapClusterLabels,
  type ClusterLabel,
} from '@/components/cluster-picker'
import {
  clusterRefCrops, deleteTeamRefs, extractRefCrops, getTeamRefsStatus,
  listRefVideos, saveTeamRefs,
  type RefCluster, type RefCrop, type RefVideo, type TeamRefsStatus,
} from '@/lib/api'

type Label = ClusterLabel
type Mode = 'cluster' | 'crop'

const LABEL_STYLE: Record<string, { border: string; tag: string; bg: string }> = {
  target: { border: '#FFBE0A', tag: 'BRADFORD', bg: 'rgba(255,190,10,0.14)' },
  other: { border: '#9aa0a6', tag: 'OTHER', bg: 'rgba(154,160,166,0.14)' },
  ignore: { border: 'var(--c-wire)', tag: 'IGNORE', bg: 'transparent' },
}

export default function TeamRefsPage() {
  const [status, setStatus] = useState<TeamRefsStatus | null>(null)
  const [videos, setVideos] = useState<RefVideo[]>([])
  const [videoKey, setVideoKey] = useState('')
  const [kit, setKit] = useState<'away' | 'home'>('away')
  const [mode, setMode] = useState<Mode>('cluster')
  const [extractId, setExtractId] = useState('')
  const [crops, setCrops] = useState<RefCrop[]>([])
  const [labels, setLabels] = useState<Label[]>([])
  // Cluster mode: the kit clusters + the team chosen for each cluster id.
  const [clusters, setClusters] = useState<RefCluster[]>([])
  const [clusterLabels, setClusterLabels] = useState<Record<number, Label>>({})
  const [busy, setBusy] = useState<'' | 'extract' | 'save'>('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  const refresh = useCallback(() => {
    getTeamRefsStatus().then(setStatus).catch(() => setStatus(null))
    listRefVideos().then(v => {
      setVideos(v)
      setVideoKey(k => k || v[0]?.storageKey || '')
    }).catch(() => setVideos([]))
  }, [])
  useEffect(refresh, [refresh])

  const resetSelection = () => {
    setCrops([]); setLabels([]); setClusters([]); setClusterLabels({}); setExtractId('')
  }

  const onExtract = async () => {
    if (!videoKey) return
    setBusy('extract'); setError(''); setMessage(''); resetSelection()
    try {
      const r = await extractRefCrops(videoKey, kit)
      setExtractId(r.extractId)
      setCrops(r.crops)
      setLabels(r.crops.map(c => c.suggested))
      if (mode === 'cluster') {
        const c = await clusterRefCrops(r.extractId)
        setClusters(c.clusters)
        setClusterLabels(initClusterLabels(c.clusters))
        setMessage(`${r.crops.length} crops grouped into ${c.clusters.length} kit clusters in ${r.tookSeconds}s `
          + `— confirm which cluster is the target team, then save.`)
      } else {
        setMessage(`${r.crops.length} crops extracted in ${r.tookSeconds}s — click any wrong ones to fix, then save.`)
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy('')
    }
  }

  // ── Per-crop mode ──────────────────────────────────────────────────────────
  // Click cycles: target -> other -> ignore -> target
  const cycle = (i: number) => {
    setLabels(ls => ls.map((l, j) => {
      if (j !== i) return l
      return l === 'target' ? 'other' : l === 'other' ? null : 'target'
    }))
  }

  const swap = () => setLabels(ls => ls.map(l =>
    l === 'target' ? 'other' : l === 'other' ? 'target' : l))

  // ── Cluster mode ───────────────────────────────────────────────────────────
  const setClusterLabel = (id: number, label: Label) =>
    setClusterLabels(m => ({ ...m, [id]: label }))

  const swapClusters = () => setClusterLabels(swapClusterLabels)

  const onSave = async () => {
    setBusy('save'); setError(''); setMessage('')
    try {
      const assignments = mode === 'cluster'
        ? expandClusterAssignments(clusters, crops.length, clusterLabels)
        : labels
      const r = await saveTeamRefs(extractId, assignments)
      setMessage(`Refs saved — ${r.nTarget} Bradford / ${r.nOther} other crops `
        + `(colour weight ${r.wColor}). All future analyses use these references.`)
      resetSelection()
      refresh()
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy('')
    }
  }

  const onDelete = async () => {
    if (!window.confirm('Delete the saved team references? Analyses fall back to per-video auto bootstrap.')) return
    await deleteTeamRefs()
    refresh()
  }

  // Crop counts per team — drives the save guard (backend needs >=3 each).
  const counts = clusterCounts(clusters, clusterLabels)
  const nTarget = mode === 'cluster' ? counts.target : labels.filter(l => l === 'target').length
  const nOther = mode === 'cluster' ? counts.other : labels.filter(l => l === 'other').length
  const hasSelection = mode === 'cluster' ? clusters.length > 0 : crops.length > 0

  return (
    <div style={{ minHeight: '100vh', background: 'var(--c-canvas)' }}>
      <Nav />
      <div style={{ maxWidth: 1280, margin: '0 auto', padding: '28px 24px 80px' }}>
        <h1 style={{ fontSize: 20, fontWeight: 700, margin: '0 0 6px' }}>Team References</h1>
        <p style={{ fontSize: 12.5, color: 'var(--c-dim)', margin: '0 0 20px', maxWidth: 760 }}>
          Pick a match video and confirm which players are the Bradford kit. <b>By cluster</b> auto-groups
          the crops by kit — just pick which group is the target team and which is the opponent (one or two
          clicks); <b>By crop</b> lets you label each crop individually for tricky clips. The saved references
          drive the team filter for every analysis — more reliable than the automatic per-video guess.
          Rebuild them whenever the kit or opponent changes.
        </p>

        {/* Current refs status */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 12, marginBottom: 22,
          padding: '10px 14px', background: 'var(--c-panel)',
          border: '1px solid var(--c-wire)', borderRadius: 10, fontSize: 12.5,
        }}>
          <span style={{
            width: 8, height: 8, borderRadius: '50%',
            background: status?.exists ? 'var(--c-spark)' : 'var(--c-wire-s)',
          }} />
          {status?.exists ? (
            <>
              <span style={{ color: 'var(--c-ink)' }}>
                Active references — {status.mode === 'manual' ? 'manually confirmed' : `auto (${status.mode})`}
                {status.nTarget != null && <> · <span className="num">{status.nTarget}</span> Bradford / <span className="num">{status.nOther}</span> other crops</>}
              </span>
              <span style={{ color: 'var(--c-ghost)' }}>
                built {status.builtAt ? new Date(status.builtAt).toLocaleString() : ''}
              </span>
              <button onClick={onDelete} style={{
                marginLeft: 'auto', fontSize: 11.5, color: '#e08585', background: 'transparent',
                border: '1px solid var(--c-wire)', borderRadius: 7, padding: '4px 10px', cursor: 'pointer',
              }}>
                Delete refs
              </button>
            </>
          ) : (
            <span style={{ color: 'var(--c-dim)' }}>
              No saved references — analyses currently auto-detect the kit per video.
            </span>
          )}
        </div>

        {/* Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap', marginBottom: 18 }}>
          <select
            value={videoKey}
            onChange={e => setVideoKey(e.target.value)}
            style={{
              background: 'var(--c-panel)', color: 'var(--c-ink)', fontSize: 12.5,
              border: '1px solid var(--c-wire)', borderRadius: 8, padding: '8px 10px', minWidth: 320,
            }}
          >
            {videos.length === 0 && <option value="">No uploaded videos yet</option>}
            {videos.map(v => (
              <option key={v.storageKey} value={v.storageKey}>
                {v.eventName || v.videoName} — {new Date(v.createdAt).toLocaleDateString()}
              </option>
            ))}
          </select>

          <div style={{ display: 'flex', border: '1px solid var(--c-wire)', borderRadius: 8, overflow: 'hidden' }}>
            {([['cluster', 'By cluster'], ['crop', 'By crop']] as const).map(([m, lbl]) => (
              <button key={m} onClick={() => { setMode(m); resetSelection(); setMessage('') }} style={{
                fontSize: 12, padding: '8px 14px', cursor: 'pointer', border: 'none',
                background: mode === m ? 'var(--c-hover)' : 'transparent',
                color: mode === m ? 'var(--c-ink)' : 'var(--c-dim)',
                fontWeight: mode === m ? 700 : 500,
              }}>
                {lbl}
              </button>
            ))}
          </div>

          <div style={{ display: 'flex', border: '1px solid var(--c-wire)', borderRadius: 8, overflow: 'hidden' }}>
            {(['away', 'home'] as const).map(k => (
              <button key={k} onClick={() => setKit(k)} style={{
                fontSize: 12, padding: '8px 14px', cursor: 'pointer', border: 'none',
                background: kit === k ? 'var(--c-hover)' : 'transparent',
                color: kit === k ? 'var(--c-ink)' : 'var(--c-dim)',
                fontWeight: kit === k ? 700 : 500,
              }}>
                {k === 'away' ? 'Away (black)' : 'Home (white)'}
              </button>
            ))}
          </div>

          <button
            onClick={onExtract}
            disabled={!videoKey || busy !== ''}
            style={{
              fontSize: 12.5, fontWeight: 700, padding: '8px 18px', borderRadius: 8,
              border: 'none', cursor: busy ? 'wait' : 'pointer',
              background: 'var(--c-spark)', color: '#000', opacity: !videoKey || busy ? 0.6 : 1,
            }}
          >
            {busy === 'extract' ? 'Extracting…' : 'Extract crops'}
          </button>
        </div>

        {error && (
          <div style={{ marginBottom: 14, padding: '9px 13px', borderRadius: 8, fontSize: 12.5, color: '#e08585', background: 'rgba(224,133,133,0.08)', border: '1px solid rgba(224,133,133,0.3)' }}>
            {error}
          </div>
        )}
        {message && (
          <div style={{ marginBottom: 14, padding: '9px 13px', borderRadius: 8, fontSize: 12.5, color: 'var(--c-dim)', background: 'var(--c-panel)', border: '1px solid var(--c-wire)' }}>
            {message}
          </div>
        )}

        {/* Selection toolbar (shared by both modes) */}
        {hasSelection && (
          <>
            <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 12, fontSize: 12.5 }}>
              {(['target', 'other', 'ignore'] as const).map(k => (
                <span key={k} style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--c-dim)' }}>
                  <span style={{ width: 11, height: 11, borderRadius: 3, background: LABEL_STYLE[k].border }} />
                  {k === 'target' ? `Bradford (${nTarget})` : k === 'other' ? `Other (${nOther})` : 'Ignore'}
                </span>
              ))}
              <span style={{ color: 'var(--c-ghost)' }}>
                {mode === 'cluster' ? '· set each cluster’s team' : '· click a crop to cycle its label'}
              </span>
              <button onClick={mode === 'cluster' ? swapClusters : swap} style={{
                marginLeft: 'auto', fontSize: 12, padding: '6px 12px', borderRadius: 7, cursor: 'pointer',
                background: 'var(--c-panel)', color: 'var(--c-ink)', border: '1px solid var(--c-wire)',
              }}>
                Swap teams
              </button>
              <button
                onClick={onSave}
                disabled={busy !== '' || nTarget < 3 || nOther < 3}
                title={nTarget < 3 || nOther < 3 ? 'Need at least 3 crops per team' : ''}
                style={{
                  fontSize: 12.5, fontWeight: 700, padding: '7px 18px', borderRadius: 7,
                  border: 'none', cursor: 'pointer',
                  background: 'var(--c-spark)', color: '#000',
                  opacity: busy || nTarget < 3 || nOther < 3 ? 0.55 : 1,
                }}
              >
                {busy === 'save' ? 'Saving…' : 'Save references'}
              </button>
            </div>

            {/* Cluster cards */}
            {mode === 'cluster' && (
              <ClusterPicker
                clusters={clusters} crops={crops}
                labels={clusterLabels} onSet={setClusterLabel}
              />
            )}

            {/* Per-crop grid */}
            {mode === 'crop' && (
              <div style={{
                display: 'grid', gap: 10,
                gridTemplateColumns: 'repeat(auto-fill, minmax(118px, 1fr))',
              }}>
                {crops.map((c, i) => {
                  const st = LABEL_STYLE[labels[i] ?? 'ignore']
                  return (
                    <button key={i} onClick={() => cycle(i)} style={{
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
                        {st.tag}
                      </span>
                    </button>
                  )
                })}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
