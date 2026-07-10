'use client'

import { useCallback, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import Nav from '@/components/nav'
import ClusterPicker, {
  clusterCounts, expandClusterAssignments, initClusterLabels, swapClusterLabels,
  type ClusterLabel,
} from '@/components/cluster-picker'
import CropPicker, {
  cropCounts, cycleCropLabel, swapCropLabels, type CropLabel,
} from '@/components/crop-picker'
import {
  buildTeamRefs, clusterRefCrops, createJob, extractRefCrops, uploadVideo,
  type RefCluster, type RefCrop,
} from '@/lib/api'

const PLACEMENTS = [
  { value: 'live-tv', label: 'Live Broadcast TV', mult: 1.0 },
  { value: 'live-stream', label: 'Live Stream', mult: 0.85 },
  { value: 'highlight', label: 'Highlight Clip', mult: 1.4 },
  { value: 'social', label: 'Social Media', mult: 0.7 },
]

type Phase = 'form' | 'team'
type TeamMode = 'crop' | 'cluster'

export default function UploadPage() {
  const router = useRouter()
  const inputRef = useRef<HTMLInputElement>(null)

  const [phase, setPhase] = useState<Phase>('form')
  const [file, setFile] = useState<File | null>(null)
  const [dragging, setDragging] = useState(false)
  const [eventName, setEventName] = useState('')
  const [audience, setAudience] = useState('2400000')
  const [placement, setPlacement] = useState('live-tv')
  const [cpm, setCpm] = useState('22')
  const [kit, setKit] = useState('away')

  const [busy, setBusy] = useState<'' | 'upload' | 'submit'>('')
  const [error, setError] = useState<string | null>(null)

  // Team-selection step (populated after the video is uploaded).
  const [teamMode, setTeamMode] = useState<TeamMode>('crop')
  const [storageKey, setStorageKey] = useState('')
  const [videoName, setVideoName] = useState('')
  const [extractId, setExtractId] = useState('')
  const [crops, setCrops] = useState<RefCrop[]>([])
  const [labels, setLabels] = useState<CropLabel[]>([])
  const [clusters, setClusters] = useState<RefCluster[]>([])
  const [clusterLabels, setClusterLabels] = useState<Record<number, ClusterLabel>>({})
  const [teamNote, setTeamNote] = useState('')

  const accept = (f: File) => {
    if (!f.type.startsWith('video/') && !/\.(mp4|mov|avi|mkv)$/i.test(f.name)) return
    setFile(f)
  }

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
    const f = e.dataTransfer.files[0]
    if (f) accept(f)
  }, [])

  const onDragOver = (e: React.DragEvent) => { e.preventDefault(); setDragging(true) }
  const onDragLeave = () => setDragging(false)

  const formatFileSize = (bytes: number) => {
    if (bytes > 1e9) return `${(bytes / 1e9).toFixed(1)} GB`
    return `${(bytes / 1e6).toFixed(0)} MB`
  }

  const buildMeta = () => ({
    eventName: eventName.trim(),
    audienceSize: parseInt(audience),
    placementType: PLACEMENTS.find(p => p.value === placement)?.label ?? 'Live Broadcast TV',
    cpmBase: parseFloat(cpm),
    kit,
  })

  const canContinue = !!(file && eventName.trim() && audience && cpm) && busy === ''

  // Step 1 -> 2: upload the video, then cluster its players for team picking.
  const onContinue = async () => {
    if (!canContinue || !file) return
    setBusy('upload'); setError(''); setTeamNote('')
    // Keep metadata for the processing/dashboard screens to display immediately.
    localStorage.setItem('sl_meta', JSON.stringify({ videoName: file.name, eventName: eventName.trim() }))
    try {
      const up = await uploadVideo(file)
      setStorageKey(up.storageKey)
      setVideoName(up.videoName)
      // Crop extraction + clustering is best-effort: if it yields nothing
      // usable, the user can still start with automatic team detection.
      try {
        const ex = await extractRefCrops(up.storageKey, kit)
        setExtractId(ex.extractId)
        setCrops(ex.crops)
        setLabels(ex.crops.map(c => c.suggested))
        // Cluster too, so the user can switch to the faster by-cluster view.
        const cl = await clusterRefCrops(ex.extractId)
        setClusters(cl.clusters)
        setClusterLabels(initClusterLabels(cl.clusters))
        setTeamNote(`${ex.crops.length} player crops extracted in ${ex.tookSeconds}s — `
          + `click any wrong ones to fix the suggested team, then start.`)
      } catch (e) {
        setCrops([]); setLabels([]); setClusters([]); setExtractId('')
        setTeamNote(`Couldn't extract player crops (${e instanceof Error ? e.message : String(e)}). `
          + `Start with automatic detection, or go back and try a different clip.`)
      }
      setPhase('team')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Upload failed')
    } finally {
      setBusy('')
    }
  }

  const counts = teamMode === 'cluster'
    ? clusterCounts(clusters, clusterLabels)
    : cropCounts(labels)
  const validTeams = crops.length > 0 && counts.target >= 3 && counts.other >= 3

  // Step 2 -> processing: build per-job refs from the chosen teams (unless
  // skipping to auto-detect), create the job, hand off to the polling screen.
  const start = async (useTeams: boolean) => {
    setBusy('submit'); setError('')
    try {
      let teamRefsKey: string | undefined
      if (useTeams && crops.length > 0) {
        const assignments = teamMode === 'cluster'
          ? expandClusterAssignments(clusters, crops.length, clusterLabels)
          : labels
        teamRefsKey = (await buildTeamRefs(extractId, assignments)).refsKey
      }
      const { jobId } = await createJob({ storageKey, videoName, teamRefsKey }, buildMeta())
      localStorage.setItem('sl_job', jobId)
      router.push('/processing')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not start analysis')
      setBusy('')
    }
  }

  const cycleCrop = (i: number) =>
    setLabels(ls => ls.map((l, j) => (j === i ? cycleCropLabel(l) : l)))
  const setClusterLabel = (id: number, label: ClusterLabel) =>
    setClusterLabels(m => ({ ...m, [id]: label }))
  const swapTeams = () => {
    if (teamMode === 'cluster') setClusterLabels(swapClusterLabels)
    else setLabels(swapCropLabels)
  }

  const label: React.CSSProperties = {
    fontSize: 11,
    fontWeight: 600,
    letterSpacing: '0.1em',
    textTransform: 'uppercase',
    color: 'var(--c-dim)',
    display: 'block',
    marginBottom: 6,
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Nav />

      <main style={{ flex: 1, display: 'flex', alignItems: phase === 'team' ? 'flex-start' : 'center', justifyContent: 'center', padding: '48px 24px' }}>
        {phase === 'form' ? (
          <div style={{ width: '100%', maxWidth: 560 }}>

            {/* Hero text */}
            <div style={{ marginBottom: 40 }}>
              <h1 style={{ fontSize: 36, fontWeight: 700, lineHeight: 1.15, letterSpacing: '-0.02em', margin: 0 }}>
                Sponsor visibility<br />
                <span style={{ color: 'var(--c-spark)' }}>measured precisely.</span>
              </h1>
              <p style={{ color: 'var(--c-dim)', marginTop: 14, marginBottom: 0, fontSize: 14, lineHeight: 1.7 }}>
                Upload a broadcast video and receive a full breakdown of every brand's
                screen time, visibility quality, and equivalent media value.
              </p>
            </div>

            {/* Drop zone */}
            <div
              onClick={() => !file && inputRef.current?.click()}
              onDrop={onDrop}
              onDragOver={onDragOver}
              onDragLeave={onDragLeave}
              style={{
                border: `1.5px dashed ${dragging ? 'var(--c-spark)' : file ? 'var(--c-wire-s)' : 'var(--c-wire)'}`,
                borderRadius: 10,
                padding: '28px 24px',
                marginBottom: 24,
                background: dragging ? 'var(--c-spark-bg)' : 'var(--c-panel)',
                cursor: file ? 'default' : 'pointer',
                transition: 'border-color 0.15s, background 0.15s',
              }}
            >
              <input
                ref={inputRef}
                type="file"
                accept="video/*,.mp4,.mov,.avi,.mkv"
                style={{ display: 'none' }}
                onChange={e => { if (e.target.files?.[0]) accept(e.target.files[0]) }}
              />

              {file ? (
                <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                  <div style={{
                    width: 44, height: 44, borderRadius: 8,
                    background: 'var(--c-spark-bg)',
                    border: '1px solid var(--c-wire)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                  }}>
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--c-spark)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                      <polygon points="23 7 16 12 23 17 23 7" /><rect x="1" y="5" width="15" height="14" rx="2" ry="2" />
                    </svg>
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{file.name}</div>
                    <div style={{ color: 'var(--c-dim)', fontSize: 12, marginTop: 2 }}>
                      {formatFileSize(file.size)} · {file.type || 'video'}
                    </div>
                  </div>
                  <button
                    onClick={e => { e.stopPropagation(); setFile(null) }}
                    style={{
                      background: 'none', border: '1px solid var(--c-wire)', borderRadius: 6,
                      color: 'var(--c-dim)', padding: '6px 12px', fontSize: 12, flexShrink: 0,
                      transition: 'border-color 0.15s, color 0.15s',
                    }}
                    onMouseEnter={e => { (e.target as HTMLButtonElement).style.borderColor = 'var(--c-wire-s)'; (e.target as HTMLButtonElement).style.color = 'var(--c-ink)' }}
                    onMouseLeave={e => { (e.target as HTMLButtonElement).style.borderColor = 'var(--c-wire)'; (e.target as HTMLButtonElement).style.color = 'var(--c-dim)' }}
                  >
                    Change
                  </button>
                </div>
              ) : (
                <div style={{ textAlign: 'center' }}>
                  <div style={{ marginBottom: 12 }}>
                    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="var(--c-ghost)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ display: 'inline-block' }}>
                      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="17 8 12 3 7 8" /><line x1="12" y1="3" x2="12" y2="15" />
                    </svg>
                  </div>
                  <div style={{ fontWeight: 500, marginBottom: 4 }}>Drop video here</div>
                  <div style={{ color: 'var(--c-dim)', fontSize: 13 }}>or click to browse</div>
                  <div style={{ color: 'var(--c-ghost)', fontSize: 12, marginTop: 10 }}>MP4 · MOV · AVI · MKV &nbsp;·&nbsp; Max 2 GB</div>
                </div>
              )}
            </div>

            {/* Form */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 18, marginBottom: 28 }}>
              <div>
                <label style={label}>Event Name</label>
                <input
                  type="text"
                  placeholder="e.g. Arsenal vs Chelsea — Premier League"
                  value={eventName}
                  onChange={e => setEventName(e.target.value)}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                <div>
                  <label style={label}>Audience Size</label>
                  <input
                    type="number"
                    placeholder="2400000"
                    value={audience}
                    onChange={e => setAudience(e.target.value)}
                  />
                </div>
                <div style={{ position: 'relative' }}>
                  <label style={label}>Placement Type</label>
                  <select value={placement} onChange={e => setPlacement(e.target.value)}>
                    {PLACEMENTS.map(p => <option key={p.value} value={p.value}>{p.label}</option>)}
                  </select>
                  <svg style={{ position: 'absolute', right: 12, top: '68%', transform: 'translateY(-50%)', pointerEvents: 'none' }}
                    width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="var(--c-dim)" strokeWidth="2" strokeLinecap="round">
                    <polyline points="6 9 12 15 18 9" />
                  </svg>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                <div>
                  <label style={label}>CPM Base (USD)</label>
                  <input
                    type="number"
                    placeholder="22"
                    value={cpm}
                    onChange={e => setCpm(e.target.value)}
                  />
                </div>
                <div style={{ position: 'relative' }}>
                  <label style={label}>Bradford Kit</label>
                  <select value={kit} onChange={e => setKit(e.target.value)}>
                    <option value="away">Away — Black</option>
                    <option value="home">Home — White</option>
                  </select>
                  <svg style={{ position: 'absolute', right: 12, top: '68%', transform: 'translateY(-50%)', pointerEvents: 'none' }}
                    width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="var(--c-dim)" strokeWidth="2" strokeLinecap="round">
                    <polyline points="6 9 12 15 18 9" />
                  </svg>
                </div>
              </div>
            </div>

            {/* Continue to team selection */}
            <button
              onClick={onContinue}
              disabled={!canContinue}
              style={{
                width: '100%',
                padding: '14px 24px',
                background: canContinue ? 'var(--c-spark)' : 'var(--c-panel)',
                color: canContinue ? '#000' : 'var(--c-ghost)',
                border: `1px solid ${canContinue ? 'transparent' : 'var(--c-wire)'}`,
                borderRadius: 8,
                fontWeight: 700,
                fontSize: 14,
                letterSpacing: '0.04em',
                transition: 'background 0.15s, opacity 0.15s',
                cursor: canContinue ? 'pointer' : 'not-allowed',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 8,
              }}
            >
              {busy === 'upload' ? 'Uploading & grouping players…' : 'Continue to team selection'}
              {busy !== 'upload' && (
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="5" y1="12" x2="19" y2="12" /><polyline points="12 5 19 12 12 19" />
                </svg>
              )}
            </button>

            {error && (
              <p style={{ textAlign: 'center', color: '#FF6B6B', fontSize: 12, marginTop: 12 }}>
                {error}
              </p>
            )}

            <p style={{ textAlign: 'center', color: 'var(--c-ghost)', fontSize: 12, marginTop: 16 }}>
              Next: confirm which players are Bradford to sharpen team detection.
            </p>
          </div>
        ) : (
          // ── Team-selection step ──────────────────────────────────────────────
          <div style={{ width: '100%', maxWidth: 1100 }} className="slide-up">
            <div style={{ marginBottom: 18 }}>
              <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--c-spark)', marginBottom: 8 }}>
                Step 2 · Team selection
              </div>
              <h2 style={{ fontSize: 22, fontWeight: 700, margin: 0, letterSpacing: '-0.01em' }}>
                {eventName || 'Pick the target team'}
              </h2>
              <p style={{ color: 'var(--c-dim)', fontSize: 13, marginTop: 8, maxWidth: 760, lineHeight: 1.6 }}>
                Mark which players are <b>Target</b> (Bradford) and which are the <b>Opponent</b> — this
                trains the team filter for this video so logo attribution is more accurate. Label each crop
                individually, or switch to <b>By cluster</b> to pick whole kit groups at once. Or skip to let
                the system detect teams automatically.
              </p>
            </div>

            {teamNote && (
              <div style={{ marginBottom: 14, padding: '9px 13px', borderRadius: 8, fontSize: 12.5, color: 'var(--c-dim)', background: 'var(--c-panel)', border: '1px solid var(--c-wire)' }}>
                {teamNote}
              </div>
            )}
            {error && (
              <div style={{ marginBottom: 14, padding: '9px 13px', borderRadius: 8, fontSize: 12.5, color: '#e08585', background: 'rgba(224,133,133,0.08)', border: '1px solid rgba(224,133,133,0.3)' }}>
                {error}
              </div>
            )}

            {crops.length > 0 && (
              <>
                <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 12, fontSize: 12.5, flexWrap: 'wrap' }}>
                  {/* Mode toggle */}
                  <div style={{ display: 'flex', border: '1px solid var(--c-wire)', borderRadius: 8, overflow: 'hidden' }}>
                    {([['crop', 'Each crop'], ['cluster', 'By cluster']] as const).map(([m, lbl]) => (
                      <button key={m} onClick={() => setTeamMode(m)} style={{
                        fontSize: 12, padding: '6px 12px', cursor: 'pointer', border: 'none',
                        background: teamMode === m ? 'var(--c-hover)' : 'transparent',
                        color: teamMode === m ? 'var(--c-ink)' : 'var(--c-dim)',
                        fontWeight: teamMode === m ? 700 : 500,
                      }}>
                        {lbl}
                      </button>
                    ))}
                  </div>
                  <span style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--c-dim)' }}>
                    <span style={{ width: 11, height: 11, borderRadius: 3, background: '#FFBE0A' }} />
                    Target ({counts.target})
                  </span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--c-dim)' }}>
                    <span style={{ width: 11, height: 11, borderRadius: 3, background: '#9aa0a6' }} />
                    Opponent ({counts.other})
                  </span>
                  <span style={{ color: 'var(--c-ghost)' }}>
                    {teamMode === 'crop' ? '· click a crop to cycle target → opponent → ignore' : '· set each cluster’s team'}
                  </span>
                  <button onClick={swapTeams} style={{
                    marginLeft: 'auto', fontSize: 12, padding: '6px 12px', borderRadius: 7, cursor: 'pointer',
                    background: 'var(--c-panel)', color: 'var(--c-ink)', border: '1px solid var(--c-wire)',
                  }}>
                    Swap teams
                  </button>
                </div>

                {teamMode === 'crop' ? (
                  <CropPicker crops={crops} labels={labels} onCycle={cycleCrop} targetTag="BRADFORD" />
                ) : (
                  <ClusterPicker
                    clusters={clusters} crops={crops}
                    labels={clusterLabels} onSet={setClusterLabel}
                  />
                )}
              </>
            )}

            {/* Actions */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 24 }}>
              <button
                onClick={() => { setPhase('form'); setError(''); setBusy('') }}
                disabled={busy !== ''}
                style={{
                  fontSize: 12.5, padding: '10px 18px', borderRadius: 8, cursor: 'pointer',
                  background: 'transparent', color: 'var(--c-dim)', border: '1px solid var(--c-wire)',
                }}
              >
                ← Back
              </button>
              <button
                onClick={() => start(false)}
                disabled={busy !== ''}
                style={{
                  fontSize: 12.5, padding: '10px 18px', borderRadius: 8, cursor: 'pointer',
                  background: 'transparent', color: 'var(--c-dim)', border: '1px solid var(--c-wire)',
                }}
              >
                {busy === 'submit' ? 'Starting…' : 'Skip — auto-detect'}
              </button>
              <button
                onClick={() => start(true)}
                disabled={busy !== '' || !validTeams}
                title={!validTeams ? 'Mark at least 3 crops as Target and 3 as Opponent' : ''}
                style={{
                  marginLeft: 'auto', fontSize: 13, fontWeight: 700, padding: '11px 26px', borderRadius: 8,
                  border: 'none', cursor: busy ? 'wait' : 'pointer',
                  background: 'var(--c-spark)', color: '#000',
                  opacity: busy || !validTeams ? 0.55 : 1,
                }}
              >
                {busy === 'submit' ? 'Starting analysis…' : 'Start Analysis'}
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
