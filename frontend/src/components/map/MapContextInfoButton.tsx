import HelpIcon from '@mui/icons-material/Help'
import { alpha } from '@mui/material/styles'
import { Box, ClickAwayListener, IconButton, Tooltip } from '@mui/material'
import { useCallback, useEffect, useState } from 'react'
import { MAP_CONTEXT_COACHMARK, MAP_CONTEXT_INFO_ARIA, MAP_CONTEXT_INFO_TOOLTIP } from '../../copy/interpretation'
import { MapCoachmark } from './MapCoachmark'
import { isMapContextHintSeen, markMapContextHintSeen } from './mapContextHintStorage'
import { MAP_OVERLAY_Z } from './mapOverlayZIndex'

export interface MapContextInfoButtonProps {
  /** When false, the control is not shown (e.g. catalog not ready, load error). */
  visible: boolean
  /** Suppress the first-visit pointer until a competing overlay is gone (e.g. welcome). */
  suppressCoachmark?: boolean
  onOpenAboutMap: () => void
}

/**
 * Map bottom-left “?” / help entry to “What am I looking at?”.
 * Optional one-time coachmark; dismisses on click-away or when opening the guide.
 */
export function MapContextInfoButton({ visible, suppressCoachmark = false, onOpenAboutMap }: MapContextInfoButtonProps) {
  const [anchor, setAnchor] = useState<HTMLButtonElement | null>(null)
  const [dismissedLocal, setDismissedLocal] = useState(() => isMapContextHintSeen())
  const showCoach = visible && !dismissedLocal && !suppressCoachmark
  const popperOpen = showCoach && Boolean(anchor)

  const endCoachmark = useCallback(() => {
    markMapContextHintSeen()
    setDismissedLocal(true)
  }, [])

  const handleOpen = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation()
      endCoachmark()
      onOpenAboutMap()
    },
    [endCoachmark, onOpenAboutMap],
  )

  const handleClickAway = useCallback(() => {
    if (showCoach) {
      endCoachmark()
    }
  }, [showCoach, endCoachmark])

  useEffect(() => {
    if (!showCoach) return
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key !== 'Escape') return
      e.stopPropagation()
      endCoachmark()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [showCoach, endCoachmark])

  if (!visible) return null

  return (
    <ClickAwayListener onClickAway={handleClickAway}>
      <Box
        sx={{
          position: 'absolute',
          bottom: 16,
          left: 16,
          zIndex: MAP_OVERLAY_Z.contextHelp,
          display: 'flex',
          flexDirection: 'row',
          alignItems: 'center',
          gap: 0.5,
        }}
      >
        <MapCoachmark
          open={popperOpen}
          anchorEl={anchor}
          id="map-context-coachmark"
          placement="right"
          pointerSide="left"
        >
          {MAP_CONTEXT_COACHMARK}
        </MapCoachmark>
        <Tooltip
          title={MAP_CONTEXT_INFO_TOOLTIP}
          enterDelay={400}
          enterTouchDelay={0}
          placement="right"
          disableHoverListener={showCoach}
        >
          <span>
            <IconButton
              ref={setAnchor}
              size="small"
              onClick={handleOpen}
              aria-label={MAP_CONTEXT_INFO_ARIA}
              aria-describedby={showCoach ? 'map-context-coachmark' : undefined}
              sx={(t) => ({
                p: 0.5,
                minWidth: 40,
                minHeight: 40,
                borderRadius: 2,
                color: t.palette.secondary.main,
                // color="inherit" + default IconButton use transparent base/hover; keep an opaque card.
                backgroundColor: t.palette.background.paper,
                border: 1,
                borderColor: 'secondary.main',
                boxShadow: 1,
                '&:hover': {
                  backgroundColor: alpha(t.palette.common.black, 0.05),
                  borderColor: t.palette.secondary.dark,
                  color: t.palette.secondary.dark,
                  boxShadow: 2,
                },
                '&:active': {
                  backgroundColor: alpha(t.palette.common.black, 0.08),
                },
                '&.Mui-focusVisible': {
                  backgroundColor: t.palette.background.paper,
                },
              })}
            >
              <HelpIcon fontSize="small" aria-hidden />
            </IconButton>
          </span>
        </Tooltip>
      </Box>
    </ClickAwayListener>
  )
}
