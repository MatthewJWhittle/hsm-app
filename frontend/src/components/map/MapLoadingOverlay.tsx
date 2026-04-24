import { Box, CircularProgress, Stack, Typography } from '@mui/material'

/** Shown over the map area while the layer catalog is loading. */
export function MapLoadingOverlay() {
  return (
    <Box
      role="status"
      aria-live="polite"
      aria-busy="true"
      sx={{
        position: 'absolute',
        inset: 0,
        zIndex: 900,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexDirection: 'column',
        gap: 2,
        bgcolor: 'rgba(255, 255, 255, 0.65)',
        backdropFilter: 'blur(4px)',
        pointerEvents: 'none',
      }}
    >
      <Stack direction="row" alignItems="center" spacing={1.5}>
        <CircularProgress size={28} />
        <Typography variant="body2" color="text.secondary" component="p">
          Loading map…
        </Typography>
      </Stack>
    </Box>
  )
}
