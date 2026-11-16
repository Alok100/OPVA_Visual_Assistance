/**
 * Thin fetch wrappers for the FastAPI backend (backend/app/main.py). Plain
 * fetch, no HTTP client library — nothing here justifies one yet per
 * CLAUDE.md's "don't reach for a library until a real need shows up."
 *
 * The backend is a separate local process (see backend/README-equivalent:
 * `uvicorn app.main:app --reload`, default port 8000). If it isn't running,
 * calls here throw ApiError/TypeError and callers fall back to the existing
 * demo experience rather than crash — see isNetworkError().
 */

import type {
  AnnotationImportResult,
  AnnotationStatus,
  CurrentBoxInput,
  CurrentBoxView,
  CurrentImageAnnotations,
  ImageResult,
  InspectionSpec,
  StoredImage,
} from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

/** True for a network-level failure (backend unreachable), not an HTTP error response. */
export function isNetworkError(err: unknown): boolean {
  return err instanceof TypeError;
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body?.detail === "string" ? body.detail : JSON.stringify(body);
    } catch {
      // response wasn't JSON; keep statusText
    }
    throw new ApiError(res.status, detail);
  }
  return (await res.json()) as T;
}

/**
 * Real deterministic requirement interpretation (app/spec.py) — keyword
 * matching for the one known bolt/color-marking pattern, not a general NL
 * planner (see CLAUDE.md). requirement_text is a query param on the
 * backend (plain `str` function arg, not a Pydantic body), not JSON.
 */
export async function interpretRequirement(
  inspectionId: string,
  requirementText: string,
): Promise<InspectionSpec> {
  const url = new URL(`${API_BASE_URL}/inspections/${encodeURIComponent(inspectionId)}/requirement`);
  url.searchParams.set("requirement_text", requirementText);
  const res = await fetch(url.toString(), { method: "POST" });
  return handleResponse<InspectionSpec>(res);
}

export interface UploadImagesResponse {
  stored: StoredImage[];
  errors: { filename: string | null; error: string }[];
}

export async function uploadImages(inspectionId: string, files: File[]): Promise<UploadImagesResponse> {
  const form = new FormData();
  files.forEach((file) => form.append("files", file));
  const res = await fetch(`${API_BASE_URL}/inspections/${encodeURIComponent(inspectionId)}/images`, {
    method: "POST",
    body: form,
  });
  return handleResponse<UploadImagesResponse>(res);
}

export async function listImages(inspectionId: string): Promise<StoredImage[]> {
  const res = await fetch(`${API_BASE_URL}/inspections/${encodeURIComponent(inspectionId)}/images`);
  return handleResponse<StoredImage[]>(res);
}

export function imageFileUrl(inspectionId: string, imageId: string): string {
  return `${API_BASE_URL}/inspections/${encodeURIComponent(inspectionId)}/images/${encodeURIComponent(imageId)}/file`;
}

/**
 * Accepts multiple files because LabelMe's own convention is one JSON file
 * per image — importing annotations for N images may mean N files, not
 * one. COCO/custom files (one file covering many images) just pass a
 * single-element array.
 */
export async function importAnnotations(
  inspectionId: string,
  files: File[],
): Promise<AnnotationImportResult> {
  const form = new FormData();
  files.forEach((file) => form.append("files", file));
  const res = await fetch(
    `${API_BASE_URL}/inspections/${encodeURIComponent(inspectionId)}/annotations/import`,
    { method: "POST", body: form },
  );
  return handleResponse<AnnotationImportResult>(res);
}

export async function getAnnotations(inspectionId: string): Promise<AnnotationImportResult | null> {
  const res = await fetch(`${API_BASE_URL}/inspections/${encodeURIComponent(inspectionId)}/annotations`);
  return handleResponse<AnnotationImportResult | null>(res);
}

/**
 * Microtask 3.2 — the live/editable annotation state. Distinct from
 * getAnnotations above, which stays the immutable original-import record.
 */
export async function getCurrentAnnotations(inspectionId: string): Promise<CurrentImageAnnotations[]> {
  const res = await fetch(`${API_BASE_URL}/inspections/${encodeURIComponent(inspectionId)}/annotations/current`);
  return handleResponse<CurrentImageAnnotations[]>(res);
}

/**
 * Replaces one image's full box list — add/move/resize/delete/relabel all
 * go through this one call (a box id absent from `boxes` is deleted
 * server-side). Never changes status; see updateAnnotationStatus.
 */
export async function updateCurrentAnnotations(
  inspectionId: string,
  imageId: string,
  boxes: CurrentBoxInput[],
): Promise<CurrentImageAnnotations> {
  const res = await fetch(
    `${API_BASE_URL}/inspections/${encodeURIComponent(inspectionId)}/annotations/current/${encodeURIComponent(imageId)}`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(boxes),
    },
  );
  return handleResponse<CurrentImageAnnotations>(res);
}

/**
 * The only way a box's review/approval status changes — enforces a
 * forward-only state machine server-side (see annotation_review.py); a
 * 422 here means an illegal transition (e.g. skipping straight to
 * approved), not a network failure.
 */
export async function updateAnnotationStatus(
  inspectionId: string,
  imageId: string,
  boxId: string,
  status: AnnotationStatus,
): Promise<CurrentBoxView> {
  const res = await fetch(
    `${API_BASE_URL}/inspections/${encodeURIComponent(inspectionId)}/annotations/current/${encodeURIComponent(imageId)}/boxes/${encodeURIComponent(boxId)}/status`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    },
  );
  return handleResponse<CurrentBoxView>(res);
}

/**
 * Runs the real detect -> color-check -> verdict pipeline on one already-
 * uploaded image. Only ever called from the explicit "Run inference" action
 * on the inference-testing page — never automatically.
 */
export async function runInference(inspectionId: string, imageId: string): Promise<ImageResult> {
  const res = await fetch(
    `${API_BASE_URL}/inspections/${encodeURIComponent(inspectionId)}/images/${encodeURIComponent(imageId)}/infer`,
    { method: "POST" },
  );
  return handleResponse<ImageResult>(res);
}
