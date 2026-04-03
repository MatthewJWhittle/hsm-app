import { Box, Paper, Stack, Typography } from '@mui/material'
import {
  SUITABILITY_RESCALE_MAX,
  SUITABILITY_RESCALE_MIN,
  SUITABILITY_VIRIDIS_GRADIENT_CSS,
} from '../../map/suitabilityScale'

/** Floating map legend: matches TiTiler viridis + rescale for the active suitability layer. */
export function SuitabilityLegend() {
  return (
    <Paper
      component="section"
      role="region"
      aria-label="Suitability colour scale from low to high"
      variant="outlined"
      sx={{
        p: 1.25,
        width: 260,
        bgcolor: 'rgba(255, 255, 255, 0.94)',
        backdropFilter: 'blur(8px)',
        borderRadius: 2,
      }}
    >
      <Typography variant="caption" sx={{ fontWeight: 600, display: 'block', mb: 0.75 }}>
        Suitability (this layer)
      </Typography>
      <Box
        sx={{
          height: 12,
          borderRadius: 0.5,
          background: SUITABILITY_VIRIDIS_GRADIENT_CSS,
          border: 1,
          borderColor: 'divider',
        }}
      />
      <Stack direction="row" justifyContent="space-between" alignItems="baseline" sx={{ mt: 0.5 }}>
        <Typography variant="caption" color="text.secondary">
          Low suitability
        </Typography>
        <Typography variant="caption" color="text.secondary">
          High suitability
        </Typography>
      </Stack>
      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.75, lineHeight: 1.45 }}>
        Modelled relative values for this layer, stretched to {SUITABILITY_RESCALE_MIN}–{SUITABILITY_RESCALE_MAX} for
        display. Not directly comparable across different layers unless their rescales match.
      </Typography>
    </Paper>
  )
}
