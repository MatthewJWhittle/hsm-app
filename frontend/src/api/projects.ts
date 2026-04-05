import type { CatalogProject, EnvironmentalBandDefinition } from '../types/project'
import { apiBase } from '../utils/apiBase'
import { isRecord } from './jsonGuards'

function parseBandDefinitions(value: unknown): EnvironmentalBandDefinition[] | null {
  if (value === undefined || value === null) return null
  if (!Array.isArray(value)) return null
  const out: EnvironmentalBandDefinition[] = []
  for (const row of value) {
    if (!isRecord(row)) return null
    const { index, name, label, description } = row
    if (typeof index !== 'number' || typeof name !== 'string') return null
    if (label !== undefined && label !== null && typeof label !== 'string') return null
    if (description !== undefined && description !== null && typeof description !== 'string') return null
    out.push({
      index,
      name,
      ...(label !== undefined && label !== null ? { label } : {}),
      ...(description !== undefined && description !== null && description !== ''
        ? { description }
        : {}),
    })
  }
  return out
}

export function parseProject(value: unknown): CatalogProject | null {
  if (!isRecord(value)) return null
  const {
    id,
    name,
    description,
    status,
    visibility,
    allowed_uids,
    driver_artifact_root,
    driver_cog_path,
    created_at,
    updated_at,
  } = value
  if (typeof id !== 'string' || typeof name !== 'string') {
    return null
  }
  if (
    driver_artifact_root !== undefined &&
    driver_artifact_root !== null &&
    typeof driver_artifact_root !== 'string'
  ) {
    return null
  }
  if (
    driver_cog_path !== undefined &&
    driver_cog_path !== null &&
    typeof driver_cog_path !== 'string'
  ) {
    return null
  }
  if (status !== 'active' && status !== 'archived') return null
  if (visibility !== 'public' && visibility !== 'private') return null
  if (!Array.isArray(allowed_uids) || !allowed_uids.every((u) => typeof u === 'string')) {
    return null
  }
  const out: CatalogProject = {
    id,
    name,
    status,
    visibility,
    allowed_uids,
  }
  if (driver_artifact_root !== undefined) out.driver_artifact_root = driver_artifact_root
  if (driver_cog_path !== undefined) out.driver_cog_path = driver_cog_path
  if (description !== undefined) {
    if (description !== null && typeof description !== 'string') return null
    out.description = description
  }
  if (created_at !== undefined) {
    if (created_at !== null && typeof created_at !== 'string') return null
    out.created_at = created_at
  }
  if (updated_at !== undefined) {
    if (updated_at !== null && typeof updated_at !== 'string') return null
    out.updated_at = updated_at
  }
  if (value.environmental_band_definitions !== undefined) {
    if (value.environmental_band_definitions === null) {
      out.environmental_band_definitions = null
    } else {
      const defs = parseBandDefinitions(value.environmental_band_definitions)
      if (defs === null) return null
      out.environmental_band_definitions = defs
    }
  }
  if (value.explainability_background_path !== undefined) {
    if (value.explainability_background_path === null) {
      out.explainability_background_path = null
    } else if (typeof value.explainability_background_path === 'string') {
      out.explainability_background_path = value.explainability_background_path
    } else {
      return null
    }
  }
  if (value.explainability_background_sample_rows !== undefined) {
    if (value.explainability_background_sample_rows === null) {
      out.explainability_background_sample_rows = null
    } else if (typeof value.explainability_background_sample_rows === 'number') {
      out.explainability_background_sample_rows = value.explainability_background_sample_rows
    } else {
      return null
    }
  }
  if (value.explainability_background_generated_at !== undefined) {
    if (value.explainability_background_generated_at === null) {
      out.explainability_background_generated_at = null
    } else if (typeof value.explainability_background_generated_at === 'string') {
      out.explainability_background_generated_at = value.explainability_background_generated_at
    } else {
      return null
    }
  }
  return out
}

function parseProjectList(value: unknown): CatalogProject[] | null {
  if (!Array.isArray(value)) return null
  const out: CatalogProject[] = []
  for (const item of value) {
    const p = parseProject(item)
    if (p === null) return null
    out.push(p)
  }
  return out
}

export async function fetchProjectCatalog(opts?: {
  token?: string | null
}): Promise<CatalogProject[]> {
  const base = apiBase()
  const headers: Record<string, string> = {}
  if (opts?.token) headers.Authorization = `Bearer ${opts.token}`
  const r = await fetch(`${base}/projects`, { headers })
  if (!r.ok) throw new Error(r.statusText || String(r.status))
  const raw: unknown = await r.json()
  const list = parseProjectList(raw)
  if (list === null) throw new Error('Invalid projects response')
  return list
}
