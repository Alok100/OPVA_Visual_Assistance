# Roadmap

Planned implementation phases, each as a small reviewable microtask. Nothing beyond Microtask 1
should be started without the user's explicit go-ahead (see CLAUDE.md).

## Microtask 1 — Project foundation, UI design & navigation (this repo, current)

- Next.js + TypeScript + Tailwind + shadcn/ui foundation.
- Application shell (sidebar, header) shared across four screens.
- All four screens built with realistic empty/demo/loading states, no real backend.
- Navigation between all screens, verified at desktop and mobile widths.
- Project docs (`docs/`), two Claude Code skills, and `CLAUDE.md`.

## Microtask 2 — Real requirement interpretation (done, deterministic not LLM)

- The User Input screen's "Analyze Requirement" action calls a real backend endpoint
  (`backend/app/spec.py`), replacing `INTERPRETED_CHECKS` mock data — but it's deterministic
  keyword matching for the one known requirement shape (bolt + count + color marking), not a
  general LLM call. See `docs/MICROTASK_2_FINDINGS.md`.
- A true general-purpose LLM-backed interpretation (arbitrary requirement text → checks) is
  still unbuilt.

## Microtask 3 — Real annotation pipeline (import, visualization, manual editing, and
review/approve persistence all done; only real AI-detection wiring still open)

- Done (Microtask 3.1 — see `docs/MICROTASK_3_1_FINDINGS.md`): real image upload, JSON
  annotation import (COCO/LabelMe/Supervisely/custom, auto-detected), and visualization of the
  imported boxes over the real uploaded image on the Annotation screen.
- Done (Microtask 3.2 — see `docs/MICROTASK_3_2_FINDINGS.md`): the manual annotation editor
  (draw/move/resize/delete/relabel a box) now persists to the backend — edits survive reload and
  reopening the inspection, with traceable provenance against the original import. A
  review/approve workflow (`not reviewed → human-verified → approved for training`) is enforced
  server-side, so an annotation can never silently become "approved."
- Still open: wiring the real detect → color-check pipeline (`backend/app/pipeline.py`, proven
  out on a side `/inference` testing screen per `docs/MICROTASK_2_FINDINGS.md`/
  `MICROTASK_2_2_FINDINGS.md`) into the main Annotation screen as "AI-generated" boxes — the
  underlying model isn't reliable enough yet (see those findings) and this hasn't been judged
  ready for the primary flow.
- Still open: a real training/export step that actually reads `approved_for_training` boxes —
  the backend now tracks approval status and guarantees unapproved boxes are excluded from it
  (mechanically, with a test), but nothing downstream consumes it yet (see Microtask 5).

## Microtask 4 (proposed) — Real dataset analysis

- Replace the static image-quality / annotation-quality metrics on the Analysis screen with a
  real analysis job over the uploaded dataset.
- Replace the static `DATASET_ISSUES` with real issue detection.

## Microtask 5 (proposed) — Real training & evaluation

- Replace the simulated progress bar on the Training screen with a real training job (polling or
  streaming status).
- Replace `TRAINING_METRICS` and the prediction-preview panel with real evaluation output.
- Add the "Approve & Publish" step from the original concept (not yet represented as its own
  screen).

## Later / unscheduled

- Multi-user accounts and auth.
- Deployment/production monitoring screens (poster steps 9–11: assign to production, monitor &
  analyze, continuous improvement) — not part of the current four-screen scope.
- Dark mode.
