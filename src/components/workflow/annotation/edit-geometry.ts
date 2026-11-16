/**
 * Pure pointer-math helpers for the manual annotation editor, kept separate
 * from annotation-canvas.tsx so the drag/resize geometry isn't tangled with
 * JSX and event wiring. Everything here operates in percent-of-image space
 * (0-100) regardless of whether the underlying ViewBox is stored in pixels
 * or percent — annotation-canvas.tsx converts at the edges.
 */

export interface PercentBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export type HandleId = "n" | "s" | "e" | "w" | "ne" | "nw" | "se" | "sw";

export const HANDLES: { id: HandleId; cursor: string; style: { left: string; top: string } }[] = [
  { id: "nw", cursor: "cursor-nwse-resize", style: { left: "0%", top: "0%" } },
  { id: "n", cursor: "cursor-ns-resize", style: { left: "50%", top: "0%" } },
  { id: "ne", cursor: "cursor-nesw-resize", style: { left: "100%", top: "0%" } },
  { id: "e", cursor: "cursor-ew-resize", style: { left: "100%", top: "50%" } },
  { id: "se", cursor: "cursor-nwse-resize", style: { left: "100%", top: "100%" } },
  { id: "s", cursor: "cursor-ns-resize", style: { left: "50%", top: "100%" } },
  { id: "sw", cursor: "cursor-nesw-resize", style: { left: "0%", top: "100%" } },
  { id: "w", cursor: "cursor-ew-resize", style: { left: "0%", top: "50%" } },
];

const MIN_SIZE = 1;

/** Clamps a percent-space box so it stays fully inside [0,100] on both axes. */
export function clampBox(box: PercentBox): PercentBox {
  const width = Math.min(Math.max(box.width, MIN_SIZE), 100);
  const height = Math.min(Math.max(box.height, MIN_SIZE), 100);
  const x = Math.min(Math.max(box.x, 0), 100 - width);
  const y = Math.min(Math.max(box.y, 0), 100 - height);
  return { x, y, width, height };
}

/** Builds a normalized (non-negative width/height) box from two drag corners, in percent space. */
export function boxFromDrag(startX: number, startY: number, currentX: number, currentY: number): PercentBox {
  const x = Math.min(startX, currentX);
  const y = Math.min(startY, currentY);
  const width = Math.abs(currentX - startX);
  const height = Math.abs(currentY - startY);
  return clampBox({ x, y, width, height });
}

/** True if a drawn box is large enough to keep (filters out accidental clicks). */
export function isDrawnBoxSignificant(box: PercentBox): boolean {
  return box.width >= MIN_SIZE && box.height >= MIN_SIZE;
}

/** Moves a box by a percent-space delta, clamped so it stays in bounds. */
export function moveBox(box: PercentBox, dx: number, dy: number): PercentBox {
  return clampBox({ ...box, x: box.x + dx, y: box.y + dy });
}

/** Resizes a box by dragging one of the 8 handles by a percent-space delta. */
export function resizeBox(box: PercentBox, handle: HandleId, dx: number, dy: number): PercentBox {
  let { x, y, width, height } = box;

  if (handle.includes("e")) width += dx;
  if (handle.includes("s")) height += dy;
  if (handle.includes("w")) {
    width -= dx;
    x += dx;
  }
  if (handle.includes("n")) {
    height -= dy;
    y += dy;
  }

  // If a drag pushes a dimension negative, flip to keep width/height positive
  // rather than letting the box invert and jump.
  if (width < MIN_SIZE) {
    x += width - MIN_SIZE;
    width = MIN_SIZE;
  }
  if (height < MIN_SIZE) {
    y += height - MIN_SIZE;
    height = MIN_SIZE;
  }

  return clampBox({ x, y, width, height });
}
