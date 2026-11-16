# UI Design Spec

Visual direction agreed for this phase. The supplied concept poster
(`artifacts/reference/visual-inspector-concept-poster.png`) is the design reference — treated as
guidance for mood and layout, not a pixel-exact spec. Where the poster was ambiguous for one of
our four screens, the assumption taken is noted inline below.

## Look and feel

Modern, industrial-professional SaaS — closer to a quality-control dashboard than a chatbot or a
consumer app. Light theme only in this phase (no dark mode toggle yet).

- **Background**: `#f8fafc` (very light slate) for the page canvas, `#ffffff` for cards — enough
  contrast to separate panels without heavy borders.
- **Primary accent**: `#2563eb` (blue-600), used for the active nav state, primary buttons, step
  badges, and the progress/gauge visualizations.
- **Text**: `#0f172a` (near-black slate) for body text, `#64748b` (slate-500) for secondary/
  muted text.
- **Status colors**: emerald for success/pass, amber for warning/needs-review, red for
  danger/failed, blue for informational. Always paired with an icon (`StatusBadge`), not color
  alone, for accessibility.
- **Borders & shadows**: 1px `#e2e8f0` borders, no heavy drop shadows — cards use a subtle
  `ring-1 ring-foreground/10` from shadcn's `Card`, not custom box-shadows.
- **Corners**: `0.75rem` base radius on cards/inputs (`--radius` in `globals.css`) — rounded but
  not pill-shaped, except badges and the sidebar's step-number circles which are fully round.
- **Type**: Geist Sans (via `next/font/google`), the default shadcn "Nova" preset pairing.

## Layout

- **Sidebar** (288px, fixed on desktop ≥ lg, off-canvas drawer below lg): logo/wordmark, a
  project selector, the four numbered workflow steps with active-state highlighting, and a
  compact project-status panel at the bottom. See `components/layout/sidebar.tsx`.
- **Header** (64px): breadcrumb (`inspection name › current screen`), a "Step N of 4" badge, and
  a persistent "UI prototype" tag reminding the user this phase has no live AI. A hamburger
  button appears below the `lg` breakpoint to open the sidebar drawer.
- **Main workspace**: centered, `max-w-6xl`, consistent `PageHeader` (title + description +
  optional actions) at the top of every screen, then a vertical stack of `Card`-based sections.

## Reusable patterns

- `PageHeader` — every screen's title + one-line description + optional action slot.
- `Card` / `CardHeader` / `CardTitle` / `CardAction` / `CardContent` — every panel.
- `StatusBadge` — tone-based pill (success/warning/danger/info/neutral) with icon.
- `DemoDataTag` — dashed amber pill marking a value as demo/illustrative data. Required wherever
  a number or prediction isn't from a real pipeline (see CLAUDE.md's "avoiding fabricated
  functionality").
- `EmptyState` — icon + title + description for "nothing here yet" states (not-analyzed,
  not-trained, etc.).
- `PlaceholderThumbnail` — a labeled gradient placeholder standing in for an inspection photo,
  since no real sample photos exist in this phase (see "Demo imagery" below).
- **Inline error banner** (added in the Task 2 review, see `ImageDropzone`'s `error` prop) —
  `border-red-200 bg-red-50 text-red-700` with an `AlertTriangle` icon and a dismiss (`X`) button,
  same red used by `StatusBadge`'s danger tone. Use this pattern for any other validation error
  that can occur client-side in this phase (no real backend errors exist yet).

## Demo imagery

No real inspection photographs are bundled with this phase. Rather than fabricate photos that
could be mistaken for real captured images, uploaded/demo images are rendered as labeled
placeholder tiles (`PlaceholderThumbnail`) with a filename and a muted icon. Real file uploads
(via drag-and-drop or the file picker) *do* render actual client-side image previews — that part
is genuinely functional, just not sent anywhere or processed.

## Per-screen notes & assumptions

- **User Input** (`/`): the poster splits "describe requirement" and "AI analysis & plan" into
  two separate steps (1 and 2). This phase merges them into one screen ("Configure Your
  Inspection") per the task's screen list, with the interpreted-plan panel appearing once
  "Analyze Requirement" is clicked.
- **AI Annotation** (`/annotation`): combines the poster's "upload" and "annotate" steps into one
  screen, since uploads happen on the User Input screen in our flow — this screen assumes images
  are already present and focuses on reviewing AI-suggested boxes. It always shows a fixed
  12-image example set (matching the "Images: 12" stat shown elsewhere), independent of whatever
  was actually uploaded on the User Input screen — this is disclosed directly on the page
  ("Showing a fixed example image set…"). Wiring the two together is a reasonable next step but
  was treated as a design decision for the user to approve rather than done silently (see the
  Task 2 completion report).
- **Analysis** (`/analysis`): not a direct 1:1 match to any single poster step — it's a new
  screen synthesizing dataset-readiness concerns that the poster spreads across its "upload" and
  "validation" steps. Readiness is shown as a conic-gradient gauge (hand-built CSS, no chart
  library) plus per-dimension progress bars.
- **Training** (`/training`): maps to the poster's "Model Creation/Training" and "Validation &
  Testing" steps combined into one screen, defaulting to a clear not-yet-run state per the task
  spec.

## Interactive annotation editor (Annotation screen)

The first interactive-canvas pattern in the repo (everything else is static display). An
"Edit annotations" toggle on the image canvas reveals:

- A floating vertical tool strip (Roboflow-style), absolute-positioned at the left-center edge
  of the image: a select/draw `ToggleGroup`, a `Separator`, then a delete button — all icon-only
  with `aria-label` + `Tooltip`.
- Boxes as absolutely-positioned `<div>`s (not `<canvas>`/`<svg>`), matching the existing
  read-only box overlay technique — percent-of-image coordinates, converted to/from the
  underlying pixel-or-percent `ViewBox` unit at the edges (see
  `src/components/workflow/annotation/edit-geometry.ts`).
- A selected box gets a `ring-2 ring-primary` highlight plus 8 small square resize handles.
- The side panel gains a "Boxes on this image" list (color swatch, inline-editable label on the
  selected row, per-row delete) — clicking a row selects the same box on the canvas.
- Edits are **frontend-only** this pass — kept in page state, not sent to a backend. A
  `StatusBadge tone="warning"` ("Unsaved edits") and a side-panel note make this explicit, per
  CLAUDE.md's rule against an action that looks like a persisted success but isn't.
- Known limitation: move/resize is pointer-only (no keyboard equivalent, and the drag handles are
  plain `<div>`s rather than `<button>`s) — Delete/Backspace is the one keyboard-accessible edit
  action, plus Escape to deselect/cancel a draw.

## Accessibility

- Color is never the only signal — status badges always carry an icon and a text label.
- All interactive elements are real `<button>`/`<a>` elements (via shadcn primitives), so they're
  keyboard-reachable and have visible focus rings by default.
- Icon-only buttons (nav toggle, image prev/next, remove-image) have `aria-label`.
- Sidebar navigation uses `aria-current="page"` on the active link.

## Responsive behavior

- `lg` (1024px) and up: sidebar is static/always visible, two-column grids apply.
- Below `lg`: sidebar becomes an off-canvas drawer (hamburger toggle in the header), grids
  collapse to a single column (every grid has an explicit base `grid-cols-1`, see CLAUDE.md).
- Verified at both a desktop width (1440px) and a narrow mobile width (390px) — see
  `artifacts/reviews/` for the review screenshots from this pass.
