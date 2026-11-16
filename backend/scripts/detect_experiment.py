"""Step 4 experiment: can a pretrained detector find bolts in the POC dataset?

Two models are tried and reported honestly, not cherry-picked:
  1. yolov8n.pt  — standard COCO-80 pretrained YOLO (baseline; COCO has no
     "bolt" class, so this is expected to fail or misfire on other classes).
  2. yolov8s-worldv2.pt — YOLO-World, open-vocabulary/zero-shot detection,
     given the text prompt "bolt" at inference time instead of a fixed class
     list. This is the realistic non-fine-tuned option for an unseen class.

Writes per-image detection counts/confidences to stdout and saves annotated
images for manual review to backend/data/experiments/<id>/detect_review/.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ultralytics import YOLO

from app.config import EXPERIMENTS_ROOT
from app.storage import load_manifest

INSPECTION_ID = "insp-bolt-torque-poc"


def run_baseline_coco():
    model = YOLO("yolov8n.pt")
    manifest = load_manifest(INSPECTION_ID)
    total_detections = 0
    images_with_detections = 0
    class_counts: dict[str, int] = {}

    for stored in manifest:
        path = EXPERIMENTS_ROOT / stored.stored_path
        result = model.predict(source=str(path), verbose=False, conf=0.15)[0]
        n = len(result.boxes)
        if n > 0:
            images_with_detections += 1
            total_detections += n
            for cls_id in result.boxes.cls.tolist():
                name = model.names[int(cls_id)]
                class_counts[name] = class_counts.get(name, 0) + 1

    print("=== Baseline: yolov8n.pt (COCO-80) ===")
    print(f"Images: {len(manifest)}")
    print(f"Images with >=1 detection: {images_with_detections}")
    print(f"Total detections: {total_detections}")
    print(f"Class counts: {class_counts}")
    print()


def run_yolo_world():
    model = YOLO("yolov8s-worldv2.pt")
    model.set_classes(["bolt", "hex bolt head", "screw"])

    manifest = load_manifest(INSPECTION_ID)
    review_dir = EXPERIMENTS_ROOT / INSPECTION_ID / "detect_review"
    review_dir.mkdir(parents=True, exist_ok=True)

    total_detections = 0
    images_with_detections = 0
    confidences = []
    per_image = []

    for stored in manifest:
        path = EXPERIMENTS_ROOT / stored.stored_path
        result = model.predict(source=str(path), verbose=False, conf=0.1)[0]
        n = len(result.boxes)
        confs = result.boxes.conf.tolist() if n else []
        per_image.append((stored.filename, n, confs))
        if n > 0:
            images_with_detections += 1
            total_detections += n
            confidences.extend(confs)
            result.save(filename=str(review_dir / f"{stored.image_id}.jpg"))

    print("=== YOLO-World zero-shot, prompt=['bolt','hex bolt head','screw'] ===")
    print(f"Images: {len(manifest)}")
    print(f"Images with >=1 detection: {images_with_detections}")
    print(f"Total detections: {total_detections}")
    if confidences:
        print(f"Confidence min/mean/max: {min(confidences):.2f} / {sum(confidences)/len(confidences):.2f} / {max(confidences):.2f}")
    print()
    print("Per-image detail:")
    for filename, n, confs in per_image:
        conf_str = ", ".join(f"{c:.2f}" for c in confs)
        print(f"  {n:2d}  {filename}  [{conf_str}]")
    print(f"\nAnnotated review images written to: {review_dir}")


if __name__ == "__main__":
    run_baseline_coco()
    run_yolo_world()
