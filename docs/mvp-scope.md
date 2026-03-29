# MVP scope

## Purpose of the MVP

The MVP should prove that the product can support real conservation and survey workflows by making habitat suitability outputs practically usable at regional and local scales.

It should not try to solve every possible use case.

## MVP goal

Enable a user to select a species or model, explore habitat suitability spatially, investigate a place of interest, and understand the main factors influencing suitability well enough to support survey targeting or site interpretation.

## Core user journeys

### 1. Explore suitability for a species

A user can:

- choose a species and model type
- view the habitat suitability map
- move around the region
- understand the broad distribution of relative suitability

### 2. Investigate a local area or site

A user can:

- zoom to a place of interest
- inspect local suitability patterns
- compare the site with the surrounding landscape
- understand whether the site appears to sit in a broader suitable context

### 3. Understand what is driving suitability

A user can:

- click or inspect a location
- see a simple explanation of the main variables contributing to suitability there
- understand whether those factors are increasing or reducing suitability
- interpret the result in plain language

### 4. Use outputs responsibly

A user can:

- understand what the map means
- see that the output is relative suitability rather than proof of presence or absence
- understand that the product supports, not replaces, ecological judgement

## Must-have capabilities

The MVP should include:

- species or model selection
- interactive map exploration
- regional-to-local zoom workflow
- point or site inspection
- simple explanation of local drivers
- clear interpretation guidance and caveats
- basic metadata such as model name and version
- **admin: add new species and upload/register models and associated data** via UI (for occasional updates) and API (for bulk or scripted updates)

## Should-have, if feasible

If time allows, the MVP could also include:

- side-by-side comparison of two locations
- a simple summary panel for a selected site
- export of map image or summary
- guided examples of how the output can be used

## Out of scope for MVP

The MVP should not include:

- end-user model training or tuning
- a full GIS editing workflow
- complex multi-species prioritisation tools
- highly technical model diagnostics for all users
- broad biodiversity scope beyond the initial bat use cases
- automated ecological recommendations

## Admin user story (MVP)

**User story (admin):**

- **As an** admin  
- **I want to** add new species and upload models and associated data for them  
- **So that** I can update the app as I get new data  

**Delivery:** support both UI (for occasional updates) and API (for bulk or scripted updates when there are many to do).

**Capabilities:**

- Add or register a new species and one or more suitability models (COGs) plus optional metadata (model name, version).
- Perform updates via an admin UI (form + upload or path to COG) and/or via API (e.g. POST/PUT catalog entries, file upload or reference to storage).
- Catalog changes are persisted and reflected in the app’s species/model selection (after refresh or immediately depending on implementation).

### Future direction (design only for first admin milestone)

The product may later add **projects** (create, configure, add data, publish) with **additional API routes** and resources scoped under projects. The **first admin delivery** (see [GitHub issue #9](https://github.com/MatthewJWhittle/hsm-app/issues/9)) should **not assume the full project feature set** but should **avoid blocking** it (stable ids, clear storage layout, extensible `driver_config`). See [Admin scope decisions](admin-scope-decisions.md).

## Success criteria for MVP

The MVP is successful if users can:

- identify areas of interest more easily than with static maps
- interpret site context more clearly
- explain why a location appears more or less suitable
- use the product without major misunderstanding of what the output means

And if admins can:

- add new species and register or upload models (COGs) and metadata via the UI or the API, and see those changes reflected in the app

Define clearer objectives (e.g. “users find areas of interest faster”, “admins add a model without developer help”) and use **monitoring in the app** (e.g. event logging or lightweight analytics for key actions) to measure progress. See [Infrastructure and deployment](infrastructure-and-deployment.md) (Objectives and monitoring).

## MVP access

MVP can be released in either of these ways (or a combination):

- **Private link:** Share the app URL only with selected users (e.g. a bat group or a few ecologists); no public listing.
- **Public URL with gated features:** Make the app publicly reachable, but hide some features (e.g. admin, or export) behind sign-up or sign-in so usage and access can be controlled.

## Accessibility

Accessibility (keyboard navigation, screen readers, contrast) is **nice to have for MVP**; prioritise core workflows first, then improve a11y in follow-up releases.

## Key assumptions

The MVP assumes that:

- COGs are produced elsewhere and added via the admin upload route; the app does not generate models
- users value both map exploration and explanation
- simple interpretation features will increase trust and usefulness
- a narrow, well-designed workflow is more valuable than a broad but shallow feature set
- the app is operated with **cost control** in mind: GCP budget alerts (and optional cap), scale-to-zero where possible, and documented steps to avoid unexpected spend, so the solo developer is not personally liable for significant costs (see [Users and use cases](users-and-use-cases.md) — solo app developer).
