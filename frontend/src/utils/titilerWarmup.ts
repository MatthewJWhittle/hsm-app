import { titilerBase } from './apiBase'

/**
 * Overlap TiTiler cold start with API catalog load (docs/issue-91-implementation-plan.md).
 * Stock titiler.application exposes FastAPI's `/openapi.json`; `/` may exist depending on deploy.
 * Fire-and-forget; failures are ignored (CORS, etc.).
 */
export function triggerTitilerWarmup(): void {
  const base = titilerBase().replace(/\/$/, '')
  if (!base) return
  const openApiUrl = `${base}/openapi.json`
  const rootUrl = `${base}/`
  fetch(openApiUrl, { method: 'GET', mode: 'cors' })
    .catch(() => fetch(rootUrl, { method: 'GET', mode: 'cors' }))
    .catch(() => {})
}
