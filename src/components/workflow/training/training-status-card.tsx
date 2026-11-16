"use client";

import { PlayCircle, Loader2, CheckCircle2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { DemoDataTag } from "@/components/shared/demo-data-tag";
import type { TrainingRunState } from "@/lib/types";

interface TrainingStatusCardProps {
  state: TrainingRunState;
  progress: number;
  onStart: () => void;
}

export function TrainingStatusCard({ state, progress, onStart }: TrainingStatusCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">Training status</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {state === "idle" && (
          <div className="flex flex-col items-start gap-3 rounded-lg border border-dashed border-border bg-muted/40 p-5">
            <p className="text-sm text-muted-foreground">
              No training run yet. Starting a run here is a UI demo only — it does not train a real
              model in this phase.
            </p>
            <Button onClick={onStart}>
              <PlayCircle className="size-4" />
              Start Demo Training Run
            </Button>
          </div>
        )}

        {state === "running" && (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="flex items-center gap-2 font-medium text-foreground">
                <Loader2 className="size-4 animate-spin text-primary" />
                Running illustrative training…
              </span>
              <span className="text-muted-foreground">{progress}%</span>
            </div>
            <Progress value={progress} />
          </div>
        )}

        {state === "completed" && (
          <div className="flex items-center justify-between rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2.5">
            <span className="flex items-center gap-2 text-sm font-medium text-emerald-700">
              <CheckCircle2 className="size-4" />
              Demo run complete
            </span>
            <DemoDataTag label="Illustrative results" />
          </div>
        )}
      </CardContent>
    </Card>
  );
}
