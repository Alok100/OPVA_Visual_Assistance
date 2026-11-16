# Architecture

## Stack

- **Next.js 16** (App Router, Turbopack) + **TypeScript** (strict mode).
- **Tailwind CSS v4** (CSS-first config via `@theme` in `src/app/globals.css`, no `tailwind.config.ts`).
- **shadcn/ui** on Radix UI primitives, generated via the shadcn CLI into `src/components/ui/`.
- **lucide-react** for icons.
- No state management library, no chart library, no backend/database/MCP server — none are
  justified yet in this UI-only phase. See "Why no X" below.
- `devIndicators: false` in `next.config.ts` — Next.js's dev-mode build indicator defaults to a
  fixed bottom-left (or bottom-right) badge; every screen in this app has real content pinned to
  both bottom corners (sidebar status panel, primary action bar), so the indicator ends up
  covering something regardless of corner. Disabling it only affects local dev, not production
  builds.

## Why this stack

- **Next.js + TypeScript**: the task asked for a maintainable, typed frontend foundation; App
  Router gives file-based routing that maps cleanly onto the four workflow screens, and a route
  group (`(workflow)`) lets them share one layout without the group showing up in the URL.
- **Tailwind + shadcn/ui**: fast to build a consistent, accessible component set without writing
  a design system from scratch, while keeping full control of the generated component source
  (shadcn copies components into the repo rather than installing an opaque UI package).
- **No chart library**: the only "charts" needed in this phase are a handful of progress bars and
  one readiness gauge. Both are a few lines of CSS (`Progress` from shadcn, a `conic-gradient` for
  the gauge in `components/workflow/analysis/readiness-gauge.tsx`). Pulling in a charting library
  for this would be the kind of unnecessary dependency CLAUDE.md asks to avoid; revisit once a
  screen needs real time-series or multi-series charts.
- **No state library**: the only cross-screen state is the current example inspection's name and
  requirement text, handled by one `React.Context` (`src/lib/inspection-context.tsx`). Redux/
  Zustand/Jotai would be premature until a real backend introduces server state worth caching.

## Folder layout

```
src/
  app/
    (workflow)/            route group: shared shell + the four screens
      layout.tsx            Sidebar + Header + scrollable main area
      page.tsx               Screen 1: User Input           → /
      annotation/page.tsx    Screen 2: AI Annotation         → /annotation
      analysis/page.tsx      Screen 3: Analysis              → /analysis
      training/page.tsx      Screen 4: Training               → /training
    layout.tsx              root layout: fonts, metadata, <TooltipProvider>
    globals.css             Tailwind + theme tokens (light theme only)
  components/
    ui/                     shadcn primitives (generated, prefer `shadcn add` to hand-editing)
    layout/                 Sidebar, Header
    shared/                 PageHeader, StatusBadge, DemoDataTag, EmptyState, PlaceholderThumbnail
    workflow/
      user-input/           components used only by Screen 1
      annotation/           components used only by Screen 2
      analysis/             components used only by Screen 3
      training/             components used only by Screen 4
  lib/
    types.ts                shared domain types (Inspection, WorkflowStageMeta, …)
    mock-data.ts            ALL demo data lives here, clearly marked as demo-only
    inspection-context.tsx  the one piece of cross-screen state
docs/                       this file + PRODUCT_SCOPE, UI_DESIGN_SPEC, ROADMAP
artifacts/
  reference/                the original concept poster (never modified)
  reviews/                  generated review screenshots (gitignored, not committed)
.claude/skills/              ui-implementation, quality-check
```

## Data flow (current phase)

Everything is client-side, in-memory, and resets on reload:

- `mock-data.ts` exports static arrays/objects (`EXAMPLE_INSPECTION`, `DEMO_IMAGES`,
  `TRAINING_METRICS`, etc.) consumed directly by components as read-only demo content.
- `InspectionProvider` (React Context) holds the one piece of state that actually needs to persist
  across screens during a session: the current inspection's name and requirement text, plus
  whether the requirement has been "analyzed" (a UI-only flag).
- Per-screen interactive state (uploaded images, annotation toggle, training run progress) lives
  in local `useState` in that screen's `page.tsx` or a child component — it does not need to be
  global since no other screen reads it in this phase.

## How future phases plug in

When real functionality replaces a demo screen, the intended seams are:

- **Annotation pipeline**: replace the static `DEMO_ANNOTATIONS` read in
  `components/workflow/annotation/annotation-canvas.tsx` with a fetch to a real
  detection/annotation API, keyed by the uploaded image. The box-overlay rendering logic (percentage-
  based positioning) already works generically — only the data source changes.
- **Dataset analysis**: replace the static quality-metric arrays in
  `app/(workflow)/analysis/page.tsx` with a real analysis API call; `QualityBreakdown` and
  `ReadinessGauge` already take plain `{ label, value }` props.
- **Training**: replace the `setInterval`-based fake progress in
  `app/(workflow)/training/page.tsx` with real job polling (or a websocket/SSE stream); keep the
  same `TrainingRunState` (`idle` | `running` | `completed`) so `TrainingStatusCard`,
  `EvaluationResultsCard`, and `PredictionPreviewCard` don't need to change shape.
- **Backend/persistence**: when introduced, it should own `Inspection` records server-side;
  `InspectionProvider` can then be backed by server data (e.g. via a fetch + mutation layer)
  instead of local `useState`, without changing the context's consumer-facing API
  (`inspection`, `setRequirementText`, `requirementConfirmed`, `confirmRequirement`).

Update this file whenever one of these seams changes shape, or a new architectural decision
(new dependency, new cross-cutting pattern) is made.
