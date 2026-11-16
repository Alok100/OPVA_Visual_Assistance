import { ImageIcon } from "lucide-react";
import { cn } from "cn";
import type { DemoImage } from "@/lib/types";

const TONE_GRADIENT: Record<DemoImage["tone"], string> = {
  steel: "from-slate-200 to-slate-400",
  copper: "from-orange-100 to-orange-300",
  slate: "from-zinc-200 to-zinc-400",
};

/**
 * No real inspection photos exist in this UI-only phase, so demo images are
 * represented as labeled placeholders rather than fabricated photos.
 */
export function PlaceholderThumbnail({
  image,
  className,
  selected = false,
}: {
  image: DemoImage;
  className?: string;
  selected?: boolean;
}) {
  return (
    <div
      className={cn(
        "relative flex aspect-square flex-col items-center justify-center gap-1.5 overflow-hidden rounded-lg border bg-gradient-to-br text-slate-600",
        TONE_GRADIENT[image.tone],
        selected ? "border-primary ring-2 ring-primary/30" : "border-border",
        className,
      )}
    >
      <ImageIcon className="size-5 opacity-60" strokeWidth={1.5} />
      <span className="px-1 text-center text-[10px] font-medium leading-tight opacity-80">
        {image.filename}
      </span>
    </div>
  );
}
