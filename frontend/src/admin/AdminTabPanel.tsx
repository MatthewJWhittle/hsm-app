import { Box } from '@mui/material'

export function AdminTabPanel(props: { children?: React.ReactNode; index: number; value: number }) {
  const { children, value, index, ...other } = props
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`admin-tabpanel-${index}`}
      aria-labelledby={`admin-tab-${index}`}
      {...other}
    >
      {/* Keep mounted so form state survives tab switches */}
      <Box sx={{ py: { xs: 2, sm: 2.5 } }}>{children}</Box>
    </div>
  )
}
