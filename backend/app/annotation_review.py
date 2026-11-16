"""Manual annotation editing, review/approve workflow, and persistence
(Microtask 3.2).

Kept as its own module, separate from annotation_import.py, so that
module's own docstring claim ("never marks boxes approved") stays true
unmodified — nothing here is imported by annotation_import.py, only the
other way around (main.py wires the two together after a successful
import; see import_annotations_endpoint).

Two on-disk records per inspection (both under storage.py's existing
per-inspection layout):
- annotations_imported.json — immutable, written only by
  annotation_import.import_annotations_batch. Never touched here.
- annotations_current.json — the live/editable state this module owns,
  keyed by image_id.

No snapshot of "what an imported box originally looked like" is stored in
the current-state file. Because the import record never changes once
written, the same box `id` can always be diffed against it live, at read
time — see _with_provenance. Simpler than snapshotting, and it can't go
stale (the source it diffs against can't change).
"""

from __future__ import annotations

from pydantic import TypeAdapter

from .annotation_import import RawBox, validate_box
from .models import (
    AnnotationImportResult,
    AnnotationOrigin,
    AnnotationStatus,
    CurrentBox,
    CurrentBoxInput,
    CurrentBoxView,
    CurrentImageAnnotations,
    CurrentImageAnnotationsView,
    ImportedBox,
)
from .storage import (
    StoredImage,
    load_current_annotations,
    load_manifest,
    load_parsed_annotations,
    save_current_annotations,
)


class AnnotationTransitionError(ValueError):
    pass


# Forward-only: reviewing an imported/AI-generated box marks it
# human-verified; approving requires it already be human-verified. Nothing
# else is a legal transition — in particular, skipping straight to
# APPROVED_FOR_TRAINING is always rejected. This is the mechanical half of
# "unapproved annotations cannot silently enter the training dataset."
_FORWARD_TRANSITIONS: dict[AnnotationStatus, AnnotationStatus] = {
    AnnotationStatus.IMPORTED_NOT_REVIEWED: AnnotationStatus.HUMAN_VERIFIED,
    AnnotationStatus.AI_GENERATED_NOT_REVIEWED: AnnotationStatus.HUMAN_VERIFIED,
    AnnotationStatus.HUMAN_VERIFIED: AnnotationStatus.APPROVED_FOR_TRAINING,
}

_CurrentStateAdapter = TypeAdapter(dict[str, CurrentImageAnnotations])


def _load_current_state(inspection_id: str) -> dict[str, CurrentImageAnnotations]:
    raw = load_current_annotations(inspection_id)
    if raw is None:
        return {}
    return _CurrentStateAdapter.validate_json(raw)


def _save_current_state(inspection_id: str, state: dict[str, CurrentImageAnnotations]) -> None:
    save_current_annotations(inspection_id, _CurrentStateAdapter.dump_json(state).decode())


def _imported_boxes_by_image(inspection_id: str) -> dict[str, dict[str, ImportedBox]]:
    raw = load_parsed_annotations(inspection_id)
    if raw is None:
        return {}
    result = AnnotationImportResult.model_validate_json(raw)
    return {img.image_id: {box.id: box for box in img.boxes} for img in result.matched_images}


def _bbox_equal(a, b) -> bool:
    return a.x == b.x and a.y == b.y and a.width == b.width and a.height == b.height


def _with_provenance(box: CurrentBox, imported_lookup: dict[str, ImportedBox]) -> CurrentBoxView:
    original = imported_lookup.get(box.id)
    edited = False
    original_bbox = None
    original_label = None
    if original is not None and (not _bbox_equal(original.bbox, box.bbox) or original.label != box.label):
        edited = True
        original_bbox = original.bbox
        original_label = original.label
    return CurrentBoxView(**box.model_dump(), edited=edited, original_bbox=original_bbox, original_label=original_label)


def get_current_annotations(inspection_id: str) -> list[CurrentImageAnnotationsView]:
    """Every uploaded image, each with its current box list (empty if
    nothing's ever been imported or hand-drawn for it yet) — joined against
    the real manifest so an image with no annotations at all still appears
    and can have a box hand-drawn on it."""
    manifest = load_manifest(inspection_id)
    current_state = _load_current_state(inspection_id)
    imported_by_image = _imported_boxes_by_image(inspection_id)

    views = []
    for stored in manifest:
        entry = current_state.get(stored.image_id)
        boxes = entry.boxes if entry is not None else []
        imported_lookup = imported_by_image.get(stored.image_id, {})
        views.append(
            CurrentImageAnnotationsView(
                image_id=stored.image_id,
                filename=stored.filename,
                boxes=[_with_provenance(b, imported_lookup) for b in boxes],
            )
        )
    return views


def seed_current_from_import(inspection_id: str, result: AnnotationImportResult) -> None:
    """Called once, right after a successful import. Per-image merge, not
    a whole-file overwrite: only the images present in this import's
    matched_images get their current-state entry replaced with fresh
    origin=imported boxes — every other image's existing current-state
    (including any review/approve/edit work already done on it) is left
    untouched. (Re-importing for an image that's *already* been reviewed
    in current-state still discards that image's review state — the same
    "latest import wins" behavior annotations_imported.json already has;
    a known, pre-existing limitation, not newly introduced here.)"""
    state = _load_current_state(inspection_id)
    for img in result.matched_images:
        state[img.image_id] = CurrentImageAnnotations(
            image_id=img.image_id,
            filename=img.filename,
            boxes=[
                CurrentBox(
                    id=box.id,
                    bbox=box.bbox,
                    label=box.label,
                    status=box.status,
                    origin=AnnotationOrigin.IMPORTED,
                    source_format=box.source_format,
                    valid=box.valid,
                    issue=box.issue,
                )
                for box in img.boxes
            ],
        )
    _save_current_state(inspection_id, state)


def replace_current_boxes_for_image(
    inspection_id: str, stored: StoredImage, boxes_input: list[CurrentBoxInput]
) -> CurrentImageAnnotationsView:
    """The manual editor's save path — covers add/move/resize/delete/
    relabel in one call, matching the frontend's existing full-replace
    convention (a box id absent from boxes_input is simply dropped, i.e.
    deleted). Re-validates every box's geometry against this image's real
    pixel dimensions (the client already clamps, but the server is the
    actual source of truth). Demotes an already-approved box back to
    human_verified if its geometry/label changed — otherwise a stale
    approval would stay attached to geometry nobody ever reviewed."""
    state = _load_current_state(inspection_id)
    existing_entry = state.get(stored.image_id)
    existing_by_id = {b.id: b for b in existing_entry.boxes} if existing_entry else {}
    imported_lookup = _imported_boxes_by_image(inspection_id).get(stored.image_id, {})

    next_boxes: list[CurrentBox] = []
    for box_input in boxes_input:
        existing = existing_by_id.get(box_input.id)
        imported = imported_lookup.get(box_input.id)

        raw = RawBox(
            x=box_input.bbox.x, y=box_input.bbox.y, width=box_input.bbox.width,
            height=box_input.bbox.height, label=box_input.label,
        )
        issue = validate_box(raw, stored.width, stored.height)
        is_valid = issue is None

        if existing is not None:
            origin = existing.origin
            status = existing.status
            source_format = existing.source_format
            if status == AnnotationStatus.APPROVED_FOR_TRAINING and (
                not _bbox_equal(existing.bbox, box_input.bbox) or existing.label != box_input.label
            ):
                status = AnnotationStatus.HUMAN_VERIFIED
        elif imported is not None:
            # Defensive fallback: current-state normally already has an
            # entry for any imported box (seeded at import time), so this
            # only matters if current-state was lost/reset independently.
            origin = AnnotationOrigin.IMPORTED
            status = imported.status
            source_format = imported.source_format
        else:
            origin = AnnotationOrigin.HUMAN_ADDED
            # A human just drew this, right now — HUMAN_VERIFIED immediately,
            # *unless* the geometry is actually invalid (the editor clamps
            # draws to stay in-bounds, so this only happens via a direct API
            # call bypassing the UI). An invalid box can't be considered
            # verified — falls back to IMPORTED_NOT_REVIEWED as the generic
            # "not reviewed yet" bucket (the label reads a little oddly for
            # a hand-drawn box in this edge case, but keeps "invalid boxes
            # can't be human_verified/approved" enforced uniformly).
            status = AnnotationStatus.HUMAN_VERIFIED if is_valid else AnnotationStatus.IMPORTED_NOT_REVIEWED
            source_format = None

        next_boxes.append(
            CurrentBox(
                id=box_input.id,
                bbox=box_input.bbox,
                label=box_input.label,
                status=status,
                origin=origin,
                source_format=source_format,
                valid=is_valid,
                issue=issue,
            )
        )

    state[stored.image_id] = CurrentImageAnnotations(
        image_id=stored.image_id, filename=stored.filename, boxes=next_boxes
    )
    _save_current_state(inspection_id, state)

    return CurrentImageAnnotationsView(
        image_id=stored.image_id,
        filename=stored.filename,
        boxes=[_with_provenance(b, imported_lookup) for b in next_boxes],
    )


def update_box_status(
    inspection_id: str, image_id: str, box_id: str, new_status: AnnotationStatus
) -> CurrentBoxView:
    state = _load_current_state(inspection_id)
    entry = state.get(image_id)
    if entry is None:
        raise KeyError(f"No annotation state for image {image_id!r}.")

    boxes = entry.boxes
    idx = next((i for i, b in enumerate(boxes) if b.id == box_id), None)
    if idx is None:
        raise KeyError(f"Box {box_id!r} not found on image {image_id!r}.")

    box = boxes[idx]
    allowed_next = _FORWARD_TRANSITIONS.get(box.status)
    if allowed_next != new_status:
        allowed_desc = allowed_next.value if allowed_next else "no further transition"
        raise AnnotationTransitionError(
            f"Cannot move box {box_id!r} from {box.status.value!r} to {new_status.value!r} "
            f"— only {allowed_desc!r} is allowed from {box.status.value!r}."
        )
    if not box.valid:
        raise AnnotationTransitionError(
            f"Cannot review/approve box {box_id!r} — it's flagged invalid ({box.issue}); "
            "fix its geometry first."
        )

    updated = box.model_copy(update={"status": new_status})
    boxes[idx] = updated
    state[image_id] = entry.model_copy(update={"boxes": boxes})
    _save_current_state(inspection_id, state)

    imported_lookup = _imported_boxes_by_image(inspection_id).get(image_id, {})
    return _with_provenance(updated, imported_lookup)


def get_approved_boxes_for_training(inspection_id: str) -> list[tuple[str, CurrentBox]]:
    """The one accessor a future training/export step should read from —
    filters to status == APPROVED_FOR_TRAINING only. No training pipeline
    in this codebase calls this yet (both /training and /analysis are
    still mock UI with no backend wiring at all); this function plus its
    own test is the mechanical guarantee that unapproved annotations can't
    reach training, pending that consumer actually being built."""
    state = _load_current_state(inspection_id)
    return [
        (image_id, box)
        for image_id, entry in state.items()
        for box in entry.boxes
        if box.status == AnnotationStatus.APPROVED_FOR_TRAINING
    ]
