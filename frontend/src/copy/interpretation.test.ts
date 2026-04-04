import { describe, expect, it } from 'vitest'
import {
  formatModelCatalogLabel,
  INTERPRETATION_CRS_NOTE,
  INTERPRETATION_DECISION_SUPPORT,
  INTERPRETATION_DRIVERS_POINTER,
  INTERPRETATION_DRIVERS_RAW,
  LAYER_DETAILS_DIALOG_TITLE,
  LAYER_DETAILS_PROJECT_METADATA_UNAVAILABLE,
  MAP_INFO_DIALOG_TITLE,
  INTERPRETATION_GUARDRAIL_SHORT,
  INTERPRETATION_HUD_REMINDER,
} from './interpretation'

describe('formatModelCatalogLabel', () => {
  it('joins name and version with middle dot', () => {
    expect(formatModelCatalogLabel({ model_name: 'Habitat v2', model_version: '2024-01' })).toBe(
      'Habitat v2 · 2024-01',
    )
  })

  it('returns name only when version missing', () => {
    expect(formatModelCatalogLabel({ model_name: 'Only', model_version: null })).toBe('Only')
  })

  it('returns em dash when both missing', () => {
    expect(formatModelCatalogLabel({ model_name: null, model_version: null })).toBe('—')
  })
})

describe('interpretation copy', () => {
  it('includes stable phrases for product review (issue #19)', () => {
    expect(INTERPRETATION_GUARDRAIL_SHORT).toMatch(/relative suitability/i)
    expect(INTERPRETATION_GUARDRAIL_SHORT).toMatch(/presence|absent/i)
    expect(INTERPRETATION_DECISION_SUPPORT).toMatch(/expert judgement|judgment/i)
    expect(INTERPRETATION_DRIVERS_POINTER).toMatch(/click the map/i)
    expect(INTERPRETATION_DRIVERS_RAW).toMatch(/environmental|inputs/i)
    expect(INTERPRETATION_HUD_REMINDER).toMatch(/relative suitability|presence|absent/i)
    expect(INTERPRETATION_CRS_NOTE).toMatch(/Web Mercator/i)
    expect(MAP_INFO_DIALOG_TITLE.length).toBeGreaterThan(0)
    expect(LAYER_DETAILS_DIALOG_TITLE.length).toBeGreaterThan(0)
    expect(LAYER_DETAILS_PROJECT_METADATA_UNAVAILABLE).toMatch(/catalog/i)
  })
})
