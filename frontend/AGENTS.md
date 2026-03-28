# AGENTS.md

## Scope

This file applies **only** to the frontend application in this directory and its subdirectories.

It does **not** define rules for backend services, infrastructure, data pipelines, or shared platform code outside the frontend scope.

If a task touches both frontend and backend, keep frontend changes aligned to this file and look for other `AGENTS.md` files or repo guidance for the other areas.

---

## Purpose

This frontend is built with React and TypeScript. The goal is to keep the codebase:

* predictable
* strongly typed
* easy to reason about
* easy to extend
* consistent across contributors
* safe for iterative AI-assisted changes

Prefer boring, explicit, maintainable code over clever abstractions.

---

## Core principles

1. **Keep components pure**

   * Components should be pure render functions of props and state.
   * Do not perform side effects during render.
   * Do not mutate props, shared objects, or module-level state during render.

2. **Prefer simple data flow**

   * Derive values during render where possible.
   * Avoid redundant or duplicated state.
   * Do not introduce extra state when a value can be computed from existing inputs.

3. **Use effects sparingly**

   * `useEffect` is for synchronising with external systems only.
   * Do not use effects to derive state, transform data for rendering, or respond to ordinary user interactions.

4. **Keep boundaries clear**

   * UI components should not own networking, caching, or raw API integration details unless that is the established pattern in this folder.
   * External data must be treated as untrusted until validated or narrowed.

5. **Change as little as needed**

   * Prefer focused changes over broad rewrites.
   * Do not refactor unrelated code unless it is necessary to complete the task safely.
   * Follow existing local patterns unless they conflict with the rules in this file.

---

## Non-negotiable rules

### React

* Use function components only.
* Do not define components inside other components.
* Do not call hooks conditionally, inside loops, or inside nested functions.
* Keep render logic free of side effects.
* Do not use `useEffect` for:

  * derived state
  * filtering/sorting/mapping data for display
  * syncing one piece of React state to another
  * handling user events
* Prefer controlled, explicit props over hidden behaviour.

### TypeScript

* Keep TypeScript strictness intact. Do not weaken compiler settings.
* Do not introduce `any` unless there is no practical alternative.
* Prefer `unknown` over `any` at external boundaries.
* Narrow or validate unknown values before use.
* Do not silence type errors without a clear comment explaining why.
* Avoid unsafe casts unless necessary and justified.

### Data and API boundaries

* Treat all external data as untrusted:

  * API responses
  * query params
  * local storage
  * session storage
  * browser APIs
  * user input
* Validate, parse, or narrow external data before it reaches business logic or UI.
* Do not pass raw backend response shapes deep into the component tree if a mapped frontend type is more appropriate.

### State management

* Keep local state minimal.
* Do not store derived values in state unless there is a clear performance or interoperability reason.
* Separate server state from local UI state.
* Do not hand-roll ad hoc caching or refetch logic if the app already has an approved server-state pattern.

### Changes and dependencies

* Do not introduce new dependencies unless they are clearly justified and consistent with the existing stack.
* Prefer existing utilities, hooks, and shared components before creating new ones.
* Do not duplicate logic that already exists elsewhere in the frontend.
* Do not change public component APIs without checking for existing usage.

---

## Preferred patterns

Use these by default unless there is a strong reason not to.

### Components

* Keep components focused and reasonably small.
* Split responsibilities clearly:

  * presentational UI
  * feature orchestration
  * hooks for reusable behaviour
  * API/service logic
* Prefer composition over deeply configurable mega-components.
* Extract repeated UI or logic only when it improves clarity or reuse.

### State

* Keep state as close as possible to where it is used.
* Lift state only when multiple consumers genuinely need the same source of truth.
* Compute display values during render with normal TypeScript and JavaScript.
* Memoise only when there is a demonstrated need.

### Data fetching

* Use the repo’s approved server-state approach for async data.
* Keep fetching and mutation logic out of purely presentational components.
* Use stable query/cache keys where relevant.
* Handle loading, empty, error, and success states explicitly.

### Types

* Prefer explicit domain types for important concepts.
* Keep types close to the code that owns them unless they are shared across features.
* Use discriminated unions for state variants where appropriate.
* Prefer narrow, precise types over broad optional bags of fields.

### Forms

* Follow the repo’s standard form approach.
* Validate user input at the boundary.
* Keep validation logic explicit and readable.
* Surface validation and submission states clearly in the UI.

---

## File placement rules

When adding code, place it according to the existing feature structure in this frontend.

Default placement rules:

* **UI components** go near the feature that owns them unless they are genuinely shared.
* **Shared reusable components** go in the shared UI/component area.
* **Hooks** go near the feature that uses them, or in a shared hooks area if reused broadly.
* **API/client code** goes in the established service/client layer, not inside presentational components.
* **Types** should live with the feature unless shared across multiple features.
* **Tests** should live alongside the code they verify unless the repo uses a separate test layout.

If there is an established local pattern in a directory, follow that pattern.

---

## Styling rules

Follow the existing styling approach in this frontend. Do not introduce a new styling pattern in a small feature change.

General expectations:

* Prefer existing design system components, tokens, and utilities.
* Reuse existing spacing, typography, and layout patterns.
* Do not hardcode one-off styles if a shared token or component already exists.
* Keep conditional styling readable.
* Avoid deeply nested styling logic in component files.

---

## Editing existing code

When modifying existing files:

* preserve the current public behaviour unless the task requires changing it
* preserve accessibility unless improving it
* preserve existing tests unless they are incorrect
* match the surrounding style and conventions
* do not opportunistically rewrite large files
* do not move files unless there is a clear structural reason

When code is messy, improve only the part you must touch unless a slightly broader cleanup materially reduces risk.

---

## Testing expectations

For any meaningful frontend change:

* update or add tests where the repo already has tests for that area
* verify loading, error, and empty states where relevant
* verify important user interactions
* verify type safety and build correctness
* do not add fragile tests tied to incidental implementation details

Prefer tests that check user-visible behaviour over tests that mirror implementation.

---

## Accessibility expectations

Do not degrade accessibility.

Minimum expectations:

* use semantic HTML where possible
* ensure interactive controls are proper buttons/links
* keep keyboard interaction intact
* keep labels and accessible names clear
* preserve focus behaviour unless intentionally changing it
* provide meaningful states for loading and errors

---

## Performance expectations

Do not optimise prematurely.

Before adding memoisation or performance complexity:

* check whether state ownership is wrong
* check whether derived state is unnecessary
* check whether renders are caused by avoidable parent updates

Only add `useMemo`, `useCallback`, or `memo` when there is a clear need.

---

## Definition of done for frontend changes

A frontend change is not complete until:

* the code follows the rules in this file
* types are sound
* linting passes
* relevant tests pass
* loading, empty, error, and success states are handled where applicable
* new code is placed in the correct location
* no unnecessary dependency or abstraction has been introduced

---

## Validation steps

Before finishing, run the relevant frontend checks from this directory.

Typical examples:

```bash
npm run lint
npm run test
npm run build
```

Or, if this repo uses another package manager:

```bash
pnpm lint
pnpm test
pnpm build
```

Only run commands that exist in this frontend project.

If you cannot run commands, say so explicitly and state which checks should be run by the user.

---

## Agent behaviour rules

When working in this frontend:

* prefer small, safe, local changes
* prefer existing patterns over invented ones
* explain trade-offs when introducing a new pattern
* do not guess architecture if the repo already implies one
* do not add new dependencies casually
* do not ignore lint or type errors
* do not leave TODO-driven half-implementations unless the task explicitly asks for scaffolding
* call out ambiguity instead of silently making high-impact architectural changes

When several valid options exist, choose the one that is:

1. most consistent with the current repo
2. simplest to understand
3. easiest to maintain

---

## Project-specific decisions

### Approved libraries

* Server state: **none** (imperative `fetch` from `src/api/*`; add TanStack Query only if caching/refetch patterns justify it)
* Forms: **none** (no forms-heavy flows yet; MUI primitives when needed)
* Validation: **manual type guards** in `src/api/` (no Zod in tree today; add if validation grows)
* Routing: **none** (single-view Vite SPA)
* Styling: **MUI 7 + Emotion** (`@mui/material`, `@emotion/react`, `@emotion/styled`), plus `src/index.css` / `src/App.css`
* Testing: **not wired yet** — track [issue #7](https://github.com/MatthewJWhittle/hsm-app/issues/7) (Vitest + Testing Library + `npm test`)

### Conventions

* Export style: **mixed** — `App` and `Map` default-exported (Vite/React convention); prefer **named exports** for new components and `src/api/*`
* Component file naming: **`PascalCase.tsx`** for components
* Hook naming: `useX`
* Test naming: **`*.test.tsx`** next to source (once test runner exists)
* Shared types location: **`src/types/`**
* API client location: **`src/api/`** (`catalog.ts`, `inspectPoint.ts`, parsers, `errors.ts`)
* Shared UI location: **`src/components/`** (feature subfolders e.g. `map/`)

### Commands

* Lint: `npm run lint`
* Test: *not configured* — [#7](https://github.com/MatthewJWhittle/hsm-app/issues/7)
* Build: `npm run build` (runs `tsc -b` then Vite)
* Typecheck: `npm run build` (project references) or `npx tsc -b --noEmit` from `frontend/`

### Forbidden in this repo

* Raw `fetch` / URL construction inside purely presentational components — use **`src/api/`** or props/callbacks from a parent that owns IO
* Weakening **`strict`** TypeScript or silencing errors without a short comment
* New dependencies without justification (see core `AGENTS.md` rules)

---

## Example decision rules

Use these defaults unless repo-specific guidance overrides them.

* If adding a new screen-level feature, create or extend a feature folder rather than placing everything in a shared directory.
* If adding API-driven UI, keep remote data logic in hooks/services and keep presentational components focused on rendering.
* If data needs transformation for display, prefer pure mapping functions over effect-driven syncing.
* If a component is becoming too large, split by responsibility, not by arbitrary line count.
* If a type comes from the backend but is awkward for the UI, map it into a frontend-specific type rather than leaking backend structure everywhere.

---

## In case of conflict

If there is a conflict between:

1. this file
2. a nearer `AGENTS.md`
3. explicit task instructions
4. existing repo constraints required for correctness

follow the more specific constraint, but keep changes minimal and explain any deviation.
