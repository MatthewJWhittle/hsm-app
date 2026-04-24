/**
 * TiTiler raster styling for suitability COGs; keep in sync with
 * `MapComponent` tile URL (`colormap_name`, `rescale`).
 */
export const COLORMAP_NAME = 'viridis' as const

export const SUITABILITY_RESCALE_MIN = 0
export const SUITABILITY_RESCALE_MAX = 1

/** Stops in ``SUITABILITY_VIRIDIS_GRADIENT_CSS`` (0 → 1 along the ramp). */
const VIRIDIS_STOPS_RGB: readonly [r: number, g: number, b: number][] = [
  [0x44, 0x01, 0x54],
  [0x47, 0x2d, 0x7b],
  [0x3b, 0x52, 0x8b],
  [0x2c, 0x72, 0x8e],
  [0x21, 0x91, 0x8c],
  [0x27, 0xad, 0x81],
  [0x5e, 0xc9, 0x62],
  [0xfd, 0xe7, 0x25],
]

function lerpByte(a: number, b: number, t: number): number {
  return Math.round(a + (b - a) * t)
}

/**
 * Interpolate matplotlib **viridis** to match the map tiles / gradient strip.
 * @param t Position in [0, 1] along the colormap
 */
export function viridisRgbAt(t: number): [number, number, number] {
  const c = Math.max(0, Math.min(1, t))
  const n = VIRIDIS_STOPS_RGB.length - 1
  const x = c * n
  const i = Math.min(Math.floor(x), n - 1)
  const f = x - i
  const p = VIRIDIS_STOPS_RGB[i]!
  const q = VIRIDIS_STOPS_RGB[i + 1]!
  return [lerpByte(p[0], q[0], f), lerpByte(p[1], q[1], f), lerpByte(p[2], q[2], f)]
}

export function viridisCssColor(t: number): string {
  const [r, g, b] = viridisRgbAt(t)
  return `rgb(${r}, ${g}, ${b})`
}

/** Number of **equal-width** 0-1 display bins for the **map** legend (compact; e.g. 0-0.2, …). */
export const SUITABILITY_DISPLAY_BIN_COUNT = 5

/** Denser **equal-width** bins for the point-inspection panel (wider strip). */
export const SUITABILITY_HUD_BIN_COUNT = 10

/** Bin boundary values for ``binCount`` equal segments from 0 to 1. */
export function suitabilityDisplayBinEdges(binCount: number): readonly number[] {
  if (!Number.isInteger(binCount) || binCount < 1) {
    throw new RangeError('binCount must be a positive integer')
  }
  return Array.from({ length: binCount + 1 }, (_, i) => i / binCount)
}

/** 0, 0.2, 0.4, 0.6, 0.8, 1 for the default map legend. */
export const SUITABILITY_DISPLAY_BIN_EDGES: readonly number[] = suitabilityDisplayBinEdges(SUITABILITY_DISPLAY_BIN_COUNT)

/**
 * Clamp suitability to [0, 1] for marker position vs TiTiler rescale.
 * Non-finite values map to 0 so UI does not break.
 */
export function clampSuitability01(n: number): number {
  if (!Number.isFinite(n)) return 0
  return Math.min(SUITABILITY_RESCALE_MAX, Math.max(SUITABILITY_RESCALE_MIN, n))
}

/**
 * Returns which equal-width 0-1 **display** bin a value lies in, `0 .. binCount-1`.
 * (Map rescale 0-1, not a population quantile.)
 */
export function suitabilityDisplayBinIndex01(v: number, binCount: number = SUITABILITY_DISPLAY_BIN_COUNT): number {
  if (!Number.isInteger(binCount) || binCount < 1) {
    throw new RangeError('binCount must be a positive integer')
  }
  const c = clampSuitability01(v)
  const w = 1 / binCount
  if (c >= 1) {
    return binCount - 1
  }
  return Math.min(binCount - 1, Math.floor(c / w))
}

/** Colours for each equal-width segment (viridis at bin **centre**). */
export function suitabilityDisplayBinSwatchColors(binCount: number = SUITABILITY_DISPLAY_BIN_COUNT): string[] {
  if (!Number.isInteger(binCount) || binCount < 1) {
    throw new RangeError('binCount must be a positive integer')
  }
  const w = 1 / binCount
  return Array.from({ length: binCount }, (_, k) => {
    const t = (k + 0.5) * w
    return viridisCssColor(t)
  })
}

/** CSS `background` value: horizontal viridis ramp (continuous fallback; binned UIs use ``suitabilityDisplayBinSwatchColors``). */
export const SUITABILITY_VIRIDIS_GRADIENT_CSS =
  'linear-gradient(to right, #440154, #472d7b, #3b528b, #2c728e, #21918c, #27ad81, #5ec962, #fde725)'
