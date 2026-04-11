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

  it('parses primary metric and extras pairs', () => {
    const d = emptyModelCardDraft()
    d.title = 'T'
    d.primaryMetricType = 'AUC'
    d.primaryMetricValue = '0.9'
    d.extrasPairs = [
      { key: 'team', value: 'a' },
      { key: '', value: 'x' },
    ]
    const r = parseModelCardDraft(d)
    expect(r.ok).toBe(true)
    if (r.ok) {
      expect(r.card?.title).toBe('T')
      expect(r.card?.primary_metric_type).toBe('AUC')
      expect(r.card?.primary_metric_value).toBe('0.9')
      expect(r.extras).toEqual({ team: 'a' })
    }
  })

  it('uses custom metric label when type is Custom', () => {
    const d = emptyModelCardDraft()
    d.primaryMetricType = 'Custom'
    d.customMetricLabel = 'Brier'
    d.primaryMetricValue = '0.1'
    const r = parseModelCardDraft(d)
    expect(r.ok).toBe(true)
    if (r.ok) {
      expect(r.card?.primary_metric_type).toBe('Brier')
    }
  })
})

describe('modelToCardDraft', () => {
  it('round-trips card from model', () => {
    const m = minimalModel({
      metadata: {
        card: { title: 'X', summary: 'Y', primary_metric_type: 'AUC', primary_metric_value: '0.8' },
        extras: { k: 'v' },
      },
    })
    const d = modelToCardDraft(m)
    expect(d.title).toBe('X')
    expect(d.primaryMetricType).toBe('AUC')
    expect(d.primaryMetricValue).toBe('0.8')
    expect(d.extrasPairs.some((r) => r.key === 'k' && r.value === 'v')).toBe(true)
  })
})
