'use client'

// Settings: the global kit-placement taxonomy (Location → anchor → Logo →
// Human %) and which algorithm criteria feed the AI %. Both back the per-video
// Location Breakdown table on the dashboard.

import { useCallback, useEffect, useState } from 'react'
import Nav from '@/components/nav'
import {
  getLocations, saveLocations, getAnchors, getBrands,
  getAiCriteriaOptions, getAiCriteria, saveAiCriteria,
} from '@/lib/api'
import type { LocationConfig, AnchorOption, BrandOption, AiCriterion } from '@/lib/types'

const labelStyle: React.CSSProperties = {
  fontSize: 10, fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase',
  color: 'var(--c-ghost)', display: 'block', marginBottom: 5,
}
const th: React.CSSProperties = {
  padding: '9px 12px', textAlign: 'left', fontSize: 10, fontWeight: 600,
  letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--c-ghost)',
  borderBottom: '1px solid var(--c-wire)', whiteSpace: 'nowrap',
}
const cellInput: React.CSSProperties = {
  width: '100%', fontSize: 13, padding: '6px 8px', background: 'var(--c-canvas)',
  border: '1px solid var(--c-wire)', borderRadius: 6, color: 'var(--c-ink)',
}
const primaryBtn: React.CSSProperties = {
  fontSize: 13, fontWeight: 700, padding: '9px 18px', borderRadius: 7, border: 'none',
  background: 'var(--c-spark)', color: '#000', cursor: 'pointer',
}
const ghostBtn: React.CSSProperties = {
  fontSize: 12, padding: '7px 13px', borderRadius: 7, cursor: 'pointer',
  background: 'transparent', color: 'var(--c-dim)', border: '1px solid var(--c-wire)',
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section style={{ marginBottom: 40 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 18 }}>
        <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--c-dim)' }}>
          {title}
        </div>
        <div style={{ flex: 1, height: 1, background: 'var(--c-wire)' }} />
      </div>
      {children}
    </section>
  )
}

const emptyRow = (): LocationConfig => ({ name: '', anchorId: '', brandKey: '', brandKeyAway: '', humanPercentage: 0 })

export default function SettingsPage() {
  const [rows, setRows] = useState<LocationConfig[]>([])
  const [anchors, setAnchors] = useState<AnchorOption[]>([])
  const [brands, setBrands] = useState<BrandOption[]>([])
  const [criteriaOpts, setCriteriaOpts] = useState<AiCriterion[]>([])
  const [enabled, setEnabled] = useState<string[]>([])
  const [error, setError] = useState('')
  const [savingLoc, setSavingLoc] = useState(false)
  const [savedLoc, setSavedLoc] = useState(false)
  const [savingCrit, setSavingCrit] = useState(false)

  const load = useCallback(async () => {
    setError('')
    try {
      const [l, a, b, opts, cur] = await Promise.all([
        getLocations(), getAnchors(), getBrands(), getAiCriteriaOptions(), getAiCriteria(),
      ])
      setRows(l); setAnchors(a); setBrands(b); setCriteriaOpts(opts); setEnabled(cur.enabled)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load settings (is the backend running?)')
    }
  }, [])
  useEffect(() => { load() }, [load])

  const setRow = (i: number, patch: Partial<LocationConfig>) =>
    setRows(rs => rs.map((r, j) => j === i ? { ...r, ...patch } : r))
  const removeRow = (i: number) => setRows(rs => rs.filter((_, j) => j !== i))
  const addRow = () => setRows(rs => [...rs, emptyRow()])
  const move = (i: number, dir: -1 | 1) => setRows(rs => {
    const j = i + dir
    if (j < 0 || j >= rs.length) return rs
    const copy = [...rs];[copy[i], copy[j]] = [copy[j], copy[i]]; return copy
  })

  const onSaveLocations = async () => {
    setSavingLoc(true); setError(''); setSavedLoc(false)
    try {
      const saved = await saveLocations(rows.filter(r => r.name.trim()))
      setRows(saved)
      setSavedLoc(true); setTimeout(() => setSavedLoc(false), 2000)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not save locations')
    } finally {
      setSavingLoc(false)
    }
  }

  const toggleCriterion = async (key: string) => {
    const next = enabled.includes(key) ? enabled.filter(k => k !== key) : [...enabled, key]
    setEnabled(next)
    setSavingCrit(true)
    try {
      const res = await saveAiCriteria(next)
      setEnabled(res.enabled)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not save criteria')
    } finally {
      setSavingCrit(false)
    }
  }

  return (
    <div style={{ minHeight: '100vh' }}>
      <Nav />
      <div style={{ maxWidth: 1100, margin: '0 auto', padding: '32px 24px 64px' }}>
        <div style={{ marginBottom: 28 }}>
          <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--c-spark)', marginBottom: 8 }}>
            Configuration
          </div>
          <h1 style={{ fontSize: 26, fontWeight: 700, margin: 0, letterSpacing: '-0.02em' }}>Settings</h1>
        </div>

        {error && (
          <div style={{
            marginBottom: 24, padding: '12px 16px', borderRadius: 10, fontSize: 13,
            background: 'rgba(224,133,133,0.08)', border: '1px solid rgba(224,133,133,0.35)', color: 'var(--c-ink)',
          }}>
            {error}
          </div>
        )}

        {/* ── Location taxonomy + mapping ────────────────────────────── */}
        <Section title="Locations — Mapping & Human %">
          <div style={{ background: 'var(--c-panel)', border: '1px solid var(--c-wire)', borderRadius: 10, overflow: 'hidden' }}>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr>
                    <th style={{ ...th, width: 40 }}>#</th>
                    <th style={th}>Location</th>
                    <th style={th}>Anchor (pose zone)</th>
                    <th style={th}>Logo (home)</th>
                    <th style={th}>Logo (away)</th>
                    <th style={{ ...th, width: 120 }}>Human %</th>
                    <th style={{ ...th, width: 110 }} />
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r, i) => (
                    <tr key={r.id ?? `new-${i}`} style={{ borderBottom: '1px solid var(--c-wire)' }}>
                      <td style={{ padding: '8px 12px', color: 'var(--c-ghost)', fontSize: 12, textAlign: 'center' }} className="num">{i + 1}</td>
                      <td style={{ padding: '8px 12px', minWidth: 160 }}>
                        <input value={r.name} onChange={e => setRow(i, { name: e.target.value })} style={cellInput} placeholder="Location name" />
                      </td>
                      <td style={{ padding: '8px 12px', minWidth: 150 }}>
                        <select value={r.anchorId} onChange={e => setRow(i, { anchorId: e.target.value })} style={cellInput}>
                          <option value="">— none —</option>
                          {anchors.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
                        </select>
                      </td>
                      <td style={{ padding: '8px 12px', minWidth: 150 }}>
                        <select value={r.brandKey ?? ''} onChange={e => setRow(i, { brandKey: e.target.value || null })} style={cellInput}>
                          <option value="">— none —</option>
                          {brands.map(b => <option key={b.key} value={b.key}>{b.name}</option>)}
                        </select>
                      </td>
                      <td style={{ padding: '8px 12px', minWidth: 150 }}>
                        <select value={r.brandKeyAway ?? ''} onChange={e => setRow(i, { brandKeyAway: e.target.value || null })} style={cellInput} title="Leave blank if the same sponsor on both kits">
                          <option value="">— same as home —</option>
                          {brands.map(b => <option key={b.key} value={b.key}>{b.name}</option>)}
                        </select>
                      </td>
                      <td style={{ padding: '8px 12px' }}>
                        <input
                          type="number" step="0.01" className="num"
                          value={r.humanPercentage}
                          onChange={e => setRow(i, { humanPercentage: Number(e.target.value) })}
                          style={{ ...cellInput, textAlign: 'right' }}
                        />
                      </td>
                      <td style={{ padding: '8px 12px', whiteSpace: 'nowrap' }}>
                        <button onClick={() => move(i, -1)} title="Move up" style={{ ...ghostBtn, padding: '5px 8px', marginRight: 4 }}>↑</button>
                        <button onClick={() => move(i, 1)} title="Move down" style={{ ...ghostBtn, padding: '5px 8px', marginRight: 4 }}>↓</button>
                        <button onClick={() => removeRow(i)} title="Remove" style={{ ...ghostBtn, padding: '5px 8px', color: '#e08585' }}>✕</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 14 }}>
            <button onClick={addRow} style={ghostBtn}>+ Add location</button>
            <div style={{ flex: 1 }} />
            {savedLoc && <span style={{ fontSize: 12, color: 'var(--c-spark)' }}>Saved</span>}
            <button onClick={onSaveLocations} disabled={savingLoc} style={{ ...primaryBtn, opacity: savingLoc ? 0.6 : 1 }}>
              {savingLoc ? 'Saving…' : 'Save Locations'}
            </button>
          </div>
        </Section>

        {/* ── AI criteria ────────────────────────────────────────────── */}
        <Section title="AI Percentage — Criteria">
          <div style={{ fontSize: 13, color: 'var(--c-dim)', marginBottom: 16 }}>
            Tick which algorithm factors feed the AI % column. Changes apply to every video&apos;s
            Location Breakdown the next time it loads. {savingCrit && <span style={{ color: 'var(--c-ghost)' }}>· saving…</span>}
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 12 }}>
            {criteriaOpts.map(c => {
              const on = enabled.includes(c.key)
              return (
                <label key={c.key} style={{
                  display: 'flex', gap: 12, alignItems: 'flex-start', cursor: 'pointer',
                  background: 'var(--c-panel)', border: `1px solid ${on ? 'var(--c-spark)' : 'var(--c-wire)'}`,
                  borderRadius: 10, padding: '14px 16px', transition: 'border-color 0.15s',
                }}>
                  <input type="checkbox" checked={on} onChange={() => toggleCriterion(c.key)} style={{ marginTop: 3 }} />
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--c-ink)' }}>{c.label}</span>
                      <span style={{ fontSize: 10, color: 'var(--c-ghost)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{c.scope}</span>
                      {!c.affectsShare && (
                        <span style={{ fontSize: 10, color: 'var(--c-ghost)', border: '1px solid var(--c-wire)', borderRadius: 4, padding: '1px 5px' }}>
                          no effect on share
                        </span>
                      )}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--c-dim)', marginTop: 4 }}>{c.description}</div>
                  </div>
                </label>
              )
            })}
          </div>
        </Section>
      </div>
    </div>
  )
}
