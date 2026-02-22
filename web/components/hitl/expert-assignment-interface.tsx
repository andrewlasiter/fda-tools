"use client";

/**
 * FDA-278 [HITL-004] — ExpertAssignmentInterface
 * =================================================
 * Routes HITL gate reviews to specific regulatory experts.
 * Displays expert profiles, current workload, specializations,
 * and allows RA leads to assign or re-assign gate reviews.
 *
 * Features:
 *   - Expert roster with availability status (available / busy / OOO)
 *   - Workload meter (open reviews + avg days to close)
 *   - Specialization tags: Class II / III, 510k, De Novo, PMA, Software, Biocompat., etc.
 *   - Assignment form: gate + priority + deadline + notes
 *   - Assignment history timeline (last 5 assignments for this expert)
 *   - Conflict-of-interest flag (same company as applicant)
 *   - Escalation path: direct DM → RA lead → FDA consultant
 */

import React, { useState, useMemo } from "react";
import { cn } from "@/lib/utils";

// ── Types ──────────────────────────────────────────────────────────────────

export type ExpertAvailability = "available" | "busy" | "ooo";

export type ExpertSpecialization =
  | "class_ii"
  | "class_iii"
  | "510k"
  | "de_novo"
  | "pma"
  | "software"
  | "biocompatibility"
  | "sterility"
  | "human_factors"
  | "combination"
  | "ivd"
  | "imaging";

export type AssignmentPriority = "routine" | "expedited" | "urgent";

export interface ExpertAssignment {
  id:            string;
  gateLabel:     string;
  projectName:   string;
  assignedAt:    string;           // ISO 8601
  deadline?:     string;           // ISO 8601
  priority:      AssignmentPriority;
  status:        "open" | "in_review" | "complete" | "overdue";
  notes?:        string;
}

export interface Expert {
  id:                string;
  name:              string;
  title:             string;
  email:             string;
  avatar?:           string;       // initials fallback
  availability:      ExpertAvailability;
  specializations:   ExpertSpecialization[];
  openReviews:       number;
  avgCloseDays:      number;       // average review turnaround
  conflictCompanies?: string[];    // company names → COI flag
  assignments:       ExpertAssignment[];   // history
}

export interface ExpertAssignmentInterfaceProps {
  experts:         Expert[];
  gateLabel:       string;         // which gate is being assigned
  projectName:     string;
  applicantCompany?: string;       // for COI detection
  currentAssigneeId?: string;
  onAssign?:       (expertId: string, opts: AssignmentOptions) => void;
  onUnassign?:     (expertId: string) => void;
  className?:      string;
}

export interface AssignmentOptions {
  priority:  AssignmentPriority;
  deadline?: string;
  notes?:    string;
}

// ── Config ─────────────────────────────────────────────────────────────────

const AVAIL_CONFIG: Record<ExpertAvailability, { label: string; dot: string; text: string }> = {
  available: { label: "Available",    dot: "bg-[#1A7F4B]",  text: "text-[#1A7F4B]"  },
  busy:      { label: "Busy",         dot: "bg-[#B45309]",  text: "text-[#B45309]"  },
  ooo:       { label: "Out of Office",dot: "bg-border",     text: "text-muted-foreground" },
};

const SPEC_CONFIG: Record<ExpertSpecialization, { label: string; color: string }> = {
  class_ii:          { label: "Class II",           color: "#005EA2" },
  class_iii:         { label: "Class III",          color: "#C5191B" },
  "510k":            { label: "510(k)",              color: "#005EA2" },
  de_novo:           { label: "De Novo",            color: "#7C3AED" },
  pma:               { label: "PMA",                color: "#C5191B" },
  software:          { label: "Software / SaMD",    color: "#1A7F4B" },
  biocompatibility:  { label: "Biocompat.",         color: "#B45309" },
  sterility:         { label: "Sterility",          color: "#B45309" },
  human_factors:     { label: "Human Factors",      color: "#005EA2" },
  combination:       { label: "Combination Prod.",  color: "#7C3AED" },
  ivd:               { label: "IVD",                color: "#1A7F4B" },
  imaging:           { label: "Imaging",            color: "#7C3AED" },
};

const PRIORITY_CONFIG: Record<AssignmentPriority, { label: string; color: string; bg: string }> = {
  routine:   { label: "Routine",   color: "#1A7F4B", bg: "bg-[#1A7F4B]/10"  },
  expedited: { label: "Expedited", color: "#B45309", bg: "bg-[#B45309]/10"  },
  urgent:    { label: "Urgent",    color: "#C5191B", bg: "bg-[#C5191B]/10"  },
};

// ── Subcomponents ──────────────────────────────────────────────────────────

function Avatar({ expert }: { expert: Expert }) {
  const initials = expert.name.split(" ").map(n => n[0]).join("").slice(0, 2).toUpperCase();
  return (
    <div className="w-10 h-10 rounded-full bg-[#005EA2]/15 border border-[#005EA2]/20 flex items-center justify-center flex-shrink-0">
      <span className="text-[12px] font-bold text-[#005EA2]">{initials}</span>
    </div>
  );
}

function WorkloadBar({ open, max = 10 }: { open: number; max?: number }) {
  const pct   = Math.min(Math.round((open / max) * 100), 100);
  const color = pct >= 80 ? "#C5191B" : pct >= 50 ? "#B45309" : "#1A7F4B";
  return (
    <div className="h-1.5 rounded-full bg-muted overflow-hidden">
      <div
        className="h-full rounded-full transition-all"
        style={{ width: `${pct}%`, background: color }}
      />
    </div>
  );
}

function ExpertCard({
  expert,
  selected,
  hasCOI,
  onSelect,
}: {
  expert:   Expert;
  selected: boolean;
  hasCOI:   boolean;
  onSelect: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const avail = AVAIL_CONFIG[expert.availability];
  const recentAssignments = expert.assignments.slice(-3);

  return (
    <div
      className={cn(
        "rounded-xl border overflow-hidden cursor-pointer transition-colors",
        selected
          ? "border-[#005EA2]/50 bg-[#005EA2]/5"
          : expert.availability === "ooo"
            ? "border-border bg-muted/20 opacity-60"
            : "border-border hover:border-[#005EA2]/30 hover:bg-muted/30",
      )}
      onClick={onSelect}
    >
      {/* Header */}
      <div className="flex items-start gap-3 p-4">
        <Avatar expert={expert} />

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[12px] font-bold text-foreground">{expert.name}</span>
            {selected && (
              <span className="text-[9px] font-bold bg-[#005EA2] text-white px-1.5 py-0.5 rounded">
                Selected
              </span>
            )}
            {hasCOI && (
              <span className="text-[9px] font-bold bg-[#C5191B]/10 text-[#C5191B] border border-[#C5191B]/30 px-1.5 py-0.5 rounded">
                ⚑ COI
              </span>
            )}
          </div>
          <p className="text-[10px] text-muted-foreground">{expert.title}</p>
          <p className="text-[10px] text-muted-foreground">{expert.email}</p>

          {/* Availability */}
          <div className="flex items-center gap-1.5 mt-1.5">
            <div className={cn("w-2 h-2 rounded-full flex-shrink-0", avail.dot)} />
            <span className={cn("text-[10px] font-medium", avail.text)}>{avail.label}</span>
            <span className="text-[10px] text-muted-foreground">·</span>
            <span className="text-[10px] text-muted-foreground">avg {expert.avgCloseDays}d close</span>
          </div>
        </div>

        <button
          onClick={(e) => { e.stopPropagation(); setExpanded(v => !v); }}
          className="text-[10px] text-muted-foreground hover:text-foreground flex-shrink-0"
        >
          {expanded ? "▲" : "▼"}
        </button>
      </div>

      {/* Workload */}
      <div className="px-4 pb-2">
        <div className="flex items-center justify-between mb-1">
          <span className="text-[9px] text-muted-foreground">Workload</span>
          <span className="text-[9px] text-muted-foreground font-mono">{expert.openReviews} open</span>
        </div>
        <WorkloadBar open={expert.openReviews} />
      </div>

      {/* Specializations */}
      <div className="px-4 pb-3 flex flex-wrap gap-1">
        {expert.specializations.slice(0, 4).map(spec => {
          const scfg = SPEC_CONFIG[spec];
          return (
            <span
              key={spec}
              className="text-[9px] font-medium px-1.5 py-0.5 rounded"
              style={{ background: `${scfg.color}15`, color: scfg.color }}
            >
              {scfg.label}
            </span>
          );
        })}
        {expert.specializations.length > 4 && (
          <span className="text-[9px] text-muted-foreground">+{expert.specializations.length - 4}</span>
        )}
      </div>

      {/* Expanded: recent assignment history */}
      {expanded && recentAssignments.length > 0 && (
        <div className="border-t border-border px-4 py-3">
          <p className="text-[10px] font-medium text-foreground mb-2">Recent Assignments</p>
          <div className="space-y-1.5">
            {recentAssignments.map(a => {
              const pcfg = PRIORITY_CONFIG[a.priority];
              return (
                <div key={a.id} className="flex items-center gap-2 text-[10px]">
                  <span
                    className={cn("font-bold px-1 py-0.5 rounded text-[9px]", pcfg.bg)}
                    style={{ color: pcfg.color }}
                  >
                    {pcfg.label}
                  </span>
                  <span className="text-foreground truncate flex-1">{a.projectName}</span>
                  <span className="text-muted-foreground flex-shrink-0">{a.gateLabel}</span>
                  <span className={cn(
                    "flex-shrink-0 text-[9px] font-bold",
                    a.status === "complete" ? "text-[#1A7F4B]" :
                    a.status === "overdue"  ? "text-[#C5191B]" :
                    "text-muted-foreground",
                  )}>
                    {a.status === "complete" ? "✓" : a.status === "overdue" ? "!" : "…"}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Main Component ─────────────────────────────────────────────────────────

export function ExpertAssignmentInterface({
  experts,
  gateLabel,
  projectName,
  applicantCompany,
  currentAssigneeId,
  onAssign,
  onUnassign,
  className,
}: ExpertAssignmentInterfaceProps) {
  const [selectedId,  setSelectedId]  = useState(currentAssigneeId ?? "");
  const [priority,    setPriority]    = useState<AssignmentPriority>("routine");
  const [deadline,    setDeadline]    = useState("");
  const [notes,       setNotes]       = useState("");
  const [specFilter,  setSpecFilter]  = useState<ExpertSpecialization | "all">("all");
  const [submitted,   setSubmitted]   = useState(false);

  const selectedExpert = useMemo(
    () => experts.find(e => e.id === selectedId),
    [experts, selectedId],
  );

  const filteredExperts = useMemo(() => {
    if (specFilter === "all") return experts;
    return experts.filter(e => e.specializations.includes(specFilter));
  }, [experts, specFilter]);

  // Unique specializations across all experts for filter
  const allSpecs = useMemo(() => {
    const set = new Set<ExpertSpecialization>();
    experts.forEach(e => e.specializations.forEach(s => set.add(s)));
    return Array.from(set);
  }, [experts]);

  function hasCOI(expert: Expert): boolean {
    if (!applicantCompany) return false;
    return (expert.conflictCompanies ?? []).some(
      c => c.toLowerCase() === applicantCompany.toLowerCase(),
    );
  }

  function handleAssign() {
    if (!selectedId) return;
    onAssign?.(selectedId, { priority, deadline: deadline || undefined, notes: notes || undefined });
    setSubmitted(true);
  }

  function handleUnassign() {
    if (!currentAssigneeId) return;
    onUnassign?.(currentAssigneeId);
    setSelectedId("");
    setSubmitted(false);
  }

  if (submitted) {
    return (
      <div className={cn("rounded-xl border border-[#1A7F4B]/30 bg-[#1A7F4B]/5 p-6", className)}>
        <div className="flex items-center gap-3">
          <span className="text-[#1A7F4B] text-xl">✓</span>
          <div>
            <p className="text-sm font-bold text-foreground">Assignment Confirmed</p>
            <p className="text-xs text-muted-foreground mt-0.5">
              {selectedExpert?.name} has been assigned to review{" "}
              <span className="font-medium text-foreground">{gateLabel}</span> for{" "}
              <span className="font-medium text-foreground">{projectName}</span>
              {deadline && <> · Due {new Date(deadline).toLocaleDateString()}</>}
            </p>
            <p className="text-[10px] text-muted-foreground mt-1">
              Notification sent to {selectedExpert?.email}
            </p>
          </div>
        </div>
        <button
          onClick={() => setSubmitted(false)}
          className="mt-4 text-[10px] text-[#005EA2] hover:underline font-medium"
        >
          Re-assign
        </button>
      </div>
    );
  }

  return (
    <div className={cn("space-y-4", className)}>
      {/* Header */}
      <div>
        <h2 className="text-sm font-semibold text-foreground">Assign Expert Reviewer</h2>
        <p className="text-xs text-muted-foreground mt-0.5">
          Gate: <span className="font-medium text-foreground">{gateLabel}</span>
          {" · "}Project: <span className="font-medium text-foreground">{projectName}</span>
        </p>
      </div>

      {/* Current assignee banner */}
      {currentAssigneeId && !submitted && (
        <div className="flex items-center gap-3 px-4 py-3 rounded-lg border border-[#005EA2]/30 bg-[#005EA2]/5">
          <span className="text-[#005EA2] text-sm">👤</span>
          <div className="flex-1">
            <p className="text-[11px] font-medium text-foreground">Currently assigned:</p>
            <p className="text-[11px] text-muted-foreground">
              {experts.find(e => e.id === currentAssigneeId)?.name ?? "Unknown"}
            </p>
          </div>
          <button
            onClick={handleUnassign}
            className="text-[10px] text-destructive hover:underline font-medium"
          >
            Unassign
          </button>
        </div>
      )}

      {/* Specialization filter */}
      <div>
        <p className="text-[10px] text-muted-foreground mb-2 font-medium">Filter by specialization</p>
        <div className="flex items-center gap-1.5 flex-wrap">
          <button
            onClick={() => setSpecFilter("all")}
            className={cn(
              "text-[10px] px-2 py-1 rounded-full border font-medium transition-colors",
              specFilter === "all"
                ? "bg-foreground text-background border-foreground"
                : "border-border text-muted-foreground hover:bg-muted",
            )}
          >
            All ({experts.length})
          </button>
          {allSpecs.map(spec => {
            const scfg = SPEC_CONFIG[spec];
            const cnt  = experts.filter(e => e.specializations.includes(spec)).length;
            return (
              <button
                key={spec}
                onClick={() => setSpecFilter(spec)}
                className={cn(
                  "text-[10px] px-2 py-1 rounded-full border font-medium transition-colors",
                  specFilter === spec
                    ? "text-white border-transparent"
                    : "border-border text-muted-foreground hover:bg-muted",
                )}
                style={specFilter === spec ? { background: scfg.color, borderColor: scfg.color } : {}}
              >
                {scfg.label} ({cnt})
              </button>
            );
          })}
        </div>
      </div>

      {/* Expert roster */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {filteredExperts.map(expert => (
          <ExpertCard
            key={expert.id}
            expert={expert}
            selected={selectedId === expert.id}
            hasCOI={hasCOI(expert)}
            onSelect={() => setSelectedId(
              selectedId === expert.id ? "" : expert.id,
            )}
          />
        ))}
        {filteredExperts.length === 0 && (
          <div className="col-span-2 py-6 text-center text-[11px] text-muted-foreground border border-dashed border-border rounded-xl">
            No experts with this specialization.
          </div>
        )}
      </div>

      {/* Assignment options (visible when expert selected) */}
      {selectedId && (
        <div className="rounded-xl border border-border bg-muted/20 p-4 space-y-4">
          <p className="text-[11px] font-bold text-foreground">
            Assignment Options — {selectedExpert?.name}
          </p>

          {/* COI warning */}
          {hasCOI(selectedExpert!) && (
            <div className="flex items-start gap-2.5 px-3 py-2.5 rounded-lg border border-[#C5191B]/30 bg-[#C5191B]/8">
              <span className="text-[#C5191B] text-sm flex-shrink-0">⚑</span>
              <div>
                <p className="text-[10px] font-bold text-[#C5191B]">Conflict of Interest Detected</p>
                <p className="text-[10px] text-muted-foreground">
                  This expert has a conflict with <strong>{applicantCompany}</strong>.
                  Proceeding requires explicit RA Lead approval.
                </p>
              </div>
            </div>
          )}

          {/* Priority */}
          <div>
            <p className="text-[10px] text-muted-foreground mb-2">Review Priority</p>
            <div className="flex gap-2">
              {(["routine", "expedited", "urgent"] as AssignmentPriority[]).map(p => {
                const pcfg = PRIORITY_CONFIG[p];
                return (
                  <button
                    key={p}
                    onClick={() => setPriority(p)}
                    className={cn(
                      "flex-1 text-[10px] py-1.5 rounded-lg border font-bold transition-colors",
                      priority === p
                        ? `text-white border-transparent`
                        : "border-border text-muted-foreground hover:bg-muted",
                    )}
                    style={priority === p ? { background: pcfg.color, borderColor: pcfg.color } : {}}
                  >
                    {pcfg.label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Deadline */}
          <div>
            <label className="text-[10px] text-muted-foreground block mb-1.5">
              Review deadline (optional)
            </label>
            <input
              type="date"
              value={deadline}
              onChange={e => setDeadline(e.target.value)}
              min={new Date().toISOString().split("T")[0]}
              className="w-full px-3 py-1.5 text-[11px] rounded-lg border border-border bg-background outline-none focus:border-[#005EA2]/50 text-foreground"
            />
          </div>

          {/* Notes */}
          <div>
            <label className="text-[10px] text-muted-foreground block mb-1.5">
              Notes to reviewer
            </label>
            <textarea
              value={notes}
              onChange={e => setNotes(e.target.value)}
              rows={2}
              placeholder="e.g. Please focus on the SE table in Section 5 and the software classification…"
              className="w-full px-3 py-2 text-[11px] rounded-lg border border-border bg-background outline-none focus:border-[#005EA2]/50 resize-none text-foreground placeholder:text-muted-foreground"
            />
          </div>

          {/* Submit */}
          <button
            onClick={handleAssign}
            disabled={selectedExpert?.availability === "ooo"}
            className={cn(
              "w-full py-2.5 text-[11px] font-bold rounded-lg border transition-colors",
              selectedExpert?.availability === "ooo"
                ? "border-border text-muted-foreground bg-muted/40 cursor-not-allowed"
                : "bg-[#005EA2] border-[#005EA2] text-white hover:bg-[#005EA2]/90",
            )}
          >
            {selectedExpert?.availability === "ooo"
              ? "Expert Unavailable"
              : `Assign to ${selectedExpert?.name} · 21 CFR Part 11 log`}
          </button>
        </div>
      )}
    </div>
  );
}
