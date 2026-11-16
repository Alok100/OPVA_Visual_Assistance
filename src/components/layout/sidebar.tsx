"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ScanEye, Check, Images, Database, FlaskConical } from "lucide-react";
import { cn } from "cn";
import { WORKFLOW_STAGES } from "@/lib/mock-data";
import { useInspection } from "@/lib/inspection-context";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface SidebarProps {
  open: boolean;
  onClose: () => void;
}

export function Sidebar({ open, onClose }: SidebarProps) {
  const pathname = usePathname();
  const { inspection } = useInspection();

  return (
    <>
      {open && (
        <div
          className="fixed inset-0 z-40 bg-foreground/20 lg:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex h-full w-72 shrink-0 -translate-x-full flex-col border-r border-sidebar-border bg-sidebar transition-transform duration-200 lg:static lg:z-auto lg:translate-x-0",
          open && "translate-x-0",
        )}
      >
      <div className="flex items-center gap-2.5 px-5 py-5">
        <div className="flex size-9 items-center justify-center rounded-lg bg-primary text-primary-foreground">
          <ScanEye className="size-5" />
        </div>
        <div>
          <p className="text-sm font-semibold leading-none text-sidebar-foreground">
            Visual Inspector
          </p>
          <p className="mt-1 text-xs text-muted-foreground">AI Quality Inspection</p>
        </div>
      </div>

      <div className="px-4 pb-2">
        <p className="mb-1.5 px-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">
          Current inspection
        </p>
        <Select defaultValue={inspection.id}>
          <SelectTrigger className="w-full bg-background" aria-label="Select inspection project">
            <SelectValue placeholder="Select inspection" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={inspection.id}>{inspection.name}</SelectItem>
            <SelectItem value="insp-example-2">Engine Cover Weld Check</SelectItem>
            <SelectItem value="insp-example-3">Panel Surface Scratch Scan</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <nav className="flex-1 space-y-1 px-4 py-3">
        <p className="mb-1.5 px-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">
          Workflow
        </p>
        {WORKFLOW_STAGES.map((stage) => {
          const isActive = pathname === stage.href;
          return (
            <Link
              key={stage.id}
              href={stage.href}
              onClick={onClose}
              aria-current={isActive ? "page" : undefined}
              className={cn(
                "group flex items-start gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors",
                isActive
                  ? "bg-sidebar-accent text-sidebar-accent-foreground"
                  : "text-sidebar-foreground hover:bg-muted",
              )}
            >
              <span
                className={cn(
                  "mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full text-[11px] font-semibold",
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted text-muted-foreground group-hover:bg-background",
                )}
              >
                {stage.step}
              </span>
              <span className="flex flex-col">
                <span className={cn("font-medium", isActive && "text-primary")}>
                  {stage.label}
                </span>
                <span className="text-xs text-muted-foreground">{stage.description}</span>
              </span>
            </Link>
          );
        })}
      </nav>

      <div className="px-4 pb-3">
        <p className="mb-1.5 px-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">
          Testing tools
        </p>
        <Link
          href="/inference"
          onClick={onClose}
          aria-current={pathname === "/inference" ? "page" : undefined}
          className={cn(
            "flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition-colors",
            pathname === "/inference"
              ? "bg-sidebar-accent text-sidebar-accent-foreground"
              : "text-sidebar-foreground hover:bg-muted",
          )}
        >
          <FlaskConical className="size-4 shrink-0 text-muted-foreground" />
          <span className="flex flex-col">
            <span className="font-medium">Test Inference</span>
            <span className="text-xs text-muted-foreground">Run the real detector on an image</span>
          </span>
        </Link>
      </div>

      <div className="mx-4 mb-4 rounded-lg border border-border bg-muted/50 p-3">
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
          Project status
        </p>
        <div className="space-y-1.5 text-xs">
          <div className="flex items-center justify-between">
            <span className="flex items-center gap-1.5 text-muted-foreground">
              <Images className="size-3.5" /> Images
            </span>
            <span className="font-medium text-foreground">{inspection.imageCount}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="flex items-center gap-1.5 text-muted-foreground">
              <Database className="size-3.5" /> Factory
            </span>
            <span className="min-w-0 truncate pl-2 text-right font-medium text-foreground">
              {inspection.factory}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="flex items-center gap-1.5 text-muted-foreground">
              <Check className="size-3.5" /> Status
            </span>
            <span className="font-medium capitalize text-foreground">
              {inspection.status.replace("_", " ")}
            </span>
          </div>
        </div>
      </div>
      </aside>
    </>
  );
}
