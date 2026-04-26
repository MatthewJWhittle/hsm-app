import { Box, Paper, Typography } from '@mui/material'
import { useEffect, useId } from 'react'
import { INTERPRETATION_CLICK_MAP_SHORT } from '../../copy/interpretation'
import { MAP_OVERLAY_Z } from './mapOverlayZIndex'

export interface MapClickInspectHintProps {
  open: boolean
  point: { x: number; y: number } | null
  onClose: () => void
}

export function MapClickInspectHint({ open, point, onClose }: MapClickInspectHintProps) {
  const labelId = useId()

  useEffect(() => {
    if (!open) return
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key !== 'Escape') return
      e.stopPropagation()
      onClose()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [onClose, open])

  if (!open || !point) return null

  return (
    <Box
      role="status"
      aria-live="polite"
      aria-labelledby={labelId}
      sx={{
        position: 'absolute',
        left: point.x,
        top: point.y,
        transform: 'translate(14px, 14px)',
        zIndex: MAP_OVERLAY_Z.clickHint,
        maxWidth: { xs: 'min(calc(100vw - 32px), 320px)', sm: 320 },
        pointerEvents: 'none',
      }}
    >
      <Paper
        elevation={2}
        sx={{
          px: 1,
          py: 0.55,
          bgcolor: 'rgba(33, 33, 33, 0.88)',
          color: 'common.white',
          borderRadius: 1,
        }}
      >
        <Typography id={labelId} variant="caption" sx={{ color: 'inherit', fontSize: '0.68rem', lineHeight: 1.35 }}>
          {INTERPRETATION_CLICK_MAP_SHORT}
        </Typography>
      </Paper>
    </Box>
  )
}
