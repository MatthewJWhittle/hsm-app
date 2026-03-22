/** Base URL for API calls. Dev: Vite proxies `/api` → backend. Production: Firebase Hosting rewrite. */
export function apiBase(): string {
  return import.meta.env.VITE_API_BASE ?? '/api'
}

export function titilerBase(): string {
  return import.meta.env.VITE_TITILER_URL ?? 'http://localhost:8080'
}
