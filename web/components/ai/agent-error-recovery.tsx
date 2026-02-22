"use client";

/**
 * FDA-281 [AI-003] — AgentErrorRecovery
 * ========================================
 * Graceful failure UI for agentic pipeline errors.
 * Shows error context, recovery options, and escalation path.
 *
 * Features:
 *   - Error classification (timeout / rate_limit / parse_error / api_error / validation_error)
 *   - Recovery actions: Retry / Skip / Fallback / Escalate
 *   - Error history timeline (last N failures for this agent)
 *   - Confidence impact indicator (how much SRI/confidence dropped)
 *   - Auto-retry countdown (optional)
 *   - Diagnostic details collapse
 */

import React, { useState, useEffect, useCallback } from "react";
import { cn } from "@/lib/utils";

// ── Types ──────────────────────────────────────────────────────────────────

export type ErrorCategory =
  | "timeout"
  | "rate_limit"
  | "parse_error"
  | "api_error"
  | "validation_error"
  | "context_overflow"
  | "unknown";

export type RecoveryAction = "retry" | "skip" | "fallback" | "escalate";

export interface AgentError {
  id:           string;
  agentName:    string;
  category:     ErrorCategory;
  message:      string;
  detail?:      string;           // stack trace / raw API error
  timestamp:    string;           // ISO 8601
  attempt:      number;           // which retry attempt
  maxAttempts:  number;
  sriImpact?:   number;           // negative pts to SRI from this failure
  gateLabel?:   string;
  resolved?:    boolean;
}

export interface AgentErrorRecoveryProps {
  error:            AgentError;
  history?:         AgentError[];   // previous errors from this agent
  autoRetryAfter?:  number;         // seconds; 0 = no auto-retry
  onRetry?:         () => void;
  onSkip?:          () => void;
  onFallback?:      () => void;
  onEscalate?:      () => void;
  className?:       string;
}

// ── Config ─────────────────────────────────────────────────────────────────

const ERR_CONFIG: Record<ErrorCategory, { label: string; icon: string; bg: string; text: string; border: string; hint: string }> = {
  timeout:          { label: "Timeout",           icon: "⏱", bg: "bg-[#B45309]/8",       text: "text-[#B45309]",    border: "border-[#B45309]/30",    hint: "Agent took too long to respond. Check network and API status." },
  rate_limit:       { label: "Rate Limited",      icon: "🚦", bg: "bg-[#7C3AED]/8",       text: "text-[#7C3AED]",   border: "border-[#7C3AED]/30",    hint: "API quota exhausted. Wait before retrying or switch to a lighter model." },
  parse_error:      { label: "Parse Error",       icon: "⚠", bg: "bg-[#B45309]/8",       text: "text-[#B45309]",   border: "border-[#B45309]/30",    hint: "Agent returned malformed output. Retry with stricter prompt constraints." },
  api_error:        { label: "API Error",         icon: "✕", bg: "bg-destructive/8",      text: "text-destructive", border: "border-destructive/30",  hint: "Upstream API returned an error. Check service status." },
  validation_error: { label: "Validation Failed", icon: "⚑", bg: "bg-[#B45309]/8",       text: "text-[#B45309]",   border: "border-[#B45309]/30",    hint: "Output did not meet regulatory quality requirements." },
  context_overflow: { label: "Context Overflow",  icon: "⟳", bg: "bg-[#005EA2]/8",       text: "text-[#005EA2]",   border: "border-[#005EA2]/30",    hint: "Input exceeded model context window. Reduce chunk size or summarize." },
  unknown:          { label: "Unknown Error",     icon: "?", bg: "bg-muted",              text: "text-muted-foreground", border: "border-border",     hint: "Unclassified failure. Review diagnostic details below." },
};

const RECOVERY_CONFIG: Record<RecoveryAction, { label: string; desc: string; variant: "primary" | "secondary" | "danger" | "neutral" }> = {
  retry:    { label: "Retry",           desc: "Re-run this agent with the same inputs",    variant: "primary" },
  skip:     { label: "Skip",            desc: "Skip this agent and continue the pipeline", variant: "neutral" },
  fallback: { label: "Use Fallback",    desc: "Switch to a simpler rule-based approach",   variant: "secondary" },
  escalate: { label: "Escalate to RA",  desc: "Flag for human regulatory expert review",   variant: "danger" },
};

function recoveryBtnClass(variant: string) {
  switch (variant) {
    case "primary":   return "bg-[#005EA2] text-white hover:bg-[#005EA2]/90 border-[#005EA2]";
    case "secondary": return "bg-background text-foreground border-border hover:bg-muted";
    case "danger":    return "bg-destructive/10 text-destructive border-destructive/30 hover:bg-destructive/20";
    default:          return "bg-background text-muted-foreground border-border hover:bg-muted";
  }
}

// ── Countdown ──────────────────────────────────────────────────────────────

function Countdown({ seconds, onComplete }: { seconds: number; onComplete: () => void }) {
  const [remaining, setRemaining] = useState(seconds);

  useEffect(() => {
    if (remaining <= 0) { onComplete(); return; }
    const t = setTimeout(() => setRemaining(r => r - 1), 1000);
    return () => clearTimeout(t);
  }, [remaining, onComplete]);

  return (
    <span className="text-[10px] text-muted-foreground">
      Auto-retry in {remaining}s
      <button
        className="ml-2 text-[#005EA2] hover:underline"
        onClick={onComplete}
      >
        Retry now
      </button>
    </span>
  );
}

// ── Main Component ─────────────────────────────────────────────────────────

export function AgentErrorRecovery({
  error,
  history = [],
  autoRetryAfter = 0,
  onRetry,
  onSkip,
  onFallback,
  onEscalate,
  className,
}: AgentErrorRecoveryProps) {
  const [showDetail, setShowDetail] = useState(false);
  const [resolved,  setResolved]   = useState(error.resolved ?? false);
  const [action,    setAction]     = useState<RecoveryAction | null>(null);

  const cfg = ERR_CONFIG[error.category];
  const dt  = new Date(error.timestamp);
  const retriesLeft = error.maxAttempts - error.attempt;

  const handlers: Record<RecoveryAction, (() => void) | undefined> = {
    retry:    onRetry,
    skip:     onSkip,
    fallback: onFallback,
    escalate: onEscalate,
  };

  const handleAction = useCallback((act: RecoveryAction) => {
    setAction(act);
    if (act !== "escalate") setResolved(true);
    handlers[act]?.();
  }, [onRetry, onSkip, onFallback, onEscalate]);

  if (resolved && action) {
    const recCfg = RECOVERY_CONFIG[action];
    return (
      <div className={cn(
        "rounded-xl border p-4 flex items-center gap-3",
        action === "escalate" ? "border-destructive/30 bg-destructive/5" : "border-[#1A7F4B]/30 bg-[#1A7F4B]/5",
        className,
      )}>
        <span className={action === "escalate" ? "text-destructive text-sm" : "text-[#1A7F4B] text-sm"}>
          {action === "escalate" ? "⚑" : "✓"}
        </span>
        <div>
          <p className="text-xs font-medium text-foreground">{recCfg.label} initiated</p>
          <p className="text-[10px] text-muted-foreground">{recCfg.desc}</p>
        </div>
      </div>
    );
  }

  return (
    <div className={cn("space-y-3", className)}>
      {/* Error card */}
      <div className={cn("rounded-xl border overflow-hidden", cfg.border, cfg.bg)}>
        {/* Header */}
        <div className="px-4 py-3 border-b border-border flex items-start gap-3">
          <span className={cn("text-base mt-0.5", cfg.text)}>{cfg.icon}</span>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className={cn("text-[11px] font-bold", cfg.text)}>{cfg.label}</span>
              <span className="text-[10px] text-muted-foreground">·</span>
              <span className="text-[10px] font-medium text-foreground">{error.agentName}</span>
              {error.gateLabel && (
                <>
                  <span className="text-[10px] text-muted-foreground">·</span>
                  <span className="text-[10px] text-muted-foreground">{error.gateLabel}</span>
                </>
              )}
            </div>
            <p className="text-xs text-foreground mt-1">{error.message}</p>
            <p className="text-[10px] text-muted-foreground mt-0.5">{cfg.hint}</p>
          </div>
          <div className="text-right flex-shrink-0">
            <time className="text-[10px] text-muted-foreground" dateTime={error.timestamp}>
              {dt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
            </time>
            <div className="text-[10px] text-muted-foreground mt-0.5">
              Attempt {error.attempt}/{error.maxAttempts}
            </div>
          </div>
        </div>

        {/* Stats row */}
        <div className="px-4 py-2.5 flex items-center gap-4 flex-wrap">
          <div>
            <span className="text-[11px] font-bold text-[#B45309]">{retriesLeft}</span>
            <span className="text-[10px] text-muted-foreground ml-1">retries left</span>
          </div>
          {error.sriImpact !== undefined && (
            <div>
              <span className="text-[11px] font-bold text-destructive">−{Math.abs(error.sriImpact)}</span>
              <span className="text-[10px] text-muted-foreground ml-1">SRI impact</span>
            </div>
          )}
          {history.length > 0 && (
            <div>
              <span className="text-[11px] font-bold text-muted-foreground">{history.length}</span>
              <span className="text-[10px] text-muted-foreground ml-1">prior failures</span>
            </div>
          )}
          {autoRetryAfter > 0 && (
            <Countdown seconds={autoRetryAfter} onComplete={() => handleAction("retry")} />
          )}
          {error.detail && (
            <button
              onClick={() => setShowDetail(d => !d)}
              className="ml-auto text-[10px] text-[#005EA2] hover:underline font-medium"
            >
              {showDetail ? "Hide" : "Show"} diagnostics
            </button>
          )}
        </div>

        {/* Diagnostic detail */}
        {showDetail && error.detail && (
          <div className="px-4 pb-3 border-t border-border/50">
            <pre className="mt-2 text-[10px] font-mono text-muted-foreground bg-muted/40 rounded p-3 overflow-x-auto whitespace-pre-wrap break-all">
              {error.detail}
            </pre>
          </div>
        )}
      </div>

      {/* Recovery actions */}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {(["retry", "skip", "fallback", "escalate"] as RecoveryAction[]).map(act => {
          const rcfg = RECOVERY_CONFIG[act];
          const disabled = act === "retry" && retriesLeft <= 0;
          return (
            <button
              key={act}
              onClick={() => handleAction(act)}
              disabled={disabled}
              className={cn(
                "px-3 py-2.5 rounded-lg border text-left transition-colors",
                recoveryBtnClass(rcfg.variant),
                disabled && "opacity-40 cursor-not-allowed",
              )}
            >
              <div className="text-[11px] font-bold">{rcfg.label}</div>
              <div className="text-[9px] opacity-70 mt-0.5 leading-tight">{rcfg.desc}</div>
            </button>
          );
        })}
      </div>

      {/* Error history */}
      {history.length > 0 && (
        <div className="rounded-lg border border-border bg-muted/20 px-4 py-3">
          <p className="text-[11px] font-medium text-foreground mb-2">Error History</p>
          <div className="space-y-1.5">
            {history.slice(-4).map(h => {
              const hcfg = ERR_CONFIG[h.category];
              const hdt  = new Date(h.timestamp);
              return (
                <div key={h.id} className="flex items-center gap-2 text-[10px]">
                  <span className={hcfg.text}>{hcfg.icon}</span>
                  <span className="text-muted-foreground font-mono">
                    {hdt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  </span>
                  <span className={cn("font-medium", hcfg.text)}>{hcfg.label}</span>
                  <span className="text-foreground truncate flex-1">{h.message}</span>
                  {h.resolved && <span className="text-[#1A7F4B]">✓</span>}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
