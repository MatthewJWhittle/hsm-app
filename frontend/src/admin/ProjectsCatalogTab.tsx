import {
  Box,
  Button,
  Chip,
  Paper,
  Skeleton,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material'
import type { CatalogProject } from '../types/project'
import { formatAdminDate, shortId } from './adminUtils'

type ProjectsCatalogTabProps = {
  projects: CatalogProject[]
  filteredProjects: CatalogProject[]
  projectTableFilter: string
  onProjectTableFilterChange: (value: string) => void
  listRefreshing: boolean
  onNewProject: () => void
  onOpenProjectEdit: (p: CatalogProject) => void
}

export function ProjectsCatalogTab({
  projects,
  filteredProjects,
  projectTableFilter,
  onProjectTableFilterChange,
  listRefreshing,
  onNewProject,
  onOpenProjectEdit,
}: ProjectsCatalogTabProps) {
  return (
    <Stack spacing={3}>
      <Button variant="contained" onClick={onNewProject} sx={{ alignSelf: 'flex-start' }}>
        New project
      </Button>

      <Box>
        <Typography variant="subtitle1" fontWeight={700} sx={{ mb: 1 }}>
          All projects
        </Typography>
        <TextField
          size="small"
          fullWidth
          placeholder="Filter by name, id, or description…"
          value={projectTableFilter}
          onChange={(e) => onProjectTableFilterChange(e.target.value)}
          sx={{ mb: 1, maxWidth: 400 }}
          aria-label="Filter projects table"
        />
        <TableContainer
          component={Paper}
          variant="outlined"
          sx={{
            borderRadius: 1,
            maxHeight: 360,
          }}
        >
          <Table size="small" stickyHeader aria-label="Projects">
            <TableHead>
              <TableRow>
                <TableCell>Project</TableCell>
                <TableCell width={120}>Environmental file</TableCell>
                <TableCell width={110}>Visibility</TableCell>
                <TableCell width={100}>Status</TableCell>
                <TableCell width={140}>Updated</TableCell>
                <TableCell align="right" width={88}>
                  Actions
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {listRefreshing && projects.length === 0 ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <TableRow key={i}>
                    <TableCell colSpan={6}>
                      <Skeleton variant="text" width="80%" height={28} />
                    </TableCell>
                  </TableRow>
                ))
              ) : filteredProjects.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6}>
                    <Typography variant="body2" color="text.secondary" sx={{ py: 2 }}>
                      {projects.length === 0
                        ? 'No projects yet. Click New project to add one.'
                        : 'No projects match this filter.'}
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : (
                filteredProjects.map((p) => (
                  <TableRow
                    key={p.id}
                    hover
                    onClick={() => onOpenProjectEdit(p)}
                    sx={{ cursor: 'pointer' }}
                  >
                    <TableCell>
                      <Typography variant="body2" fontWeight={600}>
                        {p.name}
                      </Typography>
                      <Tooltip title={p.id}>
                        <Typography
                          variant="caption"
                          color="text.secondary"
                          fontFamily="monospace"
                          component="span"
                          sx={{ display: 'block' }}
                        >
                          {shortId(p.id)}
                        </Typography>
                      </Tooltip>
                    </TableCell>
                    <TableCell>
                      {p.driver_cog_path ? (
                        <Chip label="On file" size="small" color="success" variant="outlined" />
                      ) : (
                        <Chip label="None" size="small" variant="outlined" />
                      )}
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={p.visibility}
                        size="small"
                        color={p.visibility === 'public' ? 'primary' : 'default'}
                        variant="outlined"
                      />
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={p.status}
                        size="small"
                        color={p.status === 'active' ? 'success' : 'default'}
                        variant="outlined"
                      />
                    </TableCell>
                    <TableCell>
                      <Typography variant="caption" color="text.secondary">
                        {formatAdminDate(p.updated_at ?? p.created_at)}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      <Button
                        size="small"
                        onClick={(e) => {
                          e.stopPropagation()
                          onOpenProjectEdit(p)
                        }}
                      >
                        Edit
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </Box>
    </Stack>
  )
}
