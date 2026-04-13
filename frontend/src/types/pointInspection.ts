/** Aligns with docs/data-models.md — PointInspection, DriverVariable, RawEnvironmentalValue. */

export type DriverDirection = 'increase' | 'decrease' | 'neutral'

export interface DriverVariable {
  name: string
  direction: DriverDirection
  label?: string | null
  magnitude?: number | null
  /** Human-friendly title when it differs from ``name`` (from catalog display names). */
  display_name?: string | null
}

export interface RawEnvironmentalValue {
  name: string
  value: number
  unit?: string | null
  /** Longer explanation from the catalog band definition, if any. */
  description?: string | null
}

/** Explains which parts of the inspection are populated (see GET /models/{id}/point). */
export interface PointInspectionCapabilities {
  suitability_available?: boolean
  environmental_values_available?: boolean
  driver_influence_available?: boolean
  notes?: string[]
}

export interface PointInspection {
  value: number
  unit?: string | null
  /** Which subsystems contributed (and why drivers/env may be empty). */
  capabilities?: PointInspectionCapabilities | null
  /** Variable influence (e.g. SHAP); empty array when explainability is off. */
  drivers?: DriverVariable[] | null
  /** Raw raster values at the click for configured bands. */
  raw_environmental_values?: RawEnvironmentalValue[] | null
}
