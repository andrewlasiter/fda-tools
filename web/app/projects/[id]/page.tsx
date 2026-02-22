"use client";

/**
 * FDA-293 [NPD-UI-001] — /projects/[id] page
 * ============================================
 * NPD Workspace: 12-stage pipeline navigator + stage content panel.
 *
 * Stages: CONCEPT → CLASSIFY → PREDICATE → PATHWAY → PRESUB → TESTING
 *         → DRAFTING → REVIEW → SUBMIT → FDA_REVIEW → CLEARED → POST_MARKET
 *
 * Layout:
 *   Left sidebar (240px): numbered stage list with status icons
 *   Main panel: stage-specific content (auto-generated or in-progress docs)
 *   Right drawer (collapsible, 280px): AI assistant stub
 *   Header: project name, wizard/power mode toggle, save status
 */

import React, { useState } from "react";
import { cn } from "@/lib/utils";

// ── Types ──────────────────────────────────────────────────────────────────

type StageId =
  | "CONCEPT" | "CLASSIFY" | "PREDICATE" | "PATHWAY" | "PRESUB"
  | "TESTING" | "DRAFTING" | "REVIEW" | "SUBMIT"
  | "FDA_REVIEW" | "CLEARED" | "POST_MARKET";

type StageStatus = "not_started" | "in_progress" | "complete" | "blocked";

interface Stage {
  id:          StageId;
  label:       string;
  shortLabel:  string;
  description: string;
  status:      StageStatus;
  gateRequired?: boolean;   // HITL gate required before advancing
}

type ViewMode = "wizard" | "power";

// ── Stage definitions ───────────────────────────────────────────────────────

const STAGES: Stage[] = [
  { id: "CONCEPT",     label: "Concept",             shortLabel: "Concept",    description: "Define device concept, intended use, user needs, and indication for use.",                             status: "complete"     },
  { id: "CLASSIFY",    label: "Classify",            shortLabel: "Classify",   description: "Determine device classification (Class I/II/III), product code, and applicable 21 CFR part.",         status: "complete"     },
  { id: "PREDICATE",   label: "Predicate Search",    shortLabel: "Predicate",  description: "Identify substantially equivalent predicate devices using cosine similarity search.",                  status: "complete",  gateRequired: true },
  { id: "PATHWAY",     label: "Regulatory Pathway",  shortLabel: "Pathway",    description: "Select submission type: 510(k), De Novo, PMA, or Exempt. Determine pre-Sub need.",                  status: "complete"     },
  { id: "PRESUB",      label: "Pre-Submission",      shortLabel: "Pre-Sub",    description: "Prepare and submit Q-Sub if needed. Capture FDA feedback for high-risk design questions.",            status: "in_progress", gateRequired: true },
  { id: "TESTING",     label: "Testing & Validation",shortLabel: "Testing",    description: "Execute bench, animal, and/or clinical testing per applicable standards. Compile test reports.",     status: "not_started"  },
  { id: "DRAFTING",    label: "Submission Drafting", shortLabel: "Drafting",   description: "Draft all 510(k) sections in Document Studio. AI agents assist with SE discussion and labeling.",   status: "not_started", gateRequired: true },
  { id: "REVIEW",      label: "Internal Review",     shortLabel: "Review",     description: "Expert HITL gate: RA lead reviews all sections before lock. Consistency checker runs.",              status: "not_started", gateRequired: true },
  { id: "SUBMIT",      label: "Submit to FDA",        shortLabel: "Submit",     description: "Export eSTAR XML, pay MDUFA fee, submit via CDRH Portal. Track submission receipt.",                status: "not_started"  },
  { id: "FDA_REVIEW",  label: "FDA Review",          shortLabel: "FDA Review", description: "FDA conducts 510(k) review. Respond to Additional Information (AI) requests within 180 days.",       status: "not_started"  },
  { id: "CLEARED",     label: "Cleared",             shortLabel: "Cleared",    description: "510(k) clearance received. Update labeling if conditioned. Notify EU/notified body if needed.",     status: "not_started"  },
  { id: "POST_MARKET", label: "Post-Market",         shortLabel: "Post-Mkt",  description: "MDR/MDV reporting, complaint handling, PMS surveillance, annual reports, 522 studies if required.",  status: "not_started"  },
];

// ── Status config ────────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<StageStatus, { icon: string; color: string; bg: string }> = {
  complete:    { icon: "✓", color: "#1A7F4B", bg: "bg-[#1A7F4B]/10" },
  in_progress: { icon: "●", color: "#005EA2", bg: "bg-[#005EA2]/10" },
  blocked:     { icon: "✕", color: "#C5191B", bg: "bg-[#C5191B]/10" },
  not_started: { icon: "○", color: "#94A3B8", bg: "bg-transparent"  },
};

// ── Stage content panel ─────────────────────────────────────────────────────

function StageContent({ stage, mode }: { stage: Stage; mode: ViewMode }) {
  const scfg = STATUS_CONFIG[stage.status];
  return (
    <div className="p-6 space-y-6">
      {/* Stage header */}
      <div className="flex items-start gap-3">
        <div className={cn("w-8 h-8 rounded-lg flex items-center justify-center text-sm font-bold flex-shrink-0", scfg.bg)}
          style={{ color: scfg.color }}>
          {scfg.icon}
        </div>
        <div>
          <h2 className="text-base font-bold text-foreground">{stage.label}</h2>
          <p className="text-[11px] text-muted-foreground mt-0.5">{stage.description}</p>
        </div>
      </div>

      {/* Wizard mode: step-by-step card */}
      {mode === "wizard" && (
        <div className="rounded-xl border border-[#005EA2]/20 bg-[#005EA2]/3 p-4">
          <p className="text-[11px] font-semibold text-[#005EA2] mb-2">Guided mode — next actions</p>
          <ol className="list-decimal list-inside space-y-1.5 text-[11px] text-foreground">
            {stage.id === "CONCEPT"    && <><li>Define intended use statement (IUS)</li><li>Identify target users and use environment</li><li>Capture initial device description</li></>}
            {stage.id === "CLASSIFY"   && <><li>Run product code lookup (use Research Hub)</li><li>Confirm device class with 21 CFR part</li><li>Determine exempt status</li></>}
            {stage.id === "PREDICATE"  && <><li>Search predicate database (similarity ≥ 80)</li><li>Validate predicate chain (no TOXIC health status)</li><li>Select 1–3 predicates for SE comparison</li></>}
            {stage.id === "PATHWAY"    && <><li>Confirm 510(k) pathway based on predicate</li><li>Assess De Novo/PMA risk if Class III</li><li>Schedule pre-Sub Q-Sub if needed</li></>}
            {stage.id === "PRESUB"     && <><li>Draft Q-Sub cover letter and questions</li><li>Submit via CDRH Electronic Submissions Gateway</li><li>Await FDA feedback (target 60 days)</li></>}
            {stage.id === "TESTING"    && <><li>Execute test plan per applicable standards</li><li>Collect test reports and CoA documents</li><li>Upload to project vault</li></>}
            {stage.id === "DRAFTING"   && <><li>Open Document Studio for this project</li><li>Complete all required eSTAR sections</li><li>Run consistency checker before lock</li></>}
            {stage.id === "REVIEW"     && <><li>Assign RA lead review in HITL interface</li><li>Address all reviewer comments</li><li>Obtain electronic signature (21 CFR Part 11)</li></>}
            {stage.id === "SUBMIT"     && <><li>Export finalized eSTAR XML</li><li>Pay MDUFA user fee</li><li>Submit via eCopy or eSTAR portal</li></>}
            {stage.id === "FDA_REVIEW" && <><li>Monitor for Acknowledgement Letter</li><li>Respond to AI requests within 180 days</li><li>Track review clock (90/180-day)</li></>}
            {stage.id === "CLEARED"    && <><li>Archive Decision Letter and Special Controls</li><li>Update labeling if conditioned</li><li>Initiate PMS plan</li></>}
            {stage.id === "POST_MARKET"&& <><li>File MDRs within mandatory timeframes</li><li>Run signal detection on MAUDE monthly</li><li>Submit annual reports as required</li></>}
          </ol>
        </div>
      )}

      {/* Power mode: raw data / agent outputs */}
      {mode === "power" && (
        <div className="space-y-3">
          <div className="rounded-lg border border-border bg-muted/30 p-4">
            <p className="text-[10px] font-mono text-muted-foreground mb-2">// Stage data — agent outputs</p>
            <div className="text-[11px] font-mono text-foreground space-y-1">
              <p><span className="text-[#005EA2]">stage:</span> {stage.id}</p>
              <p><span className="text-[#005EA2]">status:</span> {stage.status}</p>
              <p><span className="text-[#005EA2]">gate_required:</span> {stage.gateRequired ? "true" : "false"}</p>
              <p><span className="text-muted-foreground">// connect to FastAPI /projects/:id/stages/:stage</span></p>
            </div>
          </div>

          {/* Quick links */}
          <div className="flex gap-2 flex-wrap">
            {stage.id === "PREDICATE" && (
              <a href="/research" className="text-[10px] px-3 py-1.5 border border-[#005EA2]/30 rounded-lg text-[#005EA2] hover:bg-[#005EA2]/10 transition-colors cursor-pointer">
                Open Research Hub →
              </a>
            )}
            {stage.id === "DRAFTING" && (
              <a href="/documents/new" className="text-[10px] px-3 py-1.5 border border-[#005EA2]/30 rounded-lg text-[#005EA2] hover:bg-[#005EA2]/10 transition-colors cursor-pointer">
                Open Document Studio →
              </a>
            )}
            {stage.id === "REVIEW" && (
              <button className="text-[10px] px-3 py-1.5 border border-[#005EA2]/30 rounded-lg text-[#005EA2] hover:bg-[#005EA2]/10 transition-colors cursor-pointer">
                Assign Expert Review →
              </button>
            )}
          </div>
        </div>
      )}

      {/* HITL gate banner */}
      {stage.gateRequired && stage.status === "in_progress" && (
        <div className="rounded-xl border border-[#B45309]/30 bg-[#B45309]/5 p-4 flex items-start gap-2">
          <div className="w-1.5 h-1.5 rounded-full bg-[#B45309] flex-shrink-0 mt-1.5" />
          <div>
            <p className="text-[11px] font-semibold text-[#B45309]">HITL Gate Required</p>
            <p className="text-[10px] text-muted-foreground mt-0.5">
              A qualified RA expert must review and approve before advancing to the next stage.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

// ── AI assistant stub ────────────────────────────────────────────────────────

function AiAssistant({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [msg, setMsg] = useState("");
  if (!open) return null;
  return (
    <div className="w-72 border-l border-border flex flex-col h-full bg-card shrink-0">
      <div className="flex items-center justify-between px-4 py-3 border-b border-border">
        <div>
          <p className="text-[11px] font-semibold text-foreground">AI Assistant</p>
          <p className="text-[9px] text-muted-foreground">Context: current project + stage</p>
        </div>
        <button onClick={onClose} className="text-muted-foreground hover:text-foreground text-[14px] cursor-pointer" aria-label="Close AI assistant">✕</button>
      </div>
      <div className="flex-1 overflow-y-auto p-4 flex items-center justify-center">
        <div className="text-center">
          <p className="text-[30px] mb-2 opacity-20">⎆</p>
          <p className="text-[11px] text-muted-foreground">Ask about this stage, regulatory requirements, or request agent actions.</p>
        </div>
      </div>
      <div className="p-3 border-t border-border">
        <div className="flex gap-2">
          <input
            type="text"
            value={msg}
            onChange={e => setMsg(e.target.value)}
            placeholder="Ask anything…"
            className="flex-1 text-[11px] px-2.5 py-2 rounded-lg border border-border bg-background outline-none focus:border-[#005EA2]/50 text-foreground placeholder:text-muted-foreground"
          />
          <button
            disabled={!msg.trim()}
            className="px-3 py-2 bg-[#005EA2] text-white text-[11px] rounded-lg disabled:opacity-40 cursor-pointer disabled:cursor-not-allowed"
          >
            →
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function ProjectWorkspacePage({
  params,
}: {
  params: { id: string };
}) {
  const [activeStage, setActiveStage] = useState<StageId>("PRESUB");
  const [viewMode,    setViewMode]    = useState<ViewMode>("wizard");
  const [aiOpen,      setAiOpen]      = useState(true);

  const currentStage = STAGES.find(s => s.id === activeStage) ?? STAGES[4];

  return (
    <div className="flex h-[calc(100vh-64px)] bg-background">
      {/* Left sidebar: 12-stage navigator */}
      <nav
        aria-label="NPD pipeline stages"
        className="w-[220px] border-r border-border flex flex-col shrink-0 overflow-y-auto"
      >
        <div className="px-3 py-3 border-b border-border">
          <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">NPD Pipeline</p>
          <p className="text-[9px] text-muted-foreground mt-0.5">{params.id}</p>
        </div>
        <div className="flex-1 py-2">
          {STAGES.map((stage, i) => {
            const scfg = STATUS_CONFIG[stage.status];
            const isActive = stage.id === activeStage;
            return (
              <button
                key={stage.id}
                onClick={() => setActiveStage(stage.id)}
                className={cn(
                  "w-full text-left flex items-center gap-2.5 px-3 py-2 transition-colors cursor-pointer",
                  isActive
                    ? "bg-[#005EA2]/8 border-r-2 border-[#005EA2]"
                    : "hover:bg-muted/50 border-r-2 border-transparent",
                )}
              >
                <span
                  className="text-[10px] font-bold w-4 text-center flex-shrink-0"
                  style={{ color: scfg.color }}
                >
                  {scfg.icon}
                </span>
                <div className="flex-1 min-w-0">
                  <p className={cn("text-[11px] font-medium truncate", isActive ? "text-[#005EA2]" : "text-foreground")}>
                    {stage.shortLabel}
                  </p>
                </div>
                <span className="text-[9px] text-muted-foreground flex-shrink-0">{i + 1}</span>
              </button>
            );
          })}
        </div>
      </nav>

      {/* Main panel */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Toolbar */}
        <div className="flex items-center justify-between px-4 py-2.5 border-b border-border bg-background/80 backdrop-blur-sm shrink-0">
          <div className="flex items-center gap-3">
            <div className="flex rounded-lg border border-border overflow-hidden">
              {(["wizard", "power"] as const).map(m => (
                <button
                  key={m}
                  onClick={() => setViewMode(m)}
                  className={cn(
                    "text-[10px] px-3 py-1.5 font-medium transition-colors cursor-pointer capitalize",
                    viewMode === m
                      ? "bg-[#005EA2] text-white"
                      : "text-muted-foreground hover:bg-muted",
                  )}
                >
                  {m}
                </button>
              ))}
            </div>
            <span className="text-[10px] text-muted-foreground">Stage {STAGES.findIndex(s => s.id === activeStage) + 1} of {STAGES.length}</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setAiOpen(v => !v)}
              className={cn(
                "text-[10px] px-3 py-1.5 border rounded-lg font-medium transition-colors cursor-pointer",
                aiOpen
                  ? "bg-[#005EA2]/10 border-[#005EA2]/30 text-[#005EA2]"
                  : "border-border text-muted-foreground hover:bg-muted",
              )}
            >
              {aiOpen ? "Hide" : "Show"} AI
            </button>
          </div>
        </div>

        {/* Stage content (scrollable) */}
        <div className="flex-1 overflow-y-auto">
          <StageContent stage={currentStage} mode={viewMode} />
        </div>
      </div>

      {/* Right: AI assistant */}
      <AiAssistant open={aiOpen} onClose={() => setAiOpen(false)} />
    </div>
  );
}
