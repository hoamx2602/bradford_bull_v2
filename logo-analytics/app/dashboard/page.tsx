'use client'

import { useEffect, useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'
import Nav from '@/components/nav'
import MatchSelector from '@/components/dashboard/match-selector'
import VideoGallery from '@/components/dashboard/video-gallery'
import ExposureLineChart from '@/components/dashboard/exposure-line-chart'
import ExposurePieChart from '@/components/dashboard/exposure-pie-chart'
import BodySegmentation3D from '@/components/dashboard/body-segmentation-3d'
import DetectionPlayer from '@/components/dashboard/detection-player'
import LogoTable from '@/components/dashboard/logo-table'
import { DonutChart, TrendChart, HeatmapGrid, RadarChart, ScatterChart, colorAt } from '@/components/dashboard/charts'
import { MOCK_RESULT, MOCK_MATCHES, getBrandColor } from '@/lib/mock-data'
import { listAnalyses, bodysegVideoUrl } from '@/lib/api'
import {
  formatCurrency, formatDate, formatNumber, formatSeconds,
  exportCSV, exportPDF, aggregateBrands, filterMatches,
} from '@/lib/utils'
import type { AnalysisResult, EventMeta, MatchEntry } from '@/lib/types'

function Section({ title, right, children }: { title: string; right?: React.ReactNode; children: React.ReactNode }) {
  return (
    <section style={{ marginBottom: 32 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 18 }}>
        <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--c-dim)' }}>
          {title}
        </div>
        <div style={{ flex: 1, height: 1, background: 'var(--c-wire)' }} />
        {right}
      </div>
      {children}
    </section>
  )
}

function KpiCard({ label, value, sub, accent }: { label: string; value: string; sub?: string; accent?: boolean }) {
  return (
    <div style={{
      background: 'var(--c-panel)',
      border: '1px solid var(--c-wire)',
      borderRadius: 10,
      padding: '20px 24px',
    }}>
      <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--c-dim)', marginBottom: 10 }}>
        {label}
      </div>
      <div className="num" style={{
        fontSize: 32,
        fontWeight: 700,
        letterSpacing: '-0.02em',
        color: accent ? 'var(--c-spark)' : 'var(--c-ink)',
        lineHeight: 1,
        marginBottom: sub ? 6 : 0,
      }}>
        {value}
      </div>
      {sub && <div style={{ fontSize: 12, color: 'var(--c-ghost)' }}>{sub}</div>}
    </div>
  )
}

// Horizontal labelled bar — used for match comparison + share-of-voice rows.
function BarRow({ rank, label, sub, value, frac, onClick }: {
  rank?: number; label: string; sub?: string; value: string; frac: number; onClick?: () => void
}) {
  return (
    <div
      onClick={onClick}
      style={{
        display: 'flex', alignItems: 'center', gap: 14,
        padding: '10px 16px',
        borderRadius: 8,
        cursor: onClick ? 'pointer' : 'default',
        transition: 'background 0.15s',
      }}
      onMouseEnter={e => { if (onClick) e.currentTarget.style.background = 'var(--c-hover)' }}
      onMouseLeave={e => { if (onClick) e.currentTarget.style.background = 'transparent' }}
    >
      {rank != null && (
        <span className="num" style={{ fontSize: 11, color: 'var(--c-ghost)', width: 18, textAlign: 'center', flexShrink: 0 }}>
          {rank}
        </span>
      )}
      <div style={{ width: 220, flexShrink: 0 }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--c-ink)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {label}
        </div>
        {sub && <div style={{ fontSize: 11, color: 'var(--c-ghost)', marginTop: 1 }}>{sub}</div>}
      </div>
      <div style={{ flex: 1, height: 8, background: 'var(--c-wire)', borderRadius: 4, overflow: 'hidden' }}>
        <div style={{
          height: '100%',
          width: `${Math.max(1.5, frac * 100)}%`,
          background: 'var(--c-spark)',
          borderRadius: 4,
          transition: 'width 0.6s ease',
        }} />
      </div>
      <span className="num" style={{ fontSize: 13, fontWeight: 600, color: 'var(--c-spark)', minWidth: 86, textAlign: 'right' }}>
        {value}
      </span>
    </div>
  )
}

const inputStyle: React.CSSProperties = { fontSize: 13 }

const labelStyle: React.CSSProperties = {
  fontSize: 10, fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase',
  color: 'var(--c-ghost)', display: 'block', marginBottom: 5,
}

// Unified per-brand report row — built from a single match OR aggregated scope.
interface ReportRow {
  key: string
  name: string
  emv: number
  exposure: number
  quality: number
  avgVis: number
  segments: number
  matches?: number
}

export default function DashboardPage() {
  const router = useRouter()
  const [activeTab, setActiveTab] = useState('overview')
  const [matches, setMatches] = useState<MatchEntry[]>(MOCK_MATCHES)
  const [selectedMatchId, setSelectedMatchId] = useState('match-1')
  const [result, setResult] = useState<AnalysisResult>(MOCK_RESULT)
  const [usingBackend, setUsingBackend] = useState(false)

  // Videos tab — search + date filters + sort
  const [vidQuery, setVidQuery] = useState('')
  const [vidFrom, setVidFrom] = useState('')
  const [vidTo, setVidTo] = useState('')
  const [vidSort, setVidSort] = useState<'date' | 'emv' | 'duration'>('date')

  // Brand Insights tab — selected brand key (null = auto: top brand)
  const [insightBrand, setInsightBrand] = useState<string | null>(null)

  // Analytics tab — report scope filters
  const [scopeId, setScopeId] = useState<string>('all')
  const [brandKey, setBrandKey] = useState<string>('all')
  const [repFrom, setRepFrom] = useState('')
  const [repTo, setRepTo] = useState('')

  // Load real analyses from the backend; fall back to mock data if unavailable.
  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const list = await listAnalyses()
        if (cancelled || list.length === 0) return
        setMatches(list)
        setUsingBackend(true)
        // Prefer the analysis just produced (?analysis= or sl_analysis), else newest.
        const params = new URLSearchParams(window.location.search)
        const wantId = params.get('analysis') || localStorage.getItem('sl_analysis')
        const chosen = list.find(m => m.result.id === wantId) ?? list[0]
        setSelectedMatchId(chosen.id)
        setResult(chosen.result)
        // Deep link from upload flow: land on the video detail, not the portfolio.
        if (params.get('analysis')) setActiveTab('videos')
      } catch {
        // Backend unreachable — keep mock data + the localStorage meta merge below.
      }
    })()
    return () => { cancelled = true }
  }, [])

  // When match selection changes, update the result.
  useEffect(() => {
    const match = matches.find(m => m.id === selectedMatchId)
    if (match) setResult(match.result)
  }, [selectedMatchId, matches])

  // Mock-only: reflect the upload form metadata in the demo result header.
  // Skipped once real backend data has loaded (it carries its own metadata).
  useEffect(() => {
    if (usingBackend) return
    try {
      const raw = localStorage.getItem('sl_meta')
      if (raw) {
        const m: EventMeta = JSON.parse(raw)
        setResult(prev => ({
          ...prev,
          eventName: m.eventName || prev.eventName,
          videoName: m.videoName || prev.videoName,
          metadata: {
            ...prev.metadata,
            audienceSize: m.audienceSize || prev.metadata.audienceSize,
            placementType: m.placementType || prev.metadata.placementType,
            cpmBase: m.cpmBase || prev.metadata.cpmBase,
          },
        }))
      }
    } catch {}
  }, [usingBackend])

  // ── Portfolio aggregates (Overview) ────────────────────────────────
  const portfolio = useMemo(() => {
    const totalEmv = matches.reduce((s, m) => s + m.totalEmv, 0)
    const totalFootage = matches.reduce((s, m) => s + m.durationSeconds, 0)
    const totalQuality = matches.reduce((s, m) => s + m.result.totalQualityExposureSeconds, 0)
    const brands = aggregateBrands(matches)
    const totalSegments = brands.reduce((s, b) => s + b.segmentCount, 0)
    const visW = brands.reduce((s, b) => s + b.totalExposure, 0)
    const avgVis = visW ? brands.reduce((s, b) => s + b.avgVisibility * b.totalExposure, 0) / visW : 0
    return { totalEmv, totalFootage, totalQuality, brands, totalSegments, avgVis }
  }, [matches])

  // ── Videos tab ──────────────────────────────────────────────────────
  const filteredMatches = useMemo(() => {
    const list = filterMatches(matches, vidQuery, vidFrom, vidTo)
    const cmp: Record<typeof vidSort, (a: MatchEntry, b: MatchEntry) => number> = {
      date: (a, b) => new Date(b.date).getTime() - new Date(a.date).getTime(),
      emv: (a, b) => b.totalEmv - a.totalEmv,
      duration: (a, b) => b.durationSeconds - a.durationSeconds,
    }
    return [...list].sort(cmp[vidSort])
  }, [matches, vidQuery, vidFrom, vidTo, vidSort])
  const selectedMatch = matches.find(m => m.id === selectedMatchId)

  // ── Shared chart data ───────────────────────────────────────────────
  // Chronological match order for every trend chart x-axis.
  const chronoMatches = useMemo(
    () => [...matches].sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime()),
    [matches],
  )
  const chronoLabels = useMemo(
    () => chronoMatches.map(m => new Date(m.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })),
    [chronoMatches],
  )
  // Stable colour per brand across all portfolio views (index in EMV ranking).
  const brandColor = useMemo(() => {
    const map = new Map<string, string>()
    aggregateBrands(matches).forEach((b, i) => map.set(b.key, colorAt(i)))
    return (key: string) => map.get(key) ?? '#787878'
  }, [matches])
  // Brand EMV in one match (sum over its logos with that key).
  const brandEmvIn = (m: MatchEntry, key: string) =>
    m.result.logos.filter(l => (l.class || l.name) === key).reduce((s, l) => s + l.emvUsd, 0)

  // ── Analytics tab — scope + rows ────────────────────────────────────
  const scopeMatches = useMemo(() => {
    if (scopeId !== 'all') return matches.filter(m => m.id === scopeId)
    return filterMatches(matches, '', repFrom, repTo)
  }, [matches, scopeId, repFrom, repTo])

  const scopeResult = scopeId !== 'all' ? scopeMatches[0]?.result : undefined

  const reportRows: ReportRow[] = useMemo(() => {
    let rows: ReportRow[]
    if (scopeResult) {
      rows = scopeResult.logos.map(l => ({
        key: l.class || l.name, name: l.name, emv: l.emvUsd,
        exposure: l.totalExposureSeconds, quality: l.qualityExposureSeconds,
        avgVis: l.avgVisibilityScore, segments: l.segmentCount,
      }))
    } else {
      rows = aggregateBrands(scopeMatches).map(b => ({
        key: b.key, name: b.name, emv: b.totalEmv,
        exposure: b.totalExposure, quality: b.qualityExposure,
        avgVis: b.avgVisibility, segments: b.segmentCount, matches: b.matchCount,
      }))
    }
    if (brandKey !== 'all') rows = rows.filter(r => r.key === brandKey)
    return rows.sort((a, b) => b.emv - a.emv)
  }, [scopeResult, scopeMatches, brandKey])

  const scopeTotalEmv = reportRows.reduce((s, r) => s + r.emv, 0)
  const scopeTotalExposure = reportRows.reduce((s, r) => s + r.exposure, 0)
  const scopeTotalQuality = reportRows.reduce((s, r) => s + r.quality, 0)
  // Denominator for share-of-voice: the unfiltered scope total.
  const sovDenom = useMemo(() => {
    if (scopeResult) return scopeResult.logos.reduce((s, l) => s + l.emvUsd, 0)
    return aggregateBrands(scopeMatches).reduce((s, b) => s + b.totalEmv, 0)
  }, [scopeResult, scopeMatches])

  const brandOptions = useMemo(() => aggregateBrands(matches), [matches])

  // Single-match charts honour the brand filter.
  const chartResult: AnalysisResult | undefined = useMemo(() => {
    if (!scopeResult) return undefined
    if (brandKey === 'all') return scopeResult
    return { ...scopeResult, logos: scopeResult.logos.filter(l => (l.class || l.name) === brandKey) }
  }, [scopeResult, brandKey])

  const totalSegments = result.logos.reduce((s, l) => s + l.segmentCount, 0)

  const ExportBtn = (
    <button
      onClick={() => exportCSV(result)}
      style={{
        display: 'flex', alignItems: 'center', gap: 7,
        background: 'transparent',
        border: '1px solid var(--c-wire)',
        borderRadius: 7,
        color: 'var(--c-dim)',
        padding: '8px 14px',
        fontSize: 12,
        fontWeight: 500,
        transition: 'border-color 0.15s, color 0.15s',
      }}
      onMouseEnter={e => { const b = e.currentTarget; b.style.borderColor = 'var(--c-wire-s)'; b.style.color = 'var(--c-ink)' }}
      onMouseLeave={e => { const b = e.currentTarget; b.style.borderColor = 'var(--c-wire)'; b.style.color = 'var(--c-dim)' }}
    >
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="7 10 12 15 17 10" /><line x1="12" y1="15" x2="12" y2="3" />
      </svg>
      Export CSV
    </button>
  )

  return (
    <div style={{ minHeight: '100vh' }}>
      <Nav right={ExportBtn} />

      <div style={{ maxWidth: 1280, margin: '0 auto', padding: '32px 24px 64px' }}>

        {/* Header */}
        <div style={{ marginBottom: 28, display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: 16 }} className="slide-up">
          <div>
            <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--c-spark)', marginBottom: 8 }}>
              Sponsorship Intelligence
            </div>
            <h1 style={{ fontSize: 26, fontWeight: 700, margin: '0 0 8px', letterSpacing: '-0.02em' }}>
              Dashboard
            </h1>
            <div style={{ display: 'flex', alignItems: 'center', gap: 16, color: 'var(--c-dim)', fontSize: 13, flexWrap: 'wrap' }}>
              <span>{matches.length} matches analysed</span>
              <span style={{ color: 'var(--c-wire-s)' }}>·</span>
              <span>{formatSeconds(portfolio.totalFootage)} of footage</span>
              <span style={{ color: 'var(--c-wire-s)' }}>·</span>
              <span>{portfolio.brands.length} brands tracked</span>
              {!usingBackend && (
                <>
                  <span style={{ color: 'var(--c-wire-s)' }}>·</span>
                  <span style={{ color: 'var(--c-ghost)' }}>demo data</span>
                </>
              )}
            </div>
          </div>
          <button
            onClick={() => router.push('/')}
            className="no-print"
            style={{
              display: 'flex', alignItems: 'center', gap: 8,
              background: 'var(--c-spark)', color: '#000',
              border: 'none', borderRadius: 8,
              padding: '11px 18px', fontSize: 13, fontWeight: 700,
              cursor: 'pointer', flexShrink: 0,
            }}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round">
              <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            New Analysis
          </button>
        </div>

        {/* Tab navigation */}
        <MatchSelector activeTab={activeTab} onTabChange={setActiveTab} />

        {/* Tab content */}
        <div className="fade-scale-in" key={activeTab}>

          {/* ═══════════════ OVERVIEW — PORTFOLIO DASHBOARD ═══════════════ */}
          {activeTab === 'overview' && (
            <>
              {/* Portfolio KPIs */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 16, marginBottom: 36 }}>
                <KpiCard
                  label="Portfolio EMV"
                  value={formatCurrency(portfolio.totalEmv)}
                  sub={`across ${matches.length} matches`}
                  accent
                />
                <KpiCard
                  label="Brands Tracked"
                  value={String(portfolio.brands.length)}
                  sub={`${portfolio.totalSegments} total appearances`}
                />
                <KpiCard
                  label="Quality Exposure"
                  value={formatSeconds(portfolio.totalQuality)}
                  sub="Visibility-weighted, all matches"
                />
                <KpiCard
                  label="Avg Visibility"
                  value={`${(portfolio.avgVis * 100).toFixed(0)}%`}
                  sub="Exposure-weighted average"
                />
              </div>

              {/* EMV trend across matches — total + top brands */}
              <Section title="EMV Trend">
                <TrendChart
                  xLabels={chronoLabels}
                  format={v => formatCurrency(v)}
                  yLabel="EMV per match"
                  series={[
                    {
                      name: 'Total EMV',
                      color: 'var(--c-spark)' as string,
                      values: chronoMatches.map(m => m.totalEmv),
                    },
                    ...portfolio.brands.slice(0, 3).map(b => ({
                      name: b.name,
                      color: brandColor(b.key),
                      values: chronoMatches.map(m => brandEmvIn(m, b.key)),
                    })),
                  ]}
                />
              </Section>

              {/* Share of voice */}
              <Section title="Share of Voice — Portfolio">
                <DonutChart
                  centerLabel="Portfolio EMV"
                  format={v => formatCurrency(v)}
                  data={[
                    ...portfolio.brands.slice(0, 8).map(b => ({
                      label: b.name, value: b.totalEmv, color: brandColor(b.key),
                    })),
                    ...(portfolio.brands.length > 8 ? [{
                      label: 'Other',
                      value: portfolio.brands.slice(8).reduce((s, b) => s + b.totalEmv, 0),
                      color: '#52525B',
                    }] : []),
                  ]}
                />
              </Section>

              {/* EMV by match */}
              <Section title="EMV by Match">
                <div style={{ background: 'var(--c-panel)', border: '1px solid var(--c-wire)', borderRadius: 10, padding: '10px 4px' }}>
                  {[...matches].sort((a, b) => b.totalEmv - a.totalEmv).map(m => (
                    <BarRow
                      key={m.id}
                      label={m.eventName}
                      sub={`${formatDate(m.date)} · ${m.logoCount} brands`}
                      value={formatCurrency(m.totalEmv)}
                      frac={portfolio.totalEmv ? m.totalEmv / Math.max(...matches.map(x => x.totalEmv)) : 0}
                      onClick={() => { setSelectedMatchId(m.id); setActiveTab('videos') }}
                    />
                  ))}
                </div>
                <div style={{ fontSize: 12, color: 'var(--c-ghost)', padding: '10px 16px 0' }}>
                  Click a match to open its detailed analysis.
                </div>
              </Section>

              {/* Top brands across the portfolio */}
              <Section title="Top Brands — All Matches">
                <div style={{ background: 'var(--c-panel)', border: '1px solid var(--c-wire)', borderRadius: 10, padding: '10px 4px' }}>
                  {portfolio.brands.slice(0, 10).map((b, i) => (
                    <BarRow
                      key={b.key}
                      rank={i + 1}
                      label={b.name}
                      sub={`${formatSeconds(b.totalExposure)} on screen · ${b.matchCount} ${b.matchCount === 1 ? 'match' : 'matches'} · ${(b.avgVisibility * 100).toFixed(0)}% vis`}
                      value={formatCurrency(b.totalEmv)}
                      frac={portfolio.brands[0]?.totalEmv ? b.totalEmv / portfolio.brands[0].totalEmv : 0}
                    />
                  ))}
                </div>
              </Section>
            </>
          )}

          {/* ═══════════════════════ VIDEOS TAB ════════════════════════ */}
          {activeTab === 'videos' && (
            <>
              <Section title="Match Recordings">
                {/* Search + date filters */}
                <div className="no-print" style={{
                  display: 'flex', gap: 14, alignItems: 'flex-end', flexWrap: 'wrap',
                  background: 'var(--c-panel)', border: '1px solid var(--c-wire)',
                  borderRadius: 10, padding: '14px 16px', marginBottom: 20,
                }}>
                  <div style={{ flex: 1, minWidth: 220 }}>
                    <label style={labelStyle}>Search</label>
                    <input
                      type="text"
                      placeholder="Event or video name…"
                      value={vidQuery}
                      onChange={e => setVidQuery(e.target.value)}
                      style={inputStyle}
                    />
                  </div>
                  <div>
                    <label style={labelStyle}>From</label>
                    <input type="date" value={vidFrom} onChange={e => setVidFrom(e.target.value)} style={inputStyle} />
                  </div>
                  <div>
                    <label style={labelStyle}>To</label>
                    <input type="date" value={vidTo} onChange={e => setVidTo(e.target.value)} style={inputStyle} />
                  </div>
                  <div style={{ minWidth: 150 }}>
                    <label style={labelStyle}>Sort By</label>
                    <select value={vidSort} onChange={e => setVidSort(e.target.value as typeof vidSort)} style={inputStyle}>
                      <option value="date">Newest first</option>
                      <option value="emv">Highest EMV</option>
                      <option value="duration">Longest</option>
                    </select>
                  </div>
                  {(vidQuery || vidFrom || vidTo) && (
                    <button
                      onClick={() => { setVidQuery(''); setVidFrom(''); setVidTo('') }}
                      style={{
                        background: 'none', border: '1px solid var(--c-wire)', borderRadius: 7,
                        color: 'var(--c-dim)', padding: '9px 14px', fontSize: 12, cursor: 'pointer',
                      }}
                    >
                      Clear
                    </button>
                  )}
                </div>

                {filteredMatches.length === 0 ? (
                  <div style={{
                    padding: '40px 20px', textAlign: 'center', color: 'var(--c-ghost)', fontSize: 13,
                    background: 'var(--c-panel)', border: '1px dashed var(--c-wire)', borderRadius: 10,
                  }}>
                    No matches found for the current filters.
                  </div>
                ) : (
                  <VideoGallery
                    matches={filteredMatches}
                    selectedId={selectedMatchId}
                    onSelect={setSelectedMatchId}
                  />
                )}
              </Section>

              {/* Selected match — full per-video analysis */}
              {selectedMatch && (
                <>
                  <Section title="Match Analysis">
                    <div style={{ marginBottom: 18 }}>
                      <h2 style={{ fontSize: 19, fontWeight: 700, margin: '0 0 6px', letterSpacing: '-0.01em' }}>
                        {result.eventName}
                      </h2>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 14, color: 'var(--c-dim)', fontSize: 12, flexWrap: 'wrap' }}>
                        <span className="num" style={{ fontFamily: 'monospace', color: 'var(--c-ghost)' }}>{result.videoName}</span>
                        <span style={{ color: 'var(--c-wire-s)' }}>·</span>
                        <span>{formatDate(result.analyzedAt)}</span>
                        <span style={{ color: 'var(--c-wire-s)' }}>·</span>
                        <span>{formatNumber(result.metadata.audienceSize)} viewers</span>
                        <span style={{ color: 'var(--c-wire-s)' }}>·</span>
                        <span>{result.metadata.placementType}</span>
                      </div>
                      {result.teamFilter?.enabled && (
                        <div style={{
                          display: 'inline-flex', alignItems: 'center', gap: 7,
                          marginTop: 10, padding: '5px 11px',
                          background: 'var(--c-spark-bg)', border: '1px solid var(--c-wire)',
                          borderRadius: 14, fontSize: 11.5, color: 'var(--c-dim)',
                        }}>
                          <span style={{ width: 7, height: 7, borderRadius: '50%', background: 'var(--c-spark)' }} />
                          Target-team filter:&nbsp;
                          <span className="num" style={{ color: 'var(--c-ink)', fontWeight: 600 }}>{formatNumber(result.teamFilter.kept)}</span>
                          &nbsp;detections kept ·&nbsp;
                          <span className="num" style={{ color: 'var(--c-ink)', fontWeight: 600 }}>{formatNumber(result.teamFilter.dropped)}</span>
                          &nbsp;dropped ({(result.teamFilter.dropRate * 100).toFixed(1)}% on opponents / refs / boards)
                        </div>
                      )}
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 16, marginBottom: 24 }}>
                      <KpiCard label="Match EMV" value={formatCurrency(result.totalEmvUsd)} sub="Equivalent media value" accent />
                      <KpiCard label="Brands Detected" value={String(result.logos.length)} sub={`${totalSegments} appearances`} />
                      <KpiCard label="Quality Exposure" value={formatSeconds(result.totalQualityExposureSeconds)} sub="Visibility-weighted" />
                      <KpiCard label="Avg Visibility" value={`${(result.avgVisibilityScore * 100).toFixed(0)}%`} sub="All detections" />
                    </div>

                    {/* Annotated playback + per-brand on-screen timeline (click to seek) */}
                    {result.previewAvailable ? (
                      <div style={{ background: 'var(--c-panel)', border: '1px solid var(--c-wire)', borderRadius: 10, padding: 12 }}>
                        <DetectionPlayer result={result} />
                        <div style={{ fontSize: 12, color: 'var(--c-ghost)', marginTop: 12 }}>
                          Boxes are model detections (brand + confidence). The bars below show when each
                          brand is on screen — click anywhere on the timeline to jump the video there.
                        </div>
                      </div>
                    ) : (
                      <div style={{
                        padding: '28px 20px', textAlign: 'center', color: 'var(--c-ghost)', fontSize: 13,
                        background: 'var(--c-panel)', border: '1px dashed var(--c-wire)', borderRadius: 10,
                      }}>
                        No annotated preview video for this analysis
                        {usingBackend ? ' — re-run the analysis to generate one.' : ' (demo data).'}
                      </div>
                    )}
                  </Section>

                  <Section title="Brand Breakdown">
                    <div style={{ background: 'var(--c-panel)', border: '1px solid var(--c-wire)', borderRadius: 10, overflow: 'hidden' }}>
                      <LogoTable logos={result.logos} />
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '12px 16px 0', fontSize: 12, color: 'var(--c-ghost)' }}>
                      <span>{result.logos.length} brands · {totalSegments} appearances</span>
                      <span>CPM base ${result.metadata.cpmBase} · {result.metadata.placementType}</span>
                    </div>
                  </Section>
                </>
              )}
            </>
          )}

          {/* ═══════════════════ BRAND INSIGHTS TAB ════════════════════ */}
          {activeTab === 'brands' && (() => {
            const ibKey = insightBrand ?? brandOptions[0]?.key
            const agg = brandOptions.find(b => b.key === ibKey)
            if (!agg) {
              return (
                <div style={{ padding: '40px 20px', textAlign: 'center', color: 'var(--c-ghost)', fontSize: 13 }}>
                  No brand data available yet — run an analysis first.
                </div>
              )
            }

            const sov = portfolio.totalEmv ? agg.totalEmv / portfolio.totalEmv : 0
            const perMatch = chronoMatches.map(m => {
              const logos = m.result.logos.filter(l => (l.class || l.name) === ibKey)
              const emv = logos.reduce((s, l) => s + l.emvUsd, 0)
              const exposure = logos.reduce((s, l) => s + l.totalExposureSeconds, 0)
              const segments = logos.reduce((s, l) => s + l.segmentCount, 0)
              const vis = exposure
                ? logos.reduce((s, l) => s + l.avgVisibilityScore * l.totalExposureSeconds, 0) / exposure
                : 0
              return { m, emv, exposure, segments, vis }
            })
            const appeared = perMatch.filter(p => p.exposure > 0)
            const best = appeared.length ? appeared.reduce((a, b) => a.emv > b.emv ? a : b) : null
            const bestEff = appeared.length
              ? appeared.reduce((a, b) => (a.emv / a.exposure) > (b.emv / b.exposure) ? a : b)
              : null

            // Radar profile — every axis normalised to the best brand in the portfolio.
            const metric = (b: typeof agg) => [
              b.totalEmv,
              b.totalExposure,
              b.avgVisibility,
              b.totalExposure ? b.totalEmv / b.totalExposure : 0,
              b.segmentCount / Math.max(1, b.matchCount),
            ]
            const axisMax = [0, 1, 2, 3, 4].map(i => Math.max(1e-9, ...brandOptions.map(b => metric(b)[i])))
            const norm = (vals: number[]) => vals.map((v, i) => v / axisMax[i])
            const avgVals = [0, 1, 2, 3, 4].map(i =>
              brandOptions.reduce((s, b) => s + metric(b)[i], 0) / Math.max(1, brandOptions.length))

            return (
              <>
                {/* Brand selector chips */}
                <div className="no-print" style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 28 }}>
                  {brandOptions.map(b => {
                    const active = b.key === ibKey
                    return (
                      <button
                        key={b.key}
                        onClick={() => setInsightBrand(b.key)}
                        style={{
                          display: 'flex', alignItems: 'center', gap: 8,
                          background: active ? 'var(--c-hover)' : 'var(--c-panel)',
                          border: `1px solid ${active ? brandColor(b.key) : 'var(--c-wire)'}`,
                          borderRadius: 18,
                          color: active ? 'var(--c-ink)' : 'var(--c-dim)',
                          padding: '7px 14px', fontSize: 12, fontWeight: active ? 700 : 500,
                          cursor: 'pointer', transition: 'all 0.15s',
                        }}
                      >
                        <span style={{ width: 9, height: 9, borderRadius: '50%', background: brandColor(b.key) }} />
                        {b.name}
                      </button>
                    )
                  })}
                </div>

                {/* Brand KPIs */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 16, marginBottom: 36 }}>
                  <KpiCard label="Total EMV" value={formatCurrency(agg.totalEmv)} sub={`${(sov * 100).toFixed(1)}% share of portfolio`} accent />
                  <KpiCard label="Total Exposure" value={formatSeconds(agg.totalExposure)} sub={`${agg.segmentCount} appearances`} />
                  <KpiCard label="Matches Appeared" value={`${agg.matchCount} / ${matches.length}`} sub="Coverage across portfolio" />
                  <KpiCard label="Avg Visibility" value={`${(agg.avgVisibility * 100).toFixed(0)}%`} sub="Exposure-weighted" />
                  <KpiCard label="EMV / Second" value={agg.totalExposure ? formatCurrency(agg.totalEmv / agg.totalExposure) : '—'} sub="Value efficiency" accent />
                  <KpiCard label="Quality Ratio" value={`${agg.totalExposure ? Math.round(agg.qualityExposure / agg.totalExposure * 100) : 0}%`} sub="Quality ÷ raw exposure" />
                </div>

                {/* EMV trend vs portfolio average */}
                <Section title={`${agg.name} — EMV per Match`}>
                  <TrendChart
                    xLabels={chronoLabels}
                    format={v => formatCurrency(v)}
                    yLabel="EMV"
                    series={[
                      { name: agg.name, color: brandColor(agg.key), values: perMatch.map(p => p.emv) },
                      {
                        name: 'Avg brand in match',
                        color: '#52525B',
                        values: chronoMatches.map(m => m.result.logos.length ? m.totalEmv / m.result.logos.length : 0),
                      },
                    ]}
                  />
                </Section>

                {/* Profile radar + highlights */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 32 }}>
                  <Section title="Brand Profile">
                    <RadarChart
                      axes={['EMV', 'Exposure', 'Visibility', 'EMV / s', 'Consistency']}
                      series={[
                        { name: agg.name, color: brandColor(agg.key), values: norm(metric(agg)) },
                        { name: 'Portfolio average', color: '#52525B', values: norm(avgVals) },
                      ]}
                    />
                  </Section>
                  <Section title="Highlights">
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                      {best && (
                        <div
                          onClick={() => { setSelectedMatchId(best.m.id); setActiveTab('videos') }}
                          style={{ background: 'var(--c-panel)', border: '1px solid var(--c-wire)', borderRadius: 10, padding: '14px 18px', cursor: 'pointer' }}
                        >
                          <div style={{ fontSize: 10, color: 'var(--c-ghost)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 6 }}>
                            Best Match by EMV
                          </div>
                          <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--c-spark)' }}>{best.m.eventName}</div>
                          <div style={{ fontSize: 12, color: 'var(--c-dim)', marginTop: 3 }}>
                            {formatCurrency(best.emv)} · {formatSeconds(best.exposure)} on screen · {formatDate(best.m.date)}
                          </div>
                        </div>
                      )}
                      {bestEff && (
                        <div
                          onClick={() => { setSelectedMatchId(bestEff.m.id); setActiveTab('videos') }}
                          style={{ background: 'var(--c-panel)', border: '1px solid var(--c-wire)', borderRadius: 10, padding: '14px 18px', cursor: 'pointer' }}
                        >
                          <div style={{ fontSize: 10, color: 'var(--c-ghost)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 6 }}>
                            Most Efficient Match
                          </div>
                          <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--c-ink)' }}>{bestEff.m.eventName}</div>
                          <div style={{ fontSize: 12, color: 'var(--c-dim)', marginTop: 3 }}>
                            {formatCurrency(bestEff.emv / bestEff.exposure)}/s · {formatDate(bestEff.m.date)}
                          </div>
                        </div>
                      )}
                      <div style={{ background: 'var(--c-panel)', border: '1px solid var(--c-wire)', borderRadius: 10, padding: '14px 18px' }}>
                        <div style={{ fontSize: 10, color: 'var(--c-ghost)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 6 }}>
                          Consistency
                        </div>
                        <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--c-ink)' }}>
                          {(agg.segmentCount / Math.max(1, agg.matchCount)).toFixed(1)} appearances / match
                        </div>
                        <div style={{ fontSize: 12, color: 'var(--c-dim)', marginTop: 3 }}>
                          across {agg.matchCount} {agg.matchCount === 1 ? 'match' : 'matches'}
                        </div>
                      </div>
                    </div>
                  </Section>
                </div>

                {/* Per-match breakdown */}
                <Section title="Per-Match Breakdown">
                  <div style={{ background: 'var(--c-panel)', border: '1px solid var(--c-wire)', borderRadius: 10, overflow: 'hidden' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                      <thead>
                        <tr style={{ borderBottom: '1px solid var(--c-wire)' }}>
                          {['Match', 'Date', 'EMV', 'SoV in match', 'Exposure', 'Avg Vis', 'Segments'].map(h => (
                            <th key={h} style={{
                              textAlign: h === 'Match' || h === 'Date' ? 'left' : 'right',
                              padding: '12px 16px', fontSize: 10, fontWeight: 600,
                              letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--c-ghost)',
                            }}>
                              {h}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {[...perMatch].reverse().map(({ m, emv, exposure, segments, vis }, i, arr) => (
                          <tr
                            key={m.id}
                            onClick={() => { setSelectedMatchId(m.id); setActiveTab('videos') }}
                            style={{
                              borderBottom: i < arr.length - 1 ? '1px solid var(--c-wire)' : 'none',
                              cursor: 'pointer', transition: 'background 0.15s',
                            }}
                            onMouseEnter={e => { e.currentTarget.style.background = 'var(--c-hover)' }}
                            onMouseLeave={e => { e.currentTarget.style.background = 'transparent' }}
                          >
                            <td style={{ padding: '11px 16px', fontWeight: 600, color: 'var(--c-ink)' }}>{m.eventName}</td>
                            <td style={{ padding: '11px 16px', color: 'var(--c-ghost)' }}>{formatDate(m.date)}</td>
                            <td className="num" style={{ padding: '11px 16px', textAlign: 'right', color: 'var(--c-spark)', fontWeight: 600 }}>{formatCurrency(emv)}</td>
                            <td className="num" style={{ padding: '11px 16px', textAlign: 'right', color: 'var(--c-dim)' }}>{m.totalEmv ? (emv / m.totalEmv * 100).toFixed(1) : '0.0'}%</td>
                            <td className="num" style={{ padding: '11px 16px', textAlign: 'right', color: 'var(--c-dim)' }}>{formatSeconds(exposure)}</td>
                            <td className="num" style={{ padding: '11px 16px', textAlign: 'right', color: 'var(--c-dim)' }}>{(vis * 100).toFixed(0)}%</td>
                            <td className="num" style={{ padding: '11px 16px', textAlign: 'right', color: 'var(--c-dim)' }}>{segments}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--c-ghost)', padding: '10px 16px 0' }}>
                    Click a row to open the match's detailed analysis.
                  </div>
                </Section>
              </>
            )
          })()}

          {/* ═══════════════════════ ANALYTICS TAB ═════════════════════ */}
          {activeTab === 'analytics' && (
            <div id="report-root">
              {/* Report scope filters */}
              <div className="no-print" style={{
                display: 'flex', gap: 14, alignItems: 'flex-end', flexWrap: 'wrap',
                background: 'var(--c-panel)', border: '1px solid var(--c-wire)',
                borderRadius: 10, padding: '14px 16px', marginBottom: 28,
              }}>
                <div style={{ minWidth: 240 }}>
                  <label style={labelStyle}>Match Scope</label>
                  <select value={scopeId} onChange={e => setScopeId(e.target.value)} style={inputStyle}>
                    <option value="all">All matches</option>
                    {matches.map(m => <option key={m.id} value={m.id}>{m.eventName}</option>)}
                  </select>
                </div>
                <div style={{ minWidth: 180 }}>
                  <label style={labelStyle}>Brand</label>
                  <select value={brandKey} onChange={e => setBrandKey(e.target.value)} style={inputStyle}>
                    <option value="all">All brands</option>
                    {brandOptions.map(b => <option key={b.key} value={b.key}>{b.name}</option>)}
                  </select>
                </div>
                {scopeId === 'all' && (
                  <>
                    <div>
                      <label style={labelStyle}>From</label>
                      <input type="date" value={repFrom} onChange={e => setRepFrom(e.target.value)} style={inputStyle} />
                    </div>
                    <div>
                      <label style={labelStyle}>To</label>
                      <input type="date" value={repTo} onChange={e => setRepTo(e.target.value)} style={inputStyle} />
                    </div>
                  </>
                )}
                <div style={{ flex: 1 }} />
                <button
                  onClick={exportPDF}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 7,
                    background: 'var(--c-spark)', color: '#000',
                    border: 'none', borderRadius: 7,
                    padding: '10px 16px', fontSize: 12, fontWeight: 700, cursor: 'pointer',
                  }}
                >
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" />
                  </svg>
                  Export PDF
                </button>
              </div>

              {/* Report header (visible in the printed PDF) */}
              <div style={{ marginBottom: 24 }}>
                <h2 style={{ fontSize: 19, fontWeight: 700, margin: '0 0 6px' }}>
                  Analytics Report — {scopeId === 'all' ? `All Matches${repFrom || repTo ? ` (${repFrom || '…'} → ${repTo || '…'})` : ''}` : scopeMatches[0]?.eventName}
                </h2>
                <div style={{ fontSize: 12, color: 'var(--c-ghost)' }}>
                  {brandKey !== 'all' ? `Brand: ${brandOptions.find(b => b.key === brandKey)?.name ?? brandKey} · ` : ''}
                  Generated {new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })} · Sightline
                </div>
              </div>

              {/* Scope KPIs */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 16, marginBottom: 36 }}>
                <KpiCard label="EMV" value={formatCurrency(scopeTotalEmv)} sub={scopeId === 'all' ? `${scopeMatches.length} matches in scope` : 'This match'} accent />
                <KpiCard label="Total Exposure" value={formatSeconds(scopeTotalExposure)} sub="Raw on-screen time" />
                <KpiCard label="Quality Exposure" value={formatSeconds(scopeTotalQuality)} sub={`${scopeTotalExposure ? Math.round(scopeTotalQuality / scopeTotalExposure * 100) : 0}% of raw exposure`} />
                <KpiCard label="EMV / Second" value={scopeTotalExposure ? formatCurrency(scopeTotalEmv / scopeTotalExposure) : '—'} sub="Media value per exposed second" />
              </div>

              {/* Single-match scope: time-series + distribution charts */}
              {chartResult && (
                <>
                  <Section title="Exposure Over Time">
                    <ExposureLineChart result={chartResult} />
                  </Section>
                  {brandKey === 'all' && (
                    <Section title="Exposure Distribution">
                      <ExposurePieChart result={chartResult} />
                    </Section>
                  )}

                  {/* Quality of each appearance — duration vs visibility */}
                  <Section title="Appearance Quality Map">
                    <ScatterChart
                      xLabel="Segment duration"
                      yLabel="Avg visibility"
                      formatX={v => formatSeconds(v)}
                      formatY={v => `${Math.round(v)}%`}
                      points={chartResult.logos.flatMap(l => l.segments.map(seg => ({
                        x: seg.endTime - seg.startTime,
                        y: seg.avgVisibility * 100,
                        color: getBrandColor(l.id),
                        label: l.name,
                        sub: `${formatSeconds(seg.startTime)} → ${formatSeconds(seg.endTime)}`,
                      })))}
                    />
                    <div style={{ fontSize: 12, color: 'var(--c-ghost)', padding: '10px 16px 0' }}>
                      Each dot is one on-screen appearance. Top-right = long, highly visible segments
                      (premium inventory); bottom-left = brief, low-visibility flashes.
                    </div>
                  </Section>

                  {/* Raw vs quality exposure per brand */}
                  <Section title="Exposure Quality by Brand">
                    <div style={{ background: 'var(--c-panel)', border: '1px solid var(--c-wire)', borderRadius: 10, padding: '14px 18px' }}>
                      {[...chartResult.logos].sort((a, b) => b.totalExposureSeconds - a.totalExposureSeconds).map(l => {
                        const maxExp = Math.max(...chartResult.logos.map(x => x.totalExposureSeconds), 1e-6)
                        const qFrac = l.totalExposureSeconds ? l.qualityExposureSeconds / l.totalExposureSeconds : 0
                        return (
                          <div key={l.id} style={{ display: 'flex', alignItems: 'center', gap: 14, padding: '7px 0' }}>
                            <div style={{ width: 160, fontSize: 12.5, fontWeight: 600, color: 'var(--c-ink)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                              {l.name}
                            </div>
                            <div style={{ flex: 1, height: 14, background: 'var(--c-wire)', borderRadius: 4, overflow: 'hidden', position: 'relative' }}>
                              <div style={{
                                position: 'absolute', inset: 0,
                                width: `${(l.totalExposureSeconds / maxExp) * 100}%`,
                                background: 'rgba(197,240,0,0.22)', borderRadius: 4,
                              }} />
                              <div style={{
                                position: 'absolute', top: 0, bottom: 0, left: 0,
                                width: `${(l.totalExposureSeconds / maxExp) * qFrac * 100}%`,
                                background: getBrandColor(l.id), borderRadius: 4,
                              }} />
                            </div>
                            <span className="num" style={{ fontSize: 12, color: 'var(--c-dim)', width: 120, textAlign: 'right' }}>
                              {formatSeconds(l.qualityExposureSeconds)} / {formatSeconds(l.totalExposureSeconds)}
                            </span>
                            <span className="num" style={{ fontSize: 12, fontWeight: 600, color: 'var(--c-spark)', width: 42, textAlign: 'right' }}>
                              {Math.round(qFrac * 100)}%
                            </span>
                          </div>
                        )
                      })}
                      <div style={{ fontSize: 11.5, color: 'var(--c-ghost)', marginTop: 10 }}>
                        Solid bar = quality (visibility-weighted) exposure inside the brand's total on-screen time (tinted).
                      </div>
                    </div>
                  </Section>
                </>
              )}

              {/* All-matches scope: SoV donut + brand trend + heatmap + comparison */}
              {!scopeResult && scopeMatches.length > 0 && (() => {
                const scopeBrands = aggregateBrands(scopeMatches)
                const scopeChrono = [...scopeMatches].sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())
                const scopeLabels = scopeChrono.map(m => new Date(m.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }))
                const heatBrands = brandKey === 'all' ? scopeBrands.slice(0, 10) : scopeBrands.filter(b => b.key === brandKey)
                return (
                  <>
                    {brandKey === 'all' && (
                      <Section title="Share of Voice">
                        <DonutChart
                          centerLabel="Scope EMV"
                          format={v => formatCurrency(v)}
                          data={[
                            ...scopeBrands.slice(0, 8).map(b => ({ label: b.name, value: b.totalEmv, color: brandColor(b.key) })),
                            ...(scopeBrands.length > 8 ? [{
                              label: 'Other',
                              value: scopeBrands.slice(8).reduce((s, b) => s + b.totalEmv, 0),
                              color: '#52525B',
                            }] : []),
                          ]}
                        />
                      </Section>
                    )}

                    <Section title="EMV Trend by Brand">
                      <TrendChart
                        xLabels={scopeLabels}
                        format={v => formatCurrency(v)}
                        yLabel="EMV per match"
                        series={(brandKey === 'all' ? scopeBrands.slice(0, 5) : heatBrands).map(b => ({
                          name: b.name,
                          color: brandColor(b.key),
                          values: scopeChrono.map(m => brandEmvIn(m, b.key)),
                        }))}
                      />
                    </Section>

                    <Section title="Brand × Match Heatmap (EMV)">
                      <HeatmapGrid
                        rows={heatBrands.map(b => b.name)}
                        cols={scopeLabels}
                        values={heatBrands.map(b => scopeChrono.map(m => brandEmvIn(m, b.key)))}
                        format={v => v >= 1000 ? `$${Math.round(v / 1000)}k` : `$${Math.round(v)}`}
                        onCellClick={(_r, c) => { setSelectedMatchId(scopeChrono[c].id); setActiveTab('videos') }}
                      />
                      <div style={{ fontSize: 12, color: 'var(--c-ghost)', padding: '10px 16px 0' }}>
                        Click a cell to open that match's analysis.
                      </div>
                    </Section>

                    <Section title="Match Comparison">
                      <div style={{ background: 'var(--c-panel)', border: '1px solid var(--c-wire)', borderRadius: 10, padding: '10px 4px' }}>
                        {[...scopeMatches].sort((a, b) => b.totalEmv - a.totalEmv).map(m => {
                          const emv = brandKey === 'all' ? m.totalEmv : brandEmvIn(m, brandKey)
                          const maxEmv = Math.max(...scopeMatches.map(x => brandKey === 'all' ? x.totalEmv : brandEmvIn(x, brandKey)))
                          return (
                            <BarRow
                              key={m.id}
                              label={m.eventName}
                              sub={`${formatDate(m.date)} · ${formatSeconds(m.durationSeconds)}`}
                              value={formatCurrency(emv)}
                              frac={maxEmv ? emv / maxEmv : 0}
                              onClick={() => { setSelectedMatchId(m.id); setActiveTab('videos') }}
                            />
                          )
                        })}
                      </div>
                    </Section>
                  </>
                )
              })()}

              {/* Brand performance table — business metrics */}
              <Section title="Brand Performance">
                <div style={{ background: 'var(--c-panel)', border: '1px solid var(--c-wire)', borderRadius: 10, overflow: 'hidden' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                    <thead>
                      <tr style={{ borderBottom: '1px solid var(--c-wire)' }}>
                        {['Brand', 'EMV', 'SoV', 'Exposure', 'Quality Ratio', 'Avg Visibility', 'EMV / s', 'Segments', ...(scopeResult ? [] : ['Matches'])].map(h => (
                          <th key={h} style={{
                            textAlign: h === 'Brand' ? 'left' : 'right',
                            padding: '12px 16px', fontSize: 10, fontWeight: 600,
                            letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--c-ghost)',
                          }}>
                            {h}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {reportRows.map((r, i) => (
                        <tr key={r.key} style={{ borderBottom: i < reportRows.length - 1 ? '1px solid var(--c-wire)' : 'none' }}>
                          <td style={{ padding: '11px 16px', fontWeight: 600, color: 'var(--c-ink)' }}>{r.name}</td>
                          <td className="num" style={{ padding: '11px 16px', textAlign: 'right', color: 'var(--c-spark)', fontWeight: 600 }}>{formatCurrency(r.emv)}</td>
                          <td className="num" style={{ padding: '11px 16px', textAlign: 'right', color: 'var(--c-dim)' }}>{sovDenom ? (r.emv / sovDenom * 100).toFixed(1) : '0.0'}%</td>
                          <td className="num" style={{ padding: '11px 16px', textAlign: 'right', color: 'var(--c-dim)' }}>{formatSeconds(r.exposure)}</td>
                          <td className="num" style={{ padding: '11px 16px', textAlign: 'right', color: 'var(--c-dim)' }}>{r.exposure ? Math.round(r.quality / r.exposure * 100) : 0}%</td>
                          <td className="num" style={{ padding: '11px 16px', textAlign: 'right', color: 'var(--c-dim)' }}>{(r.avgVis * 100).toFixed(0)}%</td>
                          <td className="num" style={{ padding: '11px 16px', textAlign: 'right', color: 'var(--c-dim)' }}>{r.exposure ? formatCurrency(r.emv / r.exposure) : '—'}</td>
                          <td className="num" style={{ padding: '11px 16px', textAlign: 'right', color: 'var(--c-dim)' }}>{r.segments}</td>
                          {!scopeResult && <td className="num" style={{ padding: '11px 16px', textAlign: 'right', color: 'var(--c-dim)' }}>{r.matches}</td>}
                        </tr>
                      ))}
                      {reportRows.length === 0 && (
                        <tr><td colSpan={9} style={{ padding: '24px 16px', textAlign: 'center', color: 'var(--c-ghost)' }}>No data for the current filters.</td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
                <div style={{ fontSize: 12, color: 'var(--c-ghost)', padding: '10px 16px 0' }}>
                  SoV = share of voice (brand EMV ÷ scope EMV) · Quality Ratio = visibility-weighted ÷ raw exposure ·
                  EMV/s = media value generated per second on screen.
                </div>
              </Section>

              {/* Scope highlights */}
              {reportRows.length > 0 && (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 32 }}>
                  <div style={{ background: 'var(--c-panel)', border: '1px solid var(--c-wire)', borderRadius: 10, padding: '16px 20px' }}>
                    <div style={{ fontSize: 10, color: 'var(--c-ghost)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 8 }}>
                      Most Exposed Brand
                    </div>
                    <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--c-spark)' }}>
                      {reportRows.reduce((a, b) => a.exposure > b.exposure ? a : b).name}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--c-dim)', marginTop: 4 }}>
                      {formatSeconds(reportRows.reduce((a, b) => a.exposure > b.exposure ? a : b).exposure)} total exposure
                    </div>
                  </div>
                  <div style={{ background: 'var(--c-panel)', border: '1px solid var(--c-wire)', borderRadius: 10, padding: '16px 20px' }}>
                    <div style={{ fontSize: 10, color: 'var(--c-ghost)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 8 }}>
                      Highest Visibility
                    </div>
                    <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--c-ink)' }}>
                      {reportRows.reduce((a, b) => a.avgVis > b.avgVis ? a : b).name}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--c-dim)', marginTop: 4 }}>
                      {(reportRows.reduce((a, b) => a.avgVis > b.avgVis ? a : b).avgVis * 100).toFixed(0)}% avg visibility
                    </div>
                  </div>
                  <div style={{ background: 'var(--c-panel)', border: '1px solid var(--c-wire)', borderRadius: 10, padding: '16px 20px' }}>
                    <div style={{ fontSize: 10, color: 'var(--c-ghost)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 8 }}>
                      Best EMV Efficiency
                    </div>
                    <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--c-spark)' }}>
                      {reportRows.filter(r => r.exposure > 0).reduce((a, b) => a.emv / a.exposure > b.emv / b.exposure ? a : b, reportRows[0]).name}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--c-dim)', marginTop: 4 }}>
                      Highest media value per second
                    </div>
                  </div>
                </div>
              )}

              {/* Methodology note */}
              <div style={{
                padding: '16px 20px',
                background: 'var(--c-panel)',
                border: '1px solid var(--c-wire)',
                borderRadius: 8,
                fontSize: 12,
                color: 'var(--c-ghost)',
                lineHeight: 1.7,
              }}>
                <strong style={{ color: 'var(--c-dim)', fontWeight: 600 }}>Methodology · </strong>
                EMV = Quality Exposure × (CPM / 1000) × Audience × Placement Multiplier.
                Quality Exposure is calculated per segment as Duration × Avg Visibility Score × Duration Weight.
                Visibility score incorporates bounding box size, screen position (Gaussian), detection confidence, and OBB orientation penalty.
                Based on ExposureEngine methodology (arxiv 2510.04739) and Relo Metrics industry standard.
              </div>
            </div>
          )}

          {/* ═══════════════════════ BODY TAB ══════════════════════════ */}
          {activeTab === 'body' && (
            <>
              <div style={{ fontSize: 12, color: 'var(--c-ghost)', marginBottom: 18 }}>
                Showing body-zone exposure for: <strong style={{ color: 'var(--c-dim)' }}>{result.eventName}</strong>
                {' '}— change the match in the Match Videos tab.
              </div>

              {result.bodysegAvailable && (
                <Section title="Body-Part Segmentation — DensePose">
                  <div style={{ background: 'var(--c-panel)', border: '1px solid var(--c-wire)', borderRadius: 10, padding: 12 }}>
                    <video
                      key={`seg-${result.id}`}
                      src={bodysegVideoUrl(result.id)}
                      controls
                      playsInline
                      style={{ width: '100%', borderRadius: 8, display: 'block', background: '#000' }}
                    />
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px 14px', marginTop: 12 }}>
                      {[
                        ['Head', '#FF6347'], ['Torso', '#3CB44B'], ['Upper Arm', '#0082C8'],
                        ['Lower Arm', '#911EB4'], ['Hands', '#F58230'], ['Upper Leg', '#FFE119'],
                        ['Lower Leg', '#46F0F0'], ['Feet', '#F032E6'],
                      ].map(([name, color]) => (
                        <div key={name} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          <span style={{ width: 11, height: 11, borderRadius: 3, background: color }} />
                          <span style={{ fontSize: 12, color: 'var(--c-dim)' }}>
                            {name}
                            {result.bodysegGroups?.[name] != null && (
                              <span className="num" style={{ color: 'var(--c-ghost)', marginLeft: 5 }}>
                                {result.bodysegGroups[name]}%
                              </span>
                            )}
                          </span>
                        </div>
                      ))}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--c-ghost)', marginTop: 10 }}>
                      Every player pixel mapped to a body region (DensePose, 24 surface parts grouped into 8).
                      Percentages are share of segmented player pixels across analysed frames.
                    </div>
                  </div>
                </Section>
              )}

              <Section title="Body Zone Exposure Analysis">
                <BodySegmentation3D zones={result.bodyZones} />
              </Section>
            </>
          )}

        </div>
      </div>
    </div>
  )
}
