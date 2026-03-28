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

  return (
    <FormControl fullWidth size="small" sx={{ mb: 2 }}>
      <InputLabel>Model</InputLabel>
      <Select value={value} label="Model" onChange={handleChange}>
        {models.map((m) => (
          <MenuItem key={m.id} value={m.id}>
            {m.species} — {m.activity}
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  )
}
