import {
  Alert,
  Box,
  Button,
  Container,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  FormHelperText,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material'
import { useCallback, useEffect, useState } from 'react'
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
  'Shared environmental stack: multi-band COG (EPSG:3857), same validation as suitability uploads.'

const COG_REPLACE_HINT =
  'Optional. Same rules as a new upload; leave empty to keep the current file.'

export function AdminPage() {
  const { user, loading, isAdmin, getIdToken } = useAuth()
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
    if (!projFile) {
      setProjError('Choose an environmental COG file.')
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
        file: projFile,
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
      <div className="app-scroll-region">
        <Container maxWidth="lg" sx={{ py: 2, pb: 3 }}>
          <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 2 }}>
            <Typography variant="h5" component="h1">
              Admin — catalog
            </Typography>
            <Button component={Link} to="/" variant="outlined" size="small">
              Back to map
            </Button>
          </Stack>

          {listError && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {listError}
            </Alert>
          )}

          <Paper variant="outlined" sx={{ p: 2, mb: 3 }}>
            <Typography variant="subtitle1" sx={{ mb: 1 }}>
              Add catalog project
            </Typography>
            <Alert severity="info" variant="outlined" sx={{ mb: 2, maxWidth: 560, py: 0.75 }}>
              {DRIVER_COG_INFO}
            </Alert>
            <Box component="form" onSubmit={(e) => void handleCreateProject(e)}>
              <Stack spacing={2} sx={{ maxWidth: 560 }}>
                <TextField
                  required
                  label="Project name"
                  value={projName}
                  onChange={(e) => setProjName(e.target.value)}
                  size="small"
                  fullWidth
                />
                <TextField
                  label="Description"
                  value={projDesc}
                  onChange={(e) => setProjDesc(e.target.value)}
                  size="small"
                  fullWidth
                />
                <FormControl size="small" fullWidth>
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
                <TextField
                  label="Allowed user ids (private)"
                  helperText="Comma-separated Firebase uids, or JSON array"
                  value={projAllowedUids}
                  onChange={(e) => setProjAllowedUids(e.target.value)}
                  size="small"
                  fullWidth
                />
                <Stack direction="row" alignItems="center" spacing={1} flexWrap="wrap">
                  <Button variant="outlined" component="label" size="small">
                    Environmental COG
                    <input
                      type="file"
                      accept=".tif,.tiff,image/tiff"
                      hidden
                      onChange={(e) => setProjFile(e.target.files?.[0] ?? null)}
                    />
                  </Button>
                  <Typography variant="body2" color="text.secondary">
                    {projFile ? projFile.name : 'No file chosen'}
                  </Typography>
                </Stack>
              </Stack>
              {projError && (
                <Alert severity="error" sx={{ mt: 2 }}>
                  {projError}
                </Alert>
              )}
              <Button type="submit" variant="contained" sx={{ mt: 2 }} disabled={projCreating}>
                {projCreating ? 'Creating…' : 'Create project'}
              </Button>
            </Box>
          </Paper>

          <Table size="small" sx={{ mb: 3 }}>
            <TableHead>
              <TableRow>
                <TableCell>Project</TableCell>
                <TableCell>Visibility</TableCell>
                <TableCell>Status</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {projects.map((p) => (
                <TableRow key={p.id}>
                  <TableCell>
                    <Typography variant="body2" fontWeight={600}>
                      {p.name}
                    </Typography>
                    <Typography variant="caption" color="text.secondary" fontFamily="monospace">
                      {p.id}
                    </Typography>
                  </TableCell>
                  <TableCell>{p.visibility}</TableCell>
                  <TableCell>{p.status}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>

          <Paper variant="outlined" sx={{ p: 2, mb: 3 }}>
            <Typography variant="subtitle1" sx={{ mb: 1 }}>
              Add model
            </Typography>
            <Alert severity="info" variant="outlined" sx={{ mb: 2, maxWidth: 560, py: 0.75 }}>
              {COG_REQUIREMENTS_INFO}
            </Alert>
            <Box component="form" onSubmit={handleCreate}>
              <Stack spacing={2} sx={{ maxWidth: 560 }}>
                <FormControl required size="small" fullWidth>
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
                <TextField
                  label="Driver band indices (JSON array)"
                  helperText="Optional. E.g. [0,1,2] for bands from the project environmental COG."
                  value={driverBandIndices}
                  onChange={(e) => setDriverBandIndices(e.target.value)}
                  size="small"
                  fullWidth
                />
                <Stack direction="row" alignItems="center" spacing={1} flexWrap="wrap">
                  <Button variant="outlined" component="label" size="small">
                    Suitability COG file
                    <input
                      type="file"
                      accept=".tif,.tiff,image/tiff"
                      hidden
                      onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                    />
                  </Button>
                  <Typography variant="body2" color="text.secondary">
                    {file ? file.name : 'No file chosen'}
                  </Typography>
                </Stack>
              </Stack>
              {createError && (
                <Alert severity="error" sx={{ mt: 2 }}>
                  {createError}
                </Alert>
              )}
              <Button type="submit" variant="contained" sx={{ mt: 2 }} disabled={creating}>
                {creating ? 'Creating…' : 'Create model'}
              </Button>
            </Box>
          </Paper>

          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>ID</TableCell>
                <TableCell>Project</TableCell>
                <TableCell>Species</TableCell>
                <TableCell>Activity</TableCell>
                <TableCell>Name / version</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {models.map((m) => (
                <TableRow key={m.id}>
                  <TableCell sx={{ fontFamily: 'monospace', fontSize: 12 }}>{m.id}</TableCell>
                  <TableCell sx={{ fontFamily: 'monospace', fontSize: 11 }}>
                    {m.project_id ?? '—'}
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
              ))}
            </TableBody>
          </Table>

          <Dialog open={editOpen} onClose={() => setEditOpen(false)} fullWidth maxWidth="sm">
            <DialogTitle>Edit model</DialogTitle>
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
            <DialogActions>
              <Button onClick={() => setEditOpen(false)}>Cancel</Button>
              <Button variant="contained" onClick={() => void handleSaveEdit()} disabled={savingEdit}>
                {savingEdit ? 'Saving…' : 'Save'}
              </Button>
            </DialogActions>
          </Dialog>
        </Container>
      </div>
    </div>
  )
}
