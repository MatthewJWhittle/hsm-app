import type { Model } from '../types/model'

const COMMON_SPECIES_NAMES: Record<string, string> = {
  'Myotis brandtii': "Brandt's bat",
  'Myotis daubentonii': "Daubenton's bat",
  'Myotis mystacinus': 'Whiskered bat',
  'Myotis nattereri': "Natterer's bat",
  'Nyctalus leisleri': "Leisler's bat",
  'Nyctalus noctula': 'Noctule',
  'Pipistrellus pipistrellus': 'Common pipistrelle',
  'Pipistrellus pygmaeus': 'Soprano pipistrelle',
  'Plecotus auritus': 'Brown long-eared bat',
}

function speciesDisplayName(species: string): string {
  return COMMON_SPECIES_NAMES[species] ?? species
}

function activityDisplayName(activity: string): string {
  const normalized = activity.trim().toLowerCase()
  if (normalized === 'roost') return 'Roosting habitat'
  if (normalized === 'in flight') return 'Foraging and commuting habitat'
  return activity
}

/** Full layer label for UI (plain species/activity first where known). */
export function layerDisplayName(m: Model): string {
  return `${speciesDisplayName(m.species)} · ${activityDisplayName(m.activity)}`
}

const CARD_TITLE = (m: Model) => m.metadata?.card?.title?.trim() ?? ''

function scientificLayerName(m: Model): string {
  return `${m.species} · ${m.activity}`
}

/**
 * Primary line for the layer picker: plain species/activity beats technical catalog titles.
 */
export function layerPrimaryLine(m: Model): string {
  return layerDisplayName(m)
}

/**
 * Secondary line: scientific species/activity, then optional version.
 */
export function layerSecondaryLine(m: Model): string | null {
  const t = CARD_TITLE(m)
  const base = layerDisplayName(m)
  const scientific = scientificLayerName(m)
  const secondaryParts = [
    scientific !== base ? scientific : null,
    m.metadata?.card?.version?.trim() ?? null,
  ].filter(Boolean)
  if (secondaryParts.length > 0) return secondaryParts.join(' · ')
  if (t && t !== base) return t
  return null
}

/**
 * String for MUI Autocomplete `getOptionLabel` (unique enough for the list).
 */
export function layerAutocompleteLabel(m: Model): string {
  const base = layerDisplayName(m)
  const secondary = layerSecondaryLine(m)
  return secondary ? `${base} (${secondary})` : base
}
