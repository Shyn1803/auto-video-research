/**
 * projects/[id]/page.tsx — entry point redirects to /scenes.
 * The actual workspace layout is in layout.tsx (Step 1).
 */

"use client";

import { useEffect } from "react";
import { useParams, useRouter } from "next/navigation";

export default function ProjectPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();

  useEffect(() => {
    if (params?.id) {
      router.replace(`/projects/${params.id}/scenes`);
    }
  }, [params, router]);

  return null;
}
