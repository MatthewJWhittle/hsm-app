import type { Model } from '../types/model'

/** Matches backend ``explainability_configured`` / catalog readiness for map influence. */
export function explainabilityConfiguredInCatalog(model: Model): boolean {
  const dc = model.driver_config
  if (!dc || typeof dc !== 'object') return false
  const mp = dc['explainability_model_path']
  const bp = dc['explainability_background_path']
  const fn = dc['feature_names']
  return (
    typeof mp === 'string' &&
    mp.trim() !== '' &&
    typeof bp === 'string' &&
    bp.trim() !== '' &&
    Array.isArray(fn) &&
    fn.length > 0
  )
}

/**
 * Build ``driver_config`` JSON for POST/PUT. Only adjusts explainability file paths;
 * ``feature_names`` / ``band_labels`` are set by the API from the project band manifest.
 */
export function mergeDriverConfigForSubmit(
  existing: Record<string, unknown> | null | undefined,
  opts: { enabled: boolean },
): string {
  const base: Record<string, unknown> = { ...(existing ?? {}) }
  if (!opts.enabled) {
    delete base['explainability_model_path']
    delete base['explainability_background_path']
    delete base['explainability_background_artifact_root']
    delete base['explainability_positive_class']
  }
  return JSON.stringify(base)
}
