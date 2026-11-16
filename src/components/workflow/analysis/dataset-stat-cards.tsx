import { Images, Tags, ShieldCheck, ListTree } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { useInspection } from "@/lib/inspection-context";

function StatCard({
  icon: Icon,
  label,
  value,
}: {
  icon: LucideIcon;
  label: string;
  value: string;
}) {
  return (
    <Card>
      <CardContent className="flex items-center gap-3">
        <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
          <Icon className="size-4.5" />
        </div>
        <div className="min-w-0">
          <p className="text-xs text-muted-foreground">{label}</p>
          <p className="text-lg font-semibold text-foreground">{value}</p>
        </div>
      </CardContent>
    </Card>
  );
}

export function DatasetStatCards() {
  const { inspection, spec } = useInspection();

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      <StatCard icon={Images} label="Total images" value={String(inspection.imageCount)} />
      <StatCard icon={Tags} label="Annotated" value={`${inspection.imageCount - 1} of ${inspection.imageCount}`} />
      <StatCard icon={ListTree} label="Checks covered" value={spec ? String(spec.checks.length) : "—"} />
      <StatCard icon={ShieldCheck} label="Avg. quality score" value="88%" />
    </div>
  );
}
