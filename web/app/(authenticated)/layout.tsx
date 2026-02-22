/**
 * FDA-270 [FE-016] — Authenticated Route Group Layout
 * =====================================================
 * Wraps all authenticated pages with Sidebar + Header shell.
 * Route group `(authenticated)` keeps the folder from appearing in the URL.
 */

import { Sidebar } from "@/components/shell/sidebar";
import { Header } from "@/components/shell/header";

export default function AuthenticatedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Left sidebar */}
      <Sidebar />

      {/* Main area */}
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
