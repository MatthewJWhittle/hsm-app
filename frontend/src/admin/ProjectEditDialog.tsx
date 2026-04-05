import { Alert, Box, Button, Dialog, DialogActions, DialogContent, DialogTitle } from '@mui/material'
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
  onEditProjNameChange: (v: string) => void
  onEditProjDescChange: (v: string) => void
  onEditProjVisibilityChange: (v: 'public' | 'private') => void
  onEditProjAllowedUidsChange: (v: string) => void
  onEditProjStatusChange: (v: 'active' | 'archived') => void
  onEditProjFileChange: (f: File | null) => void
  editProjError: string | null
  savingProjectEdit: boolean
  onSave: () => void
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
  onEditProjNameChange,
  onEditProjDescChange,
  onEditProjVisibilityChange,
  onEditProjAllowedUidsChange,
  onEditProjStatusChange,
  onEditProjFileChange,
  editProjError,
  savingProjectEdit,
  onSave,
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
      <DialogTitle sx={{ fontWeight: 700 }}>Edit project</DialogTitle>
      <DialogContent>
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
          />
          {editProjError && (
            <Alert severity="error" sx={{ mt: 2 }}>
              {editProjError}
            </Alert>
          )}
        </Box>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose}>Cancel</Button>
        <Button variant="contained" onClick={() => void onSave()} disabled={savingProjectEdit}>
          {savingProjectEdit ? 'Saving…' : 'Save'}
        </Button>
      </DialogActions>
    </Dialog>
  )
}
