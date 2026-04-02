# Issue #14 — Catalog projects: implementation steps

Branch: `issue/14-catalog-projects`  
Tracker: [GitHub #14](https://github.com/MatthewJWhittle/hsm-app/issues/14)

This document breaks the issue into ordered steps **before** coding. Adjust order if parallel work is needed.

---

## 0. Lock terminology and scope (docs-only)

- Document **catalog project** (ops grouping: shared env stack + models) vs **user workspace** (future; out of scope).
- Confirm **v1**: one shared multi-band environmental COG per catalog project; schema leaves room for multiple driver assets later.
- Note **pickle** / SHAP assets as **interim** only if introduced; file a follow-up for safer serialization.

---

## 1. Data model (design)

- Define **typed** Firestore shapes for:
  - **Catalog project** — id, display metadata, **shared driver COG** location (and later: optional extra assets), lifecycle fields (e.g. `active/archived`), timestamps.
  - **Model** — **scoped to a project id**, suitability artifact paths, **typed band/feature subset** (indices or names) pointing at the project’s shared stack.
- Avoid opaque JSON blobs as the **primary** source of truth for core behaviour; use explicit fields and nested objects.
- Decide **IDs**: opaque IDs (UUID/ULID) for projects and models (aligned with existing model ids).
- Align with [`docs/data-models.md`](data-models.md) and [`docs/admin-scope-decisions.md`](admin-scope-decisions.md).

---

## 2. Storage layout

- Specify where the **shared environmental COG** lives (per project prefix under `LOCAL_STORAGE_ROOT` / GCS bucket).
- Specify **per-model suitability COG** paths (existing pattern: folder per `model_id`).
- Document how **TiTiler** and the API resolve paths in dev (`file://`) vs prod (`gs://`).
- Validation rules: COG + **EPSG:3857** (and size limits) for driver uploads where applicable.

---

## 3. API surface (contract-first)

- **Admin-only** (Firebase `admin: true`):
  - Create / list / update / archive (or delete) catalog projects — minimal subset for v1.
  - Create / update models **within** a project (or explicit `project_id` on create).
- **Public or authenticated read** (decide): list projects and list models **for a project** for the main app.
- **OpenAPI** updates: request/response models, error shapes (`401`/`403`/`404`/`422`).
- **Stub or minimal** endpoint for **point-level explanation** scaffolding (future SHAP) — can return structured placeholder until real logic exists.

---

## 4. Firestore rules and indexes

- Update [`firestore.rules`](../firestore.rules) if collections or access patterns change.
- Add composite indexes in [`firestore.indexes.json`](../firestore.indexes.json) if queries need them (e.g. models by `project_id`).

---

## 5. Backend implementation (order suggested)

1. Pydantic / Firestore adapters for project + updated model documents.
2. Storage adapter: upload + path resolution for **project-level** driver COG.
3. Router(s): project CRUD + model CRUD scoped to project.
4. Catalog service: reload/list filters by project.
5. Point explanation **stub** (optional in same milestone): fixed shape, no real SHAP yet.

---

## 6. Admin UI

- Flow to **create/edit/archive** catalog projects.
- Flow to **create/edit** models under a project, including **suitability upload** and **typed band subset** for the shared stack (no reliance on raw JSON for essentials).
- Optional: **assign legacy** standalone models to a project (migration path only if needed).

---

## 7. User app UI

- **Select catalog project** → then **select model** → map (minimal vertical slice).
- Deep links / URL state: `?project=` & `?model=` (or equivalent) for shareability.

---

## 8. Seed, emulators, and tests

- **Seed data** / export path under `data/firestore-seed/` for local parity.
- **Pytest**: auth gates, CRUD, validation; storage mocked where appropriate.
- **Frontend tests** (if Vitest lands — see #7): optional smoke for project → model selection.

---

## 9. Acceptance criteria mapping (from #14)

| Criterion | Covered by |
|-----------|------------|
| Typed catalog shape for project + model | §1, §5 |
| Admin-only project creation; clear update/delete/archive rules | §3, §4, §6 |
| One shared driver COG per project (v1); extensible schema | §1, §2 |
| User selects project then model | §7 |
| Pickle interim documented + follow-up | §0 |
| User workspace noted as future, not implemented | §0 |

---

## 10. Out of scope (reminder)

- Full SHAP implementation and polished plots.
- **User workspace** / saved analysis sessions.
