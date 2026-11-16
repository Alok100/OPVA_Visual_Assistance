import { FlaskConical } from "lucide-react";
import { cn } from "cn";

/**
 * Required on every value, image, metric, or result that is not produced by a
 * real model or pipeline yet. See docs/PRODUCT_SCOPE.md — "avoid fabricated
 * functionality" is a hard rule for this phase.
 */
export function DemoDataTag({
  label = "Demo data",
  className,
}: {
  label?: string;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border border-dashed border-amber-300 bg-amber-50 px-2 py-0.5 text-[11px] font-medium text-amber-700",
        className,
      )}
    >
      <FlaskConical className="size-3" />
      {label}
    </span>
  );
}
