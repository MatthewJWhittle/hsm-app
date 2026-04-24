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
  it('layerDisplayName is species and activity', () => {
    expect(layerDisplayName(baseModel())).toBe('Myotis daubentonii · In flight')
  })

  it('layerPrimaryLine uses card title when set', () => {
    const m = baseModel({
      metadata: { card: { title: 'Yorkshire run A' } },
    })
    expect(layerPrimaryLine(m)).toBe('Yorkshire run A')
  })

  it('layerPrimaryLine falls back to layerDisplayName', () => {
    expect(layerPrimaryLine(baseModel())).toBe('Myotis daubentonii · In flight')
  })

  it('layerSecondaryLine is species line when title present', () => {
    const m = baseModel({ metadata: { card: { title: 'T' } } })
    expect(layerSecondaryLine(m)).toBe('Myotis daubentonii · In flight')
  })

  it('layerSecondaryLine is null when no title', () => {
    expect(layerSecondaryLine(baseModel())).toBeNull()
  })

  it('layerAutocompleteLabel includes both when title present', () => {
    const m = baseModel({ metadata: { card: { title: 'T' } } })
    expect(layerAutocompleteLabel(m)).toBe('T (Myotis daubentonii · In flight)')
  })

  it('layerAutocompleteLabel does not duplicate when title matches display name', () => {
    const full = 'Myotis daubentonii · In flight'
    const m = baseModel({ metadata: { card: { title: full } } })
    expect(layerAutocompleteLabel(m)).toBe(full)
    expect(layerSecondaryLine(m)).toBeNull()
  })
})
