import { Box, Button, IconButton, Paper, Stack, Tooltip, Typography } from '@mui/material'
import RefreshIcon from '@mui/icons-material/Refresh'
import { Link } from 'react-router-dom'

type AdminCatalogHeaderProps = {
  lastRefreshedAt: Date | null
  listRefreshing: boolean
  onRefresh: () => void
}

export function AdminCatalogHeader({ lastRefreshedAt, listRefreshing, onRefresh }: AdminCatalogHeaderProps) {
  return (
    <Paper
      variant="outlined"
      sx={{
        p: 2,
        mb: 2,
        borderRadius: 2,
        display: 'flex',
        flexDirection: { xs: 'column', sm: 'row' },
        alignItems: { xs: 'stretch', sm: 'flex-start' },
        justifyContent: 'space-between',
        gap: 2,
      }}
    >
      <Box sx={{ flex: 1, minWidth: 0 }}>
        <Typography variant="h4" component="h1" fontWeight={700} sx={{ letterSpacing: '-0.02em' }}>
          Map catalog
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, maxWidth: 560 }}>
          Add <strong>projects</strong> to group layers and optional shared environmental data, then add{' '}
          <strong>map layers</strong> (suitability rasters). Published changes appear on the public map.
        </Typography>
      </Box>
      <Stack
        direction="row"
        alignItems="center"
        spacing={1}
        flexWrap="wrap"
        justifyContent={{ xs: 'flex-start', sm: 'flex-end' }}
        sx={{ flexShrink: 0 }}
      >
        <Typography variant="caption" color="text.secondary" sx={{ width: '100%', textAlign: { sm: 'right' } }}>
          {lastRefreshedAt
            ? `List updated ${lastRefreshedAt.toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' })}`
            : listRefreshing
              ? 'Loading…'
              : ''}
        </Typography>
        <Tooltip title="Reload list">
          <span>
            <IconButton
              size="small"
              onClick={() => void onRefresh()}
              disabled={listRefreshing}
              aria-label="Refresh list"
            >
              <RefreshIcon fontSize="small" />
            </IconButton>
          </span>
        </Tooltip>
        <Button component={Link} to="/" variant="outlined" size="medium">
          Back to map
        </Button>
      </Stack>
    </Paper>
  )
}
