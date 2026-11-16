"""Microtask 2.2 Step 1 fix: scene-group-aware split.

The v2 split (prepare_yolo_dataset.py) stratified busbar images individually
by image_id, treating each as an independent sample. Visual audit (see
docs/MICROTASK_2_2_FINDINGS.md) found 8 of the 11 "busbar" images are the
same physical breaker unit photographed repeatedly over a 24-second burst —
splitting that group across train/val/test leaks the exact scene (cable
colors, bracket geometry, background) across splits. Only 3 busbar images
are genuinely distinct scenes.

Fix: the 8-image same-unit group goes entirely to train (splitting it
achieves no real held-out validity — there is nothing independent to hold
out). The 3 distinct busbar images are spread 1/1/1 across train/val/test,
giving thin but *real* held-out busbar signal. Clean images keep the same
stratified split as v2 (unchanged, for comparability).

No new annotations are created — reuses the same hough_proposal and
human_verified label files from Microtask 2.1.
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

DATASET_DIR = EXP_DIR / "yolo_dataset_v3"

# Same physical breaker unit, 24-second burst — must stay together (train).
SAME_UNIT_GROUP = {
    "4e648f92f5a7", "2f1080f25f12", "4d68b0594b29", "bbe04c3260cf",
    "b7bc7be54441", "019a714885ff", "a22f947048f5", "a6495d62f5af",
}
# Genuinely distinct busbar-adjacent scenes -> spread across splits.
DISTINCT_BUSBAR_SPLIT = {
    "9d1cfa7d3656": "val",     # vertical bracket, 2 bolts
    "72dde4a33315": "train",  # single bolt, aluminum DIN rail
    "50c3534e8e3f": "test",   # single bolt, aluminum DIN rail (different screw)
}


def _split_clean(image_ids: list[str]) -> dict[str, str]:
    # Same deterministic stratification as v2, for direct comparability.
    n = len(image_ids)
    n_val = max(1, round(n * 0.15))
    n_test = max(1, round(n * 0.15))
    ordered = sorted(image_ids)
    test_ids = set(ordered[-n_test:])
    val_ids = set(ordered[-(n_test + n_val) : -n_test])
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
    assert set(human_ids) == SAME_UNIT_GROUP | set(DISTINCT_BUSBAR_SPLIT), "busbar id set changed upstream"

    splits: dict[str, str] = {}
    splits.update(_split_clean(hough_ids))
    splits.update({iid: "train" for iid in SAME_UNIT_GROUP})
    splits.update(DISTINCT_BUSBAR_SPLIT)

    for split in ("train", "val", "test"):
        (DATASET_DIR / "images" / split).mkdir(parents=True, exist_ok=True)
        (DATASET_DIR / "labels" / split).mkdir(parents=True, exist_ok=True)

    image_manifest = []
    for iid, split in splits.items():
        stored = manifest[iid]
        is_human = iid in human_ids
        label_src_dir = HUMAN_LABELS_DIR if is_human else HOUGH_LABELS_DIR

        shutil.copy(EXPERIMENTS_ROOT / stored.stored_path, DATASET_DIR / "images" / split / f"{iid}.jpg")
        shutil.copy(label_src_dir / f"{iid}.txt", DATASET_DIR / "labels" / split / f"{iid}.txt")

        image_manifest.append(
            {
                "image_id": iid,
                "filename": stored.filename,
                "split": split,
                "label_source": "human_verified" if is_human else "hough_proposal",
                "scene_type": "busbar" if is_human else "clean",
                "scene_group": "same_unit_burst" if iid in SAME_UNIT_GROUP else (
                    "distinct_busbar" if iid in DISTINCT_BUSBAR_SPLIT else "clean"
                ),
            }
        )

    data_yaml = DATASET_DIR / "data.yaml"
    data_yaml.write_text(
        f"path: {DATASET_DIR}\ntrain: images/train\nval: images/val\ntest: images/test\nnames:\n  0: bolt\n"
    )
    (DATASET_DIR / "manifest.json").write_text(json.dumps(image_manifest, indent=2))

    for split in ("train", "val", "test"):
        n = sum(1 for m in image_manifest if m["split"] == split)
        n_busbar = sum(1 for m in image_manifest if m["split"] == split and m["scene_type"] == "busbar")
        print(f"{split}: {n} images ({n_busbar} busbar / {n - n_busbar} clean)")
    print(f"\nDataset dir: {DATASET_DIR}")


if __name__ == "__main__":
    main()
