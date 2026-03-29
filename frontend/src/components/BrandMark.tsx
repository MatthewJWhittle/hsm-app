import SvgIcon from '@mui/material/SvgIcon'

/** Compact landscape mark for the nav; pairs with the wordmark (click target is the parent link). */
export function BrandMark() {
  return (
    <SvgIcon viewBox="0 0 32 32" sx={{ fontSize: 30, color: 'primary.main' }} aria-hidden>
      <path
        fill="currentColor"
        d="M26 22V10.5l-6 5.2-5-6.4-7 9.2V22h18z"
        opacity={0.92}
      />
      <path fill="currentColor" d="M4 23.5h24v3H4v-3z" opacity={0.35} />
    </SvgIcon>
  )
}
