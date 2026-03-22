# Data models

This document describes the data models for the MVP: resource-oriented APIs, stable model identity, and the shape of the catalog. Implementations: Pydantic (backend), TypeScript (frontend), and the shape of the catalog in Firestore or the index file.

---

## 1. Models (catalog)

The main resource is a **model**: one selectable layer (species + activity + suitability COG + optional metadata and driver data). COGs are produced elsewhere and added via the admin upload route; the **database stores where each model’s artifacts live**. Use a **sensible folder structure and naming** in storage so artifact paths are consistent and discoverable.

### Model (one selectable layer)

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | **Required.** Stable identifier (e.g. slug: `myotis_daubentonii_in_flight`). Assigned once on create. |
| `species` | string | Display name (e.g. "Myotis daubentonii"). |
| `activity` | string | Display name (e.g. "In flight"). |
| `artifact_root` | string | **Required.** Base path or prefix in storage (GCS, etc.) for this model’s artifacts. All paths for this model are relative or derived from this (suitability COG, driver data). Enables a consistent folder-per-model layout. |
| `suitability_cog_path` | string | Path to the suitability COG (absolute or relative to `artifact_root`). Frontend/TiTiler use this for tiles. |
| `model_name` | string? | Optional. Model or run name (MVP: basic metadata). |
| `model_version` | string? | Optional. Model version or date. |
| `driver_config` | object? | Optional. Links this model to driver/feature data: e.g. path to a multi-band COG or driver raster, plus the **subset of features (band names or feature ids) that this model uses**. Needed because each model depends on a specific set of features; the API must know which subset to read for point inspection. See “Driver and feature linkage” below. |

**Extensibility:** Add optional fields as needed (e.g. `taxon_id`, `meta` blob). Backend and frontend should ignore unknown keys so schema can evolve.

**API:** `GET /models` returns a list of Model. `GET /models/{id}` returns one Model. Admin: `POST /models` (body: species, activity, COG upload or path, optional metadata; backend assigns id, writes artifacts to a named folder structure, stores `artifact_root` and paths in DB), `PUT /models/{id}`.

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

The data model should record enough for the API to resolve “this model → these features at this point” (e.g. `driver_cog_path` + `feature_ids` or `band_names`). Exact shape can be refined when driver data format is fixed.

### Catalog storage (target shape)

- **Firestore:** Collection `models`; each document = one Model (id as document id or field). No separate species/activities arrays; frontend derives dropdowns from the model list.
- **JSON index (e.g. for local or transition):** `{ "generated_at": string, "models": Model[] }`. Optional: `species[]`, `activities[]` derived when writing the file for backward compatibility or quick filters. Normalise so each (species, activity) appears once; id is unique and stable.

When using a JSON index, use `models[]` with each entry including a stable id; optional `species[]`/`activities[]` can be derived for convenience.

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
| `value` | number | Suitability (or band value) at the point. |
| `unit` | string? | e.g. "suitability (0–1)" or "relative". |
| `drivers` | DriverVariable[]? | Main variables contributing at this location (MVP: simple explanation). |

### DriverVariable (one variable in the explanation)

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Variable or factor name (e.g. "Land cover", "Distance to water"). |
| `direction` | "increase" \| "decrease" \| "neutral" | Whether it pushes suitability up, down, or neutral. |
| `label` | string? | Short plain-language label for UI. |
| `magnitude` | number? | Optional relative importance or contribution. |

**MVP:** PointInspection with `value` and optional `drivers[]`; each driver at least `name` and `direction`.

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
| **Catalog** | Firestore `models` collection or JSON `models[]` | Stored list of Model; id required. |
| **RasterMetadata** | `GET /models/{id}/raster/metadata` when needed | Optional in MVP. |
| **PointInspection** | Response of `GET /models/{id}/point` | Required for MVP. |
| **DriverVariable** | Inside PointInspection.drivers | Required for MVP (simple explanation). |

This gives a consistent, resource-oriented set of types for backend, frontend, and catalog storage.
