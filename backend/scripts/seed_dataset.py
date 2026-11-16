"""One-off script: select 50 images from the supplied bolt-photo folder and
load them into the POC's inspection dataset via the real storage module (so
the manifest this produces is exactly what a real upload would produce).

Base selection: systematic sample (every 2nd file in filename order) across
the full source folder, which spreads the sample across the whole photo
shoot instead of biasing toward whatever was captured first. One member of
the single near-duplicate pair found during inspection is dropped.

Curation on top of that base sample, after a visual audit (contact sheet
review) of all 50: the source folder mixes genuine bolt photos with other
inspection documentation (equipment nameplates, a disconnect-switch position
photo) and a few very cluttered wide panel shots where no automatic box
proposal could be trusted. Those 10 are swapped for 10 clean bolt close-ups
from the unused pool so the fine-tune set is bolt content throughout.

Usage:
    backend/.venv/bin/python backend/scripts/seed_dataset.py \
        "/Users/alokkumar/Desktop/Workflow Content/Bolt Torque & Boxes Photos"
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.storage import UploadValidationError, save_image  # noqa: E402

INSPECTION_ID = "insp-bolt-torque-poc"

# Dropped as the near-duplicate of "WhatsApp Image 2026-09-30 at 2.56.25 PM (1).jpeg"
# (same panel, same angle, re-shot ~5s later).
DROP_DUPLICATE = "WhatsApp Image 2026-09-30 at 2.56.30 PM.jpeg"

# Not bolt content at all (equipment nameplates / switch-position photos) or
# wide, cluttered multi-bolt panel overviews unusable for automatic box
# proposals — found via contact-sheet visual audit, see docs/MICROTASK_2_FINDINGS.md.
DROP_NON_BOLT_OR_UNUSABLE = {
    "WhatsApp Image 2026-09-24 at 3.50.03 PM (1).jpeg",  # wide panel overview
    "WhatsApp Image 2026-09-25 at 9.11.47 AM.jpeg",  # wide panel overview
    "WhatsApp Image 2026-09-30 at 2.56.11 PM.jpeg",  # wide panel overview
    "WhatsApp Image 2026-09-30 at 2.56.27 PM.jpeg",  # nameplate/switch label, no bolt
    "WhatsApp Image 2026-09-30 at 2.56.28 PM.jpeg",  # nameplate
    "WhatsApp Image 2026-09-30 at 2.56.29 PM.jpeg",  # nameplate
    "WhatsApp Image 2026-09-30 at 2.56.33 PM (1).jpeg",  # disconnect switch position photo
    "WhatsApp Image 2026-09-30 at 2.56.34 PM (1).jpeg",  # nameplate
    "WhatsApp Image 2026-09-30 at 2.56.39 PM.jpeg",  # nameplate
    "WhatsApp Image 2026-09-30 at 2.56.40 PM.jpeg",  # nameplate
}

# Clean bolt close-ups from the unused half of the source folder, swapped in
# to replace the 10 dropped above.
ADD_REPLACEMENTS = {
    "WhatsApp Image 2026-09-30 at 2.56.14 PM (1).jpeg",
    "WhatsApp Image 2026-09-30 at 2.56.15 PM.jpeg",
    "WhatsApp Image 2026-09-30 at 2.56.18 PM (1).jpeg",
    "WhatsApp Image 2026-09-30 at 2.56.20 PM (2).jpeg",
    "WhatsApp Image 2026-09-30 at 2.56.22 PM.jpeg",
    "WhatsApp Image 2026-09-30 at 2.56.36 PM.jpeg",
    "WhatsApp Image 2026-09-30 at 2.56.52 PM (1).jpeg",
    "WhatsApp Image 2026-09-30 at 2.56.54 PM.jpeg",
    "WhatsApp Image 2026-09-30 at 2.56.57 PM.jpeg",
    "WhatsApp Image 2026-09-30 at 2.57.01 PM (1).jpeg",
}


def select_images(source_dir: Path) -> list[Path]:
    files = sorted(source_dir.glob("*.jpeg"))
    by_name = {f.name: f for f in files}
    sampled = files[0::2]
    base = [f for f in sampled if f.name != DROP_DUPLICATE and f.name not in DROP_NON_BOLT_OR_UNUSABLE]
    replacements = [by_name[name] for name in sorted(ADD_REPLACEMENTS)]
    return sorted(base + replacements, key=lambda f: f.name)


def main() -> None:
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    source_dir = Path(sys.argv[1])
    if not source_dir.is_dir():
        print(f"Not a directory: {source_dir}")
        sys.exit(1)

    selected = select_images(source_dir)
    print(f"Selected {len(selected)} images from {len(list(source_dir.glob('*.jpeg')))} total.")

    ok, failed = 0, 0
    for path in selected:
        try:
            data = path.read_bytes()
            stored = save_image(
                inspection_id=INSPECTION_ID,
                filename=path.name,
                content_type="image/jpeg",
                data=data,
            )
            ok += 1
            print(f"  OK  {stored.image_id}  {stored.width}x{stored.height}  {path.name}")
        except UploadValidationError as exc:
            failed += 1
            print(f"  FAIL  {path.name}: {exc}")

    print(f"\nDone. {ok} stored, {failed} failed. Inspection id: {INSPECTION_ID}")


if __name__ == "__main__":
    main()
