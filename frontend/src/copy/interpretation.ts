import type { Model } from '../types/model'

/** Section title for map interpretation (issue #19 / application-spec). */
export const INTERPRETATION_SECTION_TITLE = 'What this map shows'

/**
 * Short, plain-language caveats aligned with docs/product-principles.md
 * (decision support, relative output, visible limitations).
 */
export const INTERPRETATION_RELATIVE_SUITABILITY =
  'The layer shows relative suitability from the model, not proof that a species is present or absent. A high value does not confirm presence; a low value does not confirm absence.'

export const INTERPRETATION_DECISION_SUPPORT =
  'Use this map to support planning and discussion alongside field survey and expert judgement—it does not replace them.'

/** Where to find local driver context (point inspection in App). */
export const INTERPRETATION_DRIVERS_POINTER =
  'Click the map to see what drives suitability at that location and to review technical details for the selected layer.'

/**
 * Display line for catalog model name/version (matches admin list pattern).
 */
export function formatModelCatalogLabel(model: Pick<Model, 'model_name' | 'model_version'>): string {
  return [model.model_name, model.model_version].filter(Boolean).join(' · ') || '—'
}
