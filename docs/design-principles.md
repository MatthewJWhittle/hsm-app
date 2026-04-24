# Design principles (UI/UX)

These principles guide how the **HSM Explorer** should **look, feel, and read** in the interface. They complement **[Product principles](product-principles.md)**, which govern *what* we build and *why*; this document governs *how* we present it.

---

## 1. Map as hero, chrome as support

- The **map** remains the **largest, most stable** surface. Navigation, pickers, and inspection should feel like **light instruments** on a windshield—not a second product competing for attention.
- New UI should **default to the map in view**; avoid flows that block the map without a clear reason (e.g. full-page gates before first paint).

## 2. Calm, professional, not playful

- The audience is **ecologists, planners, and decision support**. The interface should feel **serious, legible, and unhurried**—clarity and speed are the “delight,” not decoration.
- **Avoid** consumer-gamified patterns (badges, streaks, cutesy copy) and **loud** marketing-style visuals that **compete** with the data layer for attention.

## 3. Honest, confident framing

- The product should not **hype** the model. Trust comes from **transparent framing** and **obvious limitations**, not from hiding caveats in long prose.
- **Visual hierarchy** should make “what this is” and “what it is not” **scannable in seconds**; paragraphs support that line, not replace it.

## 4. Truth hierarchy (what to see first)

Order information so a new user can answer, without hunting:

1. **What layer** this is (species, activity, project—in plain language where possible, with scientific names when useful).
2. **What the colours mean** (scale, units, normalised 0–1 if applicable)—the map should never be a **Rorschach test** for first-time users.
3. **One line of interpretation** (relative / modelled suitability, not presence or absence; use with survey and judgement).
4. **Deeper detail** (About, layer metadata, point inspection, drivers) **on demand**.

## 5. Progressive disclosure, not wizards

- **Depth is optional**; **obstruction** is not. Favour **short** banners, **compact** strips, and **dismissible** first-use help over multi-step product tours.
- **Power users** get density through **expansion, shortcuts, and optional panels**—not through cluttering the default map.

## 6. Data colours live on the map and legend

- Reserve **strong colour** for **geospatial data** and the **legend**; keep UI chrome **neutral** with a **small** set of **semantic accents** (primary action, link, focus).
- Avoid turning every control into a **competing** coloured shape.

## 7. Readability in real work conditions

- Favour **contrast**, **size**, and **spacing** that work in **offices, sunlight, and projectors**—not only on a designer’s perfect display.
- **No tiny, low-contrast** copy for **critical** labels (legends, interpretation, key actions).
- Truncation of **layer titles** and **caveat** text should be **exceptional**; prefer wrap, tooltip, or layout adjustment.

## 8. Interaction: fast, direct, touch-tolerant

- **Pan, zoom, and layer change** should feel **immediate**. Loading should **signal** state on the **map area** (e.g. skeleton, subtle placeholder)—not a blank void that reads as “broken.”
- **Hit targets** and **draggable** areas should respect **trackpads, mice, and tablets** when we claim field or meeting use.
- **Keyboard** and **accessibility** matter for desk workflows: focus order, ARIA, and **non-mouse** paths for the same actions.

## 9. Jargon: optional, not the only path

- **Scientific names** are appropriate for professionals; add **common names** or **clear subtitles** when it improves comprehension without **duplicating** long prose.
- **Acronyms** (e.g. HSM) should be **defined once** in context for first-time landings—not assumed.

## 10. What to avoid (anti-patterns)

- **Mystery map:** colour with **no** default legend or one-line frame.
- **Dashboard-first** layouts that **delay** seeing the map.
- **Feature-heavy generic GIS** chrome that **obscures** the single scenario the user is exploring.
- **Critical caveats** only in **deep** settings or long sidebar copy—**skimmers** will miss them in meetings and reports.

---

## Alignment

- **Product:** [Product principles](product-principles.md), [Users and use cases](users-and-use-cases.md)  
- **Stack / frontend code:** [frontend/AGENTS.md](../frontend/AGENTS.md)  
- **Top-level spec:** [Application spec](../application-spec.md)  

This document is **not** a visual identity system (logo, font tokens, component library). It defines **principles** that implementation and design iterations should follow; concrete tokens and components live in the frontend codebase and style choices.
