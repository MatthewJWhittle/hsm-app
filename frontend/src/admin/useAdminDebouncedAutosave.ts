import { useEffect, type MutableRefObject } from 'react'

import type { EnvironmentalBandDefinition } from '../types/project'

import type { ModelCardDraft } from './modelCardDraft'

/** Shared debounce interval for admin project/layer edit autosave (ms). */
export const ADMIN_AUTOSAVE_DEBOUNCE_MS = 550

/**
 * Debounced Firestore autosave while the project edit dialog is open.
 * Depends on `editingProjectId` and form fields, not the whole catalog object (see eslint comment).
 */
export function useDebouncedProjectAutosave(args: {
  projectEditOpen: boolean
  editingProjectId: string | undefined
  editProjName: string
  editProjDesc: string
  editProjStatus: 'active' | 'archived'
  editProjVisibility: 'public' | 'private'
  editProjAllowedUids: string
  editProjBandDefs: EnvironmentalBandDefinition[]
  baselineRef: MutableRefObject<string>
  buildSnapshot: () => string
  persist: () => void | Promise<void>
}): void {
  const {
    projectEditOpen,
    editingProjectId,
    editProjName,
    editProjDesc,
    editProjStatus,
    editProjVisibility,
    editProjAllowedUids,
    editProjBandDefs,
    baselineRef,
    buildSnapshot,
    persist,
  } = args

  useEffect(
    () => {
      if (!projectEditOpen || !editingProjectId) return
      if (!editProjName.trim()) return
      const snap = buildSnapshot()
      if (snap === baselineRef.current) return
      const t = window.setTimeout(() => {
        void persist()
      }, ADMIN_AUTOSAVE_DEBOUNCE_MS)
      return () => window.clearTimeout(t)
    },
    // Debounced autosave: `editingProjectId` plus form fields; omit full project object to avoid re-arming on catalog churn.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [
      projectEditOpen,
      editingProjectId,
      editProjName,
      editProjDesc,
      editProjStatus,
      editProjVisibility,
      editProjAllowedUids,
      editProjBandDefs,
      buildSnapshot,
      persist,
    ],
  )
}

/**
 * Debounced Firestore autosave while the layer (model) edit dialog is open.
 * Depends on `editModelId` and form fields, not the whole model object.
 */
export function useDebouncedLayerAutosave(args: {
  editOpen: boolean
  editModelId: string | undefined
  editSpecies: string
  editActivity: string
  editProjectId: string
  editSelectedEnvBands: EnvironmentalBandDefinition[]
  editExplainEnabled: boolean
  editFile: File | null
  editExplainModelFile: File | null
  editCardDraft: ModelCardDraft
  baselineRef: MutableRefObject<string>
  buildSnapshot: () => string
  canPersist: () => boolean
  persist: () => void | Promise<void>
}): void {
  const {
    editOpen,
    editModelId,
    editSpecies,
    editActivity,
    editProjectId,
    editSelectedEnvBands,
    editExplainEnabled,
    editFile,
    editExplainModelFile,
    editCardDraft,
    baselineRef,
    buildSnapshot,
    canPersist,
    persist,
  } = args

  useEffect(
    () => {
      if (!editOpen || !editModelId) return
      if (!canPersist()) return
      const snap = buildSnapshot()
      if (snap === baselineRef.current) return
      const t = window.setTimeout(() => {
        void persist()
      }, ADMIN_AUTOSAVE_DEBOUNCE_MS)
      return () => window.clearTimeout(t)
    },
    // Debounced autosave: `editModelId` plus form fields; omit full `editModel` for the same reason as project edit above.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [
      editOpen,
      editModelId,
      editSpecies,
      editActivity,
      editProjectId,
      editSelectedEnvBands,
      editExplainEnabled,
      editFile,
      editExplainModelFile,
      editCardDraft,
      buildSnapshot,
      canPersist,
      persist,
    ],
  )
}
