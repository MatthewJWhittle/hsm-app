import {
  Alert,
  Autocomplete,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  FormControl,
  FormHelperText,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
} from '@mui/material'
import { useEffect, useState } from 'react'

import type { CatalogProject, EnvironmentalBandDefinition } from '../types/project'
import type { ModelCardDraft } from './modelCardDraft'
import { COG_REPLACE_HINT, EXPLAINABILITY_HELP, FIELD_HELP } from './catalogFormConstants'
import { ModelCardFormFields } from './ModelCardFormFields'

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
  onSpeciesChange: (value: string) => void
  onActivityChange: (value: string) => void
  /** Ordered selection from the project manifest (feature order for the model). */
  selectedEnvironmentalBands: EnvironmentalBandDefinition[]
  onSelectedEnvironmentalBandsChange: (value: EnvironmentalBandDefinition[]) => void
  /** Bands available for the current project (null = none / not loaded). */
  environmentalBandOptions: EnvironmentalBandDefinition[] | null
  explainabilityEnabled: boolean
  onExplainabilityEnabledChange: (value: boolean) => void
  explainModelFile: File | null
  onExplainModelFileChange: (file: File | null) => void
  /** Edit: artefacts already saved under this layer’s folder */
  explainHasExistingArtifacts?: boolean
  pendingFile: File | null
  onFileChange: (file: File | null) => void
  /** Create: disable entire form when no projects */
  disabled?: boolean
  /** Edit: show layer id */
  layerId?: string
  /** Optional model card (metadata.card / extras); when set, shows the card editor. */
  modelCardDraft?: ModelCardDraft
  onModelCardDraftChange?: (draft: ModelCardDraft) => void
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
  onSpeciesChange,
  onActivityChange,
  selectedEnvironmentalBands,
  onSelectedEnvironmentalBandsChange,
  environmentalBandOptions,
  explainabilityEnabled,
  onExplainabilityEnabledChange,
  explainModelFile,
  onExplainModelFileChange,
  explainHasExistingArtifacts = false,
  pendingFile,
  onFileChange,
  disabled = false,
  layerId,
  modelCardDraft,
  onModelCardDraftChange,
}: MapLayerFormFieldsProps) {
  const isEdit = mode === 'edit'
  const opts = environmentalBandOptions ?? []
  const showEnvSection = Boolean(projectId)
  const noManifest = showEnvSection && opts.length === 0

  const [influenceDialogOpen, setInfluenceDialogOpen] = useState(false)
  const [draftBands, setDraftBands] = useState<EnvironmentalBandDefinition[]>([])
  const [draftFile, setDraftFile] = useState<File | null>(null)
  const [dialogError, setDialogError] = useState<string | null>(null)

  useEffect(() => {
    if (!influenceDialogOpen) return
    setDraftBands(selectedEnvironmentalBands)
    setDraftFile(explainModelFile)
    setDialogError(null)
  }, [influenceDialogOpen, selectedEnvironmentalBands, explainModelFile])

  const handleApplyInfluence = () => {
    if (draftBands.length === 0) {
      setDialogError('Select at least one environmental variable in model feature order.')
      return
    }
    if (!draftFile && !explainHasExistingArtifacts) {
      setDialogError(
        'Choose a trained model (.pkl). The reference sample is generated from the project environmental COG.',
      )
      return
    }
    onSelectedEnvironmentalBandsChange(draftBands)
    onExplainModelFileChange(draftFile)
    onExplainabilityEnabledChange(true)
    setInfluenceDialogOpen(false)
  }

  const handleRemoveInfluence = () => {
    onSelectedEnvironmentalBandsChange([])
    onExplainModelFileChange(null)
    onExplainabilityEnabledChange(false)
  }

  const featureCount = selectedEnvironmentalBands.length
  const modelLabel = explainModelFile
    ? explainModelFile.name
    : explainabilityEnabled && explainHasExistingArtifacts
      ? 'Existing model on server'
      : ''

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

      {modelCardDraft != null && onModelCardDraftChange != null && (
        <>
          <Divider sx={{ my: 0.5 }} />
          <ModelCardFormFields
            maxWidth={maxWidth}
            draft={modelCardDraft}
            onDraftChange={onModelCardDraftChange}
            disabled={disabled}
          />
        </>
      )}

      {showEnvSection && (
        <>
          <Divider sx={{ my: 0.5 }} />
          <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
            Variable influence (optional)
          </Typography>
          <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: -0.5 }}>
            {EXPLAINABILITY_HELP.toggle}
          </Typography>
          {noManifest ? (
            <Alert severity="warning" variant="outlined" sx={{ py: 0.75 }}>
              This project has no environmental band definitions yet. Upload a shared environmental COG on the project
              and save, then you can upload an explainability model here.
            </Alert>
          ) : explainabilityEnabled ? (
            <Stack spacing={1} sx={{ alignItems: 'flex-start' }}>
              <Typography variant="body2" color="text.secondary">
                {featureCount} feature{featureCount === 1 ? '' : 's'}
                {modelLabel ? ` · ${modelLabel}` : ''}
              </Typography>
              <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                <Button
                  variant="outlined"
                  size="small"
                  disabled={disabled}
                  onClick={() => setInfluenceDialogOpen(true)}
                >
                  Change model or features…
                </Button>
                <Button size="small" disabled={disabled} onClick={handleRemoveInfluence}>
                  Remove
                </Button>
              </Stack>
            </Stack>
          ) : (
            <Button
              variant="outlined"
              size="small"
              disabled={disabled}
              onClick={() => setInfluenceDialogOpen(true)}
            >
              Upload model for variable influence…
            </Button>
          )}
          <Typography variant="caption" color="text.secondary" display="block" sx={{ pl: { sm: 0.25 } }}>
            {EXPLAINABILITY_HELP.backgroundNote}
          </Typography>
        </>
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

      <Dialog
        open={influenceDialogOpen}
        onClose={() => setInfluenceDialogOpen(false)}
        fullWidth
        maxWidth="sm"
        scroll="paper"
        PaperProps={{ sx: { borderRadius: 2 } }}
      >
        <DialogTitle sx={{ fontWeight: 700 }}>Variable influence model</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Select environmental variables in the same order as your trained model, then upload the pickled estimator
            (.pkl).
          </Typography>
          {noManifest ? (
            <Alert severity="warning" sx={{ mb: 2 }}>
              This project has no band manifest yet. Configure the project’s environmental COG first.
            </Alert>
          ) : (
            <Autocomplete
              multiple
              disableCloseOnSelect
              options={opts}
              value={draftBands}
              onChange={(_e, v) => setDraftBands(v)}
              getOptionLabel={(o) => (o.label?.trim() ? `${o.name} (${o.label})` : o.name)}
              isOptionEqualToValue={(a, b) => a.index === b.index}
              sx={{ mb: 2 }}
              renderInput={(params) => (
                <TextField
                  {...params}
                  size="small"
                  label="Environmental variables (features)"
                  helperText="Order of chips = column order for training / explainability."
                />
              )}
            />
          )}
          {isEdit && explainHasExistingArtifacts && (
            <Alert severity="info" variant="outlined" sx={{ mb: 2, py: 0.75 }}>
              A trained model is already stored for this layer. Leave the file field empty to keep it, or choose a new
              .pkl to replace it.
            </Alert>
          )}
          <Box>
            <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 0.75 }}>
              Trained model (.pkl)
            </Typography>
            <Stack direction="row" alignItems="center" spacing={1} flexWrap="wrap" useFlexGap>
              <Button variant="outlined" component="label" size="small">
                Choose file
                <input
                  type="file"
                  accept=".pkl,.pickle,application/octet-stream"
                  hidden
                  onChange={(e) => setDraftFile(e.target.files?.[0] ?? null)}
                />
              </Button>
              <Typography variant="body2" color="text.secondary" noWrap sx={{ maxWidth: 240 }}>
                {draftFile ? draftFile.name : isEdit && explainHasExistingArtifacts ? 'Keep existing' : 'Required'}
              </Typography>
            </Stack>
            <FormHelperText sx={{ mx: 0, mt: 0.5 }}>{EXPLAINABILITY_HELP.modelFile}</FormHelperText>
          </Box>
          {dialogError && (
            <Alert severity="error" sx={{ mt: 2 }}>
              {dialogError}
            </Alert>
          )}
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setInfluenceDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleApplyInfluence} disabled={noManifest}>
            Save
          </Button>
        </DialogActions>
      </Dialog>
    </Stack>
  )
}
