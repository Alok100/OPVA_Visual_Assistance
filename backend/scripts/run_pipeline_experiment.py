"""End-to-end sanity run of the real pipeline (detect -> color check ->
verdict) over all 50 curated images, for honest reporting before wiring the
UI. Prints the InspectionSummary and writes an annotated contact-sheet-ready
set of review images.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cv2
import json

from app.config import EXPERIMENTS_ROOT
from app.models import BoltVerdict
from app.pipeline import process_image, summarize
from app.storage import load_manifest

INSPECTION_ID = "insp-bolt-torque-poc"
REVIEW_DIR = EXPERIMENTS_ROOT / INSPECTION_ID / "pipeline_review"

VERDICT_COLOR = {
    BoltVerdict.PASS: (0, 180, 0),
    BoltVerdict.FAIL: (0, 0, 220),
    BoltVerdict.REVIEW: (0, 165, 255),
    BoltVerdict.NOT_PROCESSED: (128, 128, 128),
}


def main() -> None:
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest(INSPECTION_ID)

    results = []
    for stored in manifest:
        img_path = EXPERIMENTS_ROOT / stored.stored_path
        result = process_image(stored.image_id, stored.filename, img_path)
        results.append(result)

        img = cv2.imread(str(img_path))
        for bolt in result.bolts:
            b = bolt.bbox
            x0, y0 = int(b.x), int(b.y)
            x1, y1 = int(b.x + b.width), int(b.y + b.height)
            color = VERDICT_COLOR[bolt.verdict]
            cv2.rectangle(img, (x0, y0), (x1, y1), color, 5)
            frac_str = f"{bolt.marking_yellow_fraction:.2f}" if bolt.marking_yellow_fraction is not None else "-"
            label = f"{bolt.verdict.value} {frac_str}"
            cv2.putText(img, label, (x0, max(0, y0 - 10)), cv2.FONT_HERSHEY_SIMPLEX, 1.1, color, 3)
        cv2.imwrite(str(REVIEW_DIR / f"{stored.image_id}.jpg"), img)

    summary = summarize(results)
    print(json.dumps(summary.model_dump(), indent=2))
    print(f"\nReview images: {REVIEW_DIR}")

    per_image_path = EXPERIMENTS_ROOT / INSPECTION_ID / "pipeline_results.json"
    per_image_path.write_text(
        json.dumps([r.model_dump() for r in results], indent=2)
    )
    print(f"Per-image results: {per_image_path}")


if __name__ == "__main__":
    main()
