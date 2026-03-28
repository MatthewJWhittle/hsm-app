/** Aligns with docs/data-models.md — PointInspection, DriverVariable. */

export type DriverDirection = 'increase' | 'decrease' | 'neutral'

export interface DriverVariable {
  name: string
  direction: DriverDirection
  label?: string | null
  magnitude?: number | null
}

export interface PointInspection {
  value: number
  unit?: string | null
  drivers?: DriverVariable[] | null
}
