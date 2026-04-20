import { describe, expect, it } from 'vitest'
import { titilerRasterUrlParam } from './cogPath'

describe('titilerRasterUrlParam', () => {
  it('passes gs:// URIs unchanged', () => {
    expect(
      titilerRasterUrlParam('gs://bucket/models/id/suitability_cog.tif'),
    ).toBe('gs://bucket/models/id/suitability_cog.tif')
  })

  it('uses file:/// for absolute local paths', () => {
    expect(titilerRasterUrlParam('/data/models/x/suitability_cog.tif')).toBe(
      'file:///data/models/x/suitability_cog.tif',
    )
  })

  it('passes https COG URLs', () => {
    expect(titilerRasterUrlParam('https://example.com/cog.tif')).toBe(
      'https://example.com/cog.tif',
    )
  })
})
