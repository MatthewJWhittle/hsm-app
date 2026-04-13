import { describe, expect, it } from 'vitest'

import { bandsFromPasteTokens, tokenizeFeaturePaste } from './adminFeaturePaste'
import type { EnvironmentalBandDefinition } from '../types/project'

const defs: EnvironmentalBandDefinition[] = [
  { index: 0, name: 'band_a', label: 'A' },
  { index: 1, name: 'band_b', label: 'B' },
]

describe('tokenizeFeaturePaste', () => {
  it('splits on commas and semicolons', () => {
    expect(tokenizeFeaturePaste('a, b; c')).toEqual(['a', 'b', 'c'])
  })
})

describe('bandsFromPasteTokens', () => {
  it('matches by name case-insensitively', () => {
    const { matched, unknown } = bandsFromPasteTokens(['Band_A', 'band_b'], defs)
    expect(unknown).toEqual([])
    expect(matched.map((b) => b.name)).toEqual(['band_a', 'band_b'])
  })

  it('returns unknown tokens', () => {
    const { matched, unknown } = bandsFromPasteTokens(['band_a', 'nope'], defs)
    expect(matched.map((b) => b.name)).toEqual(['band_a'])
    expect(unknown).toEqual(['nope'])
  })
})
