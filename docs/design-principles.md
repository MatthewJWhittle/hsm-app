# Design principles (UI/UX)

These principles guide how the **HSM Explorer** should **look, feel, and read** in the interface. They complement **[Product principles](product-principles.md)**, which govern *what* we build and *why*; this document governs *how* we present it.

---

## 1. Map as hero, chrome as support

- The **map** remains the **largest, most stable** surface. Navigation, pickers, and inspection should feel like **light instruments** on a windshield, not a second product competing for attention.
- New UI should **default to the map in view**; avoid flows that block the map without a clear reason (e.g. full-page gates before first paint).

## 2. Calm, professional, not playful

- The audience is **ecologists, planners, and decision support**. The interface should feel **serious, legible, and unhurried**; clarity and speed are the “delight,” not decoration.
- **Avoid** consumer-gamified patterns (badges, streaks, cutesy copy) and **loud** marketing-style visuals that **compete** with the data layer for attention.

## 3. Honest, confident framing

- The product should not **hype** the model. Trust comes from **transparent framing** and **obvious limitations**, not from hiding caveats in long prose.
- **Visual hierarchy** should make “what this is” and “what it is not” **scannable in seconds**; paragraphs support that line, not replace it.

## 4. Truth hierarchy (what to see first)

Order information so a new user can answer, without hunting:

1. **What layer** this is (species, activity, project in plain language where possible, with scientific names when useful).
2. **What the colours mean** (scale, units, normalised 0–1 if applicable). The map should never be a **Rorschach test** for first-time users.
3. **One line of interpretation** (relative / modelled suitability, not presence or absence; use with survey and judgement).
4. **Deeper detail** (About, layer metadata, point inspection, drivers) **on demand**.

## 5. Progressive disclosure, not wizards

- **Depth is optional**; **obstruction** is not. Favour **short** banners, **compact** strips, and **dismissible** first-use help over multi-step product tours.
- **Power users** get density through **expansion, shortcuts, and optional panels**, not through cluttering the default map.

## 6. Data colours live on the map and legend

- Reserve **strong colour** for **geospatial data** and the **legend**; keep UI chrome **neutral** with a **small** set of **semantic accents** (primary action, link, focus).
- Avoid turning every control into a **competing** coloured shape.

## 7. Readability in real work conditions

- Favour **contrast**, **size**, and **spacing** that work in **offices, sunlight, and projectors**, not only on a designer’s perfect display.
- **No tiny, low-contrast** copy for **critical** labels (legends, interpretation, key actions).
- Truncation of **layer titles** and **caveat** text should be **exceptional**; prefer wrap, tooltip, or layout adjustment.

## 8. Interaction: fast, direct, touch-tolerant

- **Pan, zoom, and layer change** should feel **immediate**. Loading should **signal** state on the **map area** (e.g. skeleton, subtle placeholder), not a blank void that reads as “broken.”
- **Hit targets** and **draggable** areas should respect **trackpads, mice, and tablets** when we claim field or meeting use.
- **Keyboard** and **accessibility** matter for desk workflows: focus order, ARIA, and **non-mouse** paths for the same actions.

## 9. Jargon: optional, not the only path

- **Scientific names** are appropriate for professionals; add **common names** or **clear subtitles** when it improves comprehension without **duplicating** long prose.
- **Acronyms** (e.g. HSM) should be **defined once** in context for first-time landings, not assumed.

## 10. What to avoid (anti-patterns)

- **Mystery map:** colour with **no** default legend or one-line frame.
- **Dashboard-first** layouts that **delay** seeing the map.
- **Feature-heavy generic GIS** chrome that **obscures** the single scenario the user is exploring.
- **Critical caveats** only in **deep** settings or long sidebar copy; **skimmers** will miss them in meetings and reports.

## 11. Information hierarchy (content scope)

The app is **general-purpose**: copy and UI must not read as if one **modelling project** or region *is* the product. Project- and layer-specific facts live in the **catalog** and in **layer-scoped** surfaces; **product-level** guidance applies to every deployment.

Use this **scope ladder** when writing or placing text:

| Level | Scope | Examples of content | Typical UI |
|--------|--------|---------------------|------------|
| **1. Product / tool** | Any user, any layer | What HSM relative suitability means; not presence/absence; use with survey and judgement; how to read the scale. | Welcome modal, **About this map**, compact legend framing |
| **2. Organisation / programme** (optional) | Service owner | Support contact, programme name, feedback, only if you maintain it. | Footer, separate “About the service” if needed, not mixed into layer copy |
| **3. Project** | One catalog **project** | Shared environmental data, visibility, project label; how layers in a project relate. | **Layer details** → project section; Admin |
| **4. Model / layer** | One **model** row | Species, activity, card title/version, identifiers for **this** raster. | Picker, **Layer details** → layer section |
| **5. Location** | One click (or future polygon) | Suitability value, drivers, raw bands at that place. | Inspection HUD |

**Rules**

- **Level 1** copy must never imply a specific region, contract, or commission unless explicitly labelled as level 2+.
- **Level 1** in-app product copy is about **how to read and use the map** (suitability meaning, limitations, what a click returns). It should **not** read like a design spec, explain where other help “lives” in the UI, or use meta labels (e.g. *“applies to every layer”*). **Navigation** belongs in short control labels, tooltips, and affordances, not in long prose.
- **Level 3–4** sentences in layer-scoped surfaces should make scope obvious to the person reading them (e.g. which project or model the facts refer to), not “The map shows…”
- In **authoring and placement** (this doc, not the product UI), prefer **linking** levels over **merging** project narrative into level-1 welcome text; that guidance is for writers, not for end-user paragraphs that describe the app chrome.

Data alignment: **Project** and **Model** are first-class in [Data models](data-models.md) and the API; the UI should mirror that split.

## 12. Punctuation in interface copy

- Do **not** use the **em dash** (Unicode U+2014) in the product UI, admin-facing strings, or in these design docs. It is easy to miss in review and inconsistent across platforms. Prefer **commas, full stops, colons, and semicolons** for the same job.
- **Separators in labels:** use a **middle dot** (`·`, U+00B7) between species and activity (and similar paired titles), and between primary and secondary lines in the layer picker, matching the rest of the app.
- **Empty or missing values** in tables and readouts: use a plain **ASCII hyphen** (`-`, U+002D), not an em dash as a “missing” glyph.
- **Numeric ranges** in documentation may use an **en dash** (0–1) where conventional; that is not the same as a sentence em dash.
- **Implementation:** follow the same rule in new **JSDoc and code comments** in the frontend so prose stays consistent and easy to `grep`. Details for contributors and agents: [frontend/AGENTS.md](../frontend/AGENTS.md) (user-facing copy and punctuation).

## 13. Map help: two entry points (same dialog)

- **Top-right help (`?`):** First-land wayfinding: “what am I looking at?” It opens the **About this map** interpretation. Tooltip and coachmark should stay short; do not duplicate long prose in the control label.
- **Expanded floating card — Help (outline):** Opens the **same** dialog, but the affordance lives **in context** next to layer tools. **Tooltip/aria** should read as a **full map guide** (colours, how to read the view, limitations), not a different feature, so the two controls feel like **two doors to one room** rather than competing products.
- Stacking: map chrome z-index is centralised in the frontend (see `mapOverlayZIndex.ts`); new overlays should extend that file so layers do not “random 1001” by accident.

---

## Alignment

- **Product:** [Product principles](product-principles.md), [Users and use cases](users-and-use-cases.md)  
- **Stack / frontend code:** [frontend/AGENTS.md](../frontend/AGENTS.md)  
- **Top-level spec:** [Application spec](../application-spec.md)  

This document is **not** a visual identity system (logo, font tokens, component library). It defines **principles** that implementation and design iterations should follow; concrete tokens and components live in the frontend codebase and style choices.
