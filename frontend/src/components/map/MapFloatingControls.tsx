import ExpandLessIcon from '@mui/icons-material/ExpandLess'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import HelpOutlineIcon from '@mui/icons-material/HelpOutline'
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined'
import VisibilityIcon from '@mui/icons-material/Visibility'
import VisibilityOffOutlinedIcon from '@mui/icons-material/VisibilityOffOutlined'
import {
  Autocomplete,
  Box,
  Divider,
  IconButton,
  Paper,
  Skeleton,
  Slider,
  Stack,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material'
import { useCallback, useMemo, useState } from 'react'
import type { Model } from '../../types/model'
import { layerDisplayName } from '../../utils/layerDisplay'
import { SuitabilityLegend } from './SuitabilityLegend'

/** Width of the floating top-left control card (map UX). */
export const MAP_FLOATING_CONTROLS_WIDTH_PX = 352

interface MapFloatingControlsProps {
  models: Model[]
  selectedModelId: string
  onModelChange: (modelId: string) => void
  onOpenMapInfoDialog: () => void
  onOpenLayerDetailsDialog: () => void
  /** Raster layer opacity as a percentage (0–100). */
  opacity: number
  onOpacityChange: (value: number) => void
  /** Whether the active raster layer is currently rendered on the map. */
  layerVisible: boolean
  onToggleLayerVisible: () => void
  /** Catalog is still loading; render a skeleton in place of the picker. */
  loading?: boolean
  /** Catalog load failed; render a short disabled-state message. */
  errored?: boolean
}

/**
 * Top-left floating control card that carries the primary map controls:
 * layer picker, transparency, and entry points to the info dialogs. Replaces
 * the old permanent sidebar so the map can take the full viewport.
 */
export function MapFloatingControls({
  models,
  selectedModelId,
  onModelChange,
  onOpenMapInfoDialog,
  onOpenLayerDetailsDialog,
  opacity,
  onOpacityChange,
  layerVisible,
  onToggleLayerVisible,
  loading = false,
  errored = false,
}: MapFloatingControlsProps) {
  const selectedModel = useMemo(
    () => models.find((m) => m.id === selectedModelId) ?? null,
    [models, selectedModelId],
  )

  const selectedTitle = selectedModel ? layerDisplayName(selectedModel) : ''

  const [detailsExpanded, setDetailsExpanded] = useState(true)

  const handleOpacityChange = useCallback(
    (_event: Event, value: number | number[]) => {
      onOpacityChange(value as number)
    },
    [onOpacityChange],
  )

  // Muted card affordance when the active raster is hidden: quick visual
  // confirmation that the map is intentionally showing the basemap only.
  const cardDimmed = !loading && Boolean(selectedModel) && !layerVisible

  const expandIfCollapsed = useCallback((e: React.MouseEvent) => {
    if (detailsExpanded) return
    const el = e.target as HTMLElement
    if (
      el.closest(
        'button, a, input, textarea, select, [role="combobox"], [role="listbox"], [role="option"], .MuiAutocomplete-root, .MuiPopover-root, .MuiModal-root, .MuiPopper-root',
      )
    ) {
      return
    }
    setDetailsExpanded(true)
  }, [detailsExpanded])

  return (
    <Paper
      elevation={4}
      aria-label="Map controls"
      aria-expanded={detailsExpanded}
      onClick={expandIfCollapsed}
      sx={{
        position: 'absolute',
        top: 16,
        left: 16,
        zIndex: 1000,
        width: MAP_FLOATING_CONTROLS_WIDTH_PX,
        maxWidth: 'calc(100vw - 32px)',
        borderRadius: 2,
        bgcolor: cardDimmed ? 'rgba(255, 255, 255, 0.82)' : 'rgba(255, 255, 255, 0.96)',
        backdropFilter: 'blur(8px)',
        border: 1,
        borderColor: 'divider',
        pointerEvents: 'auto',
        overflow: 'hidden',
        cursor: detailsExpanded ? 'default' : 'pointer',
        transition: (t) =>
          t.transitions.create(['background-color'], {
            duration: t.transitions.duration.shorter,
          }),
      }}
    >
      <Box sx={{ px: 1.75, pt: 1.25, pb: detailsExpanded ? 1.25 : 1 }}>
        <Stack direction="row" alignItems="center" spacing={1} sx={{ width: '100%' }}>
          {loading ? (
            <Skeleton
              variant="rounded"
              height={40}
              aria-label="Loading layers"
              role="status"
              sx={{ flex: 1, minWidth: 0 }}
            />
          ) : (
            <Box onClick={(e) => e.stopPropagation()} sx={{ flex: 1, minWidth: 0 }}>
              <Autocomplete
                size="small"
                options={models}
                value={selectedModel}
                onChange={(_, newValue) => {
                  onModelChange(newValue?.id ?? '')
                }}
                getOptionLabel={(m) => layerDisplayName(m)}
                isOptionEqualToValue={(a, b) => a.id === b.id}
                disabled={models.length === 0}
                noOptionsText="No matching layers"
                filterOptions={(opts, state) => {
                  const q = state.inputValue.trim().toLowerCase()
                  if (!q) return opts
                  return opts.filter(
                    (m) =>
                      m.species.toLowerCase().includes(q) ||
                      m.activity.toLowerCase().includes(q) ||
                      layerDisplayName(m).toLowerCase().includes(q),
                  )
                }}
                renderOption={(props, m) => (
                  <li {...props} key={m.id} title={layerDisplayName(m)}>
                    <Typography
                      variant="body2"
                      sx={{ whiteSpace: 'normal', wordBreak: 'break-word' }}
                      title={layerDisplayName(m)}
                    >
                      {layerDisplayName(m)}
                    </Typography>
                  </li>
                )}
                renderInput={(params) => (
                  <TextField
                    {...params}
                    placeholder="Species and activity"
                    aria-label="Species and activity"
                    sx={{
                      '& .MuiInputBase-input': {
                        fontSize: '0.8125rem',
                        lineHeight: 1.35,
                      },
                    }}
                    inputProps={{
                      ...params.inputProps,
                      title: selectedTitle,
                    }}
                  />
                )}
              />
            </Box>
          )}
          <Stack direction="row" alignItems="center" spacing={0} sx={{ flexShrink: 0 }}>
            <Tooltip
              placement="bottom-end"
              title={detailsExpanded ? 'Hide transparency & shortcuts' : 'Show transparency & shortcuts'}
            >
              <IconButton
                size="small"
                onClick={(e) => {
                  e.stopPropagation()
                  setDetailsExpanded((v) => !v)
                }}
                aria-label={detailsExpanded ? 'Collapse map controls' : 'Expand map controls'}
                aria-expanded={detailsExpanded}
                sx={{ mr: -0.25 }}
              >
                {detailsExpanded ? (
                  <ExpandLessIcon fontSize="small" />
                ) : (
                  <ExpandMoreIcon fontSize="small" />
                )}
              </IconButton>
            </Tooltip>
            <Tooltip
              placement="bottom-end"
              title={
                selectedModel
                  ? layerVisible
                    ? 'Hide layer (V)'
                    : 'Show layer (V)'
                  : 'Select a layer first'
              }
            >
              <span>
                <IconButton
                  size="small"
                  onClick={(e) => {
                    e.stopPropagation()
                    onToggleLayerVisible()
                  }}
                  disabled={!selectedModel}
                  aria-label={layerVisible ? 'Hide layer' : 'Show layer'}
                  aria-pressed={!layerVisible}
                  sx={{ mr: -0.5, color: layerVisible ? 'primary.main' : 'text.secondary' }}
                >
                  {layerVisible ? (
                    <VisibilityIcon fontSize="small" />
                  ) : (
                    <VisibilityOffOutlinedIcon fontSize="small" />
                  )}
                </IconButton>
              </span>
            </Tooltip>
          </Stack>
        </Stack>

        {!loading && !errored && models.length === 0 && (
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ display: 'block', mt: 1, lineHeight: 1.45 }}
          >
            No layers are available yet.
          </Typography>
        )}
        {!loading && errored && (
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ display: 'block', mt: 1, lineHeight: 1.45 }}
          >
            Couldn’t load the layer catalog.
          </Typography>
        )}
      </Box>

      {detailsExpanded ? (
        <>
          <Divider />

          <Box sx={{ px: 1.75, py: 1.25 }} onClick={(e) => e.stopPropagation()}>
            <Stack
              direction="row"
              alignItems="center"
              justifyContent="space-between"
              spacing={1}
              sx={{ mb: 0.25 }}
            >
              <Typography
                variant="caption"
                color="text.secondary"
                sx={{ fontWeight: 600, letterSpacing: '0.04em' }}
              >
                TRANSPARENCY
              </Typography>
              <Typography variant="caption" color="text.secondary" aria-hidden>
                {opacity}%
              </Typography>
            </Stack>
            <Slider
              size="small"
              value={opacity}
              onChange={handleOpacityChange}
              min={0}
              max={100}
              disabled={!selectedModel || !layerVisible}
              aria-label="Layer transparency"
              aria-valuetext={`${opacity} percent`}
              valueLabelDisplay="auto"
              valueLabelFormat={(v) => `${v}%`}
              sx={{ py: 1 }}
            />
          </Box>

          {selectedModel && layerVisible && !errored && (
            <Box sx={{ px: 1.75, pt: 1, pb: 1.25 }} onClick={(e) => e.stopPropagation()}>
              <SuitabilityLegend embedded />
            </Box>
          )}

          <Divider />

          <Stack
            direction="row"
            alignItems="center"
            spacing={0.5}
            sx={{ px: 0.75, py: 0.5 }}
            onClick={(e) => e.stopPropagation()}
          >
            <Tooltip
              title={selectedModel ? 'Layer details (version, project)' : 'Select a layer first'}
            >
              <span>
                <IconButton
                  size="small"
                  onClick={onOpenLayerDetailsDialog}
                  disabled={!selectedModel}
                  aria-label="Layer details: version and project"
                >
                  <InfoOutlinedIcon fontSize="small" />
                </IconButton>
              </span>
            </Tooltip>
            <Tooltip title="About this map">
              <IconButton
                size="small"
                onClick={onOpenMapInfoDialog}
                aria-label="About this map"
              >
                <HelpOutlineIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          </Stack>
        </>
      ) : null}
    </Paper>
  )
}
