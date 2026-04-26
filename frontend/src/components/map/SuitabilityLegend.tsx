import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined'
import { Box, Collapse, IconButton, Paper, Stack, Tooltip, Typography } from '@mui/material'
import { useCallback, useState, type MouseEvent } from 'react'
import { SUITABILITY_LEGEND_GUARDRAIL } from '../../copy/interpretation'
import { SuitabilityBinStrip } from './SuitabilityBinStrip'

const DETAIL_COPY = `Higher scores mark places the model rates as more suitable for the selected species and activity. Lower scores are less suitable in this model. Use the colours to compare places within this layer, not as confirmed presence or absence.`

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
  onOpenMapGuide?: () => void
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

function suitabilityInfoButton(
  guardrailOpen: boolean,
  onClick: (e: MouseEvent) => void,
) {
  return (
    <IconButton
      aria-label="Show suitability interpretation note"
      aria-describedby={guardrailOpen ? 'suitability-legend-guardrail' : undefined}
      size="small"
      onClick={onClick}
      sx={{ width: 18, height: 18, color: 'text.secondary' }}
    >
      <InfoOutlinedIcon sx={{ fontSize: 13 }} />
    </IconButton>
  )
}

/** Map legend: compact / corner bar or full card with hover detail. */
export function SuitabilityLegend({
  variant: variantProp = 'floating',
  onOpenMapGuide,
  embedded = false,
}: SuitabilityLegendProps) {
  const [hover, setHover] = useState(false)
  const [guardrailOpen, setGuardrailOpen] = useState(true)
  const variant: SuitabilityLegendVariant =
    embedded && variantProp === 'floating' ? 'embedded' : variantProp
  const embeddedMode = isEmbeddedMode(variant)
  const compact = isCompact(variant)
  const corner = isCorner(variant)

  const handleEnter = useCallback(() => setHover(true), [])
  const handleLeave = useCallback(() => setHover(false), [])
  const showGuardrail = useCallback(() => {
    setGuardrailOpen(true)
  }, [])
  const hideGuardrail = useCallback(() => {
    setGuardrailOpen(false)
  }, [])
  const handleOpenGuide = useCallback(
    (e: MouseEvent) => {
      e.stopPropagation()
      setGuardrailOpen(false)
      onOpenMapGuide?.()
    },
    [onOpenMapGuide],
  )

  if (corner) {
    return (
      <Tooltip
        id="suitability-legend-guardrail"
        title={SUITABILITY_LEGEND_GUARDRAIL}
        placement="left"
        open={guardrailOpen}
        onOpen={showGuardrail}
        onClose={hideGuardrail}
        enterDelay={400}
        enterTouchDelay={0}
      >
        <Box
          component="section"
          role="region"
          aria-labelledby="suitability-corner-strip-title"
          aria-describedby={guardrailOpen ? 'suitability-legend-guardrail' : undefined}
          onClick={(e) => e.stopPropagation()}
          sx={{
            // Parent sets width; fill it so the bar spans edge-to-edge in that slot.
            position: 'relative',
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
          <Stack direction="row" alignItems="center" justifyContent="center" spacing={0.2} sx={{ mb: 0.4 }}>
            <Typography
              id="suitability-corner-strip-title"
              component="p"
              variant="overline"
              color="text.secondary"
              sx={{
                m: 0,
                textAlign: 'center',
                fontSize: '0.58rem',
                lineHeight: 1.2,
                fontWeight: 600,
                letterSpacing: '0.07em',
                textTransform: 'uppercase',
                opacity: 0.85,
              }}
            >
              Suitability score
            </Typography>
            {suitabilityInfoButton(guardrailOpen, handleOpenGuide)}
          </Stack>
          <Tooltip
            title={DETAIL_COPY}
            enterDelay={500}
            placement="bottom-end"
            disableInteractive
            disableFocusListener={guardrailOpen}
            disableHoverListener={guardrailOpen}
            disableTouchListener={guardrailOpen}
          >
            <Box sx={{ display: 'block', width: '100%', cursor: 'default' }}>
              <SuitabilityBinStrip barHeight={11} showEdgeLabels />
            </Box>
          </Tooltip>
        </Box>
      </Tooltip>
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
