import { Alert, Box, Dialog, DialogContent, DialogTitle, Typography } from '@mui/material'
import type { CatalogProject, EnvironmentalBandDefinition } from '../types/project'
import { ProjectFormFields } from './ProjectFormFields'

type ProjectEditDialogProps = {
  open: boolean
  onClose: () => void
  formMaxWidth: number
  editingProject: CatalogProject | null
  editProjName: string
  editProjDesc: string
  editProjVisibility: 'public' | 'private'
  editProjAllowedUids: string
  editProjStatus: 'active' | 'archived'
  editProjFile: File | null
  environmentalBandDefinitions: EnvironmentalBandDefinition[]
  onEnvironmentalBandDefinitionsChange: (v: EnvironmentalBandDefinition[]) => void
  environmentalBandEditableFields?: 'label' | 'all'
  onEditProjNameChange: (v: string) => void
  onEditProjDescChange: (v: string) => void
  onEditProjVisibilityChange: (v: 'public' | 'private') => void
  onEditProjAllowedUidsChange: (v: string) => void
  onEditProjStatusChange: (v: 'active' | 'archived') => void
  onEditProjFileChange: (f: File | null) => void
  editProjError: string | null
  savingProjectEdit: boolean
  regenerateExplainabilitySampleRows?: number
  onRegenerateExplainabilitySampleRowsChange?: (n: number) => void
  onRegenerateExplainabilityBackground?: () => void | Promise<void>
  regeneratingExplainabilityBackground?: boolean
  regenerateExplainabilityError?: string | null
}

export function ProjectEditDialog({
  open,
  onClose,
  formMaxWidth,
  editingProject,
  editProjName,
  editProjDesc,
  editProjVisibility,
  editProjAllowedUids,
  editProjStatus,
  editProjFile,
  environmentalBandDefinitions,
  onEnvironmentalBandDefinitionsChange,
  environmentalBandEditableFields = 'label',
  onEditProjNameChange,
  onEditProjDescChange,
  onEditProjVisibilityChange,
  onEditProjAllowedUidsChange,
  onEditProjStatusChange,
  onEditProjFileChange,
  editProjError,
  savingProjectEdit,
  regenerateExplainabilitySampleRows,
  onRegenerateExplainabilitySampleRowsChange,
  onRegenerateExplainabilityBackground,
  regeneratingExplainabilityBackground,
  regenerateExplainabilityError,
}: ProjectEditDialogProps) {
  return (
    <Dialog
      open={open}
      onClose={() => {
        onClose()
      }}
      fullWidth
      maxWidth="sm"
      PaperProps={{ sx: { borderRadius: 2 } }}
    >
      <DialogTitle sx={{ fontWeight: 700 }}>
        Edit project
        <Typography variant="caption" component="span" display="block" color="text.secondary" fontWeight={400} sx={{ mt: 0.5 }}>
          {savingProjectEdit
            ? 'Saving…'
            : 'Changes save automatically. Click outside to close.'}
        </Typography>
      </DialogTitle>
      <DialogContent sx={{ pb: 2 }}>
        <Box sx={{ mt: 0.5 }}>
          <ProjectFormFields
            mode="edit"
            maxWidth={formMaxWidth}
            name={editProjName}
            description={editProjDesc}
            visibility={editProjVisibility}
            allowedUids={editProjAllowedUids}
            status={editProjStatus}
            onNameChange={onEditProjNameChange}
            onDescriptionChange={onEditProjDescChange}
            onVisibilityChange={onEditProjVisibilityChange}
            onAllowedUidsChange={onEditProjAllowedUidsChange}
            onStatusChange={onEditProjStatusChange}
            pendingFile={editProjFile}
            onFileChange={onEditProjFileChange}
            projectId={editingProject?.id}
            existingDriverPath={editingProject?.driver_cog_path ?? null}
            environmentalBandDefinitions={environmentalBandDefinitions}
            onEnvironmentalBandDefinitionsChange={onEnvironmentalBandDefinitionsChange}
            environmentalBandEditableFields={environmentalBandEditableFields}
            regenerateExplainabilitySampleRows={regenerateExplainabilitySampleRows}
            onRegenerateExplainabilitySampleRowsChange={onRegenerateExplainabilitySampleRowsChange}
            onRegenerateExplainabilityBackground={onRegenerateExplainabilityBackground}
            regeneratingExplainabilityBackground={regeneratingExplainabilityBackground}
            regenerateExplainabilityError={regenerateExplainabilityError}
            explainabilityBackgroundPath={editingProject?.explainability_background_path ?? null}
            explainabilityBackgroundSampleRows={editingProject?.explainability_background_sample_rows ?? null}
            explainabilityBackgroundGeneratedAt={editingProject?.explainability_background_generated_at ?? null}
          />
          {editProjError && (
            <Alert severity="error" sx={{ mt: 2 }}>
              {editProjError}
            </Alert>
          )}
        </Box>
      </DialogContent>
    </Dialog>
  )
}
