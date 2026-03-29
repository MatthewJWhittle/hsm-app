import type { Model } from '../types/model'
import { apiBase } from '../utils/apiBase'

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

export async function createModel(params: {
  token: string
  species: string
  activity: string
  file: File
  modelName?: string
  modelVersion?: string
  driverConfigJson?: string
}): Promise<Model> {
  const form = new FormData()
  form.append('species', params.species)
  form.append('activity', params.activity)
  form.append('file', params.file)
  if (params.modelName) form.append('model_name', params.modelName)
  if (params.modelVersion) form.append('model_version', params.modelVersion)
  if (params.driverConfigJson) form.append('driver_config', params.driverConfigJson)

  const r = await fetch(`${apiBase()}/models`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${params.token}` },
    body: form,
  })
  if (!r.ok) throw new Error(await errorMessage(r))
  const raw: unknown = await r.json()
  return raw as Model
}

export async function updateModel(params: {
  token: string
  modelId: string
  species: string
  activity: string
  file?: File | null
  modelName: string | null
  modelVersion: string | null
  driverConfigJson?: string | null
}): Promise<Model> {
  const form = new FormData()
  form.append('species', params.species)
  form.append('activity', params.activity)
  if (params.file) form.append('file', params.file)
  form.append('model_name', params.modelName ?? '')
  form.append('model_version', params.modelVersion ?? '')
  if (params.driverConfigJson !== undefined && params.driverConfigJson !== null) {
    form.append('driver_config', params.driverConfigJson)
  }

  const r = await fetch(`${apiBase()}/models/${encodeURIComponent(params.modelId)}`, {
    method: 'PUT',
    headers: { Authorization: `Bearer ${params.token}` },
    body: form,
  })
  if (!r.ok) throw new Error(await errorMessage(r))
  const raw: unknown = await r.json()
  return raw as Model
}
