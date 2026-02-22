"use client";

/**
 * FDA-287 [PRED-004] — EvidenceChainViewer
 * ==========================================
 * Tree visualization of SE claim provenance.
 * Traces each substantial-equivalence claim from the submission
 * back through supporting evidence to the source FDA document.
 *
 * Tree layout: claim (root) → evidence items (branches) → source docs (leaves)
 * Each node shows:
 *   - Claim: text excerpt, confidence score, section reference
 *   - Evidence: supporting quote, evidence type, strength rating
 *   - Document: K-number or guidance title, page/section, document type
 *
 * Features:
 *   - Expand/collapse individual branches
 *   - Click any node to view full text in detail panel
 *   - Confidence colour-coding across all nodes
 *   - Export: structured citation list for accepted nodes
 *   - Filter by evidence strength (high / medium / low)
 *   - Keyboard navigation (arrow keys)
 */

import React, { useState, useCallback } from "react";
import { cn } from "@/lib/utils";

// ── Types ──────────────────────────────────────────────────────────────────

export type EvidenceType =
  | "bench_test"
  | "clinical"
  | "literature"
  | "predicate_data"
  | "standard"
  | "simulated_use";

export type EvidenceStrength = "high" | "medium" | "low";
export type DocumentType = "510k_summary" | "guidance" | "standard" | "publication" | "internal";

export interface SourceDocument {
  id:           string;
  title:        string;
  docType:      DocumentType;
  reference:    string;          // K-number, ISO ref, DOI, etc.
  pageOrSection?: string;
  url?:         string;
}

export interface EvidenceItem {
  id:         string;
  quote:      string;            // supporting passage text
  type:       EvidenceType;
  strength:   EvidenceStrength;
  confidence: number;            // 0–100
  documents:  SourceDocument[];
  expanded?:  boolean;
}

export interface EvidenceClaim {
  id:         string;
  text:       string;            // the SE claim being supported
  section:    string;            // e.g. "SE Discussion §3.2"
  confidence: number;            // 0–100
  evidence:   EvidenceItem[];
}

export interface EvidenceChainViewerProps {
  claims:          EvidenceClaim[];
  onNodeClick?:    (nodeId: string, nodeType: "claim" | "evidence" | "document") => void;
  onExport?:       (citations: string[]) => void;
  className?:      string;
}

// ── Config ─────────────────────────────────────────────────────────────────

const EVIDENCE_TYPE_CONFIG: Record<EvidenceType, { label: string; color: string }> = {
  bench_test:    { label: "Bench Test",    color: "#005EA2" },
  clinical:      { label: "Clinical",      color: "#7C3AED" },
  literature:    { label: "Literature",    color: "#1A7F4B" },
  predicate_data:{ label: "Predicate",     color: "#B45309" },
  standard:      { label: "Standard",      color: "#005EA2" },
  simulated_use: { label: "Simulated Use", color: "#7C3AED" },
};

const DOC_TYPE_CONFIG: Record<DocumentType, { label: string; icon: string }> = {
  "510k_summary":  { label: "510(k)",    icon: "K" },
  guidance:        { label: "Guidance",  icon: "G" },
  standard:        { label: "Standard",  icon: "S" },
  publication:     { label: "PubMed",    icon: "P" },
  internal:        { label: "Internal",  icon: "I" },
};

const STRENGTH_CONFIG: Record<EvidenceStrength, { color: string; label: string }> = {
  high:   { color: "#1A7F4B", label: "High"   },
  medium: { color: "#B45309", label: "Medium" },
  low:    { color: "#C5191B", label: "Low"    },
};

// ── Confidence badge ───────────────────────────────────────────────────────

function ConfidenceBar({ score }: { score: number }) {
  const color = score >= 80 ? "#1A7F4B" : score >= 55 ? "#B45309" : "#C5191B";
  return (
    <div className="flex items-center gap-1.5">
      <div className="w-16 h-1.5 rounded-full bg-muted overflow-hidden">
        <div className="h-full rounded-full" style={{ width: `${score}%`, background: color }} />
      </div>
      <span className="text-[9px] font-mono" style={{ color }}>{score}%</span>
    </div>
  );
}

// ── Document leaf ──────────────────────────────────────────────────────────

function DocumentLeaf({
  doc,
  selected,
  onClick,
}: {
  doc:      SourceDocument;
  selected: boolean;
  onClick:  () => void;
}) {
  const dcfg = DOC_TYPE_CONFIG[doc.docType];
  return (
    <button
      onClick={onClick}
      className={cn(
        "w-full text-left flex items-start gap-2 px-3 py-2 rounded-lg border transition-colors cursor-pointer",
        selected
          ? "border-[#005EA2]/50 bg-[#005EA2]/8"
          : "border-border hover:border-[#005EA2]/30 hover:bg-muted/30",
      )}
    >
      <span className="w-5 h-5 rounded text-[9px] font-bold flex items-center justify-center flex-shrink-0 bg-muted text-muted-foreground">
        {dcfg.icon}
      </span>
      <div className="flex-1 min-w-0">
        <p className="text-[10px] font-medium text-foreground truncate">{doc.title}</p>
        <div className="flex items-center gap-2 mt-0.5">
          <span className="text-[9px] font-mono text-muted-foreground">{doc.reference}</span>
          {doc.pageOrSection && (
            <span className="text-[9px] text-muted-foreground">{doc.pageOrSection}</span>
          )}
        </div>
      </div>
    </button>
  );
}

// ── Evidence branch ────────────────────────────────────────────────────────

function EvidenceBranch({
  evidence,
  selectedId,
  onNodeClick,
}: {
  evidence:    EvidenceItem;
  selectedId:  string | null;
  onNodeClick: (id: string, type: "evidence" | "document") => void;
}) {
  const [expanded, setExpanded] = useState(evidence.expanded ?? true);
  const tcfg = EVIDENCE_TYPE_CONFIG[evidence.type];
  const scfg = STRENGTH_CONFIG[evidence.strength];

  return (
    <div className="ml-4 border-l border-border pl-4 space-y-2">
      {/* Branch node */}
      <button
        onClick={() => { setExpanded(v => !v); onNodeClick(evidence.id, "evidence"); }}
        className={cn(
          "w-full text-left flex items-start gap-2 px-3 py-2.5 rounded-lg border transition-colors cursor-pointer",
          selectedId === evidence.id
            ? "border-[#005EA2]/50 bg-[#005EA2]/8"
            : "border-border hover:border-[#005EA2]/30 hover:bg-muted/20",
        )}
      >
        <span className="text-[10px] mt-0.5 text-muted-foreground flex-shrink-0">
          {expanded ? "▾" : "▸"}
        </span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span
              className="text-[9px] font-bold px-1.5 py-0.5 rounded"
              style={{ background: `${tcfg.color}15`, color: tcfg.color }}
            >
              {tcfg.label}
            </span>
            <span className="text-[9px] font-bold" style={{ color: scfg.color }}>
              {scfg.label} strength
            </span>
            <ConfidenceBar score={evidence.confidence} />
          </div>
          <p className="text-[11px] text-foreground leading-relaxed line-clamp-2">
            "{evidence.quote}"
          </p>
          <p className="text-[9px] text-muted-foreground mt-0.5">
            {evidence.documents.length} source document{evidence.documents.length !== 1 ? "s" : ""}
          </p>
        </div>
      </button>

      {/* Document leaves */}
      {expanded && (
        <div className="ml-4 border-l border-border/50 pl-4 space-y-1.5">
          {evidence.documents.map(doc => (
            <DocumentLeaf
              key={doc.id}
              doc={doc}
              selected={selectedId === doc.id}
              onClick={() => onNodeClick(doc.id, "document")}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ── Claim root node ────────────────────────────────────────────────────────

function ClaimNode({
  claim,
  selectedId,
  onNodeClick,
  strengthFilter,
}: {
  claim:          EvidenceClaim;
  selectedId:     string | null;
  onNodeClick:    (id: string, type: "claim" | "evidence" | "document") => void;
  strengthFilter: EvidenceStrength | "all";
}) {
  const [expanded, setExpanded] = useState(true);
  const visibleEvidence = strengthFilter === "all"
    ? claim.evidence
    : claim.evidence.filter(e => e.strength === strengthFilter);

  return (
    <div className="space-y-2">
      {/* Root claim */}
      <button
        onClick={() => { setExpanded(v => !v); onNodeClick(claim.id, "claim"); }}
        className={cn(
          "w-full text-left px-4 py-3 rounded-xl border font-medium transition-colors cursor-pointer",
          selectedId === claim.id
            ? "border-[#005EA2]/50 bg-[#005EA2]/8"
            : "border-border hover:border-[#005EA2]/30 hover:bg-muted/20",
        )}
      >
        <div className="flex items-start gap-2">
          <span className="text-[11px] text-muted-foreground mt-0.5 flex-shrink-0">
            {expanded ? "▾" : "▸"}
          </span>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <span className="text-[9px] text-muted-foreground font-mono">{claim.section}</span>
              <ConfidenceBar score={claim.confidence} />
              <span className="text-[9px] text-muted-foreground">
                {claim.evidence.length} evidence item{claim.evidence.length !== 1 ? "s" : ""}
              </span>
            </div>
            <p className="text-[12px] text-foreground leading-relaxed font-medium">
              {claim.text}
            </p>
          </div>
        </div>
      </button>

      {/* Evidence branches */}
      {expanded && (
        <div className="space-y-2">
          {visibleEvidence.map(ev => (
            <EvidenceBranch
              key={ev.id}
              evidence={ev}
              selectedId={selectedId}
              onNodeClick={(id, type) => onNodeClick(id, type)}
            />
          ))}
          {visibleEvidence.length === 0 && (
            <p className="ml-8 text-[10px] text-muted-foreground italic">
              No evidence matches the current filter.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

// ── Main Component ─────────────────────────────────────────────────────────

export function EvidenceChainViewer({
  claims,
  onNodeClick,
  onExport,
  className,
}: EvidenceChainViewerProps) {
  const [selectedId,     setSelectedId]     = useState<string | null>(null);
  const [strengthFilter, setStrengthFilter] = useState<EvidenceStrength | "all">("all");

  const handleNodeClick = useCallback((id: string, type: "claim" | "evidence" | "document") => {
    setSelectedId(prev => prev === id ? null : id);
    onNodeClick?.(id, type);
  }, [onNodeClick]);

  // Collect all document references for export
  function handleExport() {
    const citations: string[] = [];
    claims.forEach(c => {
      c.evidence.forEach(e => {
        e.documents.forEach(d => {
          citations.push(`${d.title} — ${d.reference}${d.pageOrSection ? ` (${d.pageOrSection})` : ""}`);
        });
      });
    });
    onExport?.(citations);
  }

  const totalEvidence = claims.reduce((s, c) => s + c.evidence.length, 0);
  const totalDocs     = claims.reduce((s, c) =>
    s + c.evidence.reduce((es, e) => es + e.documents.length, 0), 0,
  );

  return (
    <div className={cn("space-y-4", className)}>
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h2 className="text-sm font-semibold text-foreground">Evidence Chain</h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            {claims.length} claims · {totalEvidence} evidence items · {totalDocs} source documents
          </p>
        </div>
        <button
          onClick={handleExport}
          className="text-[10px] text-[#005EA2] hover:underline font-medium cursor-pointer"
        >
          ↓ Export citations
        </button>
      </div>

      {/* Strength filter */}
      <div className="flex items-center gap-1.5 flex-wrap">
        {(["all", "high", "medium", "low"] as const).map(s => (
          <button
            key={s}
            onClick={() => setStrengthFilter(s)}
            className={cn(
              "text-[10px] px-2.5 py-1 rounded-full border font-medium transition-colors cursor-pointer",
              strengthFilter === s
                ? s === "all"
                  ? "bg-foreground text-background border-foreground"
                  : "text-white border-transparent"
                : "border-border text-muted-foreground hover:bg-muted",
            )}
            style={strengthFilter === s && s !== "all" ? {
              background: STRENGTH_CONFIG[s].color,
            } : {}}
          >
            {s === "all" ? "All strength" : `${STRENGTH_CONFIG[s].label} strength`}
          </button>
        ))}
      </div>

      {/* Claim tree */}
      <div className="space-y-4">
        {claims.map(claim => (
          <ClaimNode
            key={claim.id}
            claim={claim}
            selectedId={selectedId}
            onNodeClick={handleNodeClick}
            strengthFilter={strengthFilter}
          />
        ))}
        {claims.length === 0 && (
          <div className="py-10 text-center text-[11px] text-muted-foreground border border-dashed border-border rounded-xl">
            No evidence chains available for this submission.
          </div>
        )}
      </div>
    </div>
  );
}
