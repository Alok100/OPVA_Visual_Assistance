---
name: quality-check
description: Run the relevant checks for Visual Inspector, identify incomplete or fabricated functionality, and verify navigation and responsive behavior. Use before declaring any UI change in this repo done.
---

# Quality Check

Use this skill before telling the user a change to this repo is complete.

## 1. Static checks (always)

```bash
npm run build   # also runs the TypeScript check
npm run lint
```

Both must pass clean. Don't report a change as done if either fails, and don't fix a failure by
suppressing it (`// eslint-disable`, `@ts-ignore`) unless the underlying rule is genuinely wrong
for that line — fix the code instead.

## 2. Run the app and look at it

Start the dev server (`npm run dev`) and actually view the affected screen(s) — don't infer
correctness from the code alone. If a browser tool is available, use it.

**If taking screenshots via headless Chrome CLI flags**: `--window-size=<w>,<h>` is **not
reliable for small widths** on at least some Chrome versions — it silently clamps to a larger
floor (observed: requests below ~500px wide still render at a wider internal width, while
`--screenshot` crops the output to the requested pixel size, producing a screenshot that *looks*
like a horizontal-overflow bug but isn't one). Don't trust a `--window-size` screenshot under
~500px wide as proof of a responsive bug. If you need a reliable narrow-viewport screenshot,
either use a real browser automation tool's viewport/device-emulation API (not a CLI flag), or
verify independently via DOM measurement (e.g. `window.innerWidth === document.documentElement.scrollWidth`
through whatever JS-execution capability is available) before concluding there's a real overflow.

## 3. Navigation checklist

- Every sidebar link navigates to the right screen and shows the correct active state.
- Direct navigation to each route (`/`, `/annotation`, `/analysis`, `/training`) works, not just
  clicking through from the home screen.
- Primary "Continue to…" buttons on each screen navigate to the next screen.
- Browser back/forward works (this should hold automatically with plain Next.js `<Link>` /
  `useRouter().push` — flag it if you've introduced any custom history manipulation).

**If verifying back/forward over raw CDP**: there is no `Page.goBack` / `Page.goForward` method
in the Chrome DevTools Protocol — sending one silently fails (the response has no `result`, easy
to mistake for "it did nothing"). Use `Page.getNavigationHistory` to read `currentIndex`/`entries`,
then `Page.navigateToHistoryEntry` with the target entry's `id`.

**If testing a file upload (drag-and-drop or picker)**: simulating a raw `drop` DragEvent with a
script-constructed `DataTransfer` is unreliable in headless Chrome and may silently no-op. Use
`DOM.setFileInputFiles` on the underlying `<input type="file">` (with a real file on disk) instead
— it's the standard, reliable way to drive file inputs over CDP.

## 4. Responsive checklist

- Check a desktop width (~1440px) and a narrow width (~390px) — see the gotcha in step 2 for how
  to do this reliably.
- No horizontal scrollbar/overflow at either width.
- Sidebar collapses to the off-canvas drawer below `lg`; the hamburger button opens/closes it.
- Text truncates with `…` rather than clipping hard against an edge (if it clips hard, it's
  almost always a missing `min-w-0` — see CLAUDE.md).

## 5. Fabricated-functionality check

For every new or changed value, prediction, count, or result on screen, ask: is this from a real
pipeline, or is it demo/mock data? If it's demo data, it must be visibly labeled (`DemoDataTag` or
explicit "Demo"/"Illustrative" copy) at the point it's shown — check this on the actual rendered
screen, not just in the component source, since a label can be present in code but hidden/cut off
in the rendered layout.

## 6. Report honestly

State exactly which checks you ran and what passed/failed. If something couldn't be verified
(e.g. no browser tool available), say so explicitly rather than implying it was checked.
