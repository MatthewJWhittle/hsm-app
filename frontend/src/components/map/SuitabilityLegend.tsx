import { Box, Collapse, Paper, Stack, Tooltip, Typography } from '@mui/material'
import { useCallback, useState } from 'react'
import {
  SUITABILITY_RESCALE_MAX,
  SUITABILITY_RESCALE_MIN,
} from '../../map/suitabilityScale'
import { SuitabilityBinStrip } from './SuitabilityBinStrip'

const DETAIL_COPY = `Modelled relative values for this layer, stretched to ${SUITABILITY_RESCALE_MIN} to ${SUITABILITY_RESCALE_MAX} for display. The map and legend use five equal 0-1 display steps (0-0.2, 0.2-0.4, …, 0.8-1) to read the band. That is a fixed display scale, not a statistical quantile of the landscape. Not directly comparable across different layers unless their rescales match.`

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

export type SuitabilityLegendVariant = 'compact' | 'corner' | 'embedded' | 'floating'

export interface SuitabilityLegendProps {
  /**
   * - `compact`: always-visible bar (tooltip detail); legacy use on controls.
   * - `corner`: minimal high/low bar for a fixed map corner.
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

function isCorner(variant: SuitabilityLegendVariant) {
  return variant === 'corner'
}

/** Map legend: compact / corner bar or full card with hover detail. */
export function SuitabilityLegend({ variant: variantProp = 'floating', embedded = false }: SuitabilityLegendProps) {
  const [hover, setHover] = useState(false)
  const variant: SuitabilityLegendVariant =
    embedded && variantProp === 'floating' ? 'embedded' : variantProp
  const embeddedMode = isEmbeddedMode(variant)
  const compact = isCompact(variant)
  const corner = isCorner(variant)

  const handleEnter = useCallback(() => setHover(true), [])
  const handleLeave = useCallback(() => setHover(false), [])

  if (corner) {
    return (
      <Box
        component="section"
        role="region"
        aria-labelledby="suitability-corner-strip-title"
        onClick={(e) => e.stopPropagation()}
        sx={{
          // Parent sets width; fill it so the bar spans edge-to-edge in that slot.
          width: '100%',
          minWidth: 0,
          boxSizing: 'border-box',
          px: 0.75,
          py: 0.5,
          borderRadius: 1,
          border: 1,
          borderColor: 'divider',
          bgcolor: 'rgba(255, 255, 255, 0.75)',
          backdropFilter: 'blur(6px)',
          boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
        }}
      >
        <Typography id="suitability-legend-detail-sr" component="span" sx={visuallyHidden}>
          {DETAIL_COPY}
        </Typography>
        <Typography
          id="suitability-corner-strip-title"
          component="p"
          variant="overline"
          color="text.secondary"
          sx={{
            m: 0,
            mb: 0.4,
            fontSize: '0.58rem',
            lineHeight: 1.2,
            fontWeight: 600,
            letterSpacing: '0.07em',
            textTransform: 'uppercase',
            opacity: 0.85,
          }}
        >
          Suitability scale
        </Typography>
        <Tooltip title={DETAIL_COPY} enterDelay={500} placement="top-start" disableInteractive>
          <Box sx={{ display: 'block', width: '100%', cursor: 'default' }}>
            <SuitabilityBinStrip barHeight={11} showEdgeLabels />
          </Box>
        </Tooltip>
      </Box>
    )
  }

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
            <SuitabilityBinStrip barHeight={8} showEdgeLabels={false} />
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
                High
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

      <SuitabilityBinStrip barHeight={10} showEdgeLabels={false} />
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
