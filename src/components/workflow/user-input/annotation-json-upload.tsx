"use client";

import { useRef, useState } from "react";
import { FileJson, UploadCloud, CheckCircle2, AlertTriangle, Loader2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import type { AnnotationImportResult } from "@/lib/types";

interface AnnotationJsonUploadProps {
  disabled: boolean;
  onUpload: (files: File[]) => Promise<AnnotationImportResult>;
}

export function AnnotationJsonUpload({ disabled, onUpload }: AnnotationJsonUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [fileNames, setFileNames] = useState<string[]>([]);
  const [status, setStatus] = useState<"idle" | "loading" | "done" | "error">("idle");
  const [result, setResult] = useState<AnnotationImportResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleFiles(files: File[]) {
    setFileNames(files.map((f) => f.name));
    setStatus("loading");
    setError(null);
    setResult(null);
    try {
      const imported = await onUpload(files);
      setResult(imported);
      setStatus("done");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Import failed.");
      setStatus("error");
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Import annotation JSON</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-xs text-muted-foreground">
          Optional — COCO or custom-format JSON covers many images in one file; LabelMe exports
          one file per image, so you can select several at once. Boxes are matched to images by
          filename and imported as{" "}
          <span className="font-medium text-foreground">not yet reviewed</span>; nothing is
          auto-approved for training.
        </p>

        <div
          className="flex flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed border-border bg-muted/30 px-6 py-6 text-center aria-disabled:opacity-50"
          aria-disabled={disabled}
        >
          <FileJson className="size-6 text-muted-foreground" strokeWidth={1.5} />
          <p className="text-sm font-medium text-foreground">
            {disabled ? "Upload images first" : "Choose one or more annotation JSON files"}
          </p>
          <Button
            variant="outline"
            size="sm"
            disabled={disabled}
            onClick={() => inputRef.current?.click()}
          >
            <UploadCloud className="size-4" />
            Browse
          </Button>
          <input
            ref={inputRef}
            type="file"
            accept="application/json,.json"
            multiple
            className="hidden"
            disabled={disabled}
            onChange={(e) => {
              const files = e.target.files ? Array.from(e.target.files) : [];
              if (files.length > 0) void handleFiles(files);
              e.target.value = "";
            }}
          />
        </div>

        {status === "loading" && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="size-4 animate-spin" />
            Importing {fileNames.length} file{fileNames.length === 1 ? "" : "s"}…
          </div>
        )}

        {status === "error" && (
          <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2.5 text-sm text-red-700">
            <AlertTriangle className="mt-0.5 size-4 shrink-0" />
            <span>
              Could not import {fileNames.length === 1 ? `"${fileNames[0]}"` : `${fileNames.length} files`}:{" "}
              {error}
            </span>
          </div>
        )}

        {status === "done" && result && (
          <div className="space-y-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2.5 text-sm text-emerald-800">
            <div className="flex items-center gap-2 font-medium">
              <CheckCircle2 className="size-4 shrink-0" />
              {fileNames.length} file{fileNames.length === 1 ? "" : "s"} imported
              {result.detected_formats.length > 0 &&
                ` as ${result.detected_formats.map((f) => f.toUpperCase()).join(" + ")}`}
            </div>
            <ul className="space-y-0.5 pl-6 text-xs text-emerald-800/90">
              <li>
                {result.matched_images.length} image{result.matched_images.length === 1 ? "" : "s"}{" "}
                matched, {result.total_box_count} box{result.total_box_count === 1 ? "" : "es"} total
                {result.invalid_box_count > 0 && ` (${result.invalid_box_count} flagged invalid)`}
              </li>
              {result.unmatched_filenames.length > 0 && (
                <li className="text-amber-700">
                  {result.unmatched_filenames.length} filename
                  {result.unmatched_filenames.length === 1 ? "" : "s"} in the JSON didn&apos;t match any
                  uploaded image: {result.unmatched_filenames.join(", ")}
                </li>
              )}
              {result.file_errors.length > 0 && (
                <li className="text-red-700">
                  {result.file_errors.length} file{result.file_errors.length === 1 ? "" : "s"} failed to
                  parse and were skipped:{" "}
                  {result.file_errors.map((e) => `${e.filename} (${e.error})`).join("; ")}
                </li>
              )}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
