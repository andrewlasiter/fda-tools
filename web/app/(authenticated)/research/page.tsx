"use client";

/**
 * FDA-274 [FE-020] + FDA-290 [RH-003] — Regulatory Research Hub
 * ==============================================================
 * /research — Unified semantic search + predicate comparison panel.
 *
 * Tabs:
 *   Search        — Unified semantic search across all FDA data sources
 *   Predicates    — SE comparison table with inline evidence popovers  ← NEW
 *   Guidance      — Guidance document browser
 *   Safety        — CUSUM signal dashboard
 */

import React, { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { PredicateComparisonTable } from "@/components/predicate/predicate-comparison-table";
import type { AttributeRow, PredicateColumn } from "@/components/predicate/predicate-comparison-table";

// ── Source types ──────────────────────────────────────────────────────────

type SourceKey = "k510" | "guidance" | "maude" | "recalls" | "pubmed";

const SOURCES: { key: SourceKey; label: string; count: string }[] = [
  { key: "k510",     label: "510(k) DB",  count: "220K+"  },
  { key: "guidance", label: "Guidance",    count: "1,200+" },
  { key: "maude",    label: "MAUDE",       count: "11M+"   },
  { key: "recalls",  label: "Recalls",     count: "35K+"   },
  { key: "pubmed",   label: "PubMed",      count: "35M+"   },
];

const SOURCE_COLORS: Record<SourceKey, string> = {
  k510:     "text-[#005EA2]   bg-[#005EA2]/10",
  guidance: "text-[#1A7F4B]   bg-[#1A7F4B]/10",
  maude:    "text-[#B45309]   bg-[#B45309]/10",
  recalls:  "text-destructive bg-destructive/10",
  pubmed:   "text-purple-700  bg-purple-100 dark:text-purple-300 dark:bg-purple-900/30",
};

const MOCK_RESULTS = [
  { id:"r1", source:"k510",     title:"K193726 — GlucoSense Pro (DQY)", date:"2019-08-14", relevance:0.94, snippet:"Continuous glucose monitor with subcutaneous sensor. Substantially equivalent to K180822..." },
  { id:"r2", source:"guidance", title:"Design Considerations for CGM Devices", date:"2016-09-27", relevance:0.91, snippet:"This guidance discusses design considerations for blood glucose monitoring devices including performance testing..." },
  { id:"r3", source:"k510",     title:"K220031 — FlexSensor DUO (DQY)", date:"2022-03-10", relevance:0.88, snippet:"Wearable CGM system cleared via traditional 510(k). Predicate chain: K193726 → K220031..." },
  { id:"r4", source:"maude",    title:"CGM Sensor Adhesion Failure Reports", date:"2024-11-01", relevance:0.77, snippet:"87 MDR events in Q4 2024 related to sensor adhesion failure for wearable CGM devices (DQY product code)..." },
  { id:"r5", source:"pubmed",   title:"Clinical accuracy of CGM in ICU patients (2024)", date:"2024-07-15", relevance:0.73, snippet:"Prospective study (n=124): CGM MARD vs. reference YSI analyzer. Mean MARD: 8.2% ± 3.1%..." },
];

// ── Predicate comparison mock data ────────────────────────────────────────

const SUBJECT_DEVICE = { name: "NextGen Glucose Monitor", code: "DQY" };

const MOCK_PREDICATES: PredicateColumn[] = [
  {
    id: "pred1",
    kNumber: "K193726",
    name: "GlucoSense Pro",
    company: "SensorTech Inc.",
    cleared: "2019-08-14",
    trust: {
      confidence: 91,
      sourceCount: 4,
      modelId: "claude-sonnet-4-6",
      validatedAt: "2026-02-22T10:00:00Z",
      sources: [
        { label: "K193726 510(k) Summary", type: "510k", section: "Section 4: Device Description" },
        { label: "ISO 15197:2013", type: "standard" },
      ],
    },
  },
  {
    id: "pred2",
    kNumber: "K220031",
    name: "FlexSensor DUO",
    company: "BioWave Medical",
    cleared: "2022-03-10",
    trust: {
      confidence: 78,
      sourceCount: 3,
      modelId: "claude-sonnet-4-6",
      validatedAt: "2026-02-22T10:00:00Z",
      sources: [
        { label: "K220031 510(k) Summary", type: "510k", section: "Section 3: Intended Use" },
        { label: "FDA Guidance: CGM Design", type: "guidance" },
      ],
    },
  },
];

const MOCK_ROWS: AttributeRow[] = [
  // Indications for Use
  {
    id: "r1", group: "Indications for Use", attribute: "Intended Use",
    subject: {
      value: "For use by people with diabetes mellitus to replace fingerstick blood glucose testing",
      evidence: [
        {
          source: { label: "510(k) Draft — Section 2", type: "510k" },
          quote: "The NextGen Glucose Monitor is intended for use by persons with diabetes mellitus to monitor glucose levels and replace fingerstick blood glucose testing for insulin dosing decisions.",
          section: "Section 2: Indications for Use",
          confidence: 95,
          docDate: "2026-01-15",
          kNumber: "Draft",
        },
      ],
    },
    predicates: [
      {
        value: "For monitoring interstitial glucose in people with diabetes (age ≥18)",
        similarity: "similar",
        evidence: [
          {
            source: { label: "K193726 510(k) Summary", type: "510k", section: "Section 3: Indications" },
            quote: "GlucoSense Pro is indicated for the continuous monitoring of interstitial glucose in persons 18 years and older with diabetes mellitus.",
            section: "Section 3: Indications for Use",
            confidence: 92,
            docDate: "2019-08-14",
            kNumber: "K193726",
          },
        ],
      },
      {
        value: "Continuous glucose monitoring for diabetes management; not a replacement for lab tests",
        similarity: "different",
        evidence: [
          {
            source: { label: "K220031 510(k) Summary", type: "510k" },
            quote: "FlexSensor DUO is intended for continuous glucose monitoring as an adjunct to, not a replacement for, standard blood glucose measurements in patients with diabetes.",
            section: "Section 2: Device Description",
            confidence: 88,
            docDate: "2022-03-10",
            kNumber: "K220031",
          },
        ],
      },
    ],
  },
  {
    id: "r2", group: "Indications for Use", attribute: "Age Range",
    subject: {
      value: "Adults and pediatric (≥2 years)",
      evidence: [],
    },
    predicates: [
      { value: "Adults (≥18 years)", similarity: "different", evidence: [] },
      { value: "Adults (≥18 years)", similarity: "different", evidence: [] },
    ],
  },
  {
    id: "r3", group: "Indications for Use", attribute: "Wear Duration",
    subject: {
      value: "Up to 14 days per sensor",
      evidence: [
        {
          source: { label: "Design Validation Report", type: "guidance" },
          quote: "In-vitro and in-vivo testing demonstrated sensor accuracy maintained through 14 days of continuous wear with MARD < 9.0%.",
          section: "Section 5.2: Sensor Wear Duration",
          confidence: 87,
          docDate: "2025-11-10",
        },
      ],
    },
    predicates: [
      { value: "Up to 10 days per sensor", similarity: "similar", evidence: [] },
      { value: "Up to 14 days per sensor", similarity: "identical", evidence: [] },
    ],
  },

  // Technical Specifications
  {
    id: "r4", group: "Technical Specifications", attribute: "Measurement Range",
    subject: {
      value: "40–400 mg/dL",
      evidence: [
        {
          source: { label: "ISO 15197:2013", type: "standard" },
          quote: "The measurement range shall encompass the hypoglycemic range (below 70 mg/dL) and the hyperglycemic range (above 180 mg/dL) with a minimum span of 40–400 mg/dL.",
          section: "Clause 6.1: Measuring interval",
          confidence: 98,
          docDate: "2013-05-15",
        },
      ],
    },
    predicates: [
      { value: "40–400 mg/dL", similarity: "identical", evidence: [] },
      { value: "40–400 mg/dL", similarity: "identical", evidence: [] },
    ],
  },
  {
    id: "r5", group: "Technical Specifications", attribute: "Accuracy (MARD)",
    subject: {
      value: "≤8.5% MARD across all glucose ranges",
      evidence: [
        {
          source: { label: "Clinical Accuracy Study", type: "pubmed" },
          quote: "Overall MARD was 8.2% (95% CI: 7.8–8.6%) with 97.3% of paired values within Zone A+B of Clarke Error Grid.",
          section: "Results: Sensor Accuracy",
          confidence: 91,
          docDate: "2025-09-01",
          doi: "10.1109/JBHI.2025.001234",
        },
      ],
    },
    predicates: [
      {
        value: "≤9.4% MARD",
        similarity: "similar",
        evidence: [
          {
            source: { label: "K193726 Performance Testing", type: "510k" },
            quote: "Accuracy data from clinical study demonstrates MARD of 9.2% across the measurement range, meeting the predefined accuracy acceptance criteria.",
            section: "Section 6: Performance Testing",
            confidence: 89,
            docDate: "2019-06-01",
            kNumber: "K193726",
          },
        ],
      },
      { value: "≤9.0% MARD", similarity: "similar", evidence: [] },
    ],
  },
  {
    id: "r6", group: "Technical Specifications", attribute: "Calibration",
    subject: {
      value: "Factory calibrated, no fingerstick required",
      evidence: [],
    },
    predicates: [
      { value: "Factory calibrated, no fingerstick required", similarity: "identical", evidence: [] },
      { value: "2× daily fingerstick calibration required", similarity: "different", evidence: [] },
    ],
  },

  // Biocompatibility
  {
    id: "r7", group: "Biocompatibility", attribute: "Materials",
    subject: {
      value: "Medical-grade silicone housing; platinum electrode; polyurethane membrane",
      evidence: [
        {
          source: { label: "Biocompatibility Summary", type: "guidance" },
          quote: "All materials in contact with patient tissue have been evaluated per ISO 10993-1. The sensor membrane uses a proprietary polyurethane formulation characterized for biocompatibility.",
          section: "Biocompatibility Summary",
          confidence: 84,
          docDate: "2025-10-01",
        },
      ],
    },
    predicates: [
      { value: "Medical-grade silicone; gold electrode; polyurethane membrane", similarity: "similar", evidence: [] },
      { value: "Medical-grade silicone; platinum electrode; polyurethane membrane", similarity: "identical", evidence: [] },
    ],
  },
  {
    id: "r8", group: "Biocompatibility", attribute: "ISO 10993 Testing",
    subject: {
      value: "Cytotoxicity, sensitization, skin irritation, genotoxicity — all pass",
      evidence: [],
    },
    predicates: [
      { value: "Cytotoxicity, sensitization, irritation — all pass", similarity: "similar", evidence: [] },
      { value: "Full ISO 10993 panel — all pass", similarity: "identical", evidence: [] },
    ],
  },

  // Software
  {
    id: "r9", group: "Software & Connectivity", attribute: "Software Class",
    subject: {
      value: "Class B (IEC 62304); SaMD for insulin dosing support",
      evidence: [
        {
          source: { label: "FDA Guidance: AI/ML-Based SaMD", type: "guidance" },
          quote: "Software that provides insulin dosing recommendations based on CGM data is categorized as Class B under IEC 62304 and requires a Software Development Life Cycle (SDLC) documentation package.",
          section: "Section 3: Software Classification",
          confidence: 93,
          docDate: "2023-10-15",
        },
      ],
    },
    predicates: [
      { value: "Class B (IEC 62304); data display only (no treatment decisions)", similarity: "different", evidence: [] },
      { value: "Class B (IEC 62304); CGM data display and trending", similarity: "different", evidence: [] },
    ],
  },
  {
    id: "r10", group: "Software & Connectivity", attribute: "Wireless Protocol",
    subject: {
      value: "Bluetooth Low Energy 5.2",
      evidence: [],
    },
    predicates: [
      { value: "Bluetooth Low Energy 4.2", similarity: "similar", evidence: [] },
      { value: "Bluetooth Low Energy 5.0", similarity: "similar", evidence: [] },
    ],
  },

  // Sterilization
  {
    id: "r11", group: "Sterilization & Shelf Life", attribute: "Sterilization Method",
    subject: {
      value: "Ethylene oxide (EO) sterilization — sterile, single use",
      evidence: [],
    },
    predicates: [
      { value: "EO sterilization — sterile, single use", similarity: "identical", evidence: [] },
      { value: "Gamma irradiation — sterile, single use", similarity: "similar", evidence: [] },
    ],
  },
  {
    id: "r12", group: "Sterilization & Shelf Life", attribute: "Shelf Life",
    subject: {
      value: "24 months at 15–30°C",
      evidence: [],
    },
    predicates: [
      { value: "18 months at 15–25°C", similarity: "similar", evidence: [] },
      { value: "24 months at 15–30°C", similarity: "identical", evidence: [] },
    ],
  },
];

// ── Tab definition ────────────────────────────────────────────────────────

type Tab = "search" | "predicates" | "guidance" | "safety";

const TABS: { key: Tab; label: string; badge?: string }[] = [
  { key: "search",     label: "Search"              },
  { key: "predicates", label: "Predicates", badge: "NEW" },
  { key: "guidance",   label: "Guidance"             },
  { key: "safety",     label: "Safety Signals"       },
];

// ── Main page ─────────────────────────────────────────────────────────────

export default function ResearchPage() {
  const [tab, setTab]                   = useState<Tab>("search");
  const [query, setQuery]               = useState("");
  const [activeSources, setActiveSources] = useState<Set<SourceKey>>(new Set(["k510","guidance","maude"]));
  const [hasSearched, setHasSearched]   = useState(false);

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
    <div className="p-6 max-w-[1400px] mx-auto space-y-5">

      {/* ── Header ── */}
      <div>
        <h1 className="text-2xl font-bold font-heading text-foreground">Regulatory Research Hub</h1>
        <p className="text-sm text-muted-foreground mt-0.5">Unified semantic search · predicate analysis · guidance browser · safety signals</p>
      </div>

      {/* ── Tabs ── */}
      <div className="border-b border-border">
        <nav className="flex gap-0" role="tablist">
          {TABS.map(t => (
            <button
              key={t.key}
              role="tab"
              aria-selected={tab === t.key}
              onClick={() => setTab(t.key)}
              className={cn(
                "px-5 py-2.5 text-sm font-medium border-b-2 transition-colors flex items-center gap-2",
                tab === t.key
                  ? "border-[#005EA2] text-[#005EA2]"
                  : "border-transparent text-muted-foreground hover:text-foreground hover:border-muted"
              )}
            >
              {t.label}
              {t.badge && (
                <span className="text-[9px] font-bold bg-[#005EA2] text-white px-1.5 py-0.5 rounded">
                  {t.badge}
                </span>
              )}
            </button>
          ))}
        </nav>
      </div>

      {/* ── Search tab ── */}
      {tab === "search" && (
        <div className="space-y-5">
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
                <kbd className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] font-mono text-muted-foreground border border-border rounded px-1.5 py-0.5 bg-muted">↵</kbd>
              </div>
              <Button type="submit" className="h-11 px-6 bg-[#005EA2] hover:bg-[#003E73] text-white">Search</Button>
            </div>
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
                <Button
                  variant="outline"
                  size="sm"
                  className="text-xs border-[#005EA2] text-[#005EA2]"
                  onClick={() => setTab("predicates")}
                >
                  Compare Predicates →
                </Button>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {[
                { title:"Recent Searches",   items:["DQY — glucose monitors","GEI — electrosurgical","QKQ — digital pathology"] },
                { title:"Trending Guidance", items:["Predetermined Change Control Plans","AI/ML-Based SaMD","Cybersecurity — 2023 Final"] },
                { title:"Safety Signals",    items:["CGM adhesion failures (DQY)","Robotic surgery anomalies","Implant connectivity issues"] },
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
      )}

      {/* ── Predicates tab ── */}
      {tab === "predicates" && (
        <div className="space-y-4">
          {/* Contextual header */}
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="text-sm font-semibold text-foreground">Substantive Equivalence Comparison</h2>
              <p className="text-xs text-muted-foreground mt-0.5">
                {SUBJECT_DEVICE.name} ({SUBJECT_DEVICE.code}) vs {MOCK_PREDICATES.length} predicate devices ·
                Click any cell to view documentary evidence
              </p>
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              <button className="text-[11px] text-[#005EA2] hover:underline font-medium">+ Add Predicate</button>
              <span className="text-border">|</span>
              <button className="text-[11px] text-muted-foreground hover:text-foreground">Filter Attributes</button>
            </div>
          </div>

          {/* Comparison table */}
          <PredicateComparisonTable
            subject={SUBJECT_DEVICE}
            predicates={MOCK_PREDICATES}
            rows={MOCK_ROWS}
          />

          {/* Action bar */}
          <div className="flex items-center gap-3 pt-2 border-t border-border">
            <Button className="bg-[#005EA2] hover:bg-[#003E73] text-white" size="sm">
              Generate SE Summary
            </Button>
            <Button variant="outline" size="sm">View Evidence Chain</Button>
            <Button variant="outline" size="sm">Export to eSTAR</Button>
            <span className="ml-auto text-[11px] text-muted-foreground">
              {MOCK_ROWS.length} attributes · {MOCK_PREDICATES.length} predicates · FDA-285
            </span>
          </div>
        </div>
      )}

      {/* ── Guidance tab ── */}
      {tab === "guidance" && (
        <div className="flex items-center justify-center py-20 text-center">
          <div>
            <p className="text-muted-foreground text-sm">Guidance Document Inline Viewer</p>
            <p className="text-xs text-muted-foreground mt-1">Coming in Sprint 25 · FDA-288</p>
            <Button className="mt-4" variant="outline" size="sm" onClick={() => setTab("predicates")}>
              ← Try Predicate Comparison
            </Button>
          </div>
        </div>
      )}

      {/* ── Safety signals tab ── */}
      {tab === "safety" && (
        <div className="flex items-center justify-center py-20 text-center">
          <div>
            <p className="text-muted-foreground text-sm">CUSUM Safety Signal Dashboard</p>
            <p className="text-xs text-muted-foreground mt-1">Integrated in Sprint 25 · FDA-248</p>
            <Button className="mt-4" variant="outline" size="sm" onClick={() => setTab("search")}>
              ← Back to Search
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
