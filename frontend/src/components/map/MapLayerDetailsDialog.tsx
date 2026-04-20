import CloseIcon from '@mui/icons-material/Close'
import {
  Box,
  Chip,
  Dialog,
  DialogContent,
  DialogTitle,
  IconButton,
  Stack,
  Tooltip,
  Typography,
} from '@mui/material'
import {
  formatModelCatalogLabel,
  LAYER_DETAILS_DIALOG_TITLE,
  LAYER_DETAILS_PROJECT_METADATA_UNAVAILABLE,
} from '../../copy/interpretation'
import { getFeatureBandNames, type Model } from '../../types/model'
import { layerDisplayName } from '../../utils/layerDisplay'
import type { ProjectSummary } from '../../types/project'

function shortId(id: string, head = 8): string {
  if (id.length <= head + 2) return id
  return `${id.slice(0, head)}…`
}

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
  const driverFeatureBandNames = model ? getFeatureBandNames(model) : null

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

            <Box sx={{ mb: 2 }}>
              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
                Project name
              </Typography>
              <Typography variant="body1" sx={{ fontWeight: 600, mt: 0.25 }}>
                {selectedProjectLabel || '—'}
              </Typography>
            </Box>

            <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600, letterSpacing: '0.04em' }}>
              Technical identifiers
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, mb: 0.75, lineHeight: 1.45 }}>
              Use these when sharing a layer with support or comparing outputs.
            </Typography>
            <Box
              sx={{
                p: 1.25,
                borderRadius: 1,
                bgcolor: 'action.hover',
              }}
            >
              <Typography variant="caption" color="text.secondary" component="div" sx={{ lineHeight: 1.55 }}>
                <strong>Layer ID</strong>{' '}
                <Tooltip title={model.id}>
                  <span style={{ fontFamily: 'ui-monospace, monospace' }}>{shortId(model.id)}</span>
                </Tooltip>
              </Typography>
              <Typography variant="caption" color="text.secondary" component="div" sx={{ lineHeight: 1.55, mt: 0.5 }}>
                <strong>Project ID</strong>{' '}
                {model.project_id ? (
                  <Tooltip title={model.project_id}>
                    <span style={{ fontFamily: 'ui-monospace, monospace' }}>{shortId(model.project_id)}</span>
                  </Tooltip>
                ) : (
                  'None (stand-alone layer)'
                )}
              </Typography>
              <Typography variant="caption" color="text.secondary" component="div" sx={{ lineHeight: 1.55, mt: 0.5 }}>
                <strong>Environmental bands used</strong>{' '}
                {driverFeatureBandNames != null && driverFeatureBandNames.length > 0
                  ? `[${driverFeatureBandNames.join(', ')}]`
                  : '—'}
              </Typography>
            </Box>
          </DialogContent>
        </>
      )}
    </Dialog>
  )
}
