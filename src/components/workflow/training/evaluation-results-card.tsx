import { ClipboardCheck } from "lucide-react";
import { Card, CardAction, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/shared/status-badge";
import { DemoDataTag } from "@/components/shared/demo-data-tag";
import { useInspection } from "@/lib/inspection-context";

// Deterministic (not random-per-render) illustrative accuracy per check, so
// the demo numbers are stable across reloads — stand-ins only, no real
// training/evaluation has run. The checks themselves are real, from the
// deterministic requirement interpreter (app/spec.py), not a fixed demo list.
function illustrativeAccuracy(checkId: string): number {
  let hash = 0;
  for (let i = 0; i < checkId.length; i++) hash = (hash * 31 + checkId.charCodeAt(i)) >>> 0;
  return 85 + (hash % 13); // 85-97%
}

export function EvaluationResultsCard() {
  const { spec } = useInspection();
  const checks = spec?.checks ?? [];
  // A real "needs review" signal (the interpreter's own feasibility level),
  // not fabricated per-check — ties the illustrative numbers to something
  // genuinely known rather than inventing per-check confidence.
  const feasible = spec?.feasibility.level === "feasible";

  const accuracies = checks.map((c) => illustrativeAccuracy(c.id));
  const overall = accuracies.length > 0 ? Math.round(accuracies.reduce((s, a) => s + a, 0) / accuracies.length) : 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm">
          <ClipboardCheck className="size-4 text-primary" />
          Evaluation results
        </CardTitle>
        <CardAction>
          <DemoDataTag label="Illustrative" />
        </CardAction>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-center justify-between rounded-lg bg-muted/50 px-3 py-2.5">
          <span className="text-sm text-foreground">Overall model performance</span>
          <span className="text-lg font-semibold text-foreground">{overall}%</span>
        </div>
        {checks.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No checks to evaluate — analyze a requirement on the User Input screen first.
          </p>
        ) : (
          <div className="divide-y divide-border rounded-lg border border-border">
            {checks.map((check, i) => (
              <div key={check.id} className="flex items-center justify-between px-3 py-2.5 text-sm">
                <span className="text-foreground">{check.title}</span>
                <div className="flex items-center gap-3">
                  <span className="font-medium text-muted-foreground">{accuracies[i]}%</span>
                  <StatusBadge tone={feasible ? "success" : "warning"} icon={false}>
                    {feasible ? "Pass" : "Needs review"}
                  </StatusBadge>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
