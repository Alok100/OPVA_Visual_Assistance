"""Filesystem-backed dataset storage for one inspection's uploaded images.

No database: a JSON manifest per inspection, same approach as the frontend's
"no state library until a real backend justifies it" rule — a single-process
FastAPI POC doesn't justify one either. Layout:

  backend/data/experiments/<inspection_id>/
    images/<image_id>__<original_filename>
    manifest.json
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path

from PIL import Image

from .config import EXPERIMENTS_ROOT


@dataclass
class StoredImage:
    image_id: str
    filename: str
    stored_path: str
    content_type: str
    size_bytes: int
    width: int
    height: int
    sha256: str


class UploadValidationError(ValueError):
    pass


def _experiment_dir(inspection_id: str) -> Path:
    safe_id = "".join(c for c in inspection_id if c.isalnum() or c in "-_")
    if not safe_id or safe_id != inspection_id:
        raise UploadValidationError("Invalid inspection id.")
    return EXPERIMENTS_ROOT / safe_id


def _manifest_path(inspection_id: str) -> Path:
    return _experiment_dir(inspection_id) / "manifest.json"


def load_manifest(inspection_id: str) -> list[StoredImage]:
    path = _manifest_path(inspection_id)
    if not path.exists():
        return []
    raw = json.loads(path.read_text())
    return [StoredImage(**item) for item in raw]


def _write_manifest(inspection_id: str, images: list[StoredImage]) -> None:
    path = _manifest_path(inspection_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([asdict(img) for img in images], indent=2))


def save_image(
    inspection_id: str,
    filename: str,
    content_type: str,
    data: bytes,
) -> StoredImage:
    """Validate and persist one uploaded image, appending it to the manifest.

    Raises UploadValidationError on bad type/size/corrupt image content
    rather than silently accepting it — upload errors must surface, not
    become a fake success.
    """
    from .config import ALLOWED_IMAGE_CONTENT_TYPES, MAX_UPLOAD_BYTES

    if content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
        raise UploadValidationError(
            f"Unsupported content type '{content_type}'. "
            f"Allowed: {sorted(ALLOWED_IMAGE_CONTENT_TYPES)}"
        )
    if len(data) > MAX_UPLOAD_BYTES:
        raise UploadValidationError(
            f"File '{filename}' is {len(data)} bytes, exceeds the "
            f"{MAX_UPLOAD_BYTES} byte limit."
        )

    try:
        import io

        with Image.open(io.BytesIO(data)) as img:
            img.verify()
        with Image.open(io.BytesIO(data)) as img:
            width, height = img.size
    except Exception as exc:
        raise UploadValidationError(f"'{filename}' is not a valid image file: {exc}") from exc

    image_id = uuid.uuid4().hex[:12]
    exp_dir = _experiment_dir(inspection_id)
    images_dir = exp_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    safe_filename = Path(filename).name
    stored_name = f"{image_id}__{safe_filename}"
    stored_path = images_dir / stored_name
    stored_path.write_bytes(data)

    stored = StoredImage(
        image_id=image_id,
        filename=safe_filename,
        stored_path=str(stored_path.relative_to(EXPERIMENTS_ROOT)),
        content_type=content_type,
        size_bytes=len(data),
        width=width,
        height=height,
        sha256=hashlib.sha256(data).hexdigest(),
    )

    manifest = load_manifest(inspection_id)
    manifest.append(stored)
    _write_manifest(inspection_id, manifest)
    return stored


def resolve_image_path(inspection_id: str, image_id: str) -> Path | None:
    for stored in load_manifest(inspection_id):
        if stored.image_id == image_id:
            return EXPERIMENTS_ROOT / stored.stored_path
    return None


def save_imported_annotations_original(inspection_id: str, filename: str, data: bytes) -> str:
    """Preserves the exact uploaded annotation JSON, unmodified, alongside
    the parsed/matched version main.py writes separately. Returns the path
    relative to EXPERIMENTS_ROOT."""
    exp_dir = _experiment_dir(inspection_id)
    originals_dir = exp_dir / "imported_annotations"
    originals_dir.mkdir(parents=True, exist_ok=True)
    import uuid as _uuid

    safe_filename = Path(filename).name
    stored_name = f"{_uuid.uuid4().hex[:12]}__{safe_filename}"
    stored_path = originals_dir / stored_name
    stored_path.write_bytes(data)
    return str(stored_path.relative_to(EXPERIMENTS_ROOT))


def _parsed_annotations_path(inspection_id: str) -> Path:
    return _experiment_dir(inspection_id) / "annotations_imported.json"


def save_parsed_annotations(inspection_id: str, result_json: str) -> None:
    """Overwrites this inspection's imported-annotations record. A later
    import replaces the previous one (single current import per inspection
    for this milestone); the raw original files from every import remain on
    disk under imported_annotations/ regardless."""
    path = _parsed_annotations_path(inspection_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(result_json)


def load_parsed_annotations(inspection_id: str) -> str | None:
    path = _parsed_annotations_path(inspection_id)
    if not path.exists():
        return None
    return path.read_text()


def _current_annotations_path(inspection_id: str) -> Path:
    return _experiment_dir(inspection_id) / "annotations_current.json"


def save_current_annotations(inspection_id: str, result_json: str) -> None:
    """Overwrites this inspection's live/editable annotation state
    (Microtask 3.2). Distinct from save_parsed_annotations above — that one
    is the immutable original-import record, never touched by edits."""
    path = _current_annotations_path(inspection_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(result_json)


def load_current_annotations(inspection_id: str) -> str | None:
    path = _current_annotations_path(inspection_id)
    if not path.exists():
        return None
    return path.read_text()
