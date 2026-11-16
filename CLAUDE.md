# CLAUDE.md

Project instructions for Claude Code (and any other agent) working in this repository.

## Product

Visual Inspector is an AI-powered visual quality inspection tool for manufacturing. A user
describes an inspection in plain language, uploads images, reviews AI-assisted annotations,
checks dataset readiness, and trains/evaluates a detection model — without writing code or
configuring a CV pipeline by hand.

See `docs/PRODUCT_SCOPE.md` for the full vision and current boundaries.

## Current phase: UI and navigation only

This repo is in **Microtask 1**: the application shell, all four workflow screens, and
navigation between them. There is **no real AI, computer-vision, annotation, or model-training
functionality** yet — see `docs/ROADMAP.md` for what's planned next. Do not start later-phase
work (real pipelines, a backend, MCP servers, databases, LLM calls) without the user's explicit
go-ahead.

## Architecture

- Next.js (App Router) + TypeScript + Tailwind CSS v4 + shadcn/ui (Radix primitives) +
  `lucide-react` icons. No chart library — simple visualizations (progress bars, a conic-gradient
  gauge) are hand-built in `components/workflow/analysis/readiness-gauge.tsx` to avoid an
  unnecessary dependency for a handful of metrics.
- Route group `src/app/(workflow)/` holds the four screens and their shared layout
  (`layout.tsx` renders `Sidebar` + `Header` + the scrollable main area). Routes:
  `/` (User Input), `/annotation`, `/analysis`, `/training`.
- `src/lib/types.ts` — shared domain types. `src/lib/mock-data.ts` — all demo data, clearly
  commented as demo-only. `src/lib/inspection-context.tsx` — the one piece of cross-screen state
  (the example inspection's name/requirement text), via React Context. Don't reach for a state
  library (Redux/Zustand) until a real backend justifies it.
- `src/components/ui/` — shadcn primitives, generated via the shadcn CLI. Prefer regenerating/
  extending via `npx shadcn@latest add <component>` over hand-rolling a primitive.
- `src/components/layout/` — `Sidebar`, `Header` (the persistent app shell).
- `src/components/shared/` — cross-screen building blocks: `PageHeader`, `StatusBadge`,
  `DemoDataTag`, `EmptyState`, `PlaceholderThumbnail`.
- `src/components/workflow/<screen>/` — components used by exactly one screen.

See `docs/ARCHITECTURE.md` for more detail and how future phases should plug in.

## Commands

- `npm run dev` — start the dev server (Turbopack).
- `npm run build` — production build; also runs the TypeScript check.
- `npm run lint` — ESLint.

Always run `npm run build` and `npm run lint` before calling a UI change done.

## UI design conventions

Full spec in `docs/UI_DESIGN_SPEC.md`. Short version:

- Light theme only (no dark mode in this phase). Colors are plain hex custom properties in
  `src/app/globals.css`, blue (`#2563eb`) as the primary accent.
- Status colors: green/emerald = success, amber = warning, red = danger, blue = info/neutral.
  Use `StatusBadge` for these, not ad-hoc color classes.
- Every grid container needs an explicit base `grid-cols-N` (e.g. `grid-cols-1 lg:grid-cols-2`),
  never a bare `grid` with only a breakpoint-prefixed `*:grid-cols-*`. Tailwind's `grid-cols-N`
  compiles to `repeat(N, minmax(0, 1fr))`; without the `minmax(0, …)` floor a grid item's
  intrinsic content width can force the whole row (and page) wider than the viewport.
- Any flex/grid child that should truncate with `truncate` needs `min-w-0` alongside it — a flex
  item's default `min-width: auto` otherwise overrides `text-overflow: ellipsis` and the text
  silently clips against the viewport edge instead of showing `…`.
- Reuse `Card`/`CardHeader`/`CardTitle`/`CardContent`/`CardAction` from `components/ui/card.tsx`
  for every panel; don't build one-off bordered boxes.
- Accessibility: every icon-only button needs `aria-label`; interactive elements must be
  reachable by keyboard and show a visible focus ring (shadcn's defaults handle this — don't
  override `focus-visible` styles away).

## Avoiding fabricated functionality

This is a hard rule, not a style preference:

- Any value, count, score, prediction, or result that isn't computed by a real pipeline must be
  visibly labeled as demo/illustrative — use `DemoDataTag` or put "Demo data" / "Illustrative"
  directly in the copy. See `src/lib/mock-data.ts`'s file header.
- Don't wire a button to simulate success silently. If a button's real behavior is planned for a
  later phase, either make it a clearly-labeled demo action (see `TrainingStatusCard` — clicking
  "Start Demo Training Run" explicitly says it's a UI demo before you click it) or show a
  "not yet connected" state — never a fake success that looks indistinguishable from a real one.
- Don't claim a model "ran," an image was "analyzed," or a pipeline "detected" something unless
  that's literally true in this codebase.

## When architecture changes

If you change the stack, folder conventions, or a cross-cutting pattern (new shared state
approach, a new component library, a routing restructure), update `docs/ARCHITECTURE.md` and this
file in the same change — don't let docs drift from what the code does.

## Explaining decisions

When a design or architecture choice isn't obvious from the code (why this library, why this
pattern over an alternative, an assumption made because the reference image was ambiguous),
say so in your response to the user. Don't let non-obvious tradeoffs go unexplained.
