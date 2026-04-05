/** Aligns with docs/data-models.md — PointInspection, DriverVariable, RawEnvironmentalValue. */

export type DriverDirection = 'increase' | 'decrease' | 'neutral'

export interface DriverVariable {
  name: string
  direction: DriverDirection
  label?: string | null
  magnitude?: number | null
}

export interface RawEnvironmentalValue {
  name: string
  value: number
  unit?: string | null
}

export interface PointInspection {
  value: number
  unit?: string | null
  /** Variable influence (e.g. SHAP); empty array when explainability is off. */
  drivers?: DriverVariable[] | null
  /** Raw raster values at the click for configured bands. */
  raw_environmental_values?: RawEnvironmentalValue[] | null
}
