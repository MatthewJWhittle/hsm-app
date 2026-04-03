import { describe, expect, it } from 'vitest'

import { parseModel, parseModelList } from './models'

const minimalValid = {
  id: 'm1',
  species: 'Myotis daubentonii',
  activity: 'foraging',
  artifact_root: 'gs://bucket/models/m1',
  suitability_cog_path: 'gs://bucket/models/m1/suitability_cog.tif',
}

describe('parseModel', () => {
  it('parses minimal valid payload', () => {
    const m = parseModel(minimalValid)
    expect(m).not.toBeNull()
    expect(m!.id).toBe('m1')
    expect(m!.species).toBe('Myotis daubentonii')
    expect(m!.project_id).toBeUndefined()
  })

  it('accepts null project_id', () => {
    const m = parseModel({ ...minimalValid, project_id: null })
    expect(m).not.toBeNull()
    expect(m!.project_id).toBeNull()
  })

  it('accepts string project_id', () => {
    const m = parseModel({ ...minimalValid, project_id: 'proj-uuid' })
    expect(m!.project_id).toBe('proj-uuid')
  })

  it('rejects invalid project_id type', () => {
    expect(parseModel({ ...minimalValid, project_id: 123 })).toBeNull()
  })

  it('parses driver_band_indices and driver_config', () => {
    const m = parseModel({
      ...minimalValid,
      driver_band_indices: [1, 2, 3],
      driver_config: { bands: { forest: 0 } },
    })
    expect(m!.driver_band_indices).toEqual([1, 2, 3])
    expect(m!.driver_config).toEqual({ bands: { forest: 0 } })
  })

  it('accepts null driver_band_indices', () => {
    const m = parseModel({ ...minimalValid, driver_band_indices: null })
    expect(m!.driver_band_indices).toBeNull()
  })

  it('rejects non-integer driver_band_indices arrays', () => {
    expect(
      parseModel({ ...minimalValid, driver_band_indices: [1, 'x'] as unknown as number[] }),
    ).toBeNull()
  })

  it('rejects non-record driver_config', () => {
    expect(parseModel({ ...minimalValid, driver_config: 'x' })).toBeNull()
  })

  it('parses model_name and model_version', () => {
    const m = parseModel({
      ...minimalValid,
      model_name: 'v1',
      model_version: '2024-01',
    })
    expect(m!.model_name).toBe('v1')
    expect(m!.model_version).toBe('2024-01')
  })

  it('rejects missing required string fields', () => {
    expect(parseModel({ ...minimalValid, id: 1 })).toBeNull()
    expect(parseModel({ ...minimalValid, species: null })).toBeNull()
  })

  it('rejects non-object', () => {
    expect(parseModel(null)).toBeNull()
    expect(parseModel([])).toBeNull()
  })
})

describe('parseModelList', () => {
  it('parses array of valid models', () => {
    const list = parseModelList([minimalValid, { ...minimalValid, id: 'm2' }])
    expect(list).not.toBeNull()
    expect(list!.length).toBe(2)
  })

  it('returns null if any item invalid', () => {
    expect(parseModelList([minimalValid, { ...minimalValid, id: null }])).toBeNull()
  })

  it('returns null for non-array', () => {
    expect(parseModelList({})).toBeNull()
  })
})
