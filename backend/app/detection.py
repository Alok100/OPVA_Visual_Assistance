"""Bolt detection via the Microtask 2 fine-tuned YOLOv8n model.

See docs/MICROTASK_2_FINDINGS.md for why: standard pretrained COCO-80 YOLO
has no "bolt" class and misclassified everything; zero-shot YOLO-World found
0/50 bolts even at a permissive threshold. This is a real fine-tune on 39
hand-reviewed images from this project's own photos, not a stock model —
and it should still be treated as a small, noisy-data POC model, not a
production detector (see its real validation metrics in the same doc).
"""

from __future__ import annotations

from pathlib import Path

from ultralytics import YOLO

from .config import BACKEND_ROOT, DEDUP_IOU_THRESHOLD, DETECTION_CONFIDENCE_THRESHOLD
from .geometry import nms
from .models import BoundingBox

MODEL_PATH = BACKEND_ROOT / "models" / "bolt_detector_v1.pt"

_model: YOLO | None = None


def _get_model() -> YOLO:
    global _model
    if _model is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Fine-tuned bolt detector not found at {MODEL_PATH}. "
                "Run scripts/prepare_yolo_dataset.py + the training step first."
            )
        _model = YOLO(str(MODEL_PATH))
    return _model


def detect_bolts(image_path: Path) -> list[tuple[BoundingBox, float]]:
    """Runs the fine-tuned detector on one image, then collapses duplicate
    predictions of the same physical bolt (IoU > DEDUP_IOU_THRESHOLD)
    before returning — ultralytics' own NMS (iou=0.7 default) is looser
    than this and was observed leaving same-bolt duplicates in the raw
    output (see docs/MICROTASK_2_FINDINGS.md).

    Returns (bbox, confidence) pairs in pixel coordinates, confidence-sorted
    descending. Raises on an unreadable file rather than returning an empty
    list silently.
    """
    model = _get_model()
    result = model.predict(
        source=str(image_path), verbose=False, conf=DETECTION_CONFIDENCE_THRESHOLD
    )[0]

    boxes: list[BoundingBox] = []
    confs: list[float] = []
    for box, conf in zip(result.boxes.xyxy.tolist(), result.boxes.conf.tolist()):
        x0, y0, x1, y1 = box
        boxes.append(BoundingBox(x=x0, y=y0, width=x1 - x0, height=y1 - y0))
        confs.append(conf)

    kept_idx = nms(boxes, confs, DEDUP_IOU_THRESHOLD)
    detections = [(boxes[i], confs[i]) for i in kept_idx]
    detections.sort(key=lambda d: d[1], reverse=True)
    return detections
