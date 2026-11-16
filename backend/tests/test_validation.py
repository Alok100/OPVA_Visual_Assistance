import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models import BoundingBox
from app.validation import assess_detection_quality


def _box(x, y, w, h):
    return BoundingBox(x=x, y=y, width=w, height=h)


def test_empty_detections_is_ok():
    q = assess_detection_quality([], 1000, 1000)
    assert q.severity == "ok"
    assert not q.is_suspicious


def test_single_small_box_is_ok():
    q = assess_detection_quality([_box(100, 100, 100, 100)], 1000, 1000)
    assert q.severity == "ok"
    assert q.coverage_fraction == 0.01


def test_few_well_separated_boxes_is_ok():
    boxes = [_box(0, 0, 100, 100), _box(500, 500, 100, 100), _box(800, 100, 100, 100)]
    q = assess_detection_quality(boxes, 1000, 1000)
    assert q.severity == "ok"


def test_high_coverage_is_not_processed():
    # Four boxes each covering 25% of the frame, non-overlapping -> 100% coverage.
    boxes = [
        _box(0, 0, 500, 500),
        _box(500, 0, 500, 500),
        _box(0, 500, 500, 500),
        _box(500, 500, 500, 500),
    ]
    q = assess_detection_quality(boxes, 1000, 1000)
    assert q.severity == "not_processed"
    assert q.is_suspicious
    assert "cover" in q.reason.lower()


def test_overlapping_pair_below_coverage_threshold_is_review():
    # Two overlapping small boxes (IoU ~0.32), low total coverage.
    boxes = [_box(100, 100, 100, 100), _box(130, 130, 100, 100)]
    q = assess_detection_quality(boxes, 1000, 1000)
    assert q.severity == "review"
    assert q.overlapping_pair_count == 1


def test_coverage_takes_priority_over_overlap_reason():
    boxes = [
        _box(0, 0, 600, 600),
        _box(400, 400, 600, 600),
    ]
    q = assess_detection_quality(boxes, 1000, 1000)
    assert q.severity == "not_processed"
