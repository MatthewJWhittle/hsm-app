/**
 * Stacking order for absolutely positioned map chrome (low → high).
 * Add new layers here so z-index stays intentional (avoids “random 1001” drift).
 */
export const MAP_OVERLAY_Z = {
  /** Frosted “Loading map…” over the canvas */
  loading: 900,
  /** Bottom-left corner suitability strip */
  cornerLegend: 998,
  /** Bottom-left “click the map” hint */
  clickHint: 999,
  /** Top-left floating controls and bottom-right point-inspection HUD (position keeps them apart) */
  floatingAndHud: 1000,
  /** Top-right catalog error + Retry */
  errorBanner: 1001,
  /** Top-right “what am I looking at?” help control */
  contextHelp: 1002,
} as const
