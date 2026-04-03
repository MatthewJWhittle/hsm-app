import { describe, expect, it } from 'vitest'
import { clampSuitability01, SUITABILITY_VIRIDIS_GRADIENT_CSS } from './suitabilityScale'

describe('clampSuitability01', () => {
  it('clamps to 0–1', () => {
    expect(clampSuitability01(0)).toBe(0)
    expect(clampSuitability01(1)).toBe(1)
    expect(clampSuitability01(0.5)).toBe(0.5)
    expect(clampSuitability01(-0.1)).toBe(0)
    expect(clampSuitability01(1.2)).toBe(1)
  })

  it('maps non-finite to 0', () => {
    expect(clampSuitability01(Number.NaN)).toBe(0)
    expect(clampSuitability01(Number.POSITIVE_INFINITY)).toBe(0)
    expect(clampSuitability01(Number.NEGATIVE_INFINITY)).toBe(0)
  })
})

describe('SUITABILITY_VIRIDIS_GRADIENT_CSS', () => {
  it('is a linear gradient string', () => {
    expect(SUITABILITY_VIRIDIS_GRADIENT_CSS).toMatch(/^linear-gradient\(to right,/)
    expect(SUITABILITY_VIRIDIS_GRADIENT_CSS.length).toBeGreaterThan(20)
  })
})
