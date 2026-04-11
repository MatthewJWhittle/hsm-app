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
import { useEffect, useState } from 'react'

import type { CatalogProject, EnvironmentalBandDefinition } from '../types/project'
import type { ModelCardDraft } from './modelCardDraft'
import { bandsFromPasteTokens, tokenizeFeaturePaste } from './adminFeaturePaste'
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
  modelCardDraft?: ModelCardDraft
  onModelCardDraftChange?: (draft: ModelCardDraft) => void
  catalogCreatedAt?: string | null
  catalogUpdatedAt?: string | null
}

export function MapLayerFormFields({
  mode,
  maxWidth = 800,
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
  catalogCreatedAt,
  catalogUpdatedAt,
}: MapLayerFormFieldsProps) {
  const isEdit = mode === 'edit'
  const opts = environmentalBandOptions ?? []
  const showEnvSection = Boolean(projectId)
  const noManifest = showEnvSection && opts.length === 0

  const [pasteInput, setPasteInput] = useState('')
  const [pasteUnknown, setPasteUnknown] = useState<string[]>([])

  /** Reset paste text when switching layers or project (bands reloaded from parent). */
  useEffect(() => {
    setPasteInput(selectedEnvironmentalBands.map((b) => b.name).join(', '))
    setPasteUnknown([])
  }, [layerId, projectId])

  const applyPastedFeatures = () => {
    const tokens = tokenizeFeaturePaste(pasteInput)
    if (tokens.length === 0) {
      onSelectedEnvironmentalBandsChange([])
      setPasteUnknown([])
      return
    }
    const { matched, unknown } = bandsFromPasteTokens(tokens, opts)
    setPasteUnknown(unknown)
    onSelectedEnvironmentalBandsChange(matched)
  }

  const featureCount = selectedEnvironmentalBands.length
  const modelLabel = explainModelFile
    ? explainModelFile.name
    : explainabilityEnabled && explainHasExistingArtifacts
      ? 'Existing model on server'
      : ''

  return (
    <Stack
      spacing={2}
      sx={{
        width: '100%',
        maxWidth,
        mx: 'auto',
        opacity: disabled ? 0.55 : 1,
        pointerEvents: disabled ? 'none' : 'auto',
      }}
    >
      {isEdit && layerId && (
        <Typography variant="caption" color="text.secondary">
          Layer id:{' '}
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

      <Box>
        <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 0.5 }}>
          Suitability map (GeoTIFF COG)
        </Typography>
        <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1 }}>
          {FIELD_HELP.suitabilityCog}
        </Typography>
        <Stack direction="row" alignItems="center" spacing={1} flexWrap="wrap" useFlexGap>
          <Button variant="outlined" component="label" size="small" disabled={disabled}>
            {isEdit ? 'Replace suitability file…' : 'Choose suitability file…'}
            <input
              type="file"
              accept=".tif,.tiff,image/tiff"
              hidden
              onChange={(e) => onFileChange(e.target.files?.[0] ?? null)}
            />
          </Button>
          {!isEdit && (
            <Typography variant="body2" color="text.secondary" noWrap sx={{ maxWidth: 320 }}>
              {pendingFile ? pendingFile.name : 'No file selected'}
            </Typography>
          )}
        </Stack>
        {isEdit && pendingFile && (
          <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.5 }}>
            Pending: {pendingFile.name}
          </Typography>
        )}
        {isEdit && <FormHelperText sx={{ mx: 0, mt: 0.5 }}>{COG_REPLACE_HINT}</FormHelperText>}
      </Box>

      {modelCardDraft != null && onModelCardDraftChange != null && (
        <>
          <Divider sx={{ my: 0.5 }} />
          <ModelCardFormFields
            maxWidth={maxWidth}
            draft={modelCardDraft}
            onDraftChange={onModelCardDraftChange}
            disabled={disabled}
            species={species}
            activity={activity}
            onSpeciesChange={onSpeciesChange}
            onActivityChange={onActivityChange}
            catalogCreatedAt={catalogCreatedAt}
            catalogUpdatedAt={catalogUpdatedAt}
          />
        </>
      )}

      {showEnvSection && (
        <>
          <Divider sx={{ my: 0.5 }} />
          <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
            Variable influence (optional)
          </Typography>
          <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: -0.25 }}>
            {EXPLAINABILITY_HELP.toggle}
          </Typography>
          <FormControlLabel
            control={
              <Switch
                checked={explainabilityEnabled}
                onChange={(_e, v) => {
                  onExplainabilityEnabledChange(v)
                  if (!v) {
                    onSelectedEnvironmentalBandsChange([])
                    onExplainModelFileChange(null)
                  }
                }}
                disabled={disabled}
              />
            }
            label="Show which environmental variables drive suitability at clicked locations"
          />

          {explainabilityEnabled && (
            <>
              {noManifest ? (
                <Alert severity="warning" variant="outlined" sx={{ py: 0.75 }}>
                  This project has no environmental band definitions yet. Upload a shared environmental COG on the
                  project and save, then configure features here.
                </Alert>
              ) : (
                <>
                  <TextField
                    label="Feature names (paste comma-separated)"
                    value={pasteInput}
                    onChange={(e) => setPasteInput(e.target.value)}
                    size="small"
                    fullWidth
                    multiline
                    minRows={2}
                    disabled={disabled}
                    placeholder="e.g. band_0, band_1, temperature"
                    helperText="Paste or type band machine names in training order, same as Outlook separating emails—then Apply. Names must match this project’s environmental manifest."
                  />
                  <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
                    <Button variant="outlined" size="small" onClick={applyPastedFeatures} disabled={disabled}>
                      Apply pasted list
                    </Button>
                    {pasteUnknown.length > 0 && (
                      <Typography variant="caption" color="warning.main">
                        Unknown names (not applied): {pasteUnknown.join(', ')}
                      </Typography>
                    )}
                  </Stack>

                  <Autocomplete
                    multiple
                    disableCloseOnSelect
                    options={opts}
                    value={selectedEnvironmentalBands}
                    onChange={(_e, v) => {
                      onSelectedEnvironmentalBandsChange(v)
                      setPasteInput(v.map((b) => b.name).join(', '))
                      setPasteUnknown([])
                    }}
                    getOptionLabel={(o) => (o.label?.trim() ? `${o.name} (${o.label})` : o.name)}
                    isOptionEqualToValue={(a, b) => a.index === b.index}
                    renderInput={(params) => (
                      <TextField
                        {...params}
                        size="small"
                        label="Or pick features (chips preserve order)"
                        helperText="Order = column order for your trained model and SHAP."
                      />
                    )}
                  />

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
                      <Typography variant="body2" color="text.secondary" noWrap sx={{ maxWidth: 280 }}>
                        {explainModelFile
                          ? explainModelFile.name
                          : isEdit && explainHasExistingArtifacts
                            ? 'Using file already on server'
                            : 'Required for new setup'}
                      </Typography>
                    </Stack>
                    <FormHelperText sx={{ mx: 0, mt: 0.5 }}>{EXPLAINABILITY_HELP.modelFile}</FormHelperText>
                  </Box>

                  {isEdit && explainHasExistingArtifacts && (
                    <Alert severity="info" variant="outlined" sx={{ py: 0.75 }}>
                      A .pkl is already stored. Leave the file control empty to keep it, or choose a new file to replace
                      it.
                    </Alert>
                  )}

                  <Typography variant="body2" color="text.secondary">
                    {featureCount} feature{featureCount === 1 ? '' : 's'} selected
                    {modelLabel ? ` · ${modelLabel}` : ''}
                  </Typography>
                </>
              )}
              <Typography variant="caption" color="text.secondary" display="block" sx={{ pl: { sm: 0.25 } }}>
                {EXPLAINABILITY_HELP.backgroundNote}
              </Typography>
            </>
          )}
        </>
      )}
    </Stack>
  )
}
