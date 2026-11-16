import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.geometry import iou, nms
from app.models import BoundingBox


def _box(x, y, w, h):
    return BoundingBox(x=x, y=y, width=w, height=h)


def test_iou_identical_boxes_is_one():
    b = _box(0, 0, 100, 100)
    assert iou(b, b) == 1.0


def test_iou_disjoint_boxes_is_zero():
    assert iou(_box(0, 0, 10, 10), _box(100, 100, 10, 10)) == 0.0


def test_nms_collapses_near_duplicate_to_higher_confidence():
    boxes = [_box(0, 0, 100, 100), _box(5, 5, 100, 100)]
    kept = nms(boxes, [0.9, 0.6], iou_threshold=0.5)
    assert kept == [0]


def test_nms_keeps_well_separated_boxes():
    boxes = [_box(0, 0, 100, 100), _box(500, 500, 100, 100)]
    kept = nms(boxes, [0.9, 0.8], iou_threshold=0.5)
    assert set(kept) == {0, 1}
