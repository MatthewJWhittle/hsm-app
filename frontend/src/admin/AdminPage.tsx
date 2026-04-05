import { Alert, Box, Container, LinearProgress, Paper, Tab, Tabs, Typography } from '@mui/material'
import FolderOutlinedIcon from '@mui/icons-material/FolderOutlined'
import LayersOutlinedIcon from '@mui/icons-material/LayersOutlined'
import { useCallback, useEffect, useMemo, useState } from 'react'

import '../App.css'

import { createModel, updateModel } from '../api/adminModels'
import { createProject, updateProject } from '../api/adminProjects'
import { fetchModelCatalog } from '../api/catalog'
import { fetchProjectCatalog } from '../api/projects'
import { useAuth } from '../auth/useAuth'
import { Navbar } from '../components/Navbar'
import type { Model } from '../types/model'
import type { CatalogProject, EnvironmentalBandDefinition } from '../types/project'

import { bandsFromDriverIndices, environmentalBandsForProject } from './adminBandSelect'
import { explainabilityConfiguredInCatalog, mergeDriverConfigForSubmit } from './adminExplainability'
import { AdminCatalogHeader } from './AdminCatalogHeader'
import { AdminTabPanel } from './AdminTabPanel'
import { LayerCreateDialog } from './LayerCreateDialog'
import { LayerEditDialog } from './LayerEditDialog'
import { LayersCatalogTab } from './LayersCatalogTab'
import { ProjectCreateDialog } from './ProjectCreateDialog'
import { ProjectEditDialog } from './ProjectEditDialog'
import { ProjectsCatalogTab } from './ProjectsCatalogTab'

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
  const [projCreating, setProjCreating] = useState(false)
  const [projectCreateOpen, setProjectCreateOpen] = useState(false)

  const [modelProjectId, setModelProjectId] = useState('')
  const [species, setSpecies] = useState('')
  const [activity, setActivity] = useState('')
  const [modelName, setModelName] = useState('')
  const [modelVersion, setModelVersion] = useState('')
  const [selectedEnvBands, setSelectedEnvBands] = useState<EnvironmentalBandDefinition[]>([])
  const [explainEnabled, setExplainEnabled] = useState(false)
  const [explainModelFile, setExplainModelFile] = useState<File | null>(null)
  const [explainBackgroundFile, setExplainBackgroundFile] = useState<File | null>(null)
  const [file, setFile] = useState<File | null>(null)
  const [createError, setCreateError] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)
  const [layerCreateOpen, setLayerCreateOpen] = useState(false)

  const [editOpen, setEditOpen] = useState(false)
  const [editModel, setEditModel] = useState<Model | null>(null)
  const [editSpecies, setEditSpecies] = useState('')
  const [editActivity, setEditActivity] = useState('')
  const [editName, setEditName] = useState('')
  const [editVersion, setEditVersion] = useState('')
  const [editProjectId, setEditProjectId] = useState('')
  const [editFile, setEditFile] = useState<File | null>(null)
  const [editSelectedEnvBands, setEditSelectedEnvBands] = useState<EnvironmentalBandDefinition[]>([])
  const [editExplainEnabled, setEditExplainEnabled] = useState(false)
  const [editExplainModelFile, setEditExplainModelFile] = useState<File | null>(null)
  const [editExplainBackgroundFile, setEditExplainBackgroundFile] = useState<File | null>(null)
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
  const [savingProjectEdit, setSavingProjectEdit] = useState(false)

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
      const hay = `${m.species} ${m.activity} ${m.id} ${m.project_id ?? ''} ${m.model_name ?? ''} ${m.model_version ?? ''}`.toLowerCase()
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

  const handleEditProjectIdChange = useCallback(
    (id: string) => {
      setEditProjectId(id)
      if (editModel) {
        const defs = id ? environmentalBandsForProject(id, projects) : null
        setEditSelectedEnvBands(bandsFromDriverIndices(editModel.driver_band_indices, defs))
      }
    },
    [editModel, projects],
  )

  const openLayerCreateDialog = useCallback(() => {
    setLayerCreateOpen(true)
    setSelectedEnvBands([])
    setExplainEnabled(false)
    setExplainModelFile(null)
    setExplainBackgroundFile(null)
    setModelProjectId((prev) => {
      if (prev) return prev
      const first = projects.find((p) => p.status === 'active')
      return first?.id ?? ''
    })
  }, [projects])

  useEffect(() => {
    if (layerCreateOpen) setSelectedEnvBands([])
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
          modelName: m.model_name ?? null,
          modelVersion: m.model_version ?? null,
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
    setEditSpecies(m.species)
    setEditActivity(m.activity)
    setEditName(m.model_name ?? '')
    setEditVersion(m.model_version ?? '')
    setEditProjectId(m.project_id ?? '')
    const defs = m.project_id ? environmentalBandsForProject(m.project_id, projects) : null
    setEditSelectedEnvBands(bandsFromDriverIndices(m.driver_band_indices, defs))
    setEditExplainEnabled(explainabilityConfiguredInCatalog(m))
    setEditExplainModelFile(null)
    setEditExplainBackgroundFile(null)
    setEditFile(null)
    setEditError(null)
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
    setProjectEditOpen(true)
  }

  const handleSaveProjectEdit = async () => {
    if (!editingProject) return
    setEditProjError(null)
    const token = await getIdToken(true)
    if (!token) {
      setEditProjError('Not signed in.')
      return
    }
    if (!editProjName.trim()) {
      setEditProjError('Project name is required.')
      return
    }
    setSavingProjectEdit(true)
    try {
      await updateProject({
        token,
        projectId: editingProject.id,
        name: editProjName.trim(),
        description: editProjDesc.trim() || null,
        status: editProjStatus,
        visibility: editProjVisibility,
        allowedUids: editProjAllowedUids,
        file: editProjFile ?? undefined,
        ...(editingProject.driver_cog_path || editProjFile
          ? { environmentalBandDefinitionsJson: JSON.stringify(editProjBandDefs) }
          : {}),
      })
      setProjectEditOpen(false)
      setEditingProject(null)
      await refreshList()
    } catch (err) {
      setEditProjError(err instanceof Error ? err.message : 'Update failed')
    } finally {
      setSavingProjectEdit(false)
    }
  }

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
      await createProject({
        token,
        name: projName,
        file: projFile ?? undefined,
        description: projDesc || undefined,
        visibility: projVisibility,
        allowedUids: projAllowedUids || undefined,
      })
      setProjName('')
      setProjDesc('')
      setProjVisibility('public')
      setProjAllowedUids('')
      setProjFile(null)
      setProjectCreateOpen(false)
      await refreshList()
    } catch (err) {
      setProjError(err instanceof Error ? err.message : 'Create project failed')
    } finally {
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

    const driverConfigJson = mergeDriverConfigForSubmit(null, {
      enabled: explainEnabled,
    })
    const hasDriverConfig = Object.keys(JSON.parse(driverConfigJson)).length > 0

    if (explainEnabled) {
      if (selectedEnvBands.length === 0) {
        setCreateError(
          'Select environmental variables in model feature order (from the project’s band list).',
        )
        return
      }
      if (!explainModelFile || !explainBackgroundFile) {
        setCreateError(
          'Variable influence requires both a trained model (.pkl) and a reference sample (.parquet).',
        )
        return
      }
    }

    setCreating(true)
    try {
      await createModel({
        token,
        projectId: modelProjectId,
        species,
        activity,
        file,
        modelName: modelName || undefined,
        modelVersion: modelVersion || undefined,
        driverBandIndicesJson:
          selectedEnvBands.length > 0 ? JSON.stringify(selectedEnvBands.map((b) => b.index)) : undefined,
        driverConfigJson: hasDriverConfig ? driverConfigJson : undefined,
        explainabilityModelFile: explainEnabled ? explainModelFile : undefined,
        explainabilityBackgroundFile: explainEnabled ? explainBackgroundFile : undefined,
      })
      setSpecies('')
      setActivity('')
      setModelName('')
      setModelVersion('')
      setSelectedEnvBands([])
      setExplainEnabled(false)
      setExplainModelFile(null)
      setExplainBackgroundFile(null)
      setFile(null)
      setLayerCreateOpen(false)
      await refreshList()
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : 'Create failed')
    } finally {
      setCreating(false)
    }
  }

  const handleSaveEdit = async () => {
    if (!editModel) return
    setEditError(null)
    const token = await getIdToken(true)
    if (!token) {
      setEditError('Not signed in.')
      return
    }

    const driverConfigJson = mergeDriverConfigForSubmit(editModel.driver_config ?? null, {
      enabled: editExplainEnabled,
    })

    if (editExplainEnabled) {
      if (editSelectedEnvBands.length === 0) {
        setEditError(
          'Select environmental variables in model feature order (from the project’s band list).',
        )
        return
      }
      const hadArtifacts = explainabilityConfiguredInCatalog(editModel)
      if (!hadArtifacts && (!editExplainModelFile || !editExplainBackgroundFile)) {
        setEditError(
          'Upload both a trained model (.pkl) and a reference sample (.parquet), or save without variable influence.',
        )
        return
      }
    }

    setSavingEdit(true)
    try {
      await updateModel({
        token,
        modelId: editModel.id,
        species: editSpecies,
        activity: editActivity,
        modelName: editName || null,
        modelVersion: editVersion || null,
        file: editFile,
        projectId: editProjectId || undefined,
        driverBandIndicesJson:
          editSelectedEnvBands.length > 0
            ? JSON.stringify(editSelectedEnvBands.map((b) => b.index))
            : '',
        driverConfigJson,
        explainabilityModelFile: editExplainModelFile ?? undefined,
        explainabilityBackgroundFile: editExplainBackgroundFile ?? undefined,
      })
      setEditOpen(false)
      await refreshList()
    } catch (err) {
      setEditError(err instanceof Error ? err.message : 'Update failed')
    } finally {
      setSavingEdit(false)
    }
  }

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
            }}
            formMaxWidth={FORM_MAX_WIDTH}
            projCreating={projCreating}
            projError={projError}
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
            }}
            formMaxWidth={FORM_MAX_WIDTH}
            canAddModel={canAddModel}
            creating={creating}
            createError={createError}
            onSubmit={handleCreate}
            modelProjectId={modelProjectId}
            onModelProjectIdChange={setModelProjectId}
            activeProjects={activeProjects}
            species={species}
            activity={activity}
            modelName={modelName}
            modelVersion={modelVersion}
            selectedEnvironmentalBands={selectedEnvBands}
            onSelectedEnvironmentalBandsChange={setSelectedEnvBands}
            environmentalBandOptions={createLayerEnvOptions}
            explainabilityEnabled={explainEnabled}
            explainModelFile={explainModelFile}
            explainBackgroundFile={explainBackgroundFile}
            file={file}
            onSpeciesChange={setSpecies}
            onActivityChange={setActivity}
            onModelNameChange={setModelName}
            onModelVersionChange={setModelVersion}
            onExplainabilityEnabledChange={setExplainEnabled}
            onExplainModelFileChange={setExplainModelFile}
            onExplainBackgroundFileChange={setExplainBackgroundFile}
            onFileChange={setFile}
          />

          <ProjectEditDialog
            open={projectEditOpen}
            onClose={() => {
              setProjectEditOpen(false)
              setEditingProject(null)
            }}
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
            onEditProjNameChange={setEditProjName}
            onEditProjDescChange={setEditProjDesc}
            onEditProjVisibilityChange={setEditProjVisibility}
            onEditProjAllowedUidsChange={setEditProjAllowedUids}
            onEditProjStatusChange={setEditProjStatus}
            onEditProjFileChange={setEditProjFile}
            editProjError={editProjError}
            savingProjectEdit={savingProjectEdit}
            onSave={handleSaveProjectEdit}
          />

          <LayerEditDialog
            open={editOpen}
            onClose={() => setEditOpen(false)}
            formMaxWidth={FORM_MAX_WIDTH}
            editModel={editModel}
            activeProjects={activeProjects}
            editProjectId={editProjectId}
            onEditProjectIdChange={handleEditProjectIdChange}
            editSpecies={editSpecies}
            editActivity={editActivity}
            editName={editName}
            editVersion={editVersion}
            selectedEnvironmentalBands={editSelectedEnvBands}
            onSelectedEnvironmentalBandsChange={setEditSelectedEnvBands}
            environmentalBandOptions={editLayerEnvOptions}
            editExplainabilityEnabled={editExplainEnabled}
            editExplainModelFile={editExplainModelFile}
            editExplainBackgroundFile={editExplainBackgroundFile}
            editExplainHasExistingArtifacts={
              editModel ? explainabilityConfiguredInCatalog(editModel) : false
            }
            editFile={editFile}
            onEditSpeciesChange={setEditSpecies}
            onEditActivityChange={setEditActivity}
            onEditNameChange={setEditName}
            onEditVersionChange={setEditVersion}
            onEditExplainabilityEnabledChange={setEditExplainEnabled}
            onEditExplainModelFileChange={setEditExplainModelFile}
            onEditExplainBackgroundFileChange={setEditExplainBackgroundFile}
            onEditFileChange={setEditFile}
            editError={editError}
            savingEdit={savingEdit}
            onSave={handleSaveEdit}
          />
        </Container>
      </Box>
    </div>
  )
}
