# Admin scope and access — agreed decisions

This document captures **product and technical decisions** for [GitHub issue #9](https://github.com/MatthewJWhittle/hsm-app/issues/9) (MVP admin catalog) and **near-term evolution**, so implementation and docs stay aligned. It complements [MVP scope](mvp-scope.md), [Data models](data-models.md), and [Solution architecture](solution-architecture.md).

**Related:** Issue [#4](https://github.com/MatthewJWhittle/hsm-app/issues/4) (Firebase emulators + Firestore reads) is **closed**; admin work assumes that baseline.

---

## 1. Authorization: Firebase custom claims

- **Admin gate:** Use **Firebase custom claims** on the ID token — specifically **`admin: true`** — for users allowed to call write/admin APIs and use the admin UI. This matches the existing frontend check (`claims.admin === true`).
- **Not via Console:** Custom claims **cannot** be set from the Firebase Console UI; they are set with the **Firebase Admin SDK** (`auth.set_custom_user_claims`) or equivalent server-side API.
- **Local / bootstrap:** Use a **CLI or Python script** (run locally with credentials or against the **Auth emulator**) to grant the first admin user(s). Document the script in the README next to other emulator setup.
- **Future:** An admin may **grant other users** permissions (e.g. create a project, manage data). That implies **additional claims** and/or **Firestore-backed roles** later; **Firestore remains available for richer user and membership data** when needed. **This issue implements custom claims first**; fine-grained roles can build on the same patterns.

- **HTTP semantics:** **`401`** if the bearer token is missing or invalid; **`403`** if the token is valid but the user does not have the required claim(s).

- **Token refresh:** After claims change, clients need a **fresh ID token** (e.g. `getIdToken(true)` or sign-out/sign-in) before new claims appear.

---

## 2. Projects and encapsulation (design-forward, not full build in #9)

- The product will likely introduce **projects** (or similar): admins **create and configure a project**, attach data, and **publish**. That implies **additional API routes** and **nested resources** over time (e.g. models scoped to a project).
- **For issue #9:** **Design with this in mind** (stable ids, clear separation of catalog vs storage layout, avoid one-off assumptions that block a `project_id` prefix later). **Do not** ship the full project lifecycle, publishing workflow, or every route in the first admin MVP unless explicitly pulled into the same milestone.
- **Documentation:** This file and [MVP scope](mvp-scope.md) record the direction; **GitHub issue #9** remains the tracker for concrete acceptance criteria (POST/PUT models, storage, validation, `/admin` UI).

---

## 3. Identifiers and storage layout

- **Model ids:** Prefer **server-generated opaque identifiers** (e.g. **UUIDs** or **ULIDs**) for **robustness and extensibility**, unless a product need requires human-readable slugs. Paths and Firestore document ids should stay **URL-safe** and stable.
- **Artifacts per model:** Each model has its **own artifact prefix** (suitability COG and optional sidecars under that prefix). See [Data models — raster naming](data-models.md#raster-files-folders-and-naming-uploads-and-storage).
- **Drivers / shared environmental rasters:** **Driver** inputs may reference a **shared multi-band raster** of environmental variables (**not necessarily one file per model**). That dataset may be scoped to a **project** or **shared across projects**. Models then reference the appropriate **`driver_config`** (subset of bands/features). Refine exact storage paths when project boundaries and driver datasets are modelled; keep **`driver_config`** extensible.

---

## 4. Dev vs production object storage (minimal branching)

- **Requirement:** Uploads from the app in **development** should **persist to local storage** (or a bind-mounted path); in **production**, to **Google Cloud Storage**. The **environment** selects the backend; the **application logic** should not scatter `if dev` spaghetti.
- **Pattern:** A single **storage abstraction** (interface) with implementations such as:
  - **Local filesystem** — root directory from an env var (e.g. under `data/` in Docker).
  - **GCS** — bucket and credentials from env / workload identity.
- **Catalog:** Firestore documents store **logical paths** or URIs consistent with the chosen backend so **TiTiler** and the map can resolve tiles in both modes (document how `file://` vs `gs://` is resolved in [Infrastructure and deployment](infrastructure-and-deployment.md) as this lands).

---

## 5. What stays in issue #9 (reference)

Concrete delivery for the open issue remains aligned with [issue #9 description](https://github.com/MatthewJWhittle/hsm-app/issues/9): authenticated **`POST /models`** and **`PUT /models/{id}`**, COG + **EPSG:3857** validation, **GCS or local storage** via the abstraction above, Firestore persistence, **`/admin`** UI with Bearer tokens, and **documentation** (env vars, bootstrap admin claim script, dev vs prod).

Non-goals and acceptance criteria on the issue are still authoritative; **this document steers design** without replacing those checkboxes.
