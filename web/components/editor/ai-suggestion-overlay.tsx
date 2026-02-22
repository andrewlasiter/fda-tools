"use client";

/**
 * FDA-292 [DOC-002] — AISuggestionOverlay
 * ==========================================
 * AI-generated inline suggestions for submission section content.
 * Shows per-paragraph improvement cards that reviewers can accept,
 * reject, or modify before committing to the document.
 *
 * Features:
 *   - Suggestion cards: original paragraph vs. AI-proposed revision
 *   - Per-suggestion accept / reject / edit-before-accept
 *   - Confidence score badge (0–100)
 *   - Regulation reference tags (e.g. "21 CFR 807.87(e)")
 *   - Agent attribution (which sub-agent produced the suggestion)
 *   - Batch accept-all / reject-all
 *   - Suggestion filter by category (grammar / regulatory / clarity / completeness)
 *   - Accepted count + rejection reason collection
 */

import React, { useState, useMemo, useCallback } from "react";
import { cn } from "@/lib/utils";

// ── Types ──────────────────────────────────────────────────────────────────

export type SuggestionCategory =
  | "regulatory"     // References a CFR / guidance requirement
  | "clarity"        // Plain-language rewrite
  | "completeness"   // Adds missing required content
  | "grammar"        // Grammar / style fix
  | "consistency";   // Aligns with other sections

export type SuggestionStatus = "pending" | "accepted" | "rejected" | "editing";

export interface AISuggestion {
  id:               string;
  sectionId:        string;
  paragraphIndex:   number;       // 0-based paragraph position in section
  original:         string;       // current text
  proposed:         string;       // AI-suggested replacement
  rationale:        string;       // why the AI suggests this change
  category:         SuggestionCategory;
  confidence:       number;       // 0–100
  regulationRefs?:  string[];     // e.g. ["21 CFR 807.87(e)", "ISO 13485:2016 §7.3"]
  agentName:        string;       // which agent generated this
  timestamp:        string;       // ISO 8601
  status:           SuggestionStatus;
  rejectionReason?: string;
}

export interface AISuggestionOverlayProps {
  suggestions:        AISuggestion[];
  sectionId?:         string;         // filter to this section
  onAccept?:          (id: string, finalText: string) => void;
  onReject?:          (id: string, reason: string) => void;
  onBulkAccept?:      () => void;
  onBulkReject?:      () => void;
  className?:         string;
}

// ── Config ─────────────────────────────────────────────────────────────────

const CAT_CONFIG: Record<SuggestionCategory, { label: string; color: string; bg: string }> = {
  regulatory:   { label: "Regulatory",    color: "#C5191B", bg: "bg-[#C5191B]/10"   },
  clarity:      { label: "Clarity",       color: "#005EA2", bg: "bg-[#005EA2]/10"   },
  completeness: { label: "Completeness",  color: "#B45309", bg: "bg-[#B45309]/10"   },
  grammar:      { label: "Grammar",       color: "#1A7F4B", bg: "bg-[#1A7F4B]/10"   },
  consistency:  { label: "Consistency",   color: "#7C3AED", bg: "bg-[#7C3AED]/10"   },
};

// ── Confidence badge ───────────────────────────────────────────────────────

function ConfidenceBadge({ score }: { score: number }) {
  const color =
    score >= 90 ? "#1A7F4B" :
    score >= 70 ? "#B45309" :
    "#C5191B";
  return (
    <span
      className="text-[9px] font-bold px-1.5 py-0.5 rounded font-mono"
      style={{ color, background: `${color}15` }}
    >
      {score}%
    </span>
  );
}

// ── SuggestionCard ─────────────────────────────────────────────────────────

function SuggestionCard({
  suggestion,
  onAccept,
  onReject,
}: {
  suggestion: AISuggestion;
  onAccept:   (id: string, text: string) => void;
  onReject:   (id: string, reason: string) => void;
}) {
  const [editing,        setEditing]        = useState(false);
  const [editedText,     setEditedText]     = useState(suggestion.proposed);
  const [rejecting,      setRejecting]      = useState(false);
  const [rejectReason,   setRejectReason]   = useState("");
  const [showOriginal,   setShowOriginal]   = useState(false);

  const catCfg = CAT_CONFIG[suggestion.category];
  const dt     = new Date(suggestion.timestamp);

  if (suggestion.status === "accepted") {
    return (
      <div className="rounded-xl border border-[#1A7F4B]/30 bg-[#1A7F4B]/5 px-4 py-3 flex items-center gap-3">
        <span className="text-[#1A7F4B] text-sm">✓</span>
        <div className="flex-1 min-w-0">
          <p className="text-[11px] font-medium text-foreground">Accepted</p>
          <p className="text-[10px] text-muted-foreground truncate">{suggestion.proposed}</p>
        </div>
        <span className="text-[9px] text-muted-foreground flex-shrink-0">
          ¶{suggestion.paragraphIndex + 1}
        </span>
      </div>
    );
  }

  if (suggestion.status === "rejected") {
    return (
      <div className="rounded-xl border border-border bg-muted/20 px-4 py-3 flex items-center gap-3 opacity-60">
        <span className="text-muted-foreground text-sm">✕</span>
        <div className="flex-1 min-w-0">
          <p className="text-[11px] font-medium text-muted-foreground">Rejected</p>
          {suggestion.rejectionReason && (
            <p className="text-[10px] text-muted-foreground truncate">{suggestion.rejectionReason}</p>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-border overflow-hidden">
      {/* Card header */}
      <div className="flex items-center gap-2 px-4 py-2.5 bg-muted/30 border-b border-border flex-wrap">
        {/* Category */}
        <span
          className={cn("text-[9px] font-bold px-1.5 py-0.5 rounded", catCfg.bg)}
          style={{ color: catCfg.color }}
        >
          {catCfg.label}
        </span>

        <ConfidenceBadge score={suggestion.confidence} />

        <span className="text-[10px] text-muted-foreground">¶{suggestion.paragraphIndex + 1}</span>
        <span className="text-[10px] text-muted-foreground">·</span>
        <span className="text-[10px] text-muted-foreground">{suggestion.agentName}</span>

        <time className="ml-auto text-[9px] text-muted-foreground" dateTime={suggestion.timestamp}>
          {dt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
        </time>
      </div>

      {/* Regulation refs */}
      {(suggestion.regulationRefs?.length ?? 0) > 0 && (
        <div className="px-4 py-1.5 bg-[#C5191B]/5 border-b border-[#C5191B]/15 flex items-center gap-2 flex-wrap">
          <span className="text-[9px] text-[#C5191B] font-medium">Cited:</span>
          {suggestion.regulationRefs!.map(ref => (
            <span key={ref} className="text-[9px] font-mono text-[#C5191B] bg-[#C5191B]/10 px-1.5 py-0.5 rounded">
              {ref}
            </span>
          ))}
        </div>
      )}

      {/* Content */}
      <div className="p-4 space-y-3">
        {/* Rationale */}
        <p className="text-[11px] text-muted-foreground italic">{suggestion.rationale}</p>

        {/* Original (collapsible) */}
        <div>
          <button
            onClick={() => setShowOriginal(v => !v)}
            className="text-[10px] text-muted-foreground hover:text-foreground font-medium"
          >
            {showOriginal ? "▾ Hide original" : "▸ Show original"}
          </button>
          {showOriginal && (
            <div className="mt-1.5 px-3 py-2 rounded-lg bg-destructive/5 border border-destructive/20">
              <p className="text-[11px] text-muted-foreground line-through leading-relaxed">
                {suggestion.original}
              </p>
            </div>
          )}
        </div>

        {/* Proposed */}
        <div className="rounded-lg border border-[#1A7F4B]/25 bg-[#1A7F4B]/5">
          {editing ? (
            <textarea
              value={editedText}
              onChange={e => setEditedText(e.target.value)}
              rows={4}
              className="w-full px-3 py-2.5 text-[11px] text-foreground bg-transparent outline-none resize-none font-mono leading-relaxed"
            />
          ) : (
            <p className="px-3 py-2.5 text-[11px] text-foreground leading-relaxed">
              {editedText}
            </p>
          )}
        </div>
      </div>

      {/* Rejection form */}
      {rejecting && (
        <div className="px-4 pb-3 border-t border-border/50 pt-3">
          <p className="text-[10px] text-muted-foreground mb-1.5">Rejection reason (optional):</p>
          <input
            type="text"
            value={rejectReason}
            onChange={e => setRejectReason(e.target.value)}
            placeholder="e.g. Content already covered in Section 4"
            className="w-full px-2.5 py-1.5 text-[11px] rounded-lg border border-border bg-background outline-none focus:border-[#005EA2]/50"
            autoFocus
          />
        </div>
      )}

      {/* Action buttons */}
      <div className="flex items-center gap-2 px-4 py-2.5 border-t border-border bg-muted/20">
        {/* Reject flow */}
        {rejecting ? (
          <>
            <button
              onClick={() => setRejecting(false)}
              className="text-[10px] text-muted-foreground hover:text-foreground font-medium"
            >
              Cancel
            </button>
            <button
              onClick={() => onReject(suggestion.id, rejectReason)}
              className="ml-auto text-[10px] px-2.5 py-1 rounded border border-destructive/30 text-destructive hover:bg-destructive/10 font-medium"
            >
              Confirm Reject
            </button>
          </>
        ) : (
          <>
            <button
              onClick={() => setRejecting(true)}
              className="text-[10px] px-2.5 py-1 rounded border border-border text-muted-foreground hover:bg-muted font-medium"
            >
              ✕ Reject
            </button>

            <button
              onClick={() => setEditing(e => !e)}
              className={cn(
                "text-[10px] px-2.5 py-1 rounded border font-medium transition-colors",
                editing
                  ? "border-[#7C3AED]/40 text-[#7C3AED] bg-[#7C3AED]/10"
                  : "border-border text-muted-foreground hover:bg-muted",
              )}
            >
              {editing ? "Preview" : "✎ Edit"}
            </button>

            <button
              onClick={() => onAccept(suggestion.id, editedText)}
              className="ml-auto text-[10px] px-2.5 py-1 rounded border border-[#1A7F4B]/30 text-[#1A7F4B] hover:bg-[#1A7F4B]/10 font-medium"
            >
              ✓ Accept{editing ? " edited" : ""}
            </button>
          </>
        )}
      </div>
    </div>
  );
}

// ── Main Component ─────────────────────────────────────────────────────────

export function AISuggestionOverlay({
  suggestions: initial,
  sectionId,
  onAccept,
  onReject,
  onBulkAccept,
  onBulkReject,
  className,
}: AISuggestionOverlayProps) {
  const [suggestions,  setSuggestions]  = useState<AISuggestion[]>(initial);
  const [catFilter,    setCatFilter]    = useState<SuggestionCategory | "all">("all");

  const filtered = useMemo(() => {
    let list = sectionId
      ? suggestions.filter(s => s.sectionId === sectionId)
      : suggestions;
    if (catFilter !== "all") {
      list = list.filter(s => s.category === catFilter);
    }
    return list;
  }, [suggestions, sectionId, catFilter]);

  const stats = useMemo(() => ({
    total:    filtered.length,
    pending:  filtered.filter(s => s.status === "pending" || s.status === "editing").length,
    accepted: filtered.filter(s => s.status === "accepted").length,
    rejected: filtered.filter(s => s.status === "rejected").length,
  }), [filtered]);

  const handleAccept = useCallback((id: string, text: string) => {
    setSuggestions(cs => cs.map(s => s.id === id ? { ...s, status: "accepted", proposed: text } : s));
    onAccept?.(id, text);
  }, [onAccept]);

  const handleReject = useCallback((id: string, reason: string) => {
    setSuggestions(cs => cs.map(s => s.id === id ? { ...s, status: "rejected", rejectionReason: reason } : s));
    onReject?.(id, reason);
  }, [onReject]);

  function handleBulkAccept() {
    setSuggestions(cs => cs.map(s =>
      (s.status === "pending" || s.status === "editing") ? { ...s, status: "accepted" } : s,
    ));
    onBulkAccept?.();
  }

  function handleBulkReject() {
    setSuggestions(cs => cs.map(s =>
      (s.status === "pending" || s.status === "editing") ? { ...s, status: "rejected" } : s,
    ));
    onBulkReject?.();
  }

  return (
    <div className={cn("space-y-4", className)}>
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-sm font-semibold text-foreground">AI Suggestions</h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            <span className="font-mono text-foreground">{stats.pending}</span> pending ·{" "}
            <span className="text-[#1A7F4B]">{stats.accepted} accepted</span> ·{" "}
            <span className="text-muted-foreground">{stats.rejected} rejected</span>
          </p>
        </div>

        {stats.pending > 0 && (
          <div className="flex items-center gap-2 flex-shrink-0">
            <button
              onClick={handleBulkReject}
              className="text-[10px] text-destructive hover:underline font-medium"
            >
              Reject all
            </button>
            <span className="text-muted-foreground text-[10px]">·</span>
            <button
              onClick={handleBulkAccept}
              className="text-[10px] text-[#1A7F4B] hover:underline font-medium"
            >
              Accept all
            </button>
          </div>
        )}
      </div>

      {/* Category filter */}
      <div className="flex items-center gap-1.5 flex-wrap">
        {(["all", "regulatory", "completeness", "clarity", "grammar", "consistency"] as const).map(cat => (
          <button
            key={cat}
            onClick={() => setCatFilter(cat)}
            className={cn(
              "text-[10px] px-2 py-1 rounded-full border font-medium transition-colors",
              catFilter === cat
                ? cat === "all"
                  ? "bg-foreground text-background border-foreground"
                  : `border-transparent text-white`
                : "border-border text-muted-foreground hover:bg-muted",
            )}
            style={catFilter === cat && cat !== "all" ? {
              background: CAT_CONFIG[cat as SuggestionCategory].color,
              borderColor: CAT_CONFIG[cat as SuggestionCategory].color,
            } : {}}
          >
            {cat === "all" ? "All" : CAT_CONFIG[cat as SuggestionCategory].label}
            <span className="ml-1 opacity-70">
              ({cat === "all"
                ? suggestions.filter(s => s.status === "pending").length
                : suggestions.filter(s => s.category === cat && s.status === "pending").length})
            </span>
          </button>
        ))}
      </div>

      {/* Review progress bar */}
      {stats.total > 0 && (
        <div className="flex rounded-full overflow-hidden h-1.5 bg-muted">
          <div
            className="bg-[#1A7F4B] transition-all"
            style={{ width: `${(stats.accepted / stats.total) * 100}%` }}
          />
          <div
            className="bg-border transition-all"
            style={{ width: `${(stats.rejected / stats.total) * 100}%` }}
          />
        </div>
      )}

      {/* Suggestion cards */}
      {filtered.length === 0 ? (
        <div className="py-8 text-center text-[11px] text-muted-foreground border border-dashed border-border rounded-xl">
          {suggestions.length === 0
            ? "No AI suggestions for this section yet."
            : "No suggestions match the selected filter."}
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map(s => (
            <SuggestionCard
              key={s.id}
              suggestion={s}
              onAccept={handleAccept}
              onReject={handleReject}
            />
          ))}
        </div>
      )}

      {stats.pending === 0 && stats.total > 0 && (
        <div className="py-3 text-center text-[11px] text-muted-foreground border-t border-border">
          All {stats.total} suggestions reviewed · {stats.accepted} accepted · {stats.rejected} rejected
        </div>
      )}
    </div>
  );
}
