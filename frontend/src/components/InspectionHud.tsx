import { Box, IconButton, Paper, Tooltip, Typography } from '@mui/material'
import { alpha, useTheme } from '@mui/material/styles'
import { useCallback, useEffect, useRef, useState } from 'react'
import type {
  DriverVariable,
  PointInspection as PointInspectionData,
  RawEnvironmentalValue,
} from '../types/pointInspection'

interface InspectionHudProps {
  onClose: () => void
  modelLabel: string
  lng: number | null
  lat: number | null
  inspection: PointInspectionData | null
  loading: boolean
  error: string | null
}

function signedDriverContribution(d: DriverVariable): number {
  const m = d.magnitude
  if (m == null || !Number.isFinite(m)) {
    return 0
  }
  // Backend may send either a nonnegative magnitude + direction, or a signed value.
  if (m < 0) {
    return m
  }
  if (d.direction === 'increase') return m
  if (d.direction === 'decrease') return -m
  return 0
}

/** Fewer digits for large magnitudes — raw env values are often broad-scale rasters. */
function formatEnvSampleValue(value: number): string {
  if (!Number.isFinite(value)) return ''
  const a = Math.abs(value)
  if (a >= 1000) return value.toFixed(0)
  if (a >= 100) return value.toFixed(1)
  if (a >= 10) return value.toFixed(2)
  return value.toFixed(3)
}

/** One short line: signed effect + direction arrow (row label already names the variable). */
function formatContributionLine(d: DriverVariable): string {
  const s = signedDriverContribution(d)
  if (Math.abs(s) < 1e-12) return '—'
  const arrow = s > 0 ? '↑' : '↓'
  const abs = Math.abs(s)
  const nums = abs >= 1 ? abs.toFixed(2) : abs.toFixed(3)
  return `${s < 0 ? '−' : ''}${nums} ${arrow}`
}

function SuitabilityReadout({
  inspection,
  stale,
}: {
  inspection: PointInspectionData
  stale: boolean
}) {
  return (
    <Typography
      variant="h5"
      component="p"
      sx={{
        fontWeight: 600,
        letterSpacing: '-0.02em',
        fontVariantNumeric: 'tabular-nums',
        my: 0.25,
        opacity: stale ? 0.38 : 1,
        transition: stale ? 'opacity 0.2s ease' : 'opacity 0.15s ease',
      }}
    >
      {inspection.value.toFixed(3)}
      {inspection.unit ? (
        <Typography
          component="span"
          variant="body2"
          color="text.secondary"
          sx={{ ml: 0.75, fontWeight: 400 }}
        >
          {inspection.unit}
        </Typography>
      ) : null}
    </Typography>
  )
}

function normEnvKey(s: string): string {
  return s.trim().toLowerCase()
}

/**
 * Map a driver row to its sampled raster value.
 *
 * The API uses **machine feature names** on `DriverVariable.name` (SHAP / estimator columns).
 * `raw_environmental_values[].name` is often built from **catalog band labels** instead
 * (see `build_raw_environmental_values` in the backend), so the strings differ even for
 * the same variable. We match on `name`, then on `display_name` ↔ raw label.
 */
function rawValueForDriver(
  raw: RawEnvironmentalValue[] | null | undefined,
  d: DriverVariable,
): RawEnvironmentalValue | undefined {
  if (!raw?.length) return undefined

  for (const r of raw) {
    if (r.name === d.name || normEnvKey(r.name) === normEnvKey(d.name)) return r
  }

  const display = d.display_name?.trim()
  if (display) {
    for (const r of raw) {
      if (r.name === display || normEnvKey(r.name) === normEnvKey(display)) return r
    }
  }

  return undefined
}

function DriverTooltipBody({
  d,
  raw,
}: {
  d: DriverVariable
  raw: RawEnvironmentalValue | undefined
}) {
  const unit = raw?.unit != null && raw.unit !== '' ? ` ${raw.unit}` : ''
  const sampleLine =
    raw != null ? `${formatEnvSampleValue(raw.value)}${unit}` : null
  const desc = raw?.description?.trim()

  return (
    <Box sx={{ maxWidth: 260, py: 0 }}>
      {sampleLine != null ? (
        <Typography
          variant="body2"
          color="text.primary"
          sx={{ fontWeight: 600, fontVariantNumeric: 'tabular-nums', lineHeight: 1.25, mb: desc ? 0.5 : 0 }}
        >
          {sampleLine}
        </Typography>
      ) : null}
      {desc ? (
        <Typography variant="caption" sx={{ display: 'block', lineHeight: 1.45, opacity: 0.88 }}>
          {desc}
        </Typography>
      ) : null}
      {sampleLine == null && !desc ? (
        <Typography variant="caption" color="text.secondary" sx={{ lineHeight: 1.35 }}>
          {d.display_name?.trim() || d.name}
        </Typography>
      ) : null}
    </Box>
  )
}

function InfluenceDriverRow({
  d,
  maxAbs,
  rawEnv,
}: {
  d: DriverVariable
  maxAbs: number
  rawEnv: RawEnvironmentalValue[] | null | undefined
}) {
  const signed = signedDriverContribution(d)
  const frac = maxAbs > 0 ? Math.min(1, Math.abs(signed) / maxAbs) : 0
  const halfPct = frac * 50
  const title = d.display_name?.trim() ? d.display_name : d.name
  const raw = rawValueForDriver(rawEnv, d)
  const isPos = signed > 0
  const isNeg = signed < 0
  const barColor = isPos ? 'success.main' : isNeg ? 'error.main' : 'action.disabled'

  return (
    <Tooltip
      followCursor
      placement="top-start"
      enterDelay={120}
      enterNextDelay={80}
      slotProps={{
        tooltip: {
          sx: (theme) => ({
            bgcolor: alpha(theme.palette.background.paper, 0.94),
            color: theme.palette.text.secondary,
            border: `1px solid ${alpha(theme.palette.divider, 0.65)}`,
            boxShadow: `0 2px 12px ${alpha(theme.palette.common.black, 0.06)}`,
            backdropFilter: 'blur(8px)',
            py: 0.5,
            px: 0.85,
          }),
        },
        popper: {
          popperOptions: {
            modifiers: [
              {
                name: 'offset',
                options: { offset: [12, 12] },
              },
            ],
          },
        },
      }}
      title={<DriverTooltipBody d={d} raw={raw} />}
    >
      <Box
        sx={{ mb: 1, cursor: 'default' }}
        aria-label={
          [
            title,
            raw != null
              ? `Value at point ${formatEnvSampleValue(raw.value)}${raw.unit != null && raw.unit !== '' ? ` ${raw.unit}` : ''}`
              : null,
            raw?.description?.trim() ?? null,
            `Influence on suitability ${formatContributionLine(d)}`,
          ]
            .filter(Boolean)
            .join('. ')
        }
      >
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', lineHeight: 1.35, mb: 0.35 }}>
          {title}
        </Typography>
        <Box
          role="img"
          aria-label={
            isPos
              ? `Positive contribution, about ${halfPct.toFixed(0)} percent of the strongest driver at this point`
              : isNeg
                ? `Negative contribution, about ${halfPct.toFixed(0)} percent of the strongest driver at this point`
                : 'Neutral or negligible contribution'
          }
          sx={{
            position: 'relative',
            height: 8,
            borderRadius: 1,
            bgcolor: 'action.hover',
            overflow: 'hidden',
            direction: 'ltr',
          }}
        >
          <Box
            aria-hidden
            sx={{
              position: 'absolute',
              left: '50%',
              top: 0,
              bottom: 0,
              width: 1,
              ml: '-0.5px',
              bgcolor: 'divider',
              zIndex: 1,
            }}
          />
          {frac > 0 && isPos ? (
            <Box
              sx={{
                position: 'absolute',
                left: '50%',
                top: 0,
                bottom: 0,
                width: `${halfPct}%`,
                bgcolor: barColor,
                borderRadius: '0 1px 1px 0',
                transition: 'width 0.2s ease',
              }}
            />
          ) : null}
          {frac > 0 && isNeg ? (
            <Box
              sx={{
                position: 'absolute',
                // Physical left edge so the segment always fills center → left (avoid
                // `right` + `% width`, which is easy for engines to lay out wrong).
                left: `calc(50% - ${halfPct}%)`,
                top: 0,
                bottom: 0,
                width: `${halfPct}%`,
                bgcolor: barColor,
                borderRadius: '1px 0 0 1px',
                transition: 'width 0.2s ease, left 0.2s ease',
              }}
            />
          ) : null}
        </Box>
      </Box>
    </Tooltip>
  )
}

export function InspectionHud({
  onClose,
  modelLabel,
  lng,
  lat,
  inspection,
  loading,
  error,
}: InspectionHudProps) {
  const theme = useTheme()
  const paperRef = useRef<HTMLDivElement>(null)
  const prevLoadingRef = useRef<boolean | undefined>(undefined)
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 })
  const [dragging, setDragging] = useState(false)
  const dragStartRef = useRef({ clientX: 0, clientY: 0, offX: 0, offY: 0 })

  useEffect(() => {
    // Dismiss on Escape. Skip when focus is inside an input/textarea/contenteditable
    // so the user can still press Escape to clear an Autocomplete etc. without
    // collapsing the HUD.
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key !== 'Escape' || e.defaultPrevented) return
      const target = e.target as HTMLElement | null
      if (
        target &&
        (target.tagName === 'INPUT' ||
          target.tagName === 'TEXTAREA' ||
          target.isContentEditable)
      ) {
        return
      }
      onClose()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [onClose])

  const reducedMotion = () =>
    typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches

  useEffect(() => {
    if (lng == null || lat == null) return
    if (reducedMotion()) return
    const node = paperRef.current
    if (!node) return

    const baseShadow = '0 2px 12px rgba(0,0,0,0.08)'
    const ring = alpha(theme.palette.primary.main, 0.2)
    const peakShadow = `0 4px 22px rgba(0,0,0,0.1), 0 0 0 1px ${ring}`

    const anim = node.animate(
      [
        {
          boxShadow: baseShadow,
          borderColor: theme.palette.divider,
        },
        {
          boxShadow: peakShadow,
          borderColor: alpha(theme.palette.primary.main, 0.38),
        },
        {
          boxShadow: baseShadow,
          borderColor: theme.palette.divider,
        },
      ],
      { duration: 420, easing: 'cubic-bezier(0.33, 1, 0.68, 1)' },
    )
    return () => anim.cancel()
  }, [lng, lat, theme])

  useEffect(() => {
    const wasLoading = prevLoadingRef.current
    prevLoadingRef.current = loading
    if (wasLoading !== true || loading !== false) return
    if (reducedMotion()) return
    const node = paperRef.current
    if (!node) return

    const baseShadow = '0 2px 12px rgba(0,0,0,0.08)'
    const softRing = alpha(theme.palette.primary.main, 0.1)
    const peakShadow = `0 3px 14px rgba(0,0,0,0.07), 0 0 0 1px ${softRing}`

    const anim = node.animate(
      [
        { boxShadow: baseShadow, borderColor: theme.palette.divider },
        {
          boxShadow: peakShadow,
          borderColor: alpha(theme.palette.primary.main, 0.2),
        },
        { boxShadow: baseShadow, borderColor: theme.palette.divider },
      ],
      { duration: 260, easing: 'cubic-bezier(0.4, 0, 0.2, 1)' },
    )
    return () => anim.cancel()
  }, [loading, theme])

  const onDragPointerDown = useCallback(
    (e: React.PointerEvent) => {
      if (e.button !== 0) return
      e.preventDefault()
      setDragging(true)
      dragStartRef.current = {
        clientX: e.clientX,
        clientY: e.clientY,
        offX: dragOffset.x,
        offY: dragOffset.y,
      }
      ;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
    },
    [dragOffset.x, dragOffset.y],
  )

  const onDragPointerMove = useCallback((e: React.PointerEvent) => {
    if (!e.currentTarget.hasPointerCapture(e.pointerId)) return
    const { clientX, clientY, offX, offY } = dragStartRef.current
    setDragOffset({
      x: offX + (e.clientX - clientX),
      y: offY + (e.clientY - clientY),
    })
  }, [])

  const onDragPointerUp = useCallback((e: React.PointerEvent) => {
    if (!e.currentTarget.hasPointerCapture(e.pointerId)) return
    setDragging(false)
    try {
      ;(e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId)
    } catch {
      /* ignore */
    }
  }, [])

  return (
    <Paper
      ref={paperRef}
      elevation={3}
      role="dialog"
      aria-label="Habitat suitability at this point"
      aria-live="polite"
      aria-busy={loading}
      sx={{
        position: 'absolute',
        bottom: 20,
        right: 20,
        zIndex: 1000,
        maxWidth: 300,
        px: 1.75,
        py: 1.5,
        borderRadius: 1.5,
        bgcolor: 'rgba(255, 255, 255, 0.92)',
        backdropFilter: 'blur(8px)',
        pointerEvents: 'auto',
        boxShadow: '0 2px 12px rgba(0,0,0,0.08)',
        border: '1px solid',
        borderColor: 'divider',
        transform: `translate(${dragOffset.x}px, ${dragOffset.y}px)`,
        willChange: dragging ? 'transform' : undefined,
      }}
    >
      <Box
        onPointerDown={onDragPointerDown}
        onPointerMove={onDragPointerMove}
        onPointerUp={onDragPointerUp}
        onPointerCancel={onDragPointerUp}
        sx={{
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          gap: 1,
          mb: 0.75,
          cursor: dragging ? 'grabbing' : 'grab',
          touchAction: 'none',
          userSelect: 'none',
          mx: -0.5,
          mt: -0.5,
          px: 0.5,
          pt: 0.5,
          borderRadius: 1,
        }}
        title="Drag panel"
      >
        <Typography variant="caption" color="text.secondary" sx={{ lineHeight: 1.3, flex: 1, pt: 0.25 }}>
          {modelLabel}
        </Typography>
        <IconButton
          size="small"
          aria-label="Close"
          onClick={onClose}
          onPointerDown={(e) => e.stopPropagation()}
          sx={{ color: 'text.secondary', mt: -0.5, mr: -0.5 }}
        >
          <span aria-hidden style={{ fontSize: 18, lineHeight: 1 }}>
            ×
          </span>
        </IconButton>
      </Box>

      {loading && !inspection && (
        <Typography
          variant="h5"
          component="p"
          sx={{
            fontWeight: 600,
            letterSpacing: '-0.02em',
            fontVariantNumeric: 'tabular-nums',
            color: 'text.secondary',
            opacity: 0.75,
            my: 0.25,
            transition: 'opacity 0.2s ease',
          }}
        >
          …
        </Typography>
      )}

      {inspection && (loading || (!loading && !error)) && (
        <Box>
          <SuitabilityReadout inspection={inspection} stale={loading} />
        </Box>
      )}

      {!loading && error && (
        <Typography variant="body2" color="error" sx={{ lineHeight: 1.4 }}>
          {error}
        </Typography>
      )}

      {!loading &&
        !error &&
        inspection &&
        (() => {
          const drivers = inspection.drivers ?? []
          if (drivers.length === 0) return null
          const maxAbs = Math.max(
            ...drivers.map((d) => Math.abs(signedDriverContribution(d))),
            1e-9,
          )
          return (
            <Box sx={{ mt: 0.75 }}>
              {drivers.map((d, i) => (
                <InfluenceDriverRow
                  key={`${d.name}-${i}`}
                  d={d}
                  maxAbs={maxAbs}
                  rawEnv={inspection.raw_environmental_values}
                />
              ))}
            </Box>
          )
        })()}
    </Paper>
  )
}
