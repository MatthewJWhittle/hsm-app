import type { CatalogProject, EnvironmentalBandDefinition } from '../types/project'

/** Partial label update for PATCH …/environmental-band-definitions/labels (``name`` aliases display label). */
export type BandLabelPatch = {
  label?: string | null
  description?: string | null
  name?: string | null
}
import { apiBase } from '../utils/apiBase'
import { readFetchErrorDetail } from './errors'
import { isRecord } from './jsonGuards'
import { parseProject } from './projects'

export type AdminJobStatus = 'queued' | 'running' | 'succeeded' | 'failed'

export type AdminJobError = { code: string; message: string; detail?: string | null }

export type AdminJob = {
  id: string
  kind: string
  status: AdminJobStatus
  input: Record<string, unknown>
  error: AdminJobError | null
}

function isAdminJobStatus(value: string): value is AdminJobStatus {
  return value === 'queued' || value === 'running' || value === 'succeeded' || value === 'failed'
}

function parseAdminJob(raw: unknown): AdminJob | null {
  if (!isRecord(raw)) return null
  if (typeof raw.id !== 'string' || typeof raw.kind !== 'string' || typeof raw.status !== 'string') {
    return null
  }
  if (!isAdminJobStatus(raw.status)) return null
  const inputRaw = raw.input
  const input: Record<string, unknown> =
    inputRaw !== undefined && inputRaw !== null && isRecord(inputRaw) ? inputRaw : {}
  let error: AdminJobError | null = null
  if (raw.error !== undefined && raw.error !== null) {
    if (!isRecord(raw.error)) return null
    const { code, message, detail } = raw.error
    if (typeof code !== 'string' || typeof message !== 'string') return null
    if (
      detail !== undefined &&
      detail !== null &&
      typeof detail !== 'string'
    ) {
      return null
    }
    error = { code, message, ...(detail !== undefined ? { detail } : {}) }
  }
  return { id: raw.id, kind: raw.kind, status: raw.status, input, error }
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, ms)
  })
}

export async function fetchAdminProject(params: {
  token: string
  projectId: string
}): Promise<CatalogProject> {
  const r = await fetch(`${apiBase()}/projects/${encodeURIComponent(params.projectId)}`, {
    headers: { Authorization: `Bearer ${params.token}` },
  })
  if (!r.ok) throw new Error(await readFetchErrorDetail(r))
  const raw: unknown = await r.json()
  const p = parseProject(raw)
  if (p === null) throw new Error('Invalid project response')
  return p
}

export async function fetchAdminJob(params: { token: string; jobId: string }): Promise<AdminJob> {
  const r = await fetch(`${apiBase()}/jobs/${encodeURIComponent(params.jobId)}`, {
    headers: { Authorization: `Bearer ${params.token}` },
  })
  if (!r.ok) throw new Error(await readFetchErrorDetail(r))
  const raw: unknown = await r.json()
  const job = parseAdminJob(raw)
  if (job === null) throw new Error('Invalid job response')
  return job
}

export async function pollAdminJobUntilTerminal(params: {
  token: string
  jobId: string
  onStatus?: (status: AdminJobStatus) => void
  signal?: AbortSignal
  /** Shown if polling exceeds the deadline (defaults to a generic message). */
  timeoutMessage?: string
}): Promise<AdminJob> {
  let waitMs = 500
  const maxWaitMs = 10_000
  const deadline = Date.now() + 45 * 60 * 1000
  const timeoutMsg =
    params.timeoutMessage?.trim() ||
    'Background job timed out while waiting for completion.'
  while (Date.now() < deadline) {
    if (params.signal?.aborted) {
      throw new DOMException('Aborted', 'AbortError')
    }
    const job = await fetchAdminJob({ token: params.token, jobId: params.jobId })
    params.onStatus?.(job.status)
    if (job.status === 'succeeded' || job.status === 'failed') {
      return job
    }
    await delay(waitMs)
    waitMs = Math.min(maxWaitMs, Math.floor(waitMs * 1.5))
  }
  throw new Error(timeoutMsg)
}

export function parseJobAcceptedResourceIds(raw: unknown): {
  job_id: string
  project_id: string | null
  model_id: string | null
} | null {
  if (!isRecord(raw) || typeof raw.job_id !== 'string') return null
  return {
    job_id: raw.job_id,
    project_id: typeof raw.project_id === 'string' ? raw.project_id : null,
    model_id: typeof raw.model_id === 'string' ? raw.model_id : null,
  }
}

export async function createProject(params: {
  token: string
  name: string
  file?: File | null
  uploadSessionId?: string
  description?: string
  visibility?: 'public' | 'private'
  allowedUids?: string
  onJobStatus?: (status: AdminJobStatus) => void
  signal?: AbortSignal
}): Promise<CatalogProject> {
  const form = new FormData()
  form.append('name', params.name)
  if (params.file) form.append('file', params.file)
  if (params.uploadSessionId) form.append('upload_session_id', params.uploadSessionId)
  form.append('visibility', params.visibility ?? 'public')
  if (params.description) form.append('description', params.description)
  if (params.allowedUids !== undefined) form.append('allowed_uids', params.allowedUids)

  const r = await fetch(`${apiBase()}/projects`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${params.token}` },
    body: form,
    signal: params.signal,
  })
  if (r.status === 202) {
    const rawAccept: unknown = await r.json()
    const acc = parseJobAcceptedResourceIds(rawAccept)
    if (acc === null || !acc.project_id) {
      throw new Error('Invalid job accept response')
    }
    const job = await pollAdminJobUntilTerminal({
      token: params.token,
      jobId: acc.job_id,
      onStatus: params.onJobStatus,
      signal: params.signal,
      timeoutMessage: 'Project create job timed out while waiting for completion.',
    })
    if (job.status === 'failed') {
      const msg = job.error?.message?.trim() || 'Project create job failed'
      throw new Error(msg)
    }
    return fetchAdminProject({ token: params.token, projectId: acc.project_id })
  }
  if (!r.ok) throw new Error(await readFetchErrorDetail(r))
  const raw: unknown = await r.json()
  const p = parseProject(raw)
  if (p === null) throw new Error('Invalid create project response')
  return p
}

export type UploadSession = {
  id: string
  status: 'pending' | 'uploaded' | 'validating' | 'deriving' | 'ready' | 'failed'
  stage: 'init' | 'upload' | 'validate' | 'derive' | 'persist' | 'done'
  upload_url: string | null
  object_path: string
  gcs_bucket: string
}

function isUploadSession(raw: unknown): raw is UploadSession {
  if (!raw || typeof raw !== 'object') return false
  const rec = raw as Record<string, unknown>
  return (
    typeof rec.id === 'string' &&
    typeof rec.status === 'string' &&
    typeof rec.stage === 'string' &&
    (rec.upload_url === null || typeof rec.upload_url === 'string') &&
    typeof rec.object_path === 'string' &&
    typeof rec.gcs_bucket === 'string'
  )
}

export async function initUploadSession(params: {
  token: string
  filename: string
  contentType?: string
  sizeBytes?: number
  projectId?: string
}): Promise<UploadSession> {
  const r = await fetch(`${apiBase()}/uploads/init`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${params.token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      project_id: params.projectId,
      filename: params.filename,
      content_type: params.contentType ?? null,
      size_bytes: params.sizeBytes ?? null,
    }),
  })
  if (!r.ok) throw new Error(await readFetchErrorDetail(r))
  const raw: unknown = await r.json()
  if (!isUploadSession(raw)) throw new Error('Invalid upload session init response')
  return raw
}

export async function completeUploadSession(params: {
  token: string
  uploadId: string
  sizeBytes?: number
}): Promise<UploadSession> {
  const r = await fetch(`${apiBase()}/uploads/${encodeURIComponent(params.uploadId)}/complete`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${params.token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ size_bytes: params.sizeBytes ?? null }),
  })
  if (!r.ok) throw new Error(await readFetchErrorDetail(r))
  const raw: unknown = await r.json()
  if (!isUploadSession(raw)) throw new Error('Invalid upload session complete response')
  return raw
}

export async function uploadFileToSignedUrl(params: {
  uploadUrl: string
  file: File
}): Promise<void> {
  const r = await fetch(params.uploadUrl, {
    method: 'PUT',
    headers: {
      'Content-Type': params.file.type || 'application/octet-stream',
    },
    body: params.file,
  })
  if (!r.ok) {
    throw new Error(`Upload failed (${r.status} ${r.statusText})`)
  }
}

export async function updateProject(params: {
  token: string
  projectId: string
  name?: string
  description?: string | null
  status?: 'active' | 'archived'
  visibility?: 'public' | 'private'
  allowedUids?: string | null
}): Promise<CatalogProject> {
  const form = new FormData()
  if (params.name !== undefined) form.append('name', params.name)
  if (params.description !== undefined) form.append('description', params.description ?? '')
  if (params.status !== undefined) form.append('status', params.status)
  if (params.visibility !== undefined) form.append('visibility', params.visibility)
  if (params.allowedUids !== undefined) form.append('allowed_uids', params.allowedUids ?? '')

  const r = await fetch(`${apiBase()}/projects/${encodeURIComponent(params.projectId)}`, {
    method: 'PATCH',
    headers: { Authorization: `Bearer ${params.token}` },
    body: form,
  })
  if (!r.ok) throw new Error(await readFetchErrorDetail(r))
  const raw: unknown = await r.json()
  const p = parseProject(raw)
  if (p === null) throw new Error('Invalid update project response')
  return p
}

export async function replaceProjectEnvironmentalCog(params: {
  token: string
  projectId: string
  uploadSessionId: string
  onJobStatus?: (status: AdminJobStatus) => void
  signal?: AbortSignal
}): Promise<CatalogProject> {
  const form = new FormData()
  form.append('upload_session_id', params.uploadSessionId)
  const r = await fetch(`${apiBase()}/projects/${encodeURIComponent(params.projectId)}/environmental-cogs`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${params.token}` },
    body: form,
    signal: params.signal,
  })
  if (r.status === 202) {
    const rawAccept: unknown = await r.json()
    if (!isRecord(rawAccept) || typeof rawAccept.job_id !== 'string') {
      throw new Error('Invalid job accept response')
    }
    const job = await pollAdminJobUntilTerminal({
      token: params.token,
      jobId: rawAccept.job_id,
      onStatus: params.onJobStatus,
      signal: params.signal,
      timeoutMessage:
        'Environmental COG replace job timed out while waiting for completion.',
    })
    if (job.status === 'failed') {
      const msg = job.error?.message?.trim() || 'Environmental COG replace failed'
      throw new Error(msg)
    }
    return fetchAdminProject({ token: params.token, projectId: params.projectId })
  }
  if (!r.ok) throw new Error(await readFetchErrorDetail(r))
  const raw: unknown = await r.json()
  const p = parseProject(raw)
  if (p === null) throw new Error('Invalid environmental COG replacement response')
  return p
}

/** Replace band manifest (indices 0..n-1). Validates against the project’s environmental COG band count. */
export async function patchProjectEnvironmentalBandDefinitions(params: {
  token: string
  projectId: string
  definitions: EnvironmentalBandDefinition[]
}): Promise<CatalogProject> {
  const r = await fetch(
    `${apiBase()}/projects/${encodeURIComponent(params.projectId)}/environmental-band-definitions`,
    {
      method: 'PATCH',
      headers: {
        Authorization: `Bearer ${params.token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(params.definitions),
    },
  )
  if (!r.ok) throw new Error(await readFetchErrorDetail(r))
  const raw: unknown = await r.json()
  const p = parseProject(raw)
  if (p === null) throw new Error('Invalid PATCH environmental-band-definitions response')
  return p
}

/** Patch display labels/descriptions for one or more bands (keyed by machine band ``name``). */
export async function patchProjectEnvironmentalBandLabels(params: {
  token: string
  projectId: string
  updates: Record<string, BandLabelPatch>
}): Promise<CatalogProject> {
  const r = await fetch(
    `${apiBase()}/projects/${encodeURIComponent(params.projectId)}/environmental-band-definitions/labels`,
    {
      method: 'PATCH',
      headers: {
        Authorization: `Bearer ${params.token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(params.updates),
    },
  )
  if (!r.ok) throw new Error(await readFetchErrorDetail(r))
  const raw: unknown = await r.json()
  const p = parseProject(raw)
  if (p === null) throw new Error('Invalid PATCH environmental-band-definitions/labels response')
  return p
}

/** Rebuild ``explainability_background.parquet`` from the project environmental COG (admin). */
export async function postRegenerateExplainabilityBackgroundSample(params: {
  token: string
  projectId: string
  /** Pixel count; omit to use server default (ENV_BACKGROUND_SAMPLE_ROWS). */
  sampleRows?: number
  onJobStatus?: (status: AdminJobStatus) => void
  signal?: AbortSignal
}): Promise<CatalogProject> {
  const body: { sample_rows?: number } = {}
  if (params.sampleRows !== undefined) {
    body.sample_rows = params.sampleRows
  }
  const r = await fetch(
    `${apiBase()}/projects/${encodeURIComponent(params.projectId)}/explainability-background-sample`,
    {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${params.token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
      signal: params.signal,
    },
  )
  if (r.status === 202) {
    const rawAccept: unknown = await r.json()
    const acc = parseJobAcceptedResourceIds(rawAccept)
    if (acc === null || !acc.project_id) {
      throw new Error('Invalid job accept response')
    }
    const job = await pollAdminJobUntilTerminal({
      token: params.token,
      jobId: acc.job_id,
      onStatus: params.onJobStatus,
      signal: params.signal,
      timeoutMessage:
        'Explainability background job timed out while waiting for completion.',
    })
    if (job.status === 'failed') {
      const msg = job.error?.message?.trim() || 'Explainability background job failed'
      throw new Error(msg)
    }
    return fetchAdminProject({ token: params.token, projectId: acc.project_id })
  }
  if (!r.ok) throw new Error(await readFetchErrorDetail(r))
  const raw: unknown = await r.json()
  const p = parseProject(raw)
  if (p === null) throw new Error('Invalid explainability-background-sample response')
  return p
}
