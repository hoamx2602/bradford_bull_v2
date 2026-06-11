'use client'

import { useCallback, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import Nav from '@/components/nav'
import { createJob } from '@/lib/api'

const PLACEMENTS = [
  { value: 'live-tv', label: 'Live Broadcast TV', mult: 1.0 },
  { value: 'live-stream', label: 'Live Stream', mult: 0.85 },
  { value: 'highlight', label: 'Highlight Clip', mult: 1.4 },
  { value: 'social', label: 'Social Media', mult: 0.7 },
]

export default function UploadPage() {
  const router = useRouter()
  const inputRef = useRef<HTMLInputElement>(null)

  const [file, setFile] = useState<File | null>(null)
  const [dragging, setDragging] = useState(false)
  const [eventName, setEventName] = useState('')
  const [audience, setAudience] = useState('2400000')
  const [placement, setPlacement] = useState('live-tv')
  const [cpm, setCpm] = useState('22')
  const [kit, setKit] = useState('away')

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

  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const canSubmit = file && eventName.trim() && audience && cpm && !submitting

  const handleSubmit = async () => {
    if (!canSubmit) return
    const meta = {
      eventName: eventName.trim(),
      videoName: file!.name,
      audienceSize: parseInt(audience),
      placementType: PLACEMENTS.find(p => p.value === placement)?.label ?? 'Live Broadcast TV',
      cpmBase: parseFloat(cpm),
      kit,
    }
    // Keep metadata for the processing/dashboard screens to display immediately.
    localStorage.setItem('sl_meta', JSON.stringify(meta))

    setSubmitting(true)
    setError(null)
    try {
      const { jobId } = await createJob(file!, meta)
      localStorage.setItem('sl_job', jobId)
      router.push('/processing')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Upload failed')
      setSubmitting(false)
    }
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

      <main style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '48px 24px' }}>
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

          {/* Submit */}
          <button
            onClick={handleSubmit}
            disabled={!canSubmit}
            style={{
              width: '100%',
              padding: '14px 24px',
              background: canSubmit ? 'var(--c-spark)' : 'var(--c-panel)',
              color: canSubmit ? '#000' : 'var(--c-ghost)',
              border: `1px solid ${canSubmit ? 'transparent' : 'var(--c-wire)'}`,
              borderRadius: 8,
              fontWeight: 700,
              fontSize: 14,
              letterSpacing: '0.04em',
              transition: 'background 0.15s, opacity 0.15s',
              cursor: canSubmit ? 'pointer' : 'not-allowed',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 8,
            }}
          >
            {submitting ? 'Uploading…' : 'Start Analysis'}
            {!submitting && (
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
            Video is uploaded to the analysis backend and processed with YOLO26.
          </p>
        </div>
      </main>
    </div>
  )
}
