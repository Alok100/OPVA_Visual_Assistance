/**
 * View-model for the Annotation screen, shared by annotation-canvas.tsx,
 * annotation-side-panel.tsx and image-filmstrip.tsx. The page decides
 * whether to build this from real backend data (uploaded images + imported
 * annotations) or the existing demo data, so the rendering components stay
 * pure — they don't know or care which source they're showing.
 */

import type { AnnotationFormat, AnnotationOrigin, AnnotationStatus } from "@/lib/types";

export interface ViewImage {
  id: string;
  filename: string;
  /** Real image URL (backend file endpoint) or undefined for the demo
   * gradient-placeholder look. */
  url?: string;
  /** Real pixel dimensions, used to render boxes at the correct aspect
   * ratio and to convert pixel boxes to on-screen percentages. Undefined
   * for demo images (which use a fixed 16:9 placeholder). */
  width?: number;
  height?: number;
  /** Demo-only CSS gradient tone — ignored when url is set. */
  tone?: "steel" | "copper" | "slate";
}

export interface ViewBox {
  id: string;
  /** Pixel coordinates when the image has real width/height, otherwise
   * percent-of-image (0-100) to match the existing demo convention. */
  x: number;
  y: number;
  width: number;
  height: number;
  label: string;
  color: string;
  confidence?: number;
  status?: AnnotationStatus;
  /** False for an imported box that failed validation (e.g. negative
   * coordinates) — still shown, but visually flagged, never silently
   * dropped. */
  valid?: boolean;
  issue?: string | null;
  /** Microtask 3.2 — present only for real (non-demo) boxes backed by the
   * persisted current-annotations state. */
  origin?: AnnotationOrigin;
  sourceFormat?: AnnotationFormat | null;
  /** True when this box's bbox/label differs from the original import
   * record, computed server-side at read time (see annotation_review.py). */
  edited?: boolean;
  originalLabel?: string | null;
  originalBbox?: { x: number; y: number; width: number; height: number } | null;
}

export const ANNOTATION_STATUS_LABEL: Record<AnnotationStatus, string> = {
  imported_not_reviewed: "Imported · not reviewed",
  ai_generated_not_reviewed: "AI-generated · not reviewed",
  human_verified: "Human-verified",
  approved_for_training: "Approved for training",
};

/** The next legal status in the forward-only review/approve chain, or
 * null when there isn't one (already approved, or no status at all —
 * e.g. demo boxes, which have no status and so no review UI appears for
 * them, no special-casing needed). Mirrors backend/app/annotation_review.py's
 * _FORWARD_TRANSITIONS — kept in sync by hand since this is a small,
 * stable rule, not generated from the backend. */
export function nextReviewStatus(status?: AnnotationStatus): AnnotationStatus | null {
  if (status === "imported_not_reviewed" || status === "ai_generated_not_reviewed") return "human_verified";
  if (status === "human_verified") return "approved_for_training";
  return null;
}

export const REVIEW_ACTION_LABEL: Record<AnnotationStatus, string> = {
  imported_not_reviewed: "Mark reviewed",
  ai_generated_not_reviewed: "Mark reviewed",
  human_verified: "Approve for training",
  approved_for_training: "", // no next action — nextReviewStatus returns null, button is omitted
};

/** Deterministic color per label string, for imported annotations whose
 * label set isn't known ahead of time (unlike the fixed demo ANNOTATION_LABELS). */
const LABEL_COLORS = ["#2563eb", "#10b981", "#f59e0b", "#dc2626", "#7c3aed", "#0891b2"];

export function colorForLabel(label: string): string {
  let hash = 0;
  for (let i = 0; i < label.length; i++) hash = (hash * 31 + label.charCodeAt(i)) >>> 0;
  return LABEL_COLORS[hash % LABEL_COLORS.length];
}
