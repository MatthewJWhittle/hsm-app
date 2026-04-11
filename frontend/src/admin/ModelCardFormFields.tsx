import { Box, Divider, Paper, Stack, TextField, Typography } from '@mui/material'

import type { ModelCardDraft } from './modelCardDraft'
import { FIELD_HELP } from './catalogFormConstants'

export type ModelCardFormFieldsProps = {
  maxWidth?: number
  draft: ModelCardDraft
  onDraftChange: (next: ModelCardDraft) => void
  disabled?: boolean
}

export function ModelCardFormFields({
  maxWidth = 640,
  draft,
  onDraftChange,
  disabled = false,
}: ModelCardFormFieldsProps) {
  const patch = (partial: Partial<ModelCardDraft>) => {
    onDraftChange({ ...draft, ...partial })
  }

  return (
    <Paper variant="outlined" sx={{ p: 2, maxWidth, borderRadius: 2 }}>
      <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 0.5 }}>
        Model card
      </Typography>
      <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 2 }}>
        Optional catalog subtitle and documentation (stored under metadata.card). Species and activity identify the
        layer; this block is for display names, revision labels, and notes.
      </Typography>
      <Stack spacing={2}>
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
          <TextField
            label="Title"
            helperText={FIELD_HELP.cardTitle}
            value={draft.title}
            onChange={(e) => patch({ title: e.target.value })}
            size="small"
            fullWidth
            disabled={disabled}
          />
          <TextField
            label="Version"
            helperText={FIELD_HELP.cardVersion}
            value={draft.version}
            onChange={(e) => patch({ version: e.target.value })}
            size="small"
            fullWidth
            disabled={disabled}
          />
        </Stack>
        <TextField
          label="Summary"
          value={draft.summary}
          onChange={(e) => patch({ summary: e.target.value })}
          size="small"
          fullWidth
          multiline
          minRows={2}
          disabled={disabled}
        />
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
          <TextField
            label="Spatial resolution (m)"
            value={draft.spatialResolutionM}
            onChange={(e) => patch({ spatialResolutionM: e.target.value })}
            size="small"
            fullWidth
            disabled={disabled}
            placeholder="e.g. 25"
          />
          <TextField
            label="Training period"
            value={draft.trainingPeriod}
            onChange={(e) => patch({ trainingPeriod: e.target.value })}
            size="small"
            fullWidth
            disabled={disabled}
            placeholder="e.g. 2018–2022"
          />
        </Stack>
        <TextField
          label="Evaluation notes"
          value={draft.evaluationNotes}
          onChange={(e) => patch({ evaluationNotes: e.target.value })}
          size="small"
          fullWidth
          multiline
          minRows={2}
          disabled={disabled}
        />
        <TextField
          label="Metrics (JSON object)"
          value={draft.metricsJson}
          onChange={(e) => patch({ metricsJson: e.target.value })}
          size="small"
          fullWidth
          multiline
          minRows={3}
          disabled={disabled}
          placeholder='e.g. { "auc": 0.91, "f1": 0.85 }'
          helperText="Optional. Must be a JSON object with string or number values."
        />
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
          <TextField
            label="License"
            value={draft.license}
            onChange={(e) => patch({ license: e.target.value })}
            size="small"
            fullWidth
            disabled={disabled}
          />
          <TextField
            label="Citation"
            value={draft.citation}
            onChange={(e) => patch({ citation: e.target.value })}
            size="small"
            fullWidth
            disabled={disabled}
          />
        </Stack>
        <Box>
          <Divider sx={{ my: 0.5 }} />
          <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1.5, mb: 1 }}>
            Custom string fields (optional)
          </Typography>
          <TextField
            label="Extras (JSON object)"
            value={draft.extrasJson}
            onChange={(e) => patch({ extrasJson: e.target.value })}
            size="small"
            fullWidth
            multiline
            minRows={2}
            disabled={disabled}
            placeholder='e.g. { "team": "ecology", "contact": "…" }'
            helperText="Optional key/value map; values are stored as strings."
          />
        </Box>
      </Stack>
    </Paper>
  )
}
