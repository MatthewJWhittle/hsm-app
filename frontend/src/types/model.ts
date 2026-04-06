/** Aligns with backend ``Model`` / ``ModelMetadata`` (docs/data-models.md). */

export interface ModelCard {
  title?: string | null
  summary?: string | null
  /** Metric name -> number or short string */
  metrics?: Record<string, number | string> | null
  spatial_resolution_m?: number | null
  training_period?: string | null
  evaluation_notes?: string | null
  license?: string | null
  citation?: string | null
}

export interface ModelAnalysis {
  /** 0-based indices into the project environmental COG (feature order). */
  feature_band_indices?: number[] | null
  /** Path to pickled sklearn estimator relative to artifact_root. */
  serialized_model_path?: string | null
  positive_class_index?: number | null
  driver_cog_path?: string | null
}

export interface ModelMetadata {
  card?: ModelCard | null
  extras?: Record<string, string> | null
  analysis?: ModelAnalysis | null
}

export interface Model {
  id: string
  project_id?: string | null
  species: string
  activity: string
  artifact_root: string
  suitability_cog_path: string
  model_name?: string | null
  model_version?: string | null
  metadata?: ModelMetadata | null
}

export function getFeatureBandIndices(m: Model): number[] | null {
  const idx = m.metadata?.analysis?.feature_band_indices
  if (!idx?.length) return null
  return idx
}
