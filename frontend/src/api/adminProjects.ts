import type { CatalogProject } from '../types/project'
import { apiBase } from '../utils/apiBase'
import { parseProject } from './projects'

async function errorMessage(r: Response): Promise<string> {
  try {
    const raw: unknown = await r.json()
    if (
      raw &&
      typeof raw === 'object' &&
      'detail' in raw &&
      typeof (raw as { detail: unknown }).detail === 'string'
    ) {
      return (raw as { detail: string }).detail
    }
  } catch {
    /* ignore */
  }
  return r.statusText || String(r.status)
}

export async function createProject(params: {
  token: string
  name: string
  file: File
  description?: string
  visibility?: 'public' | 'private'
  allowedUids?: string
}): Promise<CatalogProject> {
  const form = new FormData()
  form.append('name', params.name)
  form.append('file', params.file)
  form.append('visibility', params.visibility ?? 'public')
  if (params.description) form.append('description', params.description)
  if (params.allowedUids !== undefined) form.append('allowed_uids', params.allowedUids)

  const r = await fetch(`${apiBase()}/projects`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${params.token}` },
    body: form,
  })
  if (!r.ok) throw new Error(await errorMessage(r))
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
  if (!r.ok) throw new Error(await errorMessage(r))
  const raw: unknown = await r.json()
  const p = parseProject(raw)
  if (p === null) throw new Error('Invalid update project response')
  return p
}
