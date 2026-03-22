import { Paper, Typography, Box } from '@mui/material'
import { styled } from '@mui/material/styles'
import type { Theme } from '@mui/material'
import { SpeciesSelector } from './SpeciesSelector'
import { ActivitySelector } from './ActivitySelector'
import { OpacityControl } from './OpacityControl'


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
  selectedSpecies: string
  selectedActivity: string
  opacity: number
  onSpeciesChange: (species: string) => void
  onActivityChange: (activity: string) => void
  onOpacityChange: (opacity: number) => void
  speciesOptions: string[]
  activityOptions: string[]
}

export function MapControlPanel({
  selectedSpecies,
  selectedActivity,
  opacity,
  onSpeciesChange,
  onActivityChange,
  onOpacityChange,
  speciesOptions,
  activityOptions,
}: MapControlPanelProps) {
  return (
    <FloatingPanel>
      <Typography variant="h6" gutterBottom>
        Map Controls
      </Typography>
      
      <Box sx={{ mb: 2 }}>
        <SpeciesSelector value={selectedSpecies} options={speciesOptions} onChange={onSpeciesChange} />

        <ActivitySelector value={selectedActivity} options={activityOptions} onChange={onActivityChange} />

        <OpacityControl
          value={opacity}
          onChange={onOpacityChange}
        />
      </Box>

    </FloatingPanel>
  )
} 