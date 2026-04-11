/** Catalog project (issue #14) — shared environmental COG; models reference ``project_id``. */

export interface EnvironmentalBandDefinition {
  index: number
  /** Machine-friendly name (GDAL / band_i); matches training columns. */
  name: string
  /** Optional human-friendly display name (map UI). */
  label?: string | null
  /** Optional longer explanation of what the variable measures. */
  description?: string | null
}

export interface CatalogProject {
  id: string
  name: string
  description?: string | null
  status: 'active' | 'archived'
  visibility: 'public' | 'private'
  allowed_uids: string[]
  /** Set after environmental COG is uploaded. */
  driver_artifact_root?: string | null
  driver_cog_path?: string | null
  /** Per-band names/labels for the environmental COG (aligned with raster band order). */
  environmental_band_definitions?: EnvironmentalBandDefinition[] | null
  /** Present only on upload responses when names were inferred from the raster (not stored). */
  band_inference_notes?: string[] | null
  /** SHAP reference sample (Parquet); generated when the environmental COG is uploaded. */
  explainability_background_path?: string | null
  /** Row count of the last generated background Parquet (random pixels). */
  explainability_background_sample_rows?: number | null
  /** ISO 8601 time when the background Parquet was last written. */
  explainability_background_generated_at?: string | null
  created_at?: string | null
  updated_at?: string | null
}
