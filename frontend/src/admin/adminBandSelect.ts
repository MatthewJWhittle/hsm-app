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
