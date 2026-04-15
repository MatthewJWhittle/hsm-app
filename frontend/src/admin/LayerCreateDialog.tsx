import { Alert, Box, Button, Dialog, DialogActions, DialogContent, DialogTitle, Typography } from '@mui/material'
import type { CatalogProject, EnvironmentalBandDefinition } from '../types/project'
import type { ModelCardDraft } from './modelCardDraft'
import { COG_REQUIREMENTS_INFO } from './catalogFormConstants'
import { MapLayerFormFields } from './MapLayerFormFields'

const FORM_ID = 'admin-new-layer-form'

type LayerCreateDialogProps = {
  open: boolean
  onClose: () => void
  formMaxWidth: number
  canAddModel: boolean
  creating: boolean
  createError: string | null
  layerUploadStatus: string | null
  onSubmit: (e: React.FormEvent) => void
  modelProjectId: string
  onModelProjectIdChange: (id: string) => void
  activeProjects: CatalogProject[]
  species: string
  activity: string
  selectedEnvironmentalBands: EnvironmentalBandDefinition[]
  onSelectedEnvironmentalBandsChange: (bands: EnvironmentalBandDefinition[]) => void
  environmentalBandOptions: EnvironmentalBandDefinition[] | null
  explainabilityEnabled: boolean
  explainModelFile: File | null
  file: File | null
  onSpeciesChange: (v: string) => void
  onActivityChange: (v: string) => void
  onExplainabilityEnabledChange: (v: boolean) => void
  onExplainModelFileChange: (f: File | null) => void
  onFileChange: (f: File | null) => void
  modelCardDraft: ModelCardDraft
  onModelCardDraftChange: (draft: ModelCardDraft) => void
}

export function LayerCreateDialog({
  open,
  onClose,
  formMaxWidth,
  canAddModel,
  creating,
  createError,
  layerUploadStatus,
  onSubmit,
  modelProjectId,
  onModelProjectIdChange,
  activeProjects,
  species,
  activity,
  selectedEnvironmentalBands,
  onSelectedEnvironmentalBandsChange,
  environmentalBandOptions,
  explainabilityEnabled,
  explainModelFile,
  file,
  onSpeciesChange,
  onActivityChange,
  onExplainabilityEnabledChange,
  onExplainModelFileChange,
  onFileChange,
  modelCardDraft,
  onModelCardDraftChange,
}: LayerCreateDialogProps) {
  const missingReason = !canAddModel
    ? 'Create at least one active project first.'
    : !modelProjectId
      ? 'Select a project.'
      : !species.trim() || !activity.trim()
        ? 'Enter species and activity.'
        : !file
          ? 'Choose a suitability file.'
          : null

  return (
    <Dialog
      open={open}
      onClose={() => {
        if (creating) return
        onClose()
      }}
      fullWidth
      maxWidth="md"
      PaperProps={{ sx: { borderRadius: 2 } }}
    >
      <DialogTitle sx={{ fontWeight: 700 }}>New map layer</DialogTitle>
      <DialogContent>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2, mt: 0.5 }}>
          One layer is one suitability raster for a species and activity, linked to a project.
        </Typography>
        {!canAddModel && (
          <Alert severity="warning" sx={{ mb: 2, maxWidth: formMaxWidth }}>
            Create at least one active project in the <strong>Projects</strong> tab first.
          </Alert>
        )}
        <Alert severity="info" variant="outlined" sx={{ mb: 2, maxWidth: formMaxWidth }}>
          {COG_REQUIREMENTS_INFO}
        </Alert>
        <Box component="form" id={FORM_ID} onSubmit={onSubmit} noValidate sx={{ width: '100%', maxWidth: formMaxWidth, mx: 'auto' }}>
          <MapLayerFormFields
            mode="create"
            maxWidth={formMaxWidth}
            projectId={modelProjectId}
            onProjectChange={onModelProjectIdChange}
            activeProjects={activeProjects}
            allowStandAloneProject={false}
            species={species}
            activity={activity}
            onSpeciesChange={onSpeciesChange}
            onActivityChange={onActivityChange}
            selectedEnvironmentalBands={selectedEnvironmentalBands}
            onSelectedEnvironmentalBandsChange={onSelectedEnvironmentalBandsChange}
            environmentalBandOptions={environmentalBandOptions}
            explainabilityEnabled={explainabilityEnabled}
            onExplainabilityEnabledChange={onExplainabilityEnabledChange}
            explainModelFile={explainModelFile}
            onExplainModelFileChange={onExplainModelFileChange}
            pendingFile={file}
            onFileChange={onFileChange}
            disabled={!canAddModel}
            modelCardDraft={modelCardDraft}
            onModelCardDraftChange={onModelCardDraftChange}
          />
          {createError && (
            <Alert severity="error" sx={{ mt: 2, maxWidth: formMaxWidth }}>
              {createError}
            </Alert>
          )}
          {layerUploadStatus && (
            <Alert severity="info" sx={{ mt: 2, maxWidth: formMaxWidth }}>
              {layerUploadStatus}
            </Alert>
          )}
        </Box>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button
          onClick={() => {
            if (creating) return
            onClose()
          }}
          disabled={creating}
        >
          Cancel
        </Button>
        <Button type="submit" form={FORM_ID} variant="contained" disabled={creating || missingReason !== null}>
          {creating ? 'Creating…' : 'Create layer'}
        </Button>
      </DialogActions>
      {missingReason && (
        <Typography variant="caption" color="text.secondary" sx={{ px: 3, pb: 2, display: 'block' }}>
          {missingReason}
        </Typography>
      )}
    </Dialog>
  )
}
