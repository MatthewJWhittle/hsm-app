import { describe, expect, it } from 'vitest'
import {
  formatModelCatalogLabel,
  INTERPRETATION_DECISION_SUPPORT,
  INTERPRETATION_DRIVERS_POINTER,
  INTERPRETATION_INFLUENCE_CAPTION,
  INTERPRETATION_RAW_VALUES_CAPTION,
  LAYER_DETAILS_DIALOG_TITLE,
  LAYER_DETAILS_SECTION_LAYER,
  LAYER_DETAILS_SECTION_PROJECT,
  LAYER_DETAILS_PROJECT_METADATA_UNAVAILABLE,
  MAP_INFO_DIALOG_TITLE,
  INTERPRETATION_DIALOG_SECTION_MEANING,
  INTERPRETATION_DIALOG_SECTION_USE,
  INTERPRETATION_GUARDRAIL_SHORT,
  INTERPRETATION_HUD_REMINDER,
} from './interpretation'

describe('formatModelCatalogLabel', () => {
  it('joins name and version with middle dot', () => {
    expect(
      formatModelCatalogLabel({
        metadata: { card: { title: 'Habitat v2', version: '2024-01' } },
      }),
    ).toBe('Habitat v2 · 2024-01')
  })

  it('returns name only when version missing', () => {
    expect(formatModelCatalogLabel({ metadata: { card: { title: 'Only' } } })).toBe('Only')
  })

  it('returns em dash when both missing', () => {
    expect(formatModelCatalogLabel({ metadata: {} })).toBe('-')
  })
})

describe('interpretation copy', () => {
  it('includes stable phrases for product review (issue #19)', () => {
    expect(INTERPRETATION_GUARDRAIL_SHORT).toMatch(/relative suitability/i)
    expect(INTERPRETATION_GUARDRAIL_SHORT).toMatch(/presence|absent/i)
    expect(INTERPRETATION_DECISION_SUPPORT).toMatch(/expert judgement|judgment/i)
    expect(INTERPRETATION_DRIVERS_POINTER).toMatch(/click the map|map/i)
    expect(INTERPRETATION_DRIVERS_POINTER).toMatch(/suitability|layer/i)
    expect(INTERPRETATION_DRIVERS_POINTER).not.toMatch(/Layer details|About this map|info icon|help icon/i)
    expect(INTERPRETATION_DIALOG_SECTION_MEANING.length).toBeGreaterThan(0)
    expect(INTERPRETATION_DIALOG_SECTION_USE.length).toBeGreaterThan(0)
    expect(LAYER_DETAILS_SECTION_LAYER).toBe('Layer')
    expect(LAYER_DETAILS_SECTION_PROJECT).toBe('Project')
    expect(INTERPRETATION_INFLUENCE_CAPTION).toMatch(/contribution|suitability|influence/i)
    expect(INTERPRETATION_RAW_VALUES_CAPTION).toMatch(/environmental|values|point/i)
    expect(INTERPRETATION_HUD_REMINDER).toMatch(/relative suitability|presence|absent/i)
    expect(MAP_INFO_DIALOG_TITLE.length).toBeGreaterThan(0)
    expect(LAYER_DETAILS_DIALOG_TITLE.length).toBeGreaterThan(0)
    expect(LAYER_DETAILS_PROJECT_METADATA_UNAVAILABLE).toMatch(/catalog/i)
  })
})
