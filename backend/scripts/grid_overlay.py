"""Draws a pixel-coordinate grid over an image so bounding boxes can be read
off visually and entered precisely — the "simple annotation workflow" for
manually correcting the 11 excluded busbar images (Microtask 2.1 Step 2).
No GUI/infrastructure: this is a plain script + hand-entered coordinates in
annotate_busbar_images.py, reviewed by eye against the grid.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cv2

from app.config import EXPERIMENTS_ROOT
from app.storage import load_manifest

INSPECTION_ID = "insp-bolt-torque-poc"
OUT_DIR = EXPERIMENTS_ROOT / INSPECTION_ID / "grid_overlays"
STEP = 100


def draw_grid(image_id: str) -> Path:
    manifest = {s.image_id: s for s in load_manifest(INSPECTION_ID)}
    stored = manifest[image_id]
    img = cv2.imread(str(EXPERIMENTS_ROOT / stored.stored_path))
    h, w = img.shape[:2]

    for x in range(0, w, STEP):
        cv2.line(img, (x, 0), (x, h), (255, 0, 255), 1)
        cv2.putText(img, str(x), (x + 2, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 1)
    for y in range(0, h, STEP):
        cv2.line(img, (0, y), (w, y), (255, 0, 255), 1)
        cv2.putText(img, str(y), (2, y + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 1)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"{image_id}.jpg"
    cv2.imwrite(str(out_path), img)
    return out_path


if __name__ == "__main__":
    for image_id in sys.argv[1:]:
        p = draw_grid(image_id)
        print(p)
