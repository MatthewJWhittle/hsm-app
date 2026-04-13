import { apiBase } from '../utils/apiBase'

/**
 * Prefetch SHAP explainer + background into the API process cache when explainability is configured.
 * Fire-and-forget from the map when the active layer changes; failures are ignored.
 */
export async function postExplainabilityWarmup(
  modelId: string,
  signal?: AbortSignal,
  opts?: { token?: string | null },
): Promise<void> {
  const headers: Record<string, string> = {}
  if (opts?.token) headers.Authorization = `Bearer ${opts.token}`
  const r = await fetch(
    `${apiBase()}/models/${encodeURIComponent(modelId)}/explainability-warmup`,
    { method: 'POST', signal, headers },
  )
  if (r.status === 204) return
  if (r.ok) return
  // 404 / 403 etc.: do not throw for background prefetch
}
