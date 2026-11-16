"""Import a pre-made annotation JSON file (Microtask 3.1).

No annotation JSON format exists anywhere in this project already (verified
by inspection before writing this) — frontend demo data, the backend's own
BoundingBox, and the YOLO label .txt files all use three different,
mutually-incompatible conventions, and none of them are serialized as a
"here's an annotation file" JSON anywhere. So an uploaded file is treated as
genuinely external with an unknown schema: this module sniffs the JSON's
top-level shape and supports exactly three recognized conventions —
anything else is rejected with a clear error rather than guessed at.

Internal canonical box representation is pixel-absolute top-left + width/
height, matching app.models.BoundingBox (what detection.py/geometry.py/
validation.py already use) — COCO and LabelMe are both natively
pixel-absolute so no unit conversion is needed for them. The custom/generic
format is documented as requiring pixel-absolute coordinates too, rather
than silently guessing whether small values mean normalized 0-1 (that
guess could be wrong and would misplace every box).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .models import (
    AnnotationFormat,
    AnnotationImportResult,
    AnnotationStatus,
    BoundingBox,
    ImageAnnotations,
    ImportedBox,
)
from .storage import (
    StoredImage,
    load_manifest,
    save_imported_annotations_original,
    save_parsed_annotations,
)


class AnnotationImportError(ValueError):
    pass


@dataclass
class RawBox:
    x: float
    y: float
    width: float
    height: float
    label: str | None = None


def detect_format(data: Any) -> AnnotationFormat:
    if isinstance(data, dict) and "images" in data and "annotations" in data:
        return AnnotationFormat.COCO
    if isinstance(data, dict) and "shapes" in data:
        return AnnotationFormat.LABELME
    if isinstance(data, dict) and "objects" in data and "size" in data:
        # Supervisely / DatasetNinja export: one JSON per image, named
        # "<image filename>.json", with {"size":{...}, "objects":[...]}.
        # Checked before the generic custom fallback below — without this,
        # a Supervisely file's top-level keys (description/tags/size/
        # objects) get misread as "filename: [box, ...]" entries.
        return AnnotationFormat.SUPERVISELY
    if isinstance(data, dict) or isinstance(data, list):
        return AnnotationFormat.CUSTOM
    raise AnnotationImportError(
        "Unrecognized JSON structure: expected a COCO-style object "
        "({'images':..,'annotations':..}), a LabelMe-style object "
        "({'shapes':..}), a Supervisely-style object ({'size':..,'objects':..}), "
        "or a custom filename-keyed object/array."
    )


def parse_coco(data: dict) -> dict[str, list[RawBox]]:
    images = data.get("images")
    annotations = data.get("annotations")
    if not isinstance(images, list) or not isinstance(annotations, list):
        raise AnnotationImportError("COCO file must have list-valued 'images' and 'annotations'.")

    categories = {c["id"]: c.get("name") for c in data.get("categories", []) if "id" in c}
    image_id_to_filename: dict[Any, str] = {}
    for img in images:
        if "id" not in img or "file_name" not in img:
            raise AnnotationImportError("Each COCO 'images' entry needs 'id' and 'file_name'.")
        image_id_to_filename[img["id"]] = img["file_name"]

    result: dict[str, list[RawBox]] = {}
    for ann in annotations:
        if "image_id" not in ann or "bbox" not in ann:
            raise AnnotationImportError("Each COCO 'annotations' entry needs 'image_id' and 'bbox'.")
        filename = image_id_to_filename.get(ann["image_id"])
        if filename is None:
            raise AnnotationImportError(
                f"Annotation references image_id={ann['image_id']!r} not present in 'images'."
            )
        bbox = ann["bbox"]
        if not (isinstance(bbox, list) and len(bbox) == 4):
            raise AnnotationImportError(f"COCO 'bbox' must be [x,y,width,height], got {bbox!r}.")
        x, y, w, h = bbox
        label = categories.get(ann.get("category_id"))
        result.setdefault(filename, []).append(RawBox(x=x, y=y, width=w, height=h, label=label))
    return result


def _bounding_rect(points: list[list[float]]) -> tuple[float, float, float, float]:
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
    return x0, y0, x1 - x0, y1 - y0


def parse_labelme(data: dict) -> dict[str, list[RawBox]]:
    image_path = data.get("imagePath")
    shapes = data.get("shapes")
    if not image_path or not isinstance(shapes, list):
        raise AnnotationImportError("LabelMe file must have 'imagePath' and a list-valued 'shapes'.")

    boxes: list[RawBox] = []
    for shape in shapes:
        points = shape.get("points")
        if not isinstance(points, list) or len(points) < 2:
            raise AnnotationImportError(f"LabelMe shape has invalid 'points': {points!r}.")
        x, y, w, h = _bounding_rect(points)
        label = shape.get("label")
        # Polygon/non-rectangle shapes are approximated by their bounding
        # rectangle — flagged in the label so it's not presented as a
        # precise polygon import.
        shape_type = shape.get("shape_type", "rectangle")
        if shape_type != "rectangle" and label:
            label = f"{label} (bounding rect of {shape_type})"
        boxes.append(RawBox(x=x, y=y, width=w, height=h, label=label))

    # LabelMe files are one-per-image; use the basename so it matches
    # however the image was actually uploaded.
    from pathlib import Path

    filename = Path(image_path).name
    return {filename: boxes}


def parse_supervisely(data: dict, filename: str) -> dict[str, list[RawBox]]:
    """Supervisely/DatasetNinja format: one JSON per image, the image's own
    filename isn't inside the JSON payload — it's the upload's filename
    with the trailing '.json' stripped (DatasetNinja's own convention,
    e.g. "AUT-0001.jpg.json" -> "AUT-0001.jpg"). Each object's
    'points.exterior' is 2 points for a rectangle (top-left, bottom-right)
    or more for other geometry types, bounding-rect'd the same way as a
    LabelMe polygon."""
    objects = data.get("objects")
    if not isinstance(objects, list):
        raise AnnotationImportError("Supervisely file must have a list-valued 'objects'.")

    boxes: list[RawBox] = []
    for obj in objects:
        points = obj.get("points") or {}
        exterior = points.get("exterior")
        if not isinstance(exterior, list) or len(exterior) < 2:
            raise AnnotationImportError(f"Supervisely object has invalid 'points.exterior': {exterior!r}.")
        x, y, w, h = _bounding_rect(exterior)
        label = obj.get("classTitle")
        geometry_type = obj.get("geometryType", "rectangle")
        if geometry_type != "rectangle" and label:
            label = f"{label} (bounding rect of {geometry_type})"
        boxes.append(RawBox(x=x, y=y, width=w, height=h, label=label))

    from pathlib import Path

    image_filename = Path(filename).stem if filename.endswith(".json") else filename
    return {image_filename: boxes}


def parse_custom(data: dict | list) -> dict[str, list[RawBox]]:
    """Documented custom format (pixel-absolute coordinates required):

    {"<filename>": [{"x":.., "y":.., "width":.., "height":.., "label": ".."}, ...], ...}

    or equivalently a list of {"filename": "..", "boxes": [...]}.
    """

    def box_from_dict(d: dict) -> RawBox:
        if "bbox" in d and isinstance(d["bbox"], list) and len(d["bbox"]) == 4:
            x, y, w, h = d["bbox"]
        else:
            try:
                x, y, w, h = d["x"], d["y"], d["width"], d["height"]
            except KeyError as exc:
                raise AnnotationImportError(
                    f"Custom-format box missing required field {exc}; expected "
                    "x/y/width/height or a 4-element 'bbox'."
                ) from exc
        label = d.get("label") or d.get("class") or d.get("category")
        return RawBox(x=x, y=y, width=w, height=h, label=label)

    result: dict[str, list[RawBox]] = {}
    if isinstance(data, dict):
        for filename, boxes in data.items():
            if not isinstance(boxes, list):
                raise AnnotationImportError(f"Custom format: value for '{filename}' must be a list of boxes.")
            result[filename] = [box_from_dict(b) for b in boxes]
    else:  # list of {"filename":.., "boxes":..}
        for entry in data:
            if not isinstance(entry, dict) or "filename" not in entry or "boxes" not in entry:
                raise AnnotationImportError(
                    "Custom format list entries must be {'filename':.., 'boxes': [...]}."
                )
            result[entry["filename"]] = [box_from_dict(b) for b in entry["boxes"]]
    return result


_PARSERS = {
    AnnotationFormat.COCO: parse_coco,
    AnnotationFormat.LABELME: parse_labelme,
    AnnotationFormat.CUSTOM: parse_custom,
}


def parse_annotation_json(
    raw_bytes: bytes, filename: str = "annotations.json"
) -> tuple[AnnotationFormat, dict[str, list[RawBox]]]:
    try:
        data = json.loads(raw_bytes)
    except json.JSONDecodeError as exc:
        raise AnnotationImportError(f"Not valid JSON: {exc}") from exc

    fmt = detect_format(data)
    if fmt == AnnotationFormat.SUPERVISELY:
        # Unlike the other formats, Supervisely needs the upload's own
        # filename to recover which image it's for.
        parsed = parse_supervisely(data, filename)
    else:
        parsed = _PARSERS[fmt](data)
    return fmt, parsed


def validate_box(box: RawBox, image_width: int, image_height: int) -> str | None:
    """Returns an issue string if invalid, else None. A small 5% tolerance
    on the image-bounds check allows for minor annotation-tool rounding."""
    if box.width <= 0 or box.height <= 0:
        return f"non-positive width/height ({box.width}x{box.height})"
    if box.x < 0 or box.y < 0:
        return f"negative coordinate (x={box.x}, y={box.y})"
    tolerance = 1.05
    if box.x + box.width > image_width * tolerance or box.y + box.height > image_height * tolerance:
        return (
            f"box [{box.x},{box.y},{box.width},{box.height}] exceeds image "
            f"bounds ({image_width}x{image_height})"
        )
    return None


def _match_and_validate(
    fmt: AnnotationFormat,
    parsed: dict[str, list[RawBox]],
    manifest: dict[str, StoredImage],
) -> tuple[list[ImageAnnotations], list[str], int, int]:
    matched_images: list[ImageAnnotations] = []
    unmatched_filenames: list[str] = []
    invalid_box_count = 0
    total_box_count = 0

    for ref_filename, raw_boxes in parsed.items():
        stored = manifest.get(ref_filename)
        if stored is None:
            unmatched_filenames.append(ref_filename)
            continue

        boxes: list[ImportedBox] = []
        for raw in raw_boxes:
            total_box_count += 1
            issue = validate_box(raw, stored.width, stored.height)
            is_valid = issue is None
            if not is_valid:
                invalid_box_count += 1
            boxes.append(
                ImportedBox(
                    bbox=BoundingBox(x=raw.x, y=raw.y, width=raw.width, height=raw.height),
                    label=raw.label,
                    status=AnnotationStatus.IMPORTED_NOT_REVIEWED,
                    source_format=fmt,
                    valid=is_valid,
                    issue=issue,
                )
            )
        matched_images.append(
            ImageAnnotations(image_id=stored.image_id, filename=stored.filename, boxes=boxes)
        )

    return matched_images, unmatched_filenames, invalid_box_count, total_box_count


def import_annotations_batch(
    inspection_id: str, files: list[tuple[str, bytes]]
) -> AnnotationImportResult:
    """Parses, validates, and matches one or more uploaded annotation JSON
    files against this inspection's already-uploaded images — never runs
    detection, never marks anything approved.

    Takes multiple files in one call because LabelMe's own convention is one
    JSON file per image (unlike COCO/custom, which batch many images into
    one file) — a real annotation set for N images may arrive as N files,
    and they must all land in the same saved result rather than each
    overwriting the previous one. A bad individual file is reported in
    `file_errors` without aborting the rest of the batch, matching how
    POST .../images already handles per-file upload errors.

    Preserves every original file unmodified and saves the merged
    matched/parsed result separately, so provenance of "what was literally
    uploaded" vs. "what we made of it" stays distinguishable.
    """
    manifest = {img.filename: img for img in load_manifest(inspection_id)}

    detected_formats: list[AnnotationFormat] = []
    original_files_saved_as: list[str] = []
    file_errors: list[dict[str, str]] = []
    images_by_id: dict[str, ImageAnnotations] = {}
    unmatched_filenames: list[str] = []
    invalid_box_count = 0
    total_box_count = 0

    for filename, raw_bytes in files:
        try:
            fmt, parsed = parse_annotation_json(raw_bytes, filename)
        except AnnotationImportError as exc:
            file_errors.append({"filename": filename, "error": str(exc)})
            continue

        matched, unmatched, invalid_count, total_count = _match_and_validate(fmt, parsed, manifest)

        if fmt not in detected_formats:
            detected_formats.append(fmt)
        unmatched_filenames.extend(f for f in unmatched if f not in unmatched_filenames)
        invalid_box_count += invalid_count
        total_box_count += total_count
        for image_annos in matched:
            if image_annos.image_id in images_by_id:
                images_by_id[image_annos.image_id].boxes.extend(image_annos.boxes)
            else:
                images_by_id[image_annos.image_id] = image_annos

        original_files_saved_as.append(
            save_imported_annotations_original(inspection_id, filename, raw_bytes)
        )

    if not detected_formats and file_errors:
        # Every file in the batch failed to parse — nothing to save, report
        # as a hard error rather than a silent empty success.
        raise AnnotationImportError(
            "All uploaded files failed to parse: "
            + "; ".join(f"{e['filename']}: {e['error']}" for e in file_errors)
        )

    result = AnnotationImportResult(
        detected_formats=detected_formats,
        original_files_saved_as=original_files_saved_as,
        matched_images=list(images_by_id.values()),
        unmatched_filenames=unmatched_filenames,
        invalid_box_count=invalid_box_count,
        total_box_count=total_box_count,
        file_errors=file_errors,
    )
    save_parsed_annotations(inspection_id, result.model_dump_json(indent=2))
    return result
