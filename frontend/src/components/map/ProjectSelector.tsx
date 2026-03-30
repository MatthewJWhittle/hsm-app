import { FormControl, InputLabel, Select, MenuItem } from '@mui/material'
import type { SelectChangeEvent } from '@mui/material'

export interface ProjectOption {
  id: string
  name: string
}

interface ProjectSelectorProps {
  value: string
  options: ProjectOption[]
  onChange: (projectId: string) => void
}

export function ProjectSelector({ value, options, onChange }: ProjectSelectorProps) {
  const handleChange = (event: SelectChangeEvent) => {
    onChange(event.target.value)
  }

  return (
    <FormControl fullWidth size="small" sx={{ mb: 2 }}>
      <InputLabel>Project</InputLabel>
      <Select value={value} label="Project" onChange={handleChange}>
        {options.map((o) => (
          <MenuItem key={o.id} value={o.id}>
            {o.name}
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  )
}
