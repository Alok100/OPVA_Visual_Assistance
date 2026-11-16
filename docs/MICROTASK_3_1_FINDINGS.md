# Microtask 3.1 — Connect UI with Real Backend and Import Annotations

## Status: already implemented and in real use — this doc is a verification pass

This microtask's brief asked to inspect-before-implementing, connect the UI to the real FastAPI
backend for image + annotation-JSON upload, and visualize imported boxes on the Annotation
screen. On inspection, **this was already fully built** — `backend/app/annotation_import.py`'s
own header comment names "Microtask 3.1" — and, more tellingly, the example inspection
(`insp-tractor-wheel`) already had 35 real uploaded images and a real Supervisely-format
annotation import on disk from the user's own prior hands-on testing
(`backend/data/experiments/insp-tractor-wheel/`), not anything created for this pass. So this
session's work was: inspect, verify, fix one real gap found, document.

## What was verified

- **Backend test suite**: `cd backend && pytest` — 54/54 passed, no changes needed.
- **Live API smoke test** (throwaway `smoketest31` inspection, cleaned up after):
  - Image upload → correct `image_id`, `width`/`height` extracted (1536×1024 from a real PNG).
  - COCO-format annotation import with one in-bounds box, one deliberately out-of-bounds box,
    and a reference to a nonexistent image → the valid box imported `valid: true`, the
    out-of-bounds box flagged `valid: false` with a precise reason string, the missing-image
    reference correctly surfaced in `unmatched_filenames`. Status on both was
    `imported_not_reviewed` — nothing auto-approved.
  - Malformed JSON → rejected with HTTP 422 and a clear message, and did **not** clobber the
    previously-saved good import (confirmed via a follow-up `GET .../annotations`).
- **Frontend build/lint**: `npm run build` and `npm run lint` both clean.
- **Frontend rendering code read in full** (`src/app/(workflow)/annotation/page.tsx`,
  `annotation-canvas.tsx`, `annotation-side-panel.tsx`, `view-model.ts`) against the real API
  response shapes above — confirmed it consumes `matched_images`, `valid`/`issue`, and
  `AnnotationStatus` correctly. **Not independently verified by driving an actual browser** — no
  browser-automation tool was available in this environment, and the Annotation page fetches
  data client-side (`useEffect`), so a plain HTTP fetch of the page only shows the pre-fetch
  "Loading images…" shell, not the hydrated result. The user's own existing real data for
  `insp-tractor-wheel` (above) is the strongest evidence this has actually worked end-to-end in
  a real browser, since that data could only exist if the upload → import → display flow
  already succeeded for them.

## One real gap found and fixed

`src/lib/types.ts`'s `AnnotationFormat` union was `"coco" | "labelme" | "custom"` — missing
`"supervisely"`, even though `backend/app/models.py`'s `AnnotationFormat` enum has had it for a
while and the user's own real example-inspection data is tagged `detected_formats: ["supervisely"]`.
Not a live bug today (the type is only ever used as a plain annotation, never as an exhaustive
switch/lookup key — confirmed by grep), but a real type/doc drift against the backend it's
meant to mirror. Fixed by adding `"supervisely"` to the union.

## Actual workflow (as implemented)

1. **User Input screen** (`/`): drag-and-drop or browse to upload one or more images
   (`ImageDropzone`) — each gets a live preview and an uploading/uploaded/error badge. Non-image
   files are rejected client-side with a named error; the backend separately validates
   content-type and size (15MB/file) and rejects corrupt image data.
2. Once at least one image has uploaded successfully, the **"Import annotation JSON"** card
   (`AnnotationJsonUpload`) becomes active. Pick one or more `.json` files — multiple files in
   one go are supported because LabelMe/Supervisely's own convention is one JSON per image,
   unlike COCO/custom which can cover a whole batch in one file.
3. The backend sniffs each file's top-level shape, parses it, matches every box to an already-
   uploaded image **by filename**, validates each box's coordinates against that image's real
   pixel dimensions, and returns a result the UI summarizes inline: formats detected, images
   matched, total/invalid box counts, any unmatched filenames, any files that failed to parse.
4. Continuing to the **AI-Assisted Annotation screen** (`/annotation`) fetches the same images
   and the saved import result from the backend and renders real boxes over the real image —
   percent-of-image positioning converted from the image's real pixel dimensions, so it stays
   correctly placed regardless of the rendered image size. Invalid boxes get a dashed red
   border and a tooltip with the specific issue; everything is labeled with its import status
   (`Imported · not reviewed`, etc.) — never silently treated as approved ground truth.
5. If no images/annotations exist yet for the inspection (or the backend is unreachable), the
   screen falls back to the existing fixed demo set, clearly labeled as such.

## Supported annotation JSON formats

Auto-detected by top-level shape — `backend/app/annotation_import.py` is the source of truth:

| Format | Detected by | Notes |
|---|---|---|
| **COCO** | `{"images":[...], "annotations":[...]}` | One file can cover many images; `bbox` is `[x,y,w,h]` pixel-absolute. |
| **LabelMe** | `{"shapes":[...]}` | One file per image (uses `imagePath`'s basename to match). Non-rectangle shapes are approximated by their bounding rectangle and the label is suffixed to say so. |
| **Supervisely / DatasetNinja** | `{"size":{...}, "objects":[...]}` | One file per image; the image filename comes from the *upload's own filename* with a trailing `.json` stripped (e.g. `AUT-0001.jpg.json` → `AUT-0001.jpg`), not from inside the JSON. Non-rectangle geometry is bounding-rect'd like LabelMe. |
| **Custom** | any other dict/list | Documented, pixel-absolute-required shape: `{"<filename>": [{"x","y","width","height","label"}, ...]}` or a list of `{"filename","boxes"}`. Chosen deliberately over guessing whether small numbers mean normalized 0–1 coordinates. |

**Not supported**: YOLO's `.txt`-per-image label format — it isn't JSON, so it's out of scope
for this importer by design (confirmed no YOLO JSON convention exists anywhere in this project).

## Known limitations (not fixed in this pass — flagging, not hiding)

- **One current import per inspection**: a new import *replaces* the previously saved parsed
  result (`save_parsed_annotations` overwrites). Every original uploaded file is still preserved
  on disk under `imported_annotations/` regardless, but the UI only ever shows the latest merged
  result.
- **Real detection pipeline is not wired into this screen.** `backend/app/pipeline.py` (detect →
  color-check → verdict) exists and is real, but per `docs/MICROTASK_2_FINDINGS.md`/
  `MICROTASK_2_2_FINDINGS.md` it's not reliable enough across scene types to show as "AI-
  generated" boxes on the main Annotation screen yet — it's only reachable from the separate,
  explicitly-labeled `/inference` testing screen, triggered by a manual button, never
  automatically.
- **Box validation tolerance**: a box is flagged invalid if it extends more than 5% past the
  image's real pixel bounds — a deliberate tolerance for minor annotation-tool rounding, not a
  strict check.
- **No pinch-zoom/pan on the canvas** — "responsive to resize" here means the percent-based box
  overlay stays correctly positioned as the container resizes (e.g. narrow vs. wide viewport),
  not a dedicated zoom control.
- **Frontend `AnnotationFormat` → display string is just `.toUpperCase()`** — fine for all four
  current formats, would need a real label map if a format with a multi-word canonical display
  name were added later.

## How to test

**Automated:**
```bash
cd backend && source .venv/bin/activate && pytest           # 54 tests
npm run build && npm run lint                                 # from repo root
```

**Manual, backend-only (no browser needed), mirrors what this pass ran:**
```bash
curl -F "files=@path/to/image.jpg" http://localhost:8000/inspections/<id>/images
curl -F "files=@path/to/annotations.json" http://localhost:8000/inspections/<id>/annotations/import
curl http://localhost:8000/inspections/<id>/annotations
```

**Manual, full UI** (`npm run dev` on :3000, backend on :8000): go to `/`, upload a few real
images, upload a matching annotation JSON (any of the four formats above), confirm the inline
import summary looks right, then go to `/annotation` and confirm the real image(s) and boxes
render with the correct status/invalid flagging. This was not independently re-driven through an
actual browser in this pass (no browser-automation tool available) — the existing real data for
`insp-tractor-wheel` is the evidence this already works, but a fresh manual click-through is the
one thing still worth doing by hand.
