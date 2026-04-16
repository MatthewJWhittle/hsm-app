// @vitest-environment jsdom
import { act } from 'react'
import { createRoot } from 'react-dom/client'
import { describe, expect, it, vi } from 'vitest'

import { useDebouncedProjectAutosave } from './useAdminDebouncedAutosave'

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT =
  true

function HookHarness(props: {
  editProjName: string
  editProjFile: File | null
  persist: () => void
  baselineRef: { current: string }
  buildSnapshot: () => string
}) {
  useDebouncedProjectAutosave({
    projectEditOpen: true,
    editingProjectId: 'proj-1',
    editProjName: props.editProjName,
    editProjDesc: 'desc',
    editProjStatus: 'active',
    editProjVisibility: 'public',
    editProjAllowedUids: '',
    editProjBandDefs: [],
    baselineRef: props.baselineRef,
    buildSnapshot: props.buildSnapshot,
    persist: props.persist,
  })
  return null
}

describe('useDebouncedProjectAutosave', () => {
  it('does not schedule autosave when only pending file changes', () => {
    vi.useFakeTimers()
    const persist = vi.fn()
    const baselineRef = { current: 'same-snapshot' }
    const buildSnapshot = vi.fn(() => 'same-snapshot')

    const host = document.createElement('div')
    const root = createRoot(host)

    act(() => {
      root.render(
        <HookHarness
          editProjName="Project"
          editProjFile={null}
          persist={persist}
          baselineRef={baselineRef}
          buildSnapshot={buildSnapshot}
        />,
      )
    })

    act(() => {
      root.render(
        <HookHarness
          editProjName="Project"
          editProjFile={new File(['x'], 'env.tif', { type: 'image/tiff' })}
          persist={persist}
          baselineRef={baselineRef}
          buildSnapshot={buildSnapshot}
        />,
      )
    })

    act(() => {
      vi.runAllTimers()
    })

    expect(persist).not.toHaveBeenCalled()

    act(() => {
      root.unmount()
    })
    vi.useRealTimers()
  })
})
