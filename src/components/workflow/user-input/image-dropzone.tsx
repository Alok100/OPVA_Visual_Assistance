"use client";

import { useRef, useState, type DragEvent } from "react";
import { UploadCloud, X, ImageIcon, AlertTriangle, Loader2, CheckCircle2 } from "lucide-react";
import { Card, CardAction, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { DemoDataTag } from "@/components/shared/demo-data-tag";
import { cn } from "cn";

export type UploadStatus = "uploading" | "uploaded" | "error";

export interface UploadedImage {
  id: string;
  name: string;
  previewUrl?: string;
  isDemo: boolean;
  /** Backend image_id once the upload succeeds — absent for demo images and
   * while a real upload is still in flight. */
  backendImageId?: string;
  uploadStatus?: UploadStatus;
  uploadError?: string;
}

interface ImageDropzoneProps {
  images: UploadedImage[];
  onAddFiles: (files: FileList) => void;
  onLoadDemo: () => void;
  onRemove: (id: string) => void;
  error?: string | null;
  onDismissError?: () => void;
}

export function ImageDropzone({
  images,
  onAddFiles,
  onLoadDemo,
  onRemove,
  error,
  onDismissError,
}: ImageDropzoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragActive, setDragActive] = useState(false);

  function handleDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragActive(false);
    if (e.dataTransfer.files?.length) onAddFiles(e.dataTransfer.files);
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Upload inspection images</CardTitle>
        <CardAction>
          <span className="text-xs text-muted-foreground">{images.length} uploaded</span>
        </CardAction>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && (
          <div className="flex items-start justify-between gap-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2.5 text-sm text-red-700">
            <span className="flex items-start gap-2">
              <AlertTriangle className="mt-0.5 size-4 shrink-0" />
              {error}
            </span>
            <button
              type="button"
              onClick={onDismissError}
              aria-label="Dismiss"
              className="shrink-0 text-red-700/70 hover:text-red-700"
            >
              <X className="size-4" />
            </button>
          </div>
        )}
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragActive(true);
          }}
          onDragLeave={() => setDragActive(false)}
          onDrop={handleDrop}
          className={cn(
            "flex flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed px-6 py-10 text-center transition-colors",
            dragActive ? "border-primary bg-accent" : "border-border bg-muted/30",
          )}
        >
          <UploadCloud className="size-7 text-muted-foreground" strokeWidth={1.5} />
          <p className="text-sm font-medium text-foreground">Drag &amp; drop images here</p>
          <p className="text-xs text-muted-foreground">or</p>
          <div className="flex flex-wrap items-center justify-center gap-2">
            <Button variant="outline" size="sm" onClick={() => inputRef.current?.click()}>
              Browse Files
            </Button>
            <Button variant="ghost" size="sm" onClick={onLoadDemo}>
              Use example images
            </Button>
          </div>
          <input
            ref={inputRef}
            type="file"
            accept="image/*"
            multiple
            className="hidden"
            onChange={(e) => e.target.files && onAddFiles(e.target.files)}
          />
        </div>

        {images.length > 0 && (
          <div className="grid grid-cols-3 gap-3 sm:grid-cols-4 md:grid-cols-6">
            {images.map((img) => (
              <div
                key={img.id}
                className="group relative aspect-square overflow-hidden rounded-lg border border-border bg-muted"
              >
                {img.previewUrl ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={img.previewUrl} alt={img.name} className="h-full w-full object-cover" />
                ) : (
                  <div className="flex h-full w-full flex-col items-center justify-center gap-1 bg-gradient-to-br from-slate-200 to-slate-300 text-slate-600">
                    <ImageIcon className="size-4 opacity-60" />
                    <span className="px-1 text-center text-[9px] font-medium leading-tight opacity-80">
                      {img.name}
                    </span>
                  </div>
                )}
                {img.isDemo && (
                  <span className="absolute left-1 top-1">
                    <DemoDataTag label="Demo" className="px-1.5 py-0 text-[9px]" />
                  </span>
                )}
                {!img.isDemo && img.uploadStatus && (
                  <span
                    className={cn(
                      "absolute left-1 top-1 flex items-center gap-1 rounded px-1.5 py-0.5 text-[9px] font-medium text-white",
                      img.uploadStatus === "uploading" && "bg-foreground/60",
                      img.uploadStatus === "uploaded" && "bg-emerald-600/90",
                      img.uploadStatus === "error" && "bg-red-600/90",
                    )}
                    title={img.uploadStatus === "error" ? img.uploadError : undefined}
                  >
                    {img.uploadStatus === "uploading" && <Loader2 className="size-2.5 animate-spin" />}
                    {img.uploadStatus === "uploaded" && <CheckCircle2 className="size-2.5" />}
                    {img.uploadStatus === "error" && <AlertTriangle className="size-2.5" />}
                    {img.uploadStatus === "uploading"
                      ? "Uploading"
                      : img.uploadStatus === "uploaded"
                        ? "Uploaded"
                        : "Failed"}
                  </span>
                )}
                <button
                  type="button"
                  onClick={() => onRemove(img.id)}
                  aria-label={`Remove ${img.name}`}
                  className="absolute right-1 top-1 flex size-5 items-center justify-center rounded-full bg-foreground/60 text-background opacity-0 transition-opacity group-hover:opacity-100"
                >
                  <X className="size-3" />
                </button>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
