import {
  Alert,
  Box,
  Button,
  FormControl,
  FormHelperText,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
} from '@mui/material'

import { DRIVER_COG_INFO, COG_REPLACE_HINT } from './catalogFormConstants'

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
  /** Edit: full id for display */
  projectId?: string
  /** Edit: existing stored path, if any */
  existingDriverPath?: string | null
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
  projectId,
  existingDriverPath,
}: ProjectFormFieldsProps) {
  const isEdit = mode === 'edit'

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
        </Stack>
        {isEdit && <FormHelperText sx={{ mx: 0, mt: 0.5 }}>{COG_REPLACE_HINT}</FormHelperText>}
      </Box>
    </Stack>
  )
}
