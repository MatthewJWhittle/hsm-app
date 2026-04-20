import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined'
import {
  Autocomplete,
  Box,
  Drawer,
  IconButton,
  Paper,
  Skeleton,
  Stack,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material'
import { useMemo } from 'react'
import type { Model } from '../../types/model'
import { layerDisplayName } from '../../utils/layerDisplay'

/** Left map sidebar width (GIS-style controls; keeps map focal area clear). */
export const MAP_SIDEBAR_WIDTH_PX = 320

/** Context for the selected catalog project (map UX). Null when nothing loaded yet. */
export type ProjectSummary = {
  visibility: 'public' | 'private'
  hasEnvironmentalCog: boolean
  isLegacy: boolean
} | null

interface MapControlPanelProps {
  models: Model[]
  selectedModelId: string
  onModelChange: (modelId: string) => void
  onOpenMapInfoDialog: () => void
  onOpenLayerDetailsDialog: () => void
  /** Catalog is still loading; render a skeleton in place of the picker. */
  loading?: boolean
  /** Catalog load failed; render a short disabled-state message. */
  errored?: boolean
}

export function MapControlPanel({
  models,
  selectedModelId,
  onModelChange,
  onOpenMapInfoDialog,
  onOpenLayerDetailsDialog,
  loading = false,
  errored = false,
}: MapControlPanelProps) {
  const selectedModel = useMemo(
    () => models.find((m) => m.id === selectedModelId) ?? null,
    [models, selectedModelId],
  )

  const selectedTitle = selectedModel ? layerDisplayName(selectedModel) : ''

  return (
    <Drawer
      variant="permanent"
      anchor="left"
      sx={{
        width: MAP_SIDEBAR_WIDTH_PX,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: MAP_SIDEBAR_WIDTH_PX,
          boxSizing: 'border-box',
          position: 'relative',
          borderRight: 1,
          borderColor: 'divider',
          height: '100%',
          overflow: 'auto',
        },
      }}
    >
      <Box sx={{ p: 2, display: 'flex', flexDirection: 'column', minHeight: '100%' }}>
        <Stack direction="row" alignItems="flex-start" justifyContent="space-between" spacing={0.5} sx={{ mb: 1 }}>
          <Typography variant="h6" component="h2" sx={{ fontWeight: 700, flex: 1, minWidth: 0 }}>
            Map
          </Typography>
          <Tooltip title="About this map">
            <IconButton
              size="small"
              onClick={onOpenMapInfoDialog}
              aria-label="About this map"
              sx={{ mt: -0.5 }}
            >
              <InfoOutlinedIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Stack>
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1.5, lineHeight: 1.45 }}>
          Explore modelled habitat suitability by species and activity.
        </Typography>

        <Paper variant="outlined" sx={{ p: 1.5, mb: 1, flex: 1, borderRadius: 1, bgcolor: 'background.paper' }}>
          <Stack direction="row" alignItems="center" justifyContent="space-between" spacing={1} sx={{ mb: 0.75 }}>
            <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600, letterSpacing: '0.04em' }}>
              Layer
            </Typography>
            <Tooltip title={selectedModel ? 'Layer details (version, project)' : 'Select a layer first'}>
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
          </Stack>
          <Typography
            id="map-section-model-help"
            variant="caption"
            color="text.secondary"
            sx={{ display: 'block', mb: 1.25, lineHeight: 1.45 }}
          >
            Habitat suitability layer (modelled raster, not raw survey points).
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
                  <Typography variant="body2" sx={{ whiteSpace: 'normal', wordBreak: 'break-word' }} title={layerDisplayName(m)}>
                    {layerDisplayName(m)}
                  </Typography>
                </li>
              )}
              renderInput={(params) => (
                <TextField
                  {...params}
                  label="Species and activity"
                  placeholder="Search layers…"
                  aria-describedby="map-section-model-help"
                  inputProps={{
                    ...params.inputProps,
                    title: selectedTitle,
                  }}
                />
              )}
            />
          )}
          {!loading && !errored && models.length === 0 && (
            <Typography
              variant="caption"
              color="text.secondary"
              sx={{ display: 'block', mt: 1.25, lineHeight: 1.45 }}
            >
              No layers are available yet. Once a catalog is published, species and
              activity combinations will appear here.
            </Typography>
          )}
          {!loading && errored && (
            <Typography
              variant="caption"
              color="text.secondary"
              sx={{ display: 'block', mt: 1.25, lineHeight: 1.45 }}
            >
              Couldn’t load the layer catalog. Use Retry in the map area to try again.
            </Typography>
          )}
        </Paper>
      </Box>
    </Drawer>
  )
}
