/** Base URL for API calls. Dev: Vite proxies `/api` → backend. Production: Firebase Hosting rewrite. */
export function apiBase(): string {
  const configuredBase = import.meta.env.VITE_API_BASE?.trim()
  if (!configuredBase) return '/api'

  const trimmed = configuredBase.replace(/\/+$/, '')
  if (!trimmed) return '/api'
  if (trimmed === '/api' || trimmed.endsWith('/api')) return trimmed

  // Common misconfiguration: setting only the origin (for example https://...run.app).
  // Canonical API paths are /api/*, so append it automatically for absolute URLs.
  if (/^https?:\/\//i.test(trimmed)) return `${trimmed}/api`
  return trimmed
}

export function titilerBase(): string {
  return import.meta.env.VITE_TITILER_URL ?? 'http://localhost:8080'
}
