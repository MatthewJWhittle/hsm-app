import { describe, expect, it } from 'vitest'

import { parsePointInspection } from './pointInspection'

describe('parsePointInspection', () => {
  it('parses minimal value', () => {
    const p = parsePointInspection({ value: 0.42 })
    expect(p).toEqual({ value: 0.42 })
  })

  it('parses unit string', () => {
    const p = parsePointInspection({ value: 1, unit: 'index' })
    expect(p).toEqual({ value: 1, unit: 'index' })
  })

  it('treats null unit as null', () => {
    const p = parsePointInspection({ value: 1, unit: null })
    expect(p!.unit).toBeNull()
  })

  it('parses drivers array', () => {
    const p = parsePointInspection({
      value: 0.5,
      drivers: [
        { name: 'forest', direction: 'increase', label: 'Tree cover', magnitude: 0.2 },
        { name: 'water', direction: 'decrease' },
      ],
    })
    expect(p!.drivers).toHaveLength(2)
    expect(p!.drivers![0].name).toBe('forest')
    expect(p!.drivers![1].magnitude).toBeUndefined()
  })

  it('rejects NaN value', () => {
    expect(parsePointInspection({ value: NaN })).toBeNull()
  })

  it('rejects non-finite value', () => {
    expect(parsePointInspection({ value: Infinity })).toBeNull()
  })

  it('rejects invalid unit type', () => {
    expect(parsePointInspection({ value: 1, unit: 2 })).toBeNull()
  })

  it('rejects non-array drivers', () => {
    expect(parsePointInspection({ value: 1, drivers: {} })).toBeNull()
  })

  it('rejects driver with bad direction', () => {
    expect(
      parsePointInspection({
        value: 1,
        drivers: [{ name: 'x', direction: 'sideways' }],
      }),
    ).toBeNull()
  })

  it('rejects driver with non-finite magnitude', () => {
    expect(
      parsePointInspection({
        value: 1,
        drivers: [{ name: 'x', direction: 'neutral', magnitude: NaN }],
      }),
    ).toBeNull()
  })

  it('rejects non-object', () => {
    expect(parsePointInspection(null)).toBeNull()
    expect(parsePointInspection('x')).toBeNull()
  })

  it('parses raw_environmental_values', () => {
    const p = parsePointInspection({
      value: 0.5,
      drivers: [],
      raw_environmental_values: [
        { name: 'elev', value: 120.5, unit: 'm' },
        { name: 'forest', value: 0.3 },
      ],
    })
    expect(p!.raw_environmental_values).toHaveLength(2)
    expect(p!.raw_environmental_values![0].name).toBe('elev')
    expect(p!.raw_environmental_values![0].value).toBe(120.5)
    expect(p!.raw_environmental_values![0].unit).toBe('m')
  })
})
