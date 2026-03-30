import {
  Box,
  Chip,
  Paper,
  Stack,
  TextField,
  Typography,
} from '@mui/material'
import { styled } from '@mui/material/styles'
import type { Theme } from '@mui/material'
import { useMemo, useState } from 'react'
import { ModelSelector } from './ModelSelector'
import { ProjectSelector, type ProjectOption } from './ProjectSelector'
import { OpacityControl } from './OpacityControl'
import type { Model } from '../../types/model'

const FloatingPanel = styled(Paper)(({ theme }: { theme: Theme }) => ({
  position: 'absolute',
  top: 20,
  left: 20,
  padding: theme.spacing(2),
  zIndex: 1000,
  backgroundColor: 'rgba(255, 255, 255, 0.9)',
  boxShadow: theme.shadows[3],
  borderRadius: theme.shape.borderRadius,
  minWidth: 320,
  maxWidth: 380,
}))

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
  opacity: number
  onModelChange: (modelId: string) => void
  onOpacityChange: (opacity: number) => void
  projectSummary: ProjectSummary
}

function normalizeFilter(s: string): string {
  return s.trim().toLowerCase()
}

function modelMatchesFilter(m: Model, q: string): boolean {
  if (!q) return true
  const hay = `${m.species} ${m.activity}`.toLowerCase()
  return hay.includes(q)
}

export function MapControlPanel({
  projectOptions,
  selectedProjectId,
  onProjectChange,
  models,
  selectedModelId,
  opacity,
  onModelChange,
  onOpacityChange,
  projectSummary,
}: MapControlPanelProps) {
  const [modelFilter, setModelFilter] = useState('')

  const filteredModels = useMemo(() => {
    const q = normalizeFilter(modelFilter)
    let list = q ? models.filter((m) => modelMatchesFilter(m, q)) : models
    if (selectedModelId && !list.some((m) => m.id === selectedModelId)) {
      const current = models.find((m) => m.id === selectedModelId)
      if (current) list = [current, ...list]
    }
    return list
  }, [models, modelFilter, selectedModelId])

  return (
    <FloatingPanel>
      <Typography variant="h6" component="h2" gutterBottom sx={{ fontWeight: 700 }}>
        Map
      </Typography>
      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1.5, lineHeight: 1.45 }}>
        Choose a catalog project (shared environmental context), then a suitability model to display.
      </Typography>

      <Box sx={{ mb: 2 }}>
        <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600, letterSpacing: '0.04em' }}>
          Catalog project
        </Typography>
        <Typography
          id="map-section-catalog-help"
          variant="caption"
          color="text.secondary"
          sx={{ display: 'block', mt: 0.25, mb: 1, lineHeight: 1.45 }}
        >
          Shared environmental stack (multi-band COG). Optional in admin until uploaded.
        </Typography>

        {projectSummary && (
          <Stack direction="row" spacing={0.75} flexWrap="wrap" useFlexGap sx={{ mb: 1 }}>
            {projectSummary.isLegacy ? (
              <Typography variant="caption" color="text.secondary" sx={{ lineHeight: 1.45 }}>
                Legacy models are not linked to a shared environmental stack.
              </Typography>
            ) : (
              <>
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
              </>
            )}
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
          Species / activity suitability raster shown on the map (not the shared environmental COG).
        </Typography>

        <TextField
          id="map-model-filter"
          size="small"
          fullWidth
          placeholder="Filter models…"
          value={modelFilter}
          onChange={(e) => setModelFilter(e.target.value)}
          aria-describedby="map-section-model-help"
          sx={{ mb: 1 }}
        />

        <ModelSelector
          value={selectedModelId}
          models={filteredModels}
          onChange={onModelChange}
          label="Suitability model"
        />

        <OpacityControl value={opacity} onChange={onOpacityChange} />
      </Box>

      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', lineHeight: 1.45, opacity: 0.9 }}>
        Map: Web Mercator (EPSG:3857). Rasters must match this CRS.
      </Typography>
    </FloatingPanel>
  )
}
