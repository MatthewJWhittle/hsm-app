import {
  Box,
  Button,
  Collapse,
  IconButton,
  Paper,
  Tooltip,
  Typography,
} from '@mui/material'
import { alpha, useTheme } from '@mui/material/styles'
import { useCallback, useEffect, useRef, useState } from 'react'
import {
  INTERPRETATION_HUD_REMINDER,
  INTERPRETATION_INFLUENCE_CAPTION,
  INTERPRETATION_RAW_VALUES_CAPTION,
} from '../copy/interpretation'
import { clampSuitability01, SUITABILITY_VIRIDIS_GRADIENT_CSS } from '../map/suitabilityScale'
import type { DriverVariable, PointInspection as PointInspectionData } from '../types/pointInspection'

export interface InspectionTechnicalDetails {
  modelId: string
  projectId?: string | null
  /** Ordered ``metadata.analysis.feature_band_names`` (machine names). */
  driverFeatureBandNames?: string[] | null
}

interface InspectionHudProps {
  onClose: () => void
  modelLabel: string
  lng: number | null
  lat: number | null
  inspection: PointInspectionData | null
  loading: boolean
  error: string | null
  technicalDetails?: InspectionTechnicalDetails | null
}

function shortId(id: string, head = 8): string {
  if (id.length <= head + 2) return id
  return `${id.slice(0, head)}…`
}

function formatCoord(n: number, digits: number): string {
  return n.toFixed(digits)
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

function SuitabilityScaleMarker({ value, stale }: { value: number; stale: boolean }) {
  const pct = clampSuitability01(value) * 100
  return (
    <Box sx={{ mt: 0.75, opacity: stale ? 0.38 : 1, transition: 'opacity 0.2s ease' }}>
      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
        On this layer’s 0–1 scale
      </Typography>
      <Box
        role="img"
        aria-label={`Sample at about ${pct.toFixed(0)} percent along the low-to-high scale for this layer`}
        sx={{
          position: 'relative',
          height: 6,
          borderRadius: 0.5,
          overflow: 'hidden',
          border: 1,
          borderColor: 'divider',
        }}
      >
        <Box sx={{ position: 'absolute', inset: 0, background: SUITABILITY_VIRIDIS_GRADIENT_CSS }} />
        <Box
          aria-hidden
          sx={{
            position: 'absolute',
            left: `${pct}%`,
            top: 0,
            bottom: 0,
            width: 2,
            ml: '-1px',
            bgcolor: 'background.paper',
            boxShadow: (t) => `0 0 0 1px ${t.palette.divider}`,
          }}
        />
      </Box>
    </Box>
  )
}

function InfluenceDriverRow({ d, maxAbs }: { d: DriverVariable; maxAbs: number }) {
  const mag = d.magnitude ?? 0
  const w = maxAbs > 0 ? (Math.abs(mag) / maxAbs) * 100 : 0
  const color =
    d.direction === 'increase'
      ? 'success.main'
      : d.direction === 'decrease'
        ? 'error.main'
        : 'text.secondary'
  const title = d.display_name?.trim() ? d.display_name : d.name
  return (
    <Box sx={{ mb: 1 }}>
      <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
        <Tooltip title={d.display_name ? `Column: ${d.name}` : ''} disableHoverListener={!d.display_name}>
          <span>{title}</span>
        </Tooltip>
        : {d.label ?? (d.magnitude != null ? d.magnitude.toFixed(4) : d.direction)}
      </Typography>
      <Box sx={{ height: 6, bgcolor: 'action.hover', borderRadius: 0.5, mt: 0.25 }}>
        <Box
          sx={{
            height: '100%',
            width: `${w}%`,
            bgcolor: color,
            borderRadius: 0.5,
            transition: 'width 0.2s ease',
          }}
        />
      </Box>
    </Box>
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
  technicalDetails,
}: InspectionHudProps) {
  const theme = useTheme()
  const paperRef = useRef<HTMLDivElement>(null)
  const prevLoadingRef = useRef<boolean | undefined>(undefined)
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 })
  const [dragging, setDragging] = useState(false)
  const [technicalOpen, setTechnicalOpen] = useState(false)
  const [rawDetailsOpen, setRawDetailsOpen] = useState(false)
  const dragStartRef = useRef({ clientX: 0, clientY: 0, offX: 0, offY: 0 })

  useEffect(() => {
    setTechnicalOpen(false)
  }, [technicalDetails?.modelId])

  useEffect(() => {
    setRawDetailsOpen(false)
  }, [lng, lat, inspection?.value])

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

      {lat != null && lng != null && (
        <Typography
          variant="body2"
          component="p"
          title="Click to select coordinates, then copy"
          sx={{
            mb: 0.75,
            px: 1,
            py: 0.75,
            borderRadius: 1,
            bgcolor: 'action.hover',
            fontFamily:
              'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace',
            fontSize: '0.8125rem',
            fontVariantNumeric: 'tabular-nums',
            userSelect: 'all',
            cursor: 'text',
            color: 'text.primary',
            lineHeight: 1.5,
          }}
        >
          {formatCoord(lat, 4)}, {formatCoord(lng, 4)}
        </Typography>
      )}

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
          <SuitabilityScaleMarker value={inspection.value} stale={loading} />
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
          const rawVals = inspection.raw_environmental_values ?? []
          if (drivers.length === 0 && rawVals.length === 0) return null
          const maxAbs = Math.max(...drivers.map((d) => Math.abs(d.magnitude ?? 0)), 1e-9)
          return (
            <Box sx={{ mt: 0.75 }}>
              {drivers.length > 0 && (
                <>
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{ display: 'block', mb: 0.75, lineHeight: 1.45 }}
                  >
                    {INTERPRETATION_INFLUENCE_CAPTION}
                  </Typography>
                  {drivers.map((d, i) => (
                    <InfluenceDriverRow key={`${d.name}-${i}`} d={d} maxAbs={maxAbs} />
                  ))}
                </>
              )}
              {rawVals.length > 0 && (
                <Box sx={{ mt: drivers.length > 0 ? 1 : 0 }}>
                  <Button
                    size="small"
                    variant="text"
                    onClick={() => setRawDetailsOpen((o) => !o)}
                    aria-expanded={rawDetailsOpen}
                    sx={{ minWidth: 0, px: 0, py: 0.25, textTransform: 'none', fontSize: '0.75rem' }}
                  >
                    {rawDetailsOpen ? '▼' : '▶'} Environmental values at this point
                  </Button>
                  <Collapse in={rawDetailsOpen}>
                    <Typography
                      variant="caption"
                      color="text.secondary"
                      sx={{ display: 'block', mb: 0.5, mt: 0.5, lineHeight: 1.45 }}
                    >
                      {INTERPRETATION_RAW_VALUES_CAPTION}
                    </Typography>
                    <Box component="ul" sx={{ m: 0, pl: 2 }}>
                      {rawVals.map((r, ri) => (
                        <li key={`${r.name}-${ri}`}>
                          <Typography variant="caption" color="text.secondary" component="div">
                            {r.name}: {r.value.toFixed(4)}
                            {r.unit ? ` ${r.unit}` : ''}
                          </Typography>
                          {r.description?.trim() ? (
                            <Typography
                              variant="caption"
                              color="text.secondary"
                              sx={{ display: 'block', opacity: 0.85, pl: 0.5, mt: 0.25 }}
                            >
                              {r.description}
                            </Typography>
                          ) : null}
                        </li>
                      ))}
                    </Box>
                  </Collapse>
                </Box>
              )}
            </Box>
          )
        })()}

      {technicalDetails && (
        <Box sx={{ mt: 1 }}>
          <Button
            size="small"
            variant="text"
            onClick={() => setTechnicalOpen((o) => !o)}
            aria-expanded={technicalOpen}
            sx={{ minWidth: 0, px: 0, py: 0.25, textTransform: 'none', fontSize: '0.75rem' }}
          >
            {technicalOpen ? '▼' : '▶'} View technical details
          </Button>
          <Collapse in={technicalOpen}>
            <Box
              sx={{
                mt: 0.75,
                p: 1,
                borderRadius: 1,
                bgcolor: 'action.hover',
                maxHeight: 200,
                overflow: 'auto',
              }}
            >
              <Typography variant="caption" color="text.secondary" component="div" sx={{ lineHeight: 1.5 }}>
                <strong>Layer ID</strong>{' '}
                <Tooltip title={technicalDetails.modelId}>
                  <span style={{ fontFamily: 'ui-monospace, monospace' }}>{shortId(technicalDetails.modelId)}</span>
                </Tooltip>
              </Typography>
              <Typography variant="caption" color="text.secondary" component="div" sx={{ lineHeight: 1.5, mt: 0.5 }}>
                <strong>Project</strong>{' '}
                {technicalDetails.projectId ? (
                  <Tooltip title={technicalDetails.projectId}>
                    <span style={{ fontFamily: 'ui-monospace, monospace' }}>
                      {shortId(technicalDetails.projectId)}
                    </span>
                  </Tooltip>
                ) : (
                  'None (stand-alone layer)'
                )}
              </Typography>
              <Typography variant="caption" color="text.secondary" component="div" sx={{ lineHeight: 1.5, mt: 0.5 }}>
                <strong>Environmental bands used</strong>{' '}
                {technicalDetails.driverFeatureBandNames != null &&
                technicalDetails.driverFeatureBandNames.length > 0
                  ? `[${technicalDetails.driverFeatureBandNames.join(', ')}]`
                  : '—'}
              </Typography>
            </Box>
          </Collapse>
        </Box>
      )}

      <Typography
        variant="caption"
        color="text.secondary"
        sx={{ display: 'block', mt: 1.25, lineHeight: 1.45, opacity: 0.85 }}
      >
        {INTERPRETATION_HUD_REMINDER}
      </Typography>
    </Paper>
  )
}
