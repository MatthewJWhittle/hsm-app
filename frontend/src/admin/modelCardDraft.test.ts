import { describe, expect, it } from 'vitest'

import { emptyModelCardDraft, modelToCardDraft, parseModelCardDraft } from './modelCardDraft'
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

describe('parseModelCardDraft', () => {
  it('accepts empty draft', () => {
    const r = parseModelCardDraft(emptyModelCardDraft())
    expect(r.ok).toBe(true)
    if (r.ok) {
      expect(r.card).toBeNull()
      expect(r.extras).toBeNull()
    }
  })

  it('parses metrics and extras JSON', () => {
    const d = emptyModelCardDraft()
    d.title = 'T'
    d.metricsJson = '{"auc": 0.9}'
    d.extrasJson = '{"team": "a"}'
    const r = parseModelCardDraft(d)
    expect(r.ok).toBe(true)
    if (r.ok) {
      expect(r.card?.title).toBe('T')
      expect(r.card?.metrics).toEqual({ auc: 0.9 })
      expect(r.extras).toEqual({ team: 'a' })
    }
  })

  it('rejects invalid metrics JSON', () => {
    const d = emptyModelCardDraft()
    d.metricsJson = '['
    expect(parseModelCardDraft(d).ok).toBe(false)
  })
})

describe('modelToCardDraft', () => {
  it('round-trips card from model', () => {
    const m = minimalModel({
      metadata: {
        card: { title: 'X', summary: 'Y' },
        extras: { k: 'v' },
      },
    })
    const d = modelToCardDraft(m)
    expect(d.title).toBe('X')
    expect(d.summary).toBe('Y')
    expect(d.extrasJson).toContain('k')
  })
})
