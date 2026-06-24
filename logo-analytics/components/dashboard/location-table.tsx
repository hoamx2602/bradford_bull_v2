'use client'

// Per-video kit-placement table: Location | Logo | Human % | AI % | Human AI %.
// AI % is recomputed server-side from the stored exposure facts under the
// currently-enabled algorithm criteria (configured in /settings). Human-AI % is
// the manual visual estimate the user types in, saved as a per-video override.

import { useCallback, useEffect, useState } from 'react'
import { getLocationBreakdown, saveLocationOverrides, locationExcelUrl } from '@/lib/api'
import type { LocationBreakdownRow } from '@/lib/types'

interface Props {
  analysisId: string
  /** False when the dashboard is showing demo data (no backend) — disables fetch. */
  enabled?: boolean
}

const th: React.CSSProperties = {
  padding: '10px 14px', textAlign: 'left', fontSize: 11, fontWeight: 600,
  letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--c-dim)',
  whiteSpace: 'nowrap', borderBottom: '1px solid var(--c-wire)',
}
const thR: React.CSSProperties = { ...th, textAlign: 'right' }
const td: React.CSSProperties = { padding: '11px 14px', fontSize: 13 }
const tdR: React.CSSProperties = { ...td, textAlign: 'right' }

function pct(v: number | null | undefined): string {
  return v == null ? '—' : `${v.toFixed(2)}%`
}

export default function LocationTable({ analysisId, enabled = true }: Props) {
  const [rows, setRows] = useState<LocationBreakdownRow[]>([])
  const [criteria, setCriteria] = useState<string[]>([])
  const [kit, setKit] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  // Local draft of the manual Human-AI % per location id (string for free typing).
  const [draft, setDraft] = useState<Record<string, string>>({})
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  const load = useCallback(async () => {
    if (!enabled || !analysisId) return
    setLoading(true); setError('')
    try {
      const bd = await getLocationBreakdown(analysisId)
      setRows(bd.rows)
      setCriteria(bd.enabledCriteria)
      setKit(bd.kit)
      setDraft(Object.fromEntries(
        bd.rows.map(r => [r.locationId, r.humanAiPercentage == null ? '' : String(r.humanAiPercentage)]),
      ))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load location breakdown')
    } finally {
      setLoading(false)
    }
  }, [analysisId, enabled])

  useEffect(() => { load() }, [load])

  const onSave = async () => {
    setSaving(true); setError(''); setSaved(false)
    try {
      await saveLocationOverrides(analysisId, rows.map(r => ({
        locationId: r.locationId,
        humanAiPercentage: draft[r.locationId] === '' ? null : Number(draft[r.locationId]),
      })))
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
      await load()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not save')
    } finally {
      setSaving(false)
    }
  }

  if (!enabled) {
    return (
      <div style={{ padding: '28px 20px', textAlign: 'center', color: 'var(--c-ghost)', fontSize: 13,
        background: 'var(--c-panel)', border: '1px dashed var(--c-wire)', borderRadius: 10 }}>
        Location breakdown needs the analysis backend (demo data shown).
      </div>
    )
  }

  const aiTotal = rows.reduce((s, r) => s + (r.aiPercentage || 0), 0)
  const humanTotal = rows.reduce((s, r) => s + (r.humanPercentage || 0), 0)

  return (
    <div>
      <div style={{ background: 'var(--c-panel)', border: '1px solid var(--c-wire)', borderRadius: 10, overflow: 'hidden' }}>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th style={th}>Location</th>
                <th style={th}>Logo</th>
                <th style={thR}>Human %</th>
                <th style={thR}>AI %</th>
                <th style={thR}>Human AI %</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={r.locationId} style={{ borderBottom: i < rows.length - 1 ? '1px solid var(--c-wire)' : 'none' }}>
                  <td style={{ ...td, fontWeight: 600 }}>{r.locationName}</td>
                  <td style={{ ...td, color: r.logo ? 'var(--c-ink)' : 'var(--c-ghost)' }}>{r.logo || '—'}</td>
                  <td style={{ ...tdR }} className="num">{pct(r.humanPercentage)}</td>
                  <td style={{ ...tdR, color: 'var(--c-spark)', fontWeight: 600 }} className="num">{pct(r.aiPercentage)}</td>
                  <td style={{ ...tdR }}>
                    <input
                      type="number"
                      step="0.01"
                      placeholder="—"
                      value={draft[r.locationId] ?? ''}
                      onChange={e => setDraft(d => ({ ...d, [r.locationId]: e.target.value }))}
                      className="num"
                      style={{
                        width: 88, textAlign: 'right', fontSize: 13, padding: '5px 8px',
                        background: 'var(--c-canvas)', border: '1px solid var(--c-wire)',
                        borderRadius: 6, color: 'var(--c-ink)',
                      }}
                    />
                  </td>
                </tr>
              ))}
              {rows.length > 0 && (
                <tr style={{ borderTop: '2px solid var(--c-wire)' }}>
                  <td style={{ ...td, fontWeight: 700 }}>Total</td>
                  <td style={td} />
                  <td style={{ ...tdR, fontWeight: 700 }} className="num">{humanTotal.toFixed(2)}%</td>
                  <td style={{ ...tdR, fontWeight: 700, color: 'var(--c-spark)' }} className="num">{aiTotal.toFixed(2)}%</td>
                  <td style={tdR} />
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '12px 16px 0', fontSize: 12, color: 'var(--c-ghost)', flexWrap: 'wrap' }}>
        <span>
          {kit && (
            <>Kit: <span style={{ color: 'var(--c-dim)' }}>{kit === 'home' ? 'Home (white)' : kit === 'away' ? 'Away (black)' : kit}</span> · </>
          )}
          AI % from {criteria.length} criteria: <span style={{ color: 'var(--c-dim)' }}>{criteria.join(', ') || 'none'}</span>{' '}
          — configure in Settings.
        </span>
        <div style={{ flex: 1 }} />
        {error && <span style={{ color: '#e08585' }}>{error}</span>}
        {saved && <span style={{ color: 'var(--c-spark)' }}>Saved</span>}
        {loading && <span>Loading…</span>}
        <a
          href={locationExcelUrl(analysisId)}
          className="no-print"
          style={{
            display: 'inline-flex', alignItems: 'center', gap: 7, textDecoration: 'none',
            fontSize: 12, fontWeight: 600, padding: '8px 14px', borderRadius: 7,
            border: '1px solid var(--c-wire)', background: 'transparent', color: 'var(--c-dim)',
          }}
        >
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="7 10 12 15 17 10" /><line x1="12" y1="15" x2="12" y2="3" />
          </svg>
          Export Excel
        </a>
        <button
          onClick={onSave}
          disabled={saving || loading}
          className="no-print"
          style={{
            fontSize: 12, fontWeight: 700, padding: '8px 16px', borderRadius: 7, border: 'none',
            background: 'var(--c-spark)', color: '#000', cursor: 'pointer', opacity: saving ? 0.6 : 1,
          }}
        >
          {saving ? 'Saving…' : 'Save Human AI %'}
        </button>
      </div>
    </div>
  )
}
