import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined'
import { Box, IconButton, Tooltip } from '@mui/material'

interface FloatingMapInterpretationProps {
  onOpen: () => void
}

/** Map corner control — opens the same interpretation dialog as the sidebar (issue #19 / #29). */
export function FloatingMapInterpretation({ onOpen }: FloatingMapInterpretationProps) {
  return (
    <Box
      sx={{
        position: 'absolute',
        bottom: 40,
        right: 12,
        zIndex: 999,
        pointerEvents: 'auto',
      }}
    >
      <Tooltip title="About this map" placement="left">
        <IconButton
          onClick={onOpen}
          aria-label="About this map"
          size="small"
          sx={{
            bgcolor: 'rgba(255, 255, 255, 0.94)',
            border: 1,
            borderColor: 'divider',
            boxShadow: 2,
            '&:hover': { bgcolor: 'rgba(255, 255, 255, 0.98)' },
          }}
        >
          <InfoOutlinedIcon fontSize="small" />
        </IconButton>
      </Tooltip>
    </Box>
  )
}
