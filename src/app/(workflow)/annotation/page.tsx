"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight } from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";
import { ImageFilmstrip } from "@/components/workflow/annotation/image-filmstrip";
import { AnnotationCanvas } from "@/components/workflow/annotation/annotation-canvas";
import { AnnotationSidePanel } from "@/components/workflow/annotation/annotation-side-panel";
import type { AnnotationTool } from "@/components/workflow/annotation/annotation-toolbar";
import { colorForLabel, type ViewBox, type ViewImage } from "@/components/workflow/annotation/view-model";
import { ANNOTATION_LABELS, DEMO_ANNOTATIONS, DEMO_IMAGES } from "@/lib/mock-data";
import { useInspection } from "@/lib/inspection-context";
import {
  getCurrentAnnotations,
  imageFileUrl,
  listImages,
  updateAnnotationStatus,
  updateCurrentAnnotations,
} from "@/lib/api-client";
import type { AnnotationStatus, CurrentBoxInput, CurrentBoxView, CurrentImageAnnotations, StoredImage } from "@/lib/types";

type LoadState = "loading" | "ready" | "unreachable";
type SaveState = "idle" | "saving" | "saved" | "error";

const SAVE_DEBOUNCE_MS = 500;

function toViewBox(b: CurrentBoxView): ViewBox {
  return {
    id: b.id,
    x: b.bbox.x,
    y: b.bbox.y,
    width: b.bbox.width,
    height: b.bbox.height,
    label: b.label ?? "object",
    color: colorForLabel(b.label ?? "object"),
    status: b.status,
    valid: b.valid,
    issue: b.issue,
    origin: b.origin,
    sourceFormat: b.source_format,
    edited: b.edited,
    originalLabel: b.original_label,
    originalBbox: b.original_bbox,
  };
}

export default function AnnotationPage() {
  const router = useRouter();
  const { inspection, spec } = useInspection();
  const [activeIndex, setActiveIndex] = useState(0);
  const [showSuggestions, setShowSuggestions] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [tool, setTool] = useState<AnnotationTool>("select");
  const [selectedBoxId, setSelectedBoxId] = useState<string | null>(null);
  const [optimisticBoxesByImageId, setOptimisticBoxesByImageId] = useState<Record<string, ViewBox[]>>({});
  const [saveStateByImageId, setSaveStateByImageId] = useState<Record<string, SaveState>>({});

  const [realImages, setRealImages] = useState<StoredImage[]>([]);
  const [currentAnnotations, setCurrentAnnotations] = useState<CurrentImageAnnotations[]>([]);
  const [loadState, setLoadState] = useState<LoadState>("loading");

  const pendingSaveRef = useRef<{ imageId: string; boxes: ViewBox[] } | null>(null);
  const saveTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isMountedRef = useRef(true);

  useEffect(() => {
    let cancelled = false;
    Promise.all([listImages(inspection.id), getCurrentAnnotations(inspection.id)])
      .then(([images, current]) => {
        if (cancelled) return;
        setRealImages(images);
        setCurrentAnnotations(current);
        setLoadState("ready");
      })
      .catch(() => {
        if (!cancelled) setLoadState("unreachable");
      });
    return () => {
      cancelled = true;
    };
  }, [inspection.id]);

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      flushSave();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const usingRealData = loadState === "ready" && realImages.length > 0;

  const viewImages: ViewImage[] = useMemo(() => {
    if (usingRealData) {
      return realImages.map((img) => ({
        id: img.image_id,
        filename: img.filename,
        url: imageFileUrl(inspection.id, img.image_id),
        width: img.width,
        height: img.height,
      }));
    }
    return DEMO_IMAGES.map((img) => ({ id: img.id, filename: img.filename, tone: img.tone }));
  }, [usingRealData, realImages, inspection.id]);

  const boundedIndex = Math.min(activeIndex, Math.max(viewImages.length - 1, 0));
  const activeImage = viewImages[boundedIndex] as ViewImage | undefined;

  const boxesByImageId = useMemo(() => {
    const map = new Map<string, ViewBox[]>();
    for (const img of currentAnnotations) {
      map.set(img.image_id, img.boxes.map(toViewBox));
    }
    return map;
  }, [currentAnnotations]);

  const demoBoxes: ViewBox[] = useMemo(
    () =>
      DEMO_ANNOTATIONS.map((box) => {
        const label = ANNOTATION_LABELS.find((l) => l.id === box.labelId);
        return {
          id: box.id,
          x: box.x,
          y: box.y,
          width: box.width,
          height: box.height,
          label: label?.name.split(" ")[0] ?? "object",
          color: label?.color ?? "#2563eb",
          confidence: box.confidence,
        };
      }),
    [],
  );

  // Known classes for the label dropdown — grown from whatever's actually
  // been used in this inspection (imported + hand-drawn), seeded with the
  // confirmed requirement's target object so the very first box already
  // offers something more useful than a generic placeholder. Not derived
  // from a fixed project-wide class list, since none exists in this app.
  const knownLabels = useMemo(() => {
    const labels = new Set<string>();
    if (spec && spec.target_object && spec.target_object !== "unknown") {
      labels.add(spec.target_object);
    }
    if (usingRealData) {
      for (const boxes of boxesByImageId.values()) {
        for (const b of boxes) if (b.label) labels.add(b.label);
      }
      for (const boxes of Object.values(optimisticBoxesByImageId)) {
        for (const b of boxes) if (b.label) labels.add(b.label);
      }
    } else {
      for (const l of ANNOTATION_LABELS) labels.add(l.name.split(" ")[0]);
    }
    return Array.from(labels).sort();
  }, [spec, usingRealData, boxesByImageId, optimisticBoxesByImageId]);

  const baseBoxes = usingRealData && activeImage ? (boxesByImageId.get(activeImage.id) ?? []) : demoBoxes;
  const activeBoxes = activeImage ? (optimisticBoxesByImageId[activeImage.id] ?? baseBoxes) : [];
  const hasImportedAnyAnnotations = currentAnnotations.some((img) => img.boxes.some((b) => b.origin === "imported"));
  const saveState: SaveState = usingRealData && activeImage ? (saveStateByImageId[activeImage.id] ?? "idle") : "idle";

  function flushSave() {
    const pending = pendingSaveRef.current;
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
      saveTimeoutRef.current = null;
    }
    if (!pending) return;
    pendingSaveRef.current = null;

    const { imageId, boxes } = pending;
    const payload: CurrentBoxInput[] = boxes.map((b) => ({
      id: b.id,
      bbox: { x: b.x, y: b.y, width: b.width, height: b.height },
      label: b.label || null,
    }));

    updateCurrentAnnotations(inspection.id, imageId, payload)
      .then((result) => {
        if (!isMountedRef.current) return;
        setCurrentAnnotations((prev) => prev.map((img) => (img.image_id === imageId ? result : img)));
        setOptimisticBoxesByImageId((prev) => {
          const next = { ...prev };
          delete next[imageId];
          return next;
        });
        setSaveStateByImageId((prev) => ({ ...prev, [imageId]: "saved" }));
      })
      .catch(() => {
        if (!isMountedRef.current) return;
        // Keep the optimistic edit rather than silently dropping it — the
        // user's change is still visible, just flagged as not persisted.
        setSaveStateByImageId((prev) => ({ ...prev, [imageId]: "error" }));
      });
  }

  function selectImage(next: number) {
    flushSave();
    setActiveIndex(next);
    setSelectedBoxId(null);
  }
  function goPrev() {
    selectImage(activeIndex === 0 ? viewImages.length - 1 : activeIndex - 1);
  }
  function goNext() {
    selectImage(activeIndex === viewImages.length - 1 ? 0 : activeIndex + 1);
  }
  function toggleEditing() {
    flushSave();
    setIsEditing((v) => !v);
    setSelectedBoxId(null);
    setTool("select");
  }
  function handleBoxesChange(nextBoxes: ViewBox[]) {
    if (!activeImage) return;
    setOptimisticBoxesByImageId((prev) => ({ ...prev, [activeImage.id]: nextBoxes }));
    if (!usingRealData) return; // demo boxes stay local-only, same as before — nothing to persist

    pendingSaveRef.current = { imageId: activeImage.id, boxes: nextBoxes };
    setSaveStateByImageId((prev) => ({ ...prev, [activeImage.id]: "saving" }));
    if (saveTimeoutRef.current) clearTimeout(saveTimeoutRef.current);
    saveTimeoutRef.current = setTimeout(flushSave, SAVE_DEBOUNCE_MS);
  }
  function handleRelabelBox(id: string, label: string) {
    handleBoxesChange(activeBoxes.map((b) => (b.id === id ? { ...b, label, color: colorForLabel(label || "object") } : b)));
  }
  function handleDeleteBox(id: string) {
    handleBoxesChange(activeBoxes.filter((b) => b.id !== id));
    if (selectedBoxId === id) setSelectedBoxId(null);
  }
  function handleStatusChange(boxId: string, nextStatus: AnnotationStatus) {
    if (!activeImage || !usingRealData) return;
    flushSave(); // commit any in-flight geometry edit first, so we don't race it
    const previous = optimisticBoxesByImageId[activeImage.id];

    updateAnnotationStatus(inspection.id, activeImage.id, boxId, nextStatus)
      .then((updated) => {
        if (!isMountedRef.current) return;
        setCurrentAnnotations((prev) =>
          prev.map((img) =>
            img.image_id !== activeImage.id
              ? img
              : { ...img, boxes: img.boxes.map((b) => (b.id === boxId ? updated : b)) },
          ),
        );
        setOptimisticBoxesByImageId((prev) => {
          const current = prev[activeImage.id];
          if (!current) return prev;
          return { ...prev, [activeImage.id]: current.map((b) => (b.id === boxId ? toViewBox(updated) : b)) };
        });
      })
      .catch(() => {
        // Illegal transition (e.g. skip-to-approved) or network error —
        // nothing was changed optimistically for status, so there's
        // nothing to revert; previous is unused but kept for clarity.
        void previous;
      });
  }

  const sourceTag = !usingRealData ? { label: "Example images", demo: true } : annotationSourceTag(activeBoxes);

  return (
    <div className="space-y-6">
      <PageHeader
        title="AI-Assisted Annotation"
        description="Review imported or example bounding boxes, then move on to dataset readiness."
      />

      {loadState === "loading" && <p className="text-xs text-muted-foreground">Loading images…</p>}
      {!usingRealData && loadState !== "loading" && (
        <p className="text-xs text-muted-foreground">
          {loadState === "unreachable"
            ? "Could not reach the backend — showing a fixed example image set instead."
            : "No images uploaded yet for this inspection — showing a fixed example image set, not the files from the previous screen."}
        </p>
      )}
      {usingRealData && !hasImportedAnyAnnotations && (
        <p className="text-xs text-muted-foreground">
          {realImages.length} image{realImages.length === 1 ? "" : "s"} uploaded, no annotation JSON
          imported yet — go back to User Input to import one, or draw boxes by hand below.
        </p>
      )}

      {activeImage && (
        <>
          <ImageFilmstrip images={viewImages} activeIndex={boundedIndex} onSelect={selectImage} />

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_320px]">
            <AnnotationCanvas
              image={activeImage}
              boxes={activeBoxes}
              index={boundedIndex}
              total={viewImages.length}
              showSuggestions={showSuggestions}
              sourceTag={sourceTag}
              onPrev={goPrev}
              onNext={goNext}
              isEditing={isEditing}
              onToggleEditing={toggleEditing}
              saveState={saveState}
              tool={tool}
              onToolChange={setTool}
              selectedBoxId={selectedBoxId}
              onSelectBox={setSelectedBoxId}
              onBoxesChange={handleBoxesChange}
              defaultLabel={knownLabels[0]}
            />
            <AnnotationSidePanel
              boxes={activeBoxes}
              showSuggestions={showSuggestions}
              onToggleSuggestions={setShowSuggestions}
              isEditing={isEditing}
              selectedBoxId={selectedBoxId}
              onSelectBox={setSelectedBoxId}
              onRelabelBox={handleRelabelBox}
              onDeleteBox={handleDeleteBox}
              onChangeStatus={usingRealData ? handleStatusChange : undefined}
              persisted={usingRealData}
              knownLabels={knownLabels}
            />
          </div>
        </>
      )}

      <div className="flex flex-col items-start gap-2 rounded-xl border border-border bg-card p-4 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-muted-foreground">
          {usingRealData
            ? "Imported or hand-drawn annotations are shown as saved and have not necessarily been reviewed yet. Proceed to review dataset readiness."
            : "Annotations shown are illustrative. Proceed to review dataset readiness."}
        </p>
        <Button
          onClick={() => {
            flushSave();
            router.push("/analysis");
          }}
        >
          Continue to Analysis
          <ArrowRight className="size-4" />
        </Button>
      </div>
    </div>
  );
}

/** Per-image source label: distinct imported formats among this image's
 * boxes, or a hand-drawn/none fallback. Computed from the active image's
 * own boxes (not a single inspection-wide value) since different images
 * can have been imported at different times/formats. */
function annotationSourceTag(boxes: ViewBox[]): { label: string; demo: boolean } {
  if (boxes.length === 0) {
    return { label: "Uploaded — no annotations imported", demo: false };
  }
  const importedFormats = Array.from(
    new Set(boxes.filter((b) => b.origin === "imported" && b.sourceFormat).map((b) => b.sourceFormat as string)),
  );
  if (importedFormats.length === 0) {
    return { label: "Hand-drawn annotations — not imported", demo: false };
  }
  return { label: `Imported (${importedFormats.map((f) => f.toUpperCase()).join(" + ")})`, demo: false };
}
