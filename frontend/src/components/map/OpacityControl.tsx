import { Typography, Slider } from '@mui/material'

interface OpacityControlProps {
  value: number
  onChange: (opacity: number) => void
}

export function OpacityControl({ value, onChange }: OpacityControlProps) {
  const handleChange = (_event: Event, newValue: number | number[]) => {
    onChange(newValue as number)
  }

  return (
    <>
      <Typography gutterBottom>Suitability layer opacity</Typography>
      <Slider
        value={value}
        onChange={handleChange}
        aria-label="Suitability layer opacity"
        valueLabelDisplay="auto"
        min={0}
        max={100}
      />
    </>
  )
} 