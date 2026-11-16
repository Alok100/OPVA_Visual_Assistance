"use client";

import { useEffect, useRef, useState } from "react";
import { PageHeader } from "@/components/shared/page-header";
import { ModelSummaryCard } from "@/components/workflow/training/model-summary-card";
import { TrainingConfigCard } from "@/components/workflow/training/training-config-card";
import { TrainingStatusCard } from "@/components/workflow/training/training-status-card";
import { EvaluationResultsCard } from "@/components/workflow/training/evaluation-results-card";
import { PredictionPreviewCard } from "@/components/workflow/training/prediction-preview-card";
import { LimitationsCard } from "@/components/workflow/training/limitations-card";
import type { TrainingRunState } from "@/lib/types";

export default function TrainingPage() {
  const [runState, setRunState] = useState<TrainingRunState>("idle");
  const [progress, setProgress] = useState(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  function startRun() {
    setRunState("running");
    setProgress(0);
    intervalRef.current = setInterval(() => {
      setProgress((p) => {
        const next = p + 10;
        if (next >= 100) {
          if (intervalRef.current) clearInterval(intervalRef.current);
          setRunState("completed");
          return 100;
        }
        return next;
      });
    }, 180);
  }

  useEffect(() => {
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, []);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Model Training & Evaluation"
        description="Configure and run a training pass, then review evaluation results before publishing."
      />

      <ModelSummaryCard />
      <TrainingConfigCard />
      <TrainingStatusCard state={runState} progress={progress} onStart={startRun} />

      {runState === "completed" && (
        <>
          <EvaluationResultsCard />
          <PredictionPreviewCard />
        </>
      )}

      <LimitationsCard />
    </div>
  );
}
