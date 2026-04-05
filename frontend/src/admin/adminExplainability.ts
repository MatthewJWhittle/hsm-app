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
 * Build ``driver_config`` JSON for POST/PUT. When explainability is disabled, strips SHAP-related
 * keys; ``band_labels`` from the form still apply (for raw value labels without influence).
 */
export function mergeDriverConfigForSubmit(
  existing: Record<string, unknown> | null | undefined,
  opts: { enabled: boolean; featureNamesCsv: string; bandLabelsCsv: string },
): string {
  const base: Record<string, unknown> = { ...(existing ?? {}) }
  if (!opts.enabled) {
    delete base['explainability_model_path']
    delete base['explainability_background_path']
    delete base['feature_names']
    delete base['explainability_positive_class']
  } else {
    const feature_names = opts.featureNamesCsv
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean)
    base['feature_names'] = feature_names
  }
  const bl = opts.bandLabelsCsv
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean)
  if (bl.length > 0) {
    base['band_labels'] = bl
  } else {
    delete base['band_labels']
  }
  return JSON.stringify(base)
}
