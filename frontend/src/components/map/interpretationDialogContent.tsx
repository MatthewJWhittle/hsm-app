import { Box, Stack, Typography } from '@mui/material'
import {
  INTERPRETATION_DECISION_SUPPORT,
  INTERPRETATION_DRIVERS_POINTER,
  INTERPRETATION_DIALOG_GUARDRAIL_EMPHASIS,
  INTERPRETATION_DIALOG_GUARDRAIL_PREFIX,
  INTERPRETATION_DIALOG_SECTION_MEANING,
  INTERPRETATION_DIALOG_SECTION_USE,
} from '../../copy/interpretation'

/** Shared copy for the welcome and “About this map” dialogs. */
export function MapInterpretationDialogContent() {
  return (
    <Stack spacing={2.25} sx={{ pt: 0.25 }}>
      <Box>
        <Typography
          variant="subtitle2"
          component="h3"
          color="text.secondary"
          sx={{ fontWeight: 600, letterSpacing: '0.02em', mb: 0.75 }}
        >
          {INTERPRETATION_DIALOG_SECTION_MEANING}
        </Typography>
        <Typography variant="body2" color="text.primary" sx={{ lineHeight: 1.55 }}>
          {INTERPRETATION_DIALOG_GUARDRAIL_PREFIX}
          <Box component="strong" sx={{ fontWeight: 700 }}>
            {INTERPRETATION_DIALOG_GUARDRAIL_EMPHASIS}
          </Box>
        </Typography>
      </Box>

      <Box>
        <Typography
          variant="subtitle2"
          component="h3"
          color="text.secondary"
          sx={{ fontWeight: 600, letterSpacing: '0.02em', mb: 0.75 }}
        >
          {INTERPRETATION_DIALOG_SECTION_USE}
        </Typography>
        <Box
          component="ul"
          sx={{
            m: 0,
            pl: 2.2,
            color: 'text.secondary',
            fontSize: (theme) => theme.typography.body2.fontSize,
            lineHeight: 1.55,
            '& li': { mb: 0.85, '&:last-of-type': { mb: 0 } },
          }}
        >
          <Box component="li">
            <Typography variant="body2" color="text.secondary" component="span" sx={{ lineHeight: 1.55 }}>
              {INTERPRETATION_DECISION_SUPPORT}
            </Typography>
          </Box>
          <Box component="li">
            <Typography variant="body2" color="text.secondary" component="span" sx={{ lineHeight: 1.55 }}>
              {INTERPRETATION_DRIVERS_POINTER}
            </Typography>
          </Box>
        </Box>
      </Box>
    </Stack>
  )
}
