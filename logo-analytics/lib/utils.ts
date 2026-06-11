import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'
import type { AnalysisResult, MatchEntry } from './types'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatSeconds(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`
  const m = Math.floor(seconds / 60)
  const s = Math.round(seconds % 60)
  return s > 0 ? `${m}m ${s}s` : `${m}m`
}

export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(amount)
}

export function formatNumber(n: number): string {
  return new Intl.NumberFormat('en-US').format(n)
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', {
    year: 'numeric', month: 'short', day: 'numeric',
  })
}

export function visibilityOpacity(score: number): number {
  return 0.25 + score * 0.75
}

// ── Portfolio aggregation (Overview / Analytics "All matches" scope) ──

export interface BrandAgg {
  key: string
  name: string
  totalEmv: number
  totalExposure: number
  qualityExposure: number
  avgVisibility: number   // exposure-weighted across matches
  segmentCount: number
  matchCount: number
}

export function aggregateBrands(matches: MatchEntry[]): BrandAgg[] {
  const map = new Map<string, BrandAgg & { _visW: number }>()
  for (const m of matches) {
    for (const l of m.result.logos) {
      const key = l.class || l.name
      let b = map.get(key)
      if (!b) {
        b = {
          key, name: l.name, totalEmv: 0, totalExposure: 0, qualityExposure: 0,
          avgVisibility: 0, segmentCount: 0, matchCount: 0, _visW: 0,
        }
        map.set(key, b)
      }
      b.totalEmv += l.emvUsd
      b.totalExposure += l.totalExposureSeconds
      b.qualityExposure += l.qualityExposureSeconds
      b.segmentCount += l.segmentCount
      b.avgVisibility += l.avgVisibilityScore * l.totalExposureSeconds
      b._visW += l.totalExposureSeconds
      b.matchCount += 1
    }
  }
  return Array.from(map.values())
    .map(({ _visW, ...b }) => ({ ...b, avgVisibility: _visW ? b.avgVisibility / _visW : 0 }))
    .sort((a, b) => b.totalEmv - a.totalEmv)
}

/** Match filter shared by the Videos tab and report scopes. */
export function filterMatches(
  matches: MatchEntry[],
  query: string,
  dateFrom: string,
  dateTo: string,
): MatchEntry[] {
  const q = query.trim().toLowerCase()
  return matches.filter(m => {
    if (q && !m.eventName.toLowerCase().includes(q) && !m.videoName.toLowerCase().includes(q)) return false
    const t = new Date(m.date).getTime()
    if (dateFrom && t < new Date(dateFrom).getTime()) return false
    // +1 day so an inclusive "to" date covers the whole day.
    if (dateTo && t >= new Date(dateTo).getTime() + 86_400_000) return false
    return true
  })
}

/** Print-based PDF export — print CSS in globals.css isolates #report-root. */
export function exportPDF(): void {
  window.print()
}

export function exportCSV(result: AnalysisResult): void {
  const header = ['Brand', 'Total Exposure (s)', 'Quality Exposure (s)', 'Avg Visibility', 'Segments', 'Longest Segment (s)', 'EMV (USD)']
  const rows = result.logos.map(l => [
    l.name,
    l.totalExposureSeconds,
    l.qualityExposureSeconds.toFixed(1),
    l.avgVisibilityScore.toFixed(2),
    l.segmentCount,
    l.longestSegmentSeconds,
    l.emvUsd,
  ])
  const csv = [header, ...rows].map(r => r.join(',')).join('\n')
  const blob = new Blob([csv], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `sightline-${result.eventName.replace(/\s+/g, '_')}.csv`
  a.click()
  URL.revokeObjectURL(url)
}
