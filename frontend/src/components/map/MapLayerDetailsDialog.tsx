import CloseIcon from '@mui/icons-material/Close'
import {
  Box,
  Chip,
  Dialog,
  DialogContent,
  DialogTitle,
  IconButton,
  Stack,
  Typography,
} from '@mui/material'
import {
  formatModelCatalogLabel,
  LAYER_DETAILS_DIALOG_TITLE,
  LAYER_DETAILS_PROJECT_METADATA_UNAVAILABLE,
} from '../../copy/interpretation'
import type { Model } from '../../types/model'
import { layerDisplayName } from '../../utils/layerDisplay'
import type { ProjectSummary } from './MapControlPanel'

export interface MapLayerDetailsDialogProps {
  open: boolean
  onClose: () => void
  model: Model | null
  projectSummary: ProjectSummary
  selectedProjectLabel: string
}

export function MapLayerDetailsDialog({
  open,
  onClose,
  model,
  projectSummary,
  selectedProjectLabel,
}: MapLayerDetailsDialogProps) {
  const show = Boolean(open && model)

  const projectContextCopy =
    model &&
    (projectSummary?.isLegacy
      ? 'This layer stands alone—it isn’t grouped with a shared project dataset.'
      : projectSummary && !projectSummary.isLegacy
        ? 'Layers in the same project can share background environmental data (for example climate or terrain). Your team adds that file in Admin if needed.'
        : model.project_id
          ? LAYER_DETAILS_PROJECT_METADATA_UNAVAILABLE
          : 'This layer stands alone—it isn’t grouped with a shared project dataset.')

  return (
    <Dialog
      open={show}
      onClose={onClose}
      maxWidth="sm"
      fullWidth
      scroll="paper"
      aria-labelledby="map-layer-details-dialog-title"
    >
      {model && (
        <>
          <DialogTitle id="map-layer-details-dialog-title" sx={{ pr: 5, fontWeight: 700 }}>
            {LAYER_DETAILS_DIALOG_TITLE}
            <IconButton aria-label="Close" onClick={onClose} sx={{ position: 'absolute', right: 8, top: 8 }} size="small">
              <CloseIcon fontSize="small" />
            </IconButton>
          </DialogTitle>
          <DialogContent dividers sx={{ pt: 1.5 }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 0.5, lineHeight: 1.35, wordBreak: 'break-word' }}>
              {layerDisplayName(model)}
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 2 }}>
              Species and activity for this suitability layer
            </Typography>

            <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600, letterSpacing: '0.04em' }}>
              Model name and version
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ display: 'block', mt: 0.25, mb: 2, lineHeight: 1.45 }}>
              {formatModelCatalogLabel(model)}
            </Typography>

            <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600, letterSpacing: '0.04em' }}>
              Project
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.55, mb: 1 }}>
              {projectContextCopy}
            </Typography>

            {projectSummary && !projectSummary.isLegacy && (
              <Stack direction="row" spacing={0.75} flexWrap="wrap" useFlexGap sx={{ mb: 2 }}>
                <Chip
                  size="small"
                  label={projectSummary.visibility === 'private' ? 'Private' : 'Public'}
                  color={projectSummary.visibility === 'private' ? 'warning' : 'default'}
                  variant="outlined"
                />
                <Chip
                  size="small"
                  label={
                    projectSummary.hasEnvironmentalCog
                      ? 'Shared environmental data on file'
                      : 'No shared environmental file yet'
                  }
                  color={projectSummary.hasEnvironmentalCog ? 'success' : 'default'}
                  variant="outlined"
                />
              </Stack>
            )}

            <Box>
              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
                Project name
              </Typography>
              <Typography variant="body1" sx={{ fontWeight: 600, mt: 0.25 }}>
                {selectedProjectLabel || '—'}
              </Typography>
            </Box>
          </DialogContent>
        </>
      )}
    </Dialog>
  )
}
