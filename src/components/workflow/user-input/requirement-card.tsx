"use client";

import { Sparkles, Loader2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { useInspection } from "@/lib/inspection-context";

interface RequirementCardProps {
  analyzing: boolean;
  onAnalyze: () => void;
}

export function RequirementCard({ analyzing, onAnalyze }: RequirementCardProps) {
  const { inspection, setRequirementText } = useInspection();

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Sparkles className="size-4 text-primary" />
          Describe the inspection
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <Textarea
          value={inspection.requirementText}
          onChange={(e) => setRequirementText(e.target.value)}
          placeholder="e.g. Detect every bolt and verify whether each bolt has the expected white line marking."
          className="min-h-32 resize-none text-sm"
          maxLength={600}
        />
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-xs text-muted-foreground">
            {inspection.requirementText.length}/600 — plain language, no technical setup required
          </p>
          <Button
            className="self-start sm:self-auto"
            onClick={onAnalyze}
            disabled={analyzing || inspection.requirementText.trim().length === 0}
          >
            {analyzing ? (
              <>
                <Loader2 className="size-4 animate-spin" />
                Analyzing…
              </>
            ) : (
              "Analyze Requirement"
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
