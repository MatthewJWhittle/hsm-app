/** Aligns with backend ``Model`` / ``ModelMetadata`` (docs/data-models.md). */

export interface ModelCard {
  title?: string | null
  /** Optional revision label (e.g. date, run id). */
  version?: string | null
  summary?: string | null
  spatial_resolution_m?: number | null
  primary_metric_type?: string | null
  primary_metric_value?: string | null
  /** Legacy responses only; prefer primary_metric_* */
  metrics?: Record<string, number | string> | null
}

export interface ModelAnalysis {
  /**
   * Ordered machine names matching the parent project’s environmental_band_definitions.name
   * (same order as the estimator’s feature matrix). The server resolves these to band indices.
   */
  feature_band_names?: string[] | null
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
  /** ISO-8601 UTC, server-set when the layer was first registered */
  created_at?: string | null
  /** ISO-8601 UTC, server-set on each save */
  updated_at?: string | null
  metadata?: ModelMetadata | null
}

export function getFeatureBandNames(m: Model): string[] | null {
  const names = m.metadata?.analysis?.feature_band_names
  if (!names?.length) return null
  return names
}
