import type { Metadata }  from "next";
import type { ReactNode } from "react";
import { AppShell } from "@/components/layout/app-shell";

export const metadata: Metadata = {
  title: "Document Studio | MDRP",
  description: "AI-powered 510(k) submission section editor with real-time suggestions",
};

export default function DocumentStudioLayout({ children }: { children: ReactNode }) {
  return <AppShell>{children}</AppShell>;
}
