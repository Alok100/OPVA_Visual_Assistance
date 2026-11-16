/**
 * DEMO DATA ONLY.
 * Nothing in this file is produced by a real model, pipeline, or backend —
 * this is the UI-only phase (see docs/PRODUCT_SCOPE.md). Every screen that
 * reads from here must visibly label the values as demo/illustrative.
 */

import type {
  AnnotationLabel,
  DatasetIssue,
  DemoAnnotationBox,
  DemoImage,
  Inspection,
  WorkflowStageMeta,
} from "./types";

export const WORKFLOW_STAGES: WorkflowStageMeta[] = [
  {
    id: "input",
    step: 1,
    label: "User Input",
    href: "/",
    description: "Describe the inspection in plain language",
  },
  {
    id: "annotation",
    step: 2,
    label: "AI Annotation",
    href: "/annotation",
    description: "Review AI-assisted bounding boxes and labels",
  },
  {
    id: "analysis",
    step: 3,
    label: "Analysis",
    href: "/analysis",
    description: "Check dataset quality and training readiness",
  },
  {
    id: "training",
    step: 4,
    label: "Training",
    href: "/training",
    description: "Train and evaluate the inspection model",
  },
];

export const EXAMPLE_INSPECTION: Inspection = {
  id: "insp-tractor-wheel",
  name: "Tractor Wheel Assembly Check",
  factory: "Plant A — Wheel Assembly Line 1",
  requirementText:
    "Detect every bolt and verify whether each bolt has the expected white line marking.",
  status: "draft",
  imageCount: 12,
  lastUpdated: "2026-10-28",
};

export const ANNOTATION_LABELS: AnnotationLabel[] = [
  { id: "label-bolt", name: "Bolt (bounding box)", color: "#2563eb", shape: "box" },
  { id: "label-mark", name: "Mark on bolt (region)", color: "#10b981", shape: "polygon" },
  { id: "label-missing", name: "Missing mark (flag)", color: "#dc2626", shape: "box" },
];

// Count kept in sync with EXAMPLE_INSPECTION.imageCount (12) so the sidebar's "Images" stat,
// the Analysis screen's stat cards, and this gallery never disagree with each other.
export const DEMO_IMAGES: DemoImage[] = [
  { id: "img-01", filename: "wheel_assembly_01.jpg", tone: "steel" },
  { id: "img-02", filename: "wheel_assembly_02.jpg", tone: "copper" },
  { id: "img-03", filename: "wheel_assembly_03.jpg", tone: "slate" },
  { id: "img-04", filename: "wheel_assembly_04.jpg", tone: "steel" },
  { id: "img-05", filename: "wheel_assembly_05.jpg", tone: "copper" },
  { id: "img-06", filename: "wheel_assembly_06.jpg", tone: "slate" },
  { id: "img-07", filename: "wheel_assembly_07.jpg", tone: "steel" },
  { id: "img-08", filename: "wheel_assembly_08.jpg", tone: "copper" },
  { id: "img-09", filename: "wheel_assembly_09.jpg", tone: "slate" },
  { id: "img-10", filename: "wheel_assembly_10.jpg", tone: "steel" },
  { id: "img-11", filename: "wheel_assembly_11.jpg", tone: "copper" },
  { id: "img-12", filename: "wheel_assembly_12.jpg", tone: "slate" },
];

export const DEMO_ANNOTATIONS: DemoAnnotationBox[] = [
  { id: "ann-1", labelId: "label-bolt", x: 18, y: 22, width: 12, height: 12, confidence: 0.97 },
  { id: "ann-2", labelId: "label-bolt", x: 54, y: 20, width: 12, height: 12, confidence: 0.95 },
  { id: "ann-3", labelId: "label-bolt", x: 68, y: 48, width: 12, height: 12, confidence: 0.93 },
  { id: "ann-4", labelId: "label-mark", x: 21, y: 30, width: 6, height: 3, confidence: 0.88 },
  { id: "ann-5", labelId: "label-missing", x: 34, y: 60, width: 12, height: 12, confidence: 0.81 },
];

export const DATASET_ISSUES: DatasetIssue[] = [
  {
    id: "issue-1",
    severity: "medium",
    title: "3 images have inconsistent lighting on the lower-left bolts",
    recommendation: "Recapture or add 4–6 more images from that angle before training.",
  },
  {
    id: "issue-2",
    severity: "low",
    title: "1 image is missing an annotated mark region",
    recommendation: "Review image wheel_assembly_06.jpg in the Annotation screen.",
  },
];
