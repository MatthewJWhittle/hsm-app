import { FormControl, InputLabel, Select, MenuItem } from '@mui/material'
import type { SelectChangeEvent } from '@mui/material'

interface ActivitySelectorProps {
  value: string
  onChange: (activity: string) => void
}

export function ActivitySelector({ value, onChange }: ActivitySelectorProps) {
  const handleChange = (event: SelectChangeEvent) => {
    onChange(event.target.value)
  }

  return (
    <FormControl fullWidth size="small" sx={{ mb: 2 }}>
      <InputLabel>Activity</InputLabel>
      <Select
        value={value}
        label="Activity"
        onChange={handleChange}
      >
        <MenuItem value="foraging">Foraging</MenuItem>
        <MenuItem value="roosting">Roosting</MenuItem>
        <MenuItem value="commuting">Commuting</MenuItem>
      </Select>
    </FormControl>
  )
} 