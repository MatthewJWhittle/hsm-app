/** Aligns with docs/data-models.md — Model (catalog). */

export interface Model {
  id: string
  species: string
  activity: string
  artifact_root: string
  suitability_cog_path: string
  model_name?: string | null
  model_version?: string | null
  driver_config?: Record<string, unknown> | null
}
