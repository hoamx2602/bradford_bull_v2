import type { AnalysisResult, LogoResult, Segment } from './types'

// Deterministic seeded value — always same output for same seed
const s = (seed: number) => {
  const x = Math.sin(seed + 1) * 10000
  return x - Math.floor(x)
}

interface LogoCfg {
  name: string
  cls: string
  count: number
  avgDur: number
  avgVis: number
  emv: number
}

const VIDEO_DURATION = 5400 // 90 min

function buildSegments(cfg: LogoCfg, li: number): Segment[] {
  const segs: Segment[] = []
  const span = VIDEO_DURATION * 0.92

  for (let j = 0; j < cfg.count; j++) {
    const base = (j / cfg.count) * span
    const jitter = (s(li * 300 + j * 7) - 0.5) * (span / cfg.count) * 0.7
    const start = Math.max(0, Math.min(span - 20, base + jitter))
    const dur = Math.max(1.5, cfg.avgDur * (0.45 + s(li * 300 + j * 7 + 1) * 1.1))
    const end = Math.min(VIDEO_DURATION, start + dur)
    const vis = Math.max(0.28, Math.min(0.97, cfg.avgVis + (s(li * 300 + j * 7 + 2) - 0.5) * 0.22))
    segs.push({
      startTime: Math.round(start),
      endTime: Math.round(end),
      avgVisibility: Math.round(vis * 100) / 100,
      durationWeight: dur < 1 ? 0.5 : dur < 5 ? 1.0 : 1.2,
    })
  }
  return segs.sort((a, b) => a.startTime - b.startTime)
}

function buildLogo(cfg: LogoCfg, idx: number): LogoResult {
  const segments = buildSegments(cfg, idx)
  const totalExp = segments.reduce((s, g) => s + (g.endTime - g.startTime), 0)
  const qualExp = segments.reduce(
    (s, g) => s + (g.endTime - g.startTime) * g.avgVisibility * g.durationWeight, 0
  )
  const avgVis = segments.reduce((s, g) => s + g.avgVisibility, 0) / segments.length
  const longest = Math.max(...segments.map(g => g.endTime - g.startTime))

  return {
    id: `logo-${idx}`,
    name: cfg.name,
    class: cfg.cls,
    segments,
    totalExposureSeconds: Math.round(totalExp),
    qualityExposureSeconds: Math.round(qualExp * 10) / 10,
    avgVisibilityScore: Math.round(avgVis * 100) / 100,
    segmentCount: segments.length,
    longestSegmentSeconds: Math.round(longest),
    emvUsd: cfg.emv,
  }
}

const CONFIGS: LogoCfg[] = [
  { name: 'Castore',                cls: 'castore',                  count: 28, avgDur: 9.5, avgVis: 0.84, emv: 63360 },
  { name: 'Bartercard',             cls: 'bartercard',               count: 24, avgDur: 7.5, avgVis: 0.79, emv: 47520 },
  { name: 'Kinetic',                cls: 'kinetic',                  count: 16, avgDur: 6.0, avgVis: 0.72, emv: 25080 },
  { name: 'Summit',                 cls: 'summit',                   count: 11, avgDur: 5.5, avgVis: 0.68, emv: 15840 },
  { name: 'ACS Group',              cls: 'acs_group',                count:  9, avgDur: 5.0, avgVis: 0.65, emv: 11880 },
  { name: 'MNA Cladding',           cls: 'mna_cladding',             count:  7, avgDur: 4.5, avgVis: 0.62, emv:  7920 },
  { name: 'ATM Hospitality',        cls: 'atm_hospitality',          count:  5, avgDur: 5.0, avgVis: 0.61, emv:  6600 },
  { name: 'Sports Events Services', cls: 'Sports Events Services',   count:  4, avgDur: 5.0, avgVis: 0.73, emv:  5280 },
  { name: 'KLG',                    cls: 'klg',                      count:  3, avgDur: 5.0, avgVis: 0.58, emv:  3960 },
  { name: 'Floor Tonic',            cls: 'floor_tonic',              count:  2, avgDur: 4.0, avgVis: 0.55, emv:  2112 },
]

const logos = CONFIGS.map((cfg, i) => buildLogo(cfg, i))

export const MOCK_RESULT: AnalysisResult = {
  id: 'analysis-001',
  eventName: 'Arsenal vs Chelsea — Premier League',
  videoName: 'Premier_League_Arsenal_Chelsea_2026.mp4',
  videoDurationSeconds: VIDEO_DURATION,
  analyzedAt: '2026-06-06T14:32:11Z',
  metadata: {
    audienceSize: 2_400_000,
    placementType: 'Live Broadcast TV',
    cpmBase: 22,
    placementMultiplier: 1.0,
  },
  logos,
  totalEmvUsd: logos.reduce((s, l) => s + l.emvUsd, 0),
  totalQualityExposureSeconds: logos.reduce((s, l) => s + l.qualityExposureSeconds, 0),
  avgVisibilityScore:
    Math.round((logos.reduce((s, l) => s + l.avgVisibilityScore, 0) / logos.length) * 100) / 100,
}
