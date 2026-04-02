import {
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

import type { CatalogProject } from '../types/project'
import { COG_REPLACE_HINT, FIELD_HELP } from './catalogFormConstants'

export interface MapLayerFormFieldsProps {
  mode: 'create' | 'edit'
  maxWidth?: number
  projectId: string
  onProjectChange: (value: string) => void
  activeProjects: CatalogProject[]
  /** When true, include empty value = stand-alone (edit only). */
  allowStandAloneProject: boolean
  species: string
  activity: string
  modelName: string
  modelVersion: string
  driverBandIndices: string
  onSpeciesChange: (value: string) => void
  onActivityChange: (value: string) => void
  onModelNameChange: (value: string) => void
  onModelVersionChange: (value: string) => void
  onDriverBandIndicesChange: (value: string) => void
  pendingFile: File | null
  onFileChange: (file: File | null) => void
  /** Create: disable entire form when no projects */
  disabled?: boolean
  /** Edit: show layer id */
  layerId?: string
}

const BANDS_HELPER_CREATE =
  'Which bands from the project’s environmental file this layer uses. Example: [0,1,2]'
const BANDS_HELPER_EDIT =
  'Which bands from the project’s environmental file this layer uses. Example: [0,1,2]. Leave empty if not used.'

export function MapLayerFormFields({
  mode,
  maxWidth = 640,
  projectId,
  onProjectChange,
  activeProjects,
  allowStandAloneProject,
  species,
  activity,
  modelName,
  modelVersion,
  driverBandIndices,
  onSpeciesChange,
  onActivityChange,
  onModelNameChange,
  onModelVersionChange,
  onDriverBandIndicesChange,
  pendingFile,
  onFileChange,
  disabled = false,
  layerId,
}: MapLayerFormFieldsProps) {
  const isEdit = mode === 'edit'

  return (
    <Stack spacing={2} sx={{ maxWidth, opacity: disabled ? 0.55 : 1, pointerEvents: disabled ? 'none' : 'auto' }}>
      {isEdit && layerId && (
        <Typography variant="caption" color="text.secondary">
          ID:{' '}
          <Box component="span" sx={{ fontFamily: 'monospace', userSelect: 'all' }}>
            {layerId}
          </Box>
        </Typography>
      )}
      <FormControl required={!isEdit} size="small" fullWidth disabled={disabled}>
        <InputLabel>Project</InputLabel>
        <Select
          value={projectId}
          label="Project"
          onChange={(e) => onProjectChange(e.target.value)}
        >
          {allowStandAloneProject && (
            <MenuItem value="">
              <em>Stand-alone layer</em>
            </MenuItem>
          )}
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
          onChange={(e) => onSpeciesChange(e.target.value)}
          size="small"
          fullWidth
          disabled={disabled}
        />
        <TextField
          required
          label="Activity"
          helperText={FIELD_HELP.activity}
          value={activity}
          onChange={(e) => onActivityChange(e.target.value)}
          size="small"
          fullWidth
          disabled={disabled}
        />
      </Stack>
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
        <TextField
          label="Model name"
          helperText={FIELD_HELP.modelName}
          value={modelName}
          onChange={(e) => onModelNameChange(e.target.value)}
          size="small"
          fullWidth
          disabled={disabled}
        />
        <TextField
          label="Model version"
          helperText={FIELD_HELP.modelVersion}
          value={modelVersion}
          onChange={(e) => onModelVersionChange(e.target.value)}
          size="small"
          fullWidth
          disabled={disabled}
        />
      </Stack>
      <TextField
        label="Environmental bands (optional)"
        helperText={isEdit ? BANDS_HELPER_EDIT : BANDS_HELPER_CREATE}
        value={driverBandIndices}
        onChange={(e) => onDriverBandIndicesChange(e.target.value)}
        size="small"
        fullWidth
        disabled={disabled}
      />
      <Box>
        <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 0.75 }}>
          {isEdit ? 'Replace map file (optional)' : 'Suitability map file (required)'}
        </Typography>
        <Stack direction="row" alignItems="center" spacing={1} flexWrap="wrap" useFlexGap>
          <Button variant="outlined" component="label" size="small" disabled={disabled}>
            Choose file
            <input
              type="file"
              accept=".tif,.tiff,image/tiff"
              hidden
              onChange={(e) => onFileChange(e.target.files?.[0] ?? null)}
            />
          </Button>
          {!isEdit && (
            <Typography variant="body2" color="text.secondary" noWrap sx={{ maxWidth: 280 }}>
              {pendingFile ? pendingFile.name : 'No file selected'}
            </Typography>
          )}
        </Stack>
        {isEdit && pendingFile && (
          <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.5 }}>
            {pendingFile.name}
          </Typography>
        )}
        {isEdit && <FormHelperText sx={{ mx: 0, mt: 0.5 }}>{COG_REPLACE_HINT}</FormHelperText>}
      </Box>
    </Stack>
  )
}
