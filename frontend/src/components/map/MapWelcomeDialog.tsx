import CloseIcon from '@mui/icons-material/Close'
import { Button, Dialog, DialogActions, DialogContent, DialogTitle, IconButton } from '@mui/material'
import { MAP_WELCOME_DIALOG_TITLE } from '../../copy/interpretation'
import { MapInterpretationDialogContent } from './interpretationDialogContent'

export interface MapWelcomeDialogProps {
  open: boolean
  /** Fired for Got it, X, Escape, and backdrop. Parent should persist and hide. */
  onClose: () => void
}

/**
 * Shown once after the catalog loads so new users get an overview without a top banner.
 */
export function MapWelcomeDialog({ open, onClose }: MapWelcomeDialogProps) {
  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="sm"
      fullWidth
      scroll="paper"
      aria-labelledby="map-welcome-dialog-title"
    >
      <DialogTitle id="map-welcome-dialog-title" sx={{ pr: 5, fontWeight: 700 }}>
        {MAP_WELCOME_DIALOG_TITLE}
        <IconButton aria-label="Close" onClick={onClose} sx={{ position: 'absolute', right: 8, top: 8 }} size="small">
          <CloseIcon fontSize="small" />
        </IconButton>
      </DialogTitle>
      <DialogContent dividers sx={{ pt: 1.5, pb: 1 }}>
        <MapInterpretationDialogContent />
      </DialogContent>
      <DialogActions sx={{ px: 3, py: 2 }}>
        <Button variant="contained" onClick={onClose}>
          Got it
        </Button>
      </DialogActions>
    </Dialog>
  )
}
