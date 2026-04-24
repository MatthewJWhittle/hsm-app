import { describe, expect, it } from 'vitest'
import {
  clampSuitability01,
  SUITABILITY_HUD_BIN_COUNT,
  suitabilityDisplayBinEdges,
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
  it('maps five equal-width display bins by default', () => {
    expect(suitabilityDisplayBinIndex01(0)).toBe(0)
    expect(suitabilityDisplayBinIndex01(0.19)).toBe(0)
    expect(suitabilityDisplayBinIndex01(0.2)).toBe(1)
    expect(suitabilityDisplayBinIndex01(0.39)).toBe(1)
    expect(suitabilityDisplayBinIndex01(0.99)).toBe(4)
    expect(suitabilityDisplayBinIndex01(1)).toBe(4)
  })

  it('maps ten equal-width display bins in the point HUD', () => {
    expect(suitabilityDisplayBinIndex01(0, SUITABILITY_HUD_BIN_COUNT)).toBe(0)
    expect(suitabilityDisplayBinIndex01(0.09, SUITABILITY_HUD_BIN_COUNT)).toBe(0)
    expect(suitabilityDisplayBinIndex01(0.1, SUITABILITY_HUD_BIN_COUNT)).toBe(1)
    expect(suitabilityDisplayBinIndex01(0.19, SUITABILITY_HUD_BIN_COUNT)).toBe(1)
    expect(suitabilityDisplayBinIndex01(0.99, SUITABILITY_HUD_BIN_COUNT)).toBe(9)
    expect(suitabilityDisplayBinIndex01(1, SUITABILITY_HUD_BIN_COUNT)).toBe(9)
  })
})

describe('suitabilityDisplayBinEdges', () => {
  it('returns 0 to 1 in equal steps', () => {
    expect(suitabilityDisplayBinEdges(5)).toEqual([0, 0.2, 0.4, 0.6, 0.8, 1])
    expect(suitabilityDisplayBinEdges(10).length).toBe(11)
    expect(suitabilityDisplayBinEdges(10)[1]).toBe(0.1)
  })
})

describe('suitabilityDisplayBinSwatchColors', () => {
  it('returns rgb strings (default 5, optional count)', () => {
    const c = suitabilityDisplayBinSwatchColors()
    expect(c).toHaveLength(5)
    const c10 = suitabilityDisplayBinSwatchColors(10)
    expect(c10).toHaveLength(10)
    expect(c.every((x) => /^rgb\(\d+, \d+, \d+\)$/.test(x))).toBe(true)
  })
})
