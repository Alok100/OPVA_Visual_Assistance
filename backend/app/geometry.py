"""Shared box geometry helpers used by detection dedup and the over-detection
guard (app/validation.py).
"""

from __future__ import annotations

from .models import BoundingBox


def iou(a: BoundingBox, b: BoundingBox) -> float:
    ax0, ay0, ax1, ay1 = a.x, a.y, a.x + a.width, a.y + a.height
    bx0, by0, bx1, by1 = b.x, b.y, b.x + b.width, b.y + b.height
    ix0, iy0 = max(ax0, bx0), max(ay0, by0)
    ix1, iy1 = min(ax1, bx1), min(ay1, by1)
    iw, ih = max(0.0, ix1 - ix0), max(0.0, iy1 - iy0)
    inter = iw * ih
    area_a = (ax1 - ax0) * (ay1 - ay0)
    area_b = (bx1 - bx0) * (by1 - by0)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def nms(
    boxes: list[BoundingBox], scores: list[float], iou_threshold: float
) -> list[int]:
    """Standard greedy NMS. Returns kept indices, highest score first."""
    order = sorted(range(len(boxes)), key=lambda i: scores[i], reverse=True)
    kept: list[int] = []
    for i in order:
        if all(iou(boxes[i], boxes[k]) < iou_threshold for k in kept):
            kept.append(i)
    return kept
