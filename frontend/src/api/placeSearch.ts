import { apiBase } from '../utils/apiBase'
import { readFetchErrorDetail } from './errors'
import { isRecord } from './jsonGuards'

export interface PlaceSearchResult {
  id: string
  label: string
  center: {
    lng: number
    lat: number
  }
  bbox?: [number, number, number, number] | null
  source: string
  attribution?: string | null
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value)
}

function parseCenter(value: unknown): PlaceSearchResult['center'] | null {
  if (!isRecord(value)) return null
  const { lng, lat } = value
  if (!isFiniteNumber(lng) || !isFiniteNumber(lat)) return null
  if (lng < -180 || lng > 180 || lat < -90 || lat > 90) return null
  return { lng, lat }
}

function parseBbox(value: unknown): [number, number, number, number] | null {
  if (value == null) return null
  if (!Array.isArray(value) || value.length !== 4) return null
  if (!value.every(isFiniteNumber)) return null
  const [west, south, east, north] = value
  if (west >= east || south >= north) return null
  if (west < -180 || east > 180 || south < -90 || north > 90) return null
  return [west, south, east, north]
}

export function parsePlaceSearchResult(value: unknown): PlaceSearchResult | null {
  if (!isRecord(value)) return null
  const { id, label, center, bbox, source, attribution } = value
  if (typeof id !== 'string' || typeof label !== 'string' || typeof source !== 'string') {
    return null
  }

  const parsedCenter = parseCenter(center)
  if (parsedCenter === null) return null

  const parsedBbox = parseBbox(bbox)
  if (bbox != null && parsedBbox === null) return null
  if (attribution != null && typeof attribution !== 'string') return null

  return {
    id,
    label,
    center: parsedCenter,
    bbox: parsedBbox,
    source,
    attribution: attribution ?? null,
  }
}

export function parsePlaceSearchResponse(value: unknown): PlaceSearchResult[] | null {
  if (!isRecord(value) || !Array.isArray(value.results)) return null
  const results = value.results.map(parsePlaceSearchResult)
  if (results.some((result) => result === null)) return null
  return results as PlaceSearchResult[]
}

export async function searchPlaces(
  query: string,
  signal?: AbortSignal,
  opts?: { limit?: number },
): Promise<PlaceSearchResult[]> {
  const trimmed = query.trim()
  const searchParams = new URLSearchParams({
    q: trimmed,
    limit: String(opts?.limit ?? 5),
  })
  const response = await fetch(`${apiBase()}/geocode/search?${searchParams.toString()}`, { signal })
  if (!response.ok) {
    throw new Error(await readFetchErrorDetail(response))
  }

  const parsed = parsePlaceSearchResponse(await response.json())
  if (parsed === null) {
    throw new Error('Invalid place search response')
  }
  return parsed
}
