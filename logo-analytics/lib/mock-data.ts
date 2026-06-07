import type { AnalysisResult, LogoResult, Segment, MatchEntry, BodyZone, TimeSeriesPoint } from './types'

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

// ── Brand color palette for charts ──────────────────────────────────

export const BRAND_COLORS: Record<string, string> = {
  'logo-0': '#C5F000', // Castore — spark green
  'logo-1': '#00D4FF', // Bartercard — cyan
  'logo-2': '#FF6B6B', // Kinetic — coral
  'logo-3': '#A78BFA', // Summit — violet
  'logo-4': '#F59E0B', // ACS Group — amber
  'logo-5': '#34D399', // MNA Cladding — emerald
  'logo-6': '#F472B6', // ATM Hospitality — pink
  'logo-7': '#60A5FA', // Sports Events — blue
  'logo-8': '#FBBF24', // KLG — gold
  'logo-9': '#A3E635', // Floor Tonic — lime
}

export function getBrandColor(logoId: string): string {
  return BRAND_COLORS[logoId] || '#787878'
}

// ── Multiple match entries ──────────────────────────────────────────

function buildMatchResult(
  id: string,
  eventName: string,
  videoName: string,
  date: string,
  audienceSize: number,
  emvMultiplier: number,
): AnalysisResult {
  const matchLogos = CONFIGS.map((cfg, i) => {
    const adjusted = { ...cfg, emv: Math.round(cfg.emv * emvMultiplier) }
    return buildLogo(adjusted, i + parseInt(id.replace('match-', '')) * 100)
  })

  return {
    id: `analysis-${id}`,
    eventName,
    videoName,
    videoDurationSeconds: VIDEO_DURATION,
    analyzedAt: date,
    metadata: {
      audienceSize,
      placementType: 'Live Broadcast TV',
      cpmBase: 22,
      placementMultiplier: 1.0,
    },
    logos: matchLogos,
    totalEmvUsd: matchLogos.reduce((s, l) => s + l.emvUsd, 0),
    totalQualityExposureSeconds: matchLogos.reduce((s, l) => s + l.qualityExposureSeconds, 0),
    avgVisibilityScore:
      Math.round((matchLogos.reduce((s, l) => s + l.avgVisibilityScore, 0) / matchLogos.length) * 100) / 100,
  }
}

export const MOCK_MATCHES: MatchEntry[] = [
  {
    id: 'match-1',
    eventName: 'Arsenal vs Chelsea — Premier League',
    date: '2026-06-06T14:32:11Z',
    videoName: 'Premier_League_Arsenal_Chelsea_2026.mp4',
    durationSeconds: 5400,
    logoCount: 10,
    totalEmv: MOCK_RESULT.totalEmvUsd,
    result: MOCK_RESULT,
  },
  {
    id: 'match-2',
    eventName: 'Bradford Bulls vs Leeds Rhinos — Super League',
    date: '2026-05-28T19:45:00Z',
    videoName: 'SuperLeague_Bradford_Leeds_2026.mp4',
    durationSeconds: 4800,
    logoCount: 10,
    totalEmv: 158400,
    result: buildMatchResult('match-2', 'Bradford Bulls vs Leeds Rhinos — Super League', 'SuperLeague_Bradford_Leeds_2026.mp4', '2026-05-28T19:45:00Z', 1_800_000, 0.85),
  },
  {
    id: 'match-3',
    eventName: 'Wigan Warriors vs Bradford Bulls — Challenge Cup',
    date: '2026-05-15T15:00:00Z',
    videoName: 'ChallengeCup_Wigan_Bradford_2026.mp4',
    durationSeconds: 4800,
    logoCount: 10,
    totalEmv: 142560,
    result: buildMatchResult('match-3', 'Wigan Warriors vs Bradford Bulls — Challenge Cup', 'ChallengeCup_Wigan_Bradford_2026.mp4', '2026-05-15T15:00:00Z', 1_500_000, 0.76),
  },
  {
    id: 'match-4',
    eventName: 'Bradford Bulls vs Hull FC — Super League',
    date: '2026-04-30T20:00:00Z',
    videoName: 'SuperLeague_Bradford_Hull_2026.mp4',
    durationSeconds: 5400,
    logoCount: 10,
    totalEmv: 169200,
    result: buildMatchResult('match-4', 'Bradford Bulls vs Hull FC — Super League', 'SuperLeague_Bradford_Hull_2026.mp4', '2026-04-30T20:00:00Z', 2_100_000, 0.9),
  },
]

// ── Time-series data for line chart ─────────────────────────────────

export function buildTimeSeries(result: AnalysisResult): TimeSeriesPoint[] {
  const points: TimeSeriesPoint[] = []
  const interval = 300 // 5-minute intervals
  const steps = Math.ceil(result.videoDurationSeconds / interval)

  for (const logo of result.logos) {
    let cumulative = 0
    for (let step = 0; step <= steps; step++) {
      const minuteMark = step * (interval / 60)
      const timeNow = step * interval

      // Sum exposure from segments that end before this time point
      for (const seg of logo.segments) {
        if (seg.startTime < timeNow && seg.endTime <= timeNow) {
          const dur = seg.endTime - seg.startTime
          if (!points.some(p => p.minuteMark === minuteMark && p.logoId === logo.id)) {
            // Only count once
          }
        }
      }

      // Calculate cumulative exposure up to this time point
      cumulative = logo.segments
        .filter(seg => seg.startTime < timeNow)
        .reduce((sum, seg) => {
          const effectiveEnd = Math.min(seg.endTime, timeNow)
          return sum + (effectiveEnd - seg.startTime) * seg.avgVisibility
        }, 0)

      points.push({
        minuteMark,
        logoId: logo.id,
        logoName: logo.name,
        cumulativeExposure: Math.round(cumulative * 10) / 10,
      })
    }
  }

  return points
}

// ── Body zone exposure data (23 zones) ─────────────────────────────

export const BODY_ZONES: BodyZone[] = [
  { id: 'head',         name: 'Head',          percentage:  4.1, color: '' },
  { id: 'neck',         name: 'Neck',          percentage:  2.3, color: '' },
  { id: 'shoulder-l',   name: 'Shoulder L',    percentage:  8.2, color: '' },
  { id: 'shoulder-r',   name: 'Shoulder R',    percentage:  7.6, color: '' },
  { id: 'chest-l',      name: 'Chest Left',    percentage: 15.8, color: '' },
  { id: 'chest-r',      name: 'Chest Right',   percentage: 14.2, color: '' },
  { id: 'upper-arm-l',  name: 'Upper Arm L',   percentage: 10.4, color: '' },
  { id: 'upper-arm-r',  name: 'Upper Arm R',   percentage:  9.1, color: '' },
  { id: 'forearm-l',    name: 'Forearm L',     percentage:  5.3, color: '' },
  { id: 'forearm-r',    name: 'Forearm R',     percentage:  4.8, color: '' },
  { id: 'hand-l',       name: 'Hand L',        percentage:  2.1, color: '' },
  { id: 'hand-r',       name: 'Hand R',        percentage:  1.9, color: '' },
  { id: 'spine',        name: 'Spine',         percentage:  2.0, color: '' },
  { id: 'back-l',       name: 'Back L',        percentage:  5.4, color: '' },
  { id: 'back-r',       name: 'Back R',        percentage:  4.8, color: '' },
  { id: 'hip-l',        name: 'Hip L',         percentage:  6.2, color: '' },
  { id: 'hip-r',        name: 'Hip R',         percentage:  5.7, color: '' },
  { id: 'upper-leg-l',  name: 'Upper Leg L',   percentage:  3.9, color: '' },
  { id: 'upper-leg-r',  name: 'Upper Leg R',   percentage:  3.6, color: '' },
  { id: 'lower-leg-l',  name: 'Lower Leg L',   percentage:  2.4, color: '' },
  { id: 'lower-leg-r',  name: 'Lower Leg R',   percentage:  2.1, color: '' },
  { id: 'foot-l',       name: 'Foot L',        percentage:  0.6, color: '' },
  { id: 'foot-r',       name: 'Foot R',        percentage:  0.5, color: '' },
]
