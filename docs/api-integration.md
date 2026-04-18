# HSM Visualiser API — integration guide

This guide is for **modellers and tooling authors** who call the HTTP API directly: authentication, **environmental** (driver) COGs on catalog **projects**, **suitability** COGs per **model**, `metadata.analysis.feature_band_names`, and common pitfalls. It complements the normative field definitions in [Data models](data-models.md).

## Assumptions

- **Base URL** is configurable (for example `http://127.0.0.1:8000` with Docker Compose).
- **OpenAPI** JSON: `{BASE_URL}/openapi.json`; interactive docs: `{BASE_URL}/docs`.
- **Admin** routes (`tags` include `admin`) require `Authorization: Bearer <Firebase ID token>` with custom claim **`admin: true`**. Obtain a suitable token with **`POST /api/auth/token`** (below).

## Concepts

| Concept | Role |
|--------|------|
| **Catalog project** | Shared **multi-band environmental COG**, **band definitions** (machine `name`, display `label`, optional `description`), and optional **explainability background** sample (`explainability_background.parquet`). |
| **Model** | One **species × activity** entry: **suitability COG** (single interpretable band is typical), optional **pickled estimator** for on-demand SHAP, and **`metadata.analysis.feature_band_names`** (ordered list aligned with the model’s feature matrix). |
| **CRS** | Uploaded rasters are validated as **EPSG:3857** (Web Mercator). Sources in other CRS (for example **EPSG:27700** in UK workflows) must be **reprojected before upload**. |
| **COG** | Uploads should be valid **Cloud Optimized GeoTIFFs** (internal tiling and overviews suitable for range reads). |

## Authentication

Exchange email and password for Firebase tokens via this API (the server calls Identity Toolkit; you do not need to call Google’s REST URL yourself).

```http
POST {BASE_URL}/api/auth/token
Content-Type: application/json
```

```json
{
  "email": "YOUR_EMAIL",
  "password": "YOUR_PASSWORD",
  "admin_only": true
}
```

Response fields you typically need:

- **`id_token`** — send as `Authorization: Bearer <id_token>` on admin routes.
- **`refresh_token`**, **`expires_in`** — for long scripts, refresh with Firebase’s token refresh flow or call **`POST /api/auth/token`** again.

**Example (shell)**

```bash
export BASE_URL="http://127.0.0.1:8000"
export TOKEN="$(
  curl -sS -X POST "${BASE_URL}/api/auth/token" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"${HSM_EMAIL}\",\"password\":\"${HSM_PASSWORD}\",\"admin_only\":true}" \
  | jq -r '.id_token'
)"
```

Do **not** commit credentials. Prefer environment variables or a secret manager. **`admin_only: true`** returns **403** if the user does not have the **`admin: true`** custom claim (see [Admin scope decisions](admin-scope-decisions.md)).

## Resolve a catalog project

List visible projects and pick one by `name`, then read `id`:

```bash
export PROJECT_ID="$(
  curl -sS "${BASE_URL}/api/projects" \
  | jq -r '.[] | select(.name=="Example project name") | .id'
)"
```

Use **`PROJECT_ID`** as **`project_id`** on **`POST /api/models`** and project update routes.

Private projects may require `Authorization: Bearer` for **`GET /api/projects`** to list them.

## Reprojecting to EPSG:3857

**Why:** The API validates CRS. Non-3857 uploads are rejected with structured **`detail`** (for example **`COG_CRS_MISMATCH`** with `expected_epsg` / `got_crs` in **`context`**).

**Pattern:** warp to Web Mercator, then build a COG. This repository’s sample pipeline uses **`gdalwarp`** then **`gdal_translate -of COG`** in [`scripts/convert_to_cog.sh`](../scripts/convert_to_cog.sh) (27700 raw rasters under `data/hsm-predictions/raw/` → 3857 COGs under `data/hsm-predictions/cog/`).

**Practical note:** Some GDAL builds have produced empty rasters when using **`gdalwarp -of COG`** in a single step. A **two-step** warp → COG (as in that script) is safer than combining steps if you see invalid or empty output.

Apply the same idea to **any** environmental stack or suitability raster you produce outside this repo before upload/create/replace calls.

## Environmental COG on the project

### Preferred large-file flow: upload sessions

For larger files, avoid sending the environmental raster through `POST /api/projects` multipart directly.
Use upload sessions:

1. `POST /api/uploads` (admin) with filename/content type/size
2. `PUT` file bytes to the returned signed `upload_url`
3. `POST /api/uploads/{upload_id}/complete`
4. `POST /api/projects` with form field `upload_session_id={upload_id}` (and no multipart `file`)

You can poll `GET /api/uploads/{upload_id}` for lifecycle status (`pending`, `complete`, `failed`).

Upload sessions are GCS-backed in this deployment: the API runtime must be configured with `GCS_BUCKET`, and the completed session object must exist in that bucket.

**Runtime signing config (Cloud Run):**

- Upload session init mints a V4 signed URL in the API runtime.
- In token-only runtime credential environments, ensure the runtime service account can mint signed URLs via IAM signing (Token Creator role with `iam.serviceAccounts.signBlob`).
  - This repo’s Terraform sets `GCS_SIGNED_URL_SERVICE_ACCOUNT` to the runtime API service account email by default.

### Create project with environmental COG (`POST /api/projects`)

```http
POST {BASE_URL}/api/projects
Authorization: Bearer {TOKEN}
Content-Type: multipart/form-data
```

Project create accepts either:

- multipart **`file`** (direct upload), or
- **`upload_session_id`** (session-backed upload).

Do not send both in the same request.

| Part | Purpose |
|------|--------|
| **`name`** | Required project name. |
| **`file`** | Optional multi-band environmental **COG** in **EPSG:3857**. |
| **`upload_session_id`** | Optional alternative to multipart `file` for large uploads. |
| **`infer_band_definitions`** | String `true` (default) to infer machine `name`s from GDAL band descriptions. Use `false` if you supply **`environmental_band_definitions`** as explicit JSON. |

### Replace environmental COG on existing project (`POST /api/projects/{project_id}/environmental-cogs`)

```http
POST {BASE_URL}/api/projects/{PROJECT_ID}/environmental-cogs
Authorization: Bearer {TOKEN}
Content-Type: multipart/form-data
```

This route is upload-session based:

- provide **`upload_session_id`**
- do not send multipart `file`

Behavior guardrails:

- `UPLOAD_MODE_UNSUPPORTED` when `file` is sent directly.
- `MISSING_UPLOAD` when `upload_session_id` is missing.
- `STORAGE_BACKEND_UNSUPPORTED` when `upload_session_id` is used without `STORAGE_BACKEND=gcs`.

Example (upload-session replace):

```bash
curl -sS -X POST "${BASE_URL}/api/projects/${PROJECT_ID}/environmental-cogs" \
  -H "Authorization: Bearer ${TOKEN}" \
  -F "upload_session_id=${UPLOAD_ID}" \
  -F "infer_band_definitions=true"
```

Project metadata updates (`PATCH /api/projects/{project_id}`) do not accept `file` or `upload_session_id`; use `/environmental-cogs` for raster replacement.

After a successful upload, the service may build **`explainability_background.parquet`**. If the COG has **no valid pixels** in sampled areas, the request can fail with an error about explainability sampling. Ensure a real extent and valid data, or adjust **`ENV_BACKGROUND_SAMPLE_ROWS`** / regenerate via **`POST /projects/{project_id}/explainability-background-sample`** once the COG is sane.

### Labels and descriptions (`PATCH`)

Human-facing **`label`** and **`description`** per machine **`name`**:

```http
PATCH {BASE_URL}/api/projects/{PROJECT_ID}/environmental-band-definitions/labels
Authorization: Bearer {TOKEN}
Content-Type: application/json
```

Body: JSON object keyed by machine **`name`**, values are objects with **`label`** and/or **`description`** (optional **`name`** as an alias for **`label`**; if both **`label`** and **`name`** are sent, **`label`** wins). Unknown keys return **422**.

This repo ships an example payload and helper:

- JSON: [`scripts/data/environmental_band_label_updates.json`](../scripts/data/environmental_band_label_updates.json)
- Script: [`scripts/apply_band_label_updates.py`](../scripts/apply_band_label_updates.py) (set **`HSM_API_BASE`**, **`HSM_PROJECT_ID`**, **`HSM_ID_TOKEN`**)

```bash
export HSM_API_BASE="${BASE_URL}"
export HSM_PROJECT_ID="${PROJECT_ID}"
export HSM_ID_TOKEN="${TOKEN}"
python3 scripts/apply_band_label_updates.py scripts/data/environmental_band_label_updates.json
```

To replace the **entire** band manifest (every index `0..n-1`), use **`PATCH /api/projects/{project_id}/environmental-band-definitions`** with a JSON **array** (see [Data models — catalog project](data-models.md#catalog-project-shared-environmental-stack)).

## Suitability model upload or update

### Check for an existing model

```bash
curl -sS "${BASE_URL}/api/models" -H "Authorization: Bearer ${TOKEN}" \
  | jq '.[] | select(.species=="Nyctalus noctula" and .activity=="Roost")'
```

- **No row** → **`POST /api/models`** (multipart requires **`file`** among other fields).
- **Row exists** → **`PUT /api/models/{model_id}`** to replace the COG and/or metadata or pickle.

### Preferred large-file flow for suitability COG uploads

`POST /api/models` also accepts `upload_session_id` as an alternative to multipart `file`:

1. `POST /api/uploads`
2. upload to signed `upload_url`
3. `POST /api/uploads/{upload_id}/complete`
4. `POST /api/models` with form field `upload_session_id={upload_id}` (omit multipart `file`)

This keeps large raster transfer off the API request body path while preserving existing model validation behavior.

**Duplicate guard:** **`POST /models`** returns **409** with **`MODEL_DUPLICATE`** when **`project_id` + `species` + `activity`** already exists.

### Metadata (multipart)

Send **`metadata`** as a multipart part whose body is a JSON object (preferred: part **`Content-Type: application/json`**). The server also accepts a legacy plain string field containing the same JSON.

At minimum, for point inspection and SHAP you typically set:

```json
{
  "analysis": {
    "feature_band_names": ["terrain_dtm", "..."]
  },
  "card": {
    "title": "Nyctalus noctula — Roost",
    "summary": "Habitat suitability",
    "version": "2026-04-11"
  }
}
```

Rules:

- Every name in **`feature_band_names`** must appear **exactly once** in the parent project’s **`environmental_band_definitions[].name`** list (case-insensitive match), in the **same order as the estimator’s feature columns**.
- Omit **`feature_band_names`** only if you do not need environmental sampling or explainability for that model.
- **`serialized_model_file`** (optional): must be a **pickle of a fitted estimator whose import graph uses only the server’s scientific stack** — primarily **scikit-learn** (see [Serialized model requirements](serialized-model-requirements.md)). Pickles that reference **custom project modules** (e.g. a private `sdm` package) will fail at **`/point`** with **`EXPLAINABILITY_PICKLE_IMPORT`**.

### Example `PUT` (update existing model)

```bash
export MODEL_ID="<uuid-from-GET-/models>"
META="$(jq -c . < path/to/metadata.json)"

curl -sS -X PUT "${BASE_URL}/api/models/${MODEL_ID}" \
  -H "Authorization: Bearer ${TOKEN}" \
  --form-string "metadata=${META}" \
  -F "file=@/path/to/suitability_epsg3857_cog.tif" \
  -F "serialized_model_file=@/path/to/model.pkl"
```

Optional multipart fields on create/update include **`project_id`**, **`species`**, **`activity`** (see **`/docs`** for the full schema).

### Point inspection

```http
GET {BASE_URL}/api/models/{MODEL_ID}/point?lng={WGS84_LON}&lat={WGS84_LAT}
```

Use coordinates **inside** the suitability raster extent (WGS84 lon/lat; the backend transforms to the raster CRS).

**Explainability:** The server loads **`metadata.analysis.serialized_model_path`** (default upload name **`serialized_model.pkl`**) with **`pickle.load`** and calls **`predict_proba`** for SHAP. The saved object must be **sklearn-centric** (no custom packages in the pickle’s import path). If loading fails, **`GET …/point`** returns **422** with **`detail.code`** **`EXPLAINABILITY_PICKLE_IMPORT`** (missing module from your training repo) or **`EXPLAINABILITY_PICKLE_LOAD`** (other load errors). Full contract: [Serialized model requirements](serialized-model-requirements.md). When the HTTP status is **200** but influence lists are empty, check **`capabilities.notes`**.

## Error reference (typical)

| Symptom | Likely cause |
|--------|----------------|
| **`COG_CRS_MISMATCH`** | Upload is not **EPSG:3857**. |
| **`invalid_feature_band_names`** / **`unknown_feature_band_names`** | Names not in the project manifest, or duplicates in **`feature_band_names`**. |
| Explainability / sampling errors on **project** upload | COG extent mostly **nodata**, or sampling cannot draw enough valid pixels. |
| **`POINT_SAMPLING`** or model load errors on **`/point`** | Raster missing, band mismatch, or pickle load failure. |
| **`EXPLAINABILITY_PICKLE_IMPORT`** / **`EXPLAINABILITY_PICKLE_LOAD`** on **`/point`** | Pickle references a module not on the server, or unpickling failed — export a **sklearn-only** artifact per [Serialized model requirements](serialized-model-requirements.md). |
| **401** / **403** on writes | Missing or invalid token, or missing **`admin: true`** claim when the route requires it. |

Validation responses use structured **`detail`**: `{ "code", "message", "context"? }` for many COG and form errors; **`feature_band_names`** issues may return **400** with an object whose **`error`** is **`invalid_feature_band_names`** (see OpenAPI and [Data models](data-models.md#upload-validation-cog-format-and-crs)).

## Quick checklist

1. Obtain **`TOKEN`** (`POST /api/auth/token`, with **`admin_only: true`** when you need an admin-capable token).
2. Resolve **`PROJECT_ID`** (`GET /api/projects`).
3. Ensure the **environmental** COG is **3857 + COG**; upload via **`POST /api/projects`** (create) or use upload sessions then call **`POST /api/projects/{id}/environmental-cogs`** (replace), with **`infer_band_definitions=true`** (or explicit **`environmental_band_definitions`**).
4. Optionally **`PATCH …/environmental-band-definitions/labels`** using the example JSON and script under **`scripts/data/`**.
5. Produce **suitability** raster → **warp to 3857** → **COG**.
6. Build **`metadata`** with **`feature_band_names`** in training column order.
7. **`POST` or `PUT` `/api/models`** with multipart: **`project_id`**, **`species`**, **`activity`**, **`file`**, optional **`metadata`**, optional **`serialized_model_file`**.
8. Verify with **`GET /api/models/{id}`** and **`GET …/point`** inside raster bounds.

## Keeping docs in sync

When the API changes, regenerate behaviour details from **`{BASE_URL}/openapi.json`** and update this guide if examples drift.

## Related repository files

| File | Purpose |
|------|---------|
| [`docs/data-models.md`](data-models.md) | Model and project shapes, validation rules, point pipeline. |
| [`docs/serialized-model-requirements.md`](serialized-model-requirements.md) | Copy-paste brief for exporters: **sklearn-only** pickle for **`serialized_model_file`**. |
| [`scripts/convert_to_cog.sh`](../scripts/convert_to_cog.sh) | Example **27700 → 3857 → COG** for sample suitability rasters. |
| [`scripts/data/environmental_band_label_updates.json`](../scripts/data/environmental_band_label_updates.json) | Example **`PATCH …/labels`** payload. |
| [`scripts/apply_band_label_updates.py`](../scripts/apply_band_label_updates.py) | Applies label patch with env-configured auth. |
| [`scripts/reproject_cog.sh`](../scripts/reproject_cog.sh) | Example **gdalwarp** flow to reproject a raster to **EPSG:3857** before COG upload. |
| [`backend/backend_api/routers/models_openapi.py`](../backend/backend_api/routers/models_openapi.py) | OpenAPI multipart schema for **`POST`/`PUT` `/api/models`**. |
