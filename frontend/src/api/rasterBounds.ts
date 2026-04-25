import type { Model } from '../types/model'
import { titilerBase } from '../utils/apiBase'
import { resolveSuitabilityPath, titilerRasterUrlParam } from '../utils/cogPath'
import { isRecord } from './jsonGuards'

export type RasterBounds = [[number, number], [number, number]]

function isFiniteNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value)
}

export function parseTitilerBounds(value: unknown): RasterBounds | null {
  if (!isRecord(value)) return null
  const { bounds, crs } = value
  if (!Array.isArray(bounds) || bounds.length !== 4) return null
  if (!bounds.every(isFiniteNumber)) return null
  if (typeof crs !== 'string' || !crs.includes('4326')) return null

  const [west, south, east, north] = bounds
  if (west >= east || south >= north) return null
  if (west < -180 || east > 180 || south < -90 || north > 90) return null

  return [
    [west, south],
    [east, north],
  ]
}

export async function fetchRasterBounds(
  model: Model,
  signal?: AbortSignal,
): Promise<RasterBounds> {
  const resolvedPath = resolveSuitabilityPath(model)
  const searchParams = new URLSearchParams({
    url: titilerRasterUrlParam(resolvedPath),
    crs: 'EPSG:4326',
  })
  const base = titilerBase().replace(/\/$/, '')
  const response = await fetch(`${base}/cog/bounds?${searchParams.toString()}`, { signal })
  if (!response.ok) {
    throw new Error(response.statusText || `TiTiler bounds request failed: ${response.status}`)
  }

  const parsed = parseTitilerBounds(await response.json())
  if (parsed === null) {
    throw new Error('Invalid TiTiler bounds response')
  }
  return parsed
}
