import { Paper, Typography, Box } from '@mui/material'
import { styled } from '@mui/material/styles'
import type { Theme } from '@mui/material'
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
  minWidth: 300,
}))

interface MapControlPanelProps {
  projectOptions: ProjectOption[]
  selectedProjectId: string
  onProjectChange: (projectId: string) => void
  models: Model[]
  selectedModelId: string
  opacity: number
  onModelChange: (modelId: string) => void
  onOpacityChange: (opacity: number) => void
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
}: MapControlPanelProps) {
  return (
    <FloatingPanel>
      <Typography variant="h6" gutterBottom>
        Map controls
      </Typography>

      <Box sx={{ mb: 2 }}>
        {projectOptions.length > 0 && (
          <ProjectSelector
            value={selectedProjectId}
            options={projectOptions}
            onChange={onProjectChange}
          />
        )}

        <ModelSelector
          value={selectedModelId}
          models={models}
          onChange={onModelChange}
        />

        <OpacityControl value={opacity} onChange={onOpacityChange} />
      </Box>
    </FloatingPanel>
  )
}
