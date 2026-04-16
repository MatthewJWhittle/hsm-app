import type { CatalogProject, EnvironmentalBandDefinition } from '../types/project'

/** Partial label update for PATCH …/environmental-band-definitions/labels (``name`` aliases display label). */
export type BandLabelPatch = {
  label?: string | null
  description?: string | null
  name?: string | null
}
import { apiBase } from '../utils/apiBase'
import { readFetchErrorDetail } from './errors'
import { parseProject } from './projects'

export async function createProject(params: {
  token: string
  name: string
  file?: File | null
  uploadSessionId?: string
  description?: string
  visibility?: 'public' | 'private'
  allowedUids?: string
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
  })
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
    method: 'PUT',
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
}): Promise<CatalogProject> {
  const form = new FormData()
  form.append('upload_session_id', params.uploadSessionId)
  const r = await fetch(`${apiBase()}/projects/${encodeURIComponent(params.projectId)}/environmental-cog`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${params.token}` },
    body: form,
  })
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
    },
  )
  if (!r.ok) throw new Error(await readFetchErrorDetail(r))
  const raw: unknown = await r.json()
  const p = parseProject(raw)
  if (p === null) throw new Error('Invalid explainability-background-sample response')
  return p
}
