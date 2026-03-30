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
import { ProjectSelector, type ProjectOption } from './ProjectSelector'
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
  projectOptions: ProjectOption[]
  selectedProjectId: string
  onProjectChange: (projectId: string) => void
  models: Model[]
  selectedModelId: string
  onModelChange: (modelId: string) => void
  projectSummary: ProjectSummary
}

function modelLabel(m: Model): string {
  return `${m.species} — ${m.activity}`
}

export function MapControlPanel({
  projectOptions,
  selectedProjectId,
  onProjectChange,
  models,
  selectedModelId,
  onModelChange,
  projectSummary,
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
          Choose a catalog project, then a suitability model. Search models by typing in the box below.
        </Typography>

        <Box sx={{ mb: 2, flex: 1 }}>
          <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600, letterSpacing: '0.04em' }}>
            Catalog project
          </Typography>
          <Typography
            id="map-section-catalog-help"
            variant="caption"
            color="text.secondary"
            sx={{ display: 'block', mt: 0.25, mb: 1, lineHeight: 1.45 }}
          >
            {projectSummary?.isLegacy
              ? 'Legacy models are not linked to a shared environmental stack.'
              : 'Shared environmental stack (multi-band COG). Optional in admin until uploaded.'}
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
                label={projectSummary.hasEnvironmentalCog ? 'Env. COG on file' : 'Env. COG not uploaded'}
                color={projectSummary.hasEnvironmentalCog ? 'success' : 'default'}
                variant="outlined"
              />
            </Stack>
          )}

          {projectOptions.length > 0 && (
            <ProjectSelector
              value={selectedProjectId}
              options={projectOptions}
              onChange={onProjectChange}
              label="Catalog project"
            />
          )}

          <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600, letterSpacing: '0.04em' }}>
            Suitability model
          </Typography>
          <Typography
            id="map-section-model-help"
            variant="caption"
            color="text.secondary"
            sx={{ display: 'block', mt: 0.25, mb: 1, lineHeight: 1.45 }}
          >
            Search or pick the species/activity layer (not the shared environmental COG).
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
            noOptionsText="No matching models"
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
                label="Suitability model"
                placeholder="Search…"
                aria-describedby="map-section-model-help"
              />
            )}
            sx={{ mb: 2 }}
          />
        </Box>

        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', lineHeight: 1.45, opacity: 0.9, mt: 'auto', pt: 1 }}>
          Map: Web Mercator (EPSG:3857). Rasters must match this CRS.
        </Typography>
      </Box>
    </Drawer>
  )
}
