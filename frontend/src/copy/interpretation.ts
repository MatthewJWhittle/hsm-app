import type { Model } from '../types/model'

/** Primary guardrail — use in Alert / high-visibility surfaces (issue #19). */
export const INTERPRETATION_GUARDLINE_SHORT =
  'This map shows modelled relative suitability, not confirmed presence or absence.'

/** Secondary line under the guardrail (map sidebar). */
export const INTERPRETATION_DECISION_SUPPORT =
  'Use it alongside field survey and expert judgement—not as a substitute.'

/** Where to find local score and drivers (point inspection). */
export const INTERPRETATION_DRIVERS_POINTER =
  'Click the map for a local score, drivers when available, and technical details.'

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

/**
 * Display line for catalog model name/version (matches admin list pattern).
 */
export function formatModelCatalogLabel(model: Pick<Model, 'model_name' | 'model_version'>): string {
  return [model.model_name, model.model_version].filter(Boolean).join(' · ') || '—'
}
