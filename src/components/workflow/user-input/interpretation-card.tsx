import { ListChecks, CircleDashed, AlertTriangle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/shared/empty-state";
import { StatusBadge, type StatusTone } from "@/components/shared/status-badge";
import type { InspectionSpec } from "@/lib/types";

interface InterpretationCardProps {
  analyzing: boolean;
  spec: InspectionSpec | null;
  error: string | null;
}

const FEASIBILITY_LABEL: Record<InspectionSpec["feasibility"]["level"], string> = {
  feasible: "Feasible",
  needs_info: "Needs more information",
  not_feasible: "Not feasible with this interpreter",
};

const FEASIBILITY_TONE: Record<InspectionSpec["feasibility"]["level"], StatusTone> = {
  feasible: "success",
  needs_info: "warning",
  not_feasible: "danger",
};

export function InterpretationCard({ analyzing, spec, error }: InterpretationCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <ListChecks className="size-4 text-primary" />
          Interpreted inspection plan
        </CardTitle>
      </CardHeader>
      <CardContent>
        {error ? (
          <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2.5 text-sm text-red-700">
            <AlertTriangle className="mt-0.5 size-4 shrink-0" />
            {error}
          </div>
        ) : !spec ? (
          <EmptyState
            icon={CircleDashed}
            title={analyzing ? "Analyzing requirement…" : "Not analyzed yet"}
            description="Describe your inspection and select “Analyze Requirement” to see the interpreted checks here."
          />
        ) : (
          <div className="space-y-4">
            <div className="flex items-center justify-between rounded-lg border border-border bg-muted/40 px-3 py-2.5">
              <span className="text-sm font-medium text-foreground">Feasibility</span>
              <StatusBadge tone={FEASIBILITY_TONE[spec.feasibility.level]}>
                {FEASIBILITY_LABEL[spec.feasibility.level]}
              </StatusBadge>
            </div>

            {spec.checks.length > 0 && (
              <ul className="space-y-2.5">
                {spec.checks.map((check, i) => (
                  <li key={check.id} className="flex gap-3 rounded-lg border border-border p-3">
                    <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">
                      {i + 1}
                    </span>
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-foreground">{check.title}</p>
                      <p className="text-xs text-muted-foreground">{check.method}</p>
                    </div>
                  </li>
                ))}
              </ul>
            )}

            {(spec.feasibility.reasons.length > 0 ||
              spec.feasibility.limitations.length > 0 ||
              spec.feasibility.missing_information.length > 0) && (
              <div className="space-y-2 text-xs text-muted-foreground">
                {spec.feasibility.reasons.map((r, i) => (
                  <p key={`reason-${i}`}>{r}</p>
                ))}
                {spec.feasibility.missing_information.length > 0 && (
                  <div>
                    <p className="font-medium text-foreground">Missing information</p>
                    <ul className="list-disc space-y-0.5 pl-4">
                      {spec.feasibility.missing_information.map((m, i) => (
                        <li key={i}>{m}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {spec.feasibility.limitations.length > 0 && (
                  <div>
                    <p className="font-medium text-foreground">Limitations</p>
                    <ul className="list-disc space-y-0.5 pl-4">
                      {spec.feasibility.limitations.map((l, i) => (
                        <li key={i}>{l}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
