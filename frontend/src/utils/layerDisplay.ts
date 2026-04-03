import type { Model } from '../types/model'

/** Full layer label for UI (species — activity). */
export function layerDisplayName(m: Model): string {
  return `${m.species} — ${m.activity}`
}
