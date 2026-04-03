import { describe, expect, it } from 'vitest'

import { parseProject } from './projects'

const valid = {
  id: 'p1',
  name: 'North region',
  status: 'active' as const,
  visibility: 'public' as const,
  allowed_uids: [] as string[],
}

describe('parseProject', () => {
  it('parses minimal required fields', () => {
    const p = parseProject(valid)
    expect(p).toEqual({
      id: 'p1',
      name: 'North region',
      status: 'active',
      visibility: 'public',
      allowed_uids: [],
    })
  })

  it('parses optional description and timestamps', () => {
    const p = parseProject({
      ...valid,
      description: 'A test project',
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-06-01T12:00:00Z',
    })
    expect(p!.description).toBe('A test project')
    expect(p!.created_at).toBe('2024-01-01T00:00:00Z')
    expect(p!.updated_at).toBe('2024-06-01T12:00:00Z')
  })

  it('parses allowed_uids', () => {
    const p = parseProject({
      ...valid,
      allowed_uids: ['uid1', 'uid2'],
      visibility: 'private',
    })
    expect(p!.allowed_uids).toEqual(['uid1', 'uid2'])
    expect(p!.visibility).toBe('private')
  })

  it('parses nullable driver paths', () => {
    const p = parseProject({
      ...valid,
      driver_artifact_root: null,
      driver_cog_path: null,
    })
    expect(p!.driver_artifact_root).toBeNull()
    expect(p!.driver_cog_path).toBeNull()
  })

  it('accepts string driver paths', () => {
    const p = parseProject({
      ...valid,
      driver_cog_path: 'gs://bucket/env.tif',
    })
    expect(p!.driver_cog_path).toBe('gs://bucket/env.tif')
  })

  it('rejects invalid status', () => {
    expect(parseProject({ ...valid, status: 'draft' })).toBeNull()
  })

  it('rejects invalid visibility', () => {
    expect(parseProject({ ...valid, visibility: 'secret' })).toBeNull()
  })

  it('rejects non-string allowed_uids entry', () => {
    expect(parseProject({ ...valid, allowed_uids: [1] })).toBeNull()
  })

  it('rejects non-array allowed_uids', () => {
    expect(parseProject({ ...valid, allowed_uids: {} })).toBeNull()
  })

  it('rejects bad description type', () => {
    expect(parseProject({ ...valid, description: 1 })).toBeNull()
  })
})
