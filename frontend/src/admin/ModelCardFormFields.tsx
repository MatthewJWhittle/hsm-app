import AddIcon from '@mui/icons-material/Add'
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline'
import {
  Box,
  Button,
  Divider,
  FormControl,
  IconButton,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Stack,
  TextField,
  Typography,
} from '@mui/material'

import type { ModelCardDraft } from './modelCardDraft'
import { PRIMARY_METRIC_TYPES } from './modelCardDraft'
import { FIELD_HELP } from './catalogFormConstants'

function formatIsoForDisplay(iso: string | null | undefined): string {
  if (!iso?.trim()) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}

export type ModelCardFormFieldsProps = {
  maxWidth?: number
  draft: ModelCardDraft
  onDraftChange: (next: ModelCardDraft) => void
  disabled?: boolean
  species: string
  activity: string
  onSpeciesChange: (value: string) => void
  onActivityChange: (value: string) => void
  /** Server timestamps (edit only); shown read-only */
  catalogCreatedAt?: string | null
  catalogUpdatedAt?: string | null
}

export function ModelCardFormFields({
  maxWidth = 800,
  draft,
  onDraftChange,
  disabled = false,
  species,
  activity,
  onSpeciesChange,
  onActivityChange,
  catalogCreatedAt,
  catalogUpdatedAt,
}: ModelCardFormFieldsProps) {
  const patch = (partial: Partial<ModelCardDraft>) => {
    onDraftChange({ ...draft, ...partial })
  }

  const setExtraRow = (index: number, field: 'key' | 'value', value: string) => {
    const next = draft.extrasPairs.map((row, i) => (i === index ? { ...row, [field]: value } : row))
    patch({ extrasPairs: next })
  }

  const addExtraRow = () => {
    patch({ extrasPairs: [...draft.extrasPairs, { key: '', value: '' }] })
  }

  const removeExtraRow = (index: number) => {
    const next = draft.extrasPairs.filter((_, i) => i !== index)
    patch({ extrasPairs: next.length ? next : [{ key: '', value: '' }] })
  }

  const showTimestamps = catalogCreatedAt != null || catalogUpdatedAt != null

  return (
    <Paper variant="outlined" sx={{ p: 2, width: '100%', maxWidth, borderRadius: 2, mx: 'auto' }}>
      <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 0.5 }}>
        Model details
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        How this layer appears in the catalog. Species and activity define the map entry; add an optional display name
        and version label if helpful.
      </Typography>

      <Stack spacing={2}>
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
          <TextField
            required
            label="Species"
            helperText={FIELD_HELP.species}
            value={species}
            onChange={(e) => onSpeciesChange(e.target.value)}
            size="small"
            fullWidth
            disabled={disabled}
          />
          <TextField
            required
            label="Activity"
            helperText={FIELD_HELP.activity}
            value={activity}
            onChange={(e) => onActivityChange(e.target.value)}
            size="small"
            fullWidth
            disabled={disabled}
          />
        </Stack>

        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
          <TextField
            label="Display name"
            helperText="Optional short label in lists (e.g. product or run name)."
            value={draft.title}
            onChange={(e) => patch({ title: e.target.value })}
            size="small"
            fullWidth
            disabled={disabled}
          />
          <TextField
            label="Version label"
            helperText="Optional tag for this release (e.g. date or batch id)."
            value={draft.version}
            onChange={(e) => patch({ version: e.target.value })}
            size="small"
            fullWidth
            disabled={disabled}
          />
        </Stack>

        {showTimestamps && (
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
            <TextField
              label="Published"
              value={formatIsoForDisplay(catalogCreatedAt)}
              size="small"
              fullWidth
              disabled
              InputProps={{ readOnly: true }}
            />
            <TextField
              label="Last updated"
              value={formatIsoForDisplay(catalogUpdatedAt)}
              size="small"
              fullWidth
              disabled
              InputProps={{ readOnly: true }}
            />
          </Stack>
        )}

        <TextField
          label="Summary"
          helperText="Optional longer description for admins or public catalog text later."
          value={draft.summary}
          onChange={(e) => patch({ summary: e.target.value })}
          size="small"
          fullWidth
          multiline
          minRows={2}
          disabled={disabled}
        />

        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} alignItems="flex-start">
          <TextField
            label="Spatial resolution (m)"
            value={draft.spatialResolutionM}
            onChange={(e) => patch({ spatialResolutionM: e.target.value })}
            size="small"
            fullWidth
            disabled={disabled}
            placeholder="e.g. 25"
          />
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ flex: 1, width: '100%' }}>
            <FormControl size="small" sx={{ minWidth: 140 }} disabled={disabled}>
              <InputLabel id="primary-metric-type">Primary metric</InputLabel>
              <Select
                labelId="primary-metric-type"
                label="Primary metric"
                value={draft.primaryMetricType}
                onChange={(e) => patch({ primaryMetricType: String(e.target.value) })}
              >
                {PRIMARY_METRIC_TYPES.map((t) => (
                  <MenuItem key={t} value={t}>
                    {t}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            {draft.primaryMetricType === 'Custom' && (
              <TextField
                label="Metric name"
                value={draft.customMetricLabel}
                onChange={(e) => patch({ customMetricLabel: e.target.value })}
                size="small"
                disabled={disabled}
                sx={{ minWidth: 120 }}
              />
            )}
            <TextField
              label="Value"
              value={draft.primaryMetricValue}
              onChange={(e) => patch({ primaryMetricValue: e.target.value })}
              size="small"
              disabled={disabled}
              placeholder="e.g. 0.87"
              sx={{ flex: 1 }}
            />
          </Stack>
        </Stack>

        <Box>
          <Divider sx={{ my: 0.5 }} />
          <Typography variant="subtitle2" sx={{ fontWeight: 600, mt: 1.5, mb: 1 }}>
            Extra fields
          </Typography>
          <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1 }}>
            Optional key/value pairs (e.g. internal codes or contacts).
          </Typography>
          <Stack spacing={1}>
            {draft.extrasPairs.map((row, index) => (
              <Stack key={index} direction="row" spacing={1} alignItems="center">
                <TextField
                  label="Key"
                  value={row.key}
                  onChange={(e) => setExtraRow(index, 'key', e.target.value)}
                  size="small"
                  disabled={disabled}
                  sx={{ flex: 1 }}
                />
                <TextField
                  label="Value"
                  value={row.value}
                  onChange={(e) => setExtraRow(index, 'value', e.target.value)}
                  size="small"
                  disabled={disabled}
                  sx={{ flex: 1 }}
                />
                <IconButton
                  aria-label="Remove row"
                  size="small"
                  onClick={() => removeExtraRow(index)}
                  disabled={disabled}
                >
                  <DeleteOutlineIcon fontSize="small" />
                </IconButton>
              </Stack>
            ))}
            <Button startIcon={<AddIcon />} size="small" onClick={addExtraRow} disabled={disabled}>
              Add field
            </Button>
          </Stack>
        </Box>
      </Stack>
    </Paper>
  )
}
