import OpacityIcon from '@mui/icons-material/Opacity'
import {
  Box,
  ClickAwayListener,
  Collapse,
  IconButton,
  Paper,
  Slider,
  Stack,
  Tooltip,
  Typography,
} from '@mui/material'
import { useCallback, useState } from 'react'

interface FloatingMapToolsProps {
  opacity: number
  onOpacityChange: (value: number) => void
  /** When true, opacity has no visible effect (no layer). */
  disabled?: boolean
}

export function FloatingMapTools({
  opacity,
  onOpacityChange,
  disabled = false,
}: FloatingMapToolsProps) {
  const [open, setOpen] = useState(false)

  const handleOpacityChange = useCallback(
    (_event: Event, newValue: number | number[]) => {
      onOpacityChange(newValue as number)
    },
    [onOpacityChange],
  )

  const handleClickAway = useCallback(() => {
    setOpen(false)
  }, [])

  return (
    <Box
      sx={{
        position: 'absolute',
        bottom: 20,
        left: 20,
        zIndex: 999,
        pointerEvents: 'auto',
      }}
    >
      <ClickAwayListener onClickAway={handleClickAway}>
        <Paper
          elevation={4}
          sx={{
            borderRadius: 2,
            border: 1,
            borderColor: 'divider',
            bgcolor: 'rgba(255, 255, 255, 0.94)',
            backdropFilter: 'blur(8px)',
            overflow: 'hidden',
          }}
        >
          <Stack direction="row" alignItems="stretch" spacing={0}>
            <Tooltip title={open ? 'Hide opacity' : 'Layer opacity'} placement="right">
              <IconButton
                size="small"
                onClick={() => setOpen((v) => !v)}
                aria-expanded={open}
                aria-controls="map-tools-opacity-panel"
                disabled={disabled}
                sx={{
                  borderRadius: 0,
                  px: 1,
                  color: open ? 'primary.main' : 'action.active',
                }}
              >
                <OpacityIcon fontSize="small" />
              </IconButton>
            </Tooltip>

            <Collapse in={open} orientation="horizontal" collapsedSize={0}>
              <Box
                id="map-tools-opacity-panel"
                role="region"
                aria-label="Suitability layer opacity"
                sx={{
                  py: 1,
                  pr: 2,
                  pl: 0.5,
                  width: 200,
                  borderLeft: 1,
                  borderColor: 'divider',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'center',
                }}
              >
                <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5 }}>
                  Suitability opacity
                </Typography>
                <Slider
                  size="small"
                  value={opacity}
                  onChange={handleOpacityChange}
                  aria-label="Suitability layer opacity"
                  valueLabelDisplay="auto"
                  min={0}
                  max={100}
                  disabled={disabled}
                />
              </Box>
            </Collapse>
          </Stack>
        </Paper>
      </ClickAwayListener>
    </Box>
  )
}
