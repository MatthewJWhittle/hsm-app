import type { Model } from '../types/model'

/** Guardrail, split so the second clause can be bold in welcome / About (full sentence = ``INTERPRETATION_GUARDRAIL_SHORT``). */
export const INTERPRETATION_DIALOG_GUARDRAIL_PREFIX =
  'This map shows areas of habitat that may be more or less suitable for the selected species and activity. Higher suitability means conditions look more favourable in the model. '
export const INTERPRETATION_DIALOG_GUARDRAIL_EMPHASIS =
  'It does not confirm that bats are present, and low suitability does not prove they are absent.'

/** Primary guardrail: one string for Alerts and tests (issue #19). */
export const INTERPRETATION_GUARDRAIL_SHORT =
  INTERPRETATION_DIALOG_GUARDRAIL_PREFIX + INTERPRETATION_DIALOG_GUARDRAIL_EMPHASIS

/** Section titles inside the welcome / “About this map” dialog body. */
export const INTERPRETATION_DIALOG_SECTION_MEANING = 'What the map shows'
export const INTERPRETATION_DIALOG_SECTION_USE = 'Using the map'

/** Secondary line under the guardrail (map sidebar). */
export const INTERPRETATION_DECISION_SUPPORT =
  'Use the map to compare places and target survey effort, alongside field survey and expert judgement.'

/** Map “About / welcome”: what happens when the user inspects a point. */
export const INTERPRETATION_DRIVERS_POINTER =
  'Click the map to see whether a place looks low, moderate or high suitability, plus the environmental factors that may be influencing that local score when the model supports it.'

/** Section overline in Layer details: the selected model. */
export const LAYER_DETAILS_SECTION_LAYER = 'Layer'

/** Section overline in Layer details: the catalog project, when applicable. */
export const LAYER_DETAILS_SECTION_PROJECT = 'Project'

/** First-sentence only; compact hint above attribution. */
export const INTERPRETATION_CLICK_MAP_SHORT =
  'Click the map to interpret habitat suitability at a place.'

/** Point inspection: variable influence (e.g. SHAP) when the model has explainability artefacts. */
export const INTERPRETATION_INFLUENCE_CAPTION =
  'Estimated contribution to suitability at this location (stronger magnitude = more influence).'

/** Point inspection: raw environmental raster values at the click (secondary detail). */
export const INTERPRETATION_RAW_VALUES_CAPTION =
  'Values sampled from the environmental layers at this point.'

/** Short reminder in the point-inspection HUD (repeat key caution). */
export const INTERPRETATION_HUD_REMINDER =
  'This is modelled habitat suitability, not a confirmed record.'

/** Compact guardrail attached to the suitability legend. */
export const SUITABILITY_LEGEND_GUARDRAIL = 'Relative suitability, not confirmed presence.'

/** Map top-right help (?): aria + tooltip. */
export const MAP_CONTEXT_INFO_ARIA = 'What am I looking at? Opens a short guide to this map view.'
export const MAP_CONTEXT_INFO_TOOLTIP = 'What am I looking at?'

/**
 * Expanded floating card — **Help** opens the same “About this map” dialog as the top-right
 * control; copy here stresses the **full guide** so it does not read as a different feature.
 */
export const MAP_FLOATING_ABOUT_MAP_TOOLTIP =
  'Full map guide: what the colours mean, how to read the view, and key limitations.'
export const MAP_FLOATING_ABOUT_MAP_ARIA =
  'Open the full map guide: interpretation, scale, and how to use the view.'

/**
 * One-time coachmark next to the top-right help control on first visit; dismisses on click-away or
 * when the user opens the guide. Kept short for a single horizontal chip.
 */
export const MAP_CONTEXT_COACHMARK = 'Click here to find out more about the map'

/** Dialog title: general map / app interpretation (not layer-specific). */
export const MAP_INFO_DIALOG_TITLE = 'About this map'

/** First-visit welcome modal; same substance as “About”, friendlier entry title. */
export const MAP_WELCOME_DIALOG_TITLE = 'What this map shows'

/** Dialog title: catalog model, project, and layer metadata. */
export const LAYER_DETAILS_DIALOG_TITLE = 'Layer details'

/** When the model references a project missing from the loaded catalog (issue #19 / PR review). */
export const LAYER_DETAILS_PROJECT_METADATA_UNAVAILABLE =
  'Project metadata isn’t available in the catalog for this layer right now. The map may still show the layer correctly.'

/**
 * Display line for catalog subtitle from ``metadata.card`` (title · version).
 */
export function formatModelCatalogLabel(model: Pick<Model, 'metadata'>): string {
  const c = model.metadata?.card
  return [c?.title, c?.version].filter(Boolean).join(' · ') || '-'
}
