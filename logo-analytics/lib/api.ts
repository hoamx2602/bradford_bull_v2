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
