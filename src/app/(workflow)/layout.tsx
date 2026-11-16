"use client";

import { useState, type ReactNode } from "react";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { InspectionProvider } from "@/lib/inspection-context";

export default function WorkflowLayout({ children }: { children: ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <InspectionProvider>
      <div className="flex h-screen w-full overflow-hidden bg-background">
        <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
        <div className="flex min-w-0 flex-1 flex-col">
          <Header onMenuClick={() => setSidebarOpen((v) => !v)} />
          <main className="flex-1 overflow-y-auto">
            <div className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6 sm:py-8">{children}</div>
          </main>
        </div>
      </div>
    </InspectionProvider>
  );
}
