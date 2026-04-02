import {
  Alert,
  Box,
  Button,
  Checkbox,
  Chip,
  FormControl,
  InputLabel,
  LinearProgress,
  MenuItem,
  Paper,
  Select,
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
import type { Model } from '../types/model'
import type { CatalogProject } from '../types/project'
import { shortId } from './adminUtils'

type LayersCatalogTabProps = {
  models: Model[]
  filteredModels: Model[]
  projectById: Map<string, string>
  modelTableFilter: string
  onModelTableFilterChange: (value: string) => void
  listRefreshing: boolean
  onNewLayer: () => void
  onOpenEdit: (m: Model) => void
  selectedModelIds: string[]
  bulkAssignProjectId: string
  onBulkAssignProjectIdChange: (id: string) => void
  bulkAssigning: boolean
  bulkAssignError: string | null
  onBulkAssign: () => void
  onClearSelection: () => void
  toggleModelSelected: (id: string) => void
  toggleSelectAllFiltered: () => void
  allFilteredSelected: boolean
  someFilteredSelected: boolean
  activeProjects: CatalogProject[]
  canAddModel: boolean
}

export function LayersCatalogTab({
  models,
  filteredModels,
  projectById,
  modelTableFilter,
  onModelTableFilterChange,
  listRefreshing,
  onNewLayer,
  onOpenEdit,
  selectedModelIds,
  bulkAssignProjectId,
  onBulkAssignProjectIdChange,
  bulkAssigning,
  bulkAssignError,
  onBulkAssign,
  onClearSelection,
  toggleModelSelected,
  toggleSelectAllFiltered,
  allFilteredSelected,
  someFilteredSelected,
  activeProjects,
  canAddModel,
}: LayersCatalogTabProps) {
  return (
    <Stack spacing={3}>
      <Button variant="contained" onClick={onNewLayer} sx={{ alignSelf: 'flex-start' }}>
        New layer
      </Button>

      <Box>
        <Typography variant="subtitle1" fontWeight={700} sx={{ mb: 1 }}>
          All map layers
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1, maxWidth: 560 }}>
          Select one or more layers with the checkboxes, then choose a project and click Assign to project.
        </Typography>
        <TextField
          size="small"
          fullWidth
          placeholder="Filter by species, activity, project…"
          value={modelTableFilter}
          onChange={(e) => onModelTableFilterChange(e.target.value)}
          sx={{ mb: 1, maxWidth: 400 }}
          aria-label="Filter map layers table"
        />
        {selectedModelIds.length > 0 && (
          <Paper
            variant="outlined"
            sx={{
              p: 1.5,
              mb: 1,
              borderRadius: 1,
              position: 'relative',
              overflow: 'hidden',
            }}
          >
            {bulkAssigning && (
              <LinearProgress
                sx={{ position: 'absolute', top: 0, left: 0, right: 0 }}
                aria-label="Assigning layers to project"
              />
            )}
            <Stack
              direction={{ xs: 'column', sm: 'row' }}
              spacing={1.5}
              alignItems={{ sm: 'center' }}
              flexWrap="wrap"
              useFlexGap
              sx={{ pt: bulkAssigning ? 0.5 : 0 }}
            >
              <Typography variant="body2" fontWeight={600}>
                {selectedModelIds.length} layer{selectedModelIds.length === 1 ? '' : 's'} selected
              </Typography>
              <FormControl size="small" sx={{ minWidth: 220 }} disabled={bulkAssigning || !canAddModel}>
                <InputLabel id="bulk-assign-project-label">Assign to project</InputLabel>
                <Select
                  labelId="bulk-assign-project-label"
                  label="Assign to project"
                  value={bulkAssignProjectId}
                  onChange={(e) => onBulkAssignProjectIdChange(e.target.value)}
                >
                  {activeProjects.map((p) => (
                    <MenuItem key={p.id} value={p.id}>
                      {p.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              <Button
                variant="contained"
                size="small"
                disabled={
                  bulkAssigning || !bulkAssignProjectId || selectedModelIds.length === 0 || !canAddModel
                }
                onClick={() => void onBulkAssign()}
              >
                {bulkAssigning ? 'Assigning…' : 'Assign to project'}
              </Button>
              <Button variant="text" size="small" disabled={bulkAssigning} onClick={onClearSelection}>
                Clear selection
              </Button>
            </Stack>
            {!canAddModel && (
              <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
                Create an active project in the Projects tab first.
              </Typography>
            )}
            {bulkAssignError && (
              <Alert severity="error" sx={{ mt: 1.5, mb: 0 }}>
                {bulkAssignError}
              </Alert>
            )}
          </Paper>
        )}
        <TableContainer
          component={Paper}
          variant="outlined"
          sx={{
            borderRadius: 1,
            maxHeight: 480,
          }}
        >
          <Table size="small" stickyHeader aria-label="Map layers">
            <TableHead>
              <TableRow>
                <TableCell padding="checkbox" sx={{ width: 48 }}>
                  <Checkbox
                    size="small"
                    indeterminate={someFilteredSelected && !allFilteredSelected}
                    checked={allFilteredSelected}
                    onChange={toggleSelectAllFiltered}
                    disabled={listRefreshing || filteredModels.length === 0}
                    inputProps={{
                      'aria-label': 'Select all layers in this list',
                    }}
                  />
                </TableCell>
                <TableCell width={100}>ID</TableCell>
                <TableCell width={160}>Project</TableCell>
                <TableCell>Species</TableCell>
                <TableCell>Activity</TableCell>
                <TableCell>Name / version</TableCell>
                <TableCell align="right" width={88}>
                  Actions
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {listRefreshing && models.length === 0 ? (
                Array.from({ length: 6 }).map((_, i) => (
                  <TableRow key={i}>
                    <TableCell colSpan={7}>
                      <Skeleton variant="text" width="70%" height={28} />
                    </TableCell>
                  </TableRow>
                ))
              ) : filteredModels.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7}>
                    <Typography variant="body2" color="text.secondary" sx={{ py: 2 }}>
                      {models.length === 0
                        ? 'No layers yet. Create a project first, then click New layer to add one.'
                        : 'No layers match this filter.'}
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : (
                filteredModels.map((m) => {
                  const projectLabel = m.project_id
                    ? (projectById.get(m.project_id) ?? shortId(m.project_id))
                    : 'Stand-alone'
                  return (
                    <TableRow key={m.id} hover onClick={() => onOpenEdit(m)} sx={{ cursor: 'pointer' }}>
                      <TableCell padding="checkbox" onClick={(e) => e.stopPropagation()}>
                        <Checkbox
                          size="small"
                          checked={selectedModelIds.includes(m.id)}
                          onChange={() => toggleModelSelected(m.id)}
                          inputProps={{ 'aria-label': `Select layer ${m.species} — ${m.activity}` }}
                        />
                      </TableCell>
                      <TableCell>
                        <Tooltip title={m.id}>
                          <Typography variant="body2" fontFamily="monospace" fontSize={12} sx={{ cursor: 'default' }}>
                            {shortId(m.id)}
                          </Typography>
                        </Tooltip>
                      </TableCell>
                      <TableCell>
                        {m.project_id ? (
                          <Typography variant="body2" noWrap title={projectLabel}>
                            {projectLabel}
                          </Typography>
                        ) : (
                          <Chip label="Stand-alone" size="small" variant="outlined" />
                        )}
                      </TableCell>
                      <TableCell>{m.species}</TableCell>
                      <TableCell>{m.activity}</TableCell>
                      <TableCell>
                        {[m.model_name, m.model_version].filter(Boolean).join(' · ') || '—'}
                      </TableCell>
                      <TableCell align="right">
                        <Button
                          size="small"
                          onClick={(e) => {
                            e.stopPropagation()
                            onOpenEdit(m)
                          }}
                        >
                          Edit
                        </Button>
                      </TableCell>
                    </TableRow>
                  )
                })
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </Box>
    </Stack>
  )
}
