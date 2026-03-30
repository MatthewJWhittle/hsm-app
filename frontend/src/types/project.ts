/** Catalog project (issue #14) — shared environmental COG; models reference ``project_id``. */

export interface CatalogProject {
  id: string
  name: string
  description?: string | null
  status: 'active' | 'archived'
  visibility: 'public' | 'private'
  allowed_uids: string[]
  /** Set after environmental COG is uploaded. */
  driver_artifact_root?: string | null
  driver_cog_path?: string | null
  created_at?: string | null
  updated_at?: string | null
}
