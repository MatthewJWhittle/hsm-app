import type { Model, ModelMetadata } from '../types/model'
import { apiBase } from '../utils/apiBase'
import { readFetchErrorDetail } from './errors'
import { parseModel } from './models'

function appendMetadataJsonPart(form: FormData, metadata: ModelMetadata) {
  form.append(
    'metadata',
    new Blob([JSON.stringify(metadata)], { type: 'application/json' }),
  )
}

export async function createModel(params: {
  token: string
  projectId: string
  species: string
  activity: string
  file: File
  uploadSessionId?: string
  /** Sent as a multipart part with ``Content-Type: application/json`` (not a double-encoded string). */
  metadata?: ModelMetadata
  serializedModelFile?: File | null
}): Promise<Model> {
  const form = new FormData()
  form.append('project_id', params.projectId)
  form.append('species', params.species)
  form.append('activity', params.activity)
  if (params.uploadSessionId) {
    form.append('upload_session_id', params.uploadSessionId)
  } else {
    form.append('file', params.file)
  }
  if (params.metadata !== undefined) {
    appendMetadataJsonPart(form, params.metadata)
  }
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
  projectId?: string | null
  /** When set, replaces catalog metadata; omit to leave unchanged. */
  metadata?: ModelMetadata | null
  serializedModelFile?: File | null
}): Promise<Model> {
  const form = new FormData()
  form.append('species', params.species)
  form.append('activity', params.activity)
  if (params.file) {
    form.append('file', params.file)
  }
  if (params.projectId) {
    form.append('project_id', params.projectId)
  }
  if (params.metadata !== undefined && params.metadata !== null) {
    appendMetadataJsonPart(form, params.metadata)
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
