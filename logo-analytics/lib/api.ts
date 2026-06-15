// Backend API client. Talks to the FastAPI service (see ../backend).
// Base URL is configurable; defaults to local dev.
import type { AnalysisResult, MatchEntry } from './types'

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

/** Upload a video + metadata, returns the job id to poll. */
export async function createJob(
  file: File,
  meta: UploadMeta,
): Promise<{ jobId: string; status: string }> {
  const form = new FormData()
  form.append('video', file)
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
