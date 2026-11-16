"""Shared Pydantic schemas for the bolt-inspection POC.

Mirrors (a subset of) the frontend's src/lib/types.ts conventions: these are
the types real pipeline output will be shaped as, once Step 6 wires the UI to
this backend.
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class FeasibilityLevel(str, Enum):
    FEASIBLE = "feasible"
    NEEDS_INFO = "needs_info"
    NOT_FEASIBLE = "not_feasible"


class CheckOperation(str, Enum):
    DETECT = "detect"
    COUNT = "count"
    COLOR_MARK_CHECK = "color_mark_check"


class InspectionCheck(BaseModel):
    id: str
    title: str
    operation: CheckOperation
    method: str
    applies_to: Optional[str] = Field(
        default=None, description="Which prior check's detections this one evaluates, if any."
    )


class FeasibilityResult(BaseModel):
    level: FeasibilityLevel
    reasons: list[str]
    limitations: list[str]
    missing_information: list[str] = Field(default_factory=list)


class InspectionSpec(BaseModel):
    requirement_text: str
    target_object: str
    checks: list[InspectionCheck]
    feasibility: FeasibilityResult


class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSED = "processed"
    FAILED = "failed"


class BoltVerdict(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    REVIEW = "review"
    NOT_PROCESSED = "not_processed"


class BoundingBox(BaseModel):
    x: float
    y: float
    width: float
    height: float


class BoltResult(BaseModel):
    bolt_id: str
    bbox: BoundingBox
    detection_confidence: float
    marking_yellow_fraction: Optional[float] = None
    verdict: BoltVerdict
    evidence: str


class ImageResult(BaseModel):
    image_id: str
    filename: str
    status: ProcessingStatus
    error: Optional[str] = None
    bolts: list[BoltResult] = Field(default_factory=list)
    detection_quality: str = "ok"  # "ok" | "review" | "not_processed", see app/validation.py
    guard_reason: Optional[str] = None


class AnnotationStatus(str, Enum):
    """Review-provenance state for an annotation box — a separate axis from
    BoltVerdict (which is the inspection pass/fail judgement). Imported
    annotations must never silently become APPROVED_FOR_TRAINING; that
    transition is a future, explicit human action (Microtask 3.2+).
    """

    IMPORTED_NOT_REVIEWED = "imported_not_reviewed"
    AI_GENERATED_NOT_REVIEWED = "ai_generated_not_reviewed"
    HUMAN_VERIFIED = "human_verified"
    APPROVED_FOR_TRAINING = "approved_for_training"


class AnnotationFormat(str, Enum):
    COCO = "coco"
    LABELME = "labelme"
    SUPERVISELY = "supervisely"
    CUSTOM = "custom"


class ImportedBox(BaseModel):
    # default_factory (not a bare required field) matters concretely: real,
    # already-on-disk annotations_imported.json from before this field
    # existed must keep loading via model_validate_json rather than raising
    # a validation error — it backfills a non-stable-across-reparses but
    # non-crashing id for that one pre-existing case; every box imported
    # from this point on gets a genuinely stable id.
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    bbox: BoundingBox
    label: Optional[str] = None
    status: AnnotationStatus = AnnotationStatus.IMPORTED_NOT_REVIEWED
    source_format: AnnotationFormat
    valid: bool = True
    issue: Optional[str] = None  # set when valid=False, e.g. "negative width"


class ImageAnnotations(BaseModel):
    image_id: str
    filename: str
    boxes: list[ImportedBox] = Field(default_factory=list)


class FileImportError(BaseModel):
    filename: str
    error: str


class AnnotationImportResult(BaseModel):
    """Result of importing one or more annotation JSON files in a single
    call. Plural fields because LabelMe's own convention is one JSON file
    per image — a real import may be many files at once, not just one."""

    detected_formats: list[AnnotationFormat] = Field(default_factory=list)
    original_files_saved_as: list[str] = Field(default_factory=list)
    matched_images: list[ImageAnnotations] = Field(default_factory=list)
    unmatched_filenames: list[str] = Field(
        default_factory=list, description="Filenames referenced in the JSON with no matching uploaded image."
    )
    invalid_box_count: int = 0
    total_box_count: int = 0
    file_errors: list[FileImportError] = Field(
        default_factory=list, description="Individual files that failed to parse; the rest of the batch still imports."
    )


class InspectionSummary(BaseModel):
    total_images: int
    processed_images: int
    failed_images: int
    total_bolts_detected: int
    pass_count: int
    fail_count: int
    review_count: int
    not_processed_count: int
    overall_result: BoltVerdict


class AnnotationOrigin(str, Enum):
    """How a box in the *current* (editable) annotation state came to
    exist — separate from AnnotationStatus (review state) and
    source_format (file format). No AI_GENERATED value yet: real detection
    isn't wired into this screen (see docs/MICROTASK_2_2_FINDINGS.md)."""

    IMPORTED = "imported"
    HUMAN_ADDED = "human_added"


class CurrentBox(BaseModel):
    """One box in the live/editable annotation state (Microtask 3.2),
    persisted in annotations_current.json. No snapshot of "what it used to
    look like" is stored here — annotations_imported.json never changes
    once written, so the same `id` can always be diffed against it live;
    see annotation_review.py's provenance function."""

    id: str
    bbox: BoundingBox
    label: Optional[str] = None
    status: AnnotationStatus = AnnotationStatus.IMPORTED_NOT_REVIEWED
    origin: AnnotationOrigin
    source_format: Optional[AnnotationFormat] = None
    valid: bool = True
    issue: Optional[str] = None


class CurrentBoxView(CurrentBox):
    """CurrentBox plus provenance fields computed at read time by diffing
    against the immutable original-import record — never stored on disk."""

    edited: bool = False
    original_bbox: Optional[BoundingBox] = None
    original_label: Optional[str] = None


class CurrentImageAnnotations(BaseModel):
    """On-disk shape for one image's entry in annotations_current.json."""

    image_id: str
    filename: str
    boxes: list[CurrentBox] = Field(default_factory=list)


class CurrentImageAnnotationsView(BaseModel):
    """API response shape — same as CurrentImageAnnotations but with
    provenance-annotated boxes."""

    image_id: str
    filename: str
    boxes: list[CurrentBoxView] = Field(default_factory=list)


class CurrentBoxInput(BaseModel):
    """PUT payload shape for replacing one image's box list. Deliberately
    has no `status` field — status only ever changes through the dedicated
    PATCH .../status endpoint's forward state machine, so a client can't
    smuggle an approval through an edit call."""

    id: str
    bbox: BoundingBox
    label: Optional[str] = None


class StatusUpdateRequest(BaseModel):
    status: AnnotationStatus
