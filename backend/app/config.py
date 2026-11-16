"""Paths and tunable thresholds for the Microtask 2 bolt-inspection POC.

Nothing here is a trained parameter — these are deterministic, hand-set
defaults for the color-marking experiment in color_check.py. Keep them in one
place instead of scattering magic numbers through the pipeline.
"""

from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
DATA_ROOT = BACKEND_ROOT / "data"
EXPERIMENTS_ROOT = DATA_ROOT / "experiments"

ALLOWED_IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png"}
MAX_UPLOAD_BYTES = 15 * 1024 * 1024  # 15MB per image

# HSV yellow range for torque-seal witness-mark detection (OpenCV H: 0-179).
# Wide-ish band because marking paint, lighting, and camera white balance vary
# across the sample photos; see docs/MICROTASK_2_FINDINGS.md for the images
# this was tuned against and its known false-positive risk (yellow cable
# insulation in frame).
YELLOW_HSV_LOWER = (18, 80, 80)
YELLOW_HSV_UPPER = (35, 255, 255)

# Fraction of a bolt's crop region that must be yellow pixels to count as
# "marking present". Below REVIEW_MIN_FRACTION the evidence is treated as
# insufficient rather than a confident fail.
MARK_PRESENT_MIN_FRACTION = 0.03
REVIEW_MIN_FRACTION = 0.01

# Detector confidence below which a detection is excluded entirely.
DETECTION_CONFIDENCE_THRESHOLD = 0.15

# --- Over-detection guard (Microtask 2.1 Step 1) ---
# Thresholds below were derived empirically from the 50-image pipeline
# experiment (see docs/MICROTASK_2_FINDINGS.md "Step 1" analysis), not
# guessed: a clean post-dedup NMS pass leaves genuinely good images with
# box-area coverage <= ~0.48 of the frame and bad (busbar/cable overfire)
# images at >= ~0.69, a wide empirical gap. These are *geometric plausibility*
# thresholds (does the detection set look like discrete bolts in a photo at
# all), not a cap on how many bolts an image may contain.

# A second prediction for the same physical bolt looks like a separate box
# with high IoU against another — collapse these before any other check.
DEDUP_IOU_THRESHOLD = 0.5

# After dedup, if detected boxes collectively cover more than this fraction
# of the frame, the detection set is not physically consistent with a
# handful of discrete bolts (bolts are small hardware, not most of a photo).
# Sits in the empirical gap between ~0.48 (clean) and ~0.69 (bad).
SUSPICIOUS_COVERAGE_FRACTION = 0.55

# After dedup, any surviving box pair with IoU above this is still unusually
# overlapping for two physically distinct bolts in one photo — weaker
# evidence than coverage, used for REVIEW rather than NOT_PROCESSED.
SUSPICIOUS_OVERLAP_IOU = 0.15
