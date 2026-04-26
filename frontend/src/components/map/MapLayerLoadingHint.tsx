import { Box, CircularProgress, Fade, Stack, Typography } from '@mui/material'
import { MAP_OVERLAY_Z } from './mapOverlayZIndex'

interface MapLayerLoadingHintProps {
  visible: boolean
}

/** Lightweight, non-blocking hint for raster tile warmup/loading after the base map is visible. */
export function MapLayerLoadingHint({ visible }: MapLayerLoadingHintProps) {
  return (
    <Fade in={visible} timeout={180} unmountOnExit>
      <Box
        role="status"
        aria-live="polite"
        sx={{
          position: 'absolute',
          top: 66,
          left: '50%',
          transform: 'translateX(-50%)',
          zIndex: MAP_OVERLAY_Z.layerLoadingHint,
          pointerEvents: 'none',
          maxWidth: 'calc(100vw - 32px)',
        }}
      >
        <Stack
          direction="row"
          alignItems="center"
          spacing={1}
          sx={{
            px: 1.25,
            py: 0.75,
            borderRadius: 999,
            border: 1,
            borderColor: 'divider',
            bgcolor: 'rgba(255, 255, 255, 0.9)',
            boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
            backdropFilter: 'blur(8px)',
          }}
        >
          <CircularProgress size={14} thickness={5} />
          <Typography variant="caption" color="text.secondary" sx={{ lineHeight: 1.2 }}>
            Waiting for layer tiles…
          </Typography>
        </Stack>
      </Box>
    </Fade>
  )
}
