import { FormControl, InputLabel, Select, MenuItem } from '@mui/material'
import type { SelectChangeEvent } from '@mui/material'
import type { Model } from '../../types/model'

interface ModelSelectorProps {
  value: string
  models: Model[]
  onChange: (modelId: string) => void
  /** Defaults to "Model". */
  label?: string
}

export function ModelSelector({
  value,
  models,
  onChange,
  label = 'Model',
}: ModelSelectorProps) {
  const handleChange = (event: SelectChangeEvent) => {
    onChange(event.target.value)
  }

  const safeValue = models.some((m) => m.id === value) ? value : ''

  const labelId = 'map-suitability-model-label'

  return (
    <FormControl fullWidth size="small" sx={{ mb: 2 }}>
      <InputLabel id={labelId}>{label}</InputLabel>
      <Select
        value={safeValue}
        label={label}
        labelId={labelId}
        onChange={handleChange}
        aria-label={label}
      >
        {models.length === 0 ? (
          <MenuItem value="" disabled>
            No models in this project
          </MenuItem>
        ) : (
          models.map((m) => (
            <MenuItem key={m.id} value={m.id}>
              {m.species} — {m.activity}
            </MenuItem>
          ))
        )}
      </Select>
    </FormControl>
  )
}
