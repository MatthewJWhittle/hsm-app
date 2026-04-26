import AppBar from '@mui/material/AppBar'
import Box from '@mui/material/Box'
import ButtonBase from '@mui/material/ButtonBase'
import Toolbar from '@mui/material/Toolbar'
import Tooltip from '@mui/material/Tooltip'
import Typography from '@mui/material/Typography'
import { Link as RouterLink } from 'react-router-dom'

import { BrandMark } from './BrandMark'
import { UserMenu } from './UserMenu'

export interface NavbarProps {
  /**
   * Active map project for the current layer (subtle, non-interactive). Omit on routes
   * where it does not apply (e.g. admin).
   */
  currentProjectName?: string | null
}

export function Navbar({ currentProjectName }: NavbarProps) {
  const showProject = Boolean(currentProjectName?.trim())
  return (
    <AppBar
      position="static"
      color="inherit"
      elevation={0}
      sx={{
        flexShrink: 0,
        borderBottom: 1,
        borderColor: 'divider',
        bgcolor: 'background.paper',
      }}
    >
      <Toolbar variant="dense" sx={{ minHeight: 48, gap: 2, px: { xs: 1, sm: 2 } }}>
        <ButtonBase
          component={RouterLink}
          to="/"
          disableRipple
          sx={{
            display: 'flex',
            alignItems: 'center',
            gap: 1.25,
            py: 0.5,
            pr: 1,
            pl: 0.5,
            maxWidth: 'min(100%, 420px)',
            borderRadius: 1.5,
            color: 'text.primary',
            textAlign: 'left',
            transition: (theme) =>
              theme.transitions.create(['background-color'], { duration: theme.transitions.duration.shortest }),
            '&:hover': {
              bgcolor: 'action.hover',
            },
            '&:focus-visible': {
              outline: '2px solid',
              outlineColor: 'primary.main',
              outlineOffset: 2,
            },
          }}
          aria-label="HSM Explorer, home"
        >
          <BrandMark />
          <Box component="span" sx={{ minWidth: 0 }}>
            <Typography
              variant="subtitle1"
              component="span"
              sx={{
                fontWeight: 700,
                letterSpacing: '-0.03em',
                lineHeight: 1.25,
                display: 'block',
              }}
            >
              HSM Explorer
            </Typography>
          </Box>
        </ButtonBase>
        <Box sx={{ flex: 1 }} />
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            gap: 1.5,
            minWidth: 0,
            flexShrink: 1,
            justifyContent: 'flex-end',
          }}
        >
          {showProject && (
            <Tooltip title={`Current project: ${currentProjectName}`} placement="bottom">
              <Typography
                component="span"
                variant="caption"
                noWrap
                aria-label={`Current project, ${currentProjectName}`}
                sx={{
                  color: 'text.secondary',
                  maxWidth: { xs: 96, sm: 220, md: 300 },
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  fontSize: '0.7rem',
                  lineHeight: 1.2,
                  fontWeight: 500,
                  opacity: 0.88,
                  flexShrink: 1,
                  minWidth: 0,
                }}
              >
                {currentProjectName}
              </Typography>
            </Tooltip>
          )}
          <Box sx={{ flexShrink: 0 }}>
            <UserMenu />
          </Box>
        </Box>
      </Toolbar>
    </AppBar>
  )
}
