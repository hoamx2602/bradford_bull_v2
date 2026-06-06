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
}
