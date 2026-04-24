import { Box, Stack, Typography } from '@mui/material'
import { useMemo } from 'react'
import {
  SUITABILITY_DISPLAY_BIN_COUNT,
  SUITABILITY_DISPLAY_BIN_EDGES,
  suitabilityDisplayBinSwatchColors,
} from '../../map/suitabilityScale'

const SWATCH = suitabilityDisplayBinSwatchColors()

function formatEdgeLabel(n: number): string {
  if (n === 0 || n === 1) return n.toFixed(0)
  if (n === 0.2 || n === 0.4 || n === 0.6 || n === 0.8) {
    return n.toFixed(1)
  }
  return String(n)
}

export interface SuitabilityBinStripProps {
  /** Height in px of the coloured blocks row. */
  barHeight: number
  /** Optional cell index 0-4 to emphasise (e.g. clicked point in HUD). */
  activeBinIndex?: number | null
  /**
   * When true, a row of **bin edge** labels 0, 0.2, …, 1 is shown.
   * When false, a single Low/High line can be drawn by the parent, or this is used in tight HUD.
   */
  showEdgeLabels: boolean
}

/**
 * Five equal-width 0-1 **display** bins (same as map rescale), as discrete swatches; not a data histogram.
 */
export function SuitabilityBinStrip({ barHeight, activeBinIndex, showEdgeLabels }: SuitabilityBinStripProps) {
  const ariaBins = useMemo(
    () =>
      Array.from({ length: SUITABILITY_DISPLAY_BIN_COUNT }, (_, k) => {
        const lo = SUITABILITY_DISPLAY_BIN_EDGES[k]!
        const hi = SUITABILITY_DISPLAY_BIN_EDGES[k + 1]!
        return `${lo} to ${hi}`
      }).join('; '),
    [],
  )

  const activeBandLabel = useMemo(() => {
    if (activeBinIndex == null) return undefined
    const lo = SUITABILITY_DISPLAY_BIN_EDGES[activeBinIndex]!
    const hi = SUITABILITY_DISPLAY_BIN_EDGES[activeBinIndex + 1]!
    return `Suitability value falls in the ${lo} to ${hi} range on the 0-1 display scale.`
  }, [activeBinIndex])

  return (
    <Box
      width="100%"
      aria-label={showEdgeLabels ? `Suitability in five display bands: ${ariaBins}.` : activeBandLabel}
    >
      <Stack
        direction="row"
        spacing={0}
        sx={(theme) => ({
          width: '100%',
          height: barHeight,
          borderRadius: 0.5,
          border: `1px solid ${theme.palette.divider}`,
          overflow: 'hidden',
        })}
      >
        {SWATCH.map((bg, k) => {
          const isActive = activeBinIndex != null && activeBinIndex === k
          const n = SWATCH.length
          return (
            <Box
              key={k}
              sx={(theme) => {
                const parts: string[] = []
                if (k < n - 1) {
                  parts.push(`inset -1px 0 0 ${theme.palette.divider}`)
                }
                if (isActive) {
                  parts.push(`inset 0 0 0 2px ${theme.palette.primary.main}`)
                }
                return {
                  flex: 1,
                  minWidth: 0,
                  alignSelf: 'stretch',
                  bgcolor: bg,
                  boxShadow: parts.length ? parts.join(', ') : 'none',
                  zIndex: isActive ? 1 : 0,
                }
              }}
            />
          )
        })}
      </Stack>
      {showEdgeLabels && (
        <Box
          component="div"
          sx={{ position: 'relative', width: '100%', height: 12, mt: 0.2 }}
        >
          {SUITABILITY_DISPLAY_BIN_EDGES.map((e, i) => {
            const n = SUITABILITY_DISPLAY_BIN_EDGES.length
            return (
              <Typography
                key={e}
                component="span"
                color="text.secondary"
                sx={{
                  position: 'absolute',
                  top: 0,
                  left: i === 0 ? 0 : `${(i / (n - 1)) * 100}%`,
                  transform: i === 0 ? 'none' : i === n - 1 ? 'translateX(-100%)' : 'translateX(-50%)',
                  fontSize: '0.55rem',
                  lineHeight: 1.1,
                  fontVariantNumeric: 'tabular-nums',
                  fontWeight: 500,
                  opacity: 0.9,
                }}
              >
                {formatEdgeLabel(e)}
              </Typography>
            )
          })}
        </Box>
      )}
    </Box>
  )
}

