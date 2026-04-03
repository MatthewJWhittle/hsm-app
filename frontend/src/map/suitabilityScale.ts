/**
 * TiTiler raster styling for suitability COGs — keep in sync with
 * `MapComponent` tile URL (`colormap_name`, `rescale`).
 */
export const COLORMAP_NAME = 'viridis' as const

export const SUITABILITY_RESCALE_MIN = 0
export const SUITABILITY_RESCALE_MAX = 1

/** CSS `background` value: horizontal viridis ramp (matches matplotlib viridis for legend UI). */
export const SUITABILITY_VIRIDIS_GRADIENT_CSS =
  'linear-gradient(to right, #440154, #472d7b, #3b528b, #2c728e, #21918c, #27ad81, #5ec962, #fde725)'

/**
 * Clamp suitability to [0, 1] for marker position vs TiTiler rescale.
 * Non-finite values map to 0 so UI does not break.
 */
export function clampSuitability01(n: number): number {
  if (!Number.isFinite(n)) return 0
  return Math.min(SUITABILITY_RESCALE_MAX, Math.max(SUITABILITY_RESCALE_MIN, n))
}
