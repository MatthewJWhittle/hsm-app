import { Alert, Box, Container, LinearProgress, Paper, Tab, Tabs, Typography } from '@mui/material'
import FolderOutlinedIcon from '@mui/icons-material/FolderOutlined'
import LayersOutlinedIcon from '@mui/icons-material/LayersOutlined'
import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'

import '../App.css'

import { createModel, updateModel } from '../api/adminModels'
import {
  completeUploadSession,
  createProject,
  initUploadSession,
  patchProjectEnvironmentalBandDefinitions,
  postRegenerateExplainabilityBackgroundSample,
  uploadFileToSignedUrl,
  updateProject,
} from '../api/adminProjects'
import { fetchModelCatalog } from '../api/catalog'
import { fetchProjectCatalog } from '../api/projects'
import { useAuth } from '../auth/useAuth'
import { Navbar } from '../components/Navbar'
import { type Model, getFeatureBandNames } from '../types/model'
import type { CatalogProject, EnvironmentalBandDefinition } from '../types/project'

import { bandsFromFeatureNames, environmentalBandsForProject } from './adminBandSelect'
import { buildModelMetadataForSubmit, explainabilityConfiguredInCatalog } from './adminExplainability'
import { emptyModelCardDraft, modelToCardDraft, parseModelCardDraft, type ModelCardDraft } from './modelCardDraft'
import { AdminCatalogHeader } from './AdminCatalogHeader'
import { AdminTabPanel } from './AdminTabPanel'
import { LayerCreateDialog } from './LayerCreateDialog'
import { LayerEditDialog } from './LayerEditDialog'
import { LayersCatalogTab } from './LayersCatalogTab'
import { ProjectCreateDialog } from './ProjectCreateDialog'
import { ProjectEditDialog } from './ProjectEditDialog'
import { ProjectsCatalogTab } from './ProjectsCatalogTab'
import { layerFormSnapshot, projectFormSnapshot } from './adminEditSnapshots'
import { useDebouncedLayerAutosave, useDebouncedProjectAutosave } from './useAdminDebouncedAutosave'

const FORM_MAX_WIDTH = 640

export function AdminPage() {
  const { user, loading, isAdmin, getIdToken } = useAuth()
  const [tab, setTab] = useState(0)
  const [projects, setProjects] = useState<CatalogProject[]>([])
  const [models, setModels] = useState<Model[]>([])
  const [listError, setListError] = useState<string | null>(null)
  const [listRefreshing, setListRefreshing] = useState(true)
  const [lastRefreshedAt, setLastRefreshedAt] = useState<Date | null>(null)
  const [projectTableFilter, setProjectTableFilter] = useState('')
  const [modelTableFilter, setModelTableFilter] = useState('')
  const [selectedModelIds, setSelectedModelIds] = useState<string[]>([])
  const [bulkAssignProjectId, setBulkAssignProjectId] = useState('')
  const [bulkAssigning, setBulkAssigning] = useState(false)
  const [bulkAssignError, setBulkAssignError] = useState<string | null>(null)

  const [projName, setProjName] = useState('')
  const [projDesc, setProjDesc] = useState('')
  const [projVisibility, setProjVisibility] = useState<'public' | 'private'>('public')
  const [projAllowedUids, setProjAllowedUids] = useState('')
  const [projFile, setProjFile] = useState<File | null>(null)
  const [projError, setProjError] = useState<string | null>(null)
  const [projUploadStatus, setProjUploadStatus] = useState<string | null>(null)
  const [projCreating, setProjCreating] = useState(false)
  const [projectCreateOpen, setProjectCreateOpen] = useState(false)

  const [modelProjectId, setModelProjectId] = useState('')
  const [species, setSpecies] = useState('')
  const [activity, setActivity] = useState('')
  const [selectedEnvBands, setSelectedEnvBands] = useState<EnvironmentalBandDefinition[]>([])
  const [explainEnabled, setExplainEnabled] = useState(false)
  const [explainModelFile, setExplainModelFile] = useState<File | null>(null)
  const [file, setFile] = useState<File | null>(null)
  const [createError, setCreateError] = useState<string | null>(null)
  const [layerUploadStatus, setLayerUploadStatus] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)
  const [layerCreateOpen, setLayerCreateOpen] = useState(false)
  const [createCardDraft, setCreateCardDraft] = useState<ModelCardDraft>(() => emptyModelCardDraft())

  const [editOpen, setEditOpen] = useState(false)
  const [editModel, setEditModel] = useState<Model | null>(null)
  const [editSpecies, setEditSpecies] = useState('')
  const [editActivity, setEditActivity] = useState('')
  const [editProjectId, setEditProjectId] = useState('')
  const [editFile, setEditFile] = useState<File | null>(null)
  const [editSelectedEnvBands, setEditSelectedEnvBands] = useState<EnvironmentalBandDefinition[]>([])
  const [editExplainEnabled, setEditExplainEnabled] = useState(false)
  const [editExplainModelFile, setEditExplainModelFile] = useState<File | null>(null)
  const [editCardDraft, setEditCardDraft] = useState<ModelCardDraft>(() => emptyModelCardDraft())
  const [editError, setEditError] = useState<string | null>(null)
  const [savingEdit, setSavingEdit] = useState(false)

  const [projectEditOpen, setProjectEditOpen] = useState(false)
  const [editingProject, setEditingProject] = useState<CatalogProject | null>(null)
  const [editProjName, setEditProjName] = useState('')
  const [editProjDesc, setEditProjDesc] = useState('')
  const [editProjVisibility, setEditProjVisibility] = useState<'public' | 'private'>('public')
  const [editProjAllowedUids, setEditProjAllowedUids] = useState('')
  const [editProjStatus, setEditProjStatus] = useState<'active' | 'archived'>('active')
  const [editProjFile, setEditProjFile] = useState<File | null>(null)
  const [editProjBandDefs, setEditProjBandDefs] = useState<EnvironmentalBandDefinition[]>([])
  const [editProjError, setEditProjError] = useState<string | null>(null)
  const [editProjUploadStatus, setEditProjUploadStatus] = useState<string | null>(null)
  const [savingProjectEdit, setSavingProjectEdit] = useState(false)
  const [regenerateExplainBgRows, setRegenerateExplainBgRows] = useState(256)
  const [regeneratingExplainBg, setRegeneratingExplainBg] = useState(false)
  const [regenerateExplainBgError, setRegenerateExplainBgError] = useState<string | null>(null)

  const projectEditBaselineRef = useRef<string>('')
  const layerEditBaselineRef = useRef<string>('')
  const [projectEditSession, setProjectEditSession] = useState(0)
  const [layerEditSession, setLayerEditSession] = useState(0)

  const projectById = useMemo(() => {
    const m = new Map<string, string>()
    for (const p of projects) {
      m.set(p.id, p.name)
    }
    return m
  }, [projects])

  const filteredProjectsTable = useMemo(() => {
    const q = projectTableFilter.trim().toLowerCase()
    if (!q) return projects
    return projects.filter(
      (p) =>
        p.name.toLowerCase().includes(q) ||
        p.id.toLowerCase().includes(q) ||
        (p.description?.toLowerCase().includes(q) ?? false),
    )
  }, [projects, projectTableFilter])

  const filteredModelsTable = useMemo(() => {
    const q = modelTableFilter.trim().toLowerCase()
    if (!q) return models
    return models.filter((m) => {
      const hay = `${m.species} ${m.activity} ${m.id} ${m.project_id ?? ''} ${m.metadata?.card?.title ?? ''} ${m.metadata?.card?.version ?? ''}`.toLowerCase()
      return hay.includes(q)
    })
  }, [models, modelTableFilter])

  const filteredModelIds = useMemo(() => filteredModelsTable.map((m) => m.id), [filteredModelsTable])

  const createLayerEnvOptions = useMemo(
    () => environmentalBandsForProject(modelProjectId, projects),
    [modelProjectId, projects],
  )
  const editLayerEnvOptions = useMemo(
    () => environmentalBandsForProject(editProjectId, projects),
    [editProjectId, projects],
  )

  const buildProjectEditSnapshot = useCallback(() => {
    return projectFormSnapshot({
      name: editProjName,
      description: editProjDesc,
      status: editProjStatus,
      visibility: editProjVisibility,
      allowedUids: editProjAllowedUids,
      bandDefs: editProjBandDefs,
      pendingFileName: editProjFile?.name ?? null,
    })
  }, [
    editProjName,
    editProjDesc,
    editProjStatus,
    editProjVisibility,
    editProjAllowedUids,
    editProjBandDefs,
    editProjFile,
  ])

  const buildLayerEditSnapshot = useCallback(() => {
    if (!editModel) return ''
    const parsed = parseModelCardDraft(editCardDraft)
    const metaForSnap =
      parsed.ok
        ? buildModelMetadataForSubmit({
            base: editModel,
            explainEnabled: editExplainEnabled,
            selectedBands: editSelectedEnvBands,
            cardPatch: { card: parsed.card, extras: parsed.extras },
          })
        : undefined
    const metadataJson = metaForSnap ? JSON.stringify(metaForSnap) : ''
    return layerFormSnapshot({
      species: editSpecies,
      activity: editActivity,
      projectId: editProjectId,
      bandDefs: editSelectedEnvBands,
      explainEnabled: editExplainEnabled,
      metadataJson,
      cardDraftJson: JSON.stringify(editCardDraft),
      suitabilityFileName: editFile?.name ?? null,
      explainModelFileName: editExplainModelFile?.name ?? null,
    })
  }, [
    editModel,
    editSpecies,
    editActivity,
    editProjectId,
    editSelectedEnvBands,
    editExplainEnabled,
    editFile,
    editExplainModelFile,
    editCardDraft,
  ])

  useLayoutEffect(() => {
    if (!projectEditOpen || !editingProject) return
    projectEditBaselineRef.current = buildProjectEditSnapshot()
    // eslint-disable-next-line react-hooks/exhaustive-deps -- baseline only when dialog opens / session bumps
  }, [projectEditOpen, editingProject?.id, projectEditSession])

  useLayoutEffect(() => {
    if (!editOpen || !editModel) return
    layerEditBaselineRef.current = buildLayerEditSnapshot()
    // eslint-disable-next-line react-hooks/exhaustive-deps -- baseline only when dialog opens / session bumps
  }, [editOpen, editModel?.id, layerEditSession])

  const canPersistLayerEdit = useCallback(() => {
    if (!parseModelCardDraft(editCardDraft).ok) return false
    if (!editSpecies.trim() || !editActivity.trim()) return false
    if (editExplainEnabled) {
      if (editSelectedEnvBands.length === 0) return false
      const hadArtifacts = editModel ? explainabilityConfiguredInCatalog(editModel) : false
      if (!hadArtifacts && !editExplainModelFile) return false
    }
    return true
  }, [
    editCardDraft,
    editSpecies,
    editActivity,
    editExplainEnabled,
    editSelectedEnvBands,
    editExplainModelFile,
    editModel,
  ])

  const uploadViaSession = useCallback(
    async (args: {
      token: string
      file: File
      projectId?: string
      setStatus: (value: string) => void
      uploadingMessage: string
      finalizingMessage: string
    }): Promise<string> => {
      const init = await initUploadSession({
        token: args.token,
        filename: args.file.name,
        contentType: args.file.type || 'image/tiff',
        sizeBytes: args.file.size,
        projectId: args.projectId,
      })
      if (!init.upload_url) {
        throw new Error('Upload session did not provide an upload URL.')
      }
      args.setStatus(args.uploadingMessage)
      await uploadFileToSignedUrl({ uploadUrl: init.upload_url, file: args.file })
      args.setStatus(args.finalizingMessage)
      await completeUploadSession({
        token: args.token,
        uploadId: init.id,
        sizeBytes: args.file.size,
      })
      return init.id
    },
    [],
  )

  const persistProjectEdit = useCallback(async () => {
    if (!editingProject || savingProjectEdit) return
    if (!editProjName.trim()) return
    const snap = buildProjectEditSnapshot()
    if (snap === projectEditBaselineRef.current) return

    setEditProjError(null)
    const token = await getIdToken(false)
    if (!token) {
      setEditProjError('Not signed in.')
      return
    }
    setSavingProjectEdit(true)
    try {
      let uploadSessionId: string | undefined = undefined
      if (editProjFile) {
        setEditProjUploadStatus('Preparing environmental upload…')
        uploadSessionId = await uploadViaSession({
          token,
          file: editProjFile,
          projectId: editingProject.id,
          setStatus: (v) => setEditProjUploadStatus(v),
          uploadingMessage: 'Uploading environmental file…',
          finalizingMessage: 'Finalizing environmental upload…',
        })
      }
      setEditProjUploadStatus('Saving project…')
      const updated = await updateProject({
        token,
        projectId: editingProject.id,
        name: editProjName.trim(),
        description: editProjDesc.trim() || null,
        status: editProjStatus,
        visibility: editProjVisibility,
        allowedUids: editProjAllowedUids,
        uploadSessionId,
      })
      let merged = updated
      if (!editProjFile && updated.driver_cog_path && editProjBandDefs.length > 0) {
        merged = await patchProjectEnvironmentalBandDefinitions({
          token,
          projectId: editingProject.id,
          definitions: editProjBandDefs,
        })
      }
      const nextBands = merged.environmental_band_definitions
        ? [...merged.environmental_band_definitions].sort((a, b) => a.index - b.index)
        : editProjBandDefs
      setEditingProject(merged)
      setEditProjBandDefs(nextBands)
      setEditProjFile(null)
      setProjects((prev) => {
        const i = prev.findIndex((p) => p.id === merged.id)
        if (i < 0) return [...prev, merged]
        const next = [...prev]
        next[i] = merged
        return next
      })
      setListError(null)
      setLastRefreshedAt(new Date())
      projectEditBaselineRef.current = projectFormSnapshot({
        name: editProjName,
        description: editProjDesc,
        status: editProjStatus,
        visibility: editProjVisibility,
        allowedUids: editProjAllowedUids,
        bandDefs: nextBands,
        pendingFileName: null,
      })
    } catch (err) {
      setEditProjError(err instanceof Error ? err.message : 'Update failed')
    } finally {
      setEditProjUploadStatus(null)
      setSavingProjectEdit(false)
    }
  }, [
    editingProject,
    savingProjectEdit,
    editProjName,
    editProjDesc,
    editProjStatus,
    editProjVisibility,
    editProjAllowedUids,
    editProjBandDefs,
    editProjFile,
    buildProjectEditSnapshot,
    getIdToken,
    uploadViaSession,
  ])

  const persistLayerEdit = useCallback(async () => {
    if (!editModel || savingEdit) return
    if (!canPersistLayerEdit()) return
    const snap = buildLayerEditSnapshot()
    if (snap === layerEditBaselineRef.current) return

    setEditError(null)
    const token = await getIdToken(false)
    if (!token) {
      setEditError('Not signed in.')
      return
    }

    const parsedCard = parseModelCardDraft(editCardDraft)
    if (!parsedCard.ok) {
      setEditError(parsedCard.message)
      return
    }
    const metadata =
      buildModelMetadataForSubmit({
        base: editModel,
        explainEnabled: editExplainEnabled,
        selectedBands: editSelectedEnvBands,
        cardPatch: { card: parsedCard.card, extras: parsedCard.extras },
      }) ?? {}

    setSavingEdit(true)
    try {
      const updated = await updateModel({
        token,
        modelId: editModel.id,
        species: editSpecies,
        activity: editActivity,
        file: editFile ?? undefined,
        projectId: editProjectId || undefined,
        metadata,
        serializedModelFile: editExplainModelFile ?? undefined,
      })
      setEditModel(updated)
      setEditCardDraft(modelToCardDraft(updated))
      setEditFile(null)
      setEditExplainModelFile(null)
      setModels((prev) => {
        const i = prev.findIndex((m) => m.id === updated.id)
        if (i < 0) return [...prev, updated]
        const next = [...prev]
        next[i] = updated
        return next
      })
      setListError(null)
      setLastRefreshedAt(new Date())
      const parsedAfter = parseModelCardDraft(editCardDraft)
      layerEditBaselineRef.current = layerFormSnapshot({
        species: editSpecies,
        activity: editActivity,
        projectId: editProjectId,
        bandDefs: editSelectedEnvBands,
        explainEnabled: editExplainEnabled,
        metadataJson:
          parsedAfter.ok
            ? JSON.stringify(
                buildModelMetadataForSubmit({
                  base: updated,
                  explainEnabled: editExplainEnabled,
                  selectedBands: editSelectedEnvBands,
                  cardPatch: { card: parsedAfter.card, extras: parsedAfter.extras },
                }) ?? {},
              )
            : '',
        cardDraftJson: JSON.stringify(editCardDraft),
        suitabilityFileName: null,
        explainModelFileName: null,
      })
    } catch (err) {
      setEditError(err instanceof Error ? err.message : 'Update failed')
    } finally {
      setSavingEdit(false)
    }
  }, [
    editModel,
    savingEdit,
    canPersistLayerEdit,
    buildLayerEditSnapshot,
    editSpecies,
    editActivity,
    editProjectId,
    editSelectedEnvBands,
    editExplainEnabled,
    editFile,
    editExplainModelFile,
    editCardDraft,
    getIdToken,
  ])

  const handleEditProjectIdChange = useCallback(
    (id: string) => {
      setEditProjectId(id)
      if (editModel) {
        const defs = id ? environmentalBandsForProject(id, projects) : null
        setEditSelectedEnvBands(bandsFromFeatureNames(getFeatureBandNames(editModel) ?? undefined, defs))
      }
    },
    [editModel, projects],
  )

  const openLayerCreateDialog = useCallback(() => {
    setLayerCreateOpen(true)
    setCreateCardDraft(emptyModelCardDraft())
    setSelectedEnvBands([])
    setExplainEnabled(false)
    setExplainModelFile(null)
    setModelProjectId((prev) => {
      if (prev) return prev
      const first = projects.find((p) => p.status === 'active')
      return first?.id ?? ''
    })
  }, [projects])

  useEffect(() => {
    if (!layerCreateOpen) return
    setSelectedEnvBands([])
    setExplainEnabled(false)
    setExplainModelFile(null)
  }, [modelProjectId, layerCreateOpen])

  const refreshList = useCallback(async () => {
    setListRefreshing(true)
    const token = await getIdToken(true)
    if (!token) {
      setListRefreshing(false)
      return
    }
    try {
      const [plist, mlist] = await Promise.all([
        fetchProjectCatalog({ token }),
        fetchModelCatalog({ token }),
      ])
      setProjects(plist)
      setModels(mlist)
      setListError(null)
      setLastRefreshedAt(new Date())
    } catch {
      setListError('Couldn’t load projects and layers. Check your connection and try again.')
    } finally {
      setListRefreshing(false)
    }
  }, [getIdToken])

  useEffect(() => {
    refreshList()
  }, [refreshList])

  useEffect(() => {
    if (!layerCreateOpen || modelProjectId) return
    const first = projects.find((p) => p.status === 'active')
    if (first) setModelProjectId(first.id)
  }, [layerCreateOpen, modelProjectId, projects])

  useEffect(() => {
    if (selectedModelIds.length === 0) {
      setBulkAssignProjectId('')
      return
    }
    setBulkAssignProjectId((prev) => {
      if (prev) return prev
      const first = projects.find((p) => p.status === 'active')
      return first?.id ?? ''
    })
  }, [selectedModelIds.length, projects])

  useEffect(() => {
    if (tab !== 1) {
      setSelectedModelIds([])
      setBulkAssignError(null)
    }
  }, [tab])

  const toggleModelSelected = useCallback((id: string) => {
    setSelectedModelIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]))
  }, [])

  const toggleSelectAllFiltered = useCallback(() => {
    setSelectedModelIds((prev) => {
      const allOn =
        filteredModelIds.length > 0 && filteredModelIds.every((fid) => prev.includes(fid))
      if (allOn) {
        return prev.filter((id) => !filteredModelIds.includes(id))
      }
      return [...new Set([...prev, ...filteredModelIds])]
    })
  }, [filteredModelIds])

  const allFilteredSelected = useMemo(
    () =>
      filteredModelIds.length > 0 && filteredModelIds.every((id) => selectedModelIds.includes(id)),
    [filteredModelIds, selectedModelIds],
  )
  const someFilteredSelected = useMemo(
    () => filteredModelIds.some((id) => selectedModelIds.includes(id)),
    [filteredModelIds, selectedModelIds],
  )

  const handleBulkAssignToProject = async () => {
    if (selectedModelIds.length === 0 || !bulkAssignProjectId) return
    setBulkAssignError(null)
    const token = await getIdToken(true)
    if (!token) {
      setBulkAssignError('Not signed in.')
      return
    }
    setBulkAssigning(true)
    try {
      const want = new Set(selectedModelIds)
      const toUpdate = models.filter((m) => want.has(m.id))
      for (const m of toUpdate) {
        await updateModel({
          token,
          modelId: m.id,
          species: m.species,
          activity: m.activity,
          projectId: bulkAssignProjectId,
        })
      }
      setSelectedModelIds([])
      await refreshList()
    } catch (err) {
      setBulkAssignError(err instanceof Error ? err.message : 'Assign failed')
    } finally {
      setBulkAssigning(false)
    }
  }

  const openEdit = (m: Model) => {
    setEditModel(m)
    setEditCardDraft(modelToCardDraft(m))
    setEditSpecies(m.species)
    setEditActivity(m.activity)
    setEditProjectId(m.project_id ?? '')
    const defs = m.project_id ? environmentalBandsForProject(m.project_id, projects) : null
    setEditSelectedEnvBands(bandsFromFeatureNames(getFeatureBandNames(m) ?? undefined, defs))
    setEditExplainEnabled(explainabilityConfiguredInCatalog(m))
    setEditExplainModelFile(null)
    setEditFile(null)
    setEditError(null)
    setLayerEditSession((s) => s + 1)
    setEditOpen(true)
  }

  const openProjectEdit = (p: CatalogProject) => {
    setEditingProject(p)
    setEditProjName(p.name)
    setEditProjDesc(p.description ?? '')
    setEditProjVisibility(p.visibility)
    setEditProjAllowedUids(p.allowed_uids?.length ? p.allowed_uids.join(', ') : '')
    setEditProjStatus(p.status)
    setEditProjFile(null)
    setEditProjBandDefs(
      p.environmental_band_definitions
        ? [...p.environmental_band_definitions].sort((a, b) => a.index - b.index)
        : [],
    )
    setEditProjError(null)
    setEditProjUploadStatus(null)
    setRegenerateExplainBgRows(256)
    setRegenerateExplainBgError(null)
    setProjectEditSession((s) => s + 1)
    setProjectEditOpen(true)
  }

  const handleRegenerateExplainabilityBackground = async () => {
    if (!editingProject) return
    setRegenerateExplainBgError(null)
    setRegeneratingExplainBg(true)
    try {
      const token = await getIdToken(false)
      if (!token) {
        setRegenerateExplainBgError('Not signed in.')
        return
      }
      const rows = Math.min(50_000, Math.max(8, Math.round(regenerateExplainBgRows)))
      const updated = await postRegenerateExplainabilityBackgroundSample({
        token,
        projectId: editingProject.id,
        sampleRows: rows,
      })
      const nextBands = updated.environmental_band_definitions
        ? [...updated.environmental_band_definitions].sort((a, b) => a.index - b.index)
        : []
      setEditingProject(updated)
      setEditProjBandDefs(nextBands)
      setProjects((prev) => {
        const i = prev.findIndex((p) => p.id === updated.id)
        if (i < 0) return [...prev, updated]
        const next = [...prev]
        next[i] = updated
        return next
      })
      setListError(null)
      setLastRefreshedAt(new Date())
      projectEditBaselineRef.current = projectFormSnapshot({
        name: editProjName,
        description: editProjDesc,
        status: editProjStatus,
        visibility: editProjVisibility,
        allowedUids: editProjAllowedUids,
        bandDefs: nextBands,
        pendingFileName: null,
      })
    } catch (err) {
      setRegenerateExplainBgError(err instanceof Error ? err.message : 'Regenerate failed')
    } finally {
      setRegeneratingExplainBg(false)
    }
  }

  useDebouncedProjectAutosave({
    projectEditOpen,
    editingProjectId: editingProject?.id,
    editProjName,
    editProjDesc,
    editProjStatus,
    editProjVisibility,
    editProjAllowedUids,
    editProjBandDefs,
    editProjFile,
    baselineRef: projectEditBaselineRef,
    buildSnapshot: buildProjectEditSnapshot,
    persist: persistProjectEdit,
  })

  useDebouncedLayerAutosave({
    editOpen,
    editModelId: editModel?.id,
    editSpecies,
    editActivity,
    editProjectId,
    editSelectedEnvBands,
    editExplainEnabled,
    editFile,
    editExplainModelFile,
    editCardDraft,
    baselineRef: layerEditBaselineRef,
    buildSnapshot: buildLayerEditSnapshot,
    canPersist: canPersistLayerEdit,
    persist: persistLayerEdit,
  })

  const handleCloseProjectEdit = useCallback(async () => {
    if (projectEditOpen && editingProject) {
      const snap = buildProjectEditSnapshot()
      if (snap !== projectEditBaselineRef.current) {
        if (!editProjName.trim()) {
          setEditProjError('Project name is required.')
          return
        }
        await persistProjectEdit()
      }
    }
    setProjectEditOpen(false)
    setEditingProject(null)
    setRegenerateExplainBgError(null)
    setEditProjUploadStatus(null)
  }, [projectEditOpen, editingProject, editProjName, buildProjectEditSnapshot, persistProjectEdit])

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault()
    setProjError(null)
    if (!projName.trim()) {
      setProjError('Project name is required.')
      return
    }
    const token = await getIdToken(true)
    if (!token) {
      setProjError('Not signed in.')
      return
    }
    setProjCreating(true)
    try {
      let uploadSessionId: string | undefined = undefined
      if (projFile) {
        setProjUploadStatus('Preparing upload…')
        uploadSessionId = await uploadViaSession({
          token,
          file: projFile,
          setStatus: (v) => setProjUploadStatus(v),
          uploadingMessage: 'Uploading environmental file…',
          finalizingMessage: 'Finalizing upload…',
        })
      }
      setProjUploadStatus('Creating project…')
      await createProject({
        token,
        name: projName,
        uploadSessionId,
        description: projDesc || undefined,
        visibility: projVisibility,
        allowedUids: projAllowedUids || undefined,
      })
      setProjName('')
      setProjDesc('')
      setProjVisibility('public')
      setProjAllowedUids('')
      setProjFile(null)
      setProjUploadStatus(null)
      setProjectCreateOpen(false)
      await refreshList()
    } catch (err) {
      setProjError(err instanceof Error ? err.message : 'Create project failed')
    } finally {
      setProjUploadStatus(null)
      setProjCreating(false)
    }
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setCreateError(null)
    if (!modelProjectId) {
      setCreateError('Select a project.')
      return
    }
    if (!file) {
      setCreateError('Choose a suitability map file.')
      return
    }
    const token = await getIdToken(true)
    if (!token) {
      setCreateError('Not signed in.')
      return
    }

    const parsedCard = parseModelCardDraft(createCardDraft)
    if (!parsedCard.ok) {
      setCreateError(parsedCard.message)
      return
    }
    const metadata =
      buildModelMetadataForSubmit({
        base: null,
        explainEnabled,
        selectedBands: selectedEnvBands,
        cardPatch: { card: parsedCard.card, extras: parsedCard.extras },
      }) ?? {}

    if (explainEnabled) {
      if (selectedEnvBands.length === 0) {
        setCreateError(
          'Variable influence: open “Upload model for variable influence”, select features, and add a .pkl.',
        )
        return
      }
      if (!explainModelFile) {
        setCreateError(
          'Variable influence requires a trained model (.pkl). Use the upload dialog to choose one.',
        )
        return
      }
    }

    setCreating(true)
    try {
      setLayerUploadStatus('Preparing upload…')
      const uploadSessionId = await uploadViaSession({
        token,
        file,
        projectId: modelProjectId,
        setStatus: (v) => setLayerUploadStatus(v),
        uploadingMessage: 'Uploading suitability file…',
        finalizingMessage: 'Finalizing upload…',
      })
      setLayerUploadStatus('Creating layer…')
      await createModel({
        token,
        projectId: modelProjectId,
        species,
        activity,
        file,
        uploadSessionId,
        metadata,
        serializedModelFile: explainEnabled ? explainModelFile : undefined,
      })
      setSpecies('')
      setActivity('')
      setSelectedEnvBands([])
      setExplainEnabled(false)
      setExplainModelFile(null)
      setCreateCardDraft(emptyModelCardDraft())
      setFile(null)
      setLayerUploadStatus(null)
      setLayerCreateOpen(false)
      await refreshList()
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : 'Create failed')
    } finally {
      setLayerUploadStatus(null)
      setCreating(false)
    }
  }

  const handleCloseLayerEdit = useCallback(async () => {
    if (editOpen && editModel) {
      const snap = buildLayerEditSnapshot()
      if (snap !== layerEditBaselineRef.current) {
        if (!canPersistLayerEdit()) {
          setEditError(
            'Fill in species and activity. For variable influence, use “Upload model for variable influence” to set features and a .pkl (or keep an existing server model).',
          )
          return
        }
        await persistLayerEdit()
      }
    }
    setEditOpen(false)
  }, [editOpen, editModel, buildLayerEditSnapshot, canPersistLayerEdit, persistLayerEdit])

  const activeProjects = projects.filter((p) => p.status === 'active')
  const canAddModel = activeProjects.length > 0

  if (loading) {
    return (
      <div className="app-container app-container--scroll">
        <Navbar />
        <div className="app-scroll-region">
          <Typography sx={{ p: 2 }}>Loading…</Typography>
        </div>
      </div>
    )
  }

  if (!user) {
    return (
      <div className="app-container app-container--scroll">
        <Navbar />
        <div className="app-scroll-region">
          <Container sx={{ py: 3 }}>
            <Alert severity="info">Sign in to manage the map catalog.</Alert>
          </Container>
        </div>
      </div>
    )
  }

  if (!isAdmin) {
    return (
      <div className="app-container app-container--scroll">
        <Navbar />
        <div className="app-scroll-region">
          <Container sx={{ py: 3 }}>
            <Alert severity="warning">
              Your account doesn’t have permission to edit the catalog. Ask your administrator for access.
            </Alert>
          </Container>
        </div>
      </div>
    )
  }

  return (
    <div className="app-container app-container--scroll">
      <Navbar />
      <Box
        className="app-scroll-region"
        sx={{
          bgcolor: (t) => (t.palette.mode === 'dark' ? 'grey.900' : 'grey.50'),
        }}
      >
        <Container maxWidth="lg" sx={{ py: { xs: 2, sm: 3 }, pb: 5 }}>
          <AdminCatalogHeader
            lastRefreshedAt={lastRefreshedAt}
            listRefreshing={listRefreshing}
            onRefresh={refreshList}
          />

          {listError && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {listError}
            </Alert>
          )}

          <Paper
            elevation={0}
            sx={{
              position: 'relative',
              borderRadius: 2,
              border: 1,
              borderColor: 'divider',
              overflow: 'hidden',
              bgcolor: 'background.paper',
            }}
          >
            {listRefreshing && (
              <LinearProgress
                sx={{ position: 'absolute', top: 0, left: 0, right: 0, zIndex: 2 }}
                aria-label="Loading projects and layers"
              />
            )}
            <Tabs
              value={tab}
              onChange={(_e, v) => setTab(v)}
              variant="fullWidth"
              sx={{
                borderBottom: 1,
                borderColor: 'divider',
                '& .MuiTab-root': { py: 1.75, textTransform: 'none', fontWeight: 600, fontSize: '0.95rem' },
              }}
            >
              <Tab
                icon={<FolderOutlinedIcon fontSize="small" />}
                iconPosition="start"
                label={`Projects (${projects.length})`}
                id="admin-tab-0"
                aria-controls="admin-tabpanel-0"
              />
              <Tab
                icon={<LayersOutlinedIcon fontSize="small" />}
                iconPosition="start"
                label={`Layers (${models.length})`}
                id="admin-tab-1"
                aria-controls="admin-tabpanel-1"
              />
            </Tabs>

            <Box sx={{ px: { xs: 2, sm: 3 } }}>
              <AdminTabPanel value={tab} index={0}>
                <ProjectsCatalogTab
                  projects={projects}
                  filteredProjects={filteredProjectsTable}
                  projectTableFilter={projectTableFilter}
                  onProjectTableFilterChange={setProjectTableFilter}
                  listRefreshing={listRefreshing}
                  onNewProject={() => setProjectCreateOpen(true)}
                  onOpenProjectEdit={openProjectEdit}
                />
              </AdminTabPanel>

              <AdminTabPanel value={tab} index={1}>
                <LayersCatalogTab
                  models={models}
                  filteredModels={filteredModelsTable}
                  projectById={projectById}
                  modelTableFilter={modelTableFilter}
                  onModelTableFilterChange={setModelTableFilter}
                  listRefreshing={listRefreshing}
                  onNewLayer={openLayerCreateDialog}
                  onOpenEdit={openEdit}
                  selectedModelIds={selectedModelIds}
                  bulkAssignProjectId={bulkAssignProjectId}
                  onBulkAssignProjectIdChange={setBulkAssignProjectId}
                  bulkAssigning={bulkAssigning}
                  bulkAssignError={bulkAssignError}
                  onBulkAssign={handleBulkAssignToProject}
                  onClearSelection={() => {
                    setSelectedModelIds([])
                    setBulkAssignError(null)
                  }}
                  toggleModelSelected={toggleModelSelected}
                  toggleSelectAllFiltered={toggleSelectAllFiltered}
                  allFilteredSelected={allFilteredSelected}
                  someFilteredSelected={someFilteredSelected}
                  activeProjects={activeProjects}
                  canAddModel={canAddModel}
                />
              </AdminTabPanel>
            </Box>
          </Paper>

          <ProjectCreateDialog
            open={projectCreateOpen}
            onClose={() => {
              setProjectCreateOpen(false)
              setProjError(null)
              setProjUploadStatus(null)
            }}
            formMaxWidth={FORM_MAX_WIDTH}
            projCreating={projCreating}
            projError={projError}
            projUploadStatus={projUploadStatus}
            onSubmit={handleCreateProject}
            projName={projName}
            projDesc={projDesc}
            projVisibility={projVisibility}
            projAllowedUids={projAllowedUids}
            projFile={projFile}
            onProjNameChange={setProjName}
            onProjDescChange={setProjDesc}
            onProjVisibilityChange={setProjVisibility}
            onProjAllowedUidsChange={setProjAllowedUids}
            onProjFileChange={setProjFile}
          />

          <LayerCreateDialog
            open={layerCreateOpen}
            onClose={() => {
              setLayerCreateOpen(false)
              setCreateError(null)
              setLayerUploadStatus(null)
            }}
            formMaxWidth={FORM_MAX_WIDTH}
            canAddModel={canAddModel}
            creating={creating}
            createError={createError}
            layerUploadStatus={layerUploadStatus}
            onSubmit={handleCreate}
            modelProjectId={modelProjectId}
            onModelProjectIdChange={setModelProjectId}
            activeProjects={activeProjects}
            species={species}
            activity={activity}
            selectedEnvironmentalBands={selectedEnvBands}
            onSelectedEnvironmentalBandsChange={setSelectedEnvBands}
            environmentalBandOptions={createLayerEnvOptions}
            explainabilityEnabled={explainEnabled}
            explainModelFile={explainModelFile}
            file={file}
            onSpeciesChange={setSpecies}
            onActivityChange={setActivity}
            onExplainabilityEnabledChange={setExplainEnabled}
            onExplainModelFileChange={setExplainModelFile}
            onFileChange={setFile}
            modelCardDraft={createCardDraft}
            onModelCardDraftChange={setCreateCardDraft}
          />

          <ProjectEditDialog
            open={projectEditOpen}
            onClose={() => void handleCloseProjectEdit()}
            formMaxWidth={FORM_MAX_WIDTH}
            editingProject={editingProject}
            editProjName={editProjName}
            editProjDesc={editProjDesc}
            editProjVisibility={editProjVisibility}
            editProjAllowedUids={editProjAllowedUids}
            editProjStatus={editProjStatus}
            editProjFile={editProjFile}
            environmentalBandDefinitions={editProjBandDefs}
            onEnvironmentalBandDefinitionsChange={setEditProjBandDefs}
            environmentalBandEditableFields="label"
            onEditProjNameChange={setEditProjName}
            onEditProjDescChange={setEditProjDesc}
            onEditProjVisibilityChange={setEditProjVisibility}
            onEditProjAllowedUidsChange={setEditProjAllowedUids}
            onEditProjStatusChange={setEditProjStatus}
            onEditProjFileChange={setEditProjFile}
            editProjError={editProjError}
            editProjUploadStatus={editProjUploadStatus}
            savingProjectEdit={savingProjectEdit}
            regenerateExplainabilitySampleRows={regenerateExplainBgRows}
            onRegenerateExplainabilitySampleRowsChange={setRegenerateExplainBgRows}
            onRegenerateExplainabilityBackground={handleRegenerateExplainabilityBackground}
            regeneratingExplainabilityBackground={regeneratingExplainBg}
            regenerateExplainabilityError={regenerateExplainBgError}
          />

          <LayerEditDialog
            open={editOpen}
            onClose={() => void handleCloseLayerEdit()}
            formMaxWidth={FORM_MAX_WIDTH}
            editModel={editModel}
            activeProjects={activeProjects}
            editProjectId={editProjectId}
            onEditProjectIdChange={handleEditProjectIdChange}
            editSpecies={editSpecies}
            editActivity={editActivity}
            selectedEnvironmentalBands={editSelectedEnvBands}
            onSelectedEnvironmentalBandsChange={setEditSelectedEnvBands}
            environmentalBandOptions={editLayerEnvOptions}
            editExplainabilityEnabled={editExplainEnabled}
            editExplainModelFile={editExplainModelFile}
            editExplainHasExistingArtifacts={
              editModel ? explainabilityConfiguredInCatalog(editModel) : false
            }
            editFile={editFile}
            onEditSpeciesChange={setEditSpecies}
            onEditActivityChange={setEditActivity}
            onEditExplainabilityEnabledChange={setEditExplainEnabled}
            onEditExplainModelFileChange={setEditExplainModelFile}
            onEditFileChange={setEditFile}
            editError={editError}
            savingEdit={savingEdit}
            modelCardDraft={editCardDraft}
            onModelCardDraftChange={setEditCardDraft}
          />
        </Container>
      </Box>
    </div>
  )
}
