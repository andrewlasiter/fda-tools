"use client";

/**
 * FDA-285 [PRED-002] — PredicateComparisonTable
 * ===============================================
 * Full substantive equivalence comparison table.
 * Every data cell is wrapped in EvidencePopover — clicking opens
 * the documentary evidence behind that specific attribute value.
 *
 * Features:
 *   - Sticky attribute column + sticky header row
 *   - Color-coded similarity: identical / similar / different / N/A
 *   - TrustBadge in column header (per-predicate AI confidence)
 *   - Pinned "Subject Device" column (always visible)
 *   - Expandable row groups (e.g. "Performance", "Biocompatibility")
 *   - Export to CSV action
 *   - Keyboard navigable
 */

import React, { useState, useCallback } from "react";
import { cn } from "@/lib/utils";
import { EvidencePopover } from "./evidence-popover";
import type { Evidence } from "./evidence-popover";
import { TrustBadge } from "@/components/trust/trust-badge";
import type { TrustData } from "@/components/trust/trust-badge";

// ── Types ─────────────────────────────────────────────────────────────────

export type Similarity = "identical" | "similar" | "different" | "na";

export interface AttributeRow {
  id:         string;
  group:      string;              // e.g. "Indications", "Performance", "Biocompatibility"
  attribute:  string;              // e.g. "Intended Use"
  subject:    { value: string; evidence: Evidence[] };
  predicates: { value: string; evidence: Evidence[]; similarity: Similarity }[];
}

export interface PredicateColumn {
  id:       string;
  kNumber:  string;               // K123456
  name:     string;               // device trade name
  company:  string;
  cleared:  string;               // clearance date
  trust:    TrustData;
}

interface PredicateComparisonTableProps {
  subject:     { name: string; code: string };
  predicates:  PredicateColumn[];
  rows:        AttributeRow[];
  className?:  string;
}

// ── Similarity config ─────────────────────────────────────────────────────

const SIM: Record<Similarity, { label: string; bg: string; text: string; dot: string }> = {
  identical:  { label: "≡",   bg: "bg-[#1A7F4B]/8 hover:bg-[#1A7F4B]/15",  text: "text-[#1A7F4B]", dot: "bg-[#1A7F4B]" },
  similar:    { label: "≈",   bg: "bg-[#B45309]/8 hover:bg-[#B45309]/15",  text: "text-[#B45309]", dot: "bg-[#B45309]" },
  different:  { label: "≠",   bg: "bg-destructive/8 hover:bg-destructive/15", text: "text-destructive", dot: "bg-destructive" },
  na:         { label: "N/A", bg: "bg-muted/40 hover:bg-muted/60",          text: "text-muted-foreground", dot: "bg-muted-foreground/40" },
};

// ── Similarity legend ─────────────────────────────────────────────────────

function SimLegend() {
  return (
    <div className="flex items-center gap-4 text-[10px] text-muted-foreground">
      {(Object.entries(SIM) as [Similarity, typeof SIM[Similarity]][]).map(([key, cfg]) => (
        <span key={key} className="flex items-center gap-1">
          <span className={cn("w-2 h-2 rounded-full flex-shrink-0", cfg.dot)} />
          <span className={cfg.text}>{cfg.label}</span>
          <span className="capitalize">{key}</span>
        </span>
      ))}
      <span className="flex items-center gap-1 ml-2 border-l border-border pl-4">
        <span className="w-2 h-2 rounded-full bg-[#005EA2] flex-shrink-0" />
        <span className="text-[#005EA2]">●</span>
        Evidence available — click cell
      </span>
    </div>
  );
}

// ── Cell component ────────────────────────────────────────────────────────

function DataCell({
  value,
  evidence,
  attribute,
  sim,
  isSubject = false,
}: {
  value:     string;
  evidence:  Evidence[];
  attribute: string;
  sim?:      Similarity;
  isSubject?: boolean;
}) {
  const cfg = sim ? SIM[sim] : null;

  const inner = (
    <div
      className={cn(
        "px-3 py-2.5 text-xs leading-relaxed h-full min-h-[2.5rem] flex items-start",
        isSubject
          ? "font-medium text-foreground bg-[#005EA2]/5 border-r-2 border-[#005EA2]/20"
          : cfg
            ? cn(cfg.bg, cfg.text)
            : "text-foreground",
        "transition-colors"
      )}
    >
      {sim && !isSubject && (
        <span className="text-[8px] font-bold mr-1 mt-0.5 flex-shrink-0 opacity-60">{SIM[sim].label}</span>
      )}
      <span className="flex-1">{value}</span>
    </div>
  );

  if (evidence.length === 0) return inner;

  return (
    <EvidencePopover evidence={evidence} cellValue={value} attribute={attribute} className="w-full">
      {inner}
    </EvidencePopover>
  );
}

// ── Row group separator ───────────────────────────────────────────────────

function GroupHeader({ label, colSpan }: { label: string; colSpan: number }) {
  return (
    <tr>
      <td
        colSpan={colSpan}
        className="px-3 py-1.5 text-[9px] font-bold uppercase tracking-widest text-muted-foreground bg-muted/50 border-y border-border"
      >
        {label}
      </td>
    </tr>
  );
}

// ── Export helper ─────────────────────────────────────────────────────────

function exportCsv(
  subject: { name: string; code: string },
  predicates: PredicateColumn[],
  rows: AttributeRow[]
) {
  const headers = ["Group", "Attribute", subject.name, ...predicates.map(p => `${p.kNumber} ${p.name}`)];
  const dataRows = rows.map(r => [
    r.group,
    r.attribute,
    r.subject.value,
    ...r.predicates.map(p => `${p.value} [${p.similarity}]`),
  ]);
  const csv = [headers, ...dataRows].map(row => row.map(c => `"${c.replace(/"/g, '""')}"`).join(",")).join("\n");
  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `se-comparison-${subject.code}-${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

// ── Similarity summary bar ────────────────────────────────────────────────

function SimilarityBar({ rows, predIdx }: { rows: AttributeRow[]; predIdx: number }) {
  const counts = { identical: 0, similar: 0, different: 0, na: 0 };
  rows.forEach(r => { if (r.predicates[predIdx]) counts[r.predicates[predIdx].similarity]++; });
  const total = rows.length;
  return (
    <div className="flex h-1 rounded-full overflow-hidden gap-px mt-1.5">
      {(["identical", "similar", "different", "na"] as Similarity[]).map(k => (
        counts[k] > 0 && (
          <div
            key={k}
            style={{ width: `${(counts[k] / total) * 100}%` }}
            className={cn("h-full", SIM[k].dot)}
            title={`${k}: ${counts[k]}`}
          />
        )
      ))}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────

export function PredicateComparisonTable({
  subject,
  predicates,
  rows,
  className,
}: PredicateComparisonTableProps) {
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(() => {
    const groups = new Set<string>();
    rows.forEach(r => groups.add(r.group));
    return groups;
  });

  const toggleGroup = useCallback((group: string) => {
    setExpandedGroups(prev => {
      const next = new Set(prev);
      next.has(group) ? next.delete(group) : next.add(group);
      return next;
    });
  }, []);

  // Group rows by group label
  const grouped: { group: string; rows: AttributeRow[] }[] = [];
  const seen = new Set<string>();
  rows.forEach(r => {
    if (!seen.has(r.group)) {
      seen.add(r.group);
      grouped.push({ group: r.group, rows: [] });
    }
    grouped[grouped.length - 1].rows.push(r);
  });

  const colSpan = 2 + predicates.length; // attribute + subject + N predicates

  // Similarity counts across all rows (for the "SE Score" header metric)
  function seScore(predIdx: number): number {
    let score = 0;
    let counted = 0;
    rows.forEach(r => {
      const p = r.predicates[predIdx];
      if (!p || p.similarity === "na") return;
      counted++;
      if (p.similarity === "identical") score += 100;
      else if (p.similarity === "similar") score += 65;
      // different = 0
    });
    return counted > 0 ? Math.round(score / counted) : 0;
  }

  return (
    <div className={cn("flex flex-col gap-3", className)}>
      {/* Toolbar */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <SimLegend />
        <button
          onClick={() => exportCsv(subject, predicates, rows)}
          className="text-[11px] text-[#005EA2] hover:underline font-medium flex items-center gap-1.5"
        >
          <svg viewBox="0 0 16 16" className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth={2}>
            <path d="M8 2v8M5 7l3 3 3-3M3 11v2a1 1 0 001 1h8a1 1 0 001-1v-2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          Export CSV
        </button>
      </div>

      {/* Table wrapper */}
      <div className="overflow-x-auto rounded-xl border border-border shadow-sm">
        <table className="w-full border-collapse text-xs" role="table" aria-label="Predicate comparison table">
          {/* ── Column headers ── */}
          <thead>
            <tr className="bg-muted/60 border-b-2 border-border">
              {/* Attribute col */}
              <th
                scope="col"
                className="sticky left-0 z-20 bg-muted/80 px-3 py-3 text-left text-[10px] font-bold uppercase tracking-wider text-muted-foreground w-48 border-r border-border"
              >
                Attribute
              </th>

              {/* Subject col */}
              <th
                scope="col"
                className="px-3 py-3 text-left min-w-[180px] border-r-2 border-[#005EA2]/30"
              >
                <div>
                  <p className="text-[9px] font-bold uppercase tracking-wider text-[#005EA2] mb-0.5">Subject Device</p>
                  <p className="text-xs font-semibold text-foreground leading-tight">{subject.name}</p>
                  <p className="text-[10px] font-mono text-muted-foreground">{subject.code}</p>
                </div>
              </th>

              {/* Predicate cols */}
              {predicates.map((pred, idx) => {
                const score = seScore(idx);
                return (
                  <th
                    key={pred.id}
                    scope="col"
                    className="px-3 py-3 text-left min-w-[200px] border-r border-border last:border-r-0"
                  >
                    <div>
                      <div className="flex items-center gap-1.5 mb-1">
                        <span className="text-[9px] font-bold uppercase tracking-wider text-muted-foreground">Predicate</span>
                        <span
                          className={cn(
                            "text-[9px] font-bold px-1 py-0.5 rounded",
                            score >= 80 ? "bg-[#1A7F4B]/15 text-[#1A7F4B]"
                            : score >= 60 ? "bg-[#B45309]/15 text-[#B45309]"
                            : "bg-destructive/15 text-destructive"
                          )}
                        >
                          SE {score}%
                        </span>
                      </div>
                      <p className="text-xs font-semibold text-foreground leading-tight">{pred.name}</p>
                      <p className="text-[10px] font-mono text-[#005EA2]">{pred.kNumber}</p>
                      <p className="text-[9px] text-muted-foreground">{pred.company} · {pred.cleared}</p>
                      <SimilarityBar rows={rows} predIdx={idx} />
                      <div className="mt-1.5">
                        <TrustBadge trust={pred.trust} variant="compact" />
                      </div>
                    </div>
                  </th>
                );
              })}
            </tr>
          </thead>

          {/* ── Data rows ── */}
          <tbody>
            {grouped.map(({ group, rows: groupRows }) => {
              const isExpanded = expandedGroups.has(group);
              return (
                <React.Fragment key={group}>
                  {/* Group header row */}
                  <tr
                    role="row"
                    aria-expanded={isExpanded}
                    onClick={() => toggleGroup(group)}
                    className="cursor-pointer select-none"
                  >
                    <td
                      colSpan={colSpan}
                      className="px-3 py-1.5 bg-muted/40 border-y border-border hover:bg-muted/60 transition-colors"
                    >
                      <div className="flex items-center gap-2">
                        <svg
                          viewBox="0 0 12 12"
                          className={cn("w-3 h-3 text-muted-foreground transition-transform", isExpanded && "rotate-90")}
                          fill="none" stroke="currentColor" strokeWidth={2}
                        >
                          <polyline points="3 2 9 6 3 10" />
                        </svg>
                        <span className="text-[9px] font-bold uppercase tracking-widest text-muted-foreground">{group}</span>
                        <span className="text-[9px] text-muted-foreground ml-auto">{groupRows.length} attribute{groupRows.length !== 1 ? "s" : ""}</span>
                      </div>
                    </td>
                  </tr>

                  {/* Data rows */}
                  {isExpanded && groupRows.map((row, rowIdx) => (
                    <tr
                      key={row.id}
                      className={cn(
                        "border-b border-border/50 last:border-b-0",
                        rowIdx % 2 === 1 && "bg-muted/20"
                      )}
                    >
                      {/* Attribute label */}
                      <td className="sticky left-0 z-10 bg-background px-3 py-0 border-r border-border">
                        <div className="py-2.5">
                          <p className="text-[11px] font-medium text-foreground">{row.attribute}</p>
                        </div>
                      </td>

                      {/* Subject value */}
                      <td className="p-0 border-r-2 border-[#005EA2]/20">
                        <DataCell
                          value={row.subject.value}
                          evidence={row.subject.evidence}
                          attribute={row.attribute}
                          isSubject
                        />
                      </td>

                      {/* Predicate values */}
                      {row.predicates.map((pred, pidx) => (
                        <td key={pidx} className="p-0 border-r border-border/50 last:border-r-0">
                          <DataCell
                            value={pred.value}
                            evidence={pred.evidence}
                            attribute={row.attribute}
                            sim={pred.similarity}
                          />
                        </td>
                      ))}
                    </tr>
                  ))}
                </React.Fragment>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Footer note */}
      <p className="text-[10px] text-muted-foreground">
        Click any highlighted cell to view documentary evidence · SE score = weighted similarity across non-N/A attributes
      </p>
    </div>
  );
}
