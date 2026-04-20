import HelpOutlineIcon from '@mui/icons-material/HelpOutline'
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined'
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
import { useCallback, useMemo } from 'react'
import type { Model } from '../../types/model'
import { layerDisplayName } from '../../utils/layerDisplay'

/** Width of the floating top-left control card (map UX). */
export const MAP_FLOATING_CONTROLS_WIDTH_PX = 320

interface MapFloatingControlsProps {
  models: Model[]
  selectedModelId: string
  onModelChange: (modelId: string) => void
  onOpenMapInfoDialog: () => void
  onOpenLayerDetailsDialog: () => void
  /** Raster layer opacity as a percentage (0–100). */
  opacity: number
  onOpacityChange: (value: number) => void
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
  loading = false,
  errored = false,
}: MapFloatingControlsProps) {
  const selectedModel = useMemo(
    () => models.find((m) => m.id === selectedModelId) ?? null,
    [models, selectedModelId],
  )

  const selectedTitle = selectedModel ? layerDisplayName(selectedModel) : ''

  const handleOpacityChange = useCallback(
    (_event: Event, value: number | number[]) => {
      onOpacityChange(value as number)
    },
    [onOpacityChange],
  )

  return (
    <Paper
      elevation={4}
      aria-label="Map controls"
      sx={{
        position: 'absolute',
        top: 16,
        left: 16,
        zIndex: 1000,
        width: MAP_FLOATING_CONTROLS_WIDTH_PX,
        maxWidth: 'calc(100vw - 32px)',
        borderRadius: 2,
        bgcolor: 'rgba(255, 255, 255, 0.96)',
        backdropFilter: 'blur(8px)',
        border: 1,
        borderColor: 'divider',
        pointerEvents: 'auto',
        overflow: 'hidden',
      }}
    >
      <Box sx={{ px: 1.75, pt: 1.5, pb: 1.25 }}>
        <Typography
          variant="caption"
          color="text.secondary"
          id="map-controls-layer-help"
          sx={{ fontWeight: 600, letterSpacing: '0.04em', display: 'block', mb: 0.75 }}
        >
          LAYER
        </Typography>

        {loading ? (
          <Skeleton
            variant="rounded"
            height={40}
            aria-label="Loading layers"
            role="status"
          />
        ) : (
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
                aria-describedby="map-controls-layer-help"
                inputProps={{
                  ...params.inputProps,
                  title: selectedTitle,
                }}
              />
            )}
          />
        )}

        {!loading && selectedModel && (
          <Typography
            variant="body2"
            color="text.secondary"
            sx={{ display: 'block', mt: 1, lineHeight: 1.4, wordBreak: 'break-word' }}
          >
            Showing:{' '}
            <Box component="span" sx={{ color: 'text.primary', fontWeight: 500 }}>
              {selectedTitle}
            </Box>
          </Typography>
        )}
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

      <Divider />

      <Box sx={{ px: 1.75, py: 1.25 }}>
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
          disabled={!selectedModel}
          aria-label="Layer transparency"
          aria-valuetext={`${opacity} percent`}
          valueLabelDisplay="auto"
          valueLabelFormat={(v) => `${v}%`}
          sx={{ py: 1 }}
        />
      </Box>

      <Divider />

      <Stack
        direction="row"
        alignItems="center"
        spacing={0.5}
        sx={{ px: 0.75, py: 0.5 }}
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
    </Paper>
  )
}
