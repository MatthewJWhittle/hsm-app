import type { Model } from '../types/model'

/** Primary guardrail — use in Alert / high-visibility surfaces (issue #19). */
export const INTERPRETATION_GUARDRAIL_SHORT =
  'This map shows modelled relative suitability, not confirmed presence or absence.'

/** Secondary line under the guardrail (map sidebar). */
export const INTERPRETATION_DECISION_SUPPORT =
  'Use it alongside field survey and expert judgement—not as a substitute.'

/** Where to find local score and drivers (point inspection). */
export const INTERPRETATION_DRIVERS_POINTER =
  'Click the map for a local score, drivers when available, and technical details.'

/** Point inspection — variable influence (e.g. SHAP) when the model has explainability artefacts. */
export const INTERPRETATION_INFLUENCE_CAPTION =
  'Estimated contribution to suitability at this location (stronger magnitude = more influence).'

/** Point inspection — raw environmental raster values at the click (secondary detail). */
export const INTERPRETATION_RAW_VALUES_CAPTION =
  'Values sampled from the environmental layers at this point.'

/** Short reminder in the point-inspection HUD (repeat key caution). */
export const INTERPRETATION_HUD_REMINDER =
  'Modelled relative suitability—not confirmed presence or absence on the ground.'

/** CRS / layout note (dialog and help). */
export const INTERPRETATION_CRS_NOTE =
  'Uses the usual web map layout (Web Mercator). Uploaded layers need to match that format.'

/** Dialog title — general map / app interpretation (not layer-specific). */
export const MAP_INFO_DIALOG_TITLE = 'About this map'

/** Dialog title — catalog model, project, and layer metadata. */
export const LAYER_DETAILS_DIALOG_TITLE = 'Layer details'

/** When the model references a project missing from the loaded catalog (issue #19 / PR review). */
export const LAYER_DETAILS_PROJECT_METADATA_UNAVAILABLE =
  'Project metadata isn’t available in the catalog for this layer right now. The map may still show the layer correctly.'

/**
 * Display line for catalog subtitle from ``metadata.card`` (title · version).
 */
export function formatModelCatalogLabel(model: Pick<Model, 'metadata'>): string {
  const c = model.metadata?.card
  return [c?.title, c?.version].filter(Boolean).join(' · ') || '—'
}
