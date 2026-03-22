# Users and use cases

## Primary users

### 1. Conservation practitioners / bat ecologists

These users are likely to be the core audience for the product.

They need to:

- understand habitat suitability for a species across the landscape
- investigate local areas of interest
- plan or prioritise survey effort
- support conservation discussions with spatial evidence
- interpret suitability responsibly in ecological context

### 2. Ecological consultants

These users need to understand how a site sits within a wider landscape and use the outputs to support planning, survey design and interpretation.

They need to:

- assess broader context around a site
- identify nearby higher- or lower-suitability areas
- interpret likely drivers of suitability
- communicate findings to clients or project teams

## Secondary users

### 3. Bat groups / citizen science organisers

These users may use the product to support local conservation, volunteer effort and engagement.

They need to:

- explore suitable areas for a species
- identify places that may warrant more survey effort
- interpret model outputs without needing deep technical knowledge
- communicate patterns to volunteers and local partners

### 4. Researchers / advanced technical users

These users are not the primary target for MVP, but may need deeper interpretation.

They may want to:

- inspect model behaviour more closely
- compare species or places
- investigate drivers of suitability
- use outputs as a starting point for further work

### 5. Admin / content manager

This user is responsible for keeping the application’s data up to date.

They need to:

- add new species and upload or register new suitability models (COGs) and associated metadata
- update the app as new data becomes available without depending on developers
- perform updates either via a UI (for occasional changes) or via the API (for bulk or scripted updates)

### 6. Solo app developer (operator)

This is the person building and operating the application—often a single developer who may be personally liable for cloud costs.

They need to:

- keep infrastructure costs low and predictable
- avoid accidental spend on GCP (e.g. runaway scaling, forgotten resources, unexpected usage)
- use free or low-cost tiers where possible and set hard limits or alerts before costs become significant

**User story:** As a solo app developer, I need to keep infrastructure costs low and controlled so that I don’t accidentally become personally liable for significant costs on GCP.

**Implications for the product:** Architecture and deployment choices should favour cost control: budget alerts and caps, use of free tiers (e.g. Firebase free tier, Cloud Run scale-to-zero), minimal always-on resources, and clear documentation of expected cost and how to set limits.

## Priority use cases

### Use case 1: Survey targeting

A user wants to identify areas where future survey effort is likely to add the most value.

#### Example needs
- see where suitability appears high
- compare areas across a region
- identify promising areas for follow-up
- justify why one area should be prioritised over another

#### Current pain points
- difficult to move from raw records to a survey plan
- survey effort is often guided by habit, local knowledge or static maps
- hard to explain prioritisation decisions consistently

### Use case 2: Site-in-landscape interpretation

A user wants to understand how a particular site or local area sits within the wider habitat suitability landscape.

#### Example needs
- inspect suitability around a chosen site
- understand whether the site sits within a broader suitable area
- compare the local area with surrounding landscape patterns
- interpret why suitability appears high or low nearby

#### Current pain points
- site interpretation is often localised and lacks wider spatial context
- existing outputs are often static and hard to interrogate
- it is difficult to explain the broader ecological setting consistently

### Use case 3: Conservation prioritisation

A user wants to identify areas that may deserve greater conservation attention or further ecological investigation.

#### Example needs
- identify larger patterns of suitability across a region
- compare areas more systematically
- support strategic discussions with evidence
- use a repeatable basis for prioritisation

#### Current pain points
- prioritisation is often fragmented or highly dependent on individual knowledge
- evidence is patchy and hard to compare at a broader scale
- existing tools may not support transparent reasoning

### Use case 4: Add or update species and models (admin)

An admin wants to add new species and upload models and associated data so that they can update the app as they get new data.

#### Example needs
- add a new species and register one or more suitability models (COGs) for it
- upload or register COG files and optional metadata (model name, version)
- do this via the UI for one-off updates, or via the API when updating many items (e.g. batch ingest)
- see or list what is currently in the catalog

#### Acceptance (in scope when this feature is implemented)
- Admin can add a new catalog entry (species + activity + COG) via the UI.
- Admin can add or update catalog entries via the API (e.g. POST/PUT) so that scripts or external systems can push new data.
- New or updated entries appear in the app’s species/model selection after the catalog is refreshed (or immediately if the app uses live catalog storage).

## Cross-cutting user needs

Across user groups and use cases, the product should help users:

- move between regional and local scales
- see what habitat suitability looks like spatially
- understand what is driving suitability in a location
- use outputs without over-interpreting them
- communicate what the tool shows and what it does not show

## What users are not asking for

At this stage, users are not primarily asking for:

- a full GIS replacement
- a model-building workbench
- a highly technical machine learning interface
- automation of ecological judgement

They are asking for a practical tool that helps them make better use of spatial habitat suitability evidence.
