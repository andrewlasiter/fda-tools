"use client";

/**
 * FDA-286 [PRED-003] — PredicateSelection
 * ==========================================
 * Search + compare interface for selecting 510(k) predicate devices.
 * Integrates with the cosine-similarity search API (FDA-225) and
 * displays predicate health signals from MAUDE + recalls.
 *
 * Features:
 *   - Full-text search with instant filter chips (class / product code / year / applicant)
 *   - SE similarity score from pgvector cosine search
 *   - Predicate health: recall count, adverse events, clearance date, applicant
 *   - Add up to 3 predicates to comparison tray
 *   - Drag-to-reorder comparison columns (visual affordance only — swaps via buttons)
 *   - Sort: similarity / year / AE count / applicant
 *   - Pagination or virtual scroll (offset-based)
 */

import React, { useState, useMemo, useCallback } from "react";
import { cn } from "@/lib/utils";

// ── Types ──────────────────────────────────────────────────────────────────

export type DeviceClass = "I" | "II" | "III" | "U";
export type SortKey = "similarity" | "year" | "ae_count" | "applicant";

export interface PredicateHealth {
  recallCount:   number;
  aeCount:       number;
  status:        "healthy" | "caution" | "toxic";    // from predicate chain validation
}

export interface PredicateDevice {
  kNumber:       string;        // e.g. K231234
  deviceName:    string;
  applicant:     string;
  productCode:   string;
  deviceClass:   DeviceClass;
  clearanceYear: number;
  similarity:    number;        // 0–100 cosine similarity score
  health:        PredicateHealth;
  decisionCode?: string;        // SE / SESE / SESP
  regulationNum?: string;       // 21 CFR xxx.xx
}

export interface PredicateSelectionProps {
  predicates:           PredicateDevice[];
  maxComparisons?:      number;           // default 3
  onCompare?:           (selected: PredicateDevice[]) => void;
  onViewDetails?:       (kNumber: string) => void;
  className?:           string;
}

// ── Config ─────────────────────────────────────────────────────────────────

const CLASS_CONFIG: Record<DeviceClass, { label: string; color: string; bg: string }> = {
  I:   { label: "Class I",   color: "#1A7F4B", bg: "bg-[#1A7F4B]/10"  },
  II:  { label: "Class II",  color: "#005EA2", bg: "bg-[#005EA2]/10"  },
  III: { label: "Class III", color: "#C5191B", bg: "bg-[#C5191B]/10"  },
  U:   { label: "Class U",   color: "#7C3AED", bg: "bg-[#7C3AED]/10"  },
};

const HEALTH_CONFIG: Record<string, { label: string; color: string; dot: string }> = {
  healthy: { label: "Healthy",  color: "#1A7F4B", dot: "bg-[#1A7F4B]" },
  caution: { label: "Caution",  color: "#B45309", dot: "bg-[#B45309]" },
  toxic:   { label: "Toxic",    color: "#C5191B", dot: "bg-[#C5191B]" },
};

const YEARS = Array.from({ length: 15 }, (_, i) => new Date().getFullYear() - i);

// ── Similarity ring ─────────────────────────────────────────────────────────

function SimilarityRing({ score }: { score: number }) {
  const r = 14;
  const circ = 2 * Math.PI * r;
  const dash = (score / 100) * circ;
  const color = score >= 85 ? "#1A7F4B" : score >= 65 ? "#B45309" : "#C5191B";
  return (
    <svg viewBox="0 0 36 36" className="w-9 h-9 flex-shrink-0 -rotate-90">
      <circle cx="18" cy="18" r={r} fill="none" stroke="currentColor" strokeWidth="3"
        className="text-muted/40" />
      <circle cx="18" cy="18" r={r} fill="none" stroke={color} strokeWidth="3"
        strokeDasharray={`${dash} ${circ}`} strokeLinecap="round" />
      <text x="18" y="22" textAnchor="middle" fontSize="8" fontWeight="bold"
        fill={color} className="rotate-90 origin-center" style={{ transform: "rotate(90deg)", transformOrigin: "18px 18px" }}>
        {score}
      </text>
    </svg>
  );
}

// ── PredicateCard ──────────────────────────────────────────────────────────

function PredicateCard({
  predicate,
  inComparison,
  comparisonFull,
  onToggleCompare,
  onViewDetails,
}: {
  predicate:       PredicateDevice;
  inComparison:    boolean;
  comparisonFull:  boolean;
  onToggleCompare: () => void;
  onViewDetails:   () => void;
}) {
  const cls    = CLASS_CONFIG[predicate.deviceClass];
  const health = HEALTH_CONFIG[predicate.health.status];

  return (
    <div className={cn(
      "rounded-xl border overflow-hidden transition-colors cursor-pointer group",
      inComparison
        ? "border-[#005EA2]/50 bg-[#005EA2]/5"
        : "border-border hover:border-[#005EA2]/30 hover:bg-muted/20",
    )}>
      {/* Header */}
      <div className="flex items-start gap-3 p-4" onClick={onViewDetails}>
        <SimilarityRing score={predicate.similarity} />

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[12px] font-bold text-foreground font-mono">
              {predicate.kNumber}
            </span>
            <span
              className={cn("text-[9px] font-bold px-1.5 py-0.5 rounded", cls.bg)}
              style={{ color: cls.color }}
            >
              {cls.label}
            </span>
            {predicate.decisionCode && (
              <span className="text-[9px] font-mono text-muted-foreground">
                {predicate.decisionCode}
              </span>
            )}
          </div>
          <p className="text-[11px] font-medium text-foreground mt-0.5 line-clamp-2">
            {predicate.deviceName}
          </p>
          <p className="text-[10px] text-muted-foreground mt-0.5">
            {predicate.applicant} · {predicate.clearanceYear} · {predicate.productCode}
          </p>
          {predicate.regulationNum && (
            <p className="text-[10px] font-mono text-muted-foreground">
              21 CFR {predicate.regulationNum}
            </p>
          )}
        </div>
      </div>

      {/* Health bar */}
      <div className="px-4 pb-3 flex items-center gap-4">
        <div className="flex items-center gap-1.5">
          <div className={cn("w-2 h-2 rounded-full flex-shrink-0", health.dot)} />
          <span className="text-[10px] font-medium" style={{ color: health.color }}>
            {health.label}
          </span>
        </div>
        <span className="text-[10px] text-muted-foreground">
          {predicate.health.recallCount} recalls
        </span>
        <span className="text-[10px] text-muted-foreground">
          {predicate.health.aeCount.toLocaleString()} AEs
        </span>

        <button
          onClick={(e) => { e.stopPropagation(); onToggleCompare(); }}
          disabled={!inComparison && comparisonFull}
          className={cn(
            "ml-auto text-[10px] px-2.5 py-1 rounded border font-medium transition-colors cursor-pointer",
            inComparison
              ? "border-[#005EA2]/40 text-[#005EA2] bg-[#005EA2]/10 hover:bg-[#005EA2]/20"
              : comparisonFull
                ? "border-border text-muted-foreground/50 cursor-not-allowed"
                : "border-border text-muted-foreground hover:border-[#005EA2]/40 hover:text-[#005EA2]",
          )}
        >
          {inComparison ? "✓ In comparison" : "Add to compare"}
        </button>
      </div>
    </div>
  );
}

// ── Comparison tray ────────────────────────────────────────────────────────

function ComparisonTray({
  selected,
  onRemove,
  onSwap,
  onCompare,
}: {
  selected:  PredicateDevice[];
  onRemove:  (kNumber: string) => void;
  onSwap:    (i: number, j: number) => void;
  onCompare: () => void;
}) {
  if (selected.length === 0) return null;

  return (
    <div className="sticky bottom-0 bg-background border-t border-[#005EA2]/30 px-4 py-3 flex items-center gap-3 flex-wrap shadow-lg">
      <span className="text-[11px] font-bold text-foreground">Compare:</span>
      {selected.map((p, i) => (
        <div key={p.kNumber} className="flex items-center gap-1.5">
          {i > 0 && (
            <button
              onClick={() => onSwap(i - 1, i)}
              className="text-[10px] text-muted-foreground hover:text-foreground px-1 cursor-pointer"
              title="Move left"
            >
              ←
            </button>
          )}
          <div className="flex items-center gap-1.5 bg-[#005EA2]/10 border border-[#005EA2]/30 rounded-lg px-2.5 py-1">
            <span className="text-[10px] font-mono font-bold text-[#005EA2]">{p.kNumber}</span>
            <span className="text-[10px] text-muted-foreground truncate max-w-24">{p.deviceName}</span>
            <button
              onClick={() => onRemove(p.kNumber)}
              className="text-[10px] text-muted-foreground hover:text-destructive ml-1 cursor-pointer"
            >
              ✕
            </button>
          </div>
        </div>
      ))}
      <button
        onClick={onCompare}
        disabled={selected.length < 2}
        className={cn(
          "ml-auto text-[11px] px-4 py-1.5 rounded-lg border font-bold transition-colors cursor-pointer",
          selected.length >= 2
            ? "bg-[#005EA2] border-[#005EA2] text-white hover:bg-[#005EA2]/90"
            : "border-border text-muted-foreground cursor-not-allowed",
        )}
      >
        Compare {selected.length} predicates
      </button>
    </div>
  );
}

// ── Main Component ─────────────────────────────────────────────────────────

export function PredicateSelection({
  predicates,
  maxComparisons = 3,
  onCompare,
  onViewDetails,
  className,
}: PredicateSelectionProps) {
  const [query,       setQuery]       = useState("");
  const [classFilter, setClassFilter] = useState<DeviceClass | "all">("all");
  const [yearFilter,  setYearFilter]  = useState<number | "all">("all");
  const [sortKey,     setSortKey]     = useState<SortKey>("similarity");
  const [comparison,  setComparison]  = useState<PredicateDevice[]>([]);

  const filtered = useMemo(() => {
    let list = predicates;
    if (query.trim()) {
      const q = query.toLowerCase();
      list = list.filter(p =>
        p.kNumber.toLowerCase().includes(q) ||
        p.deviceName.toLowerCase().includes(q) ||
        p.applicant.toLowerCase().includes(q) ||
        p.productCode.toLowerCase().includes(q),
      );
    }
    if (classFilter !== "all") list = list.filter(p => p.deviceClass === classFilter);
    if (yearFilter  !== "all") list = list.filter(p => p.clearanceYear === yearFilter);
    return [...list].sort((a, b) => {
      switch (sortKey) {
        case "similarity": return b.similarity - a.similarity;
        case "year":       return b.clearanceYear - a.clearanceYear;
        case "ae_count":   return a.health.aeCount - b.health.aeCount;
        case "applicant":  return a.applicant.localeCompare(b.applicant);
        default:           return 0;
      }
    });
  }, [predicates, query, classFilter, yearFilter, sortKey]);

  const toggleCompare = useCallback((p: PredicateDevice) => {
    setComparison(cs => {
      const exists = cs.find(c => c.kNumber === p.kNumber);
      if (exists) return cs.filter(c => c.kNumber !== p.kNumber);
      if (cs.length >= maxComparisons) return cs;
      return [...cs, p];
    });
  }, [maxComparisons]);

  function swapComparison(i: number, j: number) {
    setComparison(cs => {
      const next = [...cs];
      [next[i], next[j]] = [next[j], next[i]];
      return next;
    });
  }

  return (
    <div className={cn("flex flex-col h-full", className)}>
      {/* Search + filters */}
      <div className="p-4 border-b border-border space-y-3 shrink-0">
        <input
          type="search"
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="Search K-number, device name, applicant, product code…"
          className="w-full px-3 py-2 text-[12px] rounded-lg border border-border bg-background outline-none focus:border-[#005EA2]/50 text-foreground placeholder:text-muted-foreground font-mono"
        />

        <div className="flex items-center gap-2 flex-wrap">
          {/* Class filter */}
          {(["all", "I", "II", "III", "U"] as const).map(cls => (
            <button
              key={cls}
              onClick={() => setClassFilter(cls)}
              className={cn(
                "text-[10px] px-2 py-1 rounded-full border font-medium transition-colors cursor-pointer",
                classFilter === cls
                  ? cls === "all"
                    ? "bg-foreground text-background border-foreground"
                    : `border-transparent text-white`
                  : "border-border text-muted-foreground hover:bg-muted",
              )}
              style={classFilter === cls && cls !== "all" ? {
                background: CLASS_CONFIG[cls].color,
                borderColor: CLASS_CONFIG[cls].color,
              } : {}}
            >
              {cls === "all" ? "All Classes" : CLASS_CONFIG[cls].label}
            </button>
          ))}

          <div className="w-px h-4 bg-border" />

          {/* Sort */}
          <select
            value={sortKey}
            onChange={e => setSortKey(e.target.value as SortKey)}
            className="text-[10px] px-2 py-1 rounded border border-border bg-background text-foreground outline-none cursor-pointer"
          >
            <option value="similarity">Sort: Similarity</option>
            <option value="year">Sort: Year (newest)</option>
            <option value="ae_count">Sort: AEs (fewest)</option>
            <option value="applicant">Sort: Applicant (A–Z)</option>
          </select>

          {/* Year filter */}
          <select
            value={yearFilter}
            onChange={e => setYearFilter(e.target.value === "all" ? "all" : Number(e.target.value))}
            className="text-[10px] px-2 py-1 rounded border border-border bg-background text-foreground outline-none cursor-pointer"
          >
            <option value="all">All Years</option>
            {YEARS.map(y => <option key={y} value={y}>{y}</option>)}
          </select>

          <span className="ml-auto text-[10px] text-muted-foreground">
            {filtered.length} result{filtered.length !== 1 ? "s" : ""}
          </span>
        </div>
      </div>

      {/* Results */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {filtered.length === 0 ? (
          <div className="py-12 text-center text-[11px] text-muted-foreground border border-dashed border-border rounded-xl">
            No predicates match your search.
          </div>
        ) : (
          filtered.map(p => (
            <PredicateCard
              key={p.kNumber}
              predicate={p}
              inComparison={!!comparison.find(c => c.kNumber === p.kNumber)}
              comparisonFull={comparison.length >= maxComparisons}
              onToggleCompare={() => toggleCompare(p)}
              onViewDetails={() => onViewDetails?.(p.kNumber)}
            />
          ))
        )}
      </div>

      {/* Comparison tray */}
      <ComparisonTray
        selected={comparison}
        onRemove={(kn) => setComparison(cs => cs.filter(c => c.kNumber !== kn))}
        onSwap={swapComparison}
        onCompare={() => onCompare?.(comparison)}
      />
    </div>
  );
}
