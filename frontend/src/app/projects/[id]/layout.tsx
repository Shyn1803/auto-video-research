/**
 * projects/[id]/layout.tsx — workspace shell per Step 1.
 *
 * Route: /projects/{id}/scenes  (SCENES is the primary sub-route in Epic 5)
 *
 * In: Topbar, PipelineStepper, content children, ApproveBar slot
 * Out: 5-2 controls detail, 5-3 AssetPicker, 5-9 VersionSwitcher, 5-10 ProjectDrawer
 */

"use client";

import { use, type ReactNode } from "react";
import { WorkspaceProvider } from "@/lib/workspace-context";
import Topbar from "@/components/workspace/Topbar";
import PipelineStepper from "@/components/workspace/PipelineStepper";

interface Props {
  children: ReactNode;
  // Next.js 15: `params` is a Promise even in a route segment that renders
  // a Client Component — must be unwrapped with React's `use()`, not
  // destructured synchronously (that logs "params should be awaited").
  params: Promise<{ id: string }>;
}

export default function WorkspaceLayout({ children, params }: Props) {
  const { id } = use(params);
  return (
    <WorkspaceProvider projectId={id}>
      <div className="mx-auto max-w-[1440px] space-y-4 px-4 py-6 md:px-6 lg:px-8">
        {/* Step 1 — topbar */}
        <Topbar />
        {/* Step 2 — PipelineStepper */}
        <PipelineStepper />
        {/* Step 3 — content area */}
        <main>{children}</main>
      </div>
    </WorkspaceProvider>
  );
}
