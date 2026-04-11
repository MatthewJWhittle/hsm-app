import type { EnvironmentalBandDefinition } from '../types/project'

/** Stable JSON for comparing band definition edits (order by index). */
export function serializeBandDefinitions(defs: EnvironmentalBandDefinition[]): string {
  const sorted = [...defs].sort((a, b) => a.index - b.index)
  return JSON.stringify(sorted)
}

/** Snapshot of project edit dialog fields (for dirty detection / baseline). */
export function projectFormSnapshot(params: {
  name: string
  description: string
  status: 'active' | 'archived'
  visibility: 'public' | 'private'
  allowedUids: string
  bandDefs: EnvironmentalBandDefinition[]
  pendingFileName: string | null
}): string {
  return JSON.stringify({
    name: params.name.trim(),
    description: params.description.trim(),
    status: params.status,
    visibility: params.visibility,
    allowedUids: params.allowedUids,
    bands: serializeBandDefinitions(params.bandDefs),
    filePending: params.pendingFileName,
  })
}

/** Snapshot of layer edit dialog fields. */
export function layerFormSnapshot(params: {
  species: string
  activity: string
  projectId: string
  bandDefs: EnvironmentalBandDefinition[]
  explainEnabled: boolean
  metadataJson: string
  /** Serialized model card draft (JSON) for dirty detection. */
  cardDraftJson: string
  suitabilityFileName: string | null
  explainModelFileName: string | null
}): string {
  return JSON.stringify({
    species: params.species.trim(),
    activity: params.activity.trim(),
    projectId: params.projectId,
    bands: serializeBandDefinitions(params.bandDefs),
    explain: params.explainEnabled,
    metadata: params.metadataJson,
    cardDraft: params.cardDraftJson,
    suitabilityFile: params.suitabilityFileName,
    explainFile: params.explainModelFileName,
  })
}
