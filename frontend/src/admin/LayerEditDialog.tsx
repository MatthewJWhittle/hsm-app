import { Alert, Box, Button, Dialog, DialogActions, DialogContent, DialogTitle } from '@mui/material'
import type { Model } from '../types/model'
import type { CatalogProject } from '../types/project'
import { MapLayerFormFields } from './MapLayerFormFields'

type LayerEditDialogProps = {
  open: boolean
  onClose: () => void
  formMaxWidth: number
  editModel: Model | null
  activeProjects: CatalogProject[]
  editProjectId: string
  onEditProjectIdChange: (id: string) => void
  editSpecies: string
  editActivity: string
  editName: string
  editVersion: string
  editDriverBandIndices: string
  editBandLabelsCsv: string
  editExplainabilityEnabled: boolean
  editExplainFeatureNamesCsv: string
  editExplainModelFile: File | null
  editExplainBackgroundFile: File | null
  editExplainHasExistingArtifacts: boolean
  editFile: File | null
  onEditSpeciesChange: (v: string) => void
  onEditActivityChange: (v: string) => void
  onEditNameChange: (v: string) => void
  onEditVersionChange: (v: string) => void
  onEditDriverBandIndicesChange: (v: string) => void
  onEditBandLabelsCsvChange: (v: string) => void
  onEditExplainabilityEnabledChange: (v: boolean) => void
  onEditExplainFeatureNamesCsvChange: (v: string) => void
  onEditExplainModelFileChange: (f: File | null) => void
  onEditExplainBackgroundFileChange: (f: File | null) => void
  onEditFileChange: (f: File | null) => void
  editError: string | null
  savingEdit: boolean
  onSave: () => void
}

export function LayerEditDialog({
  open,
  onClose,
  formMaxWidth,
  editModel,
  activeProjects,
  editProjectId,
  onEditProjectIdChange,
  editSpecies,
  editActivity,
  editName,
  editVersion,
  editDriverBandIndices,
  editBandLabelsCsv,
  editExplainabilityEnabled,
  editExplainFeatureNamesCsv,
  editExplainModelFile,
  editExplainBackgroundFile,
  editExplainHasExistingArtifacts,
  editFile,
  onEditSpeciesChange,
  onEditActivityChange,
  onEditNameChange,
  onEditVersionChange,
  onEditDriverBandIndicesChange,
  onEditBandLabelsCsvChange,
  onEditExplainabilityEnabledChange,
  onEditExplainFeatureNamesCsvChange,
  onEditExplainModelFileChange,
  onEditExplainBackgroundFileChange,
  onEditFileChange,
  editError,
  savingEdit,
  onSave,
}: LayerEditDialogProps) {
  return (
    <Dialog
      open={open}
      onClose={() => onClose()}
      fullWidth
      maxWidth="md"
      PaperProps={{ sx: { borderRadius: 2 } }}
    >
      <DialogTitle sx={{ fontWeight: 700 }}>Edit map layer</DialogTitle>
      <DialogContent>
        <Box sx={{ mt: 0.5 }}>
          <MapLayerFormFields
            mode="edit"
            maxWidth={formMaxWidth}
            projectId={editProjectId}
            onProjectChange={onEditProjectIdChange}
            activeProjects={activeProjects}
            allowStandAloneProject
            species={editSpecies}
            activity={editActivity}
            modelName={editName}
            modelVersion={editVersion}
            driverBandIndices={editDriverBandIndices}
            bandLabelsCsv={editBandLabelsCsv}
            onBandLabelsCsvChange={onEditBandLabelsCsvChange}
            explainabilityEnabled={editExplainabilityEnabled}
            onExplainabilityEnabledChange={onEditExplainabilityEnabledChange}
            explainFeatureNamesCsv={editExplainFeatureNamesCsv}
            onExplainFeatureNamesCsvChange={onEditExplainFeatureNamesCsvChange}
            explainModelFile={editExplainModelFile}
            explainBackgroundFile={editExplainBackgroundFile}
            onExplainModelFileChange={onEditExplainModelFileChange}
            onExplainBackgroundFileChange={onEditExplainBackgroundFileChange}
            explainHasExistingArtifacts={editExplainHasExistingArtifacts}
            onSpeciesChange={onEditSpeciesChange}
            onActivityChange={onEditActivityChange}
            onModelNameChange={onEditNameChange}
            onModelVersionChange={onEditVersionChange}
            onDriverBandIndicesChange={onEditDriverBandIndicesChange}
            pendingFile={editFile}
            onFileChange={onEditFileChange}
            layerId={editModel?.id}
          />
          {editError && (
            <Alert severity="error" sx={{ mt: 2 }}>
              {editError}
            </Alert>
          )}
        </Box>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={() => onClose()}>Cancel</Button>
        <Button variant="contained" onClick={() => void onSave()} disabled={savingEdit}>
          {savingEdit ? 'Saving…' : 'Save'}
        </Button>
      </DialogActions>
    </Dialog>
  )
}
