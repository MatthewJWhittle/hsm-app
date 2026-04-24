/** Shorten ids for dense table display. */
export function shortId(id: string, head = 8): string {
  if (id.length <= head + 2) return id
  return `${id.slice(0, head)}…`
}

export function formatAdminDate(iso: string | null | undefined): string {
  if (!iso) return '-'
  try {
    const d = new Date(iso)
    if (Number.isNaN(d.getTime())) return '-'
    return d.toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' })
  } catch {
    return '-'
  }
}
