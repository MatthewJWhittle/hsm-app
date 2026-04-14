# Serialized estimator for explainability (`serialized_model_file`)

This document defines what the **HSM Visualiser API** can load when you upload a pickled estimator via **`POST`/`PUT` `/models`** as multipart field **`serialized_model_file`**. The file is stored as **`serialized_model.pkl`** under the model’s **`artifact_root`** and used at **`GET /models/{id}/point`** to run **permutation SHAP** against the project’s **`explainability_background.parquet`**.

---

## Message to pass to a training / export agent

Use the block below as the **system or task preamble** when asking another agent (or developer) to export a model for this API:

---

**Requirements — HSM API explainability pickle**

1. **Runtime (server):** The API runs **Python 3.11+** and loads your file with **`pickle.load`** (or equivalent). Declared dependencies include **`scikit-learn>=1.4`**, **`numpy`**, **`pandas`**, **`shap`**, and **`elapid`** (required to support compatible uploaded pickle models that reference `elapid` classes) — see the repo’s **`backend/pyproject.toml`**. There is **no** guarantee that arbitrary third-party or private packages (e.g. a local `sdm` or project-specific module) are installed.

2. **Sklearn-only object graph:** The saved object MUST unpickle using **only importable code from the standard scientific stack**, primarily **`sklearn`**. Do **not** pickle estimators that reference **custom Python modules** from your modelling repo unless those modules are also shipped inside the API container (not supported by default). Prefer a fitted **`sklearn.pipeline.Pipeline`** (or compatible composition) built **only** from `sklearn` + `numpy` (+ `scipy` as used by sklearn).

3. **Interface:** The server calls **`predict_proba(X)`** where **`X`** is a **pandas `DataFrame`** whose columns are the machine **`feature_names`** (from **`feature_band_names`**), in order. This matches training for **`Pipeline`** + **`ColumnTransformer`** (string column selectors require a DataFrame). Internally, SHAP permutation passes **numpy** batches; the API **re-wraps** them with those column names before **`predict_proba`**. Use column **`positive_class_index`** from model metadata (default **`1`**) for the positive-class probability column. Your estimator **must** implement **`predict_proba`** suitable for binary (or multi-class) probability output as sklearn classifiers do.

4. **Feature order:** Column order and names must match **`metadata.analysis.feature_band_names`** on the model (same as **`feature_names`** resolved server-side from the catalog project). The point row and background parquet use that same schema.

5. **Serialization:** Use **`joblib.dump`** or **`pickle.dump`** of the **fitted** estimator. After export, **verify** in a **clean** environment: `python -c "import pickle; pickle.load(open('model.pkl','rb'))"` with **only** `sklearn`/`numpy` installed (no editable install of your repo) — if that fails with `ModuleNotFoundError`, the API will fail too (error code **`EXPLAINABILITY_PICKLE_IMPORT`**).

6. **Non-goals:** The API does **not** run arbitrary training code, ONNX, or custom inference servers for this path — only **in-process sklearn + SHAP** as implemented.

---

## API behaviour (summary)

| Item | Detail |
|------|--------|
| **Upload** | Multipart **`serialized_model_file`** on admin **`POST /models`** or **`PUT /models/{id}`**; combined with **`metadata`** listing **`analysis.feature_band_names`**, **`analysis.positive_class_index`** (optional), and a parent **project** that has **`explainability_background.parquet`**. |
| **SHAP background size** | At **`GET …/point`**, only the first **`SHAP_BACKGROUND_MAX_ROWS`** rows of the background Parquet are used (default **512**, configurable). Larger files are truncated deterministically to bound CPU per click. |
| **Load failure (missing imports)** | **422** with **`detail.code`** **`EXPLAINABILITY_PICKLE_IMPORT`** — pickle referenced a module not available on the server. |
| **Other load failures** | **422** with **`EXPLAINABILITY_PICKLE_LOAD`**. |

## Related docs

- [API integration](api-integration.md) — multipart examples and **`GET …/point`**
- [Data models](data-models.md) — **`metadata.analysis`**, **`PointInspection.drivers`**
