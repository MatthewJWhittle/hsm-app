import type { Model } from '../types/model'

/** Full layer label for UI (species · activity). */
export function layerDisplayName(m: Model): string {
  return `${m.species} · ${m.activity}`
}

const CARD_TITLE = (m: Model) => m.metadata?.card?.title?.trim() ?? ''

/**
 * Primary line for the layer picker: catalog card title if set, else species · activity.
 */
export function layerPrimaryLine(m: Model): string {
  const t = CARD_TITLE(m)
  const base = layerDisplayName(m)
  if (t) return t === base ? base : t
  return base
}

/**
 * Secondary line when a card title is used: the scientific name and activity.
 */
export function layerSecondaryLine(m: Model): string | null {
  const t = CARD_TITLE(m)
  if (!t) return null
  const base = layerDisplayName(m)
  if (t === base) return null
  return base
}

/**
 * String for MUI Autocomplete `getOptionLabel` (unique enough for the list).
 */
export function layerAutocompleteLabel(m: Model): string {
  const t = CARD_TITLE(m)
  const base = layerDisplayName(m)
  if (t) {
    if (t === base) return base
    return `${t} (${base})`
  }
  return base
}
