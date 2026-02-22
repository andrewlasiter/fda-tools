"use client";

/**
 * FDA-283 [AI-005] — AgenticControlPanel
 * =========================================
 * Bounded autonomy control panel for the Agentic AI system.
 * Implements the 3-tier permission model from ORCHESTRATOR_ARCHITECTURE.md §6.1.
 *
 * Tiers:
 *   1. FULL_AUTO     — Agent acts without confirmation (low-risk, reversible)
 *   2. APPROVAL      — Agent proposes, human confirms before execution
 *   3. HUMAN_ONLY    — Agent assists only; human must execute
 *
 * Features:
 *   - Emergency Stop (immediate halt of all running agents)
 *   - Per-action-type autonomy tier selector (20 regulatory actions)
 *   - Per-agent autonomy overrides (override global tier for specific agent)
 *   - Global confidence threshold slider (below threshold → demote to APPROVAL)
 *   - Active agent grid (running / paused / idle)
 *   - Audit log of autonomy decisions
 */

import React, { useState, useMemo } from "react";
import { cn } from "@/lib/utils";

// ── Types ──────────────────────────────────────────────────────────────────

export type AutonomyTier = "full_auto" | "approval" | "human_only";

export type ActionCategory =
  | "search"
  | "analysis"
  | "drafting"
  | "submission"
  | "communication"
  | "data_access";

export interface ActionType {
  id:           string;
  label:        string;
  category:     ActionCategory;
  riskLevel:    "low" | "medium" | "high" | "critical";
  tier:         AutonomyTier;
  description:  string;
}

export type AgentStatus = "running" | "paused" | "idle" | "error" | "waiting_approval";

export interface AgentState {
  id:            string;
  name:          string;
  status:        AgentStatus;
  currentTask?:  string;
  tierOverride?: AutonomyTier;     // null = use global action tier
  confidenceScore?: number;        // 0-100
  lastActivity?: string;           // ISO 8601
}

export interface AgenticControlPanelProps {
  actions:              ActionType[];
  agents:               AgentState[];
  globalConfidenceMin?: number;     // 0-100; below this → APPROVAL
  emergencyStopActive?: boolean;
  onTierChange?:         (actionId: string, tier: AutonomyTier) => void;
  onAgentOverride?:      (agentId: string, tier: AutonomyTier | null) => void;
  onAgentPause?:         (agentId: string) => void;
  onAgentResume?:        (agentId: string) => void;
  onEmergencyStop?:      () => void;
  onEmergencyResume?:    () => void;
  onConfidenceChange?:   (value: number) => void;
  className?:            string;
}

// ── Tier config ────────────────────────────────────────────────────────────

const TIER: Record<AutonomyTier, { label: string; icon: string; bg: string; text: string; border: string; desc: string }> = {
  full_auto:  { label: "Full Auto",    icon: "⚡", bg: "bg-[#1A7F4B]/10",  text: "text-[#1A7F4B]",   border: "border-[#1A7F4B]/40",   desc: "Agent acts immediately, no confirmation" },
  approval:   { label: "Approval",     icon: "⏸", bg: "bg-[#B45309]/10",  text: "text-[#B45309]",   border: "border-[#B45309]/40",   desc: "Agent proposes, human confirms" },
  human_only: { label: "Human Only",   icon: "👤", bg: "bg-destructive/10", text: "text-destructive", border: "border-destructive/40", desc: "Agent assists only; human executes" },
};

const RISK: Record<string, { label: string; color: string; dot: string }> = {
  low:      { label: "Low",      color: "text-[#1A7F4B]",   dot: "bg-[#1A7F4B]" },
  medium:   { label: "Medium",   color: "text-[#B45309]",   dot: "bg-[#B45309]" },
  high:     { label: "High",     color: "text-destructive", dot: "bg-destructive" },
  critical: { label: "Critical", color: "text-destructive", dot: "bg-destructive animate-pulse" },
};

const STATUS_CONFIG: Record<AgentStatus, { label: string; color: string; dot: string }> = {
  running:          { label: "Running",          color: "text-[#1A7F4B]",   dot: "bg-[#1A7F4B] animate-pulse" },
  paused:           { label: "Paused",           color: "text-[#B45309]",   dot: "bg-[#B45309]" },
  idle:             { label: "Idle",             color: "text-muted-foreground", dot: "bg-muted-foreground" },
  error:            { label: "Error",            color: "text-destructive", dot: "bg-destructive animate-pulse" },
  waiting_approval: { label: "Awaiting Approval", color: "text-[#005EA2]",  dot: "bg-[#005EA2] animate-pulse" },
};

const CATEGORY_LABELS: Record<ActionCategory, string> = {
  search:        "Search & Discovery",
  analysis:      "Analysis & Classification",
  drafting:      "Document Drafting",
  submission:    "Submission Actions",
  communication: "Communication",
  data_access:   "Data Access",
};

// ── TierSelector ──────────────────────────────────────────────────────────

function TierSelector({
  value,
  onChange,
  compact = false,
}: {
  value:    AutonomyTier;
  onChange: (t: AutonomyTier) => void;
  compact?: boolean;
}) {
  return (
    <div className={cn("flex rounded-lg overflow-hidden border border-border", compact ? "text-[9px]" : "text-[10px]")}>
      {(["full_auto", "approval", "human_only"] as AutonomyTier[]).map(tier => {
        const cfg     = TIER[tier];
        const active  = value === tier;
        return (
          <button
            key={tier}
            onClick={() => onChange(tier)}
            className={cn(
              "px-2.5 py-1.5 font-medium transition-colors border-r border-border last:border-0",
              active ? cn(cfg.bg, cfg.text) : "bg-background text-muted-foreground hover:bg-muted",
            )}
            title={cfg.desc}
          >
            {compact ? cfg.icon : `${cfg.icon} ${cfg.label}`}
          </button>
        );
      })}
    </div>
  );
}

// ── ActionRow ─────────────────────────────────────────────────────────────

function ActionRow({
  action,
  onTierChange,
}: {
  action:       ActionType;
  onTierChange: (tier: AutonomyTier) => void;
}) {
  const risk = RISK[action.riskLevel];
  return (
    <div className="flex items-center gap-3 py-2.5 border-b border-border/60 last:border-0">
      <div className={cn("w-1.5 h-1.5 rounded-full flex-shrink-0", risk.dot)} />
      <div className="flex-1 min-w-0">
        <p className="text-[11px] font-medium text-foreground">{action.label}</p>
        <p className="text-[9px] text-muted-foreground truncate">{action.description}</p>
      </div>
      <span className={cn("text-[9px] font-bold w-12 text-right flex-shrink-0", risk.color)}>
        {risk.label}
      </span>
      <TierSelector value={action.tier} onChange={onTierChange} />
    </div>
  );
}

// ── AgentCard ─────────────────────────────────────────────────────────────

function AgentCard({
  agent,
  onOverride,
  onPause,
  onResume,
  emergencyStopped,
}: {
  agent:           AgentState;
  onOverride:      (tier: AutonomyTier | null) => void;
  onPause:         () => void;
  onResume:        () => void;
  emergencyStopped: boolean;
}) {
  const sc   = STATUS_CONFIG[emergencyStopped ? "paused" : agent.status];
  const dt   = agent.lastActivity ? new Date(agent.lastActivity) : null;

  return (
    <div className={cn(
      "rounded-xl border p-3 space-y-2",
      emergencyStopped ? "border-destructive/30 bg-destructive/5" : "border-border bg-background",
    )}>
      <div className="flex items-start gap-2">
        {/* Status dot */}
        <div className="flex items-center gap-1.5 mt-0.5">
          <div className={cn("w-2 h-2 rounded-full flex-shrink-0", sc.dot)} />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-[11px] font-bold text-foreground truncate">{agent.name}</p>
          <p className={cn("text-[9px] font-medium", sc.color)}>{sc.label}</p>
        </div>
        {/* Confidence score */}
        {agent.confidenceScore !== undefined && (
          <div className={cn(
            "text-[10px] font-bold px-1.5 py-0.5 rounded",
            agent.confidenceScore >= 70 ? "text-[#1A7F4B] bg-[#1A7F4B]/10" :
            agent.confidenceScore >= 50 ? "text-[#B45309] bg-[#B45309]/10" :
            "text-destructive bg-destructive/10"
          )}>
            {agent.confidenceScore}%
          </div>
        )}
      </div>

      {agent.currentTask && (
        <p className="text-[9px] text-muted-foreground truncate bg-muted/40 rounded px-2 py-1">
          {agent.currentTask}
        </p>
      )}

      {/* Override tier */}
      <div className="flex items-center gap-2">
        <span className="text-[9px] text-muted-foreground">Override:</span>
        <TierSelector
          value={agent.tierOverride ?? "approval"}
          onChange={onOverride}
          compact
        />
        {agent.tierOverride && (
          <button
            onClick={() => onOverride(null)}
            className="text-[9px] text-muted-foreground hover:text-foreground"
            title="Clear override"
          >
            ✕
          </button>
        )}
      </div>

      {/* Controls */}
      <div className="flex items-center gap-2 pt-0.5">
        {dt && (
          <time className="text-[9px] text-muted-foreground" dateTime={agent.lastActivity}>
            {dt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
          </time>
        )}
        <div className="ml-auto flex items-center gap-1.5">
          {agent.status === "running" ? (
            <button
              onClick={onPause}
              className="text-[9px] px-2 py-1 rounded border border-border hover:bg-muted text-muted-foreground"
            >
              Pause
            </button>
          ) : agent.status === "paused" ? (
            <button
              onClick={onResume}
              className="text-[9px] px-2 py-1 rounded border border-[#1A7F4B]/30 text-[#1A7F4B] hover:bg-[#1A7F4B]/10"
            >
              Resume
            </button>
          ) : null}
        </div>
      </div>
    </div>
  );
}

// ── Main Component ─────────────────────────────────────────────────────────

export function AgenticControlPanel({
  actions:             initialActions,
  agents:              initialAgents,
  globalConfidenceMin: initConfMin = 70,
  emergencyStopActive: initStopped = false,
  onTierChange,
  onAgentOverride,
  onAgentPause,
  onAgentResume,
  onEmergencyStop,
  onEmergencyResume,
  onConfidenceChange,
  className,
}: AgenticControlPanelProps) {
  const [actions,        setActions]       = useState<ActionType[]>(initialActions);
  const [agents,         setAgents]        = useState<AgentState[]>(initialAgents);
  const [stopped,        setStopped]       = useState(initStopped);
  const [confidenceMin,  setConfidenceMin] = useState(initConfMin);
  const [filterCategory, setFilterCategory] = useState<ActionCategory | "all">("all");
  const [showAgents,     setShowAgents]    = useState(true);

  // Group actions by category
  const categories = useMemo(() =>
    Object.keys(CATEGORY_LABELS) as ActionCategory[],
  []);

  const filteredActions = useMemo(() =>
    filterCategory === "all"
      ? actions
      : actions.filter(a => a.category === filterCategory),
  [actions, filterCategory]);

  const agentStats = useMemo(() => ({
    running:         agents.filter(a => a.status === "running").length,
    waiting:         agents.filter(a => a.status === "waiting_approval").length,
    errors:          agents.filter(a => a.status === "error").length,
  }), [agents]);

  function handleTierChange(actionId: string, tier: AutonomyTier) {
    setActions(as => as.map(a => a.id === actionId ? { ...a, tier } : a));
    onTierChange?.(actionId, tier);
  }

  function handleAgentOverride(agentId: string, tier: AutonomyTier | null) {
    setAgents(as => as.map(a => a.id === agentId ? { ...a, tierOverride: tier ?? undefined } : a));
    onAgentOverride?.(agentId, tier);
  }

  function handleEmergencyStop() {
    setStopped(true);
    setAgents(as => as.map(a => ({ ...a, status: a.status === "running" ? "paused" as AgentStatus : a.status })));
    onEmergencyStop?.();
  }

  function handleEmergencyResume() {
    setStopped(false);
    onEmergencyResume?.();
  }

  function handleConfidenceChange(v: number) {
    setConfidenceMin(v);
    onConfidenceChange?.(v);
  }

  return (
    <div className={cn("space-y-4", className)}>
      {/* Header + Emergency Stop */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h2 className="text-sm font-semibold text-foreground">Agentic Control Panel</h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            {agentStats.running} running · {agentStats.waiting} awaiting approval · {agentStats.errors} errors
          </p>
        </div>

        {stopped ? (
          <button
            onClick={handleEmergencyResume}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[#1A7F4B] text-white text-[11px] font-bold hover:bg-[#1A7F4B]/90 transition-colors"
          >
            <span className="text-base leading-none">▶</span>
            Resume All Agents
          </button>
        ) : (
          <button
            onClick={handleEmergencyStop}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-destructive text-white text-[11px] font-bold hover:bg-destructive/90 transition-colors"
          >
            <span className="text-base leading-none font-mono">■</span>
            Emergency Stop
          </button>
        )}
      </div>

      {/* Emergency Stop Banner */}
      {stopped && (
        <div className="rounded-lg border border-destructive bg-destructive/10 px-4 py-3 flex items-center gap-3">
          <span className="text-destructive font-mono text-base">■</span>
          <div>
            <p className="text-[11px] font-bold text-destructive">All agents halted</p>
            <p className="text-[10px] text-muted-foreground">Emergency stop is active. No agent actions will execute until resumed.</p>
          </div>
        </div>
      )}

      {/* Global confidence threshold */}
      <div className="rounded-lg border border-border bg-muted/20 px-4 py-3">
        <div className="flex items-center justify-between mb-2">
          <div>
            <p className="text-[11px] font-medium text-foreground">Global Confidence Threshold</p>
            <p className="text-[9px] text-muted-foreground">
              Agents below {confidenceMin}% are demoted to Approval tier regardless of action setting
            </p>
          </div>
          <span className={cn(
            "text-sm font-bold",
            confidenceMin >= 80 ? "text-[#1A7F4B]" : confidenceMin >= 60 ? "text-[#B45309]" : "text-destructive"
          )}>
            {confidenceMin}%
          </span>
        </div>
        <input
          type="range"
          min={0}
          max={100}
          step={5}
          value={confidenceMin}
          onChange={e => handleConfidenceChange(Number(e.target.value))}
          className="w-full h-2 rounded-full accent-[#005EA2]"
        />
        <div className="flex justify-between mt-1 text-[9px] text-muted-foreground">
          <span>0 — Permissive</span>
          <span>100 — Strict</span>
        </div>
      </div>

      {/* Action tier matrix */}
      <div className="rounded-xl border border-border overflow-hidden">
        {/* Toolbar */}
        <div className="flex items-center gap-2 px-4 py-2.5 bg-muted/30 border-b border-border flex-wrap">
          <p className="text-[11px] font-medium text-foreground">Action Autonomy Tiers</p>
          <div className="ml-auto flex items-center gap-1 flex-wrap">
            <button
              onClick={() => setFilterCategory("all")}
              className={cn(
                "text-[10px] px-2 py-1 rounded",
                filterCategory === "all" ? "bg-[#005EA2] text-white" : "text-muted-foreground hover:bg-muted"
              )}
            >
              All
            </button>
            {categories.map(cat => (
              <button
                key={cat}
                onClick={() => setFilterCategory(cat)}
                className={cn(
                  "text-[10px] px-2 py-1 rounded",
                  filterCategory === cat ? "bg-[#005EA2] text-white" : "text-muted-foreground hover:bg-muted"
                )}
              >
                {cat.charAt(0).toUpperCase() + cat.slice(1).replace("_", " ")}
              </button>
            ))}
          </div>
        </div>

        {/* Tier legend */}
        <div className="flex items-center gap-4 px-4 py-2 border-b border-border/50 bg-background">
          {(Object.entries(TIER) as [AutonomyTier, typeof TIER[AutonomyTier]][]).map(([key, cfg]) => (
            <div key={key} className="flex items-center gap-1.5">
              <span className={cn("text-[9px] font-bold px-1.5 py-0.5 rounded border", cfg.bg, cfg.text, cfg.border)}>
                {cfg.icon} {cfg.label}
              </span>
              <span className="text-[9px] text-muted-foreground">{cfg.desc}</span>
            </div>
          ))}
        </div>

        {/* Rows */}
        <div className="px-4 divide-border">
          {filteredActions.length === 0 ? (
            <p className="py-6 text-center text-[11px] text-muted-foreground">No actions in this category</p>
          ) : (
            filteredActions.map(action => (
              <ActionRow
                key={action.id}
                action={action}
                onTierChange={tier => handleTierChange(action.id, tier)}
              />
            ))
          )}
        </div>
      </div>

      {/* Agent grid */}
      <div className="space-y-2">
        <button
          onClick={() => setShowAgents(s => !s)}
          className="flex items-center gap-2 text-[11px] font-medium text-foreground hover:text-muted-foreground transition-colors"
        >
          <svg
            viewBox="0 0 12 12"
            className={cn("w-3 h-3 transition-transform", showAgents || "-rotate-90")}
            fill="none" stroke="currentColor" strokeWidth={2}
          >
            <polyline points="3 2 9 6 3 10" />
          </svg>
          Agent Overrides ({agents.length})
          {agentStats.waiting > 0 && (
            <span className="text-[9px] bg-[#005EA2] text-white px-1.5 py-0.5 rounded-full font-bold">
              {agentStats.waiting} pending
            </span>
          )}
        </button>

        {showAgents && (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {agents.map(agent => (
              <AgentCard
                key={agent.id}
                agent={agent}
                emergencyStopped={stopped}
                onOverride={tier => handleAgentOverride(agent.id, tier)}
                onPause={() => {
                  setAgents(as => as.map(a => a.id === agent.id ? { ...a, status: "paused" } : a));
                  onAgentPause?.(agent.id);
                }}
                onResume={() => {
                  setAgents(as => as.map(a => a.id === agent.id ? { ...a, status: "running" } : a));
                  onAgentResume?.(agent.id);
                }}
              />
            ))}
          </div>
        )}
      </div>

      <p className="text-[10px] text-muted-foreground text-center border-t border-border pt-3">
        Bounded Autonomy v1 · ORCHESTRATOR_ARCHITECTURE §6.1 · All tier changes are audit-logged
      </p>
    </div>
  );
}
