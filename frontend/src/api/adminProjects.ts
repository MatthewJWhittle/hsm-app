import type { CatalogProject, EnvironmentalBandDefinition } from '../types/project'
import { apiBase } from '../utils/apiBase'
import { readFetchErrorDetail } from './errors'
import { parseProject } from './projects'

export async function createProject(params: {
  token: string
  name: string
  file?: File | null
  description?: string
  visibility?: 'public' | 'private'
  allowedUids?: string
}): Promise<CatalogProject> {
  const form = new FormData()
  form.append('name', params.name)
  if (params.file) form.append('file', params.file)
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

export async function updateProject(params: {
  token: string
  projectId: string
  name?: string
  description?: string | null
  status?: 'active' | 'archived'
  visibility?: 'public' | 'private'
  allowedUids?: string | null
  file?: File | null
}): Promise<CatalogProject> {
  const form = new FormData()
  if (params.name !== undefined) form.append('name', params.name)
  if (params.description !== undefined) form.append('description', params.description ?? '')
  if (params.status !== undefined) form.append('status', params.status)
  if (params.visibility !== undefined) form.append('visibility', params.visibility)
  if (params.allowedUids !== undefined) form.append('allowed_uids', params.allowedUids ?? '')
  if (params.file) form.append('file', params.file)

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
