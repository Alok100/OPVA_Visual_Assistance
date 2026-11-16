---
name: ui-implementation
description: Design and implement consistent, accessible screens and reusable components for Visual Inspector. Use when adding or changing a screen, a workflow component, or a shared UI primitive in this repo.
---

# UI Implementation

Use this skill when building or changing anything under `src/app/(workflow)/` or
`src/components/` in this repo.

## Before writing a component

1. Check `src/components/shared/` and `src/components/ui/` first. `PageHeader`, `Card`,
   `StatusBadge`, `DemoDataTag`, `EmptyState`, `PlaceholderThumbnail` cover most needs — don't
   rebuild a bordered box, a status pill, or an empty state from scratch.
2. Check `docs/UI_DESIGN_SPEC.md` for the agreed colors, spacing, and per-screen assumptions
   before inventing a new pattern.
3. If the component is used by exactly one screen, put it in
   `src/components/workflow/<screen>/`. If it could reasonably be reused by another screen, put
   it in `src/components/shared/` instead.

## Building a new screen or section

1. Start from `PageHeader` for the title/description/actions row.
2. Compose the body from `Card` sections — one `Card` per logical group of information, not one
   giant card per screen.
3. Every grid needs an explicit base `grid-cols-N` (e.g. `grid-cols-1 lg:grid-cols-2`) — never a
   bare `grid` with only a breakpoint-prefixed column class. See CLAUDE.md for why (grid blowout
   on narrow viewports).
4. Every `truncate` needs a `min-w-0` on the same element (or its flex/grid item ancestor) or it
   silently fails to ellipsize and clips against the viewport edge instead.
5. If the section shows any value, count, prediction, or result that isn't from a real pipeline,
   wrap/tag it with `DemoDataTag` or say "Demo data"/"Illustrative" in the copy, every time it's
   shown — not just once on the screen.

## Accessibility checklist (apply to every new interactive element)

- Icon-only buttons get `aria-label`.
- Status is never color-only — pair color with an icon and/or text (use `StatusBadge`).
- Don't override `focus-visible` styles away; shadcn's defaults already give a visible ring.
- Active nav links get `aria-current="page"`.
- Form inputs get an associated `<Label>`.

## Responsive checklist

- Test (or at least reason through) both a desktop width (~1440px) and a narrow width (~390px).
- Below `lg` (1024px): the sidebar is an off-canvas drawer, not squeezed inline — don't add a
  second collapsing mechanism.
- Flex/grid rows with a label + a value/action pair (e.g. a card header with a badge) should
  stack (`flex-col sm:flex-row`) if the combined content could plausibly exceed ~300px at the
  `sm` breakpoint.

## When you're done

Run `npm run build` and `npm run lint`. If you changed the visual language (new color, new
pattern, new breakpoint behavior), update `docs/UI_DESIGN_SPEC.md` in the same change.
