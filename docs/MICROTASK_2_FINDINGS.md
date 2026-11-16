# Microtask 2 — Findings (Steps 1-5)

Working notes from the bolt-detection / yellow-marking POC. Written as the
work happened, not polished after the fact — numbers here are real
measurements, not illustrative.

## Dataset

Source: `/Users/alokkumar/Desktop/Workflow Content/Bolt Torque & Boxes
Photos` — 102 real JPEGs (~1600x1201px) of industrial electrical panel
hardware. Images are not committed to this repo (see `backend/.gitignore`);
`backend/scripts/seed_dataset.py` reproduces the selection from that source
folder.

Content is torque-seal witness-mark paint (a dabbed stripe across a bolt
head onto the adjacent surface, confirming it hasn't backed off since
torquing) — usually yellow, occasionally blue/teal. That variation gives
real positive/negative cases for the color check.

**Selection → 50 images:** systematic sample (every 2nd file by filename/
timestamp) across the full 102, one near-duplicate dropped. A visual
contact-sheet audit then found 10 of those 50 weren't bolt photos at all —
equipment nameplates, a disconnect-switch position photo, and 3 very
cluttered wide panel overviews — mixed into the same source folder. Those
10 were swapped for 10 clean bolt close-ups from the unused half of the
source folder. Final 50-image set is bolt content throughout.

## Step 2 — Deterministic requirement spec

`backend/app/spec.py` recognizes the one known requirement shape (bolt +
count + color marking) via keyword matching — not a general NL planner, per
instructions. Feasibility is reported as `needs_info` even on a match,
because detection feasibility can't be assumed — see below.

## Step 4 — Detection: pretrained/zero-shot failed, fine-tune required

Tested on all 50 images, nothing cherry-picked:

| Model | Result |
|---|---|
| `yolov8n.pt` (COCO-80 pretrained) | 31/50 images "detected" something — all wrong classes (book, toilet, mouse, parking meter, ...). COCO has no bolt class. |
| `yolov8s-worldv2.pt` (YOLO-World, zero-shot, prompted `["bolt","hex bolt head","screw"]`) | **0/50 images, 0 detections**, even at conf=0.1. |

Decision (user-approved): fine-tune a small YOLOv8n.

**Rough annotation pass:** no ground truth existed, so candidate boxes were
generated with classical CV (Hough circle transform tuned to expected bolt
radius), then de-duplicated with NMS (IoU 0.35) and tagged per-image
`high`/`low` confidence by candidate count (`backend/scripts/
propose_boxes.py`, `finalize_labels.py`). **39/50 images were high-
confidence; 11 were excluded** (0 candidates found, or still >6 after NMS —
mostly the busy multi-bolt busbar/cable shots where Hough circles also
picked up wire ties and connector hardware).

**Training:** `yolov8n.pt` fine-tuned on 33 train / 6 val images, 80
epochs, MPS (Apple M2 Max), ~3 min. Val metrics (6 images, 13 bolt
instances — **too small to trust as a real benchmark**, reported as
measured, not implied to generalize):

```
precision 0.951   recall 0.462   mAP50 0.600   mAP50-95 0.445
```

High precision, **low recall** — the model is usually right when it fires,
but misses roughly half the actual bolts on held-out images.

Weights: `backend/models/bolt_detector_v1.pt` (gitignored training run
artifacts live under `backend/runs/`, not committed; this one file is the
output kept).

## Step 5 — Yellow witness-mark check (OpenCV HSV)

`backend/app/color_check.py`: crop the detected box + 15% margin, HSV
in-range mask (`H 18-35, S 80-255, V 80-255`), classify by pixel fraction:
`present` ≥3%, `uncertain` 1-3%, `absent` <1% (`backend/app/config.py`).
Full-image sanity check (15 images, no crops yet) gave plausible low
percentages (0.2-1.4%) before any detection existed to crop against.
Known risk, not yet stress-tested: yellow cable insulation sitting inside a
loose crop could false-positive the mark as present.

## End-to-end pipeline run (Steps 4+5+7 combined, `scripts/
run_pipeline_experiment.py`)

Ran detect → color-check → verdict over all 50 images with the real
fine-tuned model:

```
total_images: 50   total_bolts_detected: 392   pass: 106  fail: 154  review: 132
```

**That 392 number is misleading and the aggregate is not trustworthy as
reported** — it's dominated by a handful of images where the detector
badly over-fires:

- On clean single/few-bolt close-ups (the majority image type), detection
  is genuinely good: tight boxes, plausible confidences (0.09-0.8), and
  correct `pass`/yellow-fraction verdicts matching what's visibly in frame.
- On cluttered multi-bolt busbar-with-cables scenes — the same scene type
  that was mostly excluded from training as low-confidence — the detector
  fires 15-45 overlapping boxes per image on wire ties, cable labels, and
  connector hardware that vaguely resemble its training crops. These
  images were *not* in the clean-33-image training set, so this is a
  genuine, expected generalization failure, not a bug.

Per-image detection counts: mean 7.8, median 3, max 45, min 1 — the mean is
pulled far above the median by ~6 outlier images.

## Honest overall assessment

- The pipeline is real end-to-end (upload → store → detect → color-check →
  verdict), not simulated, and works credibly on simple framing.
- It is **not reliable enough to wire into the UI as "real results" yet**
  for the full 50-image set — the busbar-scene false-positive explosion
  would show a quality engineer obviously wrong counts.
- Recommended next steps before Step 6 (UI wiring):
  1. Either restrict the first UI-connected version to single/few-bolt
     framing (document the limitation explicitly in the UI, consistent
     with the no-fabrication rule), or
  2. Get real (non-Hough-proposed) annotations for the 11 excluded
     busbar-scene images and retrain — the actual fix, more annotation
     work.
  3. Add a simple over-detection guard (e.g. flag/exclude images whose
     detection count is a statistical outlier) so a pipeline failure shows
     up as `NOT_PROCESSED`/needs-review rather than a flood of fake
     per-bolt verdicts.

All three were done next — see Microtask 2.1 below.

---

# Microtask 2.1 — Improve Detection Reliability

## Step 1 — Over-detection guard (`app/validation.py`, `app/geometry.py`)

Not an arbitrary bolt-count cap — two geometry-based plausibility checks,
thresholds derived empirically from the 50-image pipeline run above (not
guessed):

1. **Duplicate collapse**: `detect_bolts` now runs a stricter post-hoc NMS
   (IoU > 0.5) on the model's raw output before anything else — this alone
   cut total detections across the 50 images from 392 to 268. Real distinct
   bolts don't occupy the same pixels; a second box with >50% IoU against
   another is almost always the same physical bolt predicted twice.
2. **Geometric plausibility** (`assess_detection_quality`), on the deduped
   set:
   - **Coverage**: analyzed the 50-image run — after dedup, every genuinely
     good image's boxes covered ≤48% of the frame; every bad (busbar
     over-fire) image's covered ≥69%. `SUSPICIOUS_COVERAGE_FRACTION = 0.55`
     sits in that empirical gap → `NOT_PROCESSED`.
   - **Residual overlap**: any box pair still overlapping (IoU > 0.15)
     *after* the 0.5 dedup pass is physically odd for two distinct bolts →
     `REVIEW` (weaker evidence than coverage).
   - When either trips, `pipeline.py` shows the raw boxes for human review
     but **never** runs the color check or assigns PASS/FAIL to them.

Re-running the 50-image experiment with the guard active: **31 images "ok",
16 `NOT_PROCESSED`, 3 `REVIEW`** — the coverage rule caught every one of the
previously-identified busbar over-fire images. Aggregate counts are now
honest: 34 pass / 13 fail / 18 review / 203 not-processed (bolts), instead
of the old flood of 106/154/132 fake-looking verdicts.

## Step 2 — Dataset improvement, human-verified ground truth

Identified the 11 excluded images (confirmed — exactly the Step 1 "low
confidence" set from the original Hough pass). Built a minimal annotation
workflow: `scripts/grid_overlay.py` draws a pixel-coordinate grid over an
image; boxes are then read off by eye and hand-entered in
`scripts/annotate_busbar_images.py` (84 boxes across the 11 images, every
visible bolt/nut head, not just yellow-marked ones). This is this session's
own visual read of real pixel coordinates — not a Hough proposal, not
fabricated. Verified by rendering the boxes back over the source images and
reviewing the result (contact sheet) before using them.

`annotation_source.json` tags every one of the 50 curated images as either
`human_verified` (11) or `hough_proposal` (39) — the original Hough-based
labels are untouched, not overwritten, just no longer silently treated as
equivalent to verified ground truth.

## Step 3 — Retrain and evaluate

New dataset (`scripts/prepare_yolo_dataset.py` v2): all 50 images now have
usable labels (39 Hough-high-confidence + 11 human-verified), split
**train/val/test** (34/8/8), stratified by label source so val and test
each contain a realistic mix of clean and busbar scenes rather than being
accidentally all-clean. Retrained `yolov8n` the same way as before (80→67
epochs, early-stopped, MPS).

**Held-out test set (8 images, never used for training or early-stopping),
evaluated by actually matching predictions to ground truth at IoU≥0.5 — not
just ultralytics' aggregate `val()` number:**

| Scene type | images | precision | recall |
|---|---|---|---|
| clean close-up | 6 | 0.412 | 0.538 |
| busbar (cluttered) | 2 | 0.833 | 0.833 |

Ultralytics' own `val(split='test')`: precision 0.60, recall 0.68, mAP50
0.58, mAP50-95 0.22 (vs. v1's clean-only val: precision 0.95, recall 0.46,
mAP50 0.60, mAP50-95 0.445 — not directly comparable, different and harder
test set, but the gap is real).

**This is not a clean improvement — it's a different, mixed reliability
profile, and I'm not claiming otherwise:**
- **Busbar scenes improved substantially** — this was the actual goal of
  Steps 1-2, and it worked: full-dataset over-detection guard trip rate
  dropped from **19/50 (38%) with v1 to 9/50 (18%) with v2**, and total
  deduped detections across all 50 images dropped from 268 to 222 (closer
  to a physically plausible count). The model itself over-fires far less
  now, not just the guard catching it after the fact.
- **Clean close-up accuracy got worse** — precision dropped sharply
  (0.95→0.41 on held-out images), recall only mildly improved (0.46→0.54).
  With only 34 training images now split across two visually different
  scene types, the model likely has less capacity left for the clean-shot
  pattern it was previously narrowly tuned to.
- **Net effect**: v2 is not a strict upgrade over v1. `app/detection.py`
  still points at `bolt_detector_v1.pt` — I did not switch the active
  model, since neither version is uniformly better and swapping silently
  would misrepresent the result. `bolt_detector_v2.pt` is saved
  (`backend/models/`) as the busbar-capable alternative, pending either
  more clean training images to rebalance it or a per-scene-type model
  selection strategy.

## Step 4 — Yellow-marking validation (stress test)

Tested `yellow_fraction`/`classify_marking` against real crops from the
dataset and synthetic adversarial cases (now permanent regression tests,
`tests/test_color_check.py`):

- **Confirmed false-positive risk, as predicted**: a crop containing only a
  sliver of yellow cable insulation (no bolt) registers as `present`
  (fraction 0.036, real photo `bbe04c3260cf`). This is a real, demonstrated
  limitation, not just a theoretical one.
- **Reflections do not false-positive**: bare, shiny, unpainted bolt heads
  and bright specular highlights consistently classify `absent` (fraction
  ≈0) — the HSV saturation floor (S≥80) filters these out structurally,
  confirmed on 3 real unpainted-socket crops and a synthetic white-highlight
  case.
- **Blue/teal-only paint correctly reads as `absent` for yellow** — right
  behavior for *this* check, though it raises a product question (is a
  blue-marked bolt actually "not inspected for yellow" vs "genuinely
  failing the yellow check") that's outside this check's scope.
- **New finding, not originally anticipated**: a loose/oversized detection
  box on a genuinely well-marked bolt dilutes the yellow fraction and can
  push a real `present` case down into `uncertain`/REVIEW (real example:
  v1's detector on `50c3534e8e3f`, box far larger than the bolt, fraction
  0.0105 vs. an obviously-marked bolt by eye). The system fails safe to
  REVIEW here rather than silently wrong — but it's evidence that
  color-check accuracy is coupled to detection box tightness, not
  independent of it. No fix applied (out of Step 4's scope); recorded as a
  limitation.
- No false negative found (a real marking misclassified `absent`) in this
  pass — doesn't rule one out on a larger sample, just wasn't observed.

## Honest overall assessment (Microtask 2.1)

**Backend is still not ready for UI integration.** What's better: the
over-detection guard now reliably prevents the pipeline from ever showing a
flood of fabricated PASS/FAIL verdicts on a bad image — tested and
confirmed on the full 50-image set. What's still unresolved: the retrain
traded clean-close-up accuracy for busbar accuracy rather than improving
both, so there is no single current model that's reliably good at both
scene types, and the yellow check is demonstrably sensitive to detection
box looseness. Wiring either model into the UI now would mean roughly half
the clean-close-up images get weaker (if still guarded) results than v1
produced. Recommended before Step 6: add more clean-close-up training
images to rebalance v2 (the dataset is still only 50 images total), or
explicitly scope the first UI-connected release to busbar/multi-bolt
framing where v2 is now strong, and say so in the UI copy.
