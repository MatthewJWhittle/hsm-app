import {
  Alert,
  Autocomplete,
  Box,
  Button,
  Divider,
  FormControl,
  FormControlLabel,
  FormHelperText,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  Switch,
  TextField,
  Typography,
} from '@mui/material'

import type { CatalogProject } from '../types/project'
import type { EnvironmentalBandDefinition } from '../types/project'
import { COG_REPLACE_HINT, EXPLAINABILITY_HELP, FIELD_HELP } from './catalogFormConstants'

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
  onSpeciesChange: (value: string) => void
  onActivityChange: (value: string) => void
  onModelNameChange: (value: string) => void
  onModelVersionChange: (value: string) => void
  /** Ordered selection from the project manifest (feature order for the model). */
  selectedEnvironmentalBands: EnvironmentalBandDefinition[]
  onSelectedEnvironmentalBandsChange: (value: EnvironmentalBandDefinition[]) => void
  /** Bands available for the current project (null = none / not loaded). */
  environmentalBandOptions: EnvironmentalBandDefinition[] | null
  explainabilityEnabled: boolean
  onExplainabilityEnabledChange: (value: boolean) => void
  explainModelFile: File | null
  explainBackgroundFile: File | null
  onExplainModelFileChange: (file: File | null) => void
  onExplainBackgroundFileChange: (file: File | null) => void
  /** Edit: artefacts already saved under this layer’s folder */
  explainHasExistingArtifacts?: boolean
  pendingFile: File | null
  onFileChange: (file: File | null) => void
  /** Create: disable entire form when no projects */
  disabled?: boolean
  /** Edit: show layer id */
  layerId?: string
}

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
  onSpeciesChange,
  onActivityChange,
  onModelNameChange,
  onModelVersionChange,
  selectedEnvironmentalBands,
  onSelectedEnvironmentalBandsChange,
  environmentalBandOptions,
  explainabilityEnabled,
  onExplainabilityEnabledChange,
  explainModelFile,
  explainBackgroundFile,
  onExplainModelFileChange,
  onExplainBackgroundFileChange,
  explainHasExistingArtifacts = false,
  pendingFile,
  onFileChange,
  disabled = false,
  layerId,
}: MapLayerFormFieldsProps) {
  const isEdit = mode === 'edit'
  const opts = environmentalBandOptions ?? []
  const showEnvPicker = Boolean(projectId) && !allowStandAloneProject
  const noManifest = showEnvPicker && projectId && opts.length === 0

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
      {showEnvPicker && (
        <>
          {noManifest ? (
            <Alert severity="warning" variant="outlined" sx={{ py: 0.75 }}>
              This project has no environmental band definitions yet. Upload a shared environmental COG on the
              project and save, then edit band names if needed.
            </Alert>
          ) : (
            <Autocomplete
              multiple
              disableCloseOnSelect
              options={opts}
              value={selectedEnvironmentalBands}
              onChange={(_e, v) => onSelectedEnvironmentalBandsChange(v)}
              getOptionLabel={(o) => (o.label?.trim() ? `${o.name} (${o.label})` : o.name)}
              isOptionEqualToValue={(a, b) => a.index === b.index}
              disabled={disabled}
              renderInput={(params) => (
                <TextField
                  {...params}
                  size="small"
                  label="Environmental variables"
                  helperText="Select in model feature order (order of chips = column order for training / explainability)."
                />
              )}
            />
          )}
        </>
      )}
      <Divider sx={{ my: 0.5 }} />
      <FormControlLabel
        control={
          <Switch
            checked={explainabilityEnabled}
            onChange={(_e, v) => onExplainabilityEnabledChange(v)}
            disabled={disabled}
          />
        }
        label="Variable influence explanations"
      />
      <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: -1, mb: 0.5 }}>
        {EXPLAINABILITY_HELP.toggle}
      </Typography>
      {explainabilityEnabled && (
        <Stack spacing={2} sx={{ pl: { sm: 0.5 } }}>
          {isEdit && explainHasExistingArtifacts && (
            <Alert severity="info" variant="outlined" sx={{ py: 0.5 }}>
              Trained model and background sample are already stored for this layer. Upload new files below to
              replace them.
            </Alert>
          )}
          <Box>
            <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 0.75 }}>
              Trained model (.pkl)
            </Typography>
            <Stack direction="row" alignItems="center" spacing={1} flexWrap="wrap" useFlexGap>
              <Button variant="outlined" component="label" size="small" disabled={disabled}>
                Choose file
                <input
                  type="file"
                  accept=".pkl,.pickle,application/octet-stream"
                  hidden
                  onChange={(e) => onExplainModelFileChange(e.target.files?.[0] ?? null)}
                />
              </Button>
              <Typography variant="body2" color="text.secondary" noWrap sx={{ maxWidth: 220 }}>
                {explainModelFile ? explainModelFile.name : isEdit ? 'Keep existing or choose…' : 'Required on create'}
              </Typography>
            </Stack>
            <FormHelperText sx={{ mx: 0, mt: 0.5 }}>{EXPLAINABILITY_HELP.modelFile}</FormHelperText>
          </Box>
          <Box>
            <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 0.75 }}>
              Reference sample (.parquet)
            </Typography>
            <Stack direction="row" alignItems="center" spacing={1} flexWrap="wrap" useFlexGap>
              <Button variant="outlined" component="label" size="small" disabled={disabled}>
                Choose file
                <input
                  type="file"
                  accept=".parquet,application/octet-stream"
                  hidden
                  onChange={(e) => onExplainBackgroundFileChange(e.target.files?.[0] ?? null)}
                />
              </Button>
              <Typography variant="body2" color="text.secondary" noWrap sx={{ maxWidth: 220 }}>
                {explainBackgroundFile
                  ? explainBackgroundFile.name
                  : isEdit
                    ? 'Keep existing or choose…'
                    : 'Required on create'}
              </Typography>
            </Stack>
            <FormHelperText sx={{ mx: 0, mt: 0.5 }}>{EXPLAINABILITY_HELP.backgroundFile}</FormHelperText>
          </Box>
        </Stack>
      )}
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
