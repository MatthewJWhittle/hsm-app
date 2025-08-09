import { FormControl, InputLabel, Select, MenuItem } from '@mui/material'
import type { SelectChangeEvent } from '@mui/material'

interface SpeciesSelectorProps {
  value: string
  onChange: (species: string) => void
}

export function SpeciesSelector({ value, onChange }: SpeciesSelectorProps) {
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
        <MenuItem value="bat">Bat</MenuItem>
        <MenuItem value="bird">Bird</MenuItem>
        <MenuItem value="mammal">Mammal</MenuItem>
      </Select>
    </FormControl>
  )
} 