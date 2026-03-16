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
| `crs` | string? | CRS identifier (e.g. "EPSG:4326"). |
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
