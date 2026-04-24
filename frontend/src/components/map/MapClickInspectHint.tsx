import CloseIcon from '@mui/icons-material/Close'
import { Box, IconButton, Paper, Typography } from '@mui/material'
import { useCallback, useId } from 'react'
import { INTERPRETATION_CLICK_MAP_SHORT } from '../../copy/interpretation'
import { dismissClickHintStorage } from './mapClickHintStorage'

export interface MapClickInspectHintProps {
  open: boolean
  onClose: () => void
  /** Distance from map bottom; increase when a bottom-left overlay (e.g. colour legend) is visible. */
  bottomPx?: number
}

export function MapClickInspectHint({ open, onClose, bottomPx = 28 }: MapClickInspectHintProps) {
  const labelId = useId()

  const handleClose = useCallback(() => {
    dismissClickHintStorage()
    onClose()
  }, [onClose])

  if (!open) return null

  return (
    <Box
      role="status"
      aria-live="polite"
      aria-labelledby={labelId}
      sx={{
        position: 'absolute',
        bottom: bottomPx,
        left: 16,
        zIndex: 999,
        maxWidth: { xs: 'min(calc(100vw - 32px), 360px)', sm: 360 },
        pointerEvents: 'auto',
      }}
    >
      <Paper
        elevation={2}
        sx={{
          px: 1.5,
          py: 0.75,
          display: 'flex',
          alignItems: 'center',
          gap: 0.5,
          bgcolor: 'rgba(255, 255, 255, 0.95)',
        }}
      >
        <Typography id={labelId} variant="caption" color="text.secondary" sx={{ flex: 1, lineHeight: 1.4 }}>
          {INTERPRETATION_CLICK_MAP_SHORT}
        </Typography>
        <IconButton size="small" aria-label="Dismiss hint" onClick={handleClose} edge="end" sx={{ p: 0.25 }}>
          <CloseIcon fontSize="small" />
        </IconButton>
      </Paper>
    </Box>
  )
}
