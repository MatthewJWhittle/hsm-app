import { describe, expect, it } from 'vitest'
import {
  clampSuitability01,
  suitabilityDisplayBinIndex01,
  suitabilityDisplayBinSwatchColors,
  SUITABILITY_VIRIDIS_GRADIENT_CSS,
  viridisCssColor,
} from './suitabilityScale'

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

describe('viridisCssColor', () => {
  it('returns rgb at ends and middle', () => {
    expect(viridisCssColor(0)).toMatch(/^rgb\(\d+, \d+, \d+\)$/)
    expect(viridisCssColor(1)).toMatch(/^rgb\(\d+, \d+, \d+\)$/)
    expect(viridisCssColor(0.5)).toMatch(/^rgb\(\d+, \d+, \d+\)$/)
  })
})

describe('suitabilityDisplayBinIndex01', () => {
  it('maps five equal-width display bins', () => {
    expect(suitabilityDisplayBinIndex01(0)).toBe(0)
    expect(suitabilityDisplayBinIndex01(0.19)).toBe(0)
    expect(suitabilityDisplayBinIndex01(0.2)).toBe(1)
    expect(suitabilityDisplayBinIndex01(0.39)).toBe(1)
    expect(suitabilityDisplayBinIndex01(0.99)).toBe(4)
    expect(suitabilityDisplayBinIndex01(1)).toBe(4)
  })
})

describe('suitabilityDisplayBinSwatchColors', () => {
  it('returns five rgb strings', () => {
    const c = suitabilityDisplayBinSwatchColors()
    expect(c).toHaveLength(5)
    expect(c.every((x) => /^rgb\(\d+, \d+, \d+\)$/.test(x))).toBe(true)
  })
})
