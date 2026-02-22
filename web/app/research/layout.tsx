import type { Metadata } from "next";
import { AppShell } from "@/components/layout/app-shell";

export const metadata: Metadata = {
  title: "Research Hub | MDRP",
  description: "Unified semantic search across FDA guidance, 510(k) clearances, MAUDE events, and recalls",
};

export default function ResearchLayout({ children }: { children: React.ReactNode }) {
  return <AppShell>{children}</AppShell>;
}
