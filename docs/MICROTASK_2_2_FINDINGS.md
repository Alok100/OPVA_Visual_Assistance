# Microtask 2.2 — Model Balancing and Evaluation

## Step 1 — Dataset audit

**Counts by scene type** (50 curated images total):

| | images | boxes (instances) | avg boxes/image | mean box area (% of frame) |
|---|---|---|---|---|
| clean (Hough-labeled) | 39 | ~76 across all splits | 1.9–2.2 | **8.7%** |
| busbar (human-verified) | 11 | 84 | 5.1–12.0 | **1.0–1.4%** |

Two findings dominate everything downstream:

**1. The "busbar" scene type is not 11 independent scenes — it's mostly one.**
Visual audit (chronology contact sheet, filenames by timestamp) found **8 of
the 11 busbar images are the same physical breaker unit** (identical "LINE
1/3/5/N" labels, identical cable-color pattern, identical bracket geometry,
same background) photographed repeatedly over a **24-second burst**
(2:56:24 PM–2:56:46 PM). Only 3 busbar images are genuinely distinct scenes:
one 2-bolt vertical bracket (`9d1cfa7d3656`) and two single-bolt DIN-rail
shots (`72dde4a33315`, `50c3534e8e3f`) — and the DIN-rail ones aren't even
"cluttered," they're simple single-bolt scenes that happened to fail the
Hough proposal step for unrelated reasons. **There is no genuinely
independent cluttered-busbar test image anywhere in this dataset.** This
is the single most important finding of this audit and caps what any
model-tuning effort here can honestly claim.

**2. The v2 (Microtask 2.1) train/val/test split had real leakage**, both
against itself and against v1:
- Of v2's 6 clean "test" images, **5 were in v1's training set**. The v1
  vs. v2 comparison in Microtask 2.1 was not apples-to-apples.
- v2's own stratification split the 8-image same-unit busbar group across
  train(4)/val(2)/test(2) — meaning the model saw the *exact same panel*
  (different crop/angle) in training that it was then "tested" on.
- Computing the actual images held out from **both** v1's and v2's
  training: only **5 images** (4 from the leaky same-unit group, 1 clean)
  — too thin to draw conclusions from directly, which is why this task
  builds a corrected split (below) instead.

**Other annotation-quality issue found**: the Hough-proposal "high
confidence" labels (39 clean images) were tagged by box *count* heuristics
(`finalize_labels.py`), never checked for box *tightness*. Example found:
image `2.56.12 PM.jpeg`'s ground truth includes boxes covering 69%×52% and
56%×42% of the frame — not tight bolt crops. This inflates apparent
false-positive rates for any model evaluated against these labels (a
correct, tightly-boxed detection can fail the IoU≥0.5 match against a
loose ground-truth box). Per the "no additional synthetic ground truth"
constraint, these labels were not re-annotated — this is reported as a
measurement caveat, not fixed.

**No near-duplicate images** found via perceptual hashing (average hash,
10×10, Hamming ≤12/100) across the final 50 — the same-unit-burst problem
is a *same-scene* issue (different crops/angles of one object), not
pixel-duplicate images, which is why hashing alone didn't catch it; it
took visual/chronological review.

## Fix: scene-group-aware split (`scripts/prepare_yolo_dataset_v3.py`)

The 8-image same-unit group can't be meaningfully split — there's nothing
independent to hold out, so splitting it only leaks. Fix: the whole group
goes to **train** (legitimate — more real examples of the one busbar
design this project actually has); the 3 distinct busbar images spread
1/1/1 across train/val/test. Clean images keep the same stratified split
as before (unchanged, for comparability). Result: train 36 (9 busbar / 27
clean), val 7 (1/6), test 7 (1/6). No new annotations created — reuses the
existing Hough and human-verified label files.

## Step 2 — Why v2 regressed on clean close-ups

Two real, evidenced factors, not one:

1. **Scale mismatch.** Clean-image boxes average **8.7%** of frame area;
   busbar boxes average **1.0–1.4%** — roughly a 6–9x scale gap. YOLOv8's
   default training augmentation includes **mosaic (prob=1.0)**, which
   tiles 4 training images into one canvas, each resized into a quadrant —
   forcing clean images' naturally large bolts down toward the busbar
   images' small scale for most of training (`close_mosaic=10` only turns
   it off for the last 10 epochs). v1 never had this problem (100% of its
   training data was clean, so mosaic combined clean-with-clean).
2. **Measurement artifact.** Microtask 2.1 compared v1's score on *its own*
   val set (which v2 had largely trained on) against v2's score on a
   separate test set v1 had already seen most of in training — not a fair
   comparison, independent of any real model difference.

## Step 3 — Controlled experiments (one variable at a time, fixed split)

All three trained identically otherwise (yolov8n, 100 epochs w/ patience
25, imgsz 640, MPS, seed 0) on the corrected split from Step 1.

| Run | Change vs. baseline | Result |
|---|---|---|
| **v3a** | fixed split only (mosaic on, unbalanced: 27 clean / 9 busbar images in train) | val: P=0.848, R=0.357, mAP50=0.464, mAP50-95=0.300 |
| **v3b** | fixed split **+ mosaic disabled** | **Rejected** — training became unstable (P/R oscillate wildly epoch to epoch, e.g. P: 0.86→1.0→0.07→0.45→0.29; "best" checkpoint picked at epoch 2 with P=0.006, R=0.857 — i.e. flooding every frame with boxes). With only 36 training images, mosaic is load-bearing for stable convergence, not just a scale-mismatch problem to remove. |
| **v3c** | fixed split **+ busbar images oversampled 3x** (27 clean vs. 27 busbar-weighted in train loss; mosaic stays on) | val: P=1.000, R=0.421, mAP50=0.509, mAP50-95=0.329 — **better than v3a on every metric**, single isolated variable (oversampling) |

v3b is the one experiment that failed outright — reported as a real,
informative negative result (the hypothesis "mosaic hurts clean accuracy"
is only half right: removing it outright is worse, not better, at this
data size).

## Step 4 — Evaluation: v1, v2, v3a, v3c on the identical corrected test set

7 held-out images (6 clean, 1 distinct-busbar — the DIN-rail single-bolt
shot, **not** a cluttered scene; see Step 1 caveat), matched to ground
truth at IoU≥0.5:

| Model | Clean P | Clean R | Clean F1 | Busbar (n=1, not cluttered) P/R |
|---|---|---|---|---|
| **v1** | 0.419 | **1.000** | **0.590** | 0.500 / 1.000 |
| v2 | 0.412 | 0.538 | 0.467 | 1.000 / 1.000 |
| v3a | 0.211 | 0.615 | 0.314 | 1.000 / 1.000 |
| **v3c** | **0.450** | 0.692 | 0.545 | 1.000 / 1.000 |

**v1 is still the best clean-image model by F1**, driven entirely by
perfect recall (it misses nothing, at the cost of more false positives
than v3c). **v3c is the best of the three new variants** and closes most
of the gap v2 opened — a real, single-variable-isolated improvement
(oversampling) over v3a — but does not surpass v1 overall.

**No busbar generalization conclusion can be drawn** from the one-image
"busbar" test column above — it's a simple scene, not the cluttered
breaker-panel design the project actually needs to detect reliably. The
only available signal for that design is in-training-distribution
behavior, checked via the full-50-image over-detection guard trip rate
(not held-out, a robustness/stability proxy only):

| Model | Guard trips (not_processed + review) / 50 | Total deduped detections |
|---|---|---|
| v1 (never trained on busbar) | 19 (38%) | 268 |
| v2 (leaky split) | **9 (18%)** | 222 |
| v3a (fixed split, unbalanced) | 28 (56%) | 280 |
| v3c (fixed split, balanced) | 18 (36%) | 252 |

Notably, **v2 — the methodologically flawed version — has the lowest
trip rate**, better than the "corrected" v3c. Plausible reason: v2's split
scattered the same-unit images across train/val/test, which (by accident)
gave the model slightly more *compositional* variety per training step
than v3's "whole group in train" arrangement, which concentrates repeated
views of the identical scene. This is reported as observed, not fully
explained — another sign the dataset is too small/narrow to support
confident causal claims about any of these variants.

### False-positive / false-negative example

`2.56.12 PM.jpeg` (test, clean, v3c): GT=5, pred=4, TP=1, FP=3, FN=4. One
of the 3 "false positives" is the Step 1 loose-ground-truth problem in
action — a model box on an actual bolt failed to hit IoU≥0.5 against an
oversized ground-truth box; the other false positives are the model
boxing cable conduit and an unrelated bracket feature. One ground-truth
bolt near the bottom of frame also wasn't matched at all (true miss).

## Step 5 — Recommendation

1. **One combined model is not yet reliably good at both scene types** —
   confirmed again, and more precisely now: v1 is best on clean (F1 0.59,
   but far from production-grade), and no model has been, or currently
   *can be*, validated on genuine cluttered-busbar generalization at all.
2. **Two specialized models with deterministic scene routing is not yet
   worth building.** A "busbar specialist" trained on this data would
   really be a "this one specific panel" specialist — there's only one
   real example of the cluttered scene type to learn from. Building and
   shipping a dedicated model now would create false confidence, not
   real capability.
3. **More real annotated images are necessary — this is the dominant
   conclusion, not a hedge.** Specifically: more *independent* cluttered/
   busbar scenes (different physical panels or assemblies, not more
   photos of the one panel already in the dataset), and ideally a second
   annotation pass on the existing 39 Hough-labeled clean images to fix
   the loose-box problem found in Step 1/4, since that's inflating every
   precision number reported for clean scenes across every model tested.

**`app/detection.py` is unchanged — still points at `bolt_detector_v1.pt`.**
None of v2, v3a, or v3c beat it cleanly enough (by F1, on a fair held-out
set) to justify switching, per the explicit instruction not to auto-replace
without results that justify it. `bolt_detector_v3c.pt` is saved
(`backend/models/`) as the strongest balanced-training candidate so far,
for future work once more busbar data exists.

**Evidence still missing before UI integration:**
- At least 3-5 more genuinely independent cluttered/busbar scenes (different
  physical equipment), annotated the same human-verified way as Step 2 of
  Microtask 2.1 — without this, busbar reliability literally cannot be
  measured, only guessed at.
- A tightness pass on the 39 Hough-labeled clean ground-truth boxes, or
  enough new clean annotations to stop relying on them, so clean-scene
  precision numbers reflect real model errors rather than partly reflecting
  label looseness.
- A model (v1, v3c, or a future version) that beats the current best F1
  (0.590) by a clear margin on a held-out set that doesn't share any
  physical scene with the training set — not yet achieved by anything
  trained in Microtask 2.1 or 2.2.
