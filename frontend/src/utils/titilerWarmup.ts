import { titilerBase } from './apiBase'

/**
 * Overlap TiTiler cold start with API catalog load (docs/issue-91-implementation-plan.md).
 * Fire-and-forget; failures are ignored (CORS or missing /health is OK).
 */
export function triggerTitilerWarmup(): void {
  const base = titilerBase().replace(/\/$/, '')
  if (!base) return
  const url = `${base}/health`
  fetch(url, { method: 'GET', mode: 'cors' }).catch(() => {})
}
