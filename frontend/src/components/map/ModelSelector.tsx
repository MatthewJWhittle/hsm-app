import { FormControl, InputLabel, Select, MenuItem } from '@mui/material'
import type { SelectChangeEvent } from '@mui/material'
import type { Model } from '../../types/model'

interface ModelSelectorProps {
  value: string
  models: Model[]
  onChange: (modelId: string) => void
}

export function ModelSelector({ value, models, onChange }: ModelSelectorProps) {
  const handleChange = (event: SelectChangeEvent) => {
    onChange(event.target.value)
  }

  const safeValue = models.some((m) => m.id === value) ? value : ''

  return (
    <FormControl fullWidth size="small" sx={{ mb: 2 }}>
      <InputLabel>Model</InputLabel>
      <Select value={safeValue} label="Model" onChange={handleChange}>
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
