"use client";

/**
 * FDA-279 [AI-001] — TrustBadge
 * ================================
 * Universal AI output trust indicator. Attaches to any AI-generated content
 * to show: confidence score, source count, model used, last validated time.
 *
 * Variants:
 *   full    — Score + label + sources + verify button (default)
 *   compact — Score badge only (for dense tables)
 *   icon    — Shield icon only with tooltip (for very dense views)
 */

import React, { useState } from "react";
import { cn } from "@/lib/utils";

// ── Types ─────────────────────────────────────────────────────────────────

export interface TrustData {
  confidence:    number;        // 0–100
  sourceCount?:  number;
  modelId?:      string;        // e.g. "claude-opus-4-6"
  validatedAt?:  string;        // ISO timestamp
  sources?:      TrustSource[];
}

export interface TrustSource {
  label:    string;
  type:     "510k" | "guidance" | "standard" | "maude" | "pubmed" | "manual";
  section?: string;
  quote?:   string;
}

type TrustVariant = "full" | "compact" | "icon";

interface TrustBadgeProps {
  trust:      TrustData;
  variant?:   TrustVariant;
  onVerify?:  () => void;
  className?: string;
}

// ── Helpers ───────────────────────────────────────────────────────────────

function confidenceColor(score: number): string {
  if (score >= 90) return "text-[#1A7F4B]";
  if (score >= 70) return "text-[#B45309]";
  return "text-destructive";
}

function confidenceBg(score: number): string {
  if (score >= 90) return "bg-[#1A7F4B]/10 border-[#1A7F4B]/25";
  if (score >= 70) return "bg-[#B45309]/10 border-[#B45309]/25";
  return "bg-destructive/10 border-destructive/25";
}

function confidenceLabel(score: number): string {
  if (score >= 90) return "High Confidence";
  if (score >= 70) return "Moderate";
  return "Low — Verify";
}

function ShieldIcon({ score, className }: { score: number; className?: string }) {
  const color = score >= 90 ? "#1A7F4B" : score >= 70 ? "#B45309" : "#C5191B";
  return (
    <svg viewBox="0 0 20 20" className={className} fill="none">
      <path
        d="M10 2L3 5.5v5c0 4.25 3 7.5 7 8.5 4-1 7-4.25 7-8.5v-5L10 2Z"
        fill={color}
        fillOpacity="0.15"
        stroke={color}
        strokeWidth="1.25"
        strokeLinejoin="round"
      />
      {score >= 70 && (
        <path
          d="M7 10l2 2 4-4"
          stroke={color}
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      )}
      {score < 70 && (
        <path
          d="M10 7v3M10 12.5h.01"
          stroke={color}
          strokeWidth="1.5"
          strokeLinecap="round"
        />
      )}
    </svg>
  );
}

// ── Source type label map ─────────────────────────────────────────────────

const SOURCE_LABELS: Record<TrustSource["type"], string> = {
  "510k":     "510(k)",
  guidance:   "Guidance",
  standard:   "Standard",
  maude:      "MAUDE",
  pubmed:     "PubMed",
  manual:     "Manual",
};

const SOURCE_COLORS: Record<TrustSource["type"], string> = {
  "510k":     "text-[#005EA2]  bg-[#005EA2]/10",
  guidance:   "text-[#1A7F4B]  bg-[#1A7F4B]/10",
  standard:   "text-purple-600 bg-purple-100 dark:text-purple-300 dark:bg-purple-900/30",
  maude:      "text-[#B45309]  bg-[#B45309]/10",
  pubmed:     "text-pink-600   bg-pink-100   dark:text-pink-300 dark:bg-pink-900/30",
  manual:     "text-foreground bg-muted",
};

// ── Components ────────────────────────────────────────────────────────────

function SourcePill({ source }: { source: TrustSource }) {
  return (
    <span className={cn("inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-bold", SOURCE_COLORS[source.type])}>
      {SOURCE_LABELS[source.type]}
    </span>
  );
}

// ── Main export ───────────────────────────────────────────────────────────

export function TrustBadge({ trust, variant = "full", onVerify, className }: TrustBadgeProps) {
  const [expanded, setExpanded] = useState(false);
  const { confidence, sourceCount, modelId, validatedAt, sources = [] } = trust;
  const count = sourceCount ?? sources.length;

  // ── Icon variant ──────────────────────────────────────────────────────
  if (variant === "icon") {
    return (
      <span
        title={`AI confidence: ${confidence}% · ${count} source${count !== 1 ? "s" : ""}`}
        className={cn("inline-flex items-center cursor-help", className)}
      >
        <ShieldIcon score={confidence} className="w-3.5 h-3.5" />
      </span>
    );
  }

  // ── Compact variant ───────────────────────────────────────────────────
  if (variant === "compact") {
    return (
      <span
        className={cn(
          "inline-flex items-center gap-1 px-1.5 py-0.5 rounded border text-[10px] font-bold cursor-pointer",
          "transition-all hover:shadow-sm",
          confidenceBg(confidence),
          confidenceColor(confidence),
          className
        )}
        onClick={() => setExpanded(e => !e)}
        title={`${confidence}% confidence · ${count} source${count !== 1 ? "s" : ""} · ${confidenceLabel(confidence)}`}
      >
        <ShieldIcon score={confidence} className="w-3 h-3" />
        {confidence}%
      </span>
    );
  }

  // ── Full variant ──────────────────────────────────────────────────────
  return (
    <div className={cn("space-y-1", className)}>
      <div
        className={cn(
          "inline-flex items-center gap-2 px-2.5 py-1.5 rounded-lg border text-xs font-medium cursor-pointer",
          "transition-all hover:shadow-md",
          confidenceBg(confidence)
        )}
        onClick={() => setExpanded(e => !e)}
      >
        <ShieldIcon score={confidence} className="w-4 h-4 flex-shrink-0" />
        <span className={confidenceColor(confidence)}>{confidence}% confidence</span>
        <span className="text-muted-foreground">·</span>
        <span className="text-muted-foreground">{count} source{count !== 1 ? "s" : ""}</span>
        {modelId && (
          <>
            <span className="text-muted-foreground">·</span>
            <span className="text-muted-foreground font-mono text-[9px]">{modelId.split("-").slice(-2).join("-")}</span>
          </>
        )}
        <svg
          viewBox="0 0 12 12"
          className={cn("w-3 h-3 text-muted-foreground transition-transform ml-auto", expanded && "rotate-180")}
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
        >
          <polyline points="2 4 6 8 10 4" />
        </svg>
      </div>

      {/* Expanded evidence panel */}
      {expanded && (
        <div className="rounded-lg border border-border bg-background shadow-lg p-3 space-y-3">
          {/* Confidence breakdown */}
          <div>
            <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground mb-1.5">
              Confidence Breakdown
            </p>
            <div className="h-2 bg-muted rounded-full overflow-hidden">
              <div
                className={cn(
                  "h-full rounded-full transition-all",
                  confidence >= 90 ? "bg-[#1A7F4B]" : confidence >= 70 ? "bg-[#B45309]" : "bg-destructive"
                )}
                style={{ width: `${confidence}%` }}
              />
            </div>
            <div className="flex justify-between text-[9px] text-muted-foreground mt-0.5">
              <span>0%</span>
              <span className={cn("font-bold", confidenceColor(confidence))}>{confidenceLabel(confidence)}</span>
              <span>100%</span>
            </div>
          </div>

          {/* Sources */}
          {sources.length > 0 && (
            <div>
              <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground mb-1.5">Sources</p>
              <div className="space-y-1.5">
                {sources.map((src, i) => (
                  <div key={i} className="flex items-start gap-2">
                    <SourcePill source={src} />
                    <div className="flex-1 min-w-0">
                      <p className="text-[10px] text-foreground">{src.label}</p>
                      {src.section && <p className="text-[9px] text-muted-foreground">{src.section}</p>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Footer */}
          <div className="flex items-center justify-between pt-1 border-t border-border">
            {validatedAt && (
              <p className="text-[9px] text-muted-foreground">
                Validated {new Date(validatedAt).toLocaleDateString()}
              </p>
            )}
            {onVerify && (
              <button
                onClick={onVerify}
                className="text-[10px] text-[#005EA2] hover:underline font-medium"
              >
                View full evidence chain →
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
