"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ArrowRight } from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";
import { RequirementCard } from "@/components/workflow/user-input/requirement-card";
import { InterpretationCard } from "@/components/workflow/user-input/interpretation-card";
import { ImageDropzone, type UploadedImage } from "@/components/workflow/user-input/image-dropzone";
import { AnnotationJsonUpload } from "@/components/workflow/user-input/annotation-json-upload";
import { DEMO_IMAGES } from "@/lib/mock-data";
import { useInspection } from "@/lib/inspection-context";
import {
  imageFileUrl,
  importAnnotations,
  interpretRequirement,
  isNetworkError,
  listImages,
  uploadImages,
} from "@/lib/api-client";
export default function UserInputPage() {
  const router = useRouter();
  const { inspection, requirementConfirmed, confirmRequirement, spec, setSpec } = useInspection();
  const [analyzing, setAnalyzing] = useState(false);
  const [analyzeError, setAnalyzeError] = useState<string | null>(null);
  const [images, setImages] = useState<UploadedImage[]>([]);
  const [uploadError, setUploadError] = useState<string | null>(null);

  // Pick up images already uploaded to the backend for this inspection
  // (e.g. navigating back to this screen) so state survives navigation
  // without a frontend state library — the backend is the source of truth.
  useEffect(() => {
    let cancelled = false;
    listImages(inspection.id)
      .then((stored) => {
        if (cancelled || stored.length === 0) return;
        setImages((prev) =>
          prev.length > 0
            ? prev
            : stored.map((s) => ({
                id: s.image_id,
                name: s.filename,
                previewUrl: imageFileUrl(inspection.id, s.image_id),
                isDemo: false,
                backendImageId: s.image_id,
                uploadStatus: "uploaded" as const,
              })),
        );
      })
      .catch(() => {
        // Backend unreachable or no images yet — stay on the empty/demo state.
      });
    return () => {
      cancelled = true;
    };
  }, [inspection.id]);

  async function handleAnalyze() {
    setAnalyzing(true);
    setAnalyzeError(null);
    try {
      const result = await interpretRequirement(inspection.id, inspection.requirementText);
      setSpec(result);
      confirmRequirement();
    } catch (err) {
      setSpec(null);
      setAnalyzeError(
        isNetworkError(err)
          ? "Could not reach the backend — is it running on http://localhost:8000?"
          : err instanceof Error
            ? err.message
            : "Could not analyze the requirement.",
      );
    } finally {
      setAnalyzing(false);
    }
  }

  async function handleAddFiles(files: FileList) {
    const all = Array.from(files);
    const accepted = all.filter((file) => file.type.startsWith("image/"));
    const rejected = all.filter((file) => !file.type.startsWith("image/"));

    if (rejected.length > 0) {
      const names = rejected.map((f) => f.name).join(", ");
      setUploadError(
        rejected.length === 1
          ? `"${names}" isn't an image file and was skipped.`
          : `${rejected.length} files aren't image files and were skipped: ${names}`,
      );
    } else {
      setUploadError(null);
    }
    if (accepted.length === 0) return;

    const localIds = accepted.map(
      (file) => `${file.name}-${file.lastModified}-${Math.random().toString(36).slice(2, 8)}`,
    );
    const pending: UploadedImage[] = accepted.map((file, i) => ({
      id: localIds[i],
      name: file.name,
      previewUrl: URL.createObjectURL(file),
      isDemo: false,
      uploadStatus: "uploading",
    }));
    setImages((prev) => [...prev, ...pending]);

    try {
      const response = await uploadImages(inspection.id, accepted);
      setImages((prev) =>
        prev.map((img) => {
          const i = localIds.indexOf(img.id);
          if (i === -1) return img;
          const stored = response.stored.find((s) => s.filename === accepted[i].name);
          if (stored) {
            return { ...img, backendImageId: stored.image_id, uploadStatus: "uploaded" as const };
          }
          const failure = response.errors.find((e) => e.filename === accepted[i].name);
          return {
            ...img,
            uploadStatus: "error" as const,
            uploadError: failure?.error ?? "Upload failed.",
          };
        }),
      );
      if (response.errors.length > 0) {
        setUploadError(
          `${response.errors.length} file${response.errors.length === 1 ? "" : "s"} failed to upload: ` +
            response.errors.map((e) => `${e.filename ?? "unknown"} (${e.error})`).join("; "),
        );
      }
    } catch (err) {
      const message = isNetworkError(err)
        ? "Could not reach the backend — is it running on http://localhost:8000?"
        : err instanceof Error
          ? err.message
          : "Upload failed.";
      setImages((prev) =>
        prev.map((img) =>
          localIds.includes(img.id) ? { ...img, uploadStatus: "error" as const, uploadError: message } : img,
        ),
      );
      setUploadError(message);
    }
  }

  function handleLoadDemo() {
    const demo: UploadedImage[] = DEMO_IMAGES.map((img) => ({
      id: img.id,
      name: img.filename,
      isDemo: true,
    }));
    setImages(demo);
  }

  function handleRemove(id: string) {
    setImages((prev) => prev.filter((img) => img.id !== id));
  }

  const uploadedCount = images.filter((img) => !img.isDemo && img.uploadStatus === "uploaded").length;
  const canImportAnnotations = uploadedCount > 0;
  const canContinue = requirementConfirmed && images.length > 0;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Configure Your Inspection"
        description="Describe what to inspect in plain language, then upload the images you want analyzed."
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <RequirementCard analyzing={analyzing} onAnalyze={handleAnalyze} />
        <InterpretationCard analyzing={analyzing} spec={spec} error={analyzeError} />
      </div>

      <ImageDropzone
        images={images}
        onAddFiles={handleAddFiles}
        onLoadDemo={handleLoadDemo}
        onRemove={handleRemove}
        error={uploadError}
        onDismissError={() => setUploadError(null)}
      />

      <AnnotationJsonUpload
        disabled={!canImportAnnotations}
        onUpload={(files) => importAnnotations(inspection.id, files)}
      />

      <div className="flex flex-col items-start gap-2 rounded-xl border border-border bg-card p-4 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-muted-foreground">
          {canContinue
            ? "Requirement interpreted and images ready — continue to AI-assisted annotation."
            : "Analyze your requirement and add at least one image to continue."}
        </p>
        <Button disabled={!canContinue} onClick={() => router.push("/annotation")}>
          Continue to Annotation
          <ArrowRight className="size-4" />
        </Button>
      </div>
    </div>
  );
}
