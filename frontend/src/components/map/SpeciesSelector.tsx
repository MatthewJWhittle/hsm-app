import { FormControl, InputLabel, Select, MenuItem } from '@mui/material'
import type { SelectChangeEvent } from '@mui/material'

interface SpeciesSelectorProps {
  value: string
  options: string[]
  onChange: (species: string) => void
}

export function SpeciesSelector({ value, options, onChange }: SpeciesSelectorProps) {
  const handleChange = (event: SelectChangeEvent) => {
    onChange(event.target.value)
  }

  return (
    <FormControl fullWidth size="small" sx={{ mb: 2 }}>
      <InputLabel>Species</InputLabel>
      <Select
        value={value}
        label="Species"
        onChange={handleChange}
      >
        {options.map((opt) => (
          <MenuItem key={opt} value={opt}>{opt}</MenuItem>
        ))}
      </Select>
    </FormControl>
  )
}