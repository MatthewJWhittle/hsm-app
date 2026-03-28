import type { PointInspection } from '../types/pointInspection'
import { apiBase } from '../utils/apiBase'
import { parseApiError } from './errors'
import { parsePointInspection } from './pointInspection'

export async function fetchPointInspection(
  modelId: string,
  lng: number,
  lat: number,
  signal?: AbortSignal,
): Promise<PointInspection> {
  const params = new URLSearchParams({
    lng: String(lng),
    lat: String(lat),
  })
  const r = await fetch(
    `${apiBase()}/models/${encodeURIComponent(modelId)}/point?${params}`,
    { signal },
  )
  const text = await r.text()
  let body: unknown
  try {
    body = text ? JSON.parse(text) : null
  } catch {
    body = null
  }
  if (!r.ok) {
    throw new Error(parseApiError(body))
  }
  const parsed = parsePointInspection(body)
  if (parsed === null) {
    throw new Error('Invalid point inspection response')
  }
  return parsed
}
