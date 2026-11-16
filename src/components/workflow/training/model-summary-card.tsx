import { Boxes } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useInspection } from "@/lib/inspection-context";

export function ModelSummaryCard() {
  const { inspection, spec } = useInspection();

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm">
          <Boxes className="size-4 text-primary" />
          Model &amp; experiment summary
        </CardTitle>
      </CardHeader>
      <CardContent>
        <dl className="grid grid-cols-2 gap-4 text-sm sm:grid-cols-4">
          <div>
            <dt className="text-xs text-muted-foreground">Inspection</dt>
            <dd className="font-medium text-foreground">{inspection.name}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Checks in scope</dt>
            <dd className="font-medium text-foreground">{spec ? spec.checks.length : "—"}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Base models</dt>
            <dd className="font-medium text-foreground">2 reused, 1 new</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Experiment version</dt>
            <dd className="font-medium text-foreground">v0.1.0-draft</dd>
          </div>
        </dl>
      </CardContent>
    </Card>
  );
}
