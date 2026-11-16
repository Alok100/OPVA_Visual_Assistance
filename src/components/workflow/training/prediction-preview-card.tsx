import { Eye } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DemoDataTag } from "@/components/shared/demo-data-tag";
import { PlaceholderThumbnail } from "@/components/shared/placeholder-thumbnail";
import { DEMO_IMAGES } from "@/lib/mock-data";

const PREVIEW_RESULTS: Array<{ verdict: "correct" | "missed"; imageIndex: number }> = [
  { verdict: "correct", imageIndex: 0 },
  { verdict: "correct", imageIndex: 1 },
  { verdict: "missed", imageIndex: 2 },
  { verdict: "correct", imageIndex: 3 },
];

export function PredictionPreviewCard() {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm">
          <Eye className="size-4 text-primary" />
          Prediction preview
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <DemoDataTag label="Illustrative predictions on validation images" />
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {PREVIEW_RESULTS.map((result, i) => (
            <div key={i} className="space-y-1.5">
              <PlaceholderThumbnail image={DEMO_IMAGES[result.imageIndex]} />
              <p
                className={
                  result.verdict === "correct"
                    ? "text-center text-xs font-medium text-emerald-700"
                    : "text-center text-xs font-medium text-amber-700"
                }
              >
                {result.verdict === "correct" ? "Correct" : "Missed detection"}
              </p>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
