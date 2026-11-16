"use client";

import { MousePointer2, Square, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

export type AnnotationTool = "select" | "box";

interface AnnotationToolbarProps {
  tool: AnnotationTool;
  onToolChange: (tool: AnnotationTool) => void;
  hasSelection: boolean;
  onDeleteSelected: () => void;
}

/**
 * Floating vertical tool strip over the image canvas, modeled on Roboflow's
 * left-edge annotation toolbar: a select/draw tool switch plus delete.
 */
export function AnnotationToolbar({ tool, onToolChange, hasSelection, onDeleteSelected }: AnnotationToolbarProps) {
  return (
    <div className="absolute left-2 top-1/2 flex -translate-y-1/2 flex-col items-center gap-1 rounded-lg border border-border bg-background/90 p-1 shadow-sm backdrop-blur">
      <ToggleGroup
        type="single"
        orientation="vertical"
        variant="outline"
        size="sm"
        value={tool}
        onValueChange={(value: string) => {
          if (value) onToolChange(value as AnnotationTool);
        }}
      >
        <Tooltip>
          <TooltipTrigger asChild>
            <ToggleGroupItem value="select" aria-label="Select and move tool">
              <MousePointer2 className="size-3.5" />
            </ToggleGroupItem>
          </TooltipTrigger>
          <TooltipContent side="right">Select / move / resize</TooltipContent>
        </Tooltip>
        <Tooltip>
          <TooltipTrigger asChild>
            <ToggleGroupItem value="box" aria-label="Draw box tool">
              <Square className="size-3.5" />
            </ToggleGroupItem>
          </TooltipTrigger>
          <TooltipContent side="right">Draw a new box</TooltipContent>
        </Tooltip>
      </ToggleGroup>

      <Separator className="my-0.5" />

      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant="ghost"
            size="icon-sm"
            aria-label="Delete selected box"
            disabled={!hasSelection}
            onClick={onDeleteSelected}
          >
            <Trash2 className="size-3.5" />
          </Button>
        </TooltipTrigger>
        <TooltipContent side="right">Delete selected box</TooltipContent>
      </Tooltip>
    </div>
  );
}
