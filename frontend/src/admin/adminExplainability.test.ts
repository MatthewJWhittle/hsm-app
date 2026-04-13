import { describe, expect, it } from 'vitest'

import { buildModelMetadataForSubmit, explainabilityConfiguredInCatalog } from './adminExplainability'
import type { Model } from '../types/model'

const minimalModel = (over: Partial<Model>): Model => ({
  id: 'x',
  project_id: 'p',
  species: 'S',
  activity: 'A',
  artifact_root: '/r',
  suitability_cog_path: 's.tif',
  ...over,
})

describe('explainabilityConfiguredInCatalog', () => {
  it('returns true when serialized model path and feature names are set', () => {
    const m = minimalModel({
      metadata: {
        analysis: {
          serialized_model_path: 'serialized_model.pkl',
          feature_band_names: ['a', 'b'],
        },
      },
    })
    expect(explainabilityConfiguredInCatalog(m)).toBe(true)
  })

  it('returns false when incomplete', () => {
    expect(
      explainabilityConfiguredInCatalog(
        minimalModel({
          metadata: { analysis: { feature_band_names: ['a'] } },
        }),
      ),
    ).toBe(false)
  })
})

describe('buildModelMetadataForSubmit', () => {
  it('strips analysis when disabled', () => {
    const m = buildModelMetadataForSubmit({
      base: minimalModel({
        metadata: {
          card: { title: 'T' },
          analysis: {
            serialized_model_path: 'm.pkl',
            feature_band_names: ['a', 'b'],
          },
        },
      }),
      explainEnabled: false,
      selectedBands: [],
    })
    expect(m).toEqual({ card: { title: 'T' } })
  })

  it('sets feature_band_names when enabled', () => {
    const bands = [
      { index: 0, name: 'a' },
      { index: 2, name: 'c' },
    ] as import('../types/project').EnvironmentalBandDefinition[]
    const m = buildModelMetadataForSubmit({
      base: null,
      explainEnabled: true,
      selectedBands: bands,
    })
    expect(m).toEqual({
      analysis: { feature_band_names: ['a', 'c'] },
    })
  })

  it('returns undefined when disabled and empty metadata', () => {
    expect(
      buildModelMetadataForSubmit({
        base: null,
        explainEnabled: false,
        selectedBands: [],
      }),
    ).toBeUndefined()
  })

  it('applies cardPatch over base metadata', () => {
    const m = buildModelMetadataForSubmit({
      base: minimalModel({
        metadata: {
          card: { title: 'Old' },
          analysis: { feature_band_names: ['x'], serialized_model_path: 'm.pkl' },
        },
      }),
      explainEnabled: false,
      selectedBands: [],
      cardPatch: { card: { title: 'New', summary: 'S' }, extras: null },
    })
    expect(m).toEqual({ card: { title: 'New', summary: 'S' } })
  })
})
