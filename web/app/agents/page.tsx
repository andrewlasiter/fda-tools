"use client";

/**
 * FDA-296 [AGENTS-UI-001] — /agents page
 * ========================================
 * Agent Orchestration Mission Control: wires all 4 AI panel components.
 *
 * Layout:
 *   Header: stats row (running / queued / errors / avg latency)
 *   Main (2/3 width): AgenticControlPanel — live agent grid
 *   Right sidebar (1/3 width): RateLimitPanel + AgentErrorRecovery
 *   Bottom drawer (collapsible): AgentDiffViewer — show diffs from last run
 */

import React, { useState } from "react";
import { cn } from "@/lib/utils";
import { AgenticControlPanel, type ActionType, type AgentState } from "@/components/ai/agentic-control-panel";
import { AgentDiffViewer, type DiffChunk }   from "@/components/ai/agent-diff-viewer";
import { RateLimitPanel, type ModelUsage, type AgentCost } from "@/components/ai/rate-limit-panel";
import { AgentErrorRecovery, type AgentError } from "@/components/ai/agent-error-recovery";

// ── Demo data ─────────────────────────────────────────────────────────────────

const DEMO_ACTIONS: ActionType[] = [
  { id: "predicate-search", label: "Predicate Search",  category: "search",     riskLevel: "low",      tier: "full_auto",  description: "cosine search 510(k) DB" },
  { id: "guidance-fetch",   label: "Guidance Fetch",    category: "data_access", riskLevel: "low",     tier: "full_auto",  description: "download FDA guidance PDFs" },
  { id: "se-analysis",      label: "SE Analysis",       category: "analysis",   riskLevel: "medium",   tier: "approval",   description: "substantial equivalence claim" },
  { id: "draft-section",    label: "Draft Section",     category: "drafting",   riskLevel: "medium",   tier: "approval",   description: "AI-drafted eSTAR section" },
  { id: "submit-to-fda",    label: "Submit to FDA",     category: "submission", riskLevel: "critical", tier: "human_only", description: "eSTAR electronic submission" },
];

const DEMO_AGENTS: AgentState[] = [
  { id: "a1", name: "fda-predicate-agent", status: "running",          currentTask: "Scanning K231045 for SE comparison",   confidenceScore: 91, lastActivity: new Date().toISOString() },
  { id: "a2", name: "fda-drafting-agent",  status: "waiting_approval", currentTask: "Drafted Device Description §3",        confidenceScore: 88, lastActivity: new Date().toISOString() },
  { id: "a3", name: "fda-se-agent",        status: "idle",             currentTask: "Queued: SE Discussion §2.1",           confidenceScore: 74 },
  { id: "a4", name: "fda-guidance-agent",  status: "running",          currentTask: "Fetching infusion pump guidance PDFs", confidenceScore: 95, lastActivity: new Date().toISOString() },
  { id: "a5", name: "fda-quality-expert",  status: "error",            currentTask: "Risk assessment — rate limit hit",     confidenceScore: 0,  lastActivity: new Date(Date.now() - 90000).toISOString() },
];

const DEMO_MODELS: ModelUsage[] = [
  { model: "opus",   requestsUsed: 18,  requestsLimit: 50,   inputTokens: 18000, outputTokens: 6000, limitTokens: 200000, costUsd: 1.26, history: [10, 14, 18, 22, 18, 20, 24, 28, 22, 20, 26, 36] },
  { model: "sonnet", requestsUsed: 143, requestsLimit: 500,  inputTokens: 140000, outputTokens: 46000, limitTokens: 2000000, costUsd: 3.12, history: [20, 24, 30, 28, 22, 35, 40, 45, 38, 42, 48, 52] },
  { model: "haiku",  requestsUsed: 841, requestsLimit: 2000, inputTokens: 980000, outputTokens: 260000, limitTokens: 10000000, costUsd: 0.94, history: [30, 35, 40, 42, 38, 50, 55, 48, 52, 58, 62, 68] },
];

const DEMO_AGENT_COSTS: AgentCost[] = [
  { agentName: "fda-predicate-agent", model: "sonnet", tokens: 10500, costUsd: 0.16, runs: 3 },
  { agentName: "fda-drafting-agent",  model: "opus",   tokens: 18000, costUsd: 0.63, runs: 1 },
  { agentName: "fda-guidance-agent",  model: "haiku",  tokens: 24800, costUsd: 0.02, runs: 5 },
];

const DEMO_ERROR: AgentError = {
  id:        "e1",
  agentName: "fda-quality-expert",
  category:  "rate_limit",
  message:   "Anthropic API rate limit exceeded (requests/minute). Retry in 60s.",
  timestamp: new Date(Date.now() - 90000).toISOString(),
  attempt:   1,
  maxAttempts: 3,
};

const DEMO_CHUNKS: DiffChunk[] = [
  {
    id: "ch1",
    header: "@@ -1,2 +1,2 @@",
    lines: [
      { type: "context", content: "The subject device is a pump.", oldLineNo: 1, newLineNo: 1 },
      { type: "removed", content: "Intended for use in clinical settings.",  oldLineNo: 2 },
      { type: "added",   content: "Intended for short-term (≤ 7 days) continuous IV infusion in adult acute care patients.", newLineNo: 2 },
    ],
    accepted: null,
  },
];

// ── Stat card ────────────────────────────────────────────────────────────────

function StatCard({ label, value, color = "text-foreground", pulse = false }: {
  label: string; value: string | number; color?: string; pulse?: boolean;
}) {
  return (
    <div className="flex items-center gap-3 bg-card border border-border rounded-xl px-4 py-3 flex-1">
      {pulse && (
        <div className="relative flex-shrink-0">
          <div className="w-2 h-2 rounded-full bg-[#005EA2]" />
          <div className="absolute inset-0 rounded-full bg-[#005EA2] animate-ping opacity-30" />
        </div>
      )}
      <div>
        <p className={cn("text-xl font-bold font-mono", color)}>{value}</p>
        <p className="text-[10px] text-muted-foreground">{label}</p>
      </div>
    </div>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function AgentsPage() {
  const [diffOpen, setDiffOpen] = useState(false);

  return (
    <main className="flex flex-col h-[calc(100vh-64px)] bg-background overflow-hidden" aria-label="Agent Orchestration">
      {/* Page header */}
      <header className="px-5 py-4 border-b border-border shrink-0">
        <div className="flex items-center justify-between gap-4 mb-3">
          <div>
            <h1 className="text-[15px] font-bold text-foreground">Agent Orchestration</h1>
            <p className="text-[10px] text-muted-foreground mt-0.5">
              Mission control — 167 agents across 12 categories
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setDiffOpen(v => !v)}
              className={cn(
                "text-[10px] px-3 py-1.5 border rounded-lg font-medium transition-colors cursor-pointer",
                diffOpen
                  ? "bg-[#005EA2]/10 border-[#005EA2]/30 text-[#005EA2]"
                  : "border-border text-muted-foreground hover:bg-muted",
              )}
            >
              {diffOpen ? "Hide" : "Show"} Diff Viewer
            </button>
          </div>
        </div>

        {/* Stat row */}
        <div className="flex gap-3 flex-wrap">
          <StatCard label="Running"     value={2}       color="text-[#005EA2]" pulse />
          <StatCard label="Queued"      value={1}       color="text-foreground" />
          <StatCard label="Errors"      value={1}       color="text-[#C5191B]" />
          <StatCard label="Avg Latency" value="4.9s"    color="text-[#1A7F4B]" />
          <StatCard label="Rate Used"   value="28%"     color="text-muted-foreground" />
        </div>
      </header>

      {/* Main layout */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left 2/3: agentic control panel */}
        <div className="flex-1 overflow-hidden border-r border-border">
          <AgenticControlPanel
            actions={DEMO_ACTIONS}
            agents={DEMO_AGENTS}
            globalConfidenceMin={80}
            className="h-full"
          />
        </div>

        {/* Right 1/3: rate limit + error recovery */}
        <div className="w-[300px] flex-shrink-0 flex flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto border-b border-border">
            <RateLimitPanel
              models={DEMO_MODELS}
              agentCosts={DEMO_AGENT_COSTS}
              sprintBudget={25}
              sprintSpent={5.32}
              className="h-full"
            />
          </div>
          <div className="flex-1 overflow-y-auto">
            <AgentErrorRecovery
              error={DEMO_ERROR}
              autoRetryAfter={60}
              className="h-full"
            />
          </div>
        </div>
      </div>

      {/* Bottom: diff viewer drawer */}
      {diffOpen && (
        <div className="h-[240px] border-t border-border shrink-0 overflow-hidden">
          <AgentDiffViewer
            agentName="fda-drafting-agent"
            agentRun="run-2026-02-22-001"
            gateLabel="HITL Gate 2: Drafting Review"
            chunks={DEMO_CHUNKS}
            className="h-full"
          />
        </div>
      )}
    </main>
  );
}
