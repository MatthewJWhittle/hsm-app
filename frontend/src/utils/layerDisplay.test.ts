import { describe, expect, it } from 'vitest'
import type { Model } from '../types/model'
import {
  layerAutocompleteLabel,
  layerDisplayName,
  layerPrimaryLine,
  layerSecondaryLine,
} from './layerDisplay'

function baseModel(over: Partial<Model> = {}): Model {
  return {
    id: 'mid',
    species: 'Myotis daubentonii',
    activity: 'In flight',
    artifact_root: 'a',
    suitability_cog_path: 'b',
    ...over,
  }
}

describe('layerDisplay', () => {
  it('layerDisplayName uses catalog species and plain activity labels', () => {
    expect(layerDisplayName(baseModel())).toBe('Myotis daubentonii · Foraging and commuting habitat')
  })

  it('layerPrimaryLine prefers plain species and activity over card title', () => {
    const m = baseModel({
      metadata: { card: { title: 'Yorkshire run A' } },
    })
    expect(layerPrimaryLine(m)).toBe('Myotis daubentonii · Foraging and commuting habitat')
  })

  it('layerPrimaryLine falls back to layerDisplayName', () => {
    expect(layerPrimaryLine(baseModel())).toBe('Myotis daubentonii · Foraging and commuting habitat')
  })

  it('layerSecondaryLine keeps original activity when the primary activity label is rewritten', () => {
    const m = baseModel({ metadata: { card: { title: 'T' } } })
    expect(layerSecondaryLine(m)).toBe('Myotis daubentonii · In flight')
  })

  it('layerSecondaryLine is null when the scientific label is already primary', () => {
    expect(layerSecondaryLine(baseModel({ species: 'Unknown species', activity: 'Survey' }))).toBeNull()
  })

  it('layerAutocompleteLabel includes primary and scientific label', () => {
    const m = baseModel({ metadata: { card: { title: 'T' } } })
    expect(layerAutocompleteLabel(m)).toBe(
      'Myotis daubentonii · Foraging and commuting habitat (Myotis daubentonii · In flight)',
    )
  })

  it('layerAutocompleteLabel does not duplicate when scientific label is primary', () => {
    const full = 'Unknown species · Survey'
    const m = baseModel({ species: 'Unknown species', activity: 'Survey', metadata: { card: { title: full } } })
    expect(layerAutocompleteLabel(m)).toBe(full)
    expect(layerSecondaryLine(m)).toBeNull()
  })
})
