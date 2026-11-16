"use client";

import { createContext, useContext, useMemo, useState, type ReactNode } from "react";
import { EXAMPLE_INSPECTION } from "./mock-data";
import type { Inspection, InspectionSpec } from "./types";

interface InspectionContextValue {
  inspection: Inspection;
  setRequirementText: (text: string) => void;
  requirementConfirmed: boolean;
  confirmRequirement: () => void;
  /** Real (not demo) requirement-interpretation result from
   * POST /inspections/{id}/requirement — null until "Analyze Requirement"
   * has been run successfully. Shared via context so other screens
   * (Analysis, Training) show the checks actually requested, not a fixed
   * demo list unrelated to what the user typed. */
  spec: InspectionSpec | null;
  setSpec: (spec: InspectionSpec | null) => void;
}

const InspectionContext = createContext<InspectionContextValue | null>(null);

export function InspectionProvider({ children }: { children: ReactNode }) {
  const [inspection, setInspection] = useState<Inspection>(EXAMPLE_INSPECTION);
  const [requirementConfirmed, setRequirementConfirmed] = useState(false);
  const [spec, setSpec] = useState<InspectionSpec | null>(null);

  const value = useMemo<InspectionContextValue>(
    () => ({
      inspection,
      setRequirementText: (text: string) =>
        setInspection((prev) => ({ ...prev, requirementText: text })),
      requirementConfirmed,
      confirmRequirement: () => setRequirementConfirmed(true),
      spec,
      setSpec,
    }),
    [inspection, requirementConfirmed, spec],
  );

  return <InspectionContext.Provider value={value}>{children}</InspectionContext.Provider>;
}

export function useInspection() {
  const ctx = useContext(InspectionContext);
  if (!ctx) {
    throw new Error("useInspection must be used within an InspectionProvider");
  }
  return ctx;
}
