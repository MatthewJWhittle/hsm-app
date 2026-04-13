# ML artifacts and serving principles

This document captures **cross-cutting engineering and operational principles** for how trained models, rasters, and explanation artifacts connect to the **hsm-app** backend and frontend. It complements [Product principles](product-principles.md) (what the product should achieve) and [Data models](data-models.md) (schema and field definitions).

**Audience:** implementers of catalog upload, point inspection, driver layers, and any future explanation or SHAP-style features.

---

## 1. Purpose

- **Training** produces geospatial and model artifacts **outside** this app; **serving** reads them at predictable paths referenced from Firestore.
- The goal is **predictable behaviour**, **safe operations**, and **clear contracts** between notebooks/pipelines and production — without scattering one-off assumptions across issues or code.

---

## 2. Versioned artifact bundles (the training ↔ serving interface)

Treat each logical model (or model version) as an **immutable bundle** under a stable prefix (`artifact_root`):

- Prefer a **manifest** (e.g. JSON) at the bundle root that declares **schema version**, **inventory of files**, **semantic contract** (feature order, band names ↔ indices, CRS, nodata, suitability band, optional positive-class index for classifiers), and **toolchain pins** when binaries or pickles must match training.
- The **manifest is canonical** at deploy time; Firestore holds **pointers** (`artifact_root`, optional manifest path, `driver_config` / `driver_band_indices`). Resolve conflicts in favour of **validated bundle contents** over stale DB fields.
- **Co-locate** configuration with artifacts: avoid a split where DB says one set of bands and on-disk files imply another.

---

## 3. Immutability and identity

- **New training run → new `model_id` or new versioned prefix**; avoid overwriting objects in place so maps, links, and audits stay meaningful.
- **One write path** for a bundle: training or an ingest job produces the **whole** directory; admin “promote” validates then registers the catalog row.

---

## 4. Precomputation vs live inference

Prefer **offline cost** over **request-time complexity** when the UX is read-heavy:

| Strategy | Typical use | Notes |
|----------|-------------|--------|
| **Precomputed explanation surfaces** (per-variable rasters or aligned grids) | Fast point reads; no sklearn/shap on the hot path | Storage and regeneration when models change; strict **CRS/grid alignment** with the suitability layer |
| **Raw driver bands only** | Sample env stack at click | No attribution; still needs manifest + band mapping |
| **Live SHAP or similar** | Maximum fidelity to research notebooks | Model + background + library in API; **version pins**, cold start, **stable background** for reproducibility |

Default posture for production: **precompute where possible**; use live explainers only when justified and operationally bounded (limits, timeouts, isolation).

---

## 5. Validation at the boundary

- Enforce **COG** and **CRS** rules (see [Data models — upload validation](data-models.md#upload-validation-cog-format-and-crs)) before committing catalog rows.
- Validate **manifest schema** (and optional checksums) when a bundle is uploaded or promoted.
- Fail **loudly** with actionable errors — not silent partial registration.

---

## 6. Security and trust

- Treat **pickle** and similar as **trusted pipeline only**: pin **Python / numpy / sklearn / shap** (or avoid unpickling in the request path entirely).
- **Least-privilege IAM**: services read only the prefixes they need; separate **admin write** from **public read** paths.
- Prefer **portable paths** in manifests (`artifact_root`-relative or object keys), not machine-local absolute paths from a developer laptop.

---

## 7. Reproducibility (explanations)

- For permutation-style or contrastive explanations, **background data** and **random seeds** must be **defined and stable** (or shipped with the bundle) or values are not comparable across deploys.
- Document **what the output means** (local attribution vs global importance, raw env value vs contribution).

---

## 8. API and UX behaviour

- **Progressive capability**: suitability works without influence drivers; raw env values may appear when bands are configured without SHAP artefacts; avoid UI that implies a stronger signal than the API provides.
- **Honest copy**: distinguish raw env values, local contributions, and global importance where users could confuse them.
- **Explicit empty and error states**: “not configured”, “outside extent”, “nodata”, and “server error” should be distinguishable in the UI and logs.

---

## 9. Platform and operations

- **Differentiated limits**: point inspection and tile traffic have different cost profiles — apply **timeouts**, **retries**, and **rate limits** appropriately.
- **Caching**: safe caching of manifest metadata and stable reads; key by `model_id` and bundle version.
- **Observability**: structured logs with `model_id`, bundle or manifest version, and latency split (storage open vs compute) — without logging secrets or full signed URLs.

---

## 10. Data lifecycle and compliance

- Define **retention and deletion**: removing a model should have a clear story for **GCS objects**, **Firestore**, and **CDN** caches if applicable.
- Record **licensing or attribution** requirements for third-party env layers where the product must display them.

---

## 11. Calibration and semantics

- Suitability may be a **probability**, **transformed score**, or **model-specific output**. The bundle or catalog metadata should record **interpretation** so the UI and copy do not over-claim (aligned with [Product principles](product-principles.md)).

---

## 12. Testing and change control

- **Golden fixtures**: tiny COGs and minimal manifests in CI for contract tests.
- **Schema ownership**: changes to manifest or bundle format should be **reviewed** and **versioned**; note compatibility in release notes when training and API repos deploy independently.

---

## Related work

- **Implementation (issue):** [Environmental drivers for point inspection — #13](https://github.com/MatthewJWhittle/hsm-app/issues/13)
- **Architecture:** [Solution architecture — §3.3 Point and site inspection](solution-architecture.md#33-point-and-site-inspection)
- **Schema:** [Data models](data-models.md)
- **Catalog and projects:** [Admin scope decisions](admin-scope-decisions.md), [issue-14 catalog steps](issue-14-catalog-projects-steps.md)
