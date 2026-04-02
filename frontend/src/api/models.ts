import type { Model } from '../types/model'
import { isRecord } from './jsonGuards'

export function parseModel(value: unknown): Model | null {
  if (!isRecord(value)) return null
  const {
    id,
    project_id,
    species,
    activity,
    artifact_root,
    suitability_cog_path,
    model_name,
    model_version,
    driver_band_indices,
    driver_config,
  } = value
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

  if (model_name !== undefined) {
    if (model_name !== null && typeof model_name !== 'string') return null
    out.model_name = model_name
  }
  if (model_version !== undefined) {
    if (model_version !== null && typeof model_version !== 'string') return null
    out.model_version = model_version
  }
  if (driver_band_indices !== undefined) {
    if (driver_band_indices === null) {
      out.driver_band_indices = null
    } else if (
      Array.isArray(driver_band_indices) &&
      driver_band_indices.every((x) => typeof x === 'number')
    ) {
      out.driver_band_indices = driver_band_indices
    } else {
      return null
    }
  }
  if (driver_config !== undefined) {
    if (driver_config === null) {
      out.driver_config = null
    } else if (isRecord(driver_config)) {
      out.driver_config = driver_config
    } else {
      return null
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
