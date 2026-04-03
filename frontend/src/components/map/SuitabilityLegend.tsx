import { Box, Collapse, Paper, Stack, Typography } from '@mui/material'
import { useCallback, useState } from 'react'
import {
  SUITABILITY_RESCALE_MAX,
  SUITABILITY_RESCALE_MIN,
  SUITABILITY_VIRIDIS_GRADIENT_CSS,
} from '../../map/suitabilityScale'

const DETAIL_COPY = `Modelled relative values for this layer, stretched to ${SUITABILITY_RESCALE_MIN}–${SUITABILITY_RESCALE_MAX} for display. Not directly comparable across different layers unless their rescales match.`

const visuallyHidden: Record<string, string | number> = {
  position: 'absolute',
  width: 1,
  height: 1,
  p: 0,
  m: -1,
  overflow: 'hidden',
  clip: 'rect(0, 0, 0, 0)',
  whiteSpace: 'nowrap',
  border: 0,
}

/** Floating map legend: compact bar + labels; detail expands on hover. */
export function SuitabilityLegend() {
  const [hover, setHover] = useState(false)

  const handleEnter = useCallback(() => setHover(true), [])
  const handleLeave = useCallback(() => setHover(false), [])

  return (
    <Paper
      component="section"
      role="region"
      aria-label="Suitability colour scale from low to high"
      aria-describedby="suitability-legend-detail-sr"
      variant="outlined"
      onMouseEnter={handleEnter}
      onMouseLeave={handleLeave}
      sx={{
        px: 0.75,
        py: 0.5,
        width: 200,
        maxWidth: 'min(200px, calc(100vw - 48px))',
        bgcolor: 'rgba(255, 255, 255, 0.94)',
        backdropFilter: 'blur(8px)',
        borderRadius: 1.5,
        transition: (t) =>
          t.transitions.create(['box-shadow', 'padding'], {
            duration: t.transitions.duration.shorter,
          }),
        ...(hover && {
          boxShadow: 2,
          py: 0.75,
        }),
      }}
    >
      <Typography id="suitability-legend-detail-sr" component="span" sx={visuallyHidden}>
        {DETAIL_COPY}
      </Typography>

      <Box
        sx={{
          height: 8,
          borderRadius: 0.5,
          background: SUITABILITY_VIRIDIS_GRADIENT_CSS,
          border: 1,
          borderColor: 'divider',
        }}
      />
      <Stack direction="row" justifyContent="space-between" alignItems="baseline" sx={{ mt: 0.35 }}>
        <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem', lineHeight: 1.2 }}>
          Low suitability
        </Typography>
        <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem', lineHeight: 1.2 }}>
          High suitability
        </Typography>
      </Stack>

      <Collapse in={hover} timeout={200} unmountOnExit>
        <Typography
          variant="caption"
          color="text.secondary"
          component="div"
          aria-hidden
          sx={{
            mt: 0.75,
            pt: 0.75,
            lineHeight: 1.45,
            borderTop: 1,
            borderColor: 'divider',
            fontSize: '0.7rem',
          }}
        >
          {DETAIL_COPY}
        </Typography>
      </Collapse>
    </Paper>
  )
}
