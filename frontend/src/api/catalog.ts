import type { Model } from '../types/model'
import { apiBase } from '../utils/apiBase'
import { parseModelList } from './models'

export async function fetchModelCatalog(): Promise<Model[]> {
  const base = apiBase()
  const r = await fetch(`${base}/models`)
  if (!r.ok) throw new Error(r.statusText || String(r.status))
  const raw: unknown = await r.json()
  const list = parseModelList(raw)
  if (list === null) {
    throw new Error('Invalid model catalog response')
  }
  return list
}
