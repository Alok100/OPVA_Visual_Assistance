"use client";

import { usePathname } from "next/navigation";
import { ChevronRight, Menu } from "lucide-react";
import { WORKFLOW_STAGES } from "@/lib/mock-data";
import { useInspection } from "@/lib/inspection-context";
import { DemoDataTag } from "@/components/shared/demo-data-tag";
import { Button } from "@/components/ui/button";

interface HeaderProps {
  onMenuClick: () => void;
}

export function Header({ onMenuClick }: HeaderProps) {
  const pathname = usePathname();
  const { inspection } = useInspection();
  const currentStage = WORKFLOW_STAGES.find((stage) => stage.href === pathname) ?? WORKFLOW_STAGES[0];

  return (
    <header className="flex h-16 shrink-0 items-center justify-between border-b border-border bg-card px-4 sm:px-6">
      <div className="flex min-w-0 items-center gap-2 text-sm">
        <Button
          variant="ghost"
          size="icon"
          className="shrink-0 lg:hidden"
          onClick={onMenuClick}
          aria-label="Toggle navigation menu"
        >
          <Menu className="size-5" />
        </Button>
        <span className="min-w-0 truncate font-medium text-foreground">{inspection.name}</span>
        <ChevronRight className="size-3.5 shrink-0 text-muted-foreground" />
        <span className="hidden text-muted-foreground sm:inline">{currentStage.label}</span>
        <span className="ml-1 hidden shrink-0 rounded-full bg-accent px-2 py-0.5 text-xs font-medium text-accent-foreground sm:inline-block">
          Step {currentStage.step} of {WORKFLOW_STAGES.length}
        </span>
      </div>
      <div className="flex shrink-0 items-center gap-3">
        <DemoDataTag label="UI prototype" className="hidden sm:inline-flex" />
      </div>
    </header>
  );
}
