# Product Scope

## Vision

Visual Inspector lets a manufacturing team set up an AI-powered visual quality inspection
without writing code or hand-configuring a computer-vision pipeline. A user describes what to
inspect in plain language (e.g. "Detect every bolt and verify whether each bolt has the expected
white line marking"), uploads example images, and the product is meant to:

1. Interpret the requirement into a concrete set of checks.
2. Help annotate example images (AI-assisted, human-reviewed).
3. Assess whether the resulting dataset is ready to train on.
4. Train and evaluate a detection model, then let the team publish it to production.

It's designed for "any industry, any inspection requirement, no technical knowledge required" —
the target user is a quality engineer or line supervisor, not a data scientist.

## Current phase (this repo, right now)

This repo has grown past a pure UI prototype. The four-screen shell and navigation (Microtask 1)
were the starting point; real backend functionality has since landed for the first two screens.
**Implemented** = real code, not demo data. **Partial** = real code with a stated, real limit.
**Pending** = still mock/simulated UI only, no backend wiring. See `docs/ROADMAP.md` for the
microtask-by-microtask history this maps to.

### Implemented

- The four-screen workflow shell, navigation, and responsive layout.
- A real FastAPI backend (`backend/`) — filesystem-JSON storage, deliberately no database and
  no MCP server (see `docs/ARCHITECTURE.md`'s "why no X").
- Real image upload and persistence: validated content-type/size/corrupt-file checks, real pixel
  dimensions captured and used for coordinate mapping.
- Real annotation JSON import: auto-detects COCO, LabelMe, Supervisely/DatasetNinja, or a
  documented custom format; matches boxes to images by filename; validates coordinates against
  real image dimensions. See `docs/MICROTASK_3_1_FINDINGS.md`.
- Real visualization of imported and hand-drawn boxes over the real uploaded image.
- A real manual annotation editor (draw/move/resize/delete/relabel a box) with real backend
  persistence — edits survive a reload or reopening the inspection, not just local browser state.
- A real review/approve workflow: a box moves forward only through
  `not reviewed → human-verified → approved for training`, enforced server-side (an annotation
  can't silently become "approved"). See `docs/MICROTASK_3_2_FINDINGS.md`.

### Partial

- Requirement interpretation (`/` screen) calls a real backend endpoint, but it's deterministic
  keyword matching for one known requirement shape (bolt + count + color marking) — not a
  general LLM planner. See `docs/MICROTASK_2_FINDINGS.md`.
- The real detect → color-check → verdict pipeline exists and runs for real
  (`backend/app/pipeline.py`), but isn't reliable enough across scene types to wire into the main
  Annotation screen as "AI-generated" boxes yet (see `docs/MICROTASK_2_FINDINGS.md` /
  `MICROTASK_2_2_FINDINGS.md`). It's reachable only from a separate, explicitly-labeled
  `/inference` testing screen, manually triggered, never automatic.
- "Unapproved annotations cannot enter the training dataset" is enforced mechanically (a
  dedicated, tested backend function filters to approved-only boxes) but has no real
  training/export consumer yet to demonstrate it against — see the next point.

### Pending (still demo/simulated UI only, no backend wiring)

- Dataset readiness / Analysis screen — static mock metrics.
- Training & evaluation screen — a timed fake progress bar and mock metrics; no real training
  job, and nothing yet reads the approved-annotation data the backend now tracks.
- Multi-user accounts, auth, dark mode, deployment/monitoring screens — unscheduled.

Every number, prediction, or result that's still Pending is visibly labeled demo/illustrative
(`DemoDataTag` or explicit copy), per CLAUDE.md's anti-fabrication rule.

## Out of scope for this phase

- Real dataset quality analysis (Analysis screen).
- Real model training, evaluation, or deployment.
- Multi-user accounts, auth, or permissions.
- Databases or MCP servers — the backend stays filesystem-JSON, deliberately minimal.

## Example workflow used throughout the UI

To keep the four screens coherent, every screen uses the same example inspection:

- **Inspection**: "Tractor Wheel Assembly Check" at "Plant A — Wheel Assembly Line 1."
- **Requirement**: "Detect every bolt and verify whether each bolt has the expected white line
  marking."
- **Checks**: bolt detection & counting, white line mark verification, bolt count consistency.

This mirrors the example in the supplied concept poster (`artifacts/reference/`) without copying
its exact numbers — those are redrawn as this project's own demo dataset.
