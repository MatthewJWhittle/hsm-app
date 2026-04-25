import { describe, expect, it } from 'vitest'
import { parseTitilerBounds } from './rasterBounds'

describe('parseTitilerBounds', () => {
  it('maps TiTiler WGS84 bounds to MapLibre fitBounds coordinates', () => {
    expect(
      parseTitilerBounds({
        bounds: [-2.67, 53.22, 0.3, 54.62],
        crs: 'http://www.opengis.net/def/crs/EPSG/0/4326',
      }),
    ).toEqual([
      [-2.67, 53.22],
      [0.3, 54.62],
    ])
  })

  it('rejects non-WGS84 bounds', () => {
    expect(
      parseTitilerBounds({
        bounds: [-298329.9, 7023826.8, 34407.3, 7290220.2],
        crs: 'http://www.opengis.net/def/crs/EPSG/0/3857',
      }),
    ).toBeNull()
  })

  it('rejects invalid or empty bounds', () => {
    expect(parseTitilerBounds({ bounds: [1, 2, 1, 3], crs: 'EPSG:4326' })).toBeNull()
    expect(parseTitilerBounds({ bounds: [1, 2, 3], crs: 'EPSG:4326' })).toBeNull()
    expect(parseTitilerBounds({ bounds: [1, 2, 3, Number.NaN], crs: 'EPSG:4326' })).toBeNull()
  })
})
