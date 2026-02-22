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
import { AgenticControlPanel } from "@/components/ai/agentic-control-panel";
import { AgentDiffViewer }     from "@/components/ai/agent-diff-viewer";
import { RateLimitPanel }      from "@/components/ai/rate-limit-panel";
import { AgentErrorRecovery }  from "@/components/ai/agent-error-recovery";

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
    <div className="flex flex-col h-[calc(100vh-64px)] bg-background overflow-hidden">
      {/* Page header */}
      <div className="px-5 py-4 border-b border-border shrink-0">
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
          <StatCard label="Running"     value={3}         color="text-[#005EA2]" pulse />
          <StatCard label="Queued"      value={7}         color="text-foreground" />
          <StatCard label="Errors"      value={1}         color="text-[#C5191B]" />
          <StatCard label="Avg Latency" value="1.4s"      color="text-[#1A7F4B]" />
          <StatCard label="Rate Used"   value="12%"       color="text-muted-foreground" />
        </div>
      </div>

      {/* Main layout */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left 2/3: agentic control panel */}
        <div className="flex-1 overflow-hidden border-r border-border">
          <AgenticControlPanel className="h-full" />
        </div>

        {/* Right 1/3: rate limit + error recovery */}
        <div className="w-[300px] flex-shrink-0 flex flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto border-b border-border">
            <RateLimitPanel className="h-full" />
          </div>
          <div className="flex-1 overflow-y-auto">
            <AgentErrorRecovery className="h-full" />
          </div>
        </div>
      </div>

      {/* Bottom: diff viewer drawer */}
      {diffOpen && (
        <div className="h-[240px] border-t border-border shrink-0 overflow-hidden">
          <AgentDiffViewer className="h-full" />
        </div>
      )}
    </div>
  );
}
