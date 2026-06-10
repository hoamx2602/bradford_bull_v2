export interface Segment {
  startTime: number
  endTime: number
  avgVisibility: number
  durationWeight: number
}

export interface LogoResult {
  id: string
  name: string
  class: string
  segments: Segment[]
  totalExposureSeconds: number
  qualityExposureSeconds: number
  avgVisibilityScore: number
  segmentCount: number
  longestSegmentSeconds: number
  emvUsd: number
}

export interface EventMeta {
  eventName: string
  videoName: string
  audienceSize: number
  placementType: string
  cpmBase: number
}

export interface AnalysisResult {
  id: string
  eventName: string
  videoName: string
  videoDurationSeconds: number
  analyzedAt: string
  metadata: {
    audienceSize: number
    placementType: string
    cpmBase: number
    placementMultiplier: number
  }
  logos: LogoResult[]
  totalEmvUsd: number
  totalQualityExposureSeconds: number
  avgVisibilityScore: number
  // Returned by the backend (YOLO-pose body-zone attribution); optional so mock
  // data without it still type-checks.
  bodyZones?: BodyZone[]
  // True when the backend produced an annotated preview video (boxes drawn).
  previewAvailable?: boolean
  // Raw on-screen intervals per brand — matches the boxes drawn on the preview
  // video (NOT the EMV-filtered segments). Drives the player timeline.
  detectionTimeline?: DetectionTimelineBrand[]
}

export interface DetectionInterval {
  start: number
  end: number
}

export interface DetectionTimelineBrand {
  name: string
  class: string
  color: string
  intervals: DetectionInterval[]
}

// ── New types for dashboard redesign ─────────────────────────────────

export interface MatchEntry {
  id: string
  eventName: string
  date: string
  videoName: string
  durationSeconds: number
  logoCount: number
  totalEmv: number
  result: AnalysisResult
}

export interface BodyZone {
  id: string
  name: string
  percentage: number
  color: string
}

export interface TimeSeriesPoint {
  minuteMark: number
  logoId: string
  logoName: string
  cumulativeExposure: number
}
