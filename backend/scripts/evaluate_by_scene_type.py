"""Step 3: per-image test-set evaluation broken down by scene_type
(clean close-up vs busbar), using the actual deployed pipeline (dedup NMS +
guard), not just raw ultralytics val() aggregate numbers.

Matches detections to ground-truth test labels via IoU >= 0.5 (standard
mAP50 matching convention) and reports simple precision/recall per image
and per scene_type group. This is a held-out test set the model never saw
during training OR validation/early-stopping decisions.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import BACKEND_ROOT
from app.geometry import iou
from app.models import BoundingBox
from app.validation import assess_detection_quality
from ultralytics import YOLO
import cv2

import os

DATASET_DIR = Path(__file__).resolve().parent.parent / (
    "data/experiments/insp-bolt-torque-poc/" + os.environ.get("EVAL_DATASET", "yolo_dataset_v3")
)
MANIFEST_PATH = DATASET_DIR / "manifest.json"


def load_yolo_labels(path: Path, w: int, h: int) -> list[BoundingBox]:
    if not path.exists() or not path.read_text().strip():
        return []
    boxes = []
    for line in path.read_text().splitlines():
        _, ncx, ncy, nbw, nbh = (float(x) for x in line.split())
        bw, bh = nbw * w, nbh * h
        boxes.append(BoundingBox(x=ncx * w - bw / 2, y=ncy * h - bh / 2, width=bw, height=bh))
    return boxes


def match(pred: list[BoundingBox], gt: list[BoundingBox], thresh=0.5):
    matched_gt = set()
    tp = 0
    for p in pred:
        best_iou, best_j = 0.0, -1
        for j, g in enumerate(gt):
            if j in matched_gt:
                continue
            v = iou(p, g)
            if v > best_iou:
                best_iou, best_j = v, j
        if best_iou >= thresh:
            matched_gt.add(best_j)
            tp += 1
    fp = len(pred) - tp
    fn = len(gt) - len(matched_gt)
    return tp, fp, fn


def main() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text())
    test_items = [m for m in manifest if m["split"] == "test"]

    model_path = BACKEND_ROOT / "models" / (sys.argv[1] if len(sys.argv) > 1 else "bolt_detector_v2.pt")
    model = YOLO(str(model_path))
    print(f"Model: {model_path.name}")
    from app.geometry import nms as nms_fn

    results_by_scene: dict[str, list[tuple[int, int, int]]] = {"clean": [], "busbar": []}
    print(f"{'filename':45s} {'scene':7s} {'pred':>5s} {'gt':>4s} {'tp':>3s} {'fp':>3s} {'fn':>3s} {'guard':>13s}")
    for item in test_items:
        img_path = DATASET_DIR / "images" / "test" / f"{item['image_id']}.jpg"
        label_path = DATASET_DIR / "labels" / "test" / f"{item['image_id']}.txt"
        img = cv2.imread(str(img_path))
        h, w = img.shape[:2]

        result = model.predict(source=str(img_path), verbose=False, conf=0.15)[0]
        raw_boxes, raw_confs = [], []
        for box, conf in zip(result.boxes.xyxy.tolist(), result.boxes.conf.tolist()):
            x0, y0, x1, y1 = box
            raw_boxes.append(BoundingBox(x=x0, y=y0, width=x1 - x0, height=y1 - y0))
            raw_confs.append(conf)
        kept_idx = nms_fn(raw_boxes, raw_confs, 0.5)
        pred_boxes = [raw_boxes[i] for i in kept_idx]

        gt_boxes = load_yolo_labels(label_path, w, h)
        tp, fp, fn = match(pred_boxes, gt_boxes)

        quality = assess_detection_quality(pred_boxes, w, h)
        scene = item["scene_type"]
        results_by_scene[scene].append((tp, fp, fn))
        print(
            f"{item['filename']:45s} {scene:7s} {len(pred_boxes):5d} {len(gt_boxes):4d} "
            f"{tp:3d} {fp:3d} {fn:3d} {quality.severity:>13s}"
        )

    print("\n=== Summary by scene type (IoU>=0.5 matching) ===")
    for scene, rows in results_by_scene.items():
        tp = sum(r[0] for r in rows)
        fp = sum(r[1] for r in rows)
        fn = sum(r[2] for r in rows)
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        print(f"{scene:8s} images={len(rows):2d} tp={tp:3d} fp={fp:3d} fn={fn:3d} precision={precision:.3f} recall={recall:.3f}")


if __name__ == "__main__":
    main()
