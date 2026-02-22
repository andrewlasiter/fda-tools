"use client";

/**
 * FDA-290 [RH-003] — /research page
 * ====================================
 * Research Hub: tabbed layout wiring all 6 research panels.
 *
 * Tabs:
 *   1. Search      — global unified search (placeholder)
 *   2. Predicates  — PredicateSelection + EvidenceChainViewer side-by-side
 *   3. Guidance    — GuidanceDendrogram + GuidanceInlineViewer split
 *   4. Signals     — SignalDashboard full-width
 *   5. Citations   — CitationManager full-width
 *
 * Layout: fixed left tab rail (48px icons) + main panel.
 * On mobile: bottom tab bar, panels stack vertically.
 */

import React, { useState } from "react";
import { cn } from "@/lib/utils";
import { useResearchSearch, type ResearchHit, type ResearchSource } from "@/lib/api-client";

// Research Hub components
import { PredicateSelection,    type PredicateDevice }   from "@/components/research/predicate-selection";
import { EvidenceChainViewer,   type EvidenceClaim }     from "@/components/research/evidence-chain-viewer";
import { GuidanceInlineViewer,  type HighlightedPassage,
                                 type Annotation,
                                 type RelatedDocument }  from "@/components/research/guidance-inline-viewer";
import { CitationManager,       type Citation }          from "@/components/research/citation-manager";
import { GuidanceDendrogram,    type GuidanceCluster }   from "@/components/research/guidance-dendrogram";
import { SignalDashboard,       type SignalDataPoint }   from "@/components/research/signal-dashboard";

// ── Tab config ──────────────────────────────────────────────────────────────

type TabId = "search" | "predicates" | "guidance" | "signals" | "citations";

const TABS: { id: TabId; label: string; icon: string; description: string }[] = [
  { id: "search",     label: "Search",     icon: "⌕",  description: "Unified semantic search" },
  { id: "predicates", label: "Predicates", icon: "≡",  description: "Predicate selection & evidence" },
  { id: "guidance",   label: "Guidance",   icon: "⎘",  description: "Guidance documents & clusters" },
  { id: "signals",    label: "Signals",    icon: "⚡", description: "Safety signal dashboard" },
  { id: "citations",  label: "Citations",  icon: "❝",  description: "Citation library" },
];

// ── Demo data ───────────────────────────────────────────────────────────────
// In production these are fetched from the FastAPI bridge via TanStack Query.

const DEMO_PREDICATES: PredicateDevice[] = [
  {
    kNumber: "K231045", deviceName: "SmartFlow Infusion Pump Pro", applicant: "MedDevice Corp",
    productCode: "FRN", deviceClass: "II", clearanceYear: 2023, similarity: 91,
    health: { recallCount: 0, aeCount: 12, status: "healthy" },
    decisionCode: "SESE", regulationNum: "880.5860",
  },
  {
    kNumber: "K220789", deviceName: "AutoFlow IV Controller", applicant: "BioTech Solutions",
    productCode: "FRN", deviceClass: "II", clearanceYear: 2022, similarity: 78,
    health: { recallCount: 1, aeCount: 34, status: "caution" },
    decisionCode: "SE", regulationNum: "880.5860",
  },
  {
    kNumber: "K191234", deviceName: "InfuMaster 3000", applicant: "GlobalMed Inc",
    productCode: "FRN", deviceClass: "II", clearanceYear: 2019, similarity: 65,
    health: { recallCount: 3, aeCount: 187, status: "toxic" },
    decisionCode: "SE",
  },
];

const DEMO_CLAIMS: EvidenceClaim[] = [
  {
    id: "c1", confidence: 87,
    text: "The subject device uses the same pumping mechanism (peristaltic) as predicate K231045, achieving comparable flow accuracy of ±2%.",
    section: "SE Discussion §3.1",
    evidence: [
      {
        id: "e1", strength: "high", confidence: 90, type: "bench_test",
        quote: "Flow accuracy testing per IEC 60601-2-24 demonstrated ±1.8% across all programmed rates.",
        documents: [
          { id: "d1", title: "Bench Test Report: Flow Accuracy", docType: "internal", reference: "BTR-2024-001", pageOrSection: "§4.2" },
          { id: "d2", title: "SmartFlow Infusion Pump Pro 510(k)", docType: "510k_summary", reference: "K231045", pageOrSection: "p. 12" },
        ],
      },
    ],
  },
  {
    id: "c2", confidence: 72,
    text: "Both devices share the same intended use: short-term (≤ 7 days) continuous IV infusion in acute care settings.",
    section: "SE Discussion §2.1",
    evidence: [
      {
        id: "e2", strength: "medium", confidence: 75, type: "predicate_data",
        quote: "Intended for use in hospital and ambulatory care for continuous administration of IV fluids.",
        documents: [
          { id: "d3", title: "Guidance: Infusion Pumps 510(k) Submissions", docType: "guidance", reference: "FDA-2014-D-0798", pageOrSection: "§III.A" },
        ],
      },
    ],
  },
];

const DEMO_PASSAGES: HighlightedPassage[] = [
  { id: "p1", page: 4, category: "indication", relevance: 95,
    excerpt: "The device is intended for short-term IV infusion of fluids and medications in adult patients in acute care settings, consistent with the predicate's cleared indication." },
  { id: "p2", page: 7, category: "technical", relevance: 82,
    excerpt: "Flow accuracy was validated per IEC 60601-2-24:2012 at rates from 1 to 999 mL/hr." },
];

const DEMO_ANNOTATIONS: Annotation[] = [
  { id: "a1", page: 4, note: "Same intended use as our subject device", linkedTo: "SE Discussion §2.1", createdAt: "2026-02-20" },
];

const DEMO_RELATED: RelatedDocument[] = [
  { title: "FDA Guidance: Infusion Pumps 510(k)", docType: "guidance", reference: "FDA-2014-D-0798", relevance: 94 },
];

const DEMO_CLUSTERS: GuidanceCluster[] = [
  {
    id: "cl1", label: "Infusion & Fluid Delivery", area: "devices",
    docs: [
      { id: "g1", title: "Infusion Pumps 510(k) Submissions", area: "devices", applicability: 95, issueDate: "2014-11-26", cfr: "21 CFR 880.5860" },
      { id: "g2", title: "Human Factors Guidance for Infusion Pumps", area: "devices", applicability: 88, issueDate: "2020-03-12" },
    ],
    children: [],
  },
  {
    id: "cl2", label: "Software & Cybersecurity", area: "devices",
    docs: [
      { id: "g3", title: "Cybersecurity in Medical Devices", area: "devices", applicability: 72, issueDate: "2023-09-26" },
      { id: "g4", title: "Software as a Medical Device (SaMD)", area: "general", applicability: 55, issueDate: "2019-10-03" },
    ],
    children: [],
  },
  {
    id: "cl3", label: "Biocompatibility", area: "general",
    docs: [
      { id: "g5", title: "Use of ISO 10993 Biocompatibility Testing", area: "general", applicability: 80, issueDate: "2020-06-16", cfr: "21 CFR 820" },
    ],
    children: [],
  },
];

const DEMO_SIGNALS: SignalDataPoint[] = Array.from({ length: 24 }, (_, i) => {
  const d = new Date(2024, 0, 1);
  d.setMonth(d.getMonth() + i);
  const base = 15 + Math.sin(i * 0.5) * 5 + Math.random() * 3;
  const spike = i === 18 || i === 22;
  return {
    month: d.toISOString().slice(0, 7),
    productCode: "FRN",
    critical: spike ? Math.round(base * 0.4) : Math.round(base * 0.1),
    serious: spike ? Math.round(base * 0.5) : Math.round(base * 0.3),
    non_serious: Math.round(base * 0.6),
    cusum: spike ? 6.2 + Math.random() : Math.min(4.5, i * 0.2 + Math.random()),
    isAnomaly: spike,
    anomalyNote: spike ? "CUSUM threshold exceeded — investigate pump alarm reports" : undefined,
  };
});

const DEMO_CITATIONS: Citation[] = [
  {
    id: "cit1", title: "Infusion Pumps 510(k) Submissions Guidance", source: "FDA Guidance Documents",
    sourceType: "guidance", date: "2014-11-26", relevance: 95,
    url: "https://www.fda.gov/media/89381/download",
    tags: ["predicate", "standard"], note: "Primary guidance for 510(k) pathway",
    linkedSections: ["SE Discussion §2.1"], addedAt: "2026-02-20", inSubmission: true,
  },
  {
    id: "cit2", title: "ISO 60601-2-24:2012 Infusion Pumps", source: "IEC/ISO Standards",
    sourceType: "standard", date: "2012-01-01", relevance: 90,
    tags: ["standard", "safety"], note: "Flow accuracy test standard",
    linkedSections: ["Testing §4.2"], addedAt: "2026-02-20", inSubmission: true,
  },
];

// ── Source badge ─────────────────────────────────────────────────────────────

const SOURCE_CONFIG: Record<ResearchSource, { label: string; color: string; bg: string }> = {
  "510k":     { label: "510(k)",   color: "#005EA2", bg: "bg-[#005EA2]/10" },
  guidance:   { label: "Guidance", color: "#1A7F4B", bg: "bg-[#1A7F4B]/10" },
  maude:      { label: "MAUDE",    color: "#B45309", bg: "bg-[#B45309]/10" },
  recalls:    { label: "Recall",   color: "#C5191B", bg: "bg-[#C5191B]/10" },
};

function SourceBadge({ source }: { source: ResearchSource }) {
  const cfg = SOURCE_CONFIG[source] ?? { label: source, color: "#666", bg: "bg-muted" };
  return (
    <span
      className={cn("text-[9px] font-semibold px-1.5 py-0.5 rounded uppercase tracking-wide", cfg.bg)}
      style={{ color: cfg.color }}
    >
      {cfg.label}
    </span>
  );
}

// ── Result card ──────────────────────────────────────────────────────────────

function SearchResultCard({ hit }: { hit: ResearchHit }) {
  const pct = Math.round(hit.score * 100);
  return (
    <article className="rounded-lg border border-border bg-card p-3 hover:border-[#005EA2]/30 transition-colors">
      <div className="flex items-start gap-2 mb-1.5">
        <SourceBadge source={hit.source} />
        <p className="text-[11px] font-semibold text-foreground leading-tight flex-1 min-w-0">
          {hit.title}
        </p>
        <span className="text-[9px] font-mono text-muted-foreground flex-shrink-0">{pct}%</span>
      </div>
      {hit.excerpt && (
        <p className="text-[10px] text-muted-foreground leading-relaxed line-clamp-3">
          {hit.excerpt}
        </p>
      )}
      {hit.url && (
        <a
          href={hit.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-[9px] text-[#005EA2] hover:underline mt-1 inline-block cursor-pointer"
        >
          View document →
        </a>
      )}
    </article>
  );
}

// ── Search panel (FDA-311 — live) ─────────────────────────────────────────────

const ALL_SOURCES: ResearchSource[] = ["510k", "guidance", "maude", "recalls"];

function SearchPanel() {
  const [query, setQuery]       = useState("");
  const [submitted, setSubmitted] = useState("");
  const [sources, setSources]   = useState<ResearchSource[]>(["510k", "guidance", "maude"]);
  const search = useResearchSearch();

  function handleSubmit() {
    const q = query.trim();
    if (!q) return;
    setSubmitted(q);
    search.mutate({ query: q, sources, limit: 10 });
  }

  function toggleSource(src: ResearchSource) {
    setSources(prev =>
      prev.includes(src) ? prev.filter(s => s !== src) : [...prev, src]
    );
  }

  return (
    <div className="flex flex-col h-full p-6 overflow-hidden">
      <h2 className="text-sm font-semibold text-foreground mb-1">Unified Research Search</h2>
      <p className="text-[11px] text-muted-foreground mb-3">
        Search across 510(k) clearances, FDA guidance, MAUDE adverse events, and recalls.
      </p>

      {/* Query input */}
      <div className="flex gap-2 mb-2">
        <input
          type="search"
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={e => e.key === "Enter" && handleSubmit()}
          placeholder="e.g. infusion pump, glucose monitor, catheter…"
          className="flex-1 px-3 py-2 text-[12px] rounded-lg border border-border bg-background outline-none focus:border-[#005EA2]/50 text-foreground placeholder:text-muted-foreground"
        />
        <button
          onClick={handleSubmit}
          disabled={!query.trim() || search.isPending}
          className="px-4 py-2 bg-[#005EA2] text-white text-[11px] font-semibold rounded-lg disabled:opacity-40 cursor-pointer disabled:cursor-not-allowed hover:bg-[#005EA2]/90 transition-colors"
        >
          {search.isPending ? "…" : "Search"}
        </button>
      </div>

      {/* Source toggles */}
      <div className="flex gap-1.5 mb-4 flex-wrap">
        {ALL_SOURCES.map(src => {
          const cfg = SOURCE_CONFIG[src];
          const active = sources.includes(src);
          return (
            <button
              key={src}
              onClick={() => toggleSource(src)}
              className={cn(
                "text-[9px] font-semibold px-2 py-1 rounded uppercase tracking-wide border transition-colors cursor-pointer",
                active ? cn(cfg.bg, "border-transparent") : "border-border text-muted-foreground bg-background"
              )}
              style={active ? { color: cfg.color } : {}}
            >
              {cfg.label}
            </button>
          );
        })}
      </div>

      {/* Results */}
      <div className="flex-1 overflow-y-auto space-y-2">
        {/* Empty state */}
        {!search.data && !search.isPending && !search.isError && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <p className="text-[32px] mb-3 opacity-15 select-none" aria-hidden="true">⌕</p>
            <p className="text-[12px] font-medium text-foreground">Live FDA database search</p>
            <p className="text-[11px] text-muted-foreground mt-1 max-w-xs">
              Enter a device name or clinical term above. Results come from openFDA APIs
              and the FDA guidance corpus.
            </p>
          </div>
        )}

        {/* Loading */}
        {search.isPending && (
          <div className="flex items-center justify-center h-32">
            <div className="flex gap-1.5" role="status" aria-label="Searching">
              {[0, 1, 2].map(i => (
                <div
                  key={i}
                  className="w-2 h-2 rounded-full bg-[#005EA2] animate-bounce"
                  style={{ animationDelay: `${i * 120}ms` }}
                />
              ))}
            </div>
          </div>
        )}

        {/* Error */}
        {search.isError && (
          <div className="rounded-lg border border-[#C5191B]/30 bg-[#C5191B]/5 p-3 text-[11px] text-[#C5191B]" role="alert">
            Search failed — bridge server may be offline. Check that the FDA bridge is running on port 18790.
          </div>
        )}

        {/* Results */}
        {search.data && (
          <>
            <div className="flex items-center justify-between mb-2">
              <p className="text-[10px] text-muted-foreground">
                {search.data.total} result{search.data.total !== 1 ? "s" : ""} for &ldquo;{submitted}&rdquo;
                &nbsp;·&nbsp;{search.data.duration_ms.toFixed(0)}ms
                &nbsp;·&nbsp;{search.data.sources_searched.join(", ")}
              </p>
            </div>
            {search.data.results.length === 0 ? (
              <p className="text-[11px] text-muted-foreground text-center py-8">
                No results found. Try different keywords or add more data sources.
              </p>
            ) : (
              search.data.results.map((hit, i) => (
                <SearchResultCard key={`${hit.source}-${hit.id}-${i}`} hit={hit} />
              ))
            )}
          </>
        )}
      </div>
    </div>
  );
}

// ── Main page ───────────────────────────────────────────────────────────────

export default function ResearchPage() {
  const [activeTab, setActiveTab] = useState<TabId>("predicates");
  const [_selectedKNumber, setSelectedKNumber] = useState<string | null>(null);

  return (
    <div className="flex h-[calc(100vh-64px)] bg-background">
      {/* Left tab rail */}
      <nav
        aria-label="Research Hub tabs"
        className="w-14 md:w-14 border-r border-border flex flex-col items-center py-3 gap-1 shrink-0 bg-muted/20"
      >
        {TABS.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            title={tab.label}
            aria-label={tab.label}
            aria-current={activeTab === tab.id ? "page" : undefined}
            className={cn(
              "w-10 h-10 rounded-lg flex items-center justify-center text-[16px] transition-colors cursor-pointer",
              activeTab === tab.id
                ? "bg-[#005EA2]/10 text-[#005EA2]"
                : "text-muted-foreground hover:text-foreground hover:bg-muted",
            )}
          >
            {tab.icon}
          </button>
        ))}
      </nav>

      {/* Tab content */}
      <main className="flex-1 overflow-hidden">
        {/* Search */}
        {activeTab === "search" && (
          <SearchPanel />
        )}

        {/* Predicates — split: left = PredicateSelection, right = EvidenceChainViewer */}
        {activeTab === "predicates" && (
          <div className="flex h-full">
            <div className="w-[400px] border-r border-border flex-shrink-0 h-full overflow-hidden">
              <div className="px-4 pt-3 pb-2 border-b border-border">
                <h2 className="text-sm font-semibold text-foreground">Predicate Search</h2>
                <p className="text-[10px] text-muted-foreground mt-0.5">
                  Cosine-similarity ranked candidates
                </p>
              </div>
              <PredicateSelection
                predicates={DEMO_PREDICATES}
                onViewDetails={(k) => setSelectedKNumber(k)}
                onCompare={(selected) => console.log("Compare", selected.map(p => p.kNumber))}
                className="h-[calc(100%-52px)]"
              />
            </div>

            <div className="flex-1 overflow-y-auto p-4">
              <EvidenceChainViewer
                claims={DEMO_CLAIMS}
                onNodeClick={(id, type) => console.log("Node clicked", id, type)}
                onExport={(citations) => console.log("Export", citations.length, "citations")}
              />
            </div>
          </div>
        )}

        {/* Guidance — split: left = Dendrogram, right = GuidanceInlineViewer */}
        {activeTab === "guidance" && (
          <div className="flex h-full">
            <div className="w-[320px] border-r border-border flex-shrink-0 h-full overflow-hidden">
              <GuidanceDendrogram
                clusters={DEMO_CLUSTERS}
                onSelectDocument={(id) => console.log("Selected guidance doc", id)}
                className="h-full"
              />
            </div>

            <div className="flex-1 h-full overflow-hidden">
              <GuidanceInlineViewer
                title="Infusion Pumps 510(k) Submissions"
                reference="FDA-2014-D-0798"
                docType="guidance"
                pdfUrl="#"
                totalPages={24}
                highlights={DEMO_PASSAGES}
                annotations={DEMO_ANNOTATIONS}
                related={DEMO_RELATED}
                onCiteCopied={(citation) => console.log("Cite", citation.slice(0, 30))}
                className="h-full"
              />
            </div>
          </div>
        )}

        {/* Signals — full width */}
        {activeTab === "signals" && (
          <SignalDashboard
            signals={DEMO_SIGNALS}
            productCodes={["FRN", "KZE", "OZO"]}
            cusumAlarm={5}
            onExport={() => console.log("Exported signals CSV")}
            className="h-full"
          />
        )}

        {/* Citations — full width */}
        {activeTab === "citations" && (
          <CitationManager
            citations={DEMO_CITATIONS}
            submissionSections={[
              { id: "s3", label: "Device Description §3" },
              { id: "s4", label: "SE Discussion §2.1" },
              { id: "s5", label: "Testing §4.2" },
              { id: "s6", label: "Labeling §7" },
            ]}
            onRemove={(id) => console.log("Remove", id)}
            className="h-full"
          />
        )}
      </main>
    </div>
  );
}
