import HelpIcon from '@mui/icons-material/Help'
import { alpha } from '@mui/material/styles'
import { Box, ClickAwayListener, Fade, IconButton, Paper, Popper, Tooltip, Typography } from '@mui/material'
import { useCallback, useState } from 'react'
import { MAP_CONTEXT_COACHMARK, MAP_CONTEXT_INFO_ARIA, MAP_CONTEXT_INFO_TOOLTIP } from '../../copy/interpretation'
import { isMapContextHintSeen, markMapContextHintSeen } from './mapContextHintStorage'

export interface MapContextInfoButtonProps {
  /** When false, the control is not shown (e.g. catalog not ready, load error). */
  visible: boolean
  /** Suppress the first-visit pointer until a competing overlay is gone (e.g. welcome). */
  suppressCoachmark?: boolean
  onOpenAboutMap: () => void
}

/**
 * Map top-right “?” / help entry to “What am I looking at?”. Visually separate from
 * the floating card’s Help/Info (smaller, lower-left in expanded controls).
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

  if (!visible) return null

  return (
    <ClickAwayListener onClickAway={handleClickAway}>
      <Box
        sx={{
          position: 'absolute',
          top: 16,
          right: 16,
          zIndex: 1002,
          display: 'flex',
          flexDirection: 'row',
          alignItems: 'center',
          gap: 0.5,
        }}
      >
        <Popper
          open={popperOpen}
          anchorEl={anchor}
          placement="left"
          disablePortal
          transition
          modifiers={[
            { name: 'offset', options: { offset: [0, 10] } },
            { name: 'preventOverflow', options: { padding: 8 } },
          ]}
        >
          {({ TransitionProps }) => (
            <Fade {...TransitionProps} timeout={200}>
              <Paper
                elevation={0}
                role="status"
                aria-live="polite"
                onMouseDown={(e) => e.stopPropagation()}
                sx={{
                  position: 'relative',
                  pl: 1,
                  pr: 1.25,
                  py: 0.4,
                  maxWidth: { xs: 'min(320px, calc(100vw - 88px))', sm: 360 },
                  borderRadius: 1,
                  // Subtle: let the map show through a little
                  bgcolor: 'rgba(255, 255, 255, 0.78)',
                  backdropFilter: 'blur(6px)',
                  border: 1,
                  borderColor: 'rgba(0, 0, 0, 0.08)',
                  boxShadow: '0 1px 3px rgba(0, 0, 0, 0.06)',
                  // Horizontal bar: one line on most viewports; max two very short lines on narrow
                  display: 'inline-block',
                }}
              >
                <Typography
                  color="text.secondary"
                  component="p"
                  title={MAP_CONTEXT_COACHMARK}
                  sx={{
                    m: 0,
                    lineHeight: 1.25,
                    fontSize: '0.62rem',
                    fontWeight: 500,
                    letterSpacing: '0.01em',
                    display: '-webkit-box',
                    WebkitLineClamp: 2,
                    WebkitBoxOrient: 'vertical',
                    overflow: 'hidden',
                  }}
                >
                  {MAP_CONTEXT_COACHMARK}
                </Typography>
                {/* Pointer toward the help button — match paper translucency */}
                <Box
                  aria-hidden
                  sx={{
                    position: 'absolute',
                    right: -5,
                    top: '50%',
                    transform: 'translateY(-50%)',
                    width: 0,
                    height: 0,
                    borderTop: '5px solid transparent',
                    borderBottom: '5px solid transparent',
                    borderLeft: '6px solid rgba(255, 255, 255, 0.78)',
                    filter: 'drop-shadow(0.5px 0 0 rgba(0, 0, 0, 0.07))',
                  }}
                />
              </Paper>
            </Fade>
          )}
        </Popper>
        <Tooltip
          title={MAP_CONTEXT_INFO_TOOLTIP}
          enterDelay={400}
          enterTouchDelay={0}
          placement="left"
          disableHoverListener={showCoach}
        >
          <span>
            <IconButton
              ref={setAnchor}
              size="small"
              onClick={handleOpen}
              aria-label={MAP_CONTEXT_INFO_ARIA}
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
