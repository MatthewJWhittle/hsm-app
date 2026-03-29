import { HelpOutline } from '@mui/icons-material'
import {
  Alert,
  Box,
  Button,
  Container,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material'
import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { createModel, updateModel } from '../api/adminModels'
import { fetchModelCatalog } from '../api/catalog'
import { useAuth } from '../auth/useAuth'
import { Navbar } from '../components/Navbar'
import type { Model } from '../types/model'

/** Short hints for the catalog fields (aligned with API / data-models). */
const FIELD_HELP = {
  species:
    'Species or taxon this layer represents (e.g. common or scientific name). Shown in the catalog and used to identify the model on the map.',
  activity:
    'Behaviour or context for this suitability surface (e.g. roosting, foraging). Together with species, this uniquely labels the catalog entry.',
  modelName:
    'Optional display name for the model product or scenario if you want a title beyond species and activity.',
  modelVersion:
    'Optional version or revision label (e.g. date or semantic version) to track updates to this entry.',
  cogFile:
    'Must be a GeoTIFF that is a valid Cloud Optimized GeoTIFF (COG) in Web Mercator (EPSG:3857). Other CRS or invalid COGs are rejected. Maximum upload size is set on the server.',
  cogReplaceOptional:
    'Optional. Choose a new file only if you want to replace the suitability raster. Same COG and CRS rules as a new upload. Skip this to keep the existing COG and only change metadata.',
} as const

function FieldLabelWithTip({ text, hint }: { text: string; hint: string }) {
  return (
    <Box component="span" sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.25 }}>
      {text}
      <Tooltip title={hint} arrow placement="top" enterTouchDelay={0}>
        <Box
          component="span"
          sx={{
            display: 'inline-flex',
            color: 'action.active',
            cursor: 'help',
            verticalAlign: 'middle',
            '&:focus-visible': { outline: '2px solid', outlineOffset: 2, borderRadius: '2px' },
          }}
          tabIndex={0}
          aria-label={`${text}: more information`}
        >
          <HelpOutline sx={{ fontSize: '1rem' }} />
        </Box>
      </Tooltip>
    </Box>
  )
}

export function AdminPage() {
  const { user, loading, isAdmin, getIdToken } = useAuth()
  const [models, setModels] = useState<Model[]>([])
  const [listError, setListError] = useState<string | null>(null)

  const [species, setSpecies] = useState('')
  const [activity, setActivity] = useState('')
  const [modelName, setModelName] = useState('')
  const [modelVersion, setModelVersion] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [createError, setCreateError] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)

  const [editOpen, setEditOpen] = useState(false)
  const [editModel, setEditModel] = useState<Model | null>(null)
  const [editSpecies, setEditSpecies] = useState('')
  const [editActivity, setEditActivity] = useState('')
  const [editName, setEditName] = useState('')
  const [editVersion, setEditVersion] = useState('')
  const [editFile, setEditFile] = useState<File | null>(null)
  const [editError, setEditError] = useState<string | null>(null)
  const [savingEdit, setSavingEdit] = useState(false)

  const refreshList = useCallback(() => {
    fetchModelCatalog()
      .then((list) => {
        setModels(list)
        setListError(null)
      })
      .catch(() => setListError('Could not load catalog.'))
  }, [])

  useEffect(() => {
    refreshList()
  }, [refreshList])

  const openEdit = (m: Model) => {
    setEditModel(m)
    setEditSpecies(m.species)
    setEditActivity(m.activity)
    setEditName(m.model_name ?? '')
    setEditVersion(m.model_version ?? '')
    setEditFile(null)
    setEditError(null)
    setEditOpen(true)
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setCreateError(null)
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
        species,
        activity,
        file,
        modelName: modelName || undefined,
        modelVersion: modelVersion || undefined,
      })
      setSpecies('')
      setActivity('')
      setModelName('')
      setModelVersion('')
      setFile(null)
      refreshList()
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
      })
      setEditOpen(false)
      refreshList()
    } catch (err) {
      setEditError(err instanceof Error ? err.message : 'Update failed')
    } finally {
      setSavingEdit(false)
    }
  }

  if (loading) {
    return (
      <div className="app-container">
        <Navbar />
        <Typography sx={{ p: 2 }}>Loading…</Typography>
      </div>
    )
  }

  if (!user) {
    return (
      <div className="app-container">
        <Navbar />
        <Container sx={{ py: 3 }}>
          <Alert severity="info">Sign in to access admin.</Alert>
        </Container>
      </div>
    )
  }

  if (!isAdmin) {
    return (
      <div className="app-container">
        <Navbar />
        <Container sx={{ py: 3 }}>
          <Alert severity="warning">
            Admin access requires the <code>admin</code> custom claim on your account.
          </Alert>
        </Container>
      </div>
    )
  }

  return (
    <div className="app-container">
      <Navbar />
      <Container maxWidth="lg" sx={{ py: 2 }}>
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
            Add model
          </Typography>
          <Box component="form" onSubmit={handleCreate}>
            <Stack spacing={2} direction={{ xs: 'column', sm: 'row' }} useFlexGap flexWrap="wrap">
              <TextField
                required
                label={<FieldLabelWithTip text="Species" hint={FIELD_HELP.species} />}
                value={species}
                onChange={(e) => setSpecies(e.target.value)}
                size="small"
              />
              <TextField
                required
                label={<FieldLabelWithTip text="Activity" hint={FIELD_HELP.activity} />}
                value={activity}
                onChange={(e) => setActivity(e.target.value)}
                size="small"
              />
              <TextField
                label={<FieldLabelWithTip text="Model name" hint={FIELD_HELP.modelName} />}
                value={modelName}
                onChange={(e) => setModelName(e.target.value)}
                size="small"
              />
              <TextField
                label={<FieldLabelWithTip text="Model version" hint={FIELD_HELP.modelVersion} />}
                value={modelVersion}
                onChange={(e) => setModelVersion(e.target.value)}
                size="small"
              />
              <Stack direction="row" alignItems="center" spacing={1} flexWrap="wrap" sx={{ alignSelf: 'center' }}>
                <Tooltip title={FIELD_HELP.cogFile} enterTouchDelay={0}>
                  <span>
                    <Button variant="outlined" component="label" size="small">
                      COG file
                      <input
                        type="file"
                        accept=".tif,.tiff,image/tiff"
                        hidden
                        onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                      />
                    </Button>
                  </span>
                </Tooltip>
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
              {creating ? 'Creating…' : 'Create'}
            </Button>
          </Box>
        </Paper>

        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>ID</TableCell>
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
              <TextField
                label={<FieldLabelWithTip text="Species" hint={FIELD_HELP.species} />}
                value={editSpecies}
                onChange={(e) => setEditSpecies(e.target.value)}
                size="small"
                fullWidth
              />
              <TextField
                label={<FieldLabelWithTip text="Activity" hint={FIELD_HELP.activity} />}
                value={editActivity}
                onChange={(e) => setEditActivity(e.target.value)}
                size="small"
                fullWidth
              />
              <TextField
                label={<FieldLabelWithTip text="Model name" hint={FIELD_HELP.modelName} />}
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                size="small"
                fullWidth
              />
              <TextField
                label={<FieldLabelWithTip text="Model version" hint={FIELD_HELP.modelVersion} />}
                value={editVersion}
                onChange={(e) => setEditVersion(e.target.value)}
                size="small"
                fullWidth
              />
              <Tooltip title={FIELD_HELP.cogReplaceOptional} enterTouchDelay={0}>
                <span>
                  <Button variant="outlined" component="label" size="small" sx={{ alignSelf: 'flex-start' }}>
                    Replace COG (optional)
                    <input
                      type="file"
                      accept=".tif,.tiff,image/tiff"
                      hidden
                      onChange={(e) => setEditFile(e.target.files?.[0] ?? null)}
                    />
                  </Button>
                </span>
              </Tooltip>
              {editFile && (
                <Typography variant="caption" color="text.secondary">
                  {editFile.name}
                </Typography>
              )}
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
  )
}
