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
  /** JSON string: ``ModelMetadata`` (e.g. ``analysis.feature_band_indices``). */
  metadataJson?: string
  serializedModelFile?: File | null
}): Promise<Model> {
  const form = new FormData()
  form.append('project_id', params.projectId)
  form.append('species', params.species)
  form.append('activity', params.activity)
  form.append('file', params.file)
  if (params.modelName) form.append('model_name', params.modelName)
  if (params.modelVersion) form.append('model_version', params.modelVersion)
  if (params.metadataJson) form.append('metadata', params.metadataJson)
  if (params.serializedModelFile) {
    form.append('serialized_model_file', params.serializedModelFile)
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
  metadataJson?: string | null
  serializedModelFile?: File | null
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
  if (params.metadataJson !== undefined && params.metadataJson !== null) {
    form.append('metadata', params.metadataJson)
  }
  if (params.serializedModelFile) {
    form.append('serialized_model_file', params.serializedModelFile)
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
