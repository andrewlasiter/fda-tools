"use client";

/**
 * FDA-284 [PRED-001] — EvidencePopover
 * ======================================
 * Click a predicate comparison table cell → popover floats near click point
 * showing the documentary evidence behind that data value.
 *
 * Features:
 *   - Document badge (type + source)
 *   - Verbatim quote with yellow highlight
 *   - Section reference (e.g. "Section 4.2: Performance Testing")
 *   - Confidence score
 *   - Copy citation action (NLM format)
 *   - Flag for review action
 *   - Keyboard: Esc to close, Tab cycles through actions
 */

import React, { useState, useRef, useEffect, useCallback } from "react";
import { cn } from "@/lib/utils";
import type { TrustSource } from "@/components/trust/trust-badge";

// ── Types ─────────────────────────────────────────────────────────────────

export interface Evidence {
  source:       TrustSource;
  quote:        string;
  section?:     string;
  page?:        number;
  confidence:   number;
  docDate?:     string;
  kNumber?:     string;   // for 510k sources
  doi?:         string;   // for pubmed sources
}

interface EvidencePopoverProps {
  evidence:    Evidence[];
  cellValue:   string;
  attribute:   string;
  children:    React.ReactNode;
  className?:  string;
}

// ── Source config ─────────────────────────────────────────────────────────

const SOURCE_CONFIG: Record<TrustSource["type"], { label: string; color: string; bg: string }> = {
  "510k":    { label: "510(k) Summary", color: "#005EA2", bg: "bg-[#005EA2]/10 border-[#005EA2]/25" },
  guidance:  { label: "FDA Guidance",   color: "#1A7F4B", bg: "bg-[#1A7F4B]/10 border-[#1A7F4B]/25" },
  standard:  { label: "Standard",       color: "#7C3AED", bg: "bg-purple-100 border-purple-200 dark:bg-purple-900/30 dark:border-purple-700" },
  maude:     { label: "MAUDE Report",   color: "#B45309", bg: "bg-[#B45309]/10 border-[#B45309]/25" },
  pubmed:    { label: "PubMed Article", color: "#DB2777", bg: "bg-pink-100 border-pink-200 dark:bg-pink-900/30 dark:border-pink-700" },
  manual:    { label: "Manual Entry",   color: "#64748B", bg: "bg-muted border-border" },
};

// ── Confidence ring (tiny SVG) ────────────────────────────────────────────

function ConfidenceRing({ value }: { value: number }) {
  const r = 8; const c = 2 * Math.PI * r;
  const offset = c - (value / 100) * c;
  const color = value >= 90 ? "#1A7F4B" : value >= 70 ? "#B45309" : "#C5191B";
  return (
    <svg width="22" height="22" viewBox="0 0 22 22" className="flex-shrink-0">
      <circle cx="11" cy="11" r={r} fill="none" stroke="currentColor" strokeWidth="2.5" className="text-muted/40" />
      <circle
        cx="11" cy="11" r={r} fill="none"
        stroke={color} strokeWidth="2.5"
        strokeDasharray={c} strokeDashoffset={offset}
        strokeLinecap="round"
        transform="rotate(-90 11 11)"
      />
      <text x="11" y="14" textAnchor="middle" fontSize="6" fontWeight="700" fill={color}>{value}</text>
    </svg>
  );
}

// ── Individual evidence card ──────────────────────────────────────────────

function EvidenceCard({
  ev,
  index,
  total,
  onCopyCitation,
  onFlag,
}: {
  ev: Evidence;
  index: number;
  total: number;
  onCopyCitation: (ev: Evidence) => void;
  onFlag: (ev: Evidence) => void;
}) {
  const cfg = SOURCE_CONFIG[ev.source.type];

  function buildCitation(): string {
    if (ev.source.type === "510k" && ev.kNumber) {
      return `FDA 510(k) Clearance ${ev.kNumber}. ${ev.source.label}. ${ev.section ?? ""}. ${ev.docDate ?? ""}. Available at: https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/pmn.cfm`;
    }
    if (ev.source.type === "pubmed" && ev.doi) {
      return `${ev.source.label}. ${ev.section ?? ""}. DOI: ${ev.doi}`;
    }
    return `${ev.source.label}${ev.section ? `. ${ev.section}` : ""}${ev.docDate ? `. ${ev.docDate}` : ""}`;
  }

  return (
    <div className="border border-border rounded-lg overflow-hidden bg-background">
      {/* Source header */}
      <div className={cn("flex items-center gap-2 px-3 py-2 border-b border-border", cfg.bg)}>
        <span
          className="text-[9px] font-bold px-1.5 py-0.5 rounded border"
          style={{ color: cfg.color, borderColor: cfg.color + "40", background: cfg.color + "15" }}
        >
          {cfg.label}
        </span>
        {total > 1 && (
          <span className="text-[9px] text-muted-foreground ml-auto">{index + 1}/{total}</span>
        )}
      </div>

      {/* Document info */}
      <div className="px-3 py-2.5 space-y-2">
        <div>
          <p className="text-xs font-semibold text-foreground leading-tight">{ev.source.label}</p>
          {ev.kNumber && <p className="text-[10px] text-muted-foreground font-mono">{ev.kNumber}</p>}
          {ev.section && (
            <p className="text-[10px] text-muted-foreground mt-0.5">
              <span className="font-medium">§</span> {ev.section}
              {ev.page && <span className="ml-1">· p.{ev.page}</span>}
            </p>
          )}
        </div>

        {/* Verbatim quote */}
        <blockquote className="border-l-2 border-[#005EA2]/40 pl-2.5">
          <p className="text-[11px] text-foreground italic leading-relaxed">
            <span className="bg-amber-100/80 dark:bg-amber-900/40 px-0.5 rounded">
              "{ev.quote}"
            </span>
          </p>
        </blockquote>

        {/* Confidence + date */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <ConfidenceRing value={ev.confidence} />
            <span className="text-[10px] text-muted-foreground">{ev.confidence}% match</span>
          </div>
          {ev.docDate && (
            <span className="text-[10px] text-muted-foreground ml-auto">{ev.docDate}</span>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center border-t border-border px-3 py-1.5 bg-muted/30 gap-2">
        <button
          onClick={() => onCopyCitation(ev)}
          className="text-[10px] text-[#005EA2] hover:underline font-medium flex items-center gap-1"
        >
          <span>Copy citation</span>
        </button>
        <span className="text-border">|</span>
        <button
          onClick={() => onFlag(ev)}
          className="text-[10px] text-muted-foreground hover:text-foreground"
        >
          Flag for review
        </button>
        <button className="ml-auto text-[10px] text-muted-foreground hover:text-foreground">
          Open document →
        </button>
      </div>
    </div>
  );
}

// ── Main EvidencePopover ──────────────────────────────────────────────────

export function EvidencePopover({
  evidence,
  cellValue,
  attribute,
  children,
  className,
}: EvidencePopoverProps) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const [flagged, setFlagged] = useState<number[]>([]);
  const ref = useRef<HTMLDivElement>(null);

  const close = useCallback(() => setOpen(false), []);

  // Close on Esc
  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") close();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, close]);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    function onOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) close();
    }
    document.addEventListener("mousedown", onOutside);
    return () => document.removeEventListener("mousedown", onOutside);
  }, [open, close]);

  function handleCopyCitation(ev: Evidence) {
    const text = `${ev.source.label}${ev.section ? ` §${ev.section}` : ""}${ev.docDate ? ` (${ev.docDate})` : ""}: "${ev.quote}"`;
    navigator.clipboard?.writeText(text).catch(() => {});
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  function handleFlag(ev: Evidence) {
    const idx = evidence.indexOf(ev);
    setFlagged(f => f.includes(idx) ? f.filter(i => i !== idx) : [...f, idx]);
  }

  if (evidence.length === 0) return <>{children}</>;

  return (
    <div ref={ref} className={cn("relative inline-flex", className)}>
      {/* Trigger cell */}
      <div
        role="button"
        tabIndex={0}
        aria-label={`View evidence for ${attribute}`}
        onClick={() => setOpen(o => !o)}
        onKeyDown={e => e.key === "Enter" && setOpen(o => !o)}
        className={cn(
          "cursor-pointer rounded transition-all",
          "hover:ring-2 hover:ring-[#005EA2]/40 hover:bg-[#005EA2]/5",
          open && "ring-2 ring-[#005EA2] bg-[#005EA2]/5",
          "focus:outline-none focus:ring-2 focus:ring-[#005EA2]"
        )}
      >
        {children}
        {/* Evidence indicator dot */}
        <span
          className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full bg-[#005EA2] border border-background"
          aria-hidden
        />
      </div>

      {/* Popover */}
      {open && (
        <div
          className={cn(
            "absolute z-50 w-80 shadow-2xl rounded-xl border border-border bg-background",
            "animate-in zoom-in-95 slide-in-from-top-2 duration-150",
            // Position: prefer below, shift left if near right edge
            "top-full mt-2 left-0",
          )}
          role="dialog"
          aria-label={`Evidence for ${attribute}: ${cellValue}`}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-muted/40 rounded-t-xl">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Evidence</p>
              <p className="text-xs font-semibold text-foreground">{attribute}</p>
              <p className="text-[10px] text-muted-foreground font-mono">{cellValue}</p>
            </div>
            <div className="flex items-center gap-2">
              {copied && <span className="text-[10px] text-[#1A7F4B] font-medium">Copied!</span>}
              <span className="text-[10px] text-muted-foreground">{evidence.length} source{evidence.length !== 1 ? "s" : ""}</span>
              <button
                onClick={close}
                className="w-6 h-6 rounded-md flex items-center justify-center text-muted-foreground hover:bg-muted transition-colors"
                aria-label="Close evidence popover"
              >
                <svg viewBox="0 0 12 12" className="w-3 h-3" fill="none" stroke="currentColor" strokeWidth={2}>
                  <path d="M2 2l8 8M10 2L2 10" />
                </svg>
              </button>
            </div>
          </div>

          {/* Evidence cards */}
          <div className="p-3 space-y-2 max-h-80 overflow-y-auto">
            {evidence.map((ev, i) => (
              <EvidenceCard
                key={i}
                ev={ev}
                index={i}
                total={evidence.length}
                onCopyCitation={handleCopyCitation}
                onFlag={handleFlag}
              />
            ))}
          </div>

          {/* Footer: chain link */}
          <div className="border-t border-border px-4 py-2 bg-muted/20 rounded-b-xl">
            <button className="text-[10px] text-[#005EA2] hover:underline font-medium">
              View full evidence chain for this row →
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
