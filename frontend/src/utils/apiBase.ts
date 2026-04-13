/** Base URL for API calls. Dev: Vite proxies `/api` → backend. Production: Firebase Hosting rewrite. */
export function apiBase(): string {
  const configuredBase = import.meta.env.VITE_API_BASE?.trim()
  return configuredBase && configuredBase.length > 0 ? configuredBase : '/api'
}

export function titilerBase(): string {
  return import.meta.env.VITE_TITILER_URL ?? 'http://localhost:8080'
}
