"""FastAPI app for the Microtask 2 bolt-inspection POC.

Deliberately minimal: no auth, no database, filesystem-backed storage. See
docs/ARCHITECTURE.md (frontend) and backend/README.md for how this fits the
four existing UI screens.
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .annotation_import import AnnotationImportError, import_annotations_batch
from .annotation_review import (
    AnnotationTransitionError,
    get_current_annotations,
    replace_current_boxes_for_image,
    seed_current_from_import,
    update_box_status,
)
from .config import EXPERIMENTS_ROOT
from .models import (
    AnnotationImportResult,
    CurrentBoxInput,
    CurrentBoxView,
    CurrentImageAnnotationsView,
    ImageResult,
    InspectionSpec,
    StatusUpdateRequest,
)
from .pipeline import process_image
from .spec import interpret_requirement
from .storage import (
    UploadValidationError,
    load_manifest,
    load_parsed_annotations,
    resolve_image_path,
    save_image,
)

app = FastAPI(title="Visual Inspector POC Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/inspections/{inspection_id}/requirement")
def post_requirement(inspection_id: str, requirement_text: str) -> InspectionSpec:
    return interpret_requirement(requirement_text)


@app.post("/inspections/{inspection_id}/images")
async def upload_images(inspection_id: str, files: list[UploadFile]) -> dict:
    stored = []
    errors = []
    for f in files:
        data = await f.read()
        try:
            img = save_image(
                inspection_id=inspection_id,
                filename=f.filename or "upload",
                content_type=f.content_type or "application/octet-stream",
                data=data,
            )
            stored.append(img)
        except UploadValidationError as exc:
            errors.append({"filename": f.filename, "error": str(exc)})
    return {"stored": stored, "errors": errors}


@app.get("/inspections/{inspection_id}/images")
def list_images(inspection_id: str) -> list:
    return load_manifest(inspection_id)


@app.get("/inspections/{inspection_id}/images/{image_id}/file")
def get_image_file(inspection_id: str, image_id: str) -> FileResponse:
    path = resolve_image_path(inspection_id, image_id)
    if path is None or not path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(path)


@app.post("/inspections/{inspection_id}/images/{image_id}/infer")
def infer_image(inspection_id: str, image_id: str) -> ImageResult:
    """Runs the real (non-demo) detect -> color-check -> verdict pipeline
    on one already-uploaded image. Only runs when explicitly called here —
    never automatically, and never as a side effect of upload or annotation
    import. Uses whichever model app/detection.py is currently configured
    for (bolt_detector_v1.pt as of Microtask 2.2) — a small research model
    with known, documented reliability limits (see
    docs/MICROTASK_2_2_FINDINGS.md), not a production detector."""
    path = resolve_image_path(inspection_id, image_id)
    if path is None or not path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    stored = next((s for s in load_manifest(inspection_id) if s.image_id == image_id), None)
    filename = stored.filename if stored else image_id
    return process_image(image_id, filename, path)


@app.post("/inspections/{inspection_id}/annotations/import")
async def import_annotations_endpoint(
    inspection_id: str, files: list[UploadFile]
) -> AnnotationImportResult:
    """Imports one or more annotation JSON files (COCO, LabelMe, or custom
    format — may be mixed), matching boxes to already-uploaded images by
    filename. Accepts multiple files in one call because LabelMe's own
    convention is one JSON per image. Never runs detection, never marks
    boxes approved — see app/annotation_import.py."""
    payload = [(f.filename or "annotations.json", await f.read()) for f in files]
    try:
        result = import_annotations_batch(inspection_id, payload)
    except AnnotationImportError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    seed_current_from_import(inspection_id, result)
    return result


@app.get("/inspections/{inspection_id}/annotations")
def get_annotations(inspection_id: str) -> AnnotationImportResult | None:
    raw = load_parsed_annotations(inspection_id)
    if raw is None:
        return None
    return AnnotationImportResult.model_validate_json(raw)


@app.get("/inspections/{inspection_id}/annotations/current")
def get_current_annotations_endpoint(inspection_id: str) -> list[CurrentImageAnnotationsView]:
    """The live/editable annotation state (Microtask 3.2) — every uploaded
    image, each with its current boxes (empty if none yet). This is the
    Annotation screen's real data source once anything's been imported or
    hand-edited; GET .../annotations above stays as the original-import
    audit record, untouched by edits."""
    return get_current_annotations(inspection_id)


@app.put("/inspections/{inspection_id}/annotations/current/{image_id}")
def put_current_annotations_endpoint(
    inspection_id: str, image_id: str, boxes: list[CurrentBoxInput]
) -> CurrentImageAnnotationsView:
    """Replaces one image's full box list — covers add/move/resize/delete/
    relabel in a single call (a box id absent from the payload is deleted).
    Never changes `status` (CurrentBoxInput has no such field) — only
    PATCH .../status below can do that."""
    stored = next((s for s in load_manifest(inspection_id) if s.image_id == image_id), None)
    if stored is None:
        raise HTTPException(status_code=404, detail="Image not found")
    return replace_current_boxes_for_image(inspection_id, stored, boxes)


@app.patch("/inspections/{inspection_id}/annotations/current/{image_id}/boxes/{box_id}/status")
def patch_box_status_endpoint(
    inspection_id: str, image_id: str, box_id: str, body: StatusUpdateRequest
) -> CurrentBoxView:
    """The only way a box's review/approval status ever changes. Enforces
    a forward-only state machine (not_reviewed -> human_verified ->
    approved_for_training) — see annotation_review.py's
    _FORWARD_TRANSITIONS for why skipping straight to approved is always
    rejected."""
    try:
        return update_box_status(inspection_id, image_id, box_id, body.status)
    except AnnotationTransitionError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
