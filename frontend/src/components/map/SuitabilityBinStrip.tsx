import { Box, Stack, Typography } from '@mui/material'
import { alpha, useTheme } from '@mui/material/styles'
import { useMemo } from 'react'
import {
  SUITABILITY_DISPLAY_BIN_COUNT,
  suitabilityDisplayBinEdges,
  suitabilityDisplayBinSwatchColors,
} from '../../map/suitabilityScale'

function formatEdgeLabel(n: number): string {
  if (n === 0 || n === 1) return n.toFixed(0)
  return n.toFixed(1)
}

export interface SuitabilityBinStripProps {
  /**
   * How many **equal 0-1** display segments (5 for the map corner, 10 in the point HUD).
   * @default 5
   */
  binCount?: number
  /** Height in px of the coloured blocks row. */
  barHeight: number
  /** When set, that bin is shown at full strength; other bins are visually subdued. */
  activeBinIndex?: number | null
  /**
   * When true, a row of **bin edge** labels 0, …, 1 is shown.
   * When false, a parent may add Low/High, or the HUD only shows the strip.
   */
  showEdgeLabels: boolean
}

/**
 * Equal-width 0-1 **display** bins (same as map rescale), as Viridis swatches. Not a data quantile.
 */
export function SuitabilityBinStrip({
  binCount: binCountProp = SUITABILITY_DISPLAY_BIN_COUNT,
  barHeight,
  activeBinIndex,
  showEdgeLabels,
}: SuitabilityBinStripProps) {
  const theme = useTheme()
  const binCount = binCountProp
  const swatch = useMemo(() => suitabilityDisplayBinSwatchColors(binCount), [binCount])
  const binEdges = useMemo(() => suitabilityDisplayBinEdges(binCount), [binCount])

  const dimOthers = activeBinIndex != null
  const inactiveWash =
    theme.palette.mode === 'dark'
      ? alpha(theme.palette.common.black, 0.5)
      : alpha(theme.palette.common.white, 0.52)

  const ariaBins = useMemo(
    () =>
      Array.from({ length: binCount }, (_, k) => {
        const lo = binEdges[k]!
        const hi = binEdges[k + 1]!
        return `${lo} to ${hi}`
      }).join('; '),
    [binCount, binEdges],
  )

  const activeBandLabel = useMemo(() => {
    if (activeBinIndex == null) return undefined
    const lo = binEdges[activeBinIndex]!
    const hi = binEdges[activeBinIndex + 1]!
    return `Suitability value falls in the ${lo} to ${hi} range on the 0-1 display scale.`
  }, [activeBinIndex, binEdges])

  return (
    <Box
      width="100%"
      aria-label={
        showEdgeLabels
          ? `Suitability in ${binCount} equal display bands: ${ariaBins}.`
          : activeBandLabel
      }
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
        {swatch.map((bg, k) => {
          const isActive = activeBinIndex != null && activeBinIndex === k
          const n = swatch.length
          const isDimmed = dimOthers && !isActive
          const showInterCellRuler = !dimOthers && k < n - 1
          return (
            <Box
              key={k}
              sx={{
                flex: 1,
                minWidth: 0,
                position: 'relative',
                display: 'flex',
                alignSelf: 'stretch',
                boxShadow: showInterCellRuler
                  ? (t) => `inset -1px 0 0 ${alpha(t.palette.divider, 0.4)}`
                  : 'none',
              }}
            >
              <Box
                sx={{ flex: 1, minWidth: 0, minHeight: 0, alignSelf: 'stretch', backgroundColor: bg }}
                aria-hidden
              />
              {isDimmed && (
                <Box
                  sx={(t) => ({
                    position: 'absolute',
                    inset: 0,
                    backgroundColor: inactiveWash,
                    pointerEvents: 'none',
                    transition: t.transitions.create('background-color', { duration: 120 }),
                  })}
                  aria-hidden
                />
              )}
              {isActive && dimOthers && (
                <Box
                  sx={(t) => ({
                    position: 'absolute',
                    inset: 0,
                    // Neutral rim (not primary): reads on both light and dark swatches without clashing with the map palette.
                    boxShadow: `inset 0 0 0 2px ${alpha(t.palette.text.primary, 0.55)}`,
                    pointerEvents: 'none',
                    zIndex: 1,
                    transition: t.transitions.create('box-shadow', { duration: 120 }),
                  })}
                  aria-hidden
                />
              )}
            </Box>
          )
        })}
      </Stack>
      {showEdgeLabels && (
        <Box
          component="div"
          sx={{ position: 'relative', width: '100%', height: 12, mt: 0.2 }}
        >
          {binEdges.map((e, i) => {
            const n = binEdges.length
            return (
              <Typography
                key={`${e}-${i}`}
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
