import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";

interface QualityMetric {
  label: string;
  value: number;
}

interface QualityBreakdownProps {
  title: string;
  metrics: QualityMetric[];
}

export function QualityBreakdown({ title, metrics }: QualityBreakdownProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">{title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {metrics.map((metric) => (
          <div key={metric.label} className="space-y-1.5">
            <div className="flex items-center justify-between text-sm">
              <span className="text-foreground">{metric.label}</span>
              <span className="font-medium text-muted-foreground">{metric.value}%</span>
            </div>
            <Progress value={metric.value} />
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
