"use client";

/**
 * FDA-274 [FE-020] — Regulatory Research Hub
 * ============================================
 * /research — Unified semantic search across all FDA data sources.
 */

import React, { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type SourceKey = "k510" | "guidance" | "maude" | "recalls" | "pubmed";

const SOURCES: { key: SourceKey; label: string; count: string }[] = [
  { key: "k510",     label: "510(k) DB",    count: "220K+"   },
  { key: "guidance", label: "Guidance",      count: "1,200+"  },
  { key: "maude",    label: "MAUDE",         count: "11M+"    },
  { key: "recalls",  label: "Recalls",       count: "35K+"    },
  { key: "pubmed",   label: "PubMed",        count: "35M+"    },
];

const MOCK_RESULTS = [
  { id:"r1", source:"k510",     title:"K193726 — GlucoSense Pro (DQY)", date:"2019-08-14", relevance:0.94, snippet:"Continuous glucose monitor with subcutaneous sensor. Substantially equivalent to K180822..." },
  { id:"r2", source:"guidance", title:"Design Considerations for CGM Devices",date:"2016-09-27",relevance:0.91,snippet:"This guidance discusses design considerations for blood glucose monitoring devices including performance testing..." },
  { id:"r3", source:"k510",     title:"K220031 — FlexSensor DUO (DQY)", date:"2022-03-10", relevance:0.88, snippet:"Wearable CGM system cleared via traditional 510(k). Predicate chain: K193726 → K220031..." },
  { id:"r4", source:"maude",    title:"CGM Sensor Adhesion Failure Reports", date:"2024-11-01", relevance:0.77, snippet:"87 MDR events in Q4 2024 related to sensor adhesion failure for wearable CGM devices (DQY product code)..." },
  { id:"r5", source:"pubmed",   title:"Clinical accuracy of CGM in ICU patients (2024)", date:"2024-07-15", relevance:0.73, snippet:"Prospective study (n=124): CGM MARD vs. reference YSI analyzer. Mean MARD: 8.2% ± 3.1%..." },
];

const SOURCE_COLORS: Record<SourceKey, string> = {
  k510:     "text-[#005EA2]   bg-[#005EA2]/10",
  guidance: "text-[#1A7F4B]   bg-[#1A7F4B]/10",
  maude:    "text-[#B45309]   bg-[#B45309]/10",
  recalls:  "text-destructive bg-destructive/10",
  pubmed:   "text-purple-700  bg-purple-100 dark:text-purple-300 dark:bg-purple-900/30",
};

export default function ResearchPage() {
  const [query, setQuery] = useState("");
  const [activeSources, setActiveSources] = useState<Set<SourceKey>>(new Set(["k510","guidance","maude"]));
  const [hasSearched, setHasSearched] = useState(false);

  function toggleSource(key: SourceKey) {
    setActiveSources(prev => {
      const next = new Set(prev);
      next.has(key) ? next.delete(key) : next.add(key);
      return next;
    });
  }

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (query.trim()) setHasSearched(true);
  }

  const results = hasSearched
    ? MOCK_RESULTS.filter(r => activeSources.has(r.source as SourceKey))
    : [];

  return (
    <div className="p-6 max-w-[1200px] mx-auto space-y-6">

      {/* ── Header ──────────────────────────────────────────────────── */}
      <div>
        <h1 className="text-2xl font-bold font-heading text-foreground">Regulatory Research Hub</h1>
        <p className="text-sm text-muted-foreground mt-0.5">Unified semantic search across all FDA data sources</p>
      </div>

      {/* ── Search bar ──────────────────────────────────────────────── */}
      <form onSubmit={handleSearch}>
        <div className="flex gap-3">
          <div className="flex-1 relative">
            <input
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder="Search: device name, product code, standard, or clinical term..."
              className={cn(
                "w-full h-11 px-4 pr-12 text-sm rounded-lg border border-border bg-background",
                "focus:outline-none focus:ring-2 focus:ring-[#005EA2]/30 focus:border-[#005EA2]",
                "placeholder:text-muted-foreground transition-all"
              )}
            />
            <kbd className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] font-mono text-muted-foreground border border-border rounded px-1.5 py-0.5 bg-muted">
              ↵
            </kbd>
          </div>
          <Button
            type="submit"
            className="h-11 px-6 bg-[#005EA2] hover:bg-[#003E73] text-white"
          >
            Search
          </Button>
        </div>

        {/* Source toggles */}
        <div className="flex items-center gap-2 mt-3 flex-wrap">
          <span className="text-xs text-muted-foreground">Sources:</span>
          {SOURCES.map(src => (
            <button
              key={src.key}
              type="button"
              onClick={() => toggleSource(src.key)}
              className={cn(
                "text-xs px-3 py-1 rounded-full border transition-all",
                activeSources.has(src.key)
                  ? "border-[#005EA2] bg-[#005EA2]/10 text-[#005EA2]"
                  : "border-border text-muted-foreground hover:border-foreground"
              )}
            >
              {src.label} <span className="opacity-60">{src.count}</span>
            </button>
          ))}
        </div>
      </form>

      {/* ── Results ─────────────────────────────────────────────────── */}
      {hasSearched ? (
        <div className="space-y-3">
          <p className="text-xs text-muted-foreground">{results.length} results for &ldquo;{query}&rdquo;</p>
          {results.map(r => (
            <Card key={r.id} className="hover:shadow-md transition-shadow cursor-pointer">
              <CardContent className="py-4 px-5">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={cn("text-[10px] font-bold px-1.5 py-0.5 rounded", SOURCE_COLORS[r.source as SourceKey])}>
                        {r.source.toUpperCase()}
                      </span>
                      <span className="text-[10px] text-muted-foreground">{r.date}</span>
                    </div>
                    <h3 className="text-sm font-semibold text-foreground">{r.title}</h3>
                    <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{r.snippet}</p>
                  </div>
                  <div className="flex-shrink-0 text-right">
                    <div className="text-sm font-bold text-[#005EA2]">{Math.round(r.relevance * 100)}%</div>
                    <div className="text-[9px] text-muted-foreground">relevance</div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
          <div className="flex gap-2 pt-2">
            <Button variant="outline" size="sm" className="text-xs">Export CSV</Button>
            <Button variant="outline" size="sm" className="text-xs">Export PDF</Button>
            <Button variant="outline" size="sm" className="text-xs">Compare Predicates</Button>
          </div>
        </div>
      ) : (
        /* Empty state / suggestions */
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[
            { title:"Recent 510(k) Searches", items:["DQY — glucose monitors","GEI — electrosurgical","QKQ — digital pathology"] },
            { title:"Trending Guidance",      items:["Predetermined Change Control Plans","AI/ML-Based SaMD","Cybersecurity — 2023 Final"] },
            { title:"Safety Signals",         items:["CGM adhesion failures (DQY)","Robotic surgery anomalies","Implant connectivity issues"] },
          ].map(section => (
            <Card key={section.title}>
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">{section.title}</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2">
                  {section.items.map(item => (
                    <li key={item}>
                      <button
                        onClick={() => { setQuery(item); setHasSearched(true); }}
                        className="text-xs text-foreground hover:text-[#005EA2] transition-colors text-left"
                      >
                        → {item}
                      </button>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
