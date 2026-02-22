"use client";

/**
 * FDA-282 [AI-004] — RateLimitPanel
 * =====================================
 * API usage meters, cost visibility, and token budget controls.
 * Shows real-time consumption vs. limits for each Claude model tier.
 *
 * Features:
 *   - Per-model token usage rings (Opus / Sonnet / Haiku)
 *   - Cost breakdown: per-sprint, per-agent, total session
 *   - Rate limit threshold bars with warning/critical zones
 *   - Request-per-minute (RPM) live meter
 *   - Budget alerts with configurable thresholds
 *   - Usage history sparkline (last 12 intervals)
 */

import React, { useMemo } from "react";
import { cn } from "@/lib/utils";

// ── Types ──────────────────────────────────────────────────────────────────

export type ModelTier = "opus" | "sonnet" | "haiku";

export interface ModelUsage {
  model:         ModelTier;
  inputTokens:   number;
  outputTokens:  number;
  limitTokens:   number;           // per-minute limit
  requestsUsed:  number;
  requestsLimit: number;
  costUsd:       number;
  history:       number[];         // last 12 measurements (0-100% utilization)
}

export interface AgentCost {
  agentName: string;
  model:     ModelTier;
  tokens:    number;
  costUsd:   number;
  runs:      number;
}

export interface BudgetAlert {
  id:        string;
  message:   string;
  severity:  "info" | "warning" | "critical";
  timestamp: string;
}

export interface RateLimitPanelProps {
  models:       ModelUsage[];
  agentCosts:   AgentCost[];
  alerts?:      BudgetAlert[];
  sprintBudget?: number;           // USD cap for this sprint
  sprintSpent?:  number;           // USD spent so far
  className?:   string;
}

// ── Model config ───────────────────────────────────────────────────────────

const MODEL_CONFIG: Record<ModelTier, { label: string; color: string; bg: string; costPer1k: { input: number; output: number } }> = {
  opus:   { label: "Claude Opus 4.6",   color: "#7C3AED", bg: "bg-[#7C3AED]/10", costPer1k: { input: 15,  output: 75  } },
  sonnet: { label: "Claude Sonnet 4.6", color: "#005EA2", bg: "bg-[#005EA2]/10", costPer1k: { input: 3,   output: 15  } },
  haiku:  { label: "Claude Haiku 4.5",  color: "#1A7F4B", bg: "bg-[#1A7F4B]/10", costPer1k: { input: 0.8, output: 4   } },
};

// ── Alert severity config ──────────────────────────────────────────────────

const ALERT_CONFIG: Record<string, { bg: string; text: string; border: string; icon: string }> = {
  info:     { bg: "bg-[#005EA2]/8",  text: "text-[#005EA2]",   border: "border-[#005EA2]/30",   icon: "ℹ" },
  warning:  { bg: "bg-[#B45309]/8",  text: "text-[#B45309]",   border: "border-[#B45309]/30",   icon: "⚠" },
  critical: { bg: "bg-destructive/8", text: "text-destructive", border: "border-destructive/30", icon: "✕" },
};

// ── Subcomponents ──────────────────────────────────────────────────────────

function UtilBar({ pct, color, warn = 80, crit = 95 }: { pct: number; color: string; warn?: number; crit?: number }) {
  const barColor = pct >= crit ? "#C5191B" : pct >= warn ? "#B45309" : color;
  return (
    <div className="relative h-2 rounded-full bg-muted overflow-hidden">
      {/* Warning zone */}
      <div className="absolute top-0 bottom-0 bg-[#B45309]/15" style={{ left: `${warn}%`, right: `${100 - crit}%` }} />
      {/* Critical zone */}
      <div className="absolute top-0 bottom-0 bg-destructive/15" style={{ left: `${crit}%`, right: 0 }} />
      {/* Fill */}
      <div
        className="absolute top-0 left-0 bottom-0 rounded-full transition-all"
        style={{ width: `${Math.min(pct, 100)}%`, background: barColor }}
      />
    </div>
  );
}

function Sparkline({ data, color }: { data: number[]; color: string }) {
  if (!data.length) return null;
  const max = Math.max(...data, 1);
  const w = 80;
  const h = 24;
  const step = w / (data.length - 1);
  const pts = data.map((v, i) => `${i * step},${h - (v / max) * h}`).join(" ");
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-20 h-6 flex-shrink-0">
      <polyline points={pts} fill="none" stroke={color} strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function ModelCard({ usage }: { usage: ModelUsage }) {
  const cfg = MODEL_CONFIG[usage.model];
  const tokenPct = Math.round(((usage.inputTokens + usage.outputTokens) / Math.max(usage.limitTokens, 1)) * 100);
  const reqPct   = Math.round((usage.requestsUsed / Math.max(usage.requestsLimit, 1)) * 100);

  return (
    <div className={cn("rounded-xl border border-border p-4 space-y-3", cfg.bg)}>
      <div className="flex items-center justify-between gap-2">
        <div>
          <p className="text-[11px] font-bold text-foreground">{cfg.label}</p>
          <p className="text-[10px] text-muted-foreground">
            ${usage.costUsd.toFixed(4)} session · {(usage.inputTokens / 1000).toFixed(1)}K in / {(usage.outputTokens / 1000).toFixed(1)}K out
          </p>
        </div>
        <Sparkline data={usage.history} color={cfg.color} />
      </div>

      <div className="space-y-2">
        {/* Token utilization */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <span className="text-[10px] text-muted-foreground">Token utilization</span>
            <span className={cn(
              "text-[10px] font-bold",
              tokenPct >= 95 ? "text-destructive" : tokenPct >= 80 ? "text-[#B45309]" : "text-foreground"
            )}>
              {tokenPct}%
            </span>
          </div>
          <UtilBar pct={tokenPct} color={cfg.color} />
        </div>

        {/* RPM */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <span className="text-[10px] text-muted-foreground">Requests / min</span>
            <span className="text-[10px] font-mono text-foreground">
              {usage.requestsUsed}/{usage.requestsLimit}
            </span>
          </div>
          <UtilBar pct={reqPct} color={cfg.color} />
        </div>
      </div>
    </div>
  );
}

// ── Main Component ─────────────────────────────────────────────────────────

export function RateLimitPanel({
  models,
  agentCosts,
  alerts = [],
  sprintBudget,
  sprintSpent = 0,
  className,
}: RateLimitPanelProps) {
  const totalCost = useMemo(() =>
    models.reduce((sum, m) => sum + m.costUsd, 0),
  [models]);

  const topAgents = useMemo(() =>
    [...agentCosts].sort((a, b) => b.costUsd - a.costUsd).slice(0, 6),
  [agentCosts]);

  const budgetPct = sprintBudget ? Math.round((sprintSpent / sprintBudget) * 100) : null;

  return (
    <div className={cn("space-y-4", className)}>
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-sm font-semibold text-foreground">Rate Limits & Cost</h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Session total: <span className="font-mono font-bold text-foreground">${totalCost.toFixed(4)}</span>
            {sprintBudget && (
              <> · Sprint budget: <span className="font-mono font-bold text-foreground">${sprintSpent.toFixed(2)} / ${sprintBudget}</span></>
            )}
          </p>
        </div>
      </div>

      {/* Budget bar */}
      {budgetPct !== null && (
        <div className="rounded-lg border border-border px-4 py-3 bg-muted/20">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[11px] font-medium text-foreground">Sprint Budget</span>
            <span className={cn(
              "text-[11px] font-bold",
              budgetPct >= 90 ? "text-destructive" : budgetPct >= 70 ? "text-[#B45309]" : "text-[#1A7F4B]"
            )}>
              {budgetPct}% used
            </span>
          </div>
          <UtilBar pct={budgetPct} color="#1A7F4B" warn={70} crit={90} />
          <div className="flex justify-between mt-1">
            <span className="text-[9px] text-muted-foreground">${sprintSpent.toFixed(2)} spent</span>
            <span className="text-[9px] text-muted-foreground">${(sprintBudget! - sprintSpent).toFixed(2)} remaining</span>
          </div>
        </div>
      )}

      {/* Active alerts */}
      {alerts.length > 0 && (
        <div className="space-y-1.5">
          {alerts.map(alert => {
            const acfg = ALERT_CONFIG[alert.severity];
            const dt   = new Date(alert.timestamp);
            return (
              <div
                key={alert.id}
                className={cn("flex items-start gap-2.5 px-3 py-2.5 rounded-lg border text-[10px]", acfg.bg, acfg.border)}
              >
                <span className={cn("mt-0.5 font-bold", acfg.text)}>{acfg.icon}</span>
                <span className={cn("flex-1", acfg.text)}>{alert.message}</span>
                <time className="text-muted-foreground flex-shrink-0" dateTime={alert.timestamp}>
                  {dt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                </time>
              </div>
            );
          })}
        </div>
      )}

      {/* Per-model cards */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {models.map(m => <ModelCard key={m.model} usage={m} />)}
      </div>

      {/* Per-agent cost breakdown */}
      {topAgents.length > 0 && (
        <div className="rounded-xl border border-border overflow-hidden">
          <div className="px-4 py-2.5 bg-muted/30 border-b border-border">
            <p className="text-[11px] font-medium text-foreground">Top Agents by Cost</p>
          </div>
          <div className="divide-y divide-border">
            {topAgents.map((a, i) => {
              const mcfg = MODEL_CONFIG[a.model];
              const maxCost = topAgents[0]?.costUsd ?? 1;
              const barPct  = Math.round((a.costUsd / maxCost) * 100);
              return (
                <div key={i} className="px-4 py-2.5 flex items-center gap-3">
                  <div className="w-5 text-[10px] text-muted-foreground text-right">{i + 1}</div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-[11px] font-medium text-foreground truncate">{a.agentName}</span>
                      <span
                        className="text-[9px] font-bold px-1.5 py-0.5 rounded"
                        style={{ background: mcfg.color + "20", color: mcfg.color }}
                      >
                        {a.model}
                      </span>
                    </div>
                    <div className="mt-1 h-1 rounded-full bg-muted overflow-hidden">
                      <div
                        className="h-full rounded-full"
                        style={{ width: `${barPct}%`, background: mcfg.color }}
                      />
                    </div>
                  </div>
                  <div className="text-right flex-shrink-0">
                    <div className="text-[11px] font-mono text-foreground">${a.costUsd.toFixed(4)}</div>
                    <div className="text-[9px] text-muted-foreground">{a.runs} runs · {(a.tokens / 1000).toFixed(1)}K tok</div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
