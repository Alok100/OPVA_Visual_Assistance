"use client";

import { PlaceholderThumbnail } from "@/components/shared/placeholder-thumbnail";
import type { ViewImage } from "./view-model";
import { cn } from "cn";

interface ImageFilmstripProps {
  images: ViewImage[];
  activeIndex: number;
  onSelect: (index: number) => void;
}

export function ImageFilmstrip({ images, activeIndex, onSelect }: ImageFilmstripProps) {
  return (
    <div className="flex gap-2 overflow-x-auto pb-1">
      {images.map((img, i) => (
        <button
          key={img.id}
          type="button"
          onClick={() => onSelect(i)}
          className={cn(
            "w-16 shrink-0 rounded-lg transition-opacity",
            i === activeIndex ? "opacity-100" : "opacity-60 hover:opacity-90",
          )}
        >
          {img.url ? (
            <div
              className={cn(
                "aspect-square overflow-hidden rounded-lg border bg-muted",
                i === activeIndex ? "border-primary ring-2 ring-primary/30" : "border-border",
              )}
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={img.url} alt={img.filename} className="h-full w-full object-cover" />
            </div>
          ) : (
            <PlaceholderThumbnail
              image={{ id: img.id, filename: img.filename, tone: img.tone ?? "steel" }}
              selected={i === activeIndex}
            />
          )}
        </button>
      ))}
    </div>
  );
}
