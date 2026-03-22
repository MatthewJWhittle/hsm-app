import type { Model } from '../types/model'

/** Resolve absolute filesystem-style path for TiTiler `file://` URL (Docker: /data/...). */
export function resolveSuitabilityPath(model: Model): string {
  const p = model.suitability_cog_path
  if (p.startsWith('/')) return p
  const root = model.artifact_root.replace(/\/$/, '')
  return `${root}/${p}`
}
