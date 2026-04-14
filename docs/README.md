# Documentation overview

This folder holds product, architecture, and operational documentation. The set is kept consistent: **product goals and principles** → **MVP scope** → **solution architecture** → **data models** and **application spec**; **infrastructure and deployment** defines how to run and deploy the app (and cost guardrails).

## Reading order

1. [Problem statement](problem-statement.md) — the conservation and decision-support problem  
2. [Outcomes and product goal](outcomes-and-product-goal.md) — intended outcomes and product goal  
3. [Users and use cases](users-and-use-cases.md) — users, needs, and priority use cases  
4. [Product principles](product-principles.md) — principles for scope and design  
5. [MVP scope](mvp-scope.md) — smallest useful version and must-haves  
6. [Admin scope decisions](admin-scope-decisions.md) — auth, storage, ids, and project-shaped future work (issue #9)  
7. [Solution architecture](solution-architecture.md) — high-level architecture and subsystems  
8. [Data models](data-models.md) — models (Model, catalog, PointInspection, DriverVariable), GCS upload layout, naming, and COG/CRS validation  
9. [API integration](api-integration.md) — scripted HTTP flows (auth, multipart uploads, projects, models, CRS/COG prep, common errors) for modellers and tooling  
10. [Serialized model requirements](serialized-model-requirements.md) — **sklearn-only** pickled estimator for **`serialized_model_file`** / on-demand SHAP (copy-paste agent brief included)  
11. [ML artifacts and serving principles](ml-artifacts-and-serving-principles.md) — bundles, manifests, precomputation vs live inference, validation, security, and operations for model-related features  
12. [Infrastructure and deployment](infrastructure-and-deployment.md) — GCP stack, cost control, what to avoid  
13. [Deployment runbook (MVP)](deployment-runbook.md) — practical rollout guide for bootstrap, PR validation, and production promotion  

Implementation detail (endpoints, components, phases): see [Application spec](../application-spec.md) in the repo root.
