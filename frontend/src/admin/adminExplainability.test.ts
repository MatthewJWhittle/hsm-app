import { describe, expect, it } from 'vitest'

import { explainabilityConfiguredInCatalog, mergeDriverConfigForSubmit } from './adminExplainability'
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
  it('returns true when model, background, and feature_names are set', () => {
    const m = minimalModel({
      driver_config: {
        explainability_model_path: 'explainability_model.pkl',
        explainability_background_path: 'explainability_background.parquet',
        feature_names: ['a', 'b'],
      },
    })
    expect(explainabilityConfiguredInCatalog(m)).toBe(true)
  })

  it('returns false when incomplete', () => {
    expect(
      explainabilityConfiguredInCatalog(
        minimalModel({ driver_config: { feature_names: ['a'] } }),
      ),
    ).toBe(false)
  })
})

describe('mergeDriverConfigForSubmit', () => {
  it('strips explainability keys when disabled but keeps band labels from the form', () => {
    const s = mergeDriverConfigForSubmit(
      {
        explainability_model_path: 'm.pkl',
        feature_names: ['x'],
        band_labels: ['old'],
      },
      { enabled: false, featureNamesCsv: '', bandLabelsCsv: 'L' },
    )
    expect(JSON.parse(s)).toEqual({ band_labels: ['L'] })
  })

  it('sets feature_names when enabled', () => {
    const s = mergeDriverConfigForSubmit(null, {
      enabled: true,
      featureNamesCsv: 'a, b',
      bandLabelsCsv: '',
    })
    expect(JSON.parse(s)).toEqual({ feature_names: ['a', 'b'] })
  })
})
