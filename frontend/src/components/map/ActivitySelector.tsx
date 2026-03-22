import { FormControl, InputLabel, Select, MenuItem } from '@mui/material'
import type { SelectChangeEvent } from '@mui/material'

interface ActivitySelectorProps {
  value: string
  options: string[]
  onChange: (activity: string) => void
}

export function ActivitySelector({ value, options, onChange }: ActivitySelectorProps) {
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
        {options.map((opt) => (
          <MenuItem key={opt} value={opt}>{opt}</MenuItem>
        ))}
      </Select>
    </FormControl>
  )
}