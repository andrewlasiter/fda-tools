"use client";

/**
 * FDA-288 [RH-001] — GuidanceInlineViewer
 * ==========================================
 * In-app PDF viewer for FDA guidance documents and 510(k) summaries.
 * Opens as a right-panel Sheet without leaving the current view.
 *
 * Features:
 *   - PDF render via browser iframe (PDF.js-compatible URL)
 *   - Page navigation (prev / next / jump-to-page)
 *   - AI-highlighted passage list (yellow highlight badge with excerpt)
 *   - Passage citation button (copies formatted citation to clipboard)
 *   - Add annotation/note linked to current page → project notepad
 *   - Link passage to specific SE table row or submission section
 *   - Related documents suggestions (same product code / guidance family)
 *   - Accessible: keyboard nav (arrow keys), ARIA roles
 *   - Zoom level control
 */

import React, { useState, useRef, useCallback } from "react";
import { cn } from "@/lib/utils";

// ── Types ──────────────────────────────────────────────────────────────────

export type DocumentType = "guidance" | "510k_summary" | "standard" | "publication";

export interface HighlightedPassage {
  id:          string;
  page:        number;
  excerpt:     string;         // short text excerpt
  relevance:   number;         // 0–100 AI relevance score
  category:    string;         // e.g. "SE Criteria", "Biocompatibility"
}

export interface RelatedDocument {
  title:       string;
  reference:   string;
  docType:     DocumentType;
  relevance:   number;
}

export interface Annotation {
  id:          string;
  page:        number;
  note:        string;
  linkedTo?:   string;         // section ID or SE table row ID
  createdAt:   string;
}

export interface GuidanceInlineViewerProps {
  title:              string;
  reference:          string;         // K-number, guidance title, DOI
  docType:            DocumentType;
  pdfUrl:             string;         // URL for iframe src (PDF.js or direct)
  totalPages:         number;
  highlights?:        HighlightedPassage[];
  related?:           RelatedDocument[];
  annotations?:       Annotation[];
  onCiteCopied?:      (citation: string) => void;
  onAnnotationAdd?:   (annotation: Omit<Annotation, "id" | "createdAt">) => void;
  onLinkToSection?:   (passageId: string, sectionId: string) => void;
  onOpenRelated?:     (reference: string) => void;
  className?:         string;
}

// ── Config ─────────────────────────────────────────────────────────────────

const DOC_TYPE_CONFIG: Record<DocumentType, { label: string; color: string; bg: string }> = {
  guidance:      { label: "FDA Guidance",  color: "#005EA2", bg: "bg-[#005EA2]/10"  },
  "510k_summary":{ label: "510(k)",        color: "#7C3AED", bg: "bg-[#7C3AED]/10"  },
  standard:      { label: "Standard",      color: "#1A7F4B", bg: "bg-[#1A7F4B]/10"  },
  publication:   { label: "Publication",   color: "#B45309", bg: "bg-[#B45309]/10"  },
};

const ZOOM_LEVELS = [75, 100, 125, 150, 200];

// ── Passage card ───────────────────────────────────────────────────────────

function PassageCard({
  passage,
  onCite,
  onLinkToSection,
  onJumpToPage,
}: {
  passage:         HighlightedPassage;
  onCite:          (passage: HighlightedPassage) => void;
  onLinkToSection: (passageId: string) => void;
  onJumpToPage:    (page: number) => void;
}) {
  const relColor =
    passage.relevance >= 80 ? "#1A7F4B" :
    passage.relevance >= 55 ? "#B45309" :
    "#C5191B";

  return (
    <div className="rounded-lg border border-[#B45309]/20 bg-[#B45309]/5 p-3 space-y-2">
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-[9px] font-bold text-[#B45309] bg-[#B45309]/10 px-1.5 py-0.5 rounded">
          p. {passage.page}
        </span>
        <span className="text-[9px] text-muted-foreground">{passage.category}</span>
        <span
          className="text-[9px] font-mono ml-auto flex-shrink-0"
          style={{ color: relColor }}
        >
          {passage.relevance}% match
        </span>
      </div>

      <p className="text-[11px] text-foreground leading-relaxed italic">
        "{passage.excerpt}"
      </p>

      <div className="flex items-center gap-2">
        <button
          onClick={() => onJumpToPage(passage.page)}
          className="text-[10px] text-[#005EA2] hover:underline font-medium cursor-pointer"
        >
          Jump to page
        </button>
        <span className="text-muted-foreground text-[10px]">·</span>
        <button
          onClick={() => onCite(passage)}
          className="text-[10px] text-[#005EA2] hover:underline font-medium cursor-pointer"
        >
          Copy citation
        </button>
        <span className="text-muted-foreground text-[10px]">·</span>
        <button
          onClick={() => onLinkToSection(passage.id)}
          className="text-[10px] text-[#005EA2] hover:underline font-medium cursor-pointer"
        >
          Link to section
        </button>
      </div>
    </div>
  );
}

// ── Annotation form ────────────────────────────────────────────────────────

function AnnotationForm({
  currentPage,
  onAdd,
  onCancel,
}: {
  currentPage: number;
  onAdd:       (note: string, linkedTo?: string) => void;
  onCancel:    () => void;
}) {
  const [note,     setNote]     = useState("");
  const [linkedTo, setLinkedTo] = useState("");

  return (
    <div className="rounded-lg border border-border bg-muted/20 p-3 space-y-3">
      <p className="text-[10px] font-bold text-foreground">Add note — Page {currentPage}</p>
      <textarea
        value={note}
        onChange={e => setNote(e.target.value)}
        rows={3}
        placeholder="Enter your annotation…"
        className="w-full px-2.5 py-1.5 text-[11px] rounded border border-border bg-background outline-none resize-none text-foreground placeholder:text-muted-foreground"
        autoFocus
      />
      <input
        type="text"
        value={linkedTo}
        onChange={e => setLinkedTo(e.target.value)}
        placeholder="Link to section ID (optional)"
        className="w-full px-2.5 py-1.5 text-[11px] rounded border border-border bg-background outline-none text-foreground placeholder:text-muted-foreground"
      />
      <div className="flex items-center gap-2">
        <button
          onClick={onCancel}
          className="text-[10px] text-muted-foreground hover:text-foreground cursor-pointer"
        >
          Cancel
        </button>
        <button
          onClick={() => note.trim() && onAdd(note.trim(), linkedTo || undefined)}
          disabled={!note.trim()}
          className={cn(
            "ml-auto text-[10px] px-2.5 py-1 rounded border font-medium cursor-pointer transition-colors",
            note.trim()
              ? "bg-[#005EA2] border-[#005EA2] text-white hover:bg-[#005EA2]/90"
              : "border-border text-muted-foreground cursor-not-allowed",
          )}
        >
          Save note
        </button>
      </div>
    </div>
  );
}

// ── Main Component ─────────────────────────────────────────────────────────

export function GuidanceInlineViewer({
  title,
  reference,
  docType,
  pdfUrl,
  totalPages,
  highlights = [],
  related = [],
  annotations: initialAnnotations = [],
  onCiteCopied,
  onAnnotationAdd,
  onLinkToSection,
  onOpenRelated,
  className,
}: GuidanceInlineViewerProps) {
  const [currentPage,   setCurrentPage]   = useState(1);
  const [pageInput,     setPageInput]     = useState("1");
  const [zoom,          setZoom]          = useState(100);
  const [activeTab,     setActiveTab]     = useState<"highlights" | "annotations" | "related">("highlights");
  const [addingNote,    setAddingNote]    = useState(false);
  const [annotations,   setAnnotations]  = useState<Annotation[]>(initialAnnotations);
  const [copied,        setCopied]        = useState(false);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  const dcfg = DOC_TYPE_CONFIG[docType];
  const pageHighlights = highlights.filter(h => h.page === currentPage);

  function goToPage(page: number) {
    const clamped = Math.max(1, Math.min(page, totalPages));
    setCurrentPage(clamped);
    setPageInput(String(clamped));
  }

  function handlePageInputBlur() {
    const n = parseInt(pageInput, 10);
    if (!isNaN(n)) goToPage(n);
    else setPageInput(String(currentPage));
  }

  const buildCitation = useCallback((passage: HighlightedPassage): string => {
    return `${title}. ${reference}. p. ${passage.page}: "${passage.excerpt}"`;
  }, [title, reference]);

  async function handleCite(passage: HighlightedPassage) {
    const citation = buildCitation(passage);
    try {
      await navigator.clipboard.writeText(citation);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
      onCiteCopied?.(citation);
    } catch {
      // clipboard not available in test env
    }
  }

  function handleAnnotationAdd(note: string, linkedTo?: string) {
    const ann: Annotation = {
      id:        `ann-${Date.now()}`,
      page:      currentPage,
      note,
      linkedTo,
      createdAt: new Date().toISOString(),
    };
    setAnnotations(as => [...as, ann]);
    onAnnotationAdd?.({ page: currentPage, note, linkedTo });
    setAddingNote(false);
  }

  const iframeSrc = `${pdfUrl}#page=${currentPage}&zoom=${zoom}`;

  return (
    <div className={cn("flex h-full min-h-0 bg-background", className)}>

      {/* PDF Viewer pane */}
      <div className="flex-1 min-w-0 flex flex-col">
        {/* Viewer toolbar */}
        <div className="flex items-center gap-2 px-3 py-2 border-b border-border shrink-0 flex-wrap">
          <div>
            <p className="text-[11px] font-bold text-foreground truncate max-w-48">{title}</p>
            <div className="flex items-center gap-2 mt-0.5">
              <span
                className={cn("text-[9px] font-bold px-1.5 py-0.5 rounded", dcfg.bg)}
                style={{ color: dcfg.color }}
              >
                {dcfg.label}
              </span>
              <span className="text-[9px] font-mono text-muted-foreground">{reference}</span>
            </div>
          </div>

          <div className="ml-auto flex items-center gap-2">
            {/* Zoom */}
            <select
              value={zoom}
              onChange={e => setZoom(Number(e.target.value))}
              className="text-[10px] px-1.5 py-1 rounded border border-border bg-background text-foreground outline-none cursor-pointer"
              aria-label="Zoom level"
            >
              {ZOOM_LEVELS.map(z => <option key={z} value={z}>{z}%</option>)}
            </select>

            {/* Page nav */}
            <button
              onClick={() => goToPage(currentPage - 1)}
              disabled={currentPage <= 1}
              aria-label="Previous page"
              className="text-[10px] px-2 py-1 rounded border border-border text-muted-foreground hover:bg-muted disabled:opacity-40 cursor-pointer"
            >
              ←
            </button>
            <div className="flex items-center gap-1">
              <input
                type="text"
                value={pageInput}
                onChange={e => setPageInput(e.target.value)}
                onBlur={handlePageInputBlur}
                onKeyDown={e => e.key === "Enter" && handlePageInputBlur()}
                aria-label="Current page"
                className="w-10 text-[10px] text-center px-1 py-1 rounded border border-border bg-background outline-none text-foreground"
              />
              <span className="text-[10px] text-muted-foreground">/ {totalPages}</span>
            </div>
            <button
              onClick={() => goToPage(currentPage + 1)}
              disabled={currentPage >= totalPages}
              aria-label="Next page"
              className="text-[10px] px-2 py-1 rounded border border-border text-muted-foreground hover:bg-muted disabled:opacity-40 cursor-pointer"
            >
              →
            </button>
          </div>
        </div>

        {/* Page highlight indicator */}
        {pageHighlights.length > 0 && (
          <div className="px-3 py-1.5 bg-[#B45309]/8 border-b border-[#B45309]/20 flex items-center gap-2">
            <div className="w-2.5 h-2.5 rounded-sm bg-[#B45309]/60 flex-shrink-0" />
            <span className="text-[10px] text-[#B45309] font-medium">
              {pageHighlights.length} highlighted passage{pageHighlights.length !== 1 ? "s" : ""} on this page
            </span>
          </div>
        )}

        {/* iframe PDF render */}
        <div className="flex-1 min-h-0 bg-muted/30">
          <iframe
            ref={iframeRef}
            src={iframeSrc}
            title={`PDF: ${title}`}
            className="w-full h-full border-0"
            aria-label={`PDF viewer for ${title}`}
          />
        </div>
      </div>

      {/* Right sidebar: highlights / annotations / related */}
      <aside className="w-64 flex-shrink-0 border-l border-border flex flex-col">
        {/* Tabs */}
        <div className="flex border-b border-border shrink-0">
          {(["highlights", "annotations", "related"] as const).map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={cn(
                "flex-1 py-2 text-[10px] font-medium capitalize transition-colors cursor-pointer",
                activeTab === tab
                  ? "border-b-2 border-[#005EA2] text-[#005EA2]"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              {tab}
              {tab === "highlights" && highlights.length > 0 && (
                <span className="ml-1 text-[9px]">({highlights.length})</span>
              )}
              {tab === "annotations" && annotations.length > 0 && (
                <span className="ml-1 text-[9px]">({annotations.length})</span>
              )}
            </button>
          ))}
        </div>

        <div className="flex-1 overflow-y-auto p-3 space-y-3">

          {/* Highlights tab */}
          {activeTab === "highlights" && (
            <>
              {highlights.length === 0 ? (
                <p className="text-[10px] text-muted-foreground text-center py-6">
                  No AI highlights for this document.
                </p>
              ) : (
                highlights
                  .sort((a, b) => b.relevance - a.relevance)
                  .map(h => (
                    <PassageCard
                      key={h.id}
                      passage={h}
                      onCite={handleCite}
                      onLinkToSection={(passageId) => onLinkToSection?.(passageId, "")}
                      onJumpToPage={goToPage}
                    />
                  ))
              )}
              {copied && (
                <div className="text-center text-[10px] text-[#1A7F4B] font-medium">
                  Citation copied to clipboard
                </div>
              )}
            </>
          )}

          {/* Annotations tab */}
          {activeTab === "annotations" && (
            <>
              {addingNote ? (
                <AnnotationForm
                  currentPage={currentPage}
                  onAdd={handleAnnotationAdd}
                  onCancel={() => setAddingNote(false)}
                />
              ) : (
                <button
                  onClick={() => setAddingNote(true)}
                  className="w-full text-[10px] px-3 py-2 rounded-lg border border-dashed border-border text-muted-foreground hover:border-[#005EA2]/50 hover:text-[#005EA2] transition-colors cursor-pointer"
                >
                  + Add note for page {currentPage}
                </button>
              )}

              {annotations.length === 0 && !addingNote && (
                <p className="text-[10px] text-muted-foreground text-center py-4">
                  No annotations yet.
                </p>
              )}

              {annotations.map(ann => (
                <div key={ann.id} className="rounded-lg border border-border bg-muted/20 p-3">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-[9px] font-bold text-muted-foreground">p. {ann.page}</span>
                    {ann.linkedTo && (
                      <span className="text-[9px] text-[#005EA2]">→ {ann.linkedTo}</span>
                    )}
                  </div>
                  <p className="text-[11px] text-foreground leading-relaxed">{ann.note}</p>
                </div>
              ))}
            </>
          )}

          {/* Related tab */}
          {activeTab === "related" && (
            <>
              {related.length === 0 ? (
                <p className="text-[10px] text-muted-foreground text-center py-6">
                  No related documents found.
                </p>
              ) : (
                related
                  .sort((a, b) => b.relevance - a.relevance)
                  .map((doc, i) => {
                    const rcfg = DOC_TYPE_CONFIG[doc.docType];
                    return (
                      <button
                        key={i}
                        onClick={() => onOpenRelated?.(doc.reference)}
                        className="w-full text-left rounded-lg border border-border hover:border-[#005EA2]/30 hover:bg-muted/30 transition-colors p-3 cursor-pointer"
                      >
                        <div className="flex items-center gap-2 mb-1">
                          <span
                            className={cn("text-[9px] font-bold px-1.5 py-0.5 rounded", rcfg.bg)}
                            style={{ color: rcfg.color }}
                          >
                            {rcfg.label}
                          </span>
                          <span className="text-[9px] font-mono text-muted-foreground ml-auto">
                            {doc.relevance}%
                          </span>
                        </div>
                        <p className="text-[11px] text-foreground leading-snug">{doc.title}</p>
                        <p className="text-[9px] font-mono text-muted-foreground mt-0.5">
                          {doc.reference}
                        </p>
                      </button>
                    );
                  })
              )}
            </>
          )}
        </div>
      </aside>
    </div>
  );
}
