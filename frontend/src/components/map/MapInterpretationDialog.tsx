import CloseIcon from '@mui/icons-material/Close'
import { Dialog, DialogContent, DialogTitle, IconButton, Typography } from '@mui/material'
import {
  INTERPRETATION_CRS_NOTE,
  INTERPRETATION_DECISION_SUPPORT,
  INTERPRETATION_DRIVERS_POINTER,
  INTERPRETATION_GUARDLINE_SHORT,
  MAP_INFO_DIALOG_TITLE,
} from '../../copy/interpretation'

export interface MapInterpretationDialogProps {
  open: boolean
  onClose: () => void
}

/** General map / app interpretation only — not layer-specific (see MapLayerDetailsDialog). */
export function MapInterpretationDialog({ open, onClose }: MapInterpretationDialogProps) {
  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="sm"
      fullWidth
      scroll="paper"
      aria-labelledby="map-interpretation-dialog-title"
    >
      <DialogTitle id="map-interpretation-dialog-title" sx={{ pr: 5, fontWeight: 700 }}>
        {MAP_INFO_DIALOG_TITLE}
        <IconButton aria-label="Close" onClick={onClose} sx={{ position: 'absolute', right: 8, top: 8 }} size="small">
          <CloseIcon fontSize="small" />
        </IconButton>
      </DialogTitle>
      <DialogContent dividers sx={{ pt: 1 }}>
        <Typography variant="body2" color="text.primary" sx={{ lineHeight: 1.5, fontWeight: 600, mb: 1.5 }}>
          {INTERPRETATION_GUARDLINE_SHORT}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.55, mb: 1.5 }}>
          {INTERPRETATION_DECISION_SUPPORT}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.55, mb: 2 }}>
          {INTERPRETATION_DRIVERS_POINTER}
        </Typography>

        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', lineHeight: 1.5 }}>
          {INTERPRETATION_CRS_NOTE}
        </Typography>
      </DialogContent>
    </Dialog>
  )
}
