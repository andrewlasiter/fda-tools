"use client";

/**
 * FDA-275 [HITL-001] — HitlGateDecision
 * ========================================
 * Formal human-in-the-loop decision checkpoint component.
 * Used at the 5 mandatory HITL gates throughout the 12-stage NPD pipeline.
 *
 * UX Design Principle: This must feel SIGNIFICANT — regulatory professionals
 * are making legally accountable decisions. The UI communicates weight through
 * visual hierarchy, required rationale, digital signature confirmation, and
 * 21 CFR Part 11 audit trail integration.
 *
 * Decision options:
 *   Approve           — Stage cleared to advance
 *   Request Changes   — Return to agent with specific feedback
 *   Reject            — Stage blocked, escalate to RA Lead
 *   Defer             — Pause for external dependency (FDA response, lab results)
 */

import React, { useState } from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { TrustData } from "@/components/trust/trust-badge";

// ── Types ─────────────────────────────────────────────────────────────────

export type HitlDecision = "approve" | "request_changes" | "reject" | "defer";

export interface GateContext {
  gateName:       string;       // e.g. "Testing Completeness Gate"
  stageLabel:     string;       // e.g. "TESTING → DRAFTING"
  gateIdx:        number;       // 1–5
  requiredRole:   string;       // e.g. "RA Lead", "Clinical Expert"
  sri:            number;       // SRI at decision time
  agentSummary:   string;       // AI-generated summary of what's ready
  openGaps:       string[];     // Unresolved issues flagged by agents
  completionPct:  number;       // Stage completion %
  trust?:         TrustData;    // AI confidence in readiness assessment
  deadline?:      string;       // ISO date
}

export interface HitlDecisionRecord {
  decision:      HitlDecision;
  rationale:     string;
  reviewerName:  string;
  reviewerRole:  string;
  timestamp:     string;
  gateName:      string;
  sri:           number;
}

interface HitlGateDecisionProps {
  gate:        GateContext;
  onSubmit:    (record: HitlDecisionRecord) => Promise<void>;
  onCancel?:   () => void;
  className?:  string;
}

// ── Decision config ───────────────────────────────────────────────────────

const DECISION_CONFIG: Record<HitlDecision, {
  label:        string;
  description:  string;
  color:        string;
  border:       string;
  bg:           string;
  icon:         string;
  minChars:     number;
}> = {
  approve: {
    label:       "Approve",
    description: "Stage is complete and meets all regulatory requirements. Advance pipeline.",
    color:       "text-[#1A7F4B]",
    border:      "border-[#1A7F4B]",
    bg:          "bg-[#1A7F4B]/5",
    icon:        "✓",
    minChars:    25,
  },
  request_changes: {
    label:       "Request Changes",
    description: "Agent output requires revision. Specify what must be corrected before re-review.",
    color:       "text-[#B45309]",
    border:      "border-[#B45309]",
    bg:          "bg-[#B45309]/5",
    icon:        "↩",
    minChars:    50,
  },
  reject: {
    label:       "Reject",
    description: "Stage cannot proceed. Escalate to RA Lead and block advancement.",
    color:       "text-destructive",
    border:      "border-destructive",
    bg:          "bg-destructive/5",
    icon:        "✕",
    minChars:    75,
  },
  defer: {
    label:       "Defer",
    description: "Pending external dependency (FDA response, lab results, legal review). Set resume date.",
    color:       "text-[#005EA2]",
    border:      "border-[#005EA2]",
    bg:          "bg-[#005EA2]/5",
    icon:        "⏸",
    minChars:    25,
  },
};

// ── SRI ring (compact) ────────────────────────────────────────────────────

function SriRing({ score }: { score: number }) {
  const r = 24; const c = 2 * Math.PI * r;
  const offset = c - (score / 100) * c;
  const color = score >= 70 ? "#1A7F4B" : score >= 50 ? "#B45309" : "#C5191B";
  return (
    <div className="flex flex-col items-center gap-0.5">
      <svg width="60" height="60" viewBox="0 0 60 60">
        <circle cx="30" cy="30" r={r} fill="none" stroke="hsl(var(--border))" strokeWidth="5" />
        <circle
          cx="30" cy="30" r={r} fill="none"
          stroke={color} strokeWidth="5"
          strokeDasharray={c} strokeDashoffset={offset}
          strokeLinecap="round" transform="rotate(-90 30 30)"
        />
        <text x="30" y="34" textAnchor="middle" fontSize="14" fontWeight="800" fill={color} fontFamily="var(--font-heading)">
          {score}
        </text>
      </svg>
      <p className="text-[9px] text-muted-foreground uppercase tracking-wide">SRI</p>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────

export function HitlGateDecision({ gate, onSubmit, onCancel, className }: HitlGateDecisionProps) {
  const [decision, setDecision] = useState<HitlDecision | null>(null);
  const [rationale, setRationale] = useState("");
  const [reviewerName, setReviewerName] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const cfg = decision ? DECISION_CONFIG[decision] : null;
  const rationale_ok = rationale.trim().length >= (cfg?.minChars ?? 25);
  const name_ok = reviewerName.trim().length >= 2;
  const can_submit = decision !== null && rationale_ok && name_ok && confirmed;

  async function handleSubmit() {
    if (!can_submit || !decision) return;
    setSubmitting(true);
    setError(null);
    try {
      const record: HitlDecisionRecord = {
        decision,
        rationale: rationale.trim(),
        reviewerName: reviewerName.trim(),
        reviewerRole: gate.requiredRole,
        timestamp: new Date().toISOString(),
        gateName: gate.gateName,
        sri: gate.sri,
      };
      await onSubmit(record);
      setSubmitted(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Submission failed. Please retry.");
    } finally {
      setSubmitting(false);
    }
  }

  if (submitted && decision) {
    const cfg = DECISION_CONFIG[decision];
    return (
      <Card className={cn("border-2", cfg.border, className)}>
        <CardContent className="pt-8 pb-8 text-center space-y-3">
          <div className={cn("w-12 h-12 rounded-full flex items-center justify-center text-2xl mx-auto", cfg.bg, "border-2", cfg.border)}>
            {cfg.icon}
          </div>
          <h3 className={cn("text-lg font-bold font-heading", cfg.color)}>{cfg.label} Recorded</h3>
          <p className="text-sm text-muted-foreground">
            Decision logged to 21 CFR Part 11 audit trail · {new Date().toLocaleString()}
          </p>
          <Badge variant="outline" className="text-xs">{gate.gateName}</Badge>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={cn("border-2 border-border", className)}>
      <CardHeader className="pb-4">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              {/* Gate number badge */}
              <div className="w-6 h-6 rounded-full bg-[#005EA2] flex items-center justify-center">
                <span className="text-[10px] font-bold text-white">{gate.gateIdx}</span>
              </div>
              <Badge variant="secondary" className="text-[10px]">HITL Gate · {gate.requiredRole}</Badge>
            </div>
            <CardTitle className="text-base font-bold">{gate.gateName}</CardTitle>
            <p className="text-xs text-muted-foreground mt-0.5">Stage transition: <span className="font-mono font-medium">{gate.stageLabel}</span></p>
          </div>
          <SriRing score={gate.sri} />
        </div>

        {/* Deadline warning */}
        {gate.deadline && (
          <div className="flex items-center gap-2 mt-3 px-3 py-2 rounded-lg bg-[#B45309]/10 border border-[#B45309]/25">
            <span className="text-[#B45309] text-sm">⚠</span>
            <p className="text-xs text-[#B45309] font-medium">
              Decision required by {new Date(gate.deadline).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
            </p>
          </div>
        )}
      </CardHeader>

      <CardContent className="space-y-6">
        {/* AI Summary */}
        <div className="rounded-lg bg-[#005EA2]/5 border border-[#005EA2]/15 p-4 space-y-3">
          <p className="text-[10px] font-bold uppercase tracking-wider text-[#005EA2]">AI Readiness Assessment</p>
          <p className="text-sm text-foreground leading-relaxed">{gate.agentSummary}</p>

          {/* Open gaps */}
          {gate.openGaps.length > 0 && (
            <div>
              <p className="text-[10px] font-bold text-muted-foreground mb-1.5">Open Gaps ({gate.openGaps.length})</p>
              <ul className="space-y-1">
                {gate.openGaps.map((gap, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-foreground">
                    <span className="text-[#B45309] font-bold mt-0.5">!</span>
                    {gap}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Progress bar */}
          <div>
            <div className="flex justify-between text-[10px] text-muted-foreground mb-1">
              <span>Stage completion</span>
              <span className="font-medium">{gate.completionPct}%</span>
            </div>
            <div className="h-1.5 bg-muted rounded-full overflow-hidden">
              <div
                className="h-full bg-[#005EA2] rounded-full"
                style={{ width: `${gate.completionPct}%` }}
              />
            </div>
          </div>
        </div>

        {/* ── Decision selection ── */}
        <div>
          <p className="text-xs font-semibold text-foreground mb-3">Your Decision <span className="text-destructive">*</span></p>
          <div className="grid grid-cols-2 gap-2">
            {(Object.entries(DECISION_CONFIG) as [HitlDecision, typeof DECISION_CONFIG[HitlDecision]][]).map(([key, d]) => (
              <button
                key={key}
                onClick={() => setDecision(key)}
                className={cn(
                  "flex items-start gap-2.5 p-3 rounded-lg border-2 text-left transition-all",
                  "hover:shadow-sm",
                  decision === key
                    ? cn(d.border, d.bg, "shadow-sm")
                    : "border-border hover:border-muted-foreground"
                )}
              >
                <span className={cn("text-lg mt-0.5 leading-none", decision === key ? d.color : "text-muted-foreground")}>
                  {d.icon}
                </span>
                <div>
                  <p className={cn("text-xs font-bold", decision === key ? d.color : "text-foreground")}>{d.label}</p>
                  <p className="text-[10px] text-muted-foreground leading-relaxed mt-0.5">{d.description}</p>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* ── Rationale ── */}
        <div>
          <label className="text-xs font-semibold text-foreground">
            Rationale <span className="text-destructive">*</span>
            {cfg && (
              <span className="font-normal text-muted-foreground ml-1">
                (min {cfg.minChars} chars — {Math.max(0, cfg.minChars - rationale.trim().length)} remaining)
              </span>
            )}
          </label>
          <textarea
            value={rationale}
            onChange={e => setRationale(e.target.value)}
            placeholder={
              decision === "approve"           ? "Briefly confirm all requirements are met and evidence reviewed..." :
              decision === "request_changes"   ? "Specify exactly what must be corrected, including section and expected value..." :
              decision === "reject"            ? "State the regulatory concern and escalation path..." :
              decision === "defer"             ? "State the dependency and expected resolution date..." :
              "Select a decision above, then enter your rationale..."
            }
            rows={4}
            className={cn(
              "mt-1.5 w-full px-3 py-2.5 text-sm rounded-lg border resize-none",
              "bg-background placeholder:text-muted-foreground",
              "focus:outline-none focus:ring-2 focus:ring-[#005EA2] transition-all",
              rationale.trim().length > 0 && !rationale_ok ? "border-[#B45309]" : "border-border"
            )}
          />
          {/* Character counter */}
          <div className="flex justify-end mt-0.5">
            <span className={cn(
              "text-[10px]",
              rationale_ok ? "text-[#1A7F4B]" : "text-muted-foreground"
            )}>
              {rationale.trim().length} chars
            </span>
          </div>
        </div>

        {/* ── Reviewer digital signature ── */}
        <div>
          <label className="text-xs font-semibold text-foreground">
            Reviewer Name (Digital Signature) <span className="text-destructive">*</span>
          </label>
          <input
            type="text"
            value={reviewerName}
            onChange={e => setReviewerName(e.target.value)}
            placeholder="Full name as it appears in your credentials..."
            className={cn(
              "mt-1.5 w-full px-3 py-2 text-sm rounded-lg border bg-background",
              "placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-[#005EA2] transition-all",
              "border-border"
            )}
          />
          <p className="text-[10px] text-muted-foreground mt-1">
            Role: <span className="font-medium">{gate.requiredRole}</span> ·
            Timestamp: <span className="font-mono">{new Date().toISOString().replace("T", " ").slice(0, 19)} UTC</span>
          </p>
        </div>

        {/* ── Confirmation checkbox ── */}
        <label className={cn(
          "flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-all",
          confirmed ? "border-[#1A7F4B] bg-[#1A7F4B]/5" : "border-border hover:border-muted-foreground"
        )}>
          <input
            type="checkbox"
            checked={confirmed}
            onChange={e => setConfirmed(e.target.checked)}
            className="mt-0.5 w-4 h-4 accent-[#1A7F4B]"
          />
          <div>
            <p className="text-xs font-semibold text-foreground">
              I confirm I have reviewed all supporting materials and this decision is my own.
            </p>
            <p className="text-[10px] text-muted-foreground mt-0.5">
              This decision will be recorded in the 21 CFR Part 11 compliant audit trail and cannot be deleted.
            </p>
          </div>
        </label>

        {/* ── Error ── */}
        {error && (
          <div className="px-4 py-3 rounded-lg bg-destructive/10 border border-destructive/25 text-sm text-destructive">
            {error}
          </div>
        )}

        {/* ── Actions ── */}
        <div className="flex gap-3 pt-1">
          {onCancel && (
            <Button
              variant="outline"
              onClick={onCancel}
              disabled={submitting}
              className="flex-1"
            >
              Cancel
            </Button>
          )}
          <Button
            onClick={handleSubmit}
            disabled={!can_submit || submitting}
            className={cn(
              "flex-[2] font-semibold transition-all",
              decision && can_submit
                ? cn("text-white", {
                    approve:         "bg-[#1A7F4B] hover:bg-[#145F39]",
                    request_changes: "bg-[#B45309] hover:bg-[#8A3F07]",
                    reject:          "bg-destructive hover:bg-destructive/80",
                    defer:           "bg-[#005EA2] hover:bg-[#003E73]",
                  }[decision])
                : ""
            )}
          >
            {submitting ? (
              <span className="flex items-center gap-2">
                <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                  <path d="M12 3v3M12 18v3M3 12h3M18 12h3" strokeLinecap="round" />
                </svg>
                Recording decision...
              </span>
            ) : (
              decision ? `Submit: ${DECISION_CONFIG[decision].label}` : "Select a decision"
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
