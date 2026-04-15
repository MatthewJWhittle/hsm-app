import { Alert, Box, Button, Dialog, DialogActions, DialogContent, DialogTitle, Typography } from '@mui/material'
import { ProjectFormFields } from './ProjectFormFields'

const FORM_ID = 'admin-new-project-form'

type ProjectCreateDialogProps = {
  open: boolean
  onClose: () => void
  formMaxWidth: number
  projCreating: boolean
  projError: string | null
  onSubmit: (e: React.FormEvent) => void
  projName: string
  projDesc: string
  projVisibility: 'public' | 'private'
  projAllowedUids: string
  projFile: File | null
  onProjNameChange: (v: string) => void
  onProjDescChange: (v: string) => void
  onProjVisibilityChange: (v: 'public' | 'private') => void
  onProjAllowedUidsChange: (v: string) => void
  onProjFileChange: (f: File | null) => void
}

export function ProjectCreateDialog({
  open,
  onClose,
  formMaxWidth,
  projCreating,
  projError,
  onSubmit,
  projName,
  projDesc,
  projVisibility,
  projAllowedUids,
  projFile,
  onProjNameChange,
  onProjDescChange,
  onProjVisibilityChange,
  onProjAllowedUidsChange,
  onProjFileChange,
}: ProjectCreateDialogProps) {
  const missingName = !projName.trim()
  return (
    <Dialog
      open={open}
      onClose={() => {
        if (projCreating) return
        onClose()
      }}
      fullWidth
      maxWidth="sm"
      PaperProps={{ sx: { borderRadius: 2 } }}
    >
      <DialogTitle sx={{ fontWeight: 700 }}>New project</DialogTitle>
      <DialogContent>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2, mt: 0.5 }}>
          A project groups related map layers. You can attach one optional shared environmental raster used by those layers.
        </Typography>
        <Box component="form" id={FORM_ID} onSubmit={(e) => void onSubmit(e)} noValidate>
          <ProjectFormFields
            mode="create"
            maxWidth={formMaxWidth}
            name={projName}
            description={projDesc}
            visibility={projVisibility}
            allowedUids={projAllowedUids}
            onNameChange={onProjNameChange}
            onDescriptionChange={onProjDescChange}
            onVisibilityChange={onProjVisibilityChange}
            onAllowedUidsChange={onProjAllowedUidsChange}
            pendingFile={projFile}
            onFileChange={onProjFileChange}
          />
          {projError && (
            <Alert severity="error" sx={{ mt: 2, maxWidth: formMaxWidth }}>
              {projError}
            </Alert>
          )}
        </Box>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button
          onClick={() => {
            if (projCreating) return
            onClose()
          }}
          disabled={projCreating}
        >
          Cancel
        </Button>
        <Button type="submit" form={FORM_ID} variant="contained" disabled={projCreating || missingName}>
          {projCreating ? 'Creating…' : 'Create project'}
        </Button>
      </DialogActions>
      {missingName && (
        <Typography variant="caption" color="text.secondary" sx={{ px: 3, pb: 2, display: 'block' }}>
          Enter a project name to enable create.
        </Typography>
      )}
    </Dialog>
  )
}
