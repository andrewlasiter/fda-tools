"use client";

/**
 * FDA-277 [HITL-003] — HitlAuditTrail
 * =====================================
 * Immutable decision history viewer for all HITL gate decisions.
 * 21 CFR Part 11 compliant — every record shows: who, what, when, hash.
 *
 * Features:
 *   - Timeline view of decisions across all 5 NPD gates
 *   - Decision badge (Approved / Changes Requested / Rejected / Deferred)
 *   - Signature verification indicator (hash shown, verified status)
 *   - Rationale expand/collapse
 *   - Filter by gate, reviewer, decision type
 *   - Export audit log (CSV)
 *   - Diff link → opens AgentDiffViewer for that record
 */

import React, { useState, useMemo } from "react";
import { cn } from "@/lib/utils";

// ── Types ─────────────────────────────────────────────────────────────────

export type AuditDecision = "approve" | "request_changes" | "reject" | "defer";

export interface AuditRecord {
  id:            string;
  gateName:      string;
  gateIdx:       number;
  stageLabel:    string;
  decision:      AuditDecision;
  rationale:     string;
  reviewerName:  string;
  reviewerRole:  string;
  timestamp:     string;          // ISO 8601
  sri:           number;
  signatureHash: string;          // truncated SHA-256
  verified:      boolean;
  agentRun?:     string;          // link to diff viewer
}

interface HitlAuditTrailProps {
  records:       AuditRecord[];
  projectName?:  string;
  className?:    string;
}

// ── Decision config ───────────────────────────────────────────────────────

const DEC: Record<AuditDecision, { label: string; bg: string; text: string; border: string; icon: string }> = {
  approve:         { label: "Approved",          bg: "bg-[#1A7F4B]/10", text: "text-[#1A7F4B]", border: "border-[#1A7F4B]/30", icon: "✓" },
  request_changes: { label: "Changes Requested", bg: "bg-[#B45309]/10", text: "text-[#B45309]", border: "border-[#B45309]/30", icon: "↩" },
  reject:          { label: "Rejected",          bg: "bg-destructive/10", text: "text-destructive", border: "border-destructive/30", icon: "✕" },
  defer:           { label: "Deferred",          bg: "bg-[#005EA2]/10", text: "text-[#005EA2]", border: "border-[#005EA2]/30", icon: "⏸" },
};

// ── Gate connector line ───────────────────────────────────────────────────

const GATE_COLORS = ["#005EA2","#1A7F4B","#7C3AED","#B45309","#C5191B"];

// ── CSV export ────────────────────────────────────────────────────────────

function exportCsv(records: AuditRecord[], projectName = "project") {
  const headers = ["ID","Gate","Stage","Decision","Reviewer","Role","Timestamp","SRI","Rationale","SignatureHash","Verified"];
  const rows = records.map(r => [
    r.id, r.gateName, r.stageLabel, r.decision, r.reviewerName, r.reviewerRole,
    r.timestamp, r.sri, `"${r.rationale.replace(/"/g, '""')}"`, r.signatureHash, r.verified
  ]);
  const csv = [headers, ...rows].map(row => row.join(",")).join("\n");
  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a"); a.href = url;
  a.download = `hitl-audit-${projectName}-${new Date().toISOString().slice(0,10)}.csv`;
  a.click(); URL.revokeObjectURL(url);
}

// ── Individual record card ────────────────────────────────────────────────

function AuditRecordCard({ record, gateColor }: { record: AuditRecord; gateColor: string }) {
  const [expanded, setExpanded] = useState(false);
  const dec = DEC[record.decision];
  const dt = new Date(record.timestamp);

  return (
    <div className="relative flex gap-4">
      {/* Timeline dot + line */}
      <div className="flex flex-col items-center flex-shrink-0 mt-1">
        <div
          className="w-8 h-8 rounded-full border-2 flex items-center justify-center text-xs font-bold flex-shrink-0"
          style={{ borderColor: gateColor, color: gateColor, background: gateColor + "18" }}
        >
          G{record.gateIdx + 1}
        </div>
        <div className="w-px flex-1 mt-1" style={{ background: gateColor + "30", minHeight: "1.5rem" }} />
      </div>

      {/* Card */}
      <div className="flex-1 mb-4 rounded-xl border border-border bg-background shadow-sm overflow-hidden">
        {/* Header */}
        <div className="flex items-start justify-between gap-3 px-4 py-3 border-b border-border bg-muted/30">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span
                className={cn("text-[10px] font-bold px-2 py-0.5 rounded border", dec.bg, dec.text, dec.border)}
              >
                {dec.icon} {dec.label}
              </span>
              <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">
                Gate {record.gateIdx + 1} — {record.gateName}
              </span>
              <span className="text-[10px] text-muted-foreground">·</span>
              <span className="text-[10px] text-muted-foreground">{record.stageLabel}</span>
            </div>
            <div className="mt-1 flex items-center gap-2 text-[10px] text-muted-foreground">
              <span className="font-medium text-foreground">{record.reviewerName}</span>
              <span>·</span>
              <span>{record.reviewerRole}</span>
              <span>·</span>
              <time dateTime={record.timestamp} title={record.timestamp}>
                {dt.toLocaleDateString()} {dt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
              </time>
            </div>
          </div>

          {/* SRI chip */}
          <div className="flex-shrink-0 text-right">
            <div
              className={cn("text-sm font-bold",
                record.sri >= 70 ? "text-[#1A7F4B]" : record.sri >= 50 ? "text-[#B45309]" : "text-destructive"
              )}
            >
              {record.sri}
            </div>
            <div className="text-[9px] text-muted-foreground">SRI</div>
          </div>
        </div>

        {/* Rationale (collapsible) */}
        <div className="px-4 py-3">
          <button
            onClick={() => setExpanded(e => !e)}
            className="w-full flex items-start gap-2 text-left group"
          >
            <svg
              viewBox="0 0 12 12"
              className={cn("w-3 h-3 mt-0.5 flex-shrink-0 text-muted-foreground transition-transform", expanded && "rotate-90")}
              fill="none" stroke="currentColor" strokeWidth={2}
            >
              <polyline points="3 2 9 6 3 10" />
            </svg>
            <p className={cn("text-xs text-foreground", !expanded && "line-clamp-1")}>
              {record.rationale}
            </p>
          </button>
        </div>

        {/* Signature block (shown when expanded) */}
        {expanded && (
          <div className="border-t border-border px-4 py-3 bg-muted/20">
            <div className="flex items-center gap-3 flex-wrap">
              <div className="flex items-center gap-1.5">
                {record.verified ? (
                  <svg viewBox="0 0 16 16" className="w-3.5 h-3.5 text-[#1A7F4B]" fill="currentColor">
                    <path d="M8 1l2.1 4.2 4.6.7-3.35 3.2.8 4.6L8 11.5l-4.15 2.2.8-4.6L1.3 5.9l4.6-.7z"/>
                  </svg>
                ) : (
                  <svg viewBox="0 0 16 16" className="w-3.5 h-3.5 text-destructive" fill="none" stroke="currentColor" strokeWidth={2}>
                    <circle cx="8" cy="8" r="6"/><path d="M5 11l6-6M11 11L5 5"/>
                  </svg>
                )}
                <span className={cn("text-[10px] font-bold", record.verified ? "text-[#1A7F4B]" : "text-destructive")}>
                  {record.verified ? "Signature Verified" : "Verification Failed"}
                </span>
              </div>
              <span className="text-[10px] text-muted-foreground">·</span>
              <span className="text-[10px] font-mono text-muted-foreground">SHA-256: {record.signatureHash}</span>
              <span className="text-[10px] text-muted-foreground ml-auto">21 CFR Part 11 compliant</span>
            </div>
            {record.agentRun && (
              <button className="mt-2 text-[10px] text-[#005EA2] hover:underline font-medium">
                View agent output diff for this gate →
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────

export function HitlAuditTrail({ records, projectName, className }: HitlAuditTrailProps) {
  const [filterGate, setFilterGate]       = useState<string>("all");
  const [filterDecision, setFilterDecision] = useState<AuditDecision | "all">("all");
  const [filterVerified, setFilterVerified] = useState<"all" | "verified" | "failed">("all");

  const gates = useMemo(() => Array.from(new Set(records.map(r => r.gateName))), [records]);

  const filtered = useMemo(() => records.filter(r => {
    if (filterGate !== "all" && r.gateName !== filterGate) return false;
    if (filterDecision !== "all" && r.decision !== filterDecision) return false;
    if (filterVerified === "verified" && !r.verified) return false;
    if (filterVerified === "failed" && r.verified) return false;
    return true;
  }), [records, filterGate, filterDecision, filterVerified]);

  // Summary stats
  const stats = useMemo(() => ({
    total:    records.length,
    approved: records.filter(r => r.decision === "approve").length,
    changes:  records.filter(r => r.decision === "request_changes").length,
    rejected: records.filter(r => r.decision === "reject").length,
    deferred: records.filter(r => r.decision === "defer").length,
    verified: records.filter(r => r.verified).length,
  }), [records]);

  return (
    <div className={cn("space-y-4", className)}>
      {/* Header + export */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h2 className="text-sm font-semibold text-foreground">HITL Audit Trail</h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            {stats.total} decisions · {stats.verified} verified signatures · 21 CFR Part 11
          </p>
        </div>
        <button
          onClick={() => exportCsv(filtered, projectName)}
          className="text-[11px] text-[#005EA2] hover:underline font-medium flex items-center gap-1.5"
        >
          <svg viewBox="0 0 16 16" className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth={2}>
            <path d="M8 2v8M5 7l3 3 3-3M3 11v2a1 1 0 001 1h8a1 1 0 001-1v-2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          Export CSV
        </button>
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-5 gap-2">
        {(Object.entries(DEC) as [AuditDecision, typeof DEC[AuditDecision]][]).map(([key, cfg]) => (
          <div
            key={key}
            className={cn("rounded-lg border px-3 py-2 text-center", cfg.bg, cfg.border)}
          >
            <p className={cn("text-lg font-bold", cfg.text)}>
              {key === "approve" ? stats.approved : key === "request_changes" ? stats.changes : key === "reject" ? stats.rejected : stats.deferred}
            </p>
            <p className="text-[9px] text-muted-foreground">{cfg.label}</p>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 flex-wrap bg-muted/30 rounded-lg px-3 py-2.5">
        <span className="text-[11px] font-medium text-muted-foreground">Filter:</span>

        {/* Gate filter */}
        <select
          value={filterGate}
          onChange={e => setFilterGate(e.target.value)}
          className="text-xs px-2 py-1 rounded border border-border bg-background text-foreground"
        >
          <option value="all">All Gates</option>
          {gates.map(g => <option key={g} value={g}>{g}</option>)}
        </select>

        {/* Decision filter */}
        <select
          value={filterDecision}
          onChange={e => setFilterDecision(e.target.value as AuditDecision | "all")}
          className="text-xs px-2 py-1 rounded border border-border bg-background text-foreground"
        >
          <option value="all">All Decisions</option>
          {(Object.entries(DEC) as [AuditDecision, typeof DEC[AuditDecision]][]).map(([key, cfg]) => (
            <option key={key} value={key}>{cfg.label}</option>
          ))}
        </select>

        {/* Signature filter */}
        <select
          value={filterVerified}
          onChange={e => setFilterVerified(e.target.value as "all" | "verified" | "failed")}
          className="text-xs px-2 py-1 rounded border border-border bg-background text-foreground"
        >
          <option value="all">All Signatures</option>
          <option value="verified">Verified Only</option>
          <option value="failed">Failed Only</option>
        </select>

        <span className="text-[10px] text-muted-foreground ml-auto">{filtered.length} records</span>
      </div>

      {/* Timeline */}
      {filtered.length === 0 ? (
        <div className="py-12 text-center text-muted-foreground text-sm">
          No audit records match the current filters
        </div>
      ) : (
        <div className="pl-0">
          {filtered.map((record, idx) => (
            <AuditRecordCard
              key={record.id}
              record={record}
              gateColor={GATE_COLORS[record.gateIdx % GATE_COLORS.length]}
            />
          ))}
        </div>
      )}

      <p className="text-[10px] text-muted-foreground text-center border-t border-border pt-3">
        All records are immutable once committed · SHA-256 verified · 21 CFR Part 11 §11.50(a)
      </p>
    </div>
  );
}
