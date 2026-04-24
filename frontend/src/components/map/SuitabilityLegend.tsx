import { Box, Collapse, Paper, Stack, Tooltip, Typography } from '@mui/material'
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

export type SuitabilityLegendVariant = 'compact' | 'embedded' | 'floating'

export interface SuitabilityLegendProps {
  /**
   * - `compact`: always-visible bar for collapsed map controls (tooltip detail).
   * - `embedded`: full legend with hover + collapse (expanded panel; rarely used when compact is on).
   * - `floating`: small standalone card (e.g. future use outside controls).
   * @deprecated Use `variant="embedded"`; `embedded` boolean kept for compatibility.
   */
  variant?: SuitabilityLegendVariant
  /**
   * @deprecated use `variant="embedded"`
   */
  embedded?: boolean
}

function isEmbeddedMode(variant: SuitabilityLegendVariant) {
  return variant === 'embedded'
}

function isCompact(variant: SuitabilityLegendVariant) {
  return variant === 'compact'
}

/** Map legend: compact bar (default on map) or full card with hover detail. */
export function SuitabilityLegend({ variant: variantProp = 'floating', embedded = false }: SuitabilityLegendProps) {
  const [hover, setHover] = useState(false)
  const variant: SuitabilityLegendVariant =
    embedded && variantProp === 'floating' ? 'embedded' : variantProp
  const embeddedMode = isEmbeddedMode(variant)
  const compact = isCompact(variant)

  const handleEnter = useCallback(() => setHover(true), [])
  const handleLeave = useCallback(() => setHover(false), [])

  if (compact) {
    return (
      <Box
        component="section"
        role="region"
        aria-label="Suitability colour scale from low to high"
        onClick={(e) => e.stopPropagation()}
        sx={{ width: '100%' }}
      >
        <Typography id="suitability-legend-detail-sr" component="span" sx={visuallyHidden}>
          {DETAIL_COPY}
        </Typography>
        <Tooltip title={DETAIL_COPY} enterDelay={400} placement="bottom-start">
          <Box sx={{ display: 'block', cursor: 'help' }}>
            <Box
              sx={{
                height: 6,
                borderRadius: 0.5,
                background: SUITABILITY_VIRIDIS_GRADIENT_CSS,
                border: 1,
                borderColor: 'divider',
              }}
            />
            <Stack
              direction="row"
              justifyContent="space-between"
              alignItems="baseline"
              sx={{ mt: 0.25 }}
            >
              <Typography
                variant="caption"
                color="text.secondary"
                sx={{ fontSize: '0.65rem', lineHeight: 1.2 }}
              >
                Low
              </Typography>
              <Typography
                variant="caption"
                color="text.secondary"
                sx={{ fontSize: '0.65rem', lineHeight: 1.2 }}
              >
                High (0–1)
              </Typography>
            </Stack>
          </Box>
        </Tooltip>
      </Box>
    )
  }

  return (
    <Paper
      component="section"
      role="region"
      aria-label="Suitability colour scale from low to high"
      aria-describedby="suitability-legend-detail-sr"
      variant={embeddedMode ? 'elevation' : 'outlined'}
      elevation={embeddedMode ? 0 : undefined}
      onMouseEnter={handleEnter}
      onMouseLeave={handleLeave}
      onClick={(e) => e.stopPropagation()}
      sx={{
        px: embeddedMode ? 0 : 0.75,
        py: embeddedMode ? 0 : 0.5,
        width: embeddedMode ? '100%' : 200,
        maxWidth: embeddedMode ? '100%' : 'min(200px, calc(100vw - 48px))',
        bgcolor: embeddedMode ? 'transparent' : 'rgba(255, 255, 255, 0.94)',
        backdropFilter: embeddedMode ? 'none' : 'blur(8px)',
        border: embeddedMode ? 'none' : undefined,
        boxShadow: 'none',
        borderRadius: embeddedMode ? 0 : 1.5,
        transition: (t) =>
          t.transitions.create(['box-shadow', 'padding'], {
            duration: t.transitions.duration.shorter,
          }),
        ...(!embeddedMode &&
          hover && {
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
