'use client'

import { useEffect, useState } from 'react'
import Nav from '@/components/nav'
import Timeline from '@/components/dashboard/timeline'
import LogoTable from '@/components/dashboard/logo-table'
import PipelineView from '@/components/dashboard/pipeline'
import { MOCK_RESULT } from '@/lib/mock-data'
import { formatCurrency, formatDate, formatNumber, formatSeconds, exportCSV } from '@/lib/utils'
import type { AnalysisResult, EventMeta } from '@/lib/types'

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section style={{ marginBottom: 32 }}>
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

export default function DashboardPage() {
  const [result, setResult] = useState<AnalysisResult>(MOCK_RESULT)
  const [meta, setMeta] = useState<EventMeta | null>(null)

  useEffect(() => {
    try {
      const raw = localStorage.getItem('sl_meta')
      if (raw) {
        const m: EventMeta = JSON.parse(raw)
        setMeta(m)
        // Merge user-provided metadata into mock result display
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
  }, [])

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

        {/* Event header */}
        <div style={{ marginBottom: 32 }} className="slide-up">
          <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--c-spark)', marginBottom: 8 }}>
            Analysis Report
          </div>
          <h1 style={{ fontSize: 26, fontWeight: 700, margin: '0 0 8px', letterSpacing: '-0.02em' }}>
            {result.eventName}
          </h1>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16, color: 'var(--c-dim)', fontSize: 13 }}>
            <span className="num" style={{ fontFamily: 'monospace', color: 'var(--c-ghost)', fontSize: 12 }}>
              {result.videoName}
            </span>
            <span style={{ color: 'var(--c-wire-s)' }}>·</span>
            <span>{formatDate(result.analyzedAt)}</span>
            <span style={{ color: 'var(--c-wire-s)' }}>·</span>
            <span>{formatNumber(result.metadata.audienceSize)} viewers</span>
            <span style={{ color: 'var(--c-wire-s)' }}>·</span>
            <span>{result.metadata.placementType}</span>
          </div>
        </div>

        {/* KPI cards */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 16, marginBottom: 36 }} className="slide-up">
          <KpiCard
            label="Total EMV"
            value={formatCurrency(result.totalEmvUsd)}
            sub="Equivalent media value"
            accent
          />
          <KpiCard
            label="Brands Detected"
            value={String(result.logos.length)}
            sub={`${totalSegments} total appearances`}
          />
          <KpiCard
            label="Quality Exposure"
            value={formatSeconds(result.totalQualityExposureSeconds)}
            sub="Visibility-weighted"
          />
          <KpiCard
            label="Avg Visibility"
            value={`${(result.avgVisibilityScore * 100).toFixed(0)}%`}
            sub="Across all detections"
          />
        </div>

        {/* Pipeline */}
        <Section title="Processing Pipeline">
          <div style={{
            background: 'var(--c-panel)',
            border: '1px solid var(--c-wire)',
            borderRadius: 10,
            padding: '20px 20px 18px',
          }}>
            <PipelineView result={result} />
          </div>
        </Section>

        {/* Timeline */}
        <Section title="Brand Timeline">
          <div style={{
            background: 'var(--c-panel)',
            border: '1px solid var(--c-wire)',
            borderRadius: 10,
            padding: '20px 20px 24px',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
              <div style={{ fontSize: 12, color: 'var(--c-dim)' }}>
                {formatSeconds(result.videoDurationSeconds)} broadcast · hover segments for details
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 14, fontSize: 11, color: 'var(--c-ghost)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <div style={{ width: 24, height: 8, borderRadius: 2, background: 'rgba(197,240,0,0.9)' }} />
                  High visibility
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <div style={{ width: 24, height: 8, borderRadius: 2, background: 'rgba(197,240,0,0.4)' }} />
                  Low visibility
                </div>
              </div>
            </div>
            <Timeline logos={result.logos} videoDuration={result.videoDurationSeconds} />
          </div>
        </Section>

        {/* Table */}
        <Section title="Brand Breakdown">
          <div style={{
            background: 'var(--c-panel)',
            border: '1px solid var(--c-wire)',
            borderRadius: 10,
            overflow: 'hidden',
          }}>
            <LogoTable logos={result.logos} />
          </div>

          {/* Table footer */}
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            padding: '12px 16px 0',
            fontSize: 12,
            color: 'var(--c-ghost)',
          }}>
            <span>{result.logos.length} brands · {totalSegments} appearances</span>
            <span>CPM base ${result.metadata.cpmBase} · {result.metadata.placementType}</span>
          </div>
        </Section>

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
    </div>
  )
}
