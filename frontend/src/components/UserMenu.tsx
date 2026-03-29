import AdminPanelSettingsOutlinedIcon from '@mui/icons-material/AdminPanelSettingsOutlined'
import LogoutOutlinedIcon from '@mui/icons-material/LogoutOutlined'
import Avatar from '@mui/material/Avatar'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Dialog from '@mui/material/Dialog'
import DialogActions from '@mui/material/DialogActions'
import DialogContent from '@mui/material/DialogContent'
import DialogTitle from '@mui/material/DialogTitle'
import Divider from '@mui/material/Divider'
import IconButton from '@mui/material/IconButton'
import ListItemIcon from '@mui/material/ListItemIcon'
import ListItemText from '@mui/material/ListItemText'
import Menu from '@mui/material/Menu'
import MenuItem from '@mui/material/MenuItem'
import TextField from '@mui/material/TextField'
import Tooltip from '@mui/material/Tooltip'
import Typography from '@mui/material/Typography'
import { useId, useState } from 'react'

import { useAuth } from '../auth/useAuth'
import { firebaseWebConfigOk } from '../firebase/config'

function displayInitial(label: string): string {
  const c = label.trim()[0]
  return c ? c.toUpperCase() : '?'
}

export function UserMenu() {
  const { user, loading, isAdmin, signIn, signUp, signOutUser } = useAuth()
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null)
  const [signInOpen, setSignInOpen] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const formId = useId()

  const menuOpen = Boolean(anchorEl)

  if (!firebaseWebConfigOk()) {
    return (
      <Typography variant="caption" color="text.secondary" sx={{ maxWidth: 280 }}>
        Set Firebase web config (see frontend/.env.example)
      </Typography>
    )
  }

  if (loading) {
    return (
      <Typography variant="body2" color="text.secondary">
        …
      </Typography>
    )
  }

  const closeMenu = () => setAnchorEl(null)

  const onSignInDialog = async (mode: 'signIn' | 'signUp') => {
    setError(null)
    try {
      if (mode === 'signIn') {
        await signIn(email, password)
      } else {
        await signUp(email, password)
      }
      setSignInOpen(false)
      setEmail('')
      setPassword('')
    } catch (e: unknown) {
      const msg =
        e && typeof e === 'object' && 'message' in e && typeof e.message === 'string'
          ? e.message
          : 'Sign-in failed'
      setError(msg)
    }
  }

  if (!user) {
    return (
      <>
        <Button color="inherit" variant="outlined" size="small" onClick={() => setSignInOpen(true)}>
          Sign in
        </Button>
        <Dialog open={signInOpen} onClose={() => setSignInOpen(false)} maxWidth="xs" fullWidth>
          <DialogTitle>Sign in</DialogTitle>
          <DialogContent>
            <Box
              component="form"
              id={formId}
              sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 1 }}
              onSubmit={(e) => {
                e.preventDefault()
                void onSignInDialog('signIn')
              }}
            >
              <TextField
                label="Email"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                fullWidth
                size="small"
              />
              <TextField
                label="Password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                fullWidth
                size="small"
              />
              {error && (
                <Typography color="error" variant="caption" role="alert">
                  {error}
                </Typography>
              )}
            </Box>
          </DialogContent>
          <DialogActions sx={{ px: 3, pb: 2, gap: 1, flexWrap: 'wrap' }}>
            <Button onClick={() => setSignInOpen(false)}>Cancel</Button>
            <Button type="submit" form={formId} variant="contained">
              Sign in
            </Button>
            <Button
              onClick={() => void onSignInDialog('signUp')}
              disabled={!email || !password}
            >
              Create account
            </Button>
          </DialogActions>
        </Dialog>
      </>
    )
  }

  const label = user.email ?? user.uid

  return (
    <>
      <Tooltip title={label}>
        <IconButton
          size="small"
          onClick={(e) => setAnchorEl(e.currentTarget)}
          aria-controls={menuOpen ? 'user-menu' : undefined}
          aria-haspopup="true"
          aria-expanded={menuOpen ? 'true' : undefined}
          aria-label="Account menu"
          sx={{ borderRadius: 2, gap: 0.75, px: 0.75 }}
        >
          <Avatar sx={{ width: 28, height: 28, fontSize: '0.85rem' }}>
            {displayInitial(label)}
          </Avatar>
          <Typography
            variant="body2"
            component="span"
            sx={{
              maxWidth: { xs: 100, sm: 200 },
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              display: { xs: 'none', sm: 'inline' },
            }}
          >
            {label}
          </Typography>
        </IconButton>
      </Tooltip>
      <Menu
        id="user-menu"
        anchorEl={anchorEl}
        open={menuOpen}
        onClose={closeMenu}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
        transformOrigin={{ vertical: 'top', horizontal: 'right' }}
        slotProps={{ list: { dense: true } }}
      >
        <MenuItem disabled sx={{ opacity: 1, cursor: 'default' }}>
          <ListItemText primary={label} secondary="Signed in" />
        </MenuItem>
        {isAdmin && (
          <MenuItem component="a" href="/admin" onClick={closeMenu}>
            <ListItemIcon>
              <AdminPanelSettingsOutlinedIcon fontSize="small" />
            </ListItemIcon>
            <ListItemText>Admin</ListItemText>
          </MenuItem>
        )}
        <Divider />
        <MenuItem
          onClick={() => {
            closeMenu()
            void signOutUser()
          }}
        >
          <ListItemIcon>
            <LogoutOutlinedIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>Sign out</ListItemText>
        </MenuItem>
      </Menu>
    </>
  )
}
