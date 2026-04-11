import type {
  DriverVariable,
  PointInspection,
  RawEnvironmentalValue,
} from '../types/pointInspection'
import { isRecord } from './jsonGuards'

function parseDriverVariable(value: unknown): DriverVariable | null {
  if (!isRecord(value)) return null
  const { name, direction, label, magnitude, display_name } = value
  if (typeof name !== 'string') return null
  if (direction !== 'increase' && direction !== 'decrease' && direction !== 'neutral') {
    return null
  }
  const out: DriverVariable = { name, direction }
  if (label !== undefined) {
    if (label !== null && typeof label !== 'string') return null
    out.label = label
  }
  if (display_name !== undefined) {
    if (display_name !== null && typeof display_name !== 'string') return null
    out.display_name = display_name
  }
  if (magnitude !== undefined) {
    if (magnitude === null) {
      out.magnitude = null
    } else if (typeof magnitude === 'number' && Number.isFinite(magnitude)) {
      out.magnitude = magnitude
    } else {
      return null
    }
  }
  return out
}

function parseRawEnvironmentalValue(value: unknown): RawEnvironmentalValue | null {
  if (!isRecord(value)) return null
  const { name, value: v, unit, description } = value
  if (typeof name !== 'string') return null
  if (typeof v !== 'number' || !Number.isFinite(v)) return null
  const out: RawEnvironmentalValue = { name, value: v }
  if (unit !== undefined) {
    if (unit !== null && typeof unit !== 'string') return null
    out.unit = unit
  }
  if (description !== undefined) {
    if (description !== null && typeof description !== 'string') return null
    out.description = description
  }
  return out
}

function parseCapabilities(value: unknown): NonNullable<PointInspection['capabilities']> | null {
  if (value === null || value === undefined) return {}
  if (!isRecord(value)) return null
  const cap: NonNullable<PointInspection['capabilities']> = {}
  for (const k of ['suitability_available', 'environmental_values_available', 'driver_influence_available'] as const) {
    if (k in value && typeof value[k] === 'boolean') {
      cap[k] = value[k]
    }
  }
  if ('notes' in value && Array.isArray(value.notes)) {
    const notes: string[] = []
    for (const n of value.notes) {
      if (typeof n !== 'string') return null
      notes.push(n)
    }
    cap.notes = notes
  }
  return cap
}

export function parsePointInspection(value: unknown): PointInspection | null {
  if (!isRecord(value)) return null
  const val = value.value
  if (typeof val !== 'number' || !Number.isFinite(val)) return null

  const out: PointInspection = { value: val }

  if ('capabilities' in value) {
    const c = parseCapabilities(value.capabilities)
    if (c === null) return null
    out.capabilities = c
  }

  if ('unit' in value) {
    const u = value.unit
    if (u !== null && u !== undefined && typeof u !== 'string') return null
    out.unit = u ?? null
  }

  if ('drivers' in value) {
    if (value.drivers == null) {
      out.drivers = null
    } else if (Array.isArray(value.drivers)) {
      const drivers: DriverVariable[] = []
      for (const d of value.drivers) {
        const dv = parseDriverVariable(d)
        if (dv === null) return null
        drivers.push(dv)
      }
      out.drivers = drivers
    } else {
      return null
    }
  }

  if ('raw_environmental_values' in value) {
    if (value.raw_environmental_values == null) {
      out.raw_environmental_values = null
    } else if (Array.isArray(value.raw_environmental_values)) {
      const raw: RawEnvironmentalValue[] = []
      for (const r of value.raw_environmental_values) {
        const rv = parseRawEnvironmentalValue(r)
        if (rv === null) return null
        raw.push(rv)
      }
      out.raw_environmental_values = raw
    } else {
      return null
    }
  }

  return out
}
