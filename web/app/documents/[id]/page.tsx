"use client";

/**
 * FDA-295 [DOC-UI-001] — /documents/[id] page
 * =============================================
 * Document Studio: DocumentEditor + AISuggestionOverlay wired into a full page.
 *
 * Layout:
 *   Left sidebar (200px): eSTAR section navigator (12 sections)
 *   Main: DocumentEditor component (full-height)
 *   Right panel (300px, collapsible): AISuggestionOverlay
 *   Footer: word count, last saved, 21 CFR Part 11 audit timestamp, export button
 */

import React, { useState } from "react";
import { cn } from "@/lib/utils";
import { DocumentEditor, ESTAR_SECTIONS, type EditorSection } from "@/components/editor/document-editor";
import { AISuggestionOverlay, type AISuggestion } from "@/components/editor/ai-suggestion-overlay";

// ── Full EditorSection list (maps Omit<> → full type) ────────────────────────

const FULL_SECTIONS: EditorSection[] = ESTAR_SECTIONS.map(s => ({
  ...s,
  content:     "",
  completed:   false,
  aiSuggCount: 0,
}));

// ── Demo suggestions ─────────────────────────────────────────────────────────

const DEMO_SUGGESTIONS: AISuggestion[] = [
  {
    id: "s1", sectionId: "s3", paragraphIndex: 0, agentName: "fda-drafting-agent",
    category: "regulatory", confidence: 88,
    timestamp: new Date().toISOString(), status: "pending",
    original: "The device is a pump.",
    proposed: "The SmartFlow Infusion Pump (Model SFP-2024) is a peristaltic infusion pump intended for the continuous and intermittent delivery of intravenous fluids and medications in adult patients in acute care settings.",
    rationale: "FDA guidance recommends a complete device description with model number, mechanism, intended use, and patient population in the first paragraph of the device description section.",
    regulationRefs: ["21 CFR 807.92(a)(1)", "FDA Guidance: Infusion Pumps 510(k) §III.A"],
  },
  {
    id: "s2", sectionId: "s3", paragraphIndex: 2, agentName: "fda-se-agent",
    category: "completeness", confidence: 74,
    timestamp: new Date().toISOString(), status: "pending",
    original: "The device is similar to the predicate.",
    proposed: "The subject device is substantially equivalent to predicate K231045 (SmartFlow Infusion Pump Pro, MedDevice Corp, 2023) based on: (1) identical intended use — continuous IV infusion in adult acute care patients; (2) same technological characteristics — peristaltic pumping mechanism with equivalent flow accuracy (±2% vs ±1.8%); (3) same physical interface — standard IV tubing sets.",
    rationale: "SE claims must identify the predicate by K-number and clearance holder, and explicitly address intended use and technological characteristics per 21 CFR 807.87(f).",
    regulationRefs: ["21 CFR 807.87(f)", "21 CFR 807.92(a)(5)"],
  },
];

// ── Section sidebar item ─────────────────────────────────────────────────────

function SectionItem({
  section,
  active,
  onClick,
}: {
  section: EditorSection;
  active:  boolean;
  onClick: () => void;
}) {
  const completeness =
    section.completed        ? { label: "Done",  dot: "bg-[#1A7F4B]" } :
    (section.aiSuggCount ?? 0) > 0 ? { label: "AI",    dot: "bg-[#005EA2]" } :
    section.required         ? { label: "Draft", dot: "bg-[#B45309]" } :
                               { label: "N/A",   dot: "bg-muted"     };

  return (
    <button
      onClick={onClick}
      className={cn(
        "w-full text-left flex items-center gap-2 px-3 py-2 transition-colors cursor-pointer border-r-2",
        active
          ? "bg-[#005EA2]/8 border-[#005EA2]"
          : "border-transparent hover:bg-muted/50",
      )}
    >
      <div className={cn("w-1.5 h-1.5 rounded-full flex-shrink-0", completeness.dot)} />
      <span className={cn("text-[11px] truncate flex-1", active ? "text-[#005EA2] font-medium" : "text-foreground")}>
        {section.shortLabel}
      </span>
      {section.required && (
        <span className="text-[8px] text-muted-foreground flex-shrink-0">req</span>
      )}
    </button>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function DocumentStudioPage({
  params: _params,
}: {
  params: { id: string };
}) {
  const [activeSectionId, setActiveSectionId] = useState<string>(FULL_SECTIONS[0].id);
  const [suggestionsOpen, setSuggestionsOpen] = useState(true);
  const [savedAt,         setSavedAt]         = useState<string | null>(null);
  const [wordCount]                           = useState(0);

  const totalComplete = FULL_SECTIONS.filter(s => s.completed).length;

  return (
    <div className="flex h-[calc(100vh-64px)] bg-background">
      {/* Left: section navigator */}
      <nav
        aria-label="eSTAR section navigator"
        className="w-[190px] border-r border-border flex flex-col shrink-0 overflow-y-auto bg-muted/10"
      >
        <div className="px-3 py-3 border-b border-border shrink-0">
          <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Sections</p>
          <div className="mt-1 flex items-center gap-1.5">
            <div className="flex-1 h-1 rounded-full bg-muted overflow-hidden">
              <div
                className="h-full bg-[#1A7F4B] rounded-full transition-all"
                style={{ width: `${(totalComplete / FULL_SECTIONS.length) * 100}%` }}
              />
            </div>
            <span className="text-[9px] text-muted-foreground">{totalComplete}/{FULL_SECTIONS.length}</span>
          </div>
        </div>
        <div className="flex-1 py-1">
          {FULL_SECTIONS.map(section => (
            <SectionItem
              key={section.id}
              section={section}
              active={section.id === activeSectionId}
              onClick={() => setActiveSectionId(section.id)}
            />
          ))}
        </div>
      </nav>

      {/* Main: document editor */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <DocumentEditor
          sections={FULL_SECTIONS}
          onSave={(sectionId, content) => {
            setSavedAt(new Date().toLocaleTimeString());
            console.log("Saved section", sectionId, content.length, "chars");
          }}
          className="flex-1"
        />

        {/* Footer bar */}
        <div className="border-t border-border px-4 py-2 flex items-center gap-4 text-[10px] text-muted-foreground bg-background shrink-0 flex-wrap">
          <span className="font-mono">{wordCount.toLocaleString()} words</span>
          {savedAt && <span>Saved {savedAt}</span>}
          <span className="text-[9px]">21 CFR Part 11 audit: active</span>
          <div className="ml-auto flex items-center gap-2">
            <button
              onClick={() => setSuggestionsOpen(v => !v)}
              className={cn(
                "px-2.5 py-1 border rounded text-[10px] font-medium transition-colors cursor-pointer",
                suggestionsOpen
                  ? "bg-[#005EA2]/10 border-[#005EA2]/30 text-[#005EA2]"
                  : "border-border hover:bg-muted",
              )}
            >
              {suggestionsOpen ? "Hide AI" : "Show AI"}
            </button>
            <button className="px-2.5 py-1 bg-[#005EA2] text-white border border-[#005EA2] rounded text-[10px] font-medium hover:bg-[#005EA2]/90 transition-colors cursor-pointer">
              Export eSTAR
            </button>
          </div>
        </div>
      </div>

      {/* Right: AI suggestions panel */}
      {suggestionsOpen && (
        <div className="w-[290px] border-l border-border flex-shrink-0 h-full overflow-hidden">
          <AISuggestionOverlay
            suggestions={DEMO_SUGGESTIONS}
            sectionId={activeSectionId}
            onAccept={(id, finalText) => console.log("Accepted suggestion", id, finalText.slice(0, 20))}
            onReject={(id, reason) => console.log("Rejected suggestion", id, reason)}
            className="h-full"
          />
        </div>
      )}
    </div>
  );
}
