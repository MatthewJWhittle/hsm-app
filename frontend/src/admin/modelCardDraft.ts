import type { Model, ModelCard } from '../types/model'

/** Default primary metric for habitat suitability-style models */
export const PRIMARY_METRIC_TYPES = ['AUC', 'F1', 'Accuracy', 'Log loss', 'R²', 'Custom'] as const

export type ExtraPair = { key: string; value: string }

/** Form state for the model card (maps to ``metadata.card`` / ``metadata.extras``). */
export interface ModelCardDraft {
  title: string
  version: string
  summary: string
  spatialResolutionM: string
  primaryMetricType: string
  /** When ``primaryMetricType`` is ``Custom``, this becomes ``primary_metric_type`` on save. */
  customMetricLabel: string
  primaryMetricValue: string
  extrasPairs: ExtraPair[]
}

export function emptyModelCardDraft(): ModelCardDraft {
  return {
    title: '',
    version: '',
    summary: '',
    spatialResolutionM: '',
    primaryMetricType: 'AUC',
    customMetricLabel: '',
    primaryMetricValue: '',
    extrasPairs: [{ key: '', value: '' }],
  }
}

function extrasObjectToPairs(ex: Record<string, string> | null | undefined): ExtraPair[] {
  if (!ex || Object.keys(ex).length === 0) return [{ key: '', value: '' }]
  return Object.entries(ex).map(([key, value]) => ({ key, value }))
}

export function modelToCardDraft(m: Model | null): ModelCardDraft {
  const c = m?.metadata?.card
  const ex = m?.metadata?.extras

  const storedType = c?.primary_metric_type?.trim() ?? ''
  let primaryMetricType: string = 'AUC'
  let customMetricLabel = ''
  if (storedType) {
    if ((PRIMARY_METRIC_TYPES as readonly string[]).includes(storedType)) {
      primaryMetricType = storedType === 'Custom' ? 'Custom' : storedType
    } else {
      primaryMetricType = 'Custom'
      customMetricLabel = storedType
    }
  }
  let primaryMetricValue = c?.primary_metric_value ?? ''
  if (!primaryMetricValue && c?.metrics && typeof c.metrics === 'object') {
    const auc = c.metrics.auc ?? c.metrics.AUC
    if (auc !== undefined && auc !== null) {
      primaryMetricType = 'AUC'
      primaryMetricValue = String(auc)
    }
  }

  return {
    title: c?.title ?? '',
    version: c?.version ?? '',
    summary: c?.summary ?? '',
    spatialResolutionM: c?.spatial_resolution_m != null ? String(c.spatial_resolution_m) : '',
    primaryMetricType,
    customMetricLabel,
    primaryMetricValue,
    extrasPairs: extrasObjectToPairs(ex ?? undefined),
  }
}

export function parseModelCardDraft(
  draft: ModelCardDraft,
): { ok: true; card: ModelCard | null; extras: Record<string, string> | null } | { ok: false; message: string } {
  let extras: Record<string, string> | null = null
  const out: Record<string, string> = {}
  for (const row of draft.extrasPairs) {
    const k = row.key.trim()
    if (!k) continue
    out[k] = row.value.trim()
  }
  extras = Object.keys(out).length ? out : null

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
  if (draft.version.trim()) card.version = draft.version.trim()
  if (draft.summary.trim()) card.summary = draft.summary.trim()
  if (spatial_resolution_m !== undefined) card.spatial_resolution_m = spatial_resolution_m

  const mv = draft.primaryMetricValue.trim()
  if (mv) {
    let metricTypeResolved: string | undefined
    if (draft.primaryMetricType === 'Custom') {
      const custom = draft.customMetricLabel.trim()
      if (!custom) {
        return { ok: false, message: 'Enter a name for the custom metric, or choose another type.' }
      }
      metricTypeResolved = custom
    } else if (draft.primaryMetricType.trim()) {
      metricTypeResolved = draft.primaryMetricType.trim()
    }
    if (metricTypeResolved) {
      card.primary_metric_type = metricTypeResolved
      card.primary_metric_value = mv
    }
  }

  const hasCard = Object.keys(card).length > 0
  return { ok: true, card: hasCard ? card : null, extras }
}
