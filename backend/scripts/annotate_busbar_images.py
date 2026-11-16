"""Human-verified ground truth for the 11 images excluded from Microtask 2's
first training pass (Hough proposals found 0, or too many, candidates on
these busbar/cable-dense scenes — see docs/MICROTASK_2_FINDINGS.md).

Boxes below were read directly off a pixel-coordinate grid overlay
(scripts/grid_overlay.py) by visual inspection — every bolt/nut head
visible in each image, not just yellow-marked ones, matching "detect every
bolt." This is NOT a Hough/model proposal: it's this session's own visual
read of the grid, i.e. the "simple annotation workflow" for Step 2.
Coordinates are a careful visual estimate (±~10-20px), not sub-pixel
ground truth, and that's noted in annotation_source.json's `method` field.

Writes YOLO-format labels to yolo_labels_human/ (pixel coords here, XYXY, in
GRID-IMAGE coordinates which match the original image 1:1 since grid_overlay
draws on top without resizing) and updates annotation_source.json to mark
these 11 images "human_verified" distinctly from the "hough_proposal" source
of the other 39.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import EXPERIMENTS_ROOT
from app.storage import load_manifest

INSPECTION_ID = "insp-bolt-torque-poc"
HUMAN_LABELS_DIR = EXPERIMENTS_ROOT / INSPECTION_ID / "yolo_labels_human"
SOURCE_PATH = EXPERIMENTS_ROOT / INSPECTION_ID / "annotation_source.json"

# image_id -> list of (x0, y0, x1, y1) pixel boxes, read off the grid overlay.
BOXES: dict[str, list[tuple[int, int, int, int]]] = {
    "9d1cfa7d3656": [  # 2.56.22 PM (2) - 2 bolts, vertical bracket
        (700, 115, 940, 360),
        (650, 535, 900, 790),
    ],
    "4e648f92f5a7": [  # 2.56.24 PM (1) - 4 bolts, single row
        (255, 650, 390, 795),
        (570, 625, 715, 775),
        (895, 615, 1035, 765),
        (1215, 630, 1360, 780),
    ],
    "2f1080f25f12": [  # 2.56.31 PM - 4 bolts, single row
        (195, 660, 340, 805),
        (495, 660, 640, 800),
        (790, 650, 935, 795),
        (1095, 650, 1240, 795),
    ],
    "4d68b0594b29": [  # 2.56.35 PM (1) - 4 columns x 3 stacked fasteners
        (255, 215, 420, 370), (310, 400, 450, 500), (150, 515, 355, 700),
        (555, 215, 715, 365), (595, 400, 735, 500), (505, 510, 705, 700),
        (855, 210, 1020, 360), (895, 400, 1035, 500), (895, 515, 1080, 700),
        (1155, 215, 1320, 365), (1185, 400, 1335, 500), (1195, 520, 1420, 700),
    ],
    "bbe04c3260cf": [  # 2.56.36 PM (1) - 4 columns x 3 stacked fasteners
        (400, 215, 565, 355), (420, 380, 555, 470), (395, 500, 565, 620),
        (675, 215, 830, 355), (680, 380, 815, 470), (665, 500, 830, 630),
        (930, 215, 1090, 355), (935, 380, 1070, 470), (925, 505, 1090, 630),
        (1165, 215, 1330, 355), (1195, 380, 1330, 470), (1150, 505, 1330, 630),
    ],
    "b7bc7be54441": [  # 2.56.38 PM - 4 columns x 3 stacked fasteners
        (365, 200, 530, 345), (400, 370, 530, 465), (375, 500, 560, 620),
        (640, 200, 800, 345), (670, 370, 800, 465), (680, 500, 895, 630),
        (905, 195, 1070, 340), (935, 365, 1065, 460), (925, 500, 1095, 620),
        (1165, 200, 1330, 345), (1200, 370, 1330, 465), (1220, 500, 1400, 630),
    ],
    "019a714885ff": [  # 2.56.43 PM - 4 columns x 3 stacked fasteners
        (280, 200, 460, 355), (320, 400, 450, 505), (255, 565, 420, 715),
        (590, 215, 760, 360), (610, 405, 745, 510), (590, 570, 745, 720),
        (875, 220, 1050, 360), (900, 405, 1030, 510), (885, 560, 1045, 715),
        (1140, 220, 1310, 360), (1175, 400, 1305, 505), (1195, 565, 1365, 715),
    ],
    "a22f947048f5": [  # 2.56.44 PM - 4 columns x 3 stacked fasteners
        (455, 270, 600, 390), (460, 405, 585, 510), (415, 520, 585, 645),
        (715, 280, 860, 395), (730, 405, 855, 510), (745, 520, 900, 650),
        (965, 280, 1105, 395), (975, 400, 1095, 500), (1005, 520, 1160, 645),
        (1185, 255, 1330, 375), (1195, 395, 1320, 490), (1225, 500, 1410, 620),
    ],
    "a6495d62f5af": [  # 2.56.46 PM (1) - 4 columns x 3 stacked fasteners
        (370, 200, 530, 345), (400, 375, 525, 475), (355, 510, 530, 635),
        (640, 205, 800, 345), (665, 375, 795, 475), (660, 505, 800, 635),
        (905, 205, 1065, 345), (935, 370, 1065, 475), (935, 510, 1105, 635),
        (1170, 210, 1330, 345), (1195, 375, 1325, 475), (1150, 510, 1330, 635),
    ],
    "72dde4a33315": [  # 2.56.52 PM (1) - 1 bolt
        (500, 590, 755, 790),
    ],
    "50c3534e8e3f": [  # 2.56.52 PM - 1 bolt
        (450, 720, 710, 955),
    ],
}


def main() -> None:
    manifest = {s.image_id: s for s in load_manifest(INSPECTION_ID)}
    HUMAN_LABELS_DIR.mkdir(parents=True, exist_ok=True)

    source: dict[str, dict] = {}
    if SOURCE_PATH.exists():
        source = json.loads(SOURCE_PATH.read_text())

    for image_id, boxes in BOXES.items():
        stored = manifest[image_id]
        w, h = stored.width, stored.height
        lines = []
        for x0, y0, x1, y1 in boxes:
            bw, bh = (x1 - x0) / w, (y1 - y0) / h
            cx, cy = (x0 + x1) / 2 / w, (y0 + y1) / 2 / h
            lines.append(f"0 {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}")
        (HUMAN_LABELS_DIR / f"{image_id}.txt").write_text("\n".join(lines))
        source[image_id] = {
            "source": "human_verified",
            "method": "visual read off pixel-coordinate grid overlay, +/-10-20px",
            "box_count": len(boxes),
        }

    # Mark everything else in the manifest (not in BOXES) as the original
    # Hough-proposal machine source, for images we haven't touched here.
    for image_id in manifest:
        if image_id not in source:
            source[image_id] = {"source": "hough_proposal", "method": "Hough circle + NMS, confidence-tagged"}

    SOURCE_PATH.write_text(json.dumps(source, indent=2))
    print(f"Wrote {len(BOXES)} human-verified label files to {HUMAN_LABELS_DIR}")
    print(f"Updated {SOURCE_PATH}")
    total_boxes = sum(len(b) for b in BOXES.values())
    print(f"Total human-verified boxes: {total_boxes}")


if __name__ == "__main__":
    main()
