"use client";

import { useRouter } from "next/navigation";
import { ArrowRight } from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DemoDataTag } from "@/components/shared/demo-data-tag";
import { ReadinessGauge } from "@/components/workflow/analysis/readiness-gauge";
import { DatasetStatCards } from "@/components/workflow/analysis/dataset-stat-cards";
import { QualityBreakdown } from "@/components/workflow/analysis/quality-breakdown";
import { IssuesList } from "@/components/workflow/analysis/issues-list";

const IMAGE_QUALITY_METRICS = [
  { label: "Resolution & sharpness", value: 95 },
  { label: "Lighting consistency", value: 82 },
  { label: "Angle / coverage variety", value: 76 },
];

const ANNOTATION_QUALITY_METRICS = [
  { label: "Label consistency", value: 93 },
  { label: "Bounding-box precision", value: 90 },
  { label: "Missing-label rate (inverse)", value: 88 },
];

export default function AnalysisPage() {
  const router = useRouter();

  return (
    <div className="space-y-6">
      <PageHeader
        title="Dataset Analysis & Readiness"
        description="Review image and annotation quality before training a model on this dataset."
      />

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Dataset readiness</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
          <ReadinessGauge percent={88} label="Ready for training" />
          <DemoDataTag label="Illustrative example" />
        </CardContent>
      </Card>

      <DatasetStatCards />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <QualityBreakdown title="Image quality" metrics={IMAGE_QUALITY_METRICS} />
        <QualityBreakdown title="Annotation quality" metrics={ANNOTATION_QUALITY_METRICS} />
      </div>

      <IssuesList />

      <div className="flex flex-col items-start gap-2 rounded-xl border border-border bg-card p-4 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-muted-foreground">
          Dataset looks ready for a first training pass. You can continue even with open issues.
        </p>
        <Button onClick={() => router.push("/training")}>
          Continue to Training
          <ArrowRight className="size-4" />
        </Button>
      </div>
    </div>
  );
}
