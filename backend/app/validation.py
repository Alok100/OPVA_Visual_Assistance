"""Over-detection guard (Microtask 2.1 Step 1).

Deterministic, geometry-based plausibility check on a detection set — not a
cap on bolt count. Bolts are small, discrete, non-overlapping hardware; the
checks below ask "does this set of boxes look physically consistent with
that," not "are there too many."

Derived empirically from the 50-image pipeline experiment (see
docs/MICROTASK_2_FINDINGS.md): after detect_bolts' own duplicate-collapse,
genuinely good images (clean bolt close-ups) covered at most ~48% of the
frame with their boxes; bad images (detector over-firing on wires/
connectors in cluttered busbar photos) covered 69%+ and still had many
overlapping box pairs. SUSPICIOUS_COVERAGE_FRACTION sits in that gap.
"""

from __future__ import annotations

from dataclasses import dataclass

from .config import SUSPICIOUS_COVERAGE_FRACTION, SUSPICIOUS_OVERLAP_IOU
from .geometry import iou
from .models import BoundingBox


@dataclass
class DetectionQuality:
    is_suspicious: bool
    severity: str  # "ok" | "review" | "not_processed"
    reason: str | None
    coverage_fraction: float
    overlapping_pair_count: int


def assess_detection_quality(
    boxes: list[BoundingBox], image_width: int, image_height: int
) -> DetectionQuality:
    image_area = image_width * image_height
    if image_area <= 0 or not boxes:
        return DetectionQuality(False, "ok", None, 0.0, 0)

    coverage = sum(b.width * b.height for b in boxes) / image_area
    overlap_pairs = sum(
        1
        for i in range(len(boxes))
        for j in range(i + 1, len(boxes))
        if iou(boxes[i], boxes[j]) > SUSPICIOUS_OVERLAP_IOU
    )

    if coverage > SUSPICIOUS_COVERAGE_FRACTION:
        return DetectionQuality(
            True,
            "not_processed",
            (
                f"Detected boxes cover {coverage:.0%} of the image after "
                "duplicate removal — not physically consistent with a "
                "handful of discrete bolts. Likely detector over-firing on "
                "wires/connectors/background clutter."
            ),
            coverage,
            overlap_pairs,
        )

    if overlap_pairs > 0:
        return DetectionQuality(
            True,
            "review",
            (
                f"{overlap_pairs} pair(s) of detected boxes still overlap "
                "after duplicate removal — unusual for physically distinct "
                "bolts in one photo. Treating as uncertain rather than "
                "trusting individual pass/fail verdicts."
            ),
            coverage,
            overlap_pairs,
        )

    return DetectionQuality(False, "ok", None, coverage, overlap_pairs)
