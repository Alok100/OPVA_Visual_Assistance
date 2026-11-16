"use client";

import { useState } from "react";
import { History, Trash2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectSeparator, SelectTrigger, SelectValue } from "@/components/ui/select";
import { StatusBadge } from "@/components/shared/status-badge";
import { ANNOTATION_STATUS_LABEL, nextReviewStatus, REVIEW_ACTION_LABEL, type ViewBox } from "./view-model";
import type { AnnotationStatus } from "@/lib/types";
import { cn } from "cn";

const NEW_CLASS_VALUE = "__new_class__";

interface AnnotationSidePanelProps {
  boxes: ViewBox[];
  showSuggestions: boolean;
  onToggleSuggestions: (value: boolean) => void;
  isEditing?: boolean;
  selectedBoxId?: string | null;
  onSelectBox?: (id: string | null) => void;
  onRelabelBox?: (id: string, label: string) => void;
  onDeleteBox?: (id: string) => void;
  /** Microtask 3.2 — present only when boxes are real/persisted; omitted
   * entirely for demo data, which has no status to progress. */
  onChangeStatus?: (id: string, status: AnnotationStatus) => void;
  /** True when edits to these boxes are actually saved to the backend
   * (real data) rather than kept only in local page state (demo data) —
   * drives which caption is shown, never claims a save that isn't real. */
  persisted?: boolean;
  /** Classes already used in this inspection (imported + hand-drawn), plus
   * the confirmed requirement's target object when known — the relabel
   * control picks from this list instead of free-typing, so the user
   * doesn't have to retype the same class name on every box. */
  knownLabels?: string[];
}

export function AnnotationSidePanel({
  boxes,
  showSuggestions,
  onToggleSuggestions,
  isEditing = false,
  selectedBoxId = null,
  onSelectBox,
  onRelabelBox,
  onDeleteBox,
  onChangeStatus,
  persisted = false,
  knownLabels = [],
}: AnnotationSidePanelProps) {
  // Typing a brand-new class name is a deliberate escape hatch from the
  // dropdown (there's no fixed project-wide class list in this app) —
  // reset whenever the selected box changes (React's "adjust state during
  // render" pattern, not an effect) so a stale "adding" state can't leak
  // onto the next box.
  const [addingNewLabel, setAddingNewLabel] = useState(false);
  const [lastSelectedBoxId, setLastSelectedBoxId] = useState(selectedBoxId);
  if (selectedBoxId !== lastSelectedBoxId) {
    setLastSelectedBoxId(selectedBoxId);
    setAddingNewLabel(false);
  }
  const labelCounts = new Map<string, { count: number; color: string }>();
  for (const box of boxes) {
    const entry = labelCounts.get(box.label);
    if (entry) entry.count += 1;
    else labelCounts.set(box.label, { count: 1, color: box.color });
  }

  const invalidCount = boxes.filter((b) => b.valid === false).length;
  const confidences = boxes.filter((b) => typeof b.confidence === "number").map((b) => b.confidence as number);
  const avgConfidence =
    confidences.length > 0
      ? Math.round((confidences.reduce((sum, c) => sum + c, 0) / confidences.length) * 100)
      : null;

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Annotation tools</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <Label htmlFor="show-suggestions" className="text-sm font-normal text-muted-foreground">
              Show boxes
            </Label>
            <Switch id="show-suggestions" checked={showSuggestions} onCheckedChange={onToggleSuggestions} />
          </div>
          <div className="space-y-1.5">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Labels</p>
            {labelCounts.size === 0 && (
              <p className="text-sm text-muted-foreground">No boxes for this image.</p>
            )}
            {[...labelCounts.entries()].map(([label, info]) => (
              <div key={label} className="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-muted">
                <span className="size-2.5 shrink-0 rounded-full" style={{ backgroundColor: info.color }} />
                <span className="min-w-0 flex-1 truncate text-foreground">{label}</span>
                <span className="text-xs text-muted-foreground">{info.count}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {isEditing && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Boxes on this image</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1.5">
            {boxes.length === 0 && (
              <p className="text-sm text-muted-foreground">
                No boxes yet — use the draw tool on the image to add one.
              </p>
            )}
            {boxes.map((box) => {
              const selected = box.id === selectedBoxId;
              return (
                <div
                  key={box.id}
                  className={cn(
                    "flex items-center gap-2 rounded-md px-2 py-1.5 text-sm",
                    selected ? "bg-muted" : "hover:bg-muted/60",
                  )}
                >
                  <button
                    type="button"
                    aria-label={`Select box: ${box.label}`}
                    onClick={() => onSelectBox?.(selected ? null : box.id)}
                    className="size-2.5 shrink-0 rounded-full"
                    style={{ backgroundColor: box.color }}
                  />
                  {selected && addingNewLabel ? (
                    <Input
                      autoFocus
                      placeholder="New class name"
                      defaultValue=""
                      onBlur={(e) => {
                        const value = e.target.value.trim();
                        if (value) onRelabelBox?.(box.id, value);
                        setAddingNewLabel(false);
                      }}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") e.currentTarget.blur();
                        if (e.key === "Escape") setAddingNewLabel(false);
                      }}
                      className="h-7 min-w-0 flex-1 text-sm"
                      aria-label="New class name"
                    />
                  ) : selected ? (
                    <Select
                      value={box.label}
                      onValueChange={(value) => {
                        if (value === NEW_CLASS_VALUE) setAddingNewLabel(true);
                        else onRelabelBox?.(box.id, value);
                      }}
                    >
                      <SelectTrigger size="sm" className="h-7 min-w-0 flex-1" aria-label="Box class">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {Array.from(new Set([box.label, ...knownLabels])).map((label) => (
                          <SelectItem key={label} value={label}>
                            {label}
                          </SelectItem>
                        ))}
                        <SelectSeparator />
                        <SelectItem value={NEW_CLASS_VALUE}>+ New class…</SelectItem>
                      </SelectContent>
                    </Select>
                  ) : (
                    <button
                      type="button"
                      onClick={() => onSelectBox?.(box.id)}
                      className="min-w-0 flex-1 truncate text-left text-foreground"
                    >
                      {box.label}
                    </button>
                  )}
                  {box.edited && (
                    <span
                      className="shrink-0 text-muted-foreground"
                      title={`Originally imported as "${box.originalLabel ?? "object"}"${
                        box.originalBbox
                          ? ` at (${Math.round(box.originalBbox.x)}, ${Math.round(box.originalBbox.y)})`
                          : ""
                      }`}
                    >
                      <History className="size-3.5" aria-label="Corrected from the original import" />
                    </span>
                  )}
                  <Button
                    variant="ghost"
                    size="icon-xs"
                    aria-label={`Delete box: ${box.label}`}
                    onClick={() => onDeleteBox?.(box.id)}
                  >
                    <Trash2 className="size-3.5" />
                  </Button>
                </div>
              );
            })}
            <p className="pt-1 text-xs text-muted-foreground">
              {persisted
                ? "Edits save to the backend automatically a moment after you stop drawing."
                : "Edits are kept for this session only — not saved yet."}
            </p>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Annotation summary</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <dl className="grid grid-cols-2 gap-3 text-sm">
            <div className="rounded-lg border border-border p-2.5">
              <dt className="text-xs text-muted-foreground">Boxes on this image</dt>
              <dd className="text-lg font-semibold text-foreground">{boxes.length}</dd>
            </div>
            <div className="rounded-lg border border-border p-2.5">
              <dt className="text-xs text-muted-foreground">Avg. confidence</dt>
              <dd className="text-lg font-semibold text-foreground">
                {avgConfidence !== null ? `${avgConfidence}%` : "—"}
              </dd>
            </div>
          </dl>
          {invalidCount > 0 && (
            <div className="flex items-center justify-between rounded-lg bg-muted/50 px-3 py-2">
              <span className="text-sm text-foreground">Flagged invalid</span>
              <StatusBadge tone="danger">{invalidCount}</StatusBadge>
            </div>
          )}
          {boxes.some((b) => b.status) && (
            <div className="space-y-1.5 pt-1">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Review status
              </p>
              {boxes.map((box) => {
                const next = box.status ? nextReviewStatus(box.status) : null;
                return (
                  <div
                    key={box.id}
                    className="flex flex-col gap-1 rounded-md px-2 py-1 text-xs sm:flex-row sm:items-center sm:justify-between"
                  >
                    <span className="min-w-0 truncate text-muted-foreground">{box.label}</span>
                    <div className="flex shrink-0 items-center gap-1.5">
                      <span className="text-foreground">{box.status ? ANNOTATION_STATUS_LABEL[box.status] : "—"}</span>
                      {next && onChangeStatus && (
                        <Button
                          variant="outline"
                          size="xs"
                          disabled={box.valid === false}
                          title={box.valid === false ? "Fix this box's geometry before reviewing it" : undefined}
                          onClick={() => onChangeStatus(box.id, next)}
                        >
                          {box.status ? REVIEW_ACTION_LABEL[box.status] : ""}
                        </Button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
