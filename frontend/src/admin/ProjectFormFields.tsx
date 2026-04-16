import {
  Alert,
  Box,
  Button,
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

import type { EnvironmentalBandDefinition } from '../types/project'
import { DRIVER_COG_INFO, COG_REPLACE_HINT } from './catalogFormConstants'

function formatBackgroundGeneratedAt(iso: string | null | undefined): string {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}

export interface ProjectFormFieldsProps {
  mode: 'create' | 'edit'
  /** Applied to the inner field stack */
  maxWidth?: number
  name: string
  description: string
  visibility: 'public' | 'private'
  allowedUids: string
  /** Edit only */
  status?: 'active' | 'archived'
  onNameChange: (value: string) => void
  onDescriptionChange: (value: string) => void
  onVisibilityChange: (value: 'public' | 'private') => void
  onAllowedUidsChange: (value: string) => void
  onStatusChange?: (value: 'active' | 'archived') => void
  pendingFile: File | null
  onFileChange: (file: File | null) => void
  onUploadEnvironmentalCog?: () => void | Promise<void>
  canUploadEnvironmentalCog?: boolean
  /** Edit: full id for display */
  projectId?: string
  /** Edit: existing stored path, if any */
  existingDriverPath?: string | null
  /** Edit: band names/labels for the environmental COG (one row per raster band). */
  environmentalBandDefinitions?: EnvironmentalBandDefinition[]
  onEnvironmentalBandDefinitionsChange?: (value: EnvironmentalBandDefinition[]) => void
  /** Edit: ``label`` = display names only; ``all`` = name + label (stable names must match training). */
  environmentalBandEditableFields?: 'label' | 'all'
  /** Edit: SHAP background Parquet — row count for optional manual regeneration */
  regenerateExplainabilitySampleRows?: number
  onRegenerateExplainabilitySampleRowsChange?: (n: number) => void
  onRegenerateExplainabilityBackground?: () => void | Promise<void>
  regeneratingExplainabilityBackground?: boolean
  regenerateExplainabilityError?: string | null
  /** Edit: catalog metadata for the SHAP background Parquet (when present). */
  explainabilityBackgroundPath?: string | null
  explainabilityBackgroundSampleRows?: number | null
  explainabilityBackgroundGeneratedAt?: string | null
}

export function ProjectFormFields({
  mode,
  maxWidth = 640,
  name,
  description,
  visibility,
  allowedUids,
  status = 'active',
  onNameChange,
  onDescriptionChange,
  onVisibilityChange,
  onAllowedUidsChange,
  onStatusChange,
  pendingFile,
  onFileChange,
  onUploadEnvironmentalCog,
  canUploadEnvironmentalCog = false,
  projectId,
  existingDriverPath,
  environmentalBandDefinitions = [],
  onEnvironmentalBandDefinitionsChange,
  environmentalBandEditableFields = 'label',
  regenerateExplainabilitySampleRows = 256,
  onRegenerateExplainabilitySampleRowsChange,
  onRegenerateExplainabilityBackground,
  regeneratingExplainabilityBackground = false,
  regenerateExplainabilityError = null,
  explainabilityBackgroundPath = null,
  explainabilityBackgroundSampleRows = null,
  explainabilityBackgroundGeneratedAt = null,
}: ProjectFormFieldsProps) {
  const isEdit = mode === 'edit'
  const hasCog = Boolean(existingDriverPath)
  const sortedBands = [...environmentalBandDefinitions].sort((a, b) => a.index - b.index)
  const namesEditable = environmentalBandEditableFields === 'all'

  const updateBandRow = (bandIndex: number, field: 'name' | 'label' | 'description', value: string) => {
    if (!onEnvironmentalBandDefinitionsChange) return
    if (field === 'name' && !namesEditable) return
    let stored: string | null = value
    if (field === 'label' || field === 'description') {
      stored = value.trim() === '' ? null : value
    }
    const next = environmentalBandDefinitions.map((row) =>
      row.index === bandIndex ? { ...row, [field]: stored } : row,
    )
    onEnvironmentalBandDefinitionsChange(next)
  }

  return (
    <Stack spacing={2} sx={{ maxWidth }}>
      {isEdit && projectId && (
        <Typography variant="caption" color="text.secondary">
          ID:{' '}
          <Box component="span" sx={{ fontFamily: 'monospace', userSelect: 'all' }}>
            {projectId}
          </Box>
        </Typography>
      )}
      <TextField
        required
        label="Project name"
        value={name}
        onChange={(e) => onNameChange(e.target.value)}
        size="small"
        fullWidth
      />
      <TextField
        label="Description"
        value={description}
        onChange={(e) => onDescriptionChange(e.target.value)}
        size="small"
        fullWidth
        {...(isEdit ? { multiline: true, minRows: 2 } : {})}
      />
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
        <FormControl size="small" sx={{ minWidth: { sm: isEdit ? 160 : 200 } }} fullWidth>
          <InputLabel>Visibility</InputLabel>
          <Select
            value={visibility}
            label="Visibility"
            onChange={(e) => onVisibilityChange(e.target.value as 'public' | 'private')}
          >
            <MenuItem value="public">Public</MenuItem>
            <MenuItem value="private">Private</MenuItem>
          </Select>
        </FormControl>
        {isEdit && onStatusChange && (
          <FormControl size="small" sx={{ minWidth: 160 }} fullWidth>
            <InputLabel>Status</InputLabel>
            <Select
              value={status}
              label="Status"
              onChange={(e) => onStatusChange(e.target.value as 'active' | 'archived')}
            >
              <MenuItem value="active">Active</MenuItem>
              <MenuItem value="archived">Archived</MenuItem>
            </Select>
          </FormControl>
        )}
      </Stack>
      <TextField
        label="Who can view (private projects)"
        helperText="Account IDs, comma-separated or as a JSON array"
        value={allowedUids}
        onChange={(e) => onAllowedUidsChange(e.target.value)}
        size="small"
        fullWidth
      />
      {visibility === 'private' && !allowedUids.trim() && (
        <Alert severity="warning" sx={{ py: 0.5 }}>
          Add at least one account here, or signed-in map users won’t see this project.
        </Alert>
      )}
      <Alert severity="info" variant="outlined" sx={{ py: isEdit ? 1 : undefined }}>
        {DRIVER_COG_INFO}
      </Alert>
      <Box>
        <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 0.75 }}>
          {isEdit
            ? 'Shared environmental raster (optional upload or replace)'
            : 'Shared environmental raster (optional)'}
        </Typography>
        {isEdit && (
          <>
            {existingDriverPath ? (
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                Current file: <strong>{existingDriverPath}</strong>
              </Typography>
            ) : (
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                No environmental file uploaded yet.
              </Typography>
            )}
          </>
        )}
        <Stack direction="row" alignItems="center" spacing={1} flexWrap="wrap" useFlexGap>
          <Button variant="outlined" component="label" size="small">
            Choose file
            <input
              type="file"
              accept=".tif,.tiff,image/tiff"
              hidden
              onChange={(e) => onFileChange(e.target.files?.[0] ?? null)}
            />
          </Button>
          <Typography variant="body2" color="text.secondary" noWrap sx={{ maxWidth: isEdit ? 260 : 280 }}>
            {pendingFile
              ? pendingFile.name
              : isEdit
                ? 'No new file selected'
                : 'No file selected'}
          </Typography>
          {isEdit && onUploadEnvironmentalCog && (
            <Button
              variant="contained"
              size="small"
              disabled={!canUploadEnvironmentalCog}
              onClick={() => void onUploadEnvironmentalCog()}
            >
              Upload / Replace environmental COG
            </Button>
          )}
          {isEdit && hasCog && sortedBands.length > 0 && onRegenerateExplainabilityBackground && (
            <>
              <TextField
                type="number"
                size="small"
                label="SHAP sample rows"
                value={regenerateExplainabilitySampleRows}
                onChange={(e) => {
                  const v = Number(e.target.value)
                  if (!Number.isFinite(v)) return
                  onRegenerateExplainabilitySampleRowsChange?.(v)
                }}
                inputProps={{ min: 8, max: 50_000, step: 1 }}
                sx={{ width: 140 }}
              />
              <Button
                variant="outlined"
                size="small"
                disabled={regeneratingExplainabilityBackground}
                onClick={() => void onRegenerateExplainabilityBackground()}
              >
                {regeneratingExplainabilityBackground ? 'Regenerating…' : 'Regenerate reference sample'}
              </Button>
            </>
          )}
        </Stack>
        {isEdit && hasCog && sortedBands.length > 0 && onRegenerateExplainabilityBackground && (
          <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.75 }}>
            Rebuilds the SHAP background Parquet without replacing the raster above (also runs automatically on
            upload/replace).
          </Typography>
        )}
        {isEdit && explainabilityBackgroundPath && (
          <Paper variant="outlined" sx={{ mt: 1, py: 1, px: 1.25, bgcolor: 'action.hover' }}>
            <Typography variant="caption" color="text.secondary" component="div" sx={{ lineHeight: 1.5 }}>
              <Box component="span" sx={{ fontWeight: 600, color: 'text.primary' }}>
                SHAP background sample
              </Box>
              {' — '}
              {explainabilityBackgroundSampleRows != null ? (
                <>explainability uses a random sample of {explainabilityBackgroundSampleRows.toLocaleString()} rows</>
              ) : (
                <>row count not recorded (older catalog)</>
              )}
              {explainabilityBackgroundGeneratedAt ? (
                <>
                  {' · '}
                  generated {formatBackgroundGeneratedAt(explainabilityBackgroundGeneratedAt)}
                </>
              ) : (
                explainabilityBackgroundSampleRows != null && <> · generated time not recorded</>
              )}
            </Typography>
          </Paper>
        )}
        {regenerateExplainabilityError && (
          <Alert severity="error" sx={{ mt: 1, py: 0.5 }}>
            {regenerateExplainabilityError}
          </Alert>
        )}
        {isEdit && <FormHelperText sx={{ mx: 0, mt: 0.5 }}>{COG_REPLACE_HINT}</FormHelperText>}
      </Box>
      {isEdit && hasCog && sortedBands.length === 0 && (
        <Alert severity="info" variant="outlined" sx={{ py: 0.75 }}>
          Save the project once to generate default band names from the environmental raster, or upload/replace the
          file above first.
        </Alert>
      )}
      {isEdit && sortedBands.length > 0 && (
        <Box>
          <Typography variant="subtitle2" fontWeight={600} sx={{ mb: 1 }}>
            Environmental raster bands
          </Typography>
          <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1 }}>
            {onEnvironmentalBandDefinitionsChange ? (
              namesEditable ? (
                <>
                  Stable <strong>Band name</strong> values must match your training columns. <strong>Display name</strong>{' '}
                  and <strong>Description</strong> are optional and shown in the map UI.
                </>
              ) : (
                <>
                  <strong>Band name</strong> comes from the raster (or GDAL). Edit <strong>display name</strong> and{' '}
                  <strong>description</strong> for map users. Save the project to persist.
                </>
              )
            ) : (
              <>
                Names come from the environmental raster when you upload or replace it (GDAL band descriptions when
                present, otherwise <code>band_0</code> …). Reopen the dialog after save to refresh this list.
              </>
            )}
          </Typography>
          <Table size="small" sx={{ border: 1, borderColor: 'divider', borderRadius: 1 }}>
            <TableHead>
              <TableRow>
                <TableCell width={48}>#</TableCell>
                <TableCell sx={{ minWidth: 120 }}>Band name</TableCell>
                <TableCell sx={{ minWidth: 120 }}>Display name</TableCell>
                <TableCell sx={{ minWidth: 200 }}>Description</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {sortedBands.map((row) => (
                <TableRow key={row.index}>
                  <TableCell>{row.index}</TableCell>
                  <TableCell>
                    <TextField
                      size="small"
                      fullWidth
                      placeholder="e.g. band_0"
                      value={row.name}
                      disabled={!onEnvironmentalBandDefinitionsChange || !namesEditable}
                      onChange={(e) => updateBandRow(row.index, 'name', e.target.value)}
                    />
                  </TableCell>
                  <TableCell>
                    <TextField
                      size="small"
                      fullWidth
                      placeholder="Short label"
                      value={row.label ?? ''}
                      disabled={!onEnvironmentalBandDefinitionsChange}
                      onChange={(e) => updateBandRow(row.index, 'label', e.target.value)}
                    />
                  </TableCell>
                  <TableCell sx={{ verticalAlign: 'top' }}>
                    <TextField
                      size="small"
                      fullWidth
                      multiline
                      minRows={2}
                      maxRows={5}
                      placeholder="What this variable measures"
                      value={row.description ?? ''}
                      disabled={!onEnvironmentalBandDefinitionsChange}
                      onChange={(e) => updateBandRow(row.index, 'description', e.target.value)}
                    />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Box>
      )}
    </Stack>
  )
}
