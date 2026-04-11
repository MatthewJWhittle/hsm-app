import type { Model, ModelAnalysis, ModelCard, ModelMetadata } from '../types/model'
import { isRecord } from './jsonGuards'

function parseModelCard(value: unknown): ModelCard | null {
  if (value === undefined || value === null) return null
  if (!isRecord(value)) return null
  const out: ModelCard = {}
  for (const k of [
    'title',
    'version',
    'summary',
    'spatial_resolution_m',
    'training_period',
    'evaluation_notes',
    'license',
    'citation',
  ] as const) {
    const v = value[k]
    if (v === undefined) continue
    if (v === null) {
      ;(out as Record<string, unknown>)[k] = null
      continue
    }
    if (typeof v === 'string' || typeof v === 'number') {
      ;(out as Record<string, unknown>)[k] = v
    } else {
      return null
    }
  }
  if (value.metrics !== undefined) {
    if (value.metrics === null) {
      out.metrics = null
    } else if (isRecord(value.metrics)) {
      const m: Record<string, number | string> = {}
      for (const [k, v] of Object.entries(value.metrics)) {
        if (typeof v === 'number' || typeof v === 'string') m[k] = v
        else return null
      }
      out.metrics = m
    } else {
      return null
    }
  }
  return out
}

function parseModelAnalysis(value: unknown): ModelAnalysis | null {
  if (value === undefined || value === null) return null
  if (!isRecord(value)) return null
  const out: ModelAnalysis = {}
  if (value.feature_band_indices !== undefined) {
    if (value.feature_band_indices === null) {
      out.feature_band_indices = null
    } else if (
      Array.isArray(value.feature_band_indices) &&
      value.feature_band_indices.every((x) => typeof x === 'number')
    ) {
      out.feature_band_indices = value.feature_band_indices
    } else {
      return null
    }
  }
  for (const k of ['serialized_model_path', 'driver_cog_path'] as const) {
    const v = value[k]
    if (v === undefined) continue
    if (v === null || typeof v === 'string') {
      ;(out as Record<string, unknown>)[k] = v
    } else {
      return null
    }
  }
  if (value.positive_class_index !== undefined) {
    const v = value.positive_class_index
    if (v === null || typeof v === 'number') {
      out.positive_class_index = v
    } else {
      return null
    }
  }
  return out
}

function parseModelMetadata(value: unknown): ModelMetadata | null {
  if (value === undefined || value === null) return null
  if (!isRecord(value)) return null
  const out: ModelMetadata = {}
  if (value.card !== undefined) {
    if (value.card === null) {
      out.card = null
    } else {
      const c = parseModelCard(value.card)
      if (c === null) return null
      out.card = c
    }
  }
  if (value.extras !== undefined) {
    if (value.extras === null) {
      out.extras = null
    } else if (isRecord(value.extras)) {
      const ex: Record<string, string> = {}
      for (const [k, v] of Object.entries(value.extras)) {
        if (typeof v === 'string') ex[k] = v
        else return null
      }
      out.extras = ex
    } else {
      return null
    }
  }
  if (value.analysis !== undefined) {
    if (value.analysis === null) {
      out.analysis = null
    } else {
      const a = parseModelAnalysis(value.analysis)
      if (a === null) return null
      out.analysis = a
    }
  }
  return out
}

export function parseModel(value: unknown): Model | null {
  if (!isRecord(value)) return null
  const { id, project_id, species, activity, artifact_root, suitability_cog_path, metadata } = value
  if (
    typeof id !== 'string' ||
    typeof species !== 'string' ||
    typeof activity !== 'string' ||
    typeof artifact_root !== 'string' ||
    typeof suitability_cog_path !== 'string'
  ) {
    return null
  }

  const out: Model = {
    id,
    species,
    activity,
    artifact_root,
    suitability_cog_path,
  }

  if (project_id !== undefined) {
    if (project_id !== null && typeof project_id !== 'string') return null
    out.project_id = project_id
  }

  if (metadata !== undefined) {
    if (metadata === null) {
      out.metadata = null
    } else {
      const md = parseModelMetadata(metadata)
      if (md === null) return null
      out.metadata = md
    }
  }

  return out
}

export function parseModelList(value: unknown): Model[] | null {
  if (!Array.isArray(value)) return null
  const out: Model[] = []
  for (const item of value) {
    const m = parseModel(item)
    if (m === null) return null
    out.push(m)
  }
  return out
}
