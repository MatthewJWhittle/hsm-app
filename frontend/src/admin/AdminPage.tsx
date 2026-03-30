import {
  Alert,
  Box,
  Button,
  Chip,
  Container,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  FormControl,
  FormHelperText,
  InputLabel,
  MenuItem,
  Paper,
  Select,
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
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import '../App.css'

import { createModel, updateModel } from '../api/adminModels'
import { createProject } from '../api/adminProjects'
import { fetchModelCatalog } from '../api/catalog'
import { fetchProjectCatalog } from '../api/projects'
import { useAuth } from '../auth/useAuth'
import { Navbar } from '../components/Navbar'
import type { Model } from '../types/model'
import type { CatalogProject } from '../types/project'

/** One-line hints under each field (keep short to avoid a “wall of text”). */
const FIELD_HELP = {
  species: 'How this layer is labeled in the catalog and on the map.',
  activity: 'With species, identifies this entry (e.g. roosting, foraging).',
  modelName: 'Optional extra title beyond species and activity.',
  modelVersion: 'Optional label for this revision (e.g. date or version).',
} as const

const COG_REQUIREMENTS_INFO =
  'Suitability file: valid Cloud Optimized GeoTIFF (COG), Web Mercator (EPSG:3857). The server validates format, CRS, and upload size.'

const DRIVER_COG_INFO =
  'Optional on create: shared environmental stack (multi-band COG, EPSG:3857), same validation as suitability uploads. You can add or replace it later when editing the project.'

const COG_REPLACE_HINT =
  'Optional. Same rules as a new upload; leave empty to keep the current file.'

function shortId(id: string, head = 8): string {
  if (id.length <= head + 2) return id
  return `${id.slice(0, head)}…`
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

  const [projName, setProjName] = useState('')
  const [projDesc, setProjDesc] = useState('')
  const [projVisibility, setProjVisibility] = useState<'public' | 'private'>('public')
  const [projAllowedUids, setProjAllowedUids] = useState('')
  const [projFile, setProjFile] = useState<File | null>(null)
  const [projError, setProjError] = useState<string | null>(null)
  const [projCreating, setProjCreating] = useState(false)

  const [modelProjectId, setModelProjectId] = useState('')
  const [species, setSpecies] = useState('')
  const [activity, setActivity] = useState('')
  const [modelName, setModelName] = useState('')
  const [modelVersion, setModelVersion] = useState('')
  const [driverBandIndices, setDriverBandIndices] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [createError, setCreateError] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)

  const [editOpen, setEditOpen] = useState(false)
  const [editModel, setEditModel] = useState<Model | null>(null)
  const [editSpecies, setEditSpecies] = useState('')
  const [editActivity, setEditActivity] = useState('')
  const [editName, setEditName] = useState('')
  const [editVersion, setEditVersion] = useState('')
  const [editProjectId, setEditProjectId] = useState('')
  const [editFile, setEditFile] = useState<File | null>(null)
  const [editError, setEditError] = useState<string | null>(null)
  const [savingEdit, setSavingEdit] = useState(false)

  const projectById = useMemo(() => {
    const m = new Map<string, string>()
    for (const p of projects) {
      m.set(p.id, p.name)
    }
    return m
  }, [projects])

  const refreshList = useCallback(async () => {
    const token = await getIdToken(true)
    if (!token) return
    try {
      const [plist, mlist] = await Promise.all([
        fetchProjectCatalog({ token }),
        fetchModelCatalog({ token }),
      ])
      setProjects(plist)
      setModels(mlist)
      setListError(null)
    } catch {
      setListError('Could not load catalog.')
    }
  }, [getIdToken])

  useEffect(() => {
    refreshList()
  }, [refreshList])

  useEffect(() => {
    if (!modelProjectId && projects.length > 0) {
      const first = projects.find((p) => p.status === 'active')
      if (first) setModelProjectId(first.id)
    }
  }, [projects, modelProjectId])

  const openEdit = (m: Model) => {
    const first = projects.find((p) => p.status === 'active')
    setEditModel(m)
    setEditSpecies(m.species)
    setEditActivity(m.activity)
    setEditName(m.model_name ?? '')
    setEditVersion(m.model_version ?? '')
    setEditProjectId(m.project_id ?? first?.id ?? '')
    setEditFile(null)
    setEditError(null)
    setEditOpen(true)
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
      setCreateError('Select a catalog project.')
      return
    }
    if (!file) {
      setCreateError('Choose a suitability COG file.')
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
            <Alert severity="info">Sign in to access admin.</Alert>
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
              Admin access requires the <code>admin</code> custom claim on your account.
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
          <Stack
            direction={{ xs: 'column', sm: 'row' }}
            alignItems={{ xs: 'stretch', sm: 'flex-start' }}
            justifyContent="space-between"
            spacing={2}
            sx={{ mb: 3 }}
          >
            <Box>
              <Typography variant="h4" component="h1" fontWeight={700} sx={{ letterSpacing: '-0.02em' }}>
                Catalog admin
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, maxWidth: 520 }}>
                Create <strong>projects</strong> first (shared environmental stack), then attach{' '}
                <strong>models</strong> (species suitability layers). Everything here updates the live map
                catalog.
              </Typography>
            </Box>
            <Button
              component={Link}
              to="/"
              variant="outlined"
              size="medium"
              sx={{ flexShrink: 0, alignSelf: { xs: 'stretch', sm: 'center' } }}
            >
              Back to map
            </Button>
          </Stack>

          {listError && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {listError}
            </Alert>
          )}

          <Paper
            elevation={0}
            sx={{
              borderRadius: 2,
              border: 1,
              borderColor: 'divider',
              overflow: 'hidden',
              bgcolor: 'background.paper',
            }}
          >
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
                label={`Models (${models.length})`}
                id="admin-tab-1"
                aria-controls="admin-tabpanel-1"
              />
            </Tabs>

            <Box sx={{ px: { xs: 2, sm: 3 } }}>
              <TabPanel value={tab} index={0}>
                <Stack spacing={3}>
                  <Box>
                    <Typography variant="subtitle1" fontWeight={700} sx={{ mb: 1 }}>
                      New project
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                      Projects group models and hold the optional shared environmental COG.
                    </Typography>
                    <Alert severity="info" variant="outlined" sx={{ mb: 2, maxWidth: formMaxWidth }}>
                      {DRIVER_COG_INFO}
                    </Alert>
                    <Box component="form" onSubmit={(e) => void handleCreateProject(e)}>
                      <Stack spacing={2} sx={{ maxWidth: formMaxWidth }}>
                        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
                          <TextField
                            required
                            label="Project name"
                            value={projName}
                            onChange={(e) => setProjName(e.target.value)}
                            size="small"
                            fullWidth
                          />
                          <FormControl size="small" sx={{ minWidth: { sm: 200 } }} fullWidth>
                            <InputLabel>Visibility</InputLabel>
                            <Select
                              value={projVisibility}
                              label="Visibility"
                              onChange={(e) =>
                                setProjVisibility(e.target.value as 'public' | 'private')
                              }
                            >
                              <MenuItem value="public">Public</MenuItem>
                              <MenuItem value="private">Private</MenuItem>
                            </Select>
                          </FormControl>
                        </Stack>
                        <TextField
                          label="Description"
                          value={projDesc}
                          onChange={(e) => setProjDesc(e.target.value)}
                          size="small"
                          fullWidth
                        />
                        <TextField
                          label="Allowed user ids (private)"
                          helperText="Comma-separated Firebase uids, or JSON array"
                          value={projAllowedUids}
                          onChange={(e) => setProjAllowedUids(e.target.value)}
                          size="small"
                          fullWidth
                        />
                        <Box>
                          <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 0.75 }}>
                            Environmental COG (optional)
                          </Typography>
                          <Stack direction="row" alignItems="center" spacing={1} flexWrap="wrap" useFlexGap>
                            <Button variant="outlined" component="label" size="small">
                              Choose file
                              <input
                                type="file"
                                accept=".tif,.tiff,image/tiff"
                                hidden
                                onChange={(e) => setProjFile(e.target.files?.[0] ?? null)}
                              />
                            </Button>
                            <Typography variant="body2" color="text.secondary" noWrap sx={{ maxWidth: 280 }}>
                              {projFile ? projFile.name : 'No file selected'}
                            </Typography>
                          </Stack>
                        </Box>
                      </Stack>
                      {projError && (
                        <Alert severity="error" sx={{ mt: 2, maxWidth: formMaxWidth }}>
                          {projError}
                        </Alert>
                      )}
                      <Button type="submit" variant="contained" sx={{ mt: 2 }} disabled={projCreating}>
                        {projCreating ? 'Creating…' : 'Create project'}
                      </Button>
                    </Box>
                  </Box>

                  <Divider />

                  <Box>
                    <Typography variant="subtitle1" fontWeight={700} sx={{ mb: 1 }}>
                      All projects
                    </Typography>
                    <TableContainer
                      sx={{
                        borderRadius: 1,
                        border: 1,
                        borderColor: 'divider',
                        maxHeight: 360,
                      }}
                    >
                      <Table size="small" stickyHeader>
                        <TableHead>
                          <TableRow>
                            <TableCell>Project</TableCell>
                            <TableCell width={120}>Env. COG</TableCell>
                            <TableCell width={110}>Visibility</TableCell>
                            <TableCell width={100}>Status</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {projects.length === 0 ? (
                            <TableRow>
                              <TableCell colSpan={4}>
                                <Typography variant="body2" color="text.secondary" sx={{ py: 2 }}>
                                  No projects yet. Create one above.
                                </Typography>
                              </TableCell>
                            </TableRow>
                          ) : (
                            projects.map((p) => (
                              <TableRow key={p.id} hover>
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
                                    <Chip label="Uploaded" size="small" color="success" variant="outlined" />
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
                  <Box>
                    <Typography variant="subtitle1" fontWeight={700} sx={{ mb: 1 }}>
                      New model
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                      Each model is a suitability COG tied to a project.
                    </Typography>
                    {!canAddModel && (
                      <Alert severity="warning" sx={{ mb: 2, maxWidth: formMaxWidth }}>
                        Create at least one active project in the <strong>Projects</strong> tab first.
                      </Alert>
                    )}
                    <Alert severity="info" variant="outlined" sx={{ mb: 2, maxWidth: formMaxWidth }}>
                      {COG_REQUIREMENTS_INFO}
                    </Alert>
                    <Box
                      component="form"
                      onSubmit={handleCreate}
                      sx={{
                        opacity: canAddModel ? 1 : 0.55,
                        pointerEvents: canAddModel ? 'auto' : 'none',
                      }}
                    >
                      <Stack spacing={2} sx={{ maxWidth: formMaxWidth }}>
                        <FormControl required size="small" fullWidth disabled={!canAddModel}>
                          <InputLabel>Catalog project</InputLabel>
                          <Select
                            value={modelProjectId}
                            label="Catalog project"
                            onChange={(e) => setModelProjectId(e.target.value)}
                          >
                            {activeProjects.map((p) => (
                              <MenuItem key={p.id} value={p.id}>
                                {p.name}
                              </MenuItem>
                            ))}
                          </Select>
                        </FormControl>
                        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
                          <TextField
                            required
                            label="Species"
                            helperText={FIELD_HELP.species}
                            value={species}
                            onChange={(e) => setSpecies(e.target.value)}
                            size="small"
                            fullWidth
                          />
                          <TextField
                            required
                            label="Activity"
                            helperText={FIELD_HELP.activity}
                            value={activity}
                            onChange={(e) => setActivity(e.target.value)}
                            size="small"
                            fullWidth
                          />
                        </Stack>
                        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
                          <TextField
                            label="Model name"
                            helperText={FIELD_HELP.modelName}
                            value={modelName}
                            onChange={(e) => setModelName(e.target.value)}
                            size="small"
                            fullWidth
                          />
                          <TextField
                            label="Model version"
                            helperText={FIELD_HELP.modelVersion}
                            value={modelVersion}
                            onChange={(e) => setModelVersion(e.target.value)}
                            size="small"
                            fullWidth
                          />
                        </Stack>
                        <TextField
                          label="Driver band indices (JSON array)"
                          helperText="Optional. E.g. [0,1,2] for bands from the project environmental COG."
                          value={driverBandIndices}
                          onChange={(e) => setDriverBandIndices(e.target.value)}
                          size="small"
                          fullWidth
                        />
                        <Box>
                          <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 0.75 }}>
                            Suitability COG (required)
                          </Typography>
                          <Stack direction="row" alignItems="center" spacing={1} flexWrap="wrap" useFlexGap>
                            <Button variant="outlined" component="label" size="small">
                              Choose file
                              <input
                                type="file"
                                accept=".tif,.tiff,image/tiff"
                                hidden
                                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                              />
                            </Button>
                            <Typography variant="body2" color="text.secondary" noWrap sx={{ maxWidth: 280 }}>
                              {file ? file.name : 'No file selected'}
                            </Typography>
                          </Stack>
                        </Box>
                      </Stack>
                      {createError && (
                        <Alert severity="error" sx={{ mt: 2, maxWidth: formMaxWidth }}>
                          {createError}
                        </Alert>
                      )}
                      <Button
                        type="submit"
                        variant="contained"
                        sx={{ mt: 2 }}
                        disabled={creating || !canAddModel}
                      >
                        {creating ? 'Creating…' : 'Create model'}
                      </Button>
                    </Box>
                  </Box>

                  <Divider />

                  <Box>
                    <Typography variant="subtitle1" fontWeight={700} sx={{ mb: 1 }}>
                      All models
                    </Typography>
                    <TableContainer
                      sx={{
                        borderRadius: 1,
                        border: 1,
                        borderColor: 'divider',
                        maxHeight: 480,
                      }}
                    >
                      <Table size="small" stickyHeader>
                        <TableHead>
                          <TableRow>
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
                          {models.length === 0 ? (
                            <TableRow>
                              <TableCell colSpan={6}>
                                <Typography variant="body2" color="text.secondary" sx={{ py: 2 }}>
                                  No models yet. Add one above once a project exists.
                                </Typography>
                              </TableCell>
                            </TableRow>
                          ) : (
                            models.map((m) => {
                              const projectLabel = m.project_id
                                ? (projectById.get(m.project_id) ?? shortId(m.project_id))
                                : 'Legacy'
                              return (
                                <TableRow key={m.id} hover>
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
                                      <Chip label="Legacy" size="small" variant="outlined" />
                                    )}
                                  </TableCell>
                                  <TableCell>{m.species}</TableCell>
                                  <TableCell>{m.activity}</TableCell>
                                  <TableCell>
                                    {[m.model_name, m.model_version].filter(Boolean).join(' · ') || '—'}
                                  </TableCell>
                                  <TableCell align="right">
                                    <Button size="small" onClick={() => openEdit(m)}>
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
            open={editOpen}
            onClose={() => setEditOpen(false)}
            fullWidth
            maxWidth="sm"
            PaperProps={{ sx: { borderRadius: 2 } }}
          >
            <DialogTitle sx={{ fontWeight: 700 }}>Edit model</DialogTitle>
            <DialogContent>
              <Stack spacing={2} sx={{ mt: 1 }}>
                <FormControl size="small" fullWidth>
                  <InputLabel>Catalog project</InputLabel>
                  <Select
                    value={editProjectId}
                    label="Catalog project"
                    onChange={(e) => setEditProjectId(e.target.value)}
                  >
                    {activeProjects.map((p) => (
                      <MenuItem key={p.id} value={p.id}>
                        {p.name}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
                <TextField
                  label="Species"
                  helperText={FIELD_HELP.species}
                  value={editSpecies}
                  onChange={(e) => setEditSpecies(e.target.value)}
                  size="small"
                  fullWidth
                />
                <TextField
                  label="Activity"
                  helperText={FIELD_HELP.activity}
                  value={editActivity}
                  onChange={(e) => setEditActivity(e.target.value)}
                  size="small"
                  fullWidth
                />
                <TextField
                  label="Model name"
                  helperText={FIELD_HELP.modelName}
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  size="small"
                  fullWidth
                />
                <TextField
                  label="Model version"
                  helperText={FIELD_HELP.modelVersion}
                  value={editVersion}
                  onChange={(e) => setEditVersion(e.target.value)}
                  size="small"
                  fullWidth
                />
                <Box>
                  <Button variant="outlined" component="label" size="small">
                    Replace COG (optional)
                    <input
                      type="file"
                      accept=".tif,.tiff,image/tiff"
                      hidden
                      onChange={(e) => setEditFile(e.target.files?.[0] ?? null)}
                    />
                  </Button>
                  {editFile && (
                    <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.5 }}>
                      {editFile.name}
                    </Typography>
                  )}
                  <FormHelperText sx={{ mx: 0, mt: 0.5 }}>{COG_REPLACE_HINT}</FormHelperText>
                </Box>
                {editError && <Alert severity="error">{editError}</Alert>}
              </Stack>
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
