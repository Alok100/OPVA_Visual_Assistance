"use client";

import { useEffect, useRef, useState } from "react";
import { ChevronLeft, ChevronRight, ImageIcon, AlertTriangle, Pencil, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { DemoDataTag } from "@/components/shared/demo-data-tag";
import { StatusBadge } from "@/components/shared/status-badge";
import { colorForLabel, type ViewBox, type ViewImage } from "./view-model";
import { AnnotationToolbar, type AnnotationTool } from "./annotation-toolbar";
import { HANDLES, boxFromDrag, isDrawnBoxSignificant, moveBox, resizeBox, type HandleId, type PercentBox } from "./edit-geometry";
import { cn } from "cn";

const TONE_GRADIENT: Record<NonNullable<ViewImage["tone"]>, string> = {
  steel: "from-slate-300 to-slate-500",
  copper: "from-orange-200 to-orange-400",
  slate: "from-zinc-300 to-zinc-500",
};

interface AnnotationCanvasProps {
  image: ViewImage;
  boxes: ViewBox[];
  index: number;
  total: number;
  showSuggestions: boolean;
  sourceTag: { label: string; demo: boolean };
  onPrev: () => void;
  onNext: () => void;
  /** Manual editing is opt-in per screen — the inference-testing screen reviews
   * real model output read-only and doesn't pass any of these. */
  isEditing?: boolean;
  onToggleEditing?: () => void;
  /** "idle" (nothing to report), "saving"/"saved"/"error" — Microtask 3.2
   * real persistence. Demo-mode editing stays "idle" forever (nothing is
   * ever actually saved there), matching the no-fake-success rule. */
  saveState?: "idle" | "saving" | "saved" | "error";
  tool?: AnnotationTool;
  onToolChange?: (tool: AnnotationTool) => void;
  selectedBoxId?: string | null;
  onSelectBox?: (id: string | null) => void;
  onBoxesChange?: (boxes: ViewBox[]) => void;
  /** Label assigned to a freshly drawn box — the inspection's known/target
   * class when one exists, so drawing a box doesn't require immediately
   * retyping a generic placeholder. Falls back to "object". */
  defaultLabel?: string;
}

type DragState =
  | { mode: "draw"; startX: number; startY: number }
  | { mode: "move"; boxId: string; startClientX: number; startClientY: number; startBox: PercentBox }
  | { mode: "resize"; boxId: string; handle: HandleId; startClientX: number; startClientY: number; startBox: PercentBox };

export function AnnotationCanvas({
  image,
  boxes,
  index,
  total,
  showSuggestions,
  sourceTag,
  onPrev,
  onNext,
  isEditing = false,
  onToggleEditing,
  saveState = "idle",
  tool = "select",
  onToolChange = () => {},
  selectedBoxId = null,
  onSelectBox = () => {},
  onBoxesChange = () => {},
  defaultLabel = "object",
}: AnnotationCanvasProps) {
  const editingEnabled = !!onToggleEditing;
  const containerRef = useRef<HTMLDivElement>(null);
  const dragRef = useRef<DragState | null>(null);
  const [draftBox, setDraftBox] = useState<PercentBox | null>(null);
  // Mirrors of props/state read by the document-level pointer listeners below,
  // kept current every render so the mount-once effect never closes over stale values.
  const liveRef = useRef({ boxes, image, tool, isEditing, onBoxesChange, onSelectBox, onToolChange, defaultLabel });
  useEffect(() => {
    liveRef.current = { boxes, image, tool, isEditing, onBoxesChange, onSelectBox, onToolChange, defaultLabel };
  }, [boxes, image, tool, isEditing, onBoxesChange, onSelectBox, onToolChange, defaultLabel]);

  // Boxes carry pixel coordinates when the image has known real dimensions
  // (converted to on-screen percent here); demo boxes are already percent.
  const toPercent = (box: ViewBox | PercentBox) => {
    if (image.width && image.height) {
      return {
        x: (box.x / image.width) * 100,
        y: (box.y / image.height) * 100,
        width: (box.width / image.width) * 100,
        height: (box.height / image.height) * 100,
      };
    }
    return { x: box.x, y: box.y, width: box.width, height: box.height };
  };

  const fromPercent = (pct: PercentBox) => {
    if (image.width && image.height) {
      return {
        x: (pct.x / 100) * image.width,
        y: (pct.y / 100) * image.height,
        width: (pct.width / 100) * image.width,
        height: (pct.height / 100) * image.height,
      };
    }
    return pct;
  };

  const getPercentPoint = (clientX: number, clientY: number) => {
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return { x: 0, y: 0 };
    return {
      x: Math.min(Math.max(((clientX - rect.left) / rect.width) * 100, 0), 100),
      y: Math.min(Math.max(((clientY - rect.top) / rect.height) * 100, 0), 100),
    };
  };

  useEffect(() => {
    function handlePointerMove(e: PointerEvent) {
      const drag = dragRef.current;
      if (!drag) return;
      const { onBoxesChange, boxes } = liveRef.current;

      if (drag.mode === "draw") {
        const point = getPercentPoint(e.clientX, e.clientY);
        setDraftBox(boxFromDrag(drag.startX, drag.startY, point.x, point.y));
        return;
      }

      const rect = containerRef.current?.getBoundingClientRect();
      if (!rect) return;
      const dx = ((e.clientX - drag.startClientX) / rect.width) * 100;
      const dy = ((e.clientY - drag.startClientY) / rect.height) * 100;

      const nextPercent =
        drag.mode === "move" ? moveBox(drag.startBox, dx, dy) : resizeBox(drag.startBox, drag.handle, dx, dy);
      const nextNative = fromPercent(nextPercent);
      onBoxesChange(boxes.map((b) => (b.id === drag.boxId ? { ...b, ...nextNative } : b)));
    }

    function handlePointerUp() {
      const drag = dragRef.current;
      if (!drag) return;
      if (drag.mode === "draw") {
        setDraftBox((current) => {
          if (current && isDrawnBoxSignificant(current)) {
            const { boxes, onBoxesChange, onSelectBox, onToolChange, defaultLabel } = liveRef.current;
            const native = fromPercent(current);
            const newBox: ViewBox = {
              id: crypto.randomUUID(),
              ...native,
              label: defaultLabel,
              color: colorForLabel(defaultLabel),
            };
            onBoxesChange([...boxes, newBox]);
            onSelectBox(newBox.id);
            onToolChange("select");
          }
          return null;
        });
      }
      dragRef.current = null;
    }

    document.addEventListener("pointermove", handlePointerMove);
    document.addEventListener("pointerup", handlePointerUp);
    return () => {
      document.removeEventListener("pointermove", handlePointerMove);
      document.removeEventListener("pointerup", handlePointerUp);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!isEditing) return;
    function handleKeyDown(e: KeyboardEvent) {
      const activeTag = document.activeElement?.tagName;
      const isTyping = activeTag === "INPUT" || activeTag === "TEXTAREA";

      if (e.key === "Escape") {
        if (dragRef.current?.mode === "draw") {
          dragRef.current = null;
          setDraftBox(null);
        } else {
          onSelectBox(null);
        }
        return;
      }

      if ((e.key === "Delete" || e.key === "Backspace") && selectedBoxId && !isTyping) {
        onBoxesChange(boxes.filter((b) => b.id !== selectedBoxId));
        onSelectBox(null);
      }
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isEditing, selectedBoxId, boxes, onBoxesChange, onSelectBox]);

  function handleContainerPointerDown(e: React.PointerEvent) {
    if (!isEditing) return;
    if (tool !== "box") {
      onSelectBox(null);
      return;
    }
    const point = getPercentPoint(e.clientX, e.clientY);
    dragRef.current = { mode: "draw", startX: point.x, startY: point.y };
    setDraftBox({ x: point.x, y: point.y, width: 0, height: 0 });
  }

  function handleBoxPointerDown(e: React.PointerEvent, box: ViewBox) {
    if (!isEditing || tool !== "select") return;
    e.stopPropagation();
    onSelectBox(box.id);
    dragRef.current = {
      mode: "move",
      boxId: box.id,
      startClientX: e.clientX,
      startClientY: e.clientY,
      startBox: toPercent(box),
    };
  }

  function handleHandlePointerDown(e: React.PointerEvent, box: ViewBox, handle: HandleId) {
    e.stopPropagation();
    dragRef.current = {
      mode: "resize",
      boxId: box.id,
      handle,
      startClientX: e.clientX,
      startClientY: e.clientY,
      startBox: toPercent(box),
    };
  }

  // Real images keep their natural aspect ratio (our photos are portrait or
  // landscape, not 16:9) so percent-positioned boxes land correctly; demo
  // images fall back to the original fixed 16:9 placeholder look.
  const aspectStyle = image.width && image.height ? { aspectRatio: `${image.width} / ${image.height}` } : undefined;
  const boxesVisible = showSuggestions || isEditing;

  return (
    <div className="space-y-3">
      <div
        ref={containerRef}
        onPointerDown={handleContainerPointerDown}
        className={cn(
          "relative w-full touch-none overflow-hidden rounded-xl border border-border bg-gradient-to-br",
          !image.url && !aspectStyle && "aspect-video",
          !image.url && image.tone && TONE_GRADIENT[image.tone],
          isEditing && tool === "box" && "cursor-crosshair",
        )}
        style={aspectStyle}
      >
        {image.url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={image.url}
            alt={image.filename}
            draggable={false}
            className="h-full w-full object-contain bg-muted"
          />
        ) : (
          <div className="absolute inset-0 flex items-center justify-center">
            <ImageIcon className="size-10 text-white/50" strokeWidth={1.2} />
          </div>
        )}

        {boxesVisible &&
          boxes.map((box) => {
            const pct = toPercent(box);
            const selected = isEditing && tool === "select" && box.id === selectedBoxId;
            return (
              <div
                key={box.id}
                onPointerDown={(e) => handleBoxPointerDown(e, box)}
                className={cn(
                  "absolute rounded-sm border-2",
                  selected && "ring-2 ring-offset-1 ring-primary",
                  isEditing && tool === "select" && "cursor-move",
                )}
                style={{
                  left: `${pct.x}%`,
                  top: `${pct.y}%`,
                  width: `${pct.width}%`,
                  height: `${pct.height}%`,
                  borderColor: box.valid === false ? "#dc2626" : box.color,
                  borderStyle: box.valid === false ? "dashed" : "solid",
                }}
                title={box.valid === false ? (box.issue ?? "Invalid box") : undefined}
              >
                <span
                  className="absolute -top-5 left-0 flex items-center gap-1 whitespace-nowrap rounded px-1.5 py-0.5 text-[10px] font-medium text-white"
                  style={{ backgroundColor: box.valid === false ? "#dc2626" : box.color }}
                >
                  {box.valid === false && <AlertTriangle className="size-2.5" />}
                  {box.label}
                  {typeof box.confidence === "number" && ` · ${Math.round(box.confidence * 100)}%`}
                </span>

                {selected &&
                  HANDLES.map((h) => (
                    <div
                      key={h.id}
                      onPointerDown={(e) => handleHandlePointerDown(e, box, h.id)}
                      className={cn(
                        "absolute size-2.5 -translate-x-1/2 -translate-y-1/2 rounded-sm border border-primary bg-white",
                        h.cursor,
                      )}
                      style={{ left: h.style.left, top: h.style.top }}
                    />
                  ))}
              </div>
            );
          })}

        {draftBox && (
          <div
            className="absolute rounded-sm border-2 border-dashed border-primary bg-primary/10"
            style={{
              left: `${draftBox.x}%`,
              top: `${draftBox.y}%`,
              width: `${draftBox.width}%`,
              height: `${draftBox.height}%`,
            }}
          />
        )}

        {isEditing && <AnnotationToolbar tool={tool} onToolChange={onToolChange} hasSelection={!!selectedBoxId} onDeleteSelected={() => {
          if (!selectedBoxId) return;
          onBoxesChange(boxes.filter((b) => b.id !== selectedBoxId));
          onSelectBox(null);
        }} />}

        <div className="absolute left-3 top-3">
          {sourceTag.demo ? (
            <DemoDataTag label={sourceTag.label} />
          ) : (
            <StatusBadge tone="info" icon={false} className="bg-white/90">
              {sourceTag.label}
            </StatusBadge>
          )}
        </div>

        <div className="absolute bottom-3 right-3 rounded-full bg-foreground/60 px-2.5 py-1 text-xs font-medium text-background">
          Image {index + 1} of {total}
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex min-w-0 items-center gap-2">
          <p className="min-w-0 truncate text-sm text-muted-foreground">{image.filename}</p>
          {saveState === "saving" && <StatusBadge tone="info">Saving…</StatusBadge>}
          {saveState === "saved" && <StatusBadge tone="success">Saved</StatusBadge>}
          {saveState === "error" && <StatusBadge tone="danger">Save failed — edit kept locally</StatusBadge>}
        </div>
        <div className="flex shrink-0 items-center gap-1.5">
          {editingEnabled && (
            <Button variant={isEditing ? "default" : "outline"} size="sm" onClick={onToggleEditing}>
              {isEditing ? <Check className="size-4" /> : <Pencil className="size-4" />}
              {isEditing ? "Done editing" : "Edit annotations"}
            </Button>
          )}
          <Button variant="outline" size="icon" onClick={onPrev} aria-label="Previous image">
            <ChevronLeft className="size-4" />
          </Button>
          <Button variant="outline" size="icon" onClick={onNext} aria-label="Next image">
            <ChevronRight className="size-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
