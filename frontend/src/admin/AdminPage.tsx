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
  Typography,
} from '@mui/material'
import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { createModel, updateModel } from '../api/adminModels'
import { fetchModelCatalog } from '../api/catalog'
import { useAuth } from '../auth/useAuth'
import { Navbar } from '../components/Navbar'
import type { Model } from '../types/model'

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
                label="Species"
                value={species}
                onChange={(e) => setSpecies(e.target.value)}
                size="small"
              />
              <TextField
                required
                label="Activity"
                value={activity}
                onChange={(e) => setActivity(e.target.value)}
                size="small"
              />
              <TextField
                label="Model name"
                value={modelName}
                onChange={(e) => setModelName(e.target.value)}
                size="small"
              />
              <TextField
                label="Model version"
                value={modelVersion}
                onChange={(e) => setModelVersion(e.target.value)}
                size="small"
              />
              <Button variant="outlined" component="label" size="small">
                COG file
                <input
                  type="file"
                  accept=".tif,.tiff,image/tiff"
                  hidden
                  onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                />
              </Button>
              <Typography variant="body2" color="text.secondary" sx={{ alignSelf: 'center' }}>
                {file ? file.name : 'No file chosen'}
              </Typography>
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
                label="Species"
                value={editSpecies}
                onChange={(e) => setEditSpecies(e.target.value)}
                size="small"
                fullWidth
              />
              <TextField
                label="Activity"
                value={editActivity}
                onChange={(e) => setEditActivity(e.target.value)}
                size="small"
                fullWidth
              />
              <TextField
                label="Model name"
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                size="small"
                fullWidth
              />
              <TextField
                label="Model version"
                value={editVersion}
                onChange={(e) => setEditVersion(e.target.value)}
                size="small"
                fullWidth
              />
              <Button variant="outlined" component="label" size="small" sx={{ alignSelf: 'flex-start' }}>
                Replace COG (optional)
                <input
                  type="file"
                  accept=".tif,.tiff,image/tiff"
                  hidden
                  onChange={(e) => setEditFile(e.target.files?.[0] ?? null)}
                />
              </Button>
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
