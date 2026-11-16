import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge, type StatusTone } from "@/components/shared/status-badge";
import { DATASET_ISSUES } from "@/lib/mock-data";
import type { DatasetIssue } from "@/lib/types";

const SEVERITY_TONE: Record<DatasetIssue["severity"], StatusTone> = {
  low: "info",
  medium: "warning",
  high: "danger",
};

export function IssuesList() {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">Potential issues &amp; recommendations</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {DATASET_ISSUES.length === 0 ? (
          <p className="text-sm text-muted-foreground">No issues detected in this demo dataset.</p>
        ) : (
          DATASET_ISSUES.map((issue) => (
            <div key={issue.id} className="rounded-lg border border-border p-3">
              <div className="mb-1.5 flex items-start justify-between gap-2">
                <p className="text-sm font-medium text-foreground">{issue.title}</p>
                <StatusBadge tone={SEVERITY_TONE[issue.severity]} icon={false}>
                  {issue.severity}
                </StatusBadge>
              </div>
              <p className="text-xs text-muted-foreground">{issue.recommendation}</p>
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}
