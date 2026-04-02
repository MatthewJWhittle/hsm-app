function formatDetail(detail: unknown): string {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail
      .map((e) =>
        typeof e === 'object' && e !== null && 'msg' in e
          ? String((e as { msg: string }).msg)
          : JSON.stringify(e),
      )
      .join('; ')
  }
  if (detail && typeof detail === 'object' && 'detail' in detail) {
    return formatDetail((detail as { detail: unknown }).detail)
  }
  return 'Request failed'
}

/** FastAPI-style error body (`{ detail: ... }`) to a single message string. */
export function parseApiError(payload: unknown): string {
  if (payload && typeof payload === 'object' && 'detail' in payload) {
    return formatDetail((payload as { detail: unknown }).detail)
  }
  return 'Request failed'
}

/** Read JSON from a failed `fetch` response and turn it into a user-facing message. */
export async function readFetchErrorDetail(r: Response): Promise<string> {
  try {
    const raw: unknown = await r.json()
    return parseApiError(raw)
  } catch {
    return r.statusText || String(r.status)
  }
}
