import { createTheme } from '@mui/material/styles'

/**
 * App-wide MUI theme. Small, deliberate tweaks over the MUI defaults:
 * - disable ALL-CAPS button labels (preserve sentence case)
 * - modest corner radius (tighter than MUI’s previous 8px default here)
 * - Inter as the primary font (falls back to system stack if it fails to load)
 */
export const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1976d2',
    },
  },
  shape: {
    /** Base px value; components use multiples (e.g. `borderRadius: 2` → 2× this). */
    borderRadius: 4,
  },
  typography: {
    fontFamily:
      '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
  },
  components: {
    MuiButton: {
      defaultProps: {
        disableElevation: true,
      },
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontWeight: 500,
        },
      },
    },
    MuiToggleButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
        },
      },
    },
    MuiTab: {
      styleOverrides: {
        root: {
          textTransform: 'none',
        },
      },
    },
  },
})
