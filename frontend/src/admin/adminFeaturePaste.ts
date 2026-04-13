import type { EnvironmentalBandDefinition } from '../types/project'

/** Split pasted text into tokens (commas, semicolons, newlines). */
export function tokenizeFeaturePaste(raw: string): string[] {
  return raw
    .split(/[,;\n]+/)
    .map((s) => s.trim())
    .filter(Boolean)
}

/**
 * Match tokens to band definitions by machine ``name`` (case-insensitive) or exact ``label``.
 * Preserves token order; duplicates the same band if listed twice (matches training column order).
 */
export function bandsFromPasteTokens(
  tokens: string[],
  defs: EnvironmentalBandDefinition[],
): { matched: EnvironmentalBandDefinition[]; unknown: string[] } {
  const byName = new Map<string, EnvironmentalBandDefinition>()
  const byLabel = new Map<string, EnvironmentalBandDefinition>()
  for (const d of defs) {
    byName.set(d.name.toLowerCase(), d)
    if (d.label?.trim()) {
      byLabel.set(d.label.trim().toLowerCase(), d)
    }
  }
  const matched: EnvironmentalBandDefinition[] = []
  const unknown: string[] = []
  for (const t of tokens) {
    const low = t.toLowerCase()
    const a = byName.get(low) ?? byLabel.get(low)
    if (a) {
      matched.push(a)
    } else {
      unknown.push(t)
    }
  }
  return { matched, unknown }
}
