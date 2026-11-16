"""Per-bolt yellow witness-mark check via OpenCV HSV thresholding.

Deliberately simple and explainable (not a learned model): crop the bolt's
detected region with a small margin, mask yellow-range pixels, and call it
present/absent/uncertain by the fraction of yellow pixels in the crop. See
docs/MICROTASK_2_FINDINGS.md for the known false-positive risk (yellow cable
insulation near a bolt) and why REVIEW exists instead of a hard pass/fail.
"""

from __future__ import annotations

import cv2
import numpy as np

from .config import (
    MARK_PRESENT_MIN_FRACTION,
    REVIEW_MIN_FRACTION,
    YELLOW_HSV_LOWER,
    YELLOW_HSV_UPPER,
)
from .models import BoundingBox

CROP_MARGIN_FRACTION = 0.15  # grow the detected box a bit; marks often sit at its edge


def _crop_with_margin(img: np.ndarray, bbox: BoundingBox) -> np.ndarray:
    h, w = img.shape[:2]
    mx = bbox.width * CROP_MARGIN_FRACTION
    my = bbox.height * CROP_MARGIN_FRACTION
    x0 = max(0, int(bbox.x - mx))
    y0 = max(0, int(bbox.y - my))
    x1 = min(w, int(bbox.x + bbox.width + mx))
    y1 = min(h, int(bbox.y + bbox.height + my))
    return img[y0:y1, x0:x1]


def yellow_fraction(img_bgr: np.ndarray, bbox: BoundingBox) -> float:
    """Fraction (0-1) of yellow-range pixels within the bolt's crop region."""
    crop = _crop_with_margin(img_bgr, bbox)
    if crop.size == 0:
        return 0.0
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.array(YELLOW_HSV_LOWER), np.array(YELLOW_HSV_UPPER))
    return float(np.count_nonzero(mask)) / mask.size


def classify_marking(fraction: float) -> str:
    """Returns 'present', 'uncertain', or 'absent' from a yellow-pixel fraction."""
    if fraction >= MARK_PRESENT_MIN_FRACTION:
        return "present"
    if fraction >= REVIEW_MIN_FRACTION:
        return "uncertain"
    return "absent"
