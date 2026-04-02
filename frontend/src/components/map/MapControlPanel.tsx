import {
  Autocomplete,
  Box,
  Chip,
  Drawer,
  Stack,
  TextField,
  Typography,
} from '@mui/material'
import { useMemo } from 'react'
import type { Model } from '../../types/model'

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
  projectSummary: ProjectSummary
  selectedProjectLabel: string
}

function modelLabel(m: Model): string {
  return `${m.species} — ${m.activity}`
}

export function MapControlPanel({
  models,
  selectedModelId,
  onModelChange,
  projectSummary,
  selectedProjectLabel,
}: MapControlPanelProps) {
  const selectedModel = useMemo(
    () => models.find((m) => m.id === selectedModelId) ?? null,
    [models, selectedModelId],
  )

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
        <Typography variant="h6" component="h2" gutterBottom sx={{ fontWeight: 700 }}>
          Map
        </Typography>
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1.5, lineHeight: 1.45 }}>
          Choose what to show on the map. You can search by species or activity. Project information appears below after
          you pick a layer.
        </Typography>

        <Box sx={{ mb: 2, flex: 1 }}>
          <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600, letterSpacing: '0.04em' }}>
            Layer
          </Typography>
          <Typography
            id="map-section-model-help"
            variant="caption"
            color="text.secondary"
            sx={{ display: 'block', mt: 0.25, mb: 1, lineHeight: 1.45 }}
          >
            Each option is a habitat suitability map for a species and activity. The coloured layer is the prediction
            raster, not raw survey points.
          </Typography>

          <Autocomplete
            size="small"
            options={models}
            value={selectedModel}
            onChange={(_, newValue) => {
              onModelChange(newValue?.id ?? '')
            }}
            getOptionLabel={(m) => modelLabel(m)}
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
                  modelLabel(m).toLowerCase().includes(q),
              )
            }}
            renderInput={(params) => (
              <TextField
                {...params}
                label="Species and activity"
                placeholder="Search layers…"
                aria-describedby="map-section-model-help"
              />
            )}
            sx={{ mb: 2 }}
          />

          {selectedModel && (
            <>
              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600, letterSpacing: '0.04em' }}>
                Project
              </Typography>
              <Typography
                id="map-section-catalog-help"
                variant="caption"
                color="text.secondary"
                sx={{ display: 'block', mt: 0.25, mb: 1, lineHeight: 1.45 }}
              >
                {projectSummary?.isLegacy
                  ? 'This layer stands alone—it isn’t grouped with a shared project dataset.'
                  : 'Layers in the same project can share background environmental data (for example climate or terrain). Your team adds that file in Admin if needed.'}
              </Typography>

              {projectSummary && !projectSummary.isLegacy && (
                <Stack direction="row" spacing={0.75} flexWrap="wrap" useFlexGap sx={{ mb: 1 }}>
                  <Chip
                    size="small"
                    label={projectSummary.visibility === 'private' ? 'Private' : 'Public'}
                    color={projectSummary.visibility === 'private' ? 'warning' : 'default'}
                    variant="outlined"
                  />
                  <Chip
                    size="small"
                    label={
                      projectSummary.hasEnvironmentalCog
                        ? 'Shared environmental data on file'
                        : 'No shared environmental file yet'
                    }
                    color={projectSummary.hasEnvironmentalCog ? 'success' : 'default'}
                    variant="outlined"
                  />
                </Stack>
              )}

              <Typography variant="body2" sx={{ fontWeight: 600, mb: 0.5 }}>
                {selectedProjectLabel || '—'}
              </Typography>
            </>
          )}
        </Box>

        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', lineHeight: 1.45, opacity: 0.9, mt: 'auto', pt: 1 }}>
          Uses the usual web map layout (Web Mercator). Uploaded layers need to match that format.
        </Typography>
      </Box>
    </Drawer>
  )
}
