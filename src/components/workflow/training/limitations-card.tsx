import { Info } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const LIMITATIONS = [
  "This phase ships UI and navigation only — no model actually trains, and no images are sent anywhere.",
  "Evaluation numbers and predictions shown after a demo run are illustrative placeholders, not real inference output.",
  "Dataset readiness and quality scores on the Analysis screen use the same example dataset regardless of what you upload.",
];

const NEXT_STEPS = [
  "Connect the AI Annotation screen to a real detection pipeline.",
  "Wire the Analysis screen to real image-quality and annotation-quality checks.",
  "Implement an actual training job and live metrics for this screen.",
];

export function LimitationsCard() {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm">
          <Info className="size-4 text-primary" />
          Limitations &amp; next steps
        </CardTitle>
      </CardHeader>
      <CardContent className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Current limitations
          </p>
          <ul className="space-y-1.5 text-sm text-muted-foreground">
            {LIMITATIONS.map((item) => (
              <li key={item} className="flex gap-2">
                <span className="mt-1.5 size-1 shrink-0 rounded-full bg-muted-foreground" />
                {item}
              </li>
            ))}
          </ul>
        </div>
        <div>
          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Planned next microtasks
          </p>
          <ul className="space-y-1.5 text-sm text-muted-foreground">
            {NEXT_STEPS.map((item) => (
              <li key={item} className="flex gap-2">
                <span className="mt-1.5 size-1 shrink-0 rounded-full bg-primary" />
                {item}
              </li>
            ))}
          </ul>
        </div>
      </CardContent>
    </Card>
  );
}
