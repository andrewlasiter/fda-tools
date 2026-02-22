/**
 * FDA-246  [FE-008] Regulatory Research Hub — tabbed layout
 * ===========================================================
 * Wraps the 4 research surfaces in a top tab bar:
 *  1. Search     — unified semantic search (ResearchContent)
 *  2. Clusters   — Ward-linkage guidance dendrogram (DendrogramViz)
 *  3. Signals    — CUSUM MAUDE safety signal analysis (SignalDashboard)
 *  4. Predicates — side-by-side predicate comparison (PredicateTable)
 */

"use client";

import { useState } from "react";
import { Search, GitBranch, Activity, Columns } from "lucide-react";
import { ResearchContent }  from "@/components/research/research-content";
import { DendrogramViz }    from "@/components/research/dendrogram-viz";
import { SignalDashboard }  from "@/components/research/signal-dashboard";
import { PredicateTable }   from "@/components/research/predicate-table";
import { cn } from "@/lib/utils";

// ── Tab definitions ───────────────────────────────────────────────────────────

type TabId = "search" | "clusters" | "signals" | "predicates";

const TABS = [
  { id: "search"     as TabId, label: "Search",     icon: Search,    desc: "Semantic search across all sources" },
  { id: "clusters"   as TabId, label: "Clusters",   icon: GitBranch, desc: "Guidance document clustering" },
  { id: "signals"    as TabId, label: "Signals",    icon: Activity,  desc: "CUSUM MAUDE safety signals" },
  { id: "predicates" as TabId, label: "Predicates", icon: Columns,   desc: "Device comparison table" },
];

// ── Page ─────────────────────────────────────────────────────────────────────

export default function ResearchPage() {
  const [tab, setTab] = useState<TabId>("search");

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* ── Tab bar ────────────────────────────────────────────────────────── */}
      <div className="flex-shrink-0 border-b border-border bg-card px-2">
        <div className="flex items-center">
          {TABS.map((t) => {
            const Icon   = t.icon;
            const active = tab === t.id;
            return (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                title={t.desc}
                className={cn(
                  "flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors",
                  active
                    ? "border-primary text-primary"
                    : "border-transparent text-muted-foreground hover:text-foreground hover:border-muted-foreground/30",
                )}
              >
                <Icon className="h-4 w-4" />
                <span className="hidden sm:inline">{t.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* ── Tab content ────────────────────────────────────────────────────── */}
      <div className="flex-1 min-h-0 overflow-hidden">

        {/* Search — full-height with its own internal scroll */}
        {tab === "search" && <ResearchContent />}

        {/* Clusters — dendrogram visualization */}
        {tab === "clusters" && (
          <div className="h-full overflow-y-auto px-6 py-5">
            <div className="mb-4">
              <h2 className="text-xl font-heading font-bold text-foreground">
                Guidance Document Clusters
              </h2>
              <p className="mt-0.5 text-sm text-muted-foreground">
                Ward-linkage hierarchical clustering of FDA guidance documents by semantic
                similarity. Click clusters to filter; scroll wheel to zoom.
              </p>
            </div>
            <DendrogramViz />
          </div>
        )}

        {/* Signals — CUSUM MAUDE analysis */}
        {tab === "signals" && (
          <div className="h-full overflow-y-auto px-6 py-5">
            <div className="mb-4">
              <h2 className="text-xl font-heading font-bold text-foreground">
                Safety Signal Analysis
              </h2>
              <p className="mt-0.5 text-sm text-muted-foreground">
                CUSUM-based anomaly detection on MAUDE adverse event time series.
                Enter a 3-letter FDA product code to detect spikes and trends.
              </p>
            </div>
            <div className="max-w-3xl">
              <SignalDashboard />
            </div>
          </div>
        )}

        {/* Predicates — comparison table */}
        {tab === "predicates" && (
          <div className="h-full overflow-y-auto px-6 py-5">
            <div className="mb-4">
              <h2 className="text-xl font-heading font-bold text-foreground">
                Predicate Device Comparison
              </h2>
              <p className="mt-0.5 text-sm text-muted-foreground">
                Side-by-side comparison of subject device vs. predicate characteristics.
                Amber rows indicate differences requiring SE justification.
              </p>
            </div>
            <PredicateTable />
          </div>
        )}
      </div>
    </div>
  );
}
