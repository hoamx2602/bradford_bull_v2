// Backend API client. Talks to the FastAPI service (see ../backend).
// Base URL is configurable; defaults to local dev.
import type {
  AnalysisResult,
  MatchEntry,
  LocationConfig,
  AnchorOption,
  BrandOption,
  AiCriterion,
  LocationBreakdown,
  LocationOverrideInput,
} from './types'

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export interface UploadMeta {
  eventName: string
  audienceSize: number
  placementType: string
  cpmBase: number
  // Target-team kit worn in this match — drives the team filter's reference
  // bootstrap on the backend. "away" (black) | "home" (white).
  kit: string
}

export interface JobStatus {
  id: string
  status: 'queued' | 'processing' | 'done' | 'error'
  progress: number
  stage: string
  stageDetail: string
  analysisId?: string | null
  error?: string | null
}

async function asJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText
    try {
      detail = (await res.json()).detail ?? detail
    } catch {}
    throw new Error(`${res.status}: ${detail}`)
  }
  return res.json() as Promise<T>
}

/** A previously uploaded video + the teams the user picked for it inline. */
export interface JobSource {
  storageKey: string
  videoName?: string
  teamRefsKey?: string
}

/** Upload a video WITHOUT starting analysis — returns its storage key so the
 *  inline team step can run before the job is created. */
export async function uploadVideo(
  file: File,
): Promise<{ storageKey: string; videoName: string }> {
  const form = new FormData()
  form.append('video', file)
  const res = await fetch(`${API_BASE}/api/jobs/upload`, { method: 'POST', body: form })
  return asJson(res)
}

/** Create + enqueue an analysis job. `source` is either a fresh File (one-shot
 *  legacy path) or a JobSource referencing an already-uploaded video. */
export async function createJob(
  source: File | JobSource,
  meta: UploadMeta,
): Promise<{ jobId: string; status: string }> {
  const form = new FormData()
  if (source instanceof File) {
    form.append('video', source)
  } else {
    form.append('storageKey', source.storageKey)
    if (source.videoName) form.append('videoName', source.videoName)
    if (source.teamRefsKey) form.append('teamRefsKey', source.teamRefsKey)
  }
  form.append('eventName', meta.eventName)
  form.append('audienceSize', String(meta.audienceSize))
  form.append('placementType', meta.placementType)
  form.append('cpmBase', String(meta.cpmBase))
  form.append('kit', meta.kit || 'away')

  const res = await fetch(`${API_BASE}/api/jobs`, { method: 'POST', body: form })
  return asJson(res)
}

export async function getJob(id: string): Promise<JobStatus> {
  return asJson(await fetch(`${API_BASE}/api/jobs/${id}`))
}

export async function listAnalyses(): Promise<MatchEntry[]> {
  return asJson(await fetch(`${API_BASE}/api/analyses`))
}

export async function getAnalysis(id: string): Promise<AnalysisResult> {
  return asJson(await fetch(`${API_BASE}/api/analyses/${id}`))
}

/** Rename an analysis (event and/or video name). Returns the saved values. */
export async function updateAnalysis(
  id: string,
  patch: { eventName?: string; videoName?: string },
): Promise<{ id: string; eventName: string; videoName: string }> {
  const res = await fetch(`${API_BASE}/api/analyses/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(patch),
  })
  return asJson(res)
}

export function csvUrl(id: string): string {
  return `${API_BASE}/api/analyses/${id}/export.csv`
}

/** Annotated preview video (logo boxes drawn) for an analysis. */
export function videoUrl(id: string): string {
  return `${API_BASE}/api/analyses/${id}/video`
}

/** Body-part segmentation overlay video (DensePose) for an analysis. */
export function bodysegVideoUrl(id: string): string {
  return `${API_BASE}/api/analyses/${id}/bodyseg-video`
}

/** Team-detection overlay video (tracked persons boxed TARGET vs OTHER). */
export function teamdetVideoUrl(id: string): string {
  return `${API_BASE}/api/analyses/${id}/teamdet-video`
}

// ── Settings: location taxonomy, brands, anchors, AI criteria ──────────────

export async function getLocations(): Promise<LocationConfig[]> {
  return asJson(await fetch(`${API_BASE}/api/settings/locations`))
}

export async function saveLocations(rows: LocationConfig[]): Promise<LocationConfig[]> {
  const res = await fetch(`${API_BASE}/api/settings/locations`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(rows),
  })
  return asJson(res)
}

export async function getAnchors(): Promise<AnchorOption[]> {
  return asJson(await fetch(`${API_BASE}/api/settings/anchors`))
}

export async function getBrands(): Promise<BrandOption[]> {
  return asJson(await fetch(`${API_BASE}/api/settings/brands`))
}

export async function getAiCriteriaOptions(): Promise<AiCriterion[]> {
  return asJson(await fetch(`${API_BASE}/api/settings/ai-criteria/options`))
}

export async function getAiCriteria(): Promise<{ enabled: string[] }> {
  return asJson(await fetch(`${API_BASE}/api/settings/ai-criteria`))
}

export async function saveAiCriteria(enabled: string[]): Promise<{ enabled: string[] }> {
  const res = await fetch(`${API_BASE}/api/settings/ai-criteria`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ enabled }),
  })
  return asJson(res)
}

export async function getAiAdjust(): Promise<{ weight: number }> {
  return asJson(await fetch(`${API_BASE}/api/settings/ai-adjust`))
}

export async function saveAiAdjust(weight: number): Promise<{ weight: number }> {
  const res = await fetch(`${API_BASE}/api/settings/ai-adjust`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ weight }),
  })
  return asJson(res)
}

/** Per-video Location breakdown table (Location | Logo | Human% | AI% | Human-AI%).
 *  Pass `criteria` (comma-joined keys) to preview a different criteria set. */
export async function getLocationBreakdown(
  analysisId: string,
  criteria?: string[],
): Promise<LocationBreakdown> {
  const q = criteria && criteria.length ? `?criteria=${criteria.join(',')}` : ''
  return asJson(await fetch(`${API_BASE}/api/analyses/${analysisId}/location-breakdown${q}`))
}

export async function saveLocationOverrides(
  analysisId: string,
  rows: LocationOverrideInput[],
): Promise<{ saved: boolean; count: number }> {
  const res = await fetch(`${API_BASE}/api/analyses/${analysisId}/location-overrides`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(rows),
  })
  return asJson(res)
}

/** Download URL for the per-video location breakdown as an Excel workbook
 *  (table + the parameters behind each AI %). */
export function locationExcelUrl(analysisId: string): string {
  return `${API_BASE}/api/analyses/${analysisId}/location-export.xlsx`
}

// ── Team refs (manual team selection) ──────────────────────────────────────

export interface TeamRefsStatus {
  exists: boolean
  builtAt?: string
  mode?: string
  kit?: string | null
  nTarget?: number | null
  nOther?: number | null
  wColor?: number | null
}

export interface RefVideo {
  storageKey: string
  eventName: string
  videoName: string
  kit: string
  createdAt: string
}

export interface RefCrop {
  thumb: string // data URL
  suggested: 'target' | 'other'
}

export async function getTeamRefsStatus(): Promise<TeamRefsStatus> {
  return asJson(await fetch(`${API_BASE}/api/team-refs/status`))
}

export async function deleteTeamRefs(): Promise<{ deleted: boolean }> {
  return asJson(await fetch(`${API_BASE}/api/team-refs`, { method: 'DELETE' }))
}

export async function listRefVideos(): Promise<RefVideo[]> {
  return asJson(await fetch(`${API_BASE}/api/team-refs/videos`))
}

export async function extractRefCrops(
  storageKey: string,
  kit: string,
): Promise<{ extractId: string; crops: RefCrop[]; tookSeconds: number }> {
  const res = await fetch(`${API_BASE}/api/team-refs/extract`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ storageKey, kit }),
  })
  return asJson(res)
}

export interface RefCluster {
  id: number
  members: number[] // crop indices into the extract response
  samples: number[] // representative crop indices (closest to centroid)
  size: number
  suggested: 'target' | 'other'
}

/** Group extracted crops into kit clusters for fast target/opponent picking. */
export async function clusterRefCrops(
  extractId: string,
  nClusters = 3,
): Promise<{ clusters: RefCluster[]; nCrops: number }> {
  const res = await fetch(`${API_BASE}/api/team-refs/cluster`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ extractId, nClusters }),
  })
  return asJson(res)
}

export async function saveTeamRefs(
  extractId: string,
  assignments: (string | null)[],
): Promise<{ saved: boolean; nTarget: number; nOther: number; wColor: number }> {
  const res = await fetch(`${API_BASE}/api/team-refs/save`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ extractId, assignments }),
  })
  return asJson(res)
}

/** Build refs from labels and store them per-job (no global overwrite).
 *  Returns a refsKey to pass to createJob for the inline upload team step. */
export async function buildTeamRefs(
  extractId: string,
  assignments: (string | null)[],
): Promise<{ refsKey: string; nTarget: number; nOther: number; wColor: number }> {
  const res = await fetch(`${API_BASE}/api/team-refs/build`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ extractId, assignments }),
  })
  return asJson(res)
}
