import type { Model } from '../types/model'
import { apiBase } from '../utils/apiBase'
import { parseModelList } from './models'

export async function fetchModelCatalog(opts?: {
  token?: string | null
}): Promise<Model[]> {
  const base = apiBase()
  const headers: Record<string, string> = {}
  if (opts?.token) headers.Authorization = `Bearer ${opts.token}`
  const r = await fetch(`${base}/models`, { headers })
  if (!r.ok) throw new Error(r.statusText || String(r.status))
  const raw: unknown = await r.json()
  const list = parseModelList(raw)
  if (list === null) {
    throw new Error('Invalid model catalog response')
  }
  return list
}
