"""Regression tests for the Step 4 (Microtask 2.1) color-check stress test
findings: confirmed on real photos in docs/MICROTASK_2_FINDINGS.md, encoded
here as synthetic images so they don't depend on the external source photo
folder.
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.color_check import classify_marking, yellow_fraction
from app.models import BoundingBox


def _solid_bgr(color_bgr, size=(200, 200)):
    img = np.zeros((size[1], size[0], 3), dtype=np.uint8)
    img[:] = color_bgr
    return img


def test_solid_yellow_region_is_present():
    img = _solid_bgr((0, 220, 220))  # BGR yellow
    frac = yellow_fraction(img, BoundingBox(x=0, y=0, width=200, height=200))
    assert classify_marking(frac) == "present"


def test_bare_metal_gray_is_absent():
    img = _solid_bgr((160, 160, 160))  # neutral gray, low saturation
    frac = yellow_fraction(img, BoundingBox(x=0, y=0, width=200, height=200))
    assert classify_marking(frac) == "absent"


def test_bright_white_reflection_is_absent():
    # Known risk area explicitly checked: a bright specular highlight has
    # very low saturation, which the S>=80 HSV band filters out.
    img = _solid_bgr((255, 255, 255))
    frac = yellow_fraction(img, BoundingBox(x=0, y=0, width=200, height=200))
    assert classify_marking(frac) == "absent"


def test_blue_paint_is_absent_not_present():
    img = _solid_bgr((200, 80, 20))  # BGR blue-ish, outside the yellow hue band
    frac = yellow_fraction(img, BoundingBox(x=0, y=0, width=200, height=200))
    assert classify_marking(frac) == "absent"


def test_yellow_sliver_in_crop_is_confirmed_false_positive_risk():
    # Confirmed on a real photo (docs/MICROTASK_2_FINDINGS.md Step 4): a
    # small sliver of yellow cable insulation inside an otherwise-empty crop
    # is enough to register as "present" even with zero bolt present. This
    # is a known, accepted limitation, not something this test expects fixed.
    img = _solid_bgr((40, 40, 40))  # dark background
    img[0:40, 0:200] = (0, 220, 220)  # yellow sliver along one edge, ~20% of crop
    frac = yellow_fraction(img, BoundingBox(x=0, y=0, width=200, height=200))
    assert classify_marking(frac) == "present"


def test_oversized_box_dilutes_real_marking_to_review_not_absent():
    # Confirmed on a real photo: a loose/oversized detection box dilutes a
    # genuinely-present small marking's pixel fraction. The system should
    # fail safe to REVIEW (uncertain), not silently to "absent".
    img = _solid_bgr((60, 60, 60), size=(800, 800))
    img[0:100, 0:100] = (0, 220, 220)  # real small mark, tiny fraction of the oversized box
    frac = yellow_fraction(img, BoundingBox(x=0, y=0, width=800, height=800))
    assert classify_marking(frac) == "uncertain"
