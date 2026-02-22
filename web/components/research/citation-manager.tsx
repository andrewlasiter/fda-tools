"use client";

/**
 * FDA-289 [RH-002] — CitationManager
 * =====================================
 * Per-project research library for saving and organising citations
 * from any search result, predicate lookup, or guidance passage.
 *
 * Features:
 *   - Citation card: title, source, date, relevance, user note
 *   - Tag system: predicate / standard / safety / clinical / labeling
 *   - Export: NLM or APA formatted reference list (text download)
 *   - Link citations to submission sections (section-ID association)
 *   - Citation completeness check: are all standards cited in submission?
 *   - Sort by: date added / relevance / source type
 *   - Filter by tag / linked section / completeness status
 *   - Inline note editing per citation
 */

import React, { useState, useMemo, useCallback } from "react";
import { cn } from "@/lib/utils";

// ── Types ──────────────────────────────────────────────────────────────────

export type CitationTag =
  | "predicate"
  | "standard"
  | "safety"
  | "clinical"
  | "labeling"
  | "biocompatibility"
  | "software";

export type CitationSourceType =
  | "510k"
  | "guidance"
  | "pubmed"
  | "standard"
  | "internal"
  | "recall"
  | "maude";

export type CitationSortKey = "date_added" | "relevance" | "source_type" | "title";

export interface Citation {
  id:              string;
  title:           string;
  source:          string;           // formatted source string (journal, K-number, etc.)
  sourceType:      CitationSourceType;
  date?:           string;           // publication/clearance date (ISO)
  relevance:       number;           // 0–100
  url?:            string;
  tags:            CitationTag[];
  note?:           string;
  linkedSections:  string[];         // submission section IDs
  addedAt:         string;           // ISO 8601
  inSubmission?:   boolean;          // is this citation already cited in the draft?
}

export interface CitationManagerProps {
  citations:          Citation[];
  submissionSections?: { id: string; label: string }[];
  onAdd?:             (citation: Omit<Citation, "id" | "addedAt">) => void;
  onRemove?:          (id: string) => void;
  onUpdateNote?:      (id: string, note: string) => void;
  onLinkSection?:     (id: string, sectionId: string) => void;
  onUnlinkSection?:   (id: string, sectionId: string) => void;
  onExport?:          (format: "nlm" | "apa", citations: Citation[]) => void;
  className?:         string;
}

// ── Config ─────────────────────────────────────────────────────────────────

const TAG_CONFIG: Record<CitationTag, { label: string; color: string; bg: string }> = {
  predicate:        { label: "Predicate",       color: "#005EA2", bg: "bg-[#005EA2]/10" },
  standard:         { label: "Standard",        color: "#1A7F4B", bg: "bg-[#1A7F4B]/10" },
  safety:           { label: "Safety",          color: "#C5191B", bg: "bg-[#C5191B]/10" },
  clinical:         { label: "Clinical",        color: "#7C3AED", bg: "bg-[#7C3AED]/10" },
  labeling:         { label: "Labeling",        color: "#B45309", bg: "bg-[#B45309]/10" },
  biocompatibility: { label: "Biocompat.",      color: "#B45309", bg: "bg-[#B45309]/10" },
  software:         { label: "Software",        color: "#1A7F4B", bg: "bg-[#1A7F4B]/10" },
};

const SOURCE_TYPE_CONFIG: Record<CitationSourceType, { label: string; abbrev: string }> = {
  "510k":    { label: "510(k)",      abbrev: "K"  },
  guidance:  { label: "Guidance",    abbrev: "G"  },
  pubmed:    { label: "PubMed",      abbrev: "PM" },
  standard:  { label: "Standard",   abbrev: "S"  },
  internal:  { label: "Internal",   abbrev: "I"  },
  recall:    { label: "Recall",     abbrev: "R"  },
  maude:     { label: "MAUDE",      abbrev: "M"  },
};

// ── Citation formatter ─────────────────────────────────────────────────────

function formatNLM(c: Citation): string {
  const year = c.date ? new Date(c.date).getFullYear() : "n.d.";
  return `${c.title}. ${c.source}. ${year}.${c.url ? ` Available from: ${c.url}` : ""}`;
}

function formatAPA(c: Citation): string {
  const year = c.date ? new Date(c.date).getFullYear() : "n.d.";
  return `${c.title} (${year}). ${c.source}.${c.url ? ` ${c.url}` : ""}`;
}

// ── CitationCard ───────────────────────────────────────────────────────────

function CitationCard({
  citation,
  sections,
  onRemove,
  onUpdateNote,
  onLinkSection,
  onUnlinkSection,
}: {
  citation:        Citation;
  sections:        { id: string; label: string }[];
  onRemove:        (id: string) => void;
  onUpdateNote:    (id: string, note: string) => void;
  onLinkSection:   (id: string, sectionId: string) => void;
  onUnlinkSection: (id: string, sectionId: string) => void;
}) {
  const [editingNote, setEditingNote] = useState(false);
  const [noteText,    setNoteText]    = useState(citation.note ?? "");
  const [showLink,    setShowLink]    = useState(false);

  const stcfg = SOURCE_TYPE_CONFIG[citation.sourceType];
  const relevColor =
    citation.relevance >= 80 ? "#1A7F4B" :
    citation.relevance >= 55 ? "#B45309" :
    "#C5191B";

  return (
    <div className={cn(
      "rounded-xl border overflow-hidden",
      citation.inSubmission ? "border-[#1A7F4B]/30" : "border-border",
    )}>
      {/* Header */}
      <div className="flex items-start gap-3 px-4 py-3">
        <div className="w-7 h-7 rounded bg-muted flex items-center justify-center flex-shrink-0">
          <span className="text-[10px] font-bold text-muted-foreground">{stcfg.abbrev}</span>
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-start gap-2 flex-wrap">
            <p className="text-[11px] font-bold text-foreground leading-snug flex-1">
              {citation.title}
            </p>
            {citation.inSubmission && (
              <span className="text-[9px] font-bold bg-[#1A7F4B]/10 text-[#1A7F4B] px-1.5 py-0.5 rounded flex-shrink-0">
                ✓ Cited
              </span>
            )}
          </div>
          <p className="text-[10px] text-muted-foreground mt-0.5">{citation.source}</p>
          <div className="flex items-center gap-2 mt-1 flex-wrap">
            <span className="text-[9px] text-muted-foreground">{stcfg.label}</span>
            {citation.date && (
              <span className="text-[9px] text-muted-foreground">
                {new Date(citation.date).getFullYear()}
              </span>
            )}
            <span className="text-[9px] font-mono flex-shrink-0" style={{ color: relevColor }}>
              {citation.relevance}%
            </span>
          </div>
        </div>

        <button
          onClick={() => onRemove(citation.id)}
          className="text-[10px] text-muted-foreground hover:text-destructive flex-shrink-0 cursor-pointer transition-colors"
          aria-label="Remove citation"
        >
          ✕
        </button>
      </div>

      {/* Tags */}
      {citation.tags.length > 0 && (
        <div className="px-4 pb-2 flex flex-wrap gap-1">
          {citation.tags.map(tag => {
            const tcfg = TAG_CONFIG[tag];
            return (
              <span
                key={tag}
                className={cn("text-[9px] font-medium px-1.5 py-0.5 rounded", tcfg.bg)}
                style={{ color: tcfg.color }}
              >
                {tcfg.label}
              </span>
            );
          })}
        </div>
      )}

      {/* Linked sections */}
      {citation.linkedSections.length > 0 && (
        <div className="px-4 pb-2 flex items-center gap-2 flex-wrap">
          <span className="text-[9px] text-muted-foreground">Linked to:</span>
          {citation.linkedSections.map(sid => {
            const sec = sections.find(s => s.id === sid);
            return (
              <span key={sid} className="flex items-center gap-1">
                <span className="text-[9px] font-mono text-[#005EA2] bg-[#005EA2]/10 px-1.5 py-0.5 rounded">
                  {sec?.label ?? sid}
                </span>
                <button
                  onClick={() => onUnlinkSection(citation.id, sid)}
                  className="text-[9px] text-muted-foreground hover:text-destructive cursor-pointer"
                >
                  ✕
                </button>
              </span>
            );
          })}
        </div>
      )}

      {/* Note */}
      <div className="px-4 pb-3">
        {editingNote ? (
          <div className="space-y-2">
            <textarea
              value={noteText}
              onChange={e => setNoteText(e.target.value)}
              rows={2}
              placeholder="Add a note…"
              className="w-full px-2.5 py-1.5 text-[11px] rounded border border-border bg-background outline-none resize-none text-foreground placeholder:text-muted-foreground"
              autoFocus
            />
            <div className="flex gap-2">
              <button
                onClick={() => setEditingNote(false)}
                className="text-[10px] text-muted-foreground cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={() => { onUpdateNote(citation.id, noteText); setEditingNote(false); }}
                className="text-[10px] text-[#005EA2] hover:underline font-medium cursor-pointer"
              >
                Save
              </button>
            </div>
          </div>
        ) : (
          <div className="flex items-start gap-2">
            {citation.note || noteText ? (
              <p className="text-[10px] text-muted-foreground italic flex-1">{noteText || citation.note}</p>
            ) : (
              <span className="text-[10px] text-muted-foreground/50 flex-1">No note</span>
            )}
            <button
              onClick={() => setEditingNote(true)}
              className="text-[9px] text-muted-foreground hover:text-[#005EA2] flex-shrink-0 cursor-pointer"
            >
              {noteText || citation.note ? "Edit" : "Add note"}
            </button>
          </div>
        )}
      </div>

      {/* Section link form */}
      {showLink && (
        <div className="px-4 pb-3 border-t border-border/50 pt-2">
          <p className="text-[9px] text-muted-foreground mb-1.5">Link to submission section:</p>
          <div className="flex flex-wrap gap-1.5">
            {sections
              .filter(s => !citation.linkedSections.includes(s.id))
              .map(s => (
                <button
                  key={s.id}
                  onClick={() => { onLinkSection(citation.id, s.id); setShowLink(false); }}
                  className="text-[9px] px-2 py-1 rounded border border-border hover:border-[#005EA2]/40 hover:bg-[#005EA2]/5 text-muted-foreground hover:text-[#005EA2] transition-colors cursor-pointer"
                >
                  {s.label}
                </button>
              ))
            }
          </div>
        </div>
      )}

      {/* Footer actions */}
      <div className="px-4 py-2 border-t border-border/50 flex items-center gap-3 bg-muted/20">
        <button
          onClick={() => setShowLink(s => !s)}
          className="text-[10px] text-muted-foreground hover:text-[#005EA2] font-medium cursor-pointer transition-colors"
        >
          {showLink ? "Cancel" : "Link to section"}
        </button>
        <time className="ml-auto text-[9px] text-muted-foreground" dateTime={citation.addedAt}>
          Added {new Date(citation.addedAt).toLocaleDateString()}
        </time>
      </div>
    </div>
  );
}

// ── Main Component ─────────────────────────────────────────────────────────

export function CitationManager({
  citations: initialCitations,
  submissionSections = [],
  onRemove,
  onUpdateNote,
  onLinkSection,
  onUnlinkSection,
  onExport,
  className,
}: CitationManagerProps) {
  const [citations,   setCitations]   = useState<Citation[]>(initialCitations);
  const [tagFilter,   setTagFilter]   = useState<CitationTag | "all">("all");
  const [sortKey,     setSortKey]     = useState<CitationSortKey>("date_added");
  const [searchQuery, setSearchQuery] = useState("");
  const [exportFmt,   setExportFmt]   = useState<"nlm" | "apa">("nlm");

  const filtered = useMemo(() => {
    let list = citations;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      list = list.filter(c =>
        c.title.toLowerCase().includes(q) ||
        c.source.toLowerCase().includes(q) ||
        (c.note ?? "").toLowerCase().includes(q),
      );
    }
    if (tagFilter !== "all") {
      list = list.filter(c => c.tags.includes(tagFilter));
    }
    return [...list].sort((a, b) => {
      switch (sortKey) {
        case "date_added":  return new Date(b.addedAt).getTime() - new Date(a.addedAt).getTime();
        case "relevance":   return b.relevance - a.relevance;
        case "source_type": return a.sourceType.localeCompare(b.sourceType);
        case "title":       return a.title.localeCompare(b.title);
        default:            return 0;
      }
    });
  }, [citations, tagFilter, sortKey, searchQuery]);

  // Completeness check: missing from submission
  const missingFromSubmission = useMemo(
    () => citations.filter(c => c.tags.includes("standard") && !c.inSubmission),
    [citations],
  );

  const handleRemove = useCallback((id: string) => {
    setCitations(cs => cs.filter(c => c.id !== id));
    onRemove?.(id);
  }, [onRemove]);

  const handleUpdateNote = useCallback((id: string, note: string) => {
    setCitations(cs => cs.map(c => c.id === id ? { ...c, note } : c));
    onUpdateNote?.(id, note);
  }, [onUpdateNote]);

  const handleLinkSection = useCallback((id: string, sectionId: string) => {
    setCitations(cs => cs.map(c =>
      c.id === id && !c.linkedSections.includes(sectionId)
        ? { ...c, linkedSections: [...c.linkedSections, sectionId] }
        : c,
    ));
    onLinkSection?.(id, sectionId);
  }, [onLinkSection]);

  const handleUnlinkSection = useCallback((id: string, sectionId: string) => {
    setCitations(cs => cs.map(c =>
      c.id === id ? { ...c, linkedSections: c.linkedSections.filter(s => s !== sectionId) } : c,
    ));
    onUnlinkSection?.(id, sectionId);
  }, [onUnlinkSection]);

  function handleExport() {
    const formatter = exportFmt === "nlm" ? formatNLM : formatAPA;
    const text = filtered.map(formatter).join("\n\n");
    const blob  = new Blob([text], { type: "text/plain" });
    const url   = URL.createObjectURL(blob);
    const a     = document.createElement("a");
    a.href      = url;
    a.download  = `citations-${exportFmt}-${Date.now()}.txt`;
    a.click();
    URL.revokeObjectURL(url);
    onExport?.(exportFmt, filtered);
  }

  // All active tags for filter
  const activeTags = useMemo(() => {
    const set = new Set<CitationTag>();
    citations.forEach(c => c.tags.forEach(t => set.add(t)));
    return Array.from(set);
  }, [citations]);

  return (
    <div className={cn("space-y-4", className)}>
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h2 className="text-sm font-semibold text-foreground">Citation Library</h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            {citations.length} citation{citations.length !== 1 ? "s" : ""} saved
            {citations.filter(c => c.inSubmission).length > 0 && (
              <> · <span className="text-[#1A7F4B]">{citations.filter(c => c.inSubmission).length} cited in draft</span></>
            )}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={exportFmt}
            onChange={e => setExportFmt(e.target.value as "nlm" | "apa")}
            className="text-[10px] px-2 py-1 rounded border border-border bg-background text-foreground outline-none cursor-pointer"
            aria-label="Export format"
          >
            <option value="nlm">NLM format</option>
            <option value="apa">APA format</option>
          </select>
          <button
            onClick={handleExport}
            disabled={filtered.length === 0}
            className={cn(
              "text-[10px] px-2.5 py-1 rounded border font-medium transition-colors cursor-pointer",
              filtered.length > 0
                ? "border-[#005EA2] text-[#005EA2] hover:bg-[#005EA2]/10"
                : "border-border text-muted-foreground cursor-not-allowed",
            )}
          >
            ↓ Export {filtered.length > 0 ? `(${filtered.length})` : ""}
          </button>
        </div>
      </div>

      {/* Completeness warning */}
      {missingFromSubmission.length > 0 && (
        <div className="flex items-start gap-2.5 px-3 py-2.5 rounded-lg border border-[#B45309]/30 bg-[#B45309]/8">
          <span className="text-[#B45309] text-sm flex-shrink-0">!</span>
          <div>
            <p className="text-[10px] font-bold text-[#B45309]">
              {missingFromSubmission.length} standard{missingFromSubmission.length !== 1 ? "s" : ""} not cited in draft
            </p>
            <p className="text-[10px] text-muted-foreground">
              {missingFromSubmission.map(c => c.source).join(", ")}
            </p>
          </div>
        </div>
      )}

      {/* Search + sort */}
      <div className="flex items-center gap-2 flex-wrap">
        <input
          type="search"
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
          placeholder="Search citations…"
          className="flex-1 min-w-48 px-3 py-1.5 text-[11px] rounded-lg border border-border bg-background outline-none focus:border-[#005EA2]/50 text-foreground placeholder:text-muted-foreground"
        />
        <select
          value={sortKey}
          onChange={e => setSortKey(e.target.value as CitationSortKey)}
          className="text-[10px] px-2 py-1.5 rounded border border-border bg-background text-foreground outline-none cursor-pointer"
          aria-label="Sort citations"
        >
          <option value="date_added">Sort: Date added</option>
          <option value="relevance">Sort: Relevance</option>
          <option value="source_type">Sort: Source type</option>
          <option value="title">Sort: Title</option>
        </select>
      </div>

      {/* Tag filter */}
      {activeTags.length > 0 && (
        <div className="flex items-center gap-1.5 flex-wrap">
          <button
            onClick={() => setTagFilter("all")}
            className={cn(
              "text-[10px] px-2.5 py-1 rounded-full border font-medium transition-colors cursor-pointer",
              tagFilter === "all"
                ? "bg-foreground text-background border-foreground"
                : "border-border text-muted-foreground hover:bg-muted",
            )}
          >
            All ({citations.length})
          </button>
          {activeTags.map(tag => {
            const tcfg = TAG_CONFIG[tag];
            const count = citations.filter(c => c.tags.includes(tag)).length;
            return (
              <button
                key={tag}
                onClick={() => setTagFilter(tag)}
                className={cn(
                  "text-[10px] px-2.5 py-1 rounded-full border font-medium transition-colors cursor-pointer",
                  tagFilter === tag
                    ? "text-white border-transparent"
                    : "border-border text-muted-foreground hover:bg-muted",
                )}
                style={tagFilter === tag ? { background: tcfg.color, borderColor: tcfg.color } : {}}
              >
                {tcfg.label} ({count})
              </button>
            );
          })}
        </div>
      )}

      {/* Citation list */}
      {filtered.length === 0 ? (
        <div className="py-10 text-center text-[11px] text-muted-foreground border border-dashed border-border rounded-xl">
          {citations.length === 0
            ? "No citations saved yet. Add citations from search results, predicate lookups, or guidance passages."
            : "No citations match the current filter."}
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map(c => (
            <CitationCard
              key={c.id}
              citation={c}
              sections={submissionSections}
              onRemove={handleRemove}
              onUpdateNote={handleUpdateNote}
              onLinkSection={handleLinkSection}
              onUnlinkSection={handleUnlinkSection}
            />
          ))}
        </div>
      )}
    </div>
  );
}
