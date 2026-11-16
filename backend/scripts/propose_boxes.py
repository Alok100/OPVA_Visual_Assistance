"""Candidate bolt bounding-box proposals via classical CV (Hough circles),
used as a rough first annotation pass for the YOLO fine-tune.

This is NOT the product's bolt-detection pipeline (that's the fine-tuned
model in Step 4b) — it's a one-off labeling aid: propose circular,
metallic-looking regions, a human (or this session, visually) spot-checks a
sample, then all 50 get exported as YOLO-format labels for training.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cv2
import numpy as np

from app.config import EXPERIMENTS_ROOT
from app.storage import load_manifest

INSPECTION_ID = "insp-bolt-torque-poc"
REVIEW_DIR = EXPERIMENTS_ROOT / INSPECTION_ID / "box_proposals_review"
LABELS_DIR = EXPERIMENTS_ROOT / INSPECTION_ID / "yolo_labels"


def propose_circles(img_bgr: np.ndarray) -> list[tuple[int, int, int]]:
    """Returns (cx, cy, r) candidates via Hough circle transform."""
    h, w = img_bgr.shape[:2]
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.medianBlur(gray, 7)
    min_dim = min(h, w)
    circles = cv2.HoughCircles(
        gray,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=min_dim // 4,
        param1=100,
        param2=55,
        minRadius=int(min_dim * 0.08),
        maxRadius=int(min_dim * 0.35),
    )
    if circles is None:
        return []
    return [(int(x), int(y), int(r)) for x, y, r in circles[0]]


def main() -> None:
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    LABELS_DIR.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest(INSPECTION_ID)

    summary = []
    for stored in manifest:
        path = EXPERIMENTS_ROOT / stored.stored_path
        img = cv2.imread(str(path))
        h, w = img.shape[:2]
        circles = propose_circles(img)

        annotated = img.copy()
        label_lines = []
        for cx, cy, r in circles:
            x0, y0 = max(0, cx - r), max(0, cy - r)
            x1, y1 = min(w, cx + r), min(h, cy + r)
            cv2.rectangle(annotated, (x0, y0), (x1, y1), (0, 0, 255), 4)
            # YOLO format: class cx cy width height, all normalized 0-1
            bw, bh = (x1 - x0) / w, (y1 - y0) / h
            ncx, ncy = (x0 + x1) / 2 / w, (y0 + y1) / 2 / h
            label_lines.append(f"0 {ncx:.6f} {ncy:.6f} {bw:.6f} {bh:.6f}")

        cv2.imwrite(str(REVIEW_DIR / f"{stored.image_id}.jpg"), annotated)
        (LABELS_DIR / f"{stored.image_id}.txt").write_text("\n".join(label_lines))
        summary.append((stored.filename, stored.image_id, len(circles)))

    counts = [c for _, _, c in summary]
    print(f"Images: {len(summary)}")
    print(f"Zero-candidate images: {sum(1 for c in counts if c == 0)}")
    print(f"One-candidate images: {sum(1 for c in counts if c == 1)}")
    print(f"Multi-candidate images: {sum(1 for c in counts if c > 1)}")
    print(f"\nReview images: {REVIEW_DIR}")
    print(f"YOLO labels:   {LABELS_DIR}")
    for filename, image_id, n in summary:
        print(f"  {n:2d}  {image_id}  {filename}")


if __name__ == "__main__":
    main()
