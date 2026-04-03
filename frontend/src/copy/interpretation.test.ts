import { describe, expect, it } from 'vitest'
import {
  formatModelCatalogLabel,
  INTERPRETATION_DECISION_SUPPORT,
  INTERPRETATION_DRIVERS_POINTER,
  INTERPRETATION_RELATIVE_SUITABILITY,
  INTERPRETATION_SECTION_TITLE,
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
    expect(INTERPRETATION_SECTION_TITLE.length).toBeGreaterThan(0)
    expect(INTERPRETATION_RELATIVE_SUITABILITY).toMatch(/relative suitability/i)
    expect(INTERPRETATION_RELATIVE_SUITABILITY).toMatch(/present|absent/i)
    expect(INTERPRETATION_DECISION_SUPPORT).toMatch(/expert judgement|judgment/i)
    expect(INTERPRETATION_DRIVERS_POINTER).toMatch(/click the map/i)
  })
})
