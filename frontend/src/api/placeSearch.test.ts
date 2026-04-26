import { describe, expect, it } from 'vitest'

import { parsePlaceSearchResponse, parsePlaceSearchResult } from './placeSearch'

const result = {
  id: 'municipality.123',
  label: 'Guiseley, Leeds, England, United Kingdom',
  center: { lng: -1.712, lat: 53.875 },
  bbox: [-1.75, 53.84, -1.66, 53.91],
  source: 'maptiler',
  attribution: 'MapTiler OpenStreetMap contributors',
}

describe('parsePlaceSearchResult', () => {
  it('parses a valid place result', () => {
    expect(parsePlaceSearchResult(result)).toEqual(result)
  })

  it('accepts a result without bounds', () => {
    expect(parsePlaceSearchResult({ ...result, bbox: null })?.bbox).toBeNull()
  })

  it('rejects invalid coordinates and bounds', () => {
    expect(parsePlaceSearchResult({ ...result, center: { lng: 200, lat: 53.875 } })).toBeNull()
    expect(parsePlaceSearchResult({ ...result, bbox: [-1, 2, -2, 3] })).toBeNull()
  })

  it('rejects invalid attribution', () => {
    expect(parsePlaceSearchResult({ ...result, attribution: 1 })).toBeNull()
  })
})

describe('parsePlaceSearchResponse', () => {
  it('parses a response list', () => {
    expect(parsePlaceSearchResponse({ results: [result] })).toEqual([result])
  })

  it('rejects malformed results', () => {
    expect(parsePlaceSearchResponse({ results: [{ ...result, id: 1 }] })).toBeNull()
  })
})
