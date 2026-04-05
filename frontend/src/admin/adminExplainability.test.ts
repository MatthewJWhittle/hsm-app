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
  it('strips explainability path keys when disabled but keeps other driver_config keys', () => {
    const s = mergeDriverConfigForSubmit(
      {
        explainability_model_path: 'm.pkl',
        explainability_background_path: 'b.parquet',
        explainability_background_artifact_root: '/proj',
        feature_names: ['x'],
        band_labels: ['old'],
      },
      { enabled: false },
    )
    expect(JSON.parse(s)).toEqual({ feature_names: ['x'], band_labels: ['old'] })
  })

  it('passes through existing config when enabled (feature_names come from the API after save)', () => {
    const s = mergeDriverConfigForSubmit(
      { explainability_model_path: 'm.pkl', feature_names: ['a', 'b'] },
      { enabled: true },
    )
    expect(JSON.parse(s)).toEqual({ explainability_model_path: 'm.pkl', feature_names: ['a', 'b'] })
  })

  it('returns empty object when no existing config and enabled', () => {
    const s = mergeDriverConfigForSubmit(null, { enabled: true })
    expect(JSON.parse(s)).toEqual({})
  })
})
