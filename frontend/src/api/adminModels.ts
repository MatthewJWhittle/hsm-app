import type { Model } from '../types/model'
import { apiBase } from '../utils/apiBase'
import { readFetchErrorDetail } from './errors'
import { parseModel } from './models'

export async function createModel(params: {
  token: string
  projectId: string
  species: string
  activity: string
  file: File
  modelName?: string
  modelVersion?: string
  driverBandIndicesJson?: string
}): Promise<Model> {
  const form = new FormData()
  form.append('project_id', params.projectId)
  form.append('species', params.species)
  form.append('activity', params.activity)
  form.append('file', params.file)
  if (params.modelName) form.append('model_name', params.modelName)
  if (params.modelVersion) form.append('model_version', params.modelVersion)
  if (params.driverBandIndicesJson) {
    form.append('driver_band_indices', params.driverBandIndicesJson)
  }

  const r = await fetch(`${apiBase()}/models`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${params.token}` },
    body: form,
  })
  if (!r.ok) throw new Error(await readFetchErrorDetail(r))
  const raw: unknown = await r.json()
  const model = parseModel(raw)
  if (model === null) throw new Error('Invalid create model response')
  return model
}

export async function updateModel(params: {
  token: string
  modelId: string
  species: string
  activity: string
  file?: File | null
  modelName: string | null
  modelVersion: string | null
  projectId?: string | null
  driverBandIndicesJson?: string | null
}): Promise<Model> {
  const form = new FormData()
  form.append('species', params.species)
  form.append('activity', params.activity)
  if (params.file) form.append('file', params.file)
  form.append('model_name', params.modelName ?? '')
  form.append('model_version', params.modelVersion ?? '')
  if (params.projectId) {
    form.append('project_id', params.projectId)
  }
  if (params.driverBandIndicesJson !== undefined && params.driverBandIndicesJson !== null) {
    form.append('driver_band_indices', params.driverBandIndicesJson)
  }

  const r = await fetch(`${apiBase()}/models/${encodeURIComponent(params.modelId)}`, {
    method: 'PUT',
    headers: { Authorization: `Bearer ${params.token}` },
    body: form,
  })
  if (!r.ok) throw new Error(await readFetchErrorDetail(r))
  const raw: unknown = await r.json()
  const model = parseModel(raw)
  if (model === null) throw new Error('Invalid update model response')
  return model
}
