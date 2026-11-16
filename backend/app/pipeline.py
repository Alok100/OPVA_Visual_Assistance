"""Orchestrates detect -> per-bolt color check -> verdict -> image/inspection
summary. This is the real (non-demo) pipeline Step 6 wires the UI to.

Verdict semantics (per Microtask 2 spec, Step 7):
  PASS          detected bolt, yellow marking present, detection set trusted
  FAIL          detected bolt, marking confirmed absent, detection set trusted
  REVIEW        marking evidence insufficient/ambiguous, OR the image's
                detection set tripped the over-detection guard (see
                app/validation.py) and individual boxes aren't trusted
  NOT_PROCESSED image failed before per-bolt results could be produced, OR
                the detection set was too implausible to use at all

A processing failure never silently becomes PASS — see process_image's
except branch (technical failure) and the detection_quality guard below
(unreliable-but-technically-successful detection): neither path runs the
color check or assigns PASS/FAIL to individual boxes.
"""

from __future__ import annotations

import uuid
from pathlib import Path

import cv2

from .color_check import CROP_MARGIN_FRACTION, classify_marking, yellow_fraction
from .detection import detect_bolts
from .models import (
    BoltResult,
    BoltVerdict,
    ImageResult,
    InspectionSummary,
    ProcessingStatus,
)
from .validation import assess_detection_quality

_VERDICT_BY_MARKING = {
    "present": BoltVerdict.PASS,
    "uncertain": BoltVerdict.REVIEW,
    "absent": BoltVerdict.FAIL,
}

_GUARD_VERDICT = {
    "review": BoltVerdict.REVIEW,
    "not_processed": BoltVerdict.NOT_PROCESSED,
}


def process_image(image_id: str, filename: str, image_path: Path) -> ImageResult:
    try:
        img = cv2.imread(str(image_path))
        if img is None:
            raise ValueError(f"Could not decode image: {image_path}")

        detections = detect_bolts(image_path)
        h, w = img.shape[:2]
        quality = assess_detection_quality([bbox for bbox, _ in detections], w, h)

        bolts: list[BoltResult] = []
        if quality.is_suspicious:
            # Guard tripped: the detection set itself isn't trustworthy, so
            # we show the raw boxes for human review but never run the
            # color check or assign PASS/FAIL to them.
            guard_verdict = _GUARD_VERDICT[quality.severity]
            for bbox, confidence in detections:
                bolts.append(
                    BoltResult(
                        bolt_id=uuid.uuid4().hex[:8],
                        bbox=bbox,
                        detection_confidence=confidence,
                        marking_yellow_fraction=None,
                        verdict=guard_verdict,
                        evidence=quality.reason or "Detection set flagged by over-detection guard.",
                    )
                )
        else:
            for bbox, confidence in detections:
                fraction = yellow_fraction(img, bbox)
                marking = classify_marking(fraction)
                bolts.append(
                    BoltResult(
                        bolt_id=uuid.uuid4().hex[:8],
                        bbox=bbox,
                        detection_confidence=confidence,
                        marking_yellow_fraction=fraction,
                        verdict=_VERDICT_BY_MARKING[marking],
                        evidence=(
                            f"yellow pixel fraction {fraction:.3f} in detected region "
                            f"(+{CROP_MARGIN_FRACTION:.0%} margin) -> {marking}"
                        ),
                    )
                )

        return ImageResult(
            image_id=image_id,
            filename=filename,
            status=ProcessingStatus.PROCESSED,
            bolts=bolts,
            detection_quality=quality.severity,
            guard_reason=quality.reason,
        )
    except Exception as exc:
        return ImageResult(
            image_id=image_id,
            filename=filename,
            status=ProcessingStatus.FAILED,
            error=str(exc),
            bolts=[],
            detection_quality="not_processed",
            guard_reason=f"Processing failed: {exc}",
        )


def summarize(results: list[ImageResult]) -> InspectionSummary:
    processed = [r for r in results if r.status == ProcessingStatus.PROCESSED]
    failed = [r for r in results if r.status == ProcessingStatus.FAILED]
    all_bolts = [b for r in processed for b in r.bolts]

    pass_count = sum(1 for b in all_bolts if b.verdict == BoltVerdict.PASS)
    fail_count = sum(1 for b in all_bolts if b.verdict == BoltVerdict.FAIL)
    review_count = sum(1 for b in all_bolts if b.verdict == BoltVerdict.REVIEW)
    # Bolts the over-detection guard refused to trust, plus every failed
    # image counted as one not-processed unit (we don't know how many bolts
    # it contained).
    not_processed_count = sum(
        1 for b in all_bolts if b.verdict == BoltVerdict.NOT_PROCESSED
    ) + len(failed)

    if failed or review_count > 0 or not_processed_count > 0:
        overall = BoltVerdict.REVIEW
    elif fail_count > 0:
        overall = BoltVerdict.FAIL
    elif pass_count > 0:
        overall = BoltVerdict.PASS
    else:
        overall = BoltVerdict.NOT_PROCESSED

    return InspectionSummary(
        total_images=len(results),
        processed_images=len(processed),
        failed_images=len(failed),
        total_bolts_detected=len(all_bolts),
        pass_count=pass_count,
        fail_count=fail_count,
        review_count=review_count,
        not_processed_count=not_processed_count,
        overall_result=overall,
    )
