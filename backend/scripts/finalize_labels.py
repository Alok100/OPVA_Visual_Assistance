"""Turn the raw Hough-circle candidates from propose_boxes.py into final
YOLO training labels: de-duplicate overlapping circles for the same bolt
(NMS), then tag each image's label confidence so the fine-tune can exclude
images where the rough pass clearly missed or misfired, instead of training
on wrong "no bolt here" signal.

Confidence tags (printed, and written to confidence.json for the training
script to read):
  high  — 1-6 boxes after NMS, i.e. plausible given 1-4 bolts per image
  low   — 0 boxes (rough pass missed every bolt) or >6 boxes (still noisy
          after NMS, usually a cluttered background) — excluded from
          training rather than taught as a (wrong) label.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cv2
import numpy as np

from app.config import EXPERIMENTS_ROOT
from app.storage import load_manifest

INSPECTION_ID = "insp-bolt-torque-poc"
RAW_LABELS_DIR = EXPERIMENTS_ROOT / INSPECTION_ID / "yolo_labels"
FINAL_LABELS_DIR = EXPERIMENTS_ROOT / INSPECTION_ID / "yolo_labels_final"
FINAL_REVIEW_DIR = EXPERIMENTS_ROOT / INSPECTION_ID / "box_proposals_final_review"

NMS_IOU_THRESHOLD = 0.35
MAX_PLAUSIBLE_BOXES = 6


def _yolo_line_to_xyxy(line: str, w: int, h: int) -> tuple[float, float, float, float]:
    _, ncx, ncy, nbw, nbh = (float(x) for x in line.split())
    cx, cy, bw, bh = ncx * w, ncy * h, nbw * w, nbh * h
    return cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2


def _iou(a, b) -> float:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    ix0, iy0 = max(ax0, bx0), max(ay0, by0)
    ix1, iy1 = min(ax1, bx1), min(ay1, by1)
    iw, ih = max(0, ix1 - ix0), max(0, iy1 - iy0)
    inter = iw * ih
    area_a = (ax1 - ax0) * (ay1 - ay0)
    area_b = (bx1 - bx0) * (by1 - by0)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def nms(boxes: list[tuple[float, float, float, float]]) -> list[tuple[float, float, float, float]]:
    # Larger boxes first (Hough gives no confidence score, so area is the tiebreaker).
    boxes = sorted(boxes, key=lambda b: (b[2] - b[0]) * (b[3] - b[1]), reverse=True)
    kept: list[tuple[float, float, float, float]] = []
    for b in boxes:
        if all(_iou(b, k) < NMS_IOU_THRESHOLD for k in kept):
            kept.append(b)
    return kept


def main() -> None:
    FINAL_LABELS_DIR.mkdir(parents=True, exist_ok=True)
    FINAL_REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest(INSPECTION_ID)

    confidence: dict[str, str] = {}
    for stored in manifest:
        img_path = EXPERIMENTS_ROOT / stored.stored_path
        img = cv2.imread(str(img_path))
        h, w = img.shape[:2]

        raw_path = RAW_LABELS_DIR / f"{stored.image_id}.txt"
        lines = [l for l in raw_path.read_text().splitlines() if l.strip()]
        boxes = [_yolo_line_to_xyxy(l, w, h) for l in lines]
        kept = nms(boxes)

        if len(kept) == 0 or len(kept) > MAX_PLAUSIBLE_BOXES:
            confidence[stored.image_id] = "low"
        else:
            confidence[stored.image_id] = "high"

        out_lines = []
        annotated = img.copy()
        for x0, y0, x1, y1 in kept:
            bw, bh = (x1 - x0) / w, (y1 - y0) / h
            ncx, ncy = (x0 + x1) / 2 / w, (y0 + y1) / 2 / h
            out_lines.append(f"0 {ncx:.6f} {ncy:.6f} {bw:.6f} {bh:.6f}")
            color = (0, 255, 0) if confidence[stored.image_id] == "high" else (0, 0, 255)
            cv2.rectangle(annotated, (int(x0), int(y0)), (int(x1), int(y1)), color, 4)

        (FINAL_LABELS_DIR / f"{stored.image_id}.txt").write_text("\n".join(out_lines))
        cv2.imwrite(str(FINAL_REVIEW_DIR / f"{stored.image_id}.jpg"), annotated)

    (EXPERIMENTS_ROOT / INSPECTION_ID / "confidence.json").write_text(json.dumps(confidence, indent=2))

    high = sum(1 for v in confidence.values() if v == "high")
    low = sum(1 for v in confidence.values() if v == "low")
    print(f"Images: {len(manifest)}  high-confidence: {high}  low-confidence (excluded): {low}")
    print(f"Final labels: {FINAL_LABELS_DIR}")
    print(f"Final review: {FINAL_REVIEW_DIR}")


if __name__ == "__main__":
    main()
