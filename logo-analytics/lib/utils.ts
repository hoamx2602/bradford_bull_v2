import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'
import type { AnalysisResult } from './types'

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
