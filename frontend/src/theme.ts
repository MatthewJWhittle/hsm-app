import { createTheme } from '@mui/material/styles'
import { brandPalette } from './brand/palette'

const { jungleTeal, dustyMauve, inkBlack } = brandPalette

/**
 * App-wide MUI theme tied to `brand/palette.ts`.
 * - **Primary (jungle teal):** main actions, focus rings, `primary` components.
 * - **Secondary (dusty mauve):** second accent, `secondary` components.
 * - **Text** uses ink black; page background a warm off-white to sit with the scheme.
 * - All-caps on buttons disabled, modest radius, Inter.
 */
export const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: jungleTeal,
      light: '#7ab3a1',
      dark: '#3b6a5c',
      contrastText: '#ffffff',
    },
    secondary: {
      main: dustyMauve,
      light: '#b08fa0',
      dark: '#6d4d60',
      contrastText: '#ffffff',
    },
    text: {
      primary: inkBlack,
      secondary: '#4d5056',
    },
    background: {
      default: '#f7f5f3',
      paper: '#ffffff',
    },
    divider: 'rgba(16, 20, 25, 0.12)',
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
