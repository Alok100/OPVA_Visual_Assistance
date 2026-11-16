"use client";

import { useRef, useState } from "react";
import {
  UploadCloud,
  PlayCircle,
  Loader2,
  AlertTriangle,
  FlaskConical,
  CheckCircle2,
  XCircle,
  HelpCircle,
  ChevronDown,
} from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge, type StatusTone } from "@/components/shared/status-badge";
import { AnnotationCanvas } from "@/components/workflow/annotation/annotation-canvas";
import type { ViewBox, ViewImage } from "@/components/workflow/annotation/view-model";
import { useInspection } from "@/lib/inspection-context";
import { imageFileUrl, isNetworkError, runInference, uploadImages } from "@/lib/api-client";
import type { BoltResult, BoltVerdict, ImageResult, StoredImage } from "@/lib/types";
import { cn } from "cn";

const VERDICT_COLOR: Record<BoltVerdict, string> = {
  pass: "#16a34a",
  fail: "#dc2626",
  review: "#f59e0b",
  not_processed: "#6b7280",
};

// Plain-language explanations for a non-technical admin — the raw
// guard_reason/evidence strings (pixel fractions, coverage %, IoU) are kept
// available under "Technical details" rather than hidden, just not shown
// by default.
function overallImageMessage(result: ImageResult): { tone: StatusTone; text: string } | null {
  if (result.detection_quality === "not_processed") {
    return {
      tone: "danger",
      text:
        "We couldn't reliably find bolts in this photo. This usually means the photo is too cluttered, taken from too far away, or shows something different from what the system was trained on. Please retake a clearer, closer photo of the bolt(s) to check, or review this image by hand.",
    };
  }
  if (result.detection_quality === "review") {
    return {
      tone: "warning",
      text:
        "Something in this photo was detected more than once in the same spot, so we're not fully confident in the results below. Please double-check them by hand.",
    };
  }
  return null;
}

function boltMessage(bolt: BoltResult): string {
  switch (bolt.verdict) {
    case "pass":
      return "A yellow mark was found on this bolt — it meets the requirement.";
    case "fail":
      return "No yellow mark was found on this bolt — it does not meet the requirement.";
    case "review":
      return "The yellow mark on this bolt isn't clear enough to be sure either way. Please check it by hand.";
    case "not_processed":
      return "This bolt was found, but its mark wasn't checked because the whole photo's detections aren't trusted (see notice above).";
  }
}

const VERDICT_ICON: Record<BoltVerdict, typeof CheckCircle2> = {
  pass: CheckCircle2,
  fail: XCircle,
  review: HelpCircle,
  not_processed: HelpCircle,
};

const VERDICT_TONE: Record<BoltVerdict, StatusTone> = {
  pass: "success",
  fail: "danger",
  review: "warning",
  not_processed: "neutral",
};

export default function InferenceTestPage() {
  const { inspection } = useInspection();
  const inputRef = useRef<HTMLInputElement>(null);
  const [stored, setStored] = useState<StoredImage | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [status, setStatus] = useState<"idle" | "running" | "done" | "error">("idle");
  const [result, setResult] = useState<ImageResult | null>(null);
  const [runError, setRunError] = useState<string | null>(null);
  const [expandedBoltId, setExpandedBoltId] = useState<string | null>(null);

  async function handleFile(file: File) {
    setUploadError(null);
    setResult(null);
    setStatus("idle");
    try {
      const response = await uploadImages(inspection.id, [file]);
      if (response.stored[0]) {
        setStored(response.stored[0]);
      } else {
        setUploadError(response.errors[0]?.error ?? "Upload failed.");
      }
    } catch (err) {
      setUploadError(
        isNetworkError(err)
          ? "Could not reach the backend — is it running on http://localhost:8000?"
          : err instanceof Error
            ? err.message
            : "Upload failed.",
      );
    }
  }

  async function handleRunInference() {
    if (!stored) return;
    setStatus("running");
    setRunError(null);
    try {
      const imageResult = await runInference(inspection.id, stored.image_id);
      setResult(imageResult);
      setStatus("done");
    } catch (err) {
      setRunError(err instanceof Error ? err.message : "Inspection failed.");
      setStatus("error");
    }
  }

  const viewImage: ViewImage | null = stored
    ? {
        id: stored.image_id,
        filename: stored.filename,
        url: imageFileUrl(inspection.id, stored.image_id),
        width: stored.width,
        height: stored.height,
      }
    : null;

  const boxes: ViewBox[] =
    result?.bolts.map((bolt) => ({
      id: bolt.bolt_id,
      x: bolt.bbox.x,
      y: bolt.bbox.y,
      width: bolt.bbox.width,
      height: bolt.bbox.height,
      label: bolt.verdict.toUpperCase().replace("_", " "),
      color: VERDICT_COLOR[bolt.verdict],
      confidence: bolt.detection_confidence,
    })) ?? [];

  const boltCount = result?.bolts.length ?? 0;
  const passCount = result?.bolts.filter((b) => b.verdict === "pass").length ?? 0;
  const failCount = result?.bolts.filter((b) => b.verdict === "fail").length ?? 0;
  const reviewCount =
    result?.bolts.filter((b) => b.verdict === "review" || b.verdict === "not_processed").length ?? 0;

  const overallMessage = result ? overallImageMessage(result) : null;
  const overallTone: StatusTone =
    result?.detection_quality === "not_processed"
      ? "danger"
      : result?.detection_quality === "review" || failCount > 0 || reviewCount > 0
        ? "warning"
        : "success";

  return (
    <div className="space-y-6">
      <PageHeader
        title="Test Inference"
        description="Upload one image and run the real inspection checks on it."
      />

      <div className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2.5 text-xs text-amber-800">
        <FlaskConical className="mt-0.5 size-4 shrink-0" />
        <p>
          This runs the actual trained detector, not a demo — results are real model output. It was
          trained on a small set of example photos and can still make mistakes, especially on photos very
          different from its training examples.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">1. Upload a photo</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {uploadError && (
            <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2.5 text-sm text-red-700">
              <AlertTriangle className="mt-0.5 size-4 shrink-0" />
              {uploadError}
            </div>
          )}
          <div className="flex flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed border-border bg-muted/30 px-6 py-6 text-center">
            <UploadCloud className="size-6 text-muted-foreground" strokeWidth={1.5} />
            <p className="text-sm font-medium text-foreground">
              {stored ? `Using: ${stored.filename}` : "Choose one photo to test"}
            </p>
            <Button variant="outline" size="sm" onClick={() => inputRef.current?.click()}>
              {stored ? "Choose a different photo" : "Browse"}
            </Button>
            <input
              ref={inputRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) void handleFile(file);
                e.target.value = "";
              }}
            />
          </div>
        </CardContent>
      </Card>

      {viewImage && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">2. Run the inspection checks</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground">
              This checks: how many bolts are in the photo, and whether each bolt has the required
              yellow mark.
            </p>
            <AnnotationCanvas
              image={viewImage}
              boxes={boxes}
              index={0}
              total={1}
              showSuggestions={true}
              sourceTag={{ label: result ? "Real model output" : "Not checked yet", demo: false }}
              onPrev={() => {}}
              onNext={() => {}}
            />
            <Button onClick={handleRunInference} disabled={status === "running"}>
              {status === "running" ? (
                <>
                  <Loader2 className="size-4 animate-spin" />
                  Checking…
                </>
              ) : (
                <>
                  <PlayCircle className="size-4" />
                  {result ? "Run checks again" : "Run checks"}
                </>
              )}
            </Button>
            {status === "error" && (
              <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2.5 text-sm text-red-700">
                <AlertTriangle className="mt-0.5 size-4 shrink-0" />
                {runError}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {result && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">3. Results</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div
              className={cn(
                "flex items-center gap-2 rounded-lg px-3 py-2.5 text-sm font-medium",
                overallTone === "success" && "bg-emerald-50 text-emerald-800",
                overallTone === "warning" && "bg-amber-50 text-amber-800",
                overallTone === "danger" && "bg-red-50 text-red-800",
              )}
            >
              {overallTone === "success" && <CheckCircle2 className="size-5 shrink-0" />}
              {overallTone !== "success" && <AlertTriangle className="size-5 shrink-0" />}
              {overallTone === "success"
                ? `All ${boltCount} bolt${boltCount === 1 ? "" : "s"} checked — ${passCount} passed.`
                : `${boltCount} bolt${boltCount === 1 ? "" : "s"} found — ${passCount} passed, ${failCount} failed, ${reviewCount} need review.`}
            </div>

            {overallMessage && (
              <div
                className={cn(
                  "rounded-lg border px-3 py-2.5 text-sm",
                  overallMessage.tone === "danger" && "border-red-200 bg-red-50 text-red-700",
                  overallMessage.tone === "warning" && "border-amber-200 bg-amber-50 text-amber-800",
                )}
              >
                {overallMessage.text}
              </div>
            )}

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div className="rounded-lg border border-border p-3">
                <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  Check 1 — Bolt count
                </p>
                <p className="mt-1 text-sm text-foreground">
                  {boltCount} bolt{boltCount === 1 ? "" : "s"} detected in this photo.
                </p>
              </div>
              <div className="rounded-lg border border-border p-3">
                <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  Check 2 — Yellow mark
                </p>
                <p className="mt-1 text-sm text-foreground">
                  {passCount} passed, {failCount} failed, {reviewCount} need review.
                </p>
              </div>
            </div>

            <div className="space-y-2">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Per-bolt results
              </p>
              {boltCount === 0 && (
                <p className="text-sm text-muted-foreground">
                  No bolts were detected in this photo, so there&apos;s nothing to check.
                </p>
              )}
              {result.bolts.map((bolt, i) => {
                const Icon = VERDICT_ICON[bolt.verdict];
                const isExpanded = expandedBoltId === bolt.bolt_id;
                return (
                  <div key={bolt.bolt_id} className="rounded-lg border border-border">
                    <div className="flex items-start gap-3 p-3">
                      <Icon
                        className={cn(
                          "mt-0.5 size-5 shrink-0",
                          bolt.verdict === "pass" && "text-emerald-600",
                          bolt.verdict === "fail" && "text-red-600",
                          (bolt.verdict === "review" || bolt.verdict === "not_processed") &&
                            "text-amber-600",
                        )}
                      />
                      <div className="min-w-0 flex-1 space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium text-foreground">Bolt {i + 1}</span>
                          <StatusBadge tone={VERDICT_TONE[bolt.verdict]} icon={false}>
                            {bolt.verdict.replace("_", " ")}
                          </StatusBadge>
                        </div>
                        <p className="text-sm text-muted-foreground">{boltMessage(bolt)}</p>
                      </div>
                      <button
                        type="button"
                        onClick={() => setExpandedBoltId(isExpanded ? null : bolt.bolt_id)}
                        className="shrink-0 rounded-md p-1 text-muted-foreground hover:bg-muted"
                        aria-label={isExpanded ? "Hide technical details" : "Show technical details"}
                        aria-expanded={isExpanded}
                      >
                        <ChevronDown className={cn("size-4 transition-transform", isExpanded && "rotate-180")} />
                      </button>
                    </div>
                    {isExpanded && (
                      <div className="border-t border-border bg-muted/30 px-3 py-2 text-xs text-muted-foreground">
                        <p>Detection confidence: {Math.round(bolt.detection_confidence * 100)}%</p>
                        <p>Evidence: {bolt.evidence}</p>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {result.guard_reason && (
              <details className="rounded-lg border border-border px-3 py-2 text-xs text-muted-foreground">
                <summary className="cursor-pointer font-medium text-foreground">Technical details</summary>
                <p className="mt-1">{result.guard_reason}</p>
              </details>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
