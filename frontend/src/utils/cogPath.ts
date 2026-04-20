import type { Model } from '../types/model'

/** Resolve absolute filesystem-style path for TiTiler `file://` URL (Docker: /data/...). */
export function resolveSuitabilityPath(model: Model): string {
  const p = model.suitability_cog_path
  if (p.startsWith('/')) return p
  const root = model.artifact_root.replace(/\/$/, '')
  return `${root}/${p}`
}

/**
 * Value for TiTiler's `url` query parameter.
 * - Cloud artifacts: pass `gs://...` through (not `file:///gs://...`, which is invalid).
 * - Local Docker: `/data/...` → `file:///data/...`.
 */
export function titilerRasterUrlParam(resolvedPath: string): string {
  const t = resolvedPath.trim()
  if (t.startsWith('gs://')) return t
  if (/^https?:\/\//i.test(t)) return t
  if (t.startsWith('/')) return `file://${t}`
  return `file:///${t.replace(/^\/+/, '')}`
}
