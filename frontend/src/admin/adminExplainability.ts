import type { EnvironmentalBandDefinition } from '../types/project'
import type { Model, ModelCard, ModelMetadata } from '../types/model'

/** Matches backend explainability readiness for map influence (serialized model + bands + project background). */
export function explainabilityConfiguredInCatalog(model: Model): boolean {
  const a = model.metadata?.analysis
  if (!a?.serialized_model_path?.trim()) return false
  if (!a.feature_band_names?.length) return false
  return true
}

/**
 * Build ``metadata`` for POST/PUT /models. Strips analysis fields when explainability is off;
 * sets ``feature_band_names`` from the current band selection when on.
 * When ``cardPatch`` is set, it replaces ``metadata.card`` / ``metadata.extras`` from the form (null = omit).
 */
export function buildModelMetadataForSubmit(params: {
  base: Model | null
  explainEnabled: boolean
  selectedBands: EnvironmentalBandDefinition[]
  /** When provided (create/edit with model card UI), overrides card/extras on the cloned base metadata. */
  cardPatch?: { card: ModelCard | null; extras: Record<string, string> | null } | null
}): ModelMetadata | undefined {
  const raw = params.base?.metadata
  const meta: ModelMetadata = raw
    ? (JSON.parse(JSON.stringify(raw)) as ModelMetadata)
    : {}

  if (params.cardPatch != null) {
    if (params.cardPatch.card === null) {
      delete meta.card
    } else {
      meta.card = params.cardPatch.card
    }
    if (params.cardPatch.extras === null) {
      delete meta.extras
    } else {
      meta.extras = params.cardPatch.extras
    }
  }

  if (!params.explainEnabled) {
    if (meta.analysis) {
      const { analysis: _a, ...rest } = meta
      const cleaned = { ...rest } as ModelMetadata
      return Object.keys(cleaned).length ? cleaned : undefined
    }
    return Object.keys(meta).length ? meta : undefined
  }

  meta.analysis = {
    ...meta.analysis,
    feature_band_names: params.selectedBands.map((b) => b.name),
  }
  return meta
}
