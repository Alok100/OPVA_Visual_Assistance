/**
 * Shared domain types for the Visual Inspector UI prototype.
 * Values that model future AI/backend output are explicitly marked as demo data
 * at the point of use — see docs/PRODUCT_SCOPE.md for current phase boundaries.
 */

export type WorkflowStageId = "input" | "annotation" | "analysis" | "training";

export interface WorkflowStageMeta {
  id: WorkflowStageId;
  step: number;
  label: string;
  href: string;
  description: string;
}

export type InspectionStatus = "draft" | "in_review" | "ready";

export interface Inspection {
  id: string;
  name: string;
  factory: string;
  requirementText: string;
  status: InspectionStatus;
  imageCount: number;
  lastUpdated: string;
}

export interface AnnotationLabel {
  id: string;
  name: string;
  color: string;
  shape: "box" | "polygon" | "text";
}

export interface DemoAnnotationBox {
  id: string;
  labelId: string;
  x: number;
  y: number;
  width: number;
  height: number;
  confidence: number;
}

export interface DemoImage {
  id: string;
  filename: string;
  tone: "steel" | "copper" | "slate";
}

export interface DatasetIssue {
  id: string;
  severity: "low" | "medium" | "high";
  title: string;
  recommendation: string;
}

export type TrainingRunState = "idle" | "running" | "completed";

/**
 * Types mirroring backend/app/models.py and backend/app/storage.py — the
 * real (non-demo) shapes returned by the FastAPI backend. See
 * src/lib/api-client.ts for the calls that produce these.
 */

export interface StoredImage {
  image_id: string;
  filename: string;
  stored_path: string;
  content_type: string;
  size_bytes: number;
  width: number;
  height: number;
  sha256: string;
}

export interface BackendBoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export type AnnotationStatus =
  | "imported_not_reviewed"
  | "ai_generated_not_reviewed"
  | "human_verified"
  | "approved_for_training";

export type AnnotationFormat = "coco" | "labelme" | "supervisely" | "custom";

export interface ImportedBox {
  id: string;
  bbox: BackendBoundingBox;
  label: string | null;
  status: AnnotationStatus;
  source_format: AnnotationFormat;
  valid: boolean;
  issue: string | null;
}

export interface ImageAnnotations {
  image_id: string;
  filename: string;
  boxes: ImportedBox[];
}

/**
 * Microtask 3.2 — the live/editable annotation state, mirroring
 * backend/app/models.py's CurrentBox family and AnnotationOrigin. Distinct
 * from ImportedBox/ImageAnnotations above, which stay the immutable
 * original-import record.
 */
export type AnnotationOrigin = "imported" | "human_added";

export interface CurrentBox {
  id: string;
  bbox: BackendBoundingBox;
  label: string | null;
  status: AnnotationStatus;
  origin: AnnotationOrigin;
  source_format: AnnotationFormat | null;
  valid: boolean;
  issue: string | null;
}

/** CurrentBox plus provenance computed server-side at read time by
 * diffing against the immutable import record — never stored. */
export interface CurrentBoxView extends CurrentBox {
  edited: boolean;
  original_bbox: BackendBoundingBox | null;
  original_label: string | null;
}

export interface CurrentImageAnnotations {
  image_id: string;
  filename: string;
  boxes: CurrentBoxView[];
}

/** PUT payload shape — deliberately has no `status` field; status only
 * ever changes through the dedicated PATCH .../status call. */
export interface CurrentBoxInput {
  id: string;
  bbox: BackendBoundingBox;
  label: string | null;
}

export interface FileImportError {
  filename: string;
  error: string;
}

export type RequirementFeasibilityLevel = "feasible" | "needs_info" | "not_feasible";
export type CheckOperation = "detect" | "count" | "color_mark_check";

export interface InspectionCheck {
  id: string;
  title: string;
  operation: CheckOperation;
  method: string;
  applies_to: string | null;
}

export interface RequirementFeasibility {
  level: RequirementFeasibilityLevel;
  reasons: string[];
  limitations: string[];
  missing_information: string[];
}

export interface InspectionSpec {
  requirement_text: string;
  target_object: string;
  checks: InspectionCheck[];
  feasibility: RequirementFeasibility;
}

export type ProcessingStatus = "pending" | "processed" | "failed";
export type BoltVerdict = "pass" | "fail" | "review" | "not_processed";

export interface BoltResult {
  bolt_id: string;
  bbox: BackendBoundingBox;
  detection_confidence: number;
  marking_yellow_fraction: number | null;
  verdict: BoltVerdict;
  evidence: string;
}

export interface ImageResult {
  image_id: string;
  filename: string;
  status: ProcessingStatus;
  error: string | null;
  bolts: BoltResult[];
  detection_quality: "ok" | "review" | "not_processed";
  guard_reason: string | null;
}

export interface AnnotationImportResult {
  detected_formats: AnnotationFormat[];
  original_files_saved_as: string[];
  matched_images: ImageAnnotations[];
  unmatched_filenames: string[];
  invalid_box_count: number;
  total_box_count: number;
  file_errors: FileImportError[];
}
