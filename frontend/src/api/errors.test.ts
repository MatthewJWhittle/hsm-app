import { describe, expect, it } from 'vitest'

import { parseApiError, readFetchErrorDetail } from './errors'

describe('parseApiError', () => {
  it('returns string detail', () => {
    expect(parseApiError({ detail: 'Not found' })).toBe('Not found')
  })

  it('formats validation array items with msg', () => {
    expect(
      parseApiError({
        detail: [{ msg: 'bad' }, { msg: 'worse' }],
      }),
    ).toBe('bad; worse')
  })

  it('stringifies array items without msg', () => {
    expect(parseApiError({ detail: [1, 'x'] })).toBe('1; "x"')
  })

  it('unwraps nested detail', () => {
    expect(parseApiError({ detail: { detail: 'inner' } })).toBe('inner')
  })

  it('returns default when no detail key', () => {
    expect(parseApiError({})).toBe('Request failed')
    expect(parseApiError(null)).toBe('Request failed')
  })
})

describe('readFetchErrorDetail', () => {
  it('parses JSON body with detail', async () => {
    const r = new Response(JSON.stringify({ detail: 'Quota exceeded' }), { status: 413 })
    expect(await readFetchErrorDetail(r)).toBe('Quota exceeded')
  })

  it('falls back to statusText when JSON invalid', async () => {
    const r = new Response('not json', { status: 502, statusText: 'Bad Gateway' })
    expect(await readFetchErrorDetail(r)).toBe('Bad Gateway')
  })
})
