import type { Model, ModelCard } from '../types/model'

/** Form state for the optional Hugging Face–style model card (maps to `metadata.card` / `metadata.extras`). */
export interface ModelCardDraft {
  title: string
  summary: string
  metricsJson: string
  spatialResolutionM: string
  trainingPeriod: string
  evaluationNotes: string
  license: string
  citation: string
  extrasJson: string
}

export function emptyModelCardDraft(): ModelCardDraft {
  return {
    title: '',
    summary: '',
    metricsJson: '',
    spatialResolutionM: '',
    trainingPeriod: '',
    evaluationNotes: '',
    license: '',
    citation: '',
    extrasJson: '',
  }
}

export function modelToCardDraft(m: Model | null): ModelCardDraft {
  const c = m?.metadata?.card
  const ex = m?.metadata?.extras
  return {
    title: c?.title ?? '',
    summary: c?.summary ?? '',
    metricsJson: c?.metrics ? JSON.stringify(c.metrics, null, 2) : '',
    spatialResolutionM: c?.spatial_resolution_m != null ? String(c.spatial_resolution_m) : '',
    trainingPeriod: c?.training_period ?? '',
    evaluationNotes: c?.evaluation_notes ?? '',
    license: c?.license ?? '',
    citation: c?.citation ?? '',
    extrasJson: ex ? JSON.stringify(ex, null, 2) : '',
  }
}

export function parseModelCardDraft(
  draft: ModelCardDraft,
): { ok: true; card: ModelCard | null; extras: Record<string, string> | null } | { ok: false; message: string } {
  let metrics: Record<string, number | string> | undefined
  if (draft.metricsJson.trim()) {
    try {
      const p = JSON.parse(draft.metricsJson) as unknown
      if (p === null || typeof p !== 'object' || Array.isArray(p)) {
        return { ok: false, message: 'Metrics must be a JSON object.' }
      }
      const out: Record<string, number | string> = {}
      for (const [k, v] of Object.entries(p as Record<string, unknown>)) {
        if (typeof v === 'number' && Number.isFinite(v)) {
          out[k] = v
        } else if (typeof v === 'string') {
          out[k] = v
        } else {
          return { ok: false, message: `Metrics values must be numbers or strings (key: ${k}).` }
        }
      }
      metrics = Object.keys(out).length ? out : undefined
    } catch {
      return { ok: false, message: 'Metrics must be valid JSON.' }
    }
  }

  let extras: Record<string, string> | null = null
  if (draft.extrasJson.trim()) {
    try {
      const p = JSON.parse(draft.extrasJson) as unknown
      if (p === null || typeof p !== 'object' || Array.isArray(p)) {
        return { ok: false, message: 'Extras must be a JSON object.' }
      }
      const out: Record<string, string> = {}
      for (const [k, v] of Object.entries(p as Record<string, unknown>)) {
        if (typeof v === 'number' && Number.isFinite(v)) {
          out[k] = String(v)
        } else if (typeof v === 'string') {
          out[k] = v
        } else {
          return { ok: false, message: `Extras values must be strings or numbers (key: ${k}).` }
        }
      }
      extras = Object.keys(out).length ? out : null
    } catch {
      return { ok: false, message: 'Extras must be valid JSON.' }
    }
  }

  let spatial_resolution_m: number | undefined
  if (draft.spatialResolutionM.trim()) {
    const n = Number(draft.spatialResolutionM)
    if (!Number.isFinite(n)) {
      return { ok: false, message: 'Spatial resolution must be a number.' }
    }
    spatial_resolution_m = n
  }

  const card: ModelCard = {}
  if (draft.title.trim()) card.title = draft.title.trim()
  if (draft.summary.trim()) card.summary = draft.summary.trim()
  if (metrics) card.metrics = metrics
  if (spatial_resolution_m !== undefined) card.spatial_resolution_m = spatial_resolution_m
  if (draft.trainingPeriod.trim()) card.training_period = draft.trainingPeriod.trim()
  if (draft.evaluationNotes.trim()) card.evaluation_notes = draft.evaluationNotes.trim()
  if (draft.license.trim()) card.license = draft.license.trim()
  if (draft.citation.trim()) card.citation = draft.citation.trim()

  const hasCard = Object.keys(card).length > 0
  return { ok: true, card: hasCard ? card : null, extras }
}
