import type { DriverVariable, PointInspection } from '../types/pointInspection'
import { isRecord } from './jsonGuards'

function parseDriverVariable(value: unknown): DriverVariable | null {
  if (!isRecord(value)) return null
  const { name, direction, label, magnitude } = value
  if (typeof name !== 'string') return null
  if (direction !== 'increase' && direction !== 'decrease' && direction !== 'neutral') {
    return null
  }
  const out: DriverVariable = { name, direction }
  if (label !== undefined) {
    if (label !== null && typeof label !== 'string') return null
    out.label = label
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

export function parsePointInspection(value: unknown): PointInspection | null {
  if (!isRecord(value)) return null
  const v = value.value
  if (typeof v !== 'number' || !Number.isFinite(v)) return null

  const out: PointInspection = { value: v }

  if ('unit' in value) {
    const u = value.unit
    if (u !== null && u !== undefined && typeof u !== 'string') return null
    out.unit = u ?? null
  }

  if ('drivers' in value && value.drivers != null) {
    if (!Array.isArray(value.drivers)) return null
    const drivers: DriverVariable[] = []
    for (const d of value.drivers) {
      const dv = parseDriverVariable(d)
      if (dv === null) return null
      drivers.push(dv)
    }
    out.drivers = drivers
  }

  return out
}
