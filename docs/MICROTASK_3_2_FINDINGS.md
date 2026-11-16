# Microtask 3.2 — Annotation Editor Audit and Persistence

## Step 2 audit — what already worked, what was missing

The manual annotation editor (draw/move/resize/delete/relabel a box) from the previous session
was audited against the brief's checklist, by reading the code, not re-guessing:

| Capability | Status before this task |
|---|---|
| Add bounding box | Worked (draw tool) |
| Move bounding box | Worked (drag) |
| Resize bounding box | Worked (8 handles) |
| Delete bounding box | Worked (toolbar/row/Delete key) |
| Change annotation class | Worked (label input) |
| Review imported/AI-generated annotations | **Missing** — the side panel only *displayed* `status`, no control changed it |
| Approve human-verified annotations | **Missing** — same reason, confirmed by grep (nothing in the codebase ever set `human_verified`/`approved_for_training`) |

So "review" and "approve" didn't exist as actions anywhere, on top of the already-known gap that
none of the editing actions persisted past a page reload.

## What was built

### Stable box ids
`ImportedBox` (backend) and its TS mirror had no `id` — the frontend was synthesizing one
(`${image_id}-${i}`) that wasn't stable across reloads, so an edit couldn't be reliably
reattached to "the same box" after a refresh. Added `id: str` (uuid, `default_factory` so the
one real pre-existing dataset without this field still loads without error — see
`backend/app/models.py`).

### Two-record provenance model
- `annotations_imported.json` (existing) stays the immutable original-import record — untouched
  by any edit, review, or approval from this point forward.
- New `annotations_current.json` — the live/editable state, per image. Provenance (`edited`,
  `original_bbox`, `original_label`) is **not stored** — it's computed at read time by diffing
  the same box `id` against the immutable import record. Simpler than snapshotting, and it
  can't go stale because the source it diffs against never changes.
- Seeded automatically right after a successful import (`seed_current_from_import`, called from
  `main.py`'s import endpoint) — a **per-image merge**, so importing new annotations for some
  images never wipes out review/edit work already done on other images.

### Review/approve workflow
A forward-only state machine: `imported_not_reviewed`/`ai_generated_not_reviewed` →
`human_verified` → `approved_for_training`. The only way `status` changes is a dedicated
`PATCH .../boxes/{box_id}/status` call — the edit endpoint's payload type has no `status` field
at all, so a client can't smuggle an approval through an edit. Two extra safety rules, both
direct consequences of "unapproved annotations cannot silently enter the training dataset":
- Editing an already-approved box's geometry or label demotes it back to `human_verified` —
  otherwise a stale approval would stay attached to geometry nobody actually reviewed.
- A box flagged `valid: false` (failed coordinate validation) can't be marked reviewed or
  approved until its geometry is fixed.

New UI: the side panel's existing "Review status" section gained a per-row "Mark reviewed" /
"Approve for training" button (hidden once there's no next legal status), and rows for an edited
box show a small history icon with a tooltip stating what it was originally imported as.

### Persistence wiring
The Annotation screen now fetches `GET /inspections/{id}/annotations/current` instead of the
old import-only endpoint, and saves through `PUT .../current/{image_id}` (debounced ~500ms so a
single drag doesn't fire dozens of requests, flushed immediately before switching images or
leaving the screen so an edit can't be silently dropped) and
`PATCH .../current/{image_id}/boxes/{box_id}/status`. A `StatusBadge` next to the Edit/Done
toggle shows "Saving…" / "Saved" / "Save failed — edit kept locally."

**Demo-mode editing is deliberately unchanged** — there's no backend inspection for demo images
to persist against, so demo-box edits stay local-state-only exactly as before, with no "Saved"
badge (showing one would be exactly the fake-success CLAUDE.md forbids).

## Demonstrated edit → save → reload → reopen → approve workflow

Run against the real backend with a throwaway inspection (cleaned up afterward); commands and
responses abbreviated here — the full sequence is reproducible with the commands below.

1. **Upload + import**: uploaded a real image, imported a COCO box at `(100, 100, 200×150)`.
   `GET .../annotations/current` → box present, `origin: "imported"`, `status:
   "imported_not_reviewed"`, `edited: false`.
2. **Edit (move)**: `PUT .../current/{image_id}` with the same box id moved to `(150, 150)`.
   Response: `edited: true`, `original_bbox: {x:100, y:100, ...}` — the diff against the
   untouched import record, computed live.
3. **"Refresh"**: re-ran `GET .../annotations/current` — the moved box, still `edited: true`
   with the same `original_bbox`, came back unchanged. The edit survived.
4. **Review + approve**: `PATCH .../status` with `human_verified`, then `approved_for_training`
   — both succeeded (200). A direct attempt to skip straight from `imported_not_reviewed` to
   `approved_for_training` on a fresh box was rejected with **422** and a precise message naming
   the only legal next status.
5. **"Reopen"**: re-ran `GET .../annotations/current` again — `status: "approved_for_training"`
   persisted.
6. **Provenance integrity**: read both on-disk files directly —
   `annotations_imported.json` still shows the box at its original `(100, 100)`;
   `annotations_current.json` shows it at `(150, 150)`, `approved_for_training`. The import
   record was never touched by any of the above.
7. **Training-data guard**: `get_approved_boxes_for_training()` called directly — returned
   exactly the one approved box, confirming the mechanical filter works. (No real training/
   export step in this codebase calls it yet — see the Limitations section below.)

Reproduce steps 1–5 directly against the API:
```bash
curl -F "files=@image.jpg" http://localhost:8000/inspections/<id>/images
curl -F "files=@anno.json" http://localhost:8000/inspections/<id>/annotations/import
curl http://localhost:8000/inspections/<id>/annotations/current
curl -X PUT http://localhost:8000/inspections/<id>/annotations/current/<image_id> \
  -H "Content-Type: application/json" -d '[{"id":"<box_id>","bbox":{"x":150,"y":150,"width":200,"height":150},"label":"bolt"}]'
curl http://localhost:8000/inspections/<id>/annotations/current   # "refresh"
curl -X PATCH http://localhost:8000/inspections/<id>/annotations/current/<image_id>/boxes/<box_id>/status \
  -H "Content-Type: application/json" -d '{"status":"human_verified"}'
curl -X PATCH http://localhost:8000/inspections/<id>/annotations/current/<image_id>/boxes/<box_id>/status \
  -H "Content-Type: application/json" -d '{"status":"approved_for_training"}'
curl http://localhost:8000/inspections/<id>/annotations/current   # "reopen"
```

## Regression safety

- `cd backend && pytest` — **73 passed** (54 pre-existing + 19 new in
  `test_annotation_review.py` and `test_annotation_import.py`), no detection/inference logic
  touched.
- `npm run build && npm run lint` — clean.
- No frontend test runner exists in this repo (`package.json` has no Jest/Vitest/Playwright) —
  adding one now would itself be the "unnecessary infrastructure" the brief says to avoid, so
  frontend verification is build/lint plus the manual walkthrough above (same precedent as
  `docs/MICROTASK_3_1_FINDINGS.md`).

## Known limitations (flagged, not hidden)

- Move/resize stays pointer-only (no keyboard equivalent) — unchanged from the original editor,
  not newly introduced.
- `insp-tractor-wheel`'s real, pre-existing `annotations_imported.json` predates per-box ids;
  it now backfills a non-stable id on each parse rather than crashing, but full provenance
  tracking only works reliably for annotations imported after this change.
- Re-importing annotation JSON for an image that's already been reviewed/approved in
  current-state still discards that image's review state (same "latest import wins" behavior
  the import endpoint already had before this task — not newly introduced, not fixed here).
- "Unapproved cannot enter training" is enforced mechanically and has its own passing test, but
  there is still no real training/export consumer in this codebase to demonstrate it against —
  `/training` and `/analysis` remain 100% mock UI. Building that consumer is out of scope for
  this milestone.
- No concurrent-write locking on the new filesystem writes — consistent with the rest of
  `storage.py` (the image manifest isn't locked either), not a new gap introduced here.
