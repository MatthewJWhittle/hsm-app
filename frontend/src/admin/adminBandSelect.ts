import type { CatalogProject, EnvironmentalBandDefinition } from '../types/project'

/** Sorted band definitions for the selected project, or null if none. */
export function environmentalBandsForProject(
  projectId: string,
  projects: CatalogProject[],
): EnvironmentalBandDefinition[] | null {
  const p = projects.find((x) => x.id === projectId)
  const defs = p?.environmental_band_definitions
  if (!defs || defs.length === 0) return null
  return [...defs].sort((a, b) => a.index - b.index)
}

/** Map stored driver_band_indices to definition objects in order. */
export function bandsFromDriverIndices(
  indices: number[] | null | undefined,
  defs: EnvironmentalBandDefinition[] | null,
): EnvironmentalBandDefinition[] {
  if (!indices?.length || !defs?.length) return []
  const byIdx = new Map(defs.map((d) => [d.index, d]))
  return indices.map((i) => byIdx.get(i)).filter((x): x is EnvironmentalBandDefinition => x != null)
}

/** Map stored ``feature_band_names`` (order preserved) to definition objects. */
export function bandsFromFeatureNames(
  names: string[] | null | undefined,
  defs: EnvironmentalBandDefinition[] | null,
): EnvironmentalBandDefinition[] {
  if (!names?.length || !defs?.length) return []
  const byLower = new Map(defs.map((d) => [d.name.toLowerCase(), d]))
  const out: EnvironmentalBandDefinition[] = []
  for (const raw of names) {
    const d = byLower.get(raw.trim().toLowerCase())
    if (d) out.push(d)
  }
  return out
}
