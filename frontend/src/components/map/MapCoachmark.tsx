import { Box, Fade, Paper, Popper, Typography, type PopperPlacementType } from '@mui/material'
import type { ReactNode } from 'react'

type PointerSide = 'left' | 'right' | 'bottom'

interface MapCoachmarkProps {
  open: boolean
  anchorEl: HTMLElement | null
  id: string
  placement: PopperPlacementType
  pointerSide: PointerSide
  children: ReactNode
  maxWidth?: object | string | number
}

function pointerSx(pointerSide: PointerSide) {
  const base = {
    position: 'absolute',
    width: 0,
    height: 0,
  }

  if (pointerSide === 'right') {
    return {
      ...base,
      right: -5,
      top: '50%',
      transform: 'translateY(-50%)',
      borderTop: '5px solid transparent',
      borderBottom: '5px solid transparent',
      borderLeft: '6px solid rgba(255, 255, 255, 0.78)',
      filter: 'drop-shadow(0.5px 0 0 rgba(0, 0, 0, 0.07))',
    }
  }

  if (pointerSide === 'left') {
    return {
      ...base,
      left: -5,
      top: '50%',
      transform: 'translateY(-50%)',
      borderTop: '5px solid transparent',
      borderBottom: '5px solid transparent',
      borderRight: '6px solid rgba(255, 255, 255, 0.78)',
      filter: 'drop-shadow(-0.5px 0 0 rgba(0, 0, 0, 0.07))',
    }
  }

  return {
    ...base,
    bottom: -5,
    left: '50%',
    transform: 'translateX(-50%)',
    borderLeft: '5px solid transparent',
    borderRight: '5px solid transparent',
    borderTop: '6px solid rgba(255, 255, 255, 0.78)',
    filter: 'drop-shadow(0 0.5px 0 rgba(0, 0, 0, 0.07))',
  }
}

export function MapCoachmark({
  open,
  anchorEl,
  id,
  placement,
  pointerSide,
  children,
  maxWidth = { xs: 'min(320px, calc(100vw - 88px))', sm: 360 },
}: MapCoachmarkProps) {
  return (
    <Popper
      open={open && Boolean(anchorEl)}
      anchorEl={anchorEl}
      placement={placement}
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
            id={id}
            elevation={0}
            role="status"
            aria-live="polite"
            onMouseDown={(e) => e.stopPropagation()}
            sx={{
              position: 'relative',
              pl: 1,
              pr: 1.25,
              py: 0.4,
              maxWidth,
              borderRadius: 1,
              bgcolor: 'rgba(255, 255, 255, 0.78)',
              backdropFilter: 'blur(6px)',
              border: 1,
              borderColor: 'rgba(0, 0, 0, 0.08)',
              boxShadow: '0 1px 3px rgba(0, 0, 0, 0.06)',
              display: 'inline-block',
            }}
          >
            {typeof children === 'string' ? (
              <Typography
                color="text.secondary"
                component="p"
                title={children}
                sx={{
                  m: 0,
                  lineHeight: 1.25,
                  fontSize: '0.62rem',
                  fontWeight: 500,
                  letterSpacing: '0.01em',
                }}
              >
                {children}
              </Typography>
            ) : (
              children
            )}
            <Box aria-hidden sx={pointerSx(pointerSide)} />
          </Paper>
        </Fade>
      )}
    </Popper>
  )
}
