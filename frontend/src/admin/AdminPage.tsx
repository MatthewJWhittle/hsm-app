import {
  Alert,
  Box,
  Button,
  Checkbox,
  Chip,
  Container,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  IconButton,
  InputLabel,
  LinearProgress,
  MenuItem,
  Paper,
  Select,
  Skeleton,
  Stack,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tabs,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material'
import FolderOutlinedIcon from '@mui/icons-material/FolderOutlined'
import LayersOutlinedIcon from '@mui/icons-material/LayersOutlined'
import RefreshIcon from '@mui/icons-material/Refresh'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import '../App.css'

import { createModel, updateModel } from '../api/adminModels'
import { createProject, updateProject } from '../api/adminProjects'
import { fetchModelCatalog } from '../api/catalog'
import { fetchProjectCatalog } from '../api/projects'
import { useAuth } from '../auth/useAuth'
import { Navbar } from '../components/Navbar'
import type { Model } from '../types/model'
import type { CatalogProject } from '../types/project'

import { COG_REQUIREMENTS_INFO } from './catalogFormConstants'
import { MapLayerFormFields } from './MapLayerFormFields'
import { ProjectFormFields } from './ProjectFormFields'

function shortId(id: string, head = 8): string {
  if (id.length <= head + 2) return id
  return `${id.slice(0, head)}…`
}

function formatAdminDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  try {
    const d = new Date(iso)
    if (Number.isNaN(d.getTime())) return '—'
    return d.toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' })
  } catch {
    return '—'
  }
}

function TabPanel(props: { children?: React.ReactNode; index: number; value: number }) {
  const { children, value, index, ...other } = props
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`admin-tabpanel-${index}`}
      aria-labelledby={`admin-tab-${index}`}
      {...other}
    >
      {/* Keep mounted so form state survives tab switches */}
      <Box sx={{ py: { xs: 2, sm: 2.5 } }}>{children}</Box>
    </div>
  )
}

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
  const [driverBandIndices, setDriverBandIndices] = useState('')
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
  const [editDriverBandIndices, setEditDriverBandIndices] = useState('')
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

  const openLayerCreateDialog = useCallback(() => {
    setLayerCreateOpen(true)
    setModelProjectId((prev) => {
      if (prev) return prev
      const first = projects.find((p) => p.status === 'active')
      return first?.id ?? ''
    })
  }, [projects])

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
    setEditDriverBandIndices(
      m.driver_band_indices && m.driver_band_indices.length > 0
        ? JSON.stringify(m.driver_band_indices)
        : '',
    )
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
        driverBandIndicesJson: driverBandIndices.trim()
          ? driverBandIndices.trim()
          : undefined,
      })
      setSpecies('')
      setActivity('')
      setModelName('')
      setModelVersion('')
      setDriverBandIndices('')
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
        driverBandIndicesJson: editDriverBandIndices.trim() || '',
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

  const formMaxWidth = 640

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
          <Paper
            variant="outlined"
            sx={{
              p: 2,
              mb: 2,
              borderRadius: 2,
              display: 'flex',
              flexDirection: { xs: 'column', sm: 'row' },
              alignItems: { xs: 'stretch', sm: 'flex-start' },
              justifyContent: 'space-between',
              gap: 2,
            }}
          >
            <Box sx={{ flex: 1, minWidth: 0 }}>
              <Typography variant="h4" component="h1" fontWeight={700} sx={{ letterSpacing: '-0.02em' }}>
                Map catalog
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, maxWidth: 560 }}>
                Add <strong>projects</strong> to group layers and optional shared environmental data, then add{' '}
                <strong>map layers</strong> (suitability rasters). Published changes appear on the public map.
              </Typography>
            </Box>
            <Stack
              direction="row"
              alignItems="center"
              spacing={1}
              flexWrap="wrap"
              justifyContent={{ xs: 'flex-start', sm: 'flex-end' }}
              sx={{ flexShrink: 0 }}
            >
              <Typography variant="caption" color="text.secondary" sx={{ width: '100%', textAlign: { sm: 'right' } }}>
                {lastRefreshedAt
                  ? `List updated ${lastRefreshedAt.toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' })}`
                  : listRefreshing
                    ? 'Loading…'
                    : ''}
              </Typography>
              <Tooltip title="Reload list">
                <span>
                  <IconButton
                    size="small"
                    onClick={() => void refreshList()}
                    disabled={listRefreshing}
                    aria-label="Refresh list"
                  >
                    <RefreshIcon fontSize="small" />
                  </IconButton>
                </span>
              </Tooltip>
              <Button component={Link} to="/" variant="outlined" size="medium">
                Back to map
              </Button>
            </Stack>
          </Paper>

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
              <TabPanel value={tab} index={0}>
                <Stack spacing={3}>
                  <Button
                    variant="contained"
                    onClick={() => setProjectCreateOpen(true)}
                    sx={{ alignSelf: 'flex-start' }}
                  >
                    New project
                  </Button>

                  <Box>
                    <Typography variant="subtitle1" fontWeight={700} sx={{ mb: 1 }}>
                      All projects
                    </Typography>
                    <TextField
                      size="small"
                      fullWidth
                      placeholder="Filter by name, id, or description…"
                      value={projectTableFilter}
                      onChange={(e) => setProjectTableFilter(e.target.value)}
                      sx={{ mb: 1, maxWidth: 400 }}
                      aria-label="Filter projects table"
                    />
                    <TableContainer
                      component={Paper}
                      variant="outlined"
                      sx={{
                        borderRadius: 1,
                        maxHeight: 360,
                      }}
                    >
                      <Table size="small" stickyHeader aria-label="Projects">
                        <TableHead>
                          <TableRow>
                            <TableCell>Project</TableCell>
                            <TableCell width={120}>Environmental file</TableCell>
                            <TableCell width={110}>Visibility</TableCell>
                            <TableCell width={100}>Status</TableCell>
                            <TableCell width={140}>Updated</TableCell>
                            <TableCell align="right" width={88}>
                              Actions
                            </TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {listRefreshing && projects.length === 0 ? (
                            Array.from({ length: 5 }).map((_, i) => (
                              <TableRow key={i}>
                                <TableCell colSpan={6}>
                                  <Skeleton variant="text" width="80%" height={28} />
                                </TableCell>
                              </TableRow>
                            ))
                          ) : filteredProjectsTable.length === 0 ? (
                            <TableRow>
                              <TableCell colSpan={6}>
                                <Typography variant="body2" color="text.secondary" sx={{ py: 2 }}>
                                  {projects.length === 0
                                    ? 'No projects yet. Click New project to add one.'
                                    : 'No projects match this filter.'}
                                </Typography>
                              </TableCell>
                            </TableRow>
                          ) : (
                            filteredProjectsTable.map((p) => (
                              <TableRow
                                key={p.id}
                                hover
                                onClick={() => openProjectEdit(p)}
                                sx={{ cursor: 'pointer' }}
                              >
                                <TableCell>
                                  <Typography variant="body2" fontWeight={600}>
                                    {p.name}
                                  </Typography>
                                  <Tooltip title={p.id}>
                                    <Typography
                                      variant="caption"
                                      color="text.secondary"
                                      fontFamily="monospace"
                                      component="span"
                                      sx={{ display: 'block' }}
                                    >
                                      {shortId(p.id)}
                                    </Typography>
                                  </Tooltip>
                                </TableCell>
                                <TableCell>
                                  {p.driver_cog_path ? (
                                    <Chip label="On file" size="small" color="success" variant="outlined" />
                                  ) : (
                                    <Chip label="None" size="small" variant="outlined" />
                                  )}
                                </TableCell>
                                <TableCell>
                                  <Chip
                                    label={p.visibility}
                                    size="small"
                                    color={p.visibility === 'public' ? 'primary' : 'default'}
                                    variant="outlined"
                                  />
                                </TableCell>
                                <TableCell>
                                  <Chip
                                    label={p.status}
                                    size="small"
                                    color={p.status === 'active' ? 'success' : 'default'}
                                    variant="outlined"
                                  />
                                </TableCell>
                                <TableCell>
                                  <Typography variant="caption" color="text.secondary">
                                    {formatAdminDate(p.updated_at ?? p.created_at)}
                                  </Typography>
                                </TableCell>
                                <TableCell align="right">
                                  <Button
                                    size="small"
                                    onClick={(e) => {
                                      e.stopPropagation()
                                      openProjectEdit(p)
                                    }}
                                  >
                                    Edit
                                  </Button>
                                </TableCell>
                              </TableRow>
                            ))
                          )}
                        </TableBody>
                      </Table>
                    </TableContainer>
                  </Box>
                </Stack>
              </TabPanel>

              <TabPanel value={tab} index={1}>
                <Stack spacing={3}>
                  <Button
                    variant="contained"
                    onClick={openLayerCreateDialog}
                    sx={{ alignSelf: 'flex-start' }}
                  >
                    New layer
                  </Button>

                  <Box>
                    <Typography variant="subtitle1" fontWeight={700} sx={{ mb: 1 }}>
                      All map layers
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 1, maxWidth: 560 }}>
                      Select one or more layers with the checkboxes, then choose a project and click Assign to project.
                    </Typography>
                    <TextField
                      size="small"
                      fullWidth
                      placeholder="Filter by species, activity, project…"
                      value={modelTableFilter}
                      onChange={(e) => setModelTableFilter(e.target.value)}
                      sx={{ mb: 1, maxWidth: 400 }}
                      aria-label="Filter map layers table"
                    />
                    {selectedModelIds.length > 0 && (
                      <Paper
                        variant="outlined"
                        sx={{
                          p: 1.5,
                          mb: 1,
                          borderRadius: 1,
                          position: 'relative',
                          overflow: 'hidden',
                        }}
                      >
                        {bulkAssigning && (
                          <LinearProgress
                            sx={{ position: 'absolute', top: 0, left: 0, right: 0 }}
                            aria-label="Assigning layers to project"
                          />
                        )}
                        <Stack
                          direction={{ xs: 'column', sm: 'row' }}
                          spacing={1.5}
                          alignItems={{ sm: 'center' }}
                          flexWrap="wrap"
                          useFlexGap
                          sx={{ pt: bulkAssigning ? 0.5 : 0 }}
                        >
                          <Typography variant="body2" fontWeight={600}>
                            {selectedModelIds.length} layer{selectedModelIds.length === 1 ? '' : 's'} selected
                          </Typography>
                          <FormControl size="small" sx={{ minWidth: 220 }} disabled={bulkAssigning || !canAddModel}>
                            <InputLabel id="bulk-assign-project-label">Assign to project</InputLabel>
                            <Select
                              labelId="bulk-assign-project-label"
                              label="Assign to project"
                              value={bulkAssignProjectId}
                              onChange={(e) => setBulkAssignProjectId(e.target.value)}
                            >
                              {activeProjects.map((p) => (
                                <MenuItem key={p.id} value={p.id}>
                                  {p.name}
                                </MenuItem>
                              ))}
                            </Select>
                          </FormControl>
                          <Button
                            variant="contained"
                            size="small"
                            disabled={
                              bulkAssigning || !bulkAssignProjectId || selectedModelIds.length === 0 || !canAddModel
                            }
                            onClick={() => void handleBulkAssignToProject()}
                          >
                            {bulkAssigning ? 'Assigning…' : 'Assign to project'}
                          </Button>
                          <Button
                            variant="text"
                            size="small"
                            disabled={bulkAssigning}
                            onClick={() => {
                              setSelectedModelIds([])
                              setBulkAssignError(null)
                            }}
                          >
                            Clear selection
                          </Button>
                        </Stack>
                        {!canAddModel && (
                          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
                            Create an active project in the Projects tab first.
                          </Typography>
                        )}
                        {bulkAssignError && (
                          <Alert severity="error" sx={{ mt: 1.5, mb: 0 }}>
                            {bulkAssignError}
                          </Alert>
                        )}
                      </Paper>
                    )}
                    <TableContainer
                      component={Paper}
                      variant="outlined"
                      sx={{
                        borderRadius: 1,
                        maxHeight: 480,
                      }}
                    >
                      <Table size="small" stickyHeader aria-label="Map layers">
                        <TableHead>
                          <TableRow>
                            <TableCell padding="checkbox" sx={{ width: 48 }}>
                              <Checkbox
                                size="small"
                                indeterminate={someFilteredSelected && !allFilteredSelected}
                                checked={allFilteredSelected}
                                onChange={toggleSelectAllFiltered}
                                disabled={listRefreshing || filteredModelsTable.length === 0}
                                inputProps={{
                                  'aria-label': 'Select all layers in this list',
                                }}
                              />
                            </TableCell>
                            <TableCell width={100}>ID</TableCell>
                            <TableCell width={160}>Project</TableCell>
                            <TableCell>Species</TableCell>
                            <TableCell>Activity</TableCell>
                            <TableCell>Name / version</TableCell>
                            <TableCell align="right" width={88}>
                              Actions
                            </TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {listRefreshing && models.length === 0 ? (
                            Array.from({ length: 6 }).map((_, i) => (
                              <TableRow key={i}>
                                <TableCell colSpan={7}>
                                  <Skeleton variant="text" width="70%" height={28} />
                                </TableCell>
                              </TableRow>
                            ))
                          ) : filteredModelsTable.length === 0 ? (
                            <TableRow>
                              <TableCell colSpan={7}>
                                <Typography variant="body2" color="text.secondary" sx={{ py: 2 }}>
                                  {models.length === 0
                                    ? 'No layers yet. Create a project first, then click New layer to add one.'
                                    : 'No layers match this filter.'}
                                </Typography>
                              </TableCell>
                            </TableRow>
                          ) : (
                            filteredModelsTable.map((m) => {
                              const projectLabel = m.project_id
                                ? (projectById.get(m.project_id) ?? shortId(m.project_id))
                                : 'Stand-alone'
                              return (
                                <TableRow key={m.id} hover onClick={() => openEdit(m)} sx={{ cursor: 'pointer' }}>
                                  <TableCell padding="checkbox" onClick={(e) => e.stopPropagation()}>
                                    <Checkbox
                                      size="small"
                                      checked={selectedModelIds.includes(m.id)}
                                      onChange={() => toggleModelSelected(m.id)}
                                      inputProps={{ 'aria-label': `Select layer ${m.species} — ${m.activity}` }}
                                    />
                                  </TableCell>
                                  <TableCell>
                                    <Tooltip title={m.id}>
                                      <Typography
                                        variant="body2"
                                        fontFamily="monospace"
                                        fontSize={12}
                                        sx={{ cursor: 'default' }}
                                      >
                                        {shortId(m.id)}
                                      </Typography>
                                    </Tooltip>
                                  </TableCell>
                                  <TableCell>
                                    {m.project_id ? (
                                      <Typography variant="body2" noWrap title={projectLabel}>
                                        {projectLabel}
                                      </Typography>
                                    ) : (
                                      <Chip label="Stand-alone" size="small" variant="outlined" />
                                    )}
                                  </TableCell>
                                  <TableCell>{m.species}</TableCell>
                                  <TableCell>{m.activity}</TableCell>
                                  <TableCell>
                                    {[m.model_name, m.model_version].filter(Boolean).join(' · ') || '—'}
                                  </TableCell>
                                  <TableCell align="right">
                                    <Button
                                      size="small"
                                      onClick={(e) => {
                                        e.stopPropagation()
                                        openEdit(m)
                                      }}
                                    >
                                      Edit
                                    </Button>
                                  </TableCell>
                                </TableRow>
                              )
                            })
                          )}
                        </TableBody>
                      </Table>
                    </TableContainer>
                  </Box>
                </Stack>
              </TabPanel>
            </Box>
          </Paper>

          <Dialog
            open={projectCreateOpen}
            onClose={() => {
              if (projCreating) return
              setProjectCreateOpen(false)
              setProjError(null)
            }}
            fullWidth
            maxWidth="sm"
            PaperProps={{ sx: { borderRadius: 2 } }}
          >
            <DialogTitle sx={{ fontWeight: 700 }}>New project</DialogTitle>
            <DialogContent>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2, mt: 0.5 }}>
                A project groups related map layers. You can attach one optional shared environmental raster used by those
                layers.
              </Typography>
              <Box component="form" id="admin-new-project-form" onSubmit={(e) => void handleCreateProject(e)}>
                <ProjectFormFields
                  mode="create"
                  maxWidth={formMaxWidth}
                  name={projName}
                  description={projDesc}
                  visibility={projVisibility}
                  allowedUids={projAllowedUids}
                  onNameChange={setProjName}
                  onDescriptionChange={setProjDesc}
                  onVisibilityChange={setProjVisibility}
                  onAllowedUidsChange={setProjAllowedUids}
                  pendingFile={projFile}
                  onFileChange={setProjFile}
                />
                {projError && (
                  <Alert severity="error" sx={{ mt: 2, maxWidth: formMaxWidth }}>
                    {projError}
                  </Alert>
                )}
              </Box>
            </DialogContent>
            <DialogActions sx={{ px: 3, pb: 2 }}>
              <Button
                onClick={() => {
                  if (projCreating) return
                  setProjectCreateOpen(false)
                  setProjError(null)
                }}
                disabled={projCreating}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                form="admin-new-project-form"
                variant="contained"
                disabled={projCreating}
              >
                {projCreating ? 'Creating…' : 'Create project'}
              </Button>
            </DialogActions>
          </Dialog>

          <Dialog
            open={layerCreateOpen}
            onClose={() => {
              if (creating) return
              setLayerCreateOpen(false)
              setCreateError(null)
            }}
            fullWidth
            maxWidth="sm"
            PaperProps={{ sx: { borderRadius: 2 } }}
          >
            <DialogTitle sx={{ fontWeight: 700 }}>New map layer</DialogTitle>
            <DialogContent>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2, mt: 0.5 }}>
                One layer is one suitability raster for a species and activity, linked to a project.
              </Typography>
              {!canAddModel && (
                <Alert severity="warning" sx={{ mb: 2, maxWidth: formMaxWidth }}>
                  Create at least one active project in the <strong>Projects</strong> tab first.
                </Alert>
              )}
              <Alert severity="info" variant="outlined" sx={{ mb: 2, maxWidth: formMaxWidth }}>
                {COG_REQUIREMENTS_INFO}
              </Alert>
              <Box component="form" id="admin-new-layer-form" onSubmit={handleCreate}>
                <MapLayerFormFields
                  mode="create"
                  maxWidth={formMaxWidth}
                  projectId={modelProjectId}
                  onProjectChange={setModelProjectId}
                  activeProjects={activeProjects}
                  allowStandAloneProject={false}
                  species={species}
                  activity={activity}
                  modelName={modelName}
                  modelVersion={modelVersion}
                  driverBandIndices={driverBandIndices}
                  onSpeciesChange={setSpecies}
                  onActivityChange={setActivity}
                  onModelNameChange={setModelName}
                  onModelVersionChange={setModelVersion}
                  onDriverBandIndicesChange={setDriverBandIndices}
                  pendingFile={file}
                  onFileChange={setFile}
                  disabled={!canAddModel}
                />
                {createError && (
                  <Alert severity="error" sx={{ mt: 2, maxWidth: formMaxWidth }}>
                    {createError}
                  </Alert>
                )}
              </Box>
            </DialogContent>
            <DialogActions sx={{ px: 3, pb: 2 }}>
              <Button
                onClick={() => {
                  if (creating) return
                  setLayerCreateOpen(false)
                  setCreateError(null)
                }}
                disabled={creating}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                form="admin-new-layer-form"
                variant="contained"
                disabled={creating || !canAddModel}
              >
                {creating ? 'Creating…' : 'Create layer'}
              </Button>
            </DialogActions>
          </Dialog>

          <Dialog
            open={projectEditOpen}
            onClose={() => {
              setProjectEditOpen(false)
              setEditingProject(null)
            }}
            fullWidth
            maxWidth="sm"
            PaperProps={{ sx: { borderRadius: 2 } }}
          >
            <DialogTitle sx={{ fontWeight: 700 }}>Edit project</DialogTitle>
            <DialogContent>
              <Box sx={{ mt: 0.5 }}>
                <ProjectFormFields
                  mode="edit"
                  maxWidth={formMaxWidth}
                  name={editProjName}
                  description={editProjDesc}
                  visibility={editProjVisibility}
                  allowedUids={editProjAllowedUids}
                  status={editProjStatus}
                  onNameChange={setEditProjName}
                  onDescriptionChange={setEditProjDesc}
                  onVisibilityChange={setEditProjVisibility}
                  onAllowedUidsChange={setEditProjAllowedUids}
                  onStatusChange={setEditProjStatus}
                  pendingFile={editProjFile}
                  onFileChange={setEditProjFile}
                  projectId={editingProject?.id}
                  existingDriverPath={editingProject?.driver_cog_path ?? null}
                />
                {editProjError && (
                  <Alert severity="error" sx={{ mt: 2 }}>
                    {editProjError}
                  </Alert>
                )}
              </Box>
            </DialogContent>
            <DialogActions sx={{ px: 3, pb: 2 }}>
              <Button
                onClick={() => {
                  setProjectEditOpen(false)
                  setEditingProject(null)
                }}
              >
                Cancel
              </Button>
              <Button variant="contained" onClick={() => void handleSaveProjectEdit()} disabled={savingProjectEdit}>
                {savingProjectEdit ? 'Saving…' : 'Save'}
              </Button>
            </DialogActions>
          </Dialog>

          <Dialog
            open={editOpen}
            onClose={() => setEditOpen(false)}
            fullWidth
            maxWidth="sm"
            PaperProps={{ sx: { borderRadius: 2 } }}
          >
            <DialogTitle sx={{ fontWeight: 700 }}>Edit map layer</DialogTitle>
            <DialogContent>
              <Box sx={{ mt: 0.5 }}>
                <MapLayerFormFields
                  mode="edit"
                  maxWidth={formMaxWidth}
                  projectId={editProjectId}
                  onProjectChange={setEditProjectId}
                  activeProjects={activeProjects}
                  allowStandAloneProject
                  species={editSpecies}
                  activity={editActivity}
                  modelName={editName}
                  modelVersion={editVersion}
                  driverBandIndices={editDriverBandIndices}
                  onSpeciesChange={setEditSpecies}
                  onActivityChange={setEditActivity}
                  onModelNameChange={setEditName}
                  onModelVersionChange={setEditVersion}
                  onDriverBandIndicesChange={setEditDriverBandIndices}
                  pendingFile={editFile}
                  onFileChange={setEditFile}
                  layerId={editModel?.id}
                />
                {editError && (
                  <Alert severity="error" sx={{ mt: 2 }}>
                    {editError}
                  </Alert>
                )}
              </Box>
            </DialogContent>
            <DialogActions sx={{ px: 3, pb: 2 }}>
              <Button onClick={() => setEditOpen(false)}>Cancel</Button>
              <Button variant="contained" onClick={() => void handleSaveEdit()} disabled={savingEdit}>
                {savingEdit ? 'Saving…' : 'Save'}
              </Button>
            </DialogActions>
          </Dialog>
        </Container>
      </Box>
    </div>
  )
}
