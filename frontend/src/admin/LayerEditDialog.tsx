import { Alert, Box, Dialog, DialogContent, DialogTitle, Typography } from '@mui/material'
import type { Model } from '../types/model'
import type { CatalogProject, EnvironmentalBandDefinition } from '../types/project'
import type { ModelCardDraft } from './modelCardDraft'
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
  selectedEnvironmentalBands: EnvironmentalBandDefinition[]
  onSelectedEnvironmentalBandsChange: (bands: EnvironmentalBandDefinition[]) => void
  environmentalBandOptions: EnvironmentalBandDefinition[] | null
  editExplainabilityEnabled: boolean
  editExplainModelFile: File | null
  editExplainHasExistingArtifacts: boolean
  editFile: File | null
  onEditSpeciesChange: (v: string) => void
  onEditActivityChange: (v: string) => void
  onEditExplainabilityEnabledChange: (v: boolean) => void
  onEditExplainModelFileChange: (f: File | null) => void
  onEditFileChange: (f: File | null) => void
  editError: string | null
  savingEdit: boolean
  modelCardDraft: ModelCardDraft
  onModelCardDraftChange: (draft: ModelCardDraft) => void
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
  selectedEnvironmentalBands,
  onSelectedEnvironmentalBandsChange,
  environmentalBandOptions,
  editExplainabilityEnabled,
  editExplainModelFile,
  editExplainHasExistingArtifacts,
  editFile,
  onEditSpeciesChange,
  onEditActivityChange,
  onEditExplainabilityEnabledChange,
  onEditExplainModelFileChange,
  onEditFileChange,
  editError,
  savingEdit,
  modelCardDraft,
  onModelCardDraftChange,
}: LayerEditDialogProps) {
  return (
    <Dialog
      open={open}
      onClose={() => onClose()}
      fullWidth
      maxWidth="md"
      PaperProps={{ sx: { borderRadius: 2 } }}
    >
      <DialogTitle sx={{ fontWeight: 700 }}>
        Edit map layer
        <Typography variant="caption" component="span" display="block" color="text.secondary" fontWeight={400} sx={{ mt: 0.5 }}>
          {savingEdit ? 'Saving…' : 'Changes save automatically. Click outside to close.'}
        </Typography>
      </DialogTitle>
      <DialogContent sx={{ pb: 2 }}>
        <Box sx={{ width: '100%', maxWidth: formMaxWidth, mx: 'auto', mt: 0.5 }}>
          <MapLayerFormFields
            mode="edit"
            maxWidth={formMaxWidth}
            projectId={editProjectId}
            onProjectChange={onEditProjectIdChange}
            activeProjects={activeProjects}
            allowStandAloneProject
            species={editSpecies}
            activity={editActivity}
            onSpeciesChange={onEditSpeciesChange}
            onActivityChange={onEditActivityChange}
            selectedEnvironmentalBands={selectedEnvironmentalBands}
            onSelectedEnvironmentalBandsChange={onSelectedEnvironmentalBandsChange}
            environmentalBandOptions={environmentalBandOptions}
            explainabilityEnabled={editExplainabilityEnabled}
            onExplainabilityEnabledChange={onEditExplainabilityEnabledChange}
            explainModelFile={editExplainModelFile}
            onExplainModelFileChange={onEditExplainModelFileChange}
            explainHasExistingArtifacts={editExplainHasExistingArtifacts}
            pendingFile={editFile}
            onFileChange={onEditFileChange}
            layerId={editModel?.id}
            modelCardDraft={modelCardDraft}
            onModelCardDraftChange={onModelCardDraftChange}
            catalogCreatedAt={editModel?.created_at ?? null}
            catalogUpdatedAt={editModel?.updated_at ?? null}
          />
          {editError && (
            <Alert severity="error" sx={{ mt: 2 }}>
              {editError}
            </Alert>
          )}
        </Box>
      </DialogContent>
    </Dialog>
  )
}
