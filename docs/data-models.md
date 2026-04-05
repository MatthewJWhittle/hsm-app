# Data models

This document describes the data models for the MVP: resource-oriented APIs, stable model identity, and the shape of the catalog. Implementations: Pydantic (backend), TypeScript (frontend), and the shape of the catalog in Firestore or the index file.

---

## 1. Models (catalog)

The main resource is a **model**: one selectable layer (species + activity + suitability COG + optional metadata and driver data). COGs are produced elsewhere and added via the admin upload route; the **database stores where each model’s artifacts live**. Use a **sensible folder structure and naming** in storage so artifact paths are consistent and discoverable.

### Model (one selectable layer)

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | **Required.** Stable identifier assigned **once on create**. Prefer **server-generated opaque ids** (UUID or ULID) for robustness; structured slugs remain an alternative where human-readable ids are required. See [Admin scope decisions](admin-scope-decisions.md). |
| `project_id` | string? | **Catalog project** this model belongs to (Firestore `projects` collection). **Required** for new admin-created models; legacy documents may omit until migrated. |
| `species` | string | Display name (e.g. "Myotis daubentonii"). |
| `activity` | string | Display name (e.g. "In flight"). |
| `artifact_root` | string | **Required.** Base path or prefix in storage (GCS, etc.) for this model’s artifacts. All paths for this model are relative or derived from this (suitability COG, driver data). Enables a consistent folder-per-model layout. |
| `suitability_cog_path` | string | Path to the suitability COG (absolute or relative to `artifact_root`). Frontend/TiTiler use this for tiles. |
| `model_name` | string? | Optional. Model or run name (MVP: basic metadata). |
| `model_version` | string? | Optional. Model version or date. |
| `driver_band_indices` | int[]? | Optional typed subset: **0-based band indices** into the environmental COG (project stack or per-model file below). |
| `driver_config` | object? | Optional. **Server-persisted** JSON (set via admin `POST/PUT /models` or ingest), not supplied by map clients. See **driver_config keys** below. Links this model to driver/feature paths and display metadata. Prefer **`driver_band_indices`** when the stack is project-scoped. |

**Extensibility:** Add optional fields as needed (e.g. `taxon_id`, `meta` blob). Backend and frontend should ignore unknown keys so schema can evolve.

#### `driver_config` keys (point inspection)

These fields are read by the backend for `GET /models/{id}/point`. **Band indices** select which raster bands to sample; **feature names** align model inputs with those bands in order.

| Key | Type | Description |
|-----|------|-------------|
| `driver_cog_path` | string? | Optional. When the model does **not** use a project environmental stack (or to override), path to a multi-band COG **relative to `artifact_root`**, or absolute filesystem path in local dev. If omitted and `project_id` is set, the project’s `driver_artifact_root` + `driver_cog_path` is used. |
| `band_labels` or `band_names` | string[]? | Optional. Human-readable names for each index in `driver_band_indices` (same length), used for `raw_environmental_values` labels. |
| `band_units` | string[]? | Optional. Units per band (same length as indices) for display, e.g. `"m"`. |
| `feature_names` | string[]? | **Required for SHAP explainability.** Column names for the trained model, **same length and order** as `driver_band_indices` (each index samples one band; values become one row in this column order). |
| `explainability_model_path` | string? | Path to pickled **sklearn** estimator **relative to `artifact_root`**. The Admin “Variable influence” flow uploads to the fixed name `explainability_model.pkl`; JSON-only registration can use any safe single-segment filename. When set with `explainability_background_path` and `feature_names`, the API runs permutation SHAP and fills `PointInspection.drivers`. |
| `explainability_background_path` | string? | Path to **Parquet** background matrix **relative to `artifact_root`** (columns must include `feature_names`). Admin uploads use `explainability_background.parquet`. Used to reconstruct `shap.Explainer` (see training repo pattern). |
| `explainability_positive_class` | int? | Optional. Index of the positive class for `predict_proba` (default `1`). |

Admin `POST/PUT /models` accepts optional multipart fields `explainability_model_file` and `explainability_background_file`; the API stores them under the model’s `artifact_root` with the fixed relative names above and sets `driver_config` paths. It validates band indices against the environmental COG when possible, and—when explainability paths are set—that files exist and `feature_names` length matches `driver_band_indices`.

### Catalog project (shared environmental stack)

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | **Required.** Opaque id (Firestore document id). |
| `name` | string | Display name. |
| `description` | string? | Optional. |
| `status` | `active` \| `archived` | Archived projects are hidden from non-admin catalog readers. |
| `visibility` | `public` \| `private` | **Public** models are visible to anonymous catalog reads. **Private** restricts listing to **allowed_uids** (Firebase uids) and **admins**. |
| `allowed_uids` | string[] | When `visibility` is `private`, these uids may read the project and its models (via optional `Authorization: Bearer` on `GET /projects` and `GET /models`). |
| `driver_artifact_root` | string | Storage prefix for the project’s shared multi-band environmental COG. |
| `driver_cog_path` | string | Filename or path relative to `driver_artifact_root` (e.g. `environmental_cog.tif`). |

**Firestore:** Collection **`projects`**. **Models** stay in the top-level **`models`** collection and reference **`project_id`** (no subcollections for models under projects).

**Storage layout:** Local `{LOCAL_STORAGE_ROOT}/projects/{project_id}/environmental_cog.tif`; GCS mirror under `projects/{project_id}/` in the bucket.

**API:** `GET /models` returns a list of Model. `GET /models/{id}` returns one Model. Admin: `POST /models` (body: species, activity, **COG file upload**, optional metadata; backend assigns id, writes artifacts to a named folder structure, stores `artifact_root` and paths in DB), `PUT /models/{id}`. Registering a model by **path-only** (no upload) is not part of the first admin MVP — see [Admin scope decisions — §6](admin-scope-decisions.md#6-out-of-scope-for-the-first-admin-delivery-issue-9).

### Raster files, folders, and naming (uploads and storage)

Human-readable **species** and **activity** belong in the **catalog** (Firestore `Model` fields), not in a fragile filename convention. Object storage should use a layout that **scales** as you add models, retrain, and attach driver rasters: no global uniqueness in a single long filename, no parsing display names out of paths.

#### Recommended pattern (production and admin upload)

1. **One prefix per model** — Set `artifact_root` to a dedicated prefix for that model only, e.g. `gs://{bucket}/models/{model_id}/` (trailing slash implied in conventions below).
2. **Fixed blob names inside that prefix** — Use the **same basename** for the main suitability COG in every model folder, e.g. **`suitability_cog.tif`**. Uniqueness comes from **`model_id` in the path**, not from encoding the species in the filename. Store `suitability_cog_path` as the full object path or as relative to `artifact_root` (e.g. `suitability_cog.tif`), consistently.
3. **Optional sidecar files in the same prefix** — e.g. `drivers_cog.tif`, `metadata.json`, or other artifacts; reference them from `driver_config` or optional fields so names stay stable and discoverable.

This supports many models, retrains (new `model_id` or new version segment), and tooling that always looks for `…/suitability_cog.tif` under a known root.

#### `model_id` (stable identifier)

Assign **`id` once on create**; treat it as immutable for that logical model. It must be **unique**, **stable**, and **safe in URLs and object keys** (no spaces, minimal punctuation).

| Strategy | When to use | Shape (examples) |
|----------|-------------|------------------|
| **Opaque id** | Maximum robustness; no parsing | `mdl_01ARZ3NDEKTSV4RRFFQ69G5FAV` (ULID), or UUID with a short prefix |
| **Structured slug** | Human-readable buckets and logs | Lowercase **ASCII slug** segments separated by **`--` (double hyphen)** between major parts so single hyphens inside a segment stay unambiguous: e.g. `myotis-daubentonii--in-flight` |

Rules for structured slugs:

- Normalise unicode (e.g. NFC), map to lowercase ASCII where possible; replace spaces with single hyphens; strip or replace characters that are not `[a-z0-9-]`.
- Use **`--` only** between **taxon/concept** and **activity** (and optionally before a version segment), e.g. `myotis-daubentonii--in-flight--v2025-03` for a retrains or dated run.
- Cap length (e.g. ≤ 128 characters) so keys stay comfortable in Firestore and logs.

**Retrains / new versions:** Prefer a **new `model_id`** (or a new version segment in the slug) rather than overwriting objects in place, so historic links and audits stay meaningful unless you explicitly support replace-in-place.

#### What to avoid

- **Single flat directory** where the only differentiator is a long filename built from display strings (spaces, mixed case, arbitrary punctuation) — does not scale and is hard to make URL-safe.
- **Inferring species or activity by splitting on `_`** from filenames — breaks when taxon names contain underscores or variants; the catalog must hold display names.
- **Relying on filename alone** for identity — the database (`id` + paths) is the source of truth after upload.

#### Local development (transitional)

The repo may use a **flat** folder of COGs and a generated Firestore snapshot JSON for local Docker (`data/catalog/firestore_models.json`; see `scripts/generate_hsm_index.py`). That flow is a **dev shortcut**, not the target upload contract. **New data** and **admin uploads** should follow the **folder-per-model + `suitability_cog.tif`** pattern above; migrate or re-index local samples when moving off the flat layout.

### Upload validation (COG format and CRS)

Uploaded suitability rasters (and driver rasters referenced from `driver_config`) should be **validated before** the backend writes the final object and commits the `Model` to the catalog. Otherwise the map tiles, legend, and point inspection can fail in opaque ways.

#### Must pass (reject or quarantine if not met)

1. **Cloud Optimized GeoTIFF (COG)** — Not merely GeoTIFF with a `.tif` name: the file should conform to COG expectations (internal tiling, layout suitable for range reads and overviews) so TiTiler and object storage behave well. Prefer creating with `gdal_translate -of COG` (as in [`scripts/convert_to_cog.sh`](../scripts/convert_to_cog.sh)) or equivalent ([`rio cogeo`](https://cogeotiff.github.io/rio-cogeo/) and similar). Validation can use GDAL/rasterio checks for COG structure or delegate to a short-lived job that opens the file and asserts COG/geo metadata.
2. **Coordinate reference system** — **EPSG:3857 (WGS 84 / Pseudo-Mercator)** is the **contract** for suitability COGs served as web map tiles with MapLibre and TiTiler’s Web Mercator tile matrix. Reject files whose georeferencing is missing or whose CRS is not **3857** (unless you explicitly add a server-side reprojection step and document a different rule).  
   - *Rationale:* One expected CRS keeps tile URLs, bounds, and point-inspection alignment predictable. Local prep in this repo reprojects to 3857 before COG creation (see `convert_to_cog.sh`).  
   - If a source model is in another CRS (e.g. **EPSG:27700** for UK grids), **reproject to 3857 offline** (or in a dedicated ingest job) *before* validation passes — do not rely on the viewer to guess.

#### Should pass (warn or block depending on policy)

- **Overviews** — Present for COGs used at multiple zoom levels (typical COG creation includes overviews).
- **Compression** — Sensible compression (e.g. DEFLATE/LZW) and predictors where appropriate; avoids huge uncompressed objects in GCS.
- **Band count** — Suitability layer: usually **one** interpretable band for the main map; multi-band files need a defined **which band** is suitability (record in metadata or `driver_config`).

#### Expected artifact size (MVP)

Target **under ~100 MB** per suitability COG so direct upload + validation on Cloud Run stays simple; switch to signed/resumable GCS upload if files grow larger.

#### API behaviour

- **`POST /models` / file upload:** Run validation **after** upload to a temporary object or **before** promoting to `models/{model_id}/suitability_cog.tif`. On failure, return **4xx** with a **clear message** (e.g. “not a valid COG”, “CRS must be EPSG:3857, got EPSG:27700”). Do not register the `Model` until validation succeeds.
- **`PUT /models/{id}`** replacing the COG: same checks.
- Optionally store validation timestamp or checksum on the model document for audit.

### Driver and feature linkage

Drivers must be available to the API for point inspection. Each model is tied to a **specific set of features** (the environment variables / inputs that model was built with). Design options to capture in the data model:

- **Single multi-band COG:** One COG contains all driver variables (e.g. one band per feature). The model document specifies which **band names or feature ids** belong to this model. For `GET /models/{id}/point`, the API reads that subset at the requested location and returns DriverVariables. The “environment” (feature set) and the model are linked via this subset.
- **Per-model driver raster or lookup:** Each model has its own driver dataset (path in `driver_config`); no shared COG.
- **Shared multi-band environmental stack (common case for scaling):** A **single raster** (or stack) of environmental variables may be **shared** — e.g. scoped to a **project** or **reused across projects** — while each **model** still references only the **subset of bands/features** it uses via `driver_config`. Suitability outputs remain **per-model** under each model’s artifact prefix; driver **inputs** can point at shared storage without duplicating rasters per model.

The data model should record enough for the API to resolve “this model → these features at this point” (e.g. `driver_cog_path` + `feature_ids` or `band_names`). Exact shape can be refined when driver data format is fixed. See [Admin scope decisions](admin-scope-decisions.md) for steering.

### Catalog storage (target shape)

- **Firestore:** Collections **`projects`** (Catalog projects) and **`models`** (Model). Each document is one entity; **model** documents include **`project_id`** when applicable. No separate species/activities arrays; frontend derives dropdowns from the model list.
- **JSON snapshot (local Docker):** Firestore-shaped object with a **`documents`** array (one object per Model, `id` as document id). Optional metadata such as `generated_at`. The repo uses [`data/catalog/firestore_models.json`](../data/catalog/firestore_models.json); regenerate via `scripts/generate_hsm_index.py`.

---

## 2. Raster / layer metadata

### RasterMetadata (layer info for legend and map)

Used for legend (min/max, units), extent, and “what is this layer”. Can be fetched from TiTiler’s `/info` or `/statistics` and optionally cached.

| Field | Type | Description |
|-------|------|-------------|
| `band_min` | number? | Min value in band (e.g. suitability 0–1). |
| `band_max` | number? | Max value in band. |
| `crs` | string? | CRS identifier from the raster (for web tiles, suitability COGs are expected in **EPSG:3857**; see [upload validation](#upload-validation-cog-format-and-crs)). |
| `bounds` | [number, number, number, number]? | [minX, minY, maxX, maxY]. |
| `resolution` | number? | Pixel size (optional). |

**MVP:** Can be derived on the fly from TiTiler; add a formal response when exposing legend stats or extent via `GET /models/{id}/raster/metadata`.

---

## 3. Point inspection and driver explanation

### PointInspection (response for “value at a point”)

Returned by `GET /models/{id}/point?lng=&lat=` when the user clicks the map or requests inspection.

| Field | Type | Description |
|-------|------|-------------|
| `value` | number | Suitability at the point. |
| `unit` | string? | e.g. "suitability (0–1)" or "relative". |
| `drivers` | DriverVariable[] | Variable **influence** at this location (e.g. SHAP contribution); empty when explainability artefacts are not configured. |
| `raw_environmental_values` | RawEnvironmentalValue[]? | Optional sampled **raw** raster values for each configured band (secondary detail for the UI). |

### RawEnvironmentalValue (one sampled input)

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Label for the variable / band. |
| `value` | number | Raster value at the click. |
| `unit` | string? | Optional unit for display. |

### DriverVariable (one variable in the influence list)

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Variable name (matches model feature name). |
| `direction` | "increase" \| "decrease" \| "neutral" | Sign of contribution toward higher suitability at this point. |
| `label` | string? | Short display string (e.g. formatted contribution). |
| `magnitude` | number? | Signed contribution (e.g. SHAP value). |

**MVP:** PointInspection with `value`, optional `drivers` (influence), optional `raw_environmental_values`.

---

## 4. Optional / later

- **VectorLayer:** Overlay layers (e.g. protected areas). Fields: `id`, `name`, `source_url` or `path`. Keep as a separate type and API surface from Model so the map can mix raster layers (models) with N vector overlays without overloading the catalog.
- **InterpretationGuide:** If caveats/guidance are served from the API: e.g. `key`, `title`, `body`. MVP can use static frontend copy only.
- **User / Session:** Only if we add auth and saved state or sharing; out of scope for MVP.

---

## 5. Summary: target set to implement

| Model | Where used | MVP priority |
|-------|------------|--------------|
| **Model** | Catalog; `GET /models`, `GET /models/{id}`; admin POST/PUT | Required: `id`, species, activity, `artifact_root`, `suitability_cog_path`; optional model_name, model_version, driver_config. |
| **Catalog** | Firestore `models` collection or local JSON `documents[]` snapshot | Stored list of Model; id required. |
| **RasterMetadata** | `GET /models/{id}/raster/metadata` when needed | Optional in MVP. |
| **PointInspection** | Response of `GET /models/{id}/point` | Required for MVP. |
| **DriverVariable** | Inside PointInspection.drivers | Required for MVP (simple explanation). |

This gives a consistent, resource-oriented set of types for backend, frontend, and catalog storage.
