import { Alert, Box, Button, Dialog, DialogActions, DialogContent, DialogTitle, Typography } from '@mui/material'
import type { CatalogProject } from '../types/project'
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
  onSubmit: (e: React.FormEvent) => void
  modelProjectId: string
  onModelProjectIdChange: (id: string) => void
  activeProjects: CatalogProject[]
  species: string
  activity: string
  modelName: string
  modelVersion: string
  driverBandIndices: string
  bandLabelsCsv: string
  explainabilityEnabled: boolean
  explainFeatureNamesCsv: string
  explainModelFile: File | null
  explainBackgroundFile: File | null
  file: File | null
  onSpeciesChange: (v: string) => void
  onActivityChange: (v: string) => void
  onModelNameChange: (v: string) => void
  onModelVersionChange: (v: string) => void
  onDriverBandIndicesChange: (v: string) => void
  onBandLabelsCsvChange: (v: string) => void
  onExplainabilityEnabledChange: (v: boolean) => void
  onExplainFeatureNamesCsvChange: (v: string) => void
  onExplainModelFileChange: (f: File | null) => void
  onExplainBackgroundFileChange: (f: File | null) => void
  onFileChange: (f: File | null) => void
}

export function LayerCreateDialog({
  open,
  onClose,
  formMaxWidth,
  canAddModel,
  creating,
  createError,
  onSubmit,
  modelProjectId,
  onModelProjectIdChange,
  activeProjects,
  species,
  activity,
  modelName,
  modelVersion,
  driverBandIndices,
  bandLabelsCsv,
  explainabilityEnabled,
  explainFeatureNamesCsv,
  explainModelFile,
  explainBackgroundFile,
  file,
  onSpeciesChange,
  onActivityChange,
  onModelNameChange,
  onModelVersionChange,
  onDriverBandIndicesChange,
  onBandLabelsCsvChange,
  onExplainabilityEnabledChange,
  onExplainFeatureNamesCsvChange,
  onExplainModelFileChange,
  onExplainBackgroundFileChange,
  onFileChange,
}: LayerCreateDialogProps) {
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
        <Box component="form" id={FORM_ID} onSubmit={onSubmit}>
          <MapLayerFormFields
            mode="create"
            maxWidth={formMaxWidth}
            projectId={modelProjectId}
            onProjectChange={onModelProjectIdChange}
            activeProjects={activeProjects}
            allowStandAloneProject={false}
            species={species}
            activity={activity}
            modelName={modelName}
            modelVersion={modelVersion}
            driverBandIndices={driverBandIndices}
            bandLabelsCsv={bandLabelsCsv}
            onBandLabelsCsvChange={onBandLabelsCsvChange}
            explainabilityEnabled={explainabilityEnabled}
            onExplainabilityEnabledChange={onExplainabilityEnabledChange}
            explainFeatureNamesCsv={explainFeatureNamesCsv}
            onExplainFeatureNamesCsvChange={onExplainFeatureNamesCsvChange}
            explainModelFile={explainModelFile}
            explainBackgroundFile={explainBackgroundFile}
            onExplainModelFileChange={onExplainModelFileChange}
            onExplainBackgroundFileChange={onExplainBackgroundFileChange}
            onSpeciesChange={onSpeciesChange}
            onActivityChange={onActivityChange}
            onModelNameChange={onModelNameChange}
            onModelVersionChange={onModelVersionChange}
            onDriverBandIndicesChange={onDriverBandIndicesChange}
            pendingFile={file}
            onFileChange={onFileChange}
            disabled={!canAddModel}
          />
          {createError && (
            <Alert severity="error" sx={{ mt: 2, maxWidth: formMaxWidth }}>
              {createError}
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
        <Button type="submit" form={FORM_ID} variant="contained" disabled={creating || !canAddModel}>
          {creating ? 'Creating…' : 'Create layer'}
        </Button>
      </DialogActions>
    </Dialog>
  )
}
