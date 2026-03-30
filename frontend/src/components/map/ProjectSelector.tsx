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
  /** Defaults to "Project". */
  label?: string
}

export function ProjectSelector({
  value,
  options,
  onChange,
  label = 'Project',
}: ProjectSelectorProps) {
  const handleChange = (event: SelectChangeEvent) => {
    onChange(event.target.value)
  }

  const labelId = 'map-catalog-project-label'

  return (
    <FormControl fullWidth size="small" sx={{ mb: 2 }}>
      <InputLabel id={labelId}>{label}</InputLabel>
      <Select value={value} label={label} labelId={labelId} onChange={handleChange}>
        {options.map((o) => (
          <MenuItem key={o.id} value={o.id}>
            {o.name}
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  )
}
