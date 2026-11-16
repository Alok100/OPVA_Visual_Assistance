"""Build a YOLO-format dataset (images/, labels/, data.yaml) for the
Microtask 2.1 retrain, from BOTH label sources:

  - yolo_labels_final/  — Hough-circle proposals + NMS, "high confidence"
    tagged (39 images, mostly clean single/few-bolt close-ups)
  - yolo_labels_human/  — this session's human-verified boxes for the 11
    busbar/cable-dense images Hough couldn't handle (Step 2)

Every one of the 50 curated images now has usable labels. Split is
train/val/TEST (three-way, not the earlier train/val — Step 3 asks to keep
them separate) and stratified by label source, so val/test each contain a
realistic mix of clean and busbar scenes instead of all-clean or all-busbar
by chance. The split is deterministic (sorted order, not random) for
reproducibility, and a manifest.json records each image's source + split
for the Step 3 clean-vs-busbar evaluation breakdown.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import EXPERIMENTS_ROOT
from app.storage import load_manifest

INSPECTION_ID = "insp-bolt-torque-poc"
EXP_DIR = EXPERIMENTS_ROOT / INSPECTION_ID
CONFIDENCE_PATH = EXP_DIR / "confidence.json"
SOURCE_PATH = EXP_DIR / "annotation_source.json"
HOUGH_LABELS_DIR = EXP_DIR / "yolo_labels_final"
HUMAN_LABELS_DIR = EXP_DIR / "yolo_labels_human"

DATASET_DIR = EXP_DIR / "yolo_dataset_v2"
# Roughly 70/15/15, applied per source group so val/test aren't accidentally
# all-clean or all-busbar.
SPLIT_FRACTIONS = {"val": 0.15, "test": 0.15}


def _split_group(image_ids: list[str]) -> dict[str, str]:
    n = len(image_ids)
    n_val = max(1, round(n * SPLIT_FRACTIONS["val"])) if n >= 4 else 0
    n_test = max(1, round(n * SPLIT_FRACTIONS["test"])) if n >= 4 else 0
    # Deterministic: sorted order, test from the end, val just before it.
    ordered = sorted(image_ids)
    test_ids = set(ordered[-n_test:]) if n_test else set()
    val_ids = set(ordered[-(n_test + n_val) : -n_test or None]) if n_val else set()
    return {
        iid: ("test" if iid in test_ids else "val" if iid in val_ids else "train")
        for iid in ordered
    }


def main() -> None:
    manifest = {s.image_id: s for s in load_manifest(INSPECTION_ID)}
    confidence = json.loads(CONFIDENCE_PATH.read_text())
    source = json.loads(SOURCE_PATH.read_text())

    human_ids = [iid for iid, v in source.items() if v.get("source") == "human_verified"]
    hough_ids = [iid for iid, v in confidence.items() if v == "high"]

    splits = {}
    splits.update({iid: s for iid, s in _split_group(human_ids).items()})
    splits.update({iid: s for iid, s in _split_group(hough_ids).items()})

    for split in ("train", "val", "test"):
        (DATASET_DIR / "images" / split).mkdir(parents=True, exist_ok=True)
        (DATASET_DIR / "labels" / split).mkdir(parents=True, exist_ok=True)

    image_manifest = []
    for iid, split in splits.items():
        stored = manifest[iid]
        is_human = iid in human_ids
        label_src_dir = HUMAN_LABELS_DIR if is_human else HOUGH_LABELS_DIR

        dst_img = DATASET_DIR / "images" / split / f"{iid}.jpg"
        shutil.copy(EXPERIMENTS_ROOT / stored.stored_path, dst_img)
        dst_label = DATASET_DIR / "labels" / split / f"{iid}.txt"
        shutil.copy(label_src_dir / f"{iid}.txt", dst_label)

        image_manifest.append(
            {
                "image_id": iid,
                "filename": stored.filename,
                "split": split,
                "label_source": "human_verified" if is_human else "hough_proposal",
                "scene_type": "busbar" if is_human else "clean",
            }
        )

    data_yaml = DATASET_DIR / "data.yaml"
    data_yaml.write_text(
        f"path: {DATASET_DIR}\n"
        f"train: images/train\n"
        f"val: images/val\n"
        f"test: images/test\n"
        f"names:\n"
        f"  0: bolt\n"
    )

    (DATASET_DIR / "manifest.json").write_text(json.dumps(image_manifest, indent=2))

    for split in ("train", "val", "test"):
        n = sum(1 for m in image_manifest if m["split"] == split)
        n_busbar = sum(1 for m in image_manifest if m["split"] == split and m["scene_type"] == "busbar")
        print(f"{split}: {n} images ({n_busbar} busbar / {n - n_busbar} clean)")
    print(f"\nDataset dir: {DATASET_DIR}")
    print(f"data.yaml: {data_yaml}")


if __name__ == "__main__":
    main()
