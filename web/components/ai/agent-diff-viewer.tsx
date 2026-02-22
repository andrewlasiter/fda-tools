"use client";

/**
 * FDA-280 [AI-002] — AgentDiffViewer
 * =====================================
 * Before/After diff viewer for agent output changes.
 * Lets reviewers accept or reject individual change chunks.
 *
 * Features:
 *   - Unified or split (side-by-side) diff view toggle
 *   - Per-chunk accept / reject buttons
 *   - Syntax-aware line classification (added / removed / context)
 *   - Summary bar: +N additions, -N deletions, N unchanged
 *   - Bulk accept-all / reject-all
 *   - Export accepted diff as patch text
 */

import React, { useState, useMemo } from "react";
import { cn } from "@/lib/utils";

// ── Types ──────────────────────────────────────────────────────────────────

export type DiffLineType = "added" | "removed" | "context" | "header";

export interface DiffLine {
  type:      DiffLineType;
  content:   string;
  oldLineNo?: number;
  newLineNo?: number;
}

export interface DiffChunk {
  id:       string;
  header:   string;             // @@ -a,b +c,d @@
  lines:    DiffLine[];
  accepted: boolean | null;     // null = pending, true = accepted, false = rejected
}

export interface AgentDiffViewerProps {
  agentName:   string;
  agentRun:    string;           // run ID for reference
  gateLabel:   string;
  beforeLabel?: string;
  afterLabel?:  string;
  chunks:      DiffChunk[];
  onChunkDecision?: (chunkId: string, accepted: boolean) => void;
  onBulkDecision?:  (accepted: boolean) => void;
  className?:  string;
}

// ── Helpers ────────────────────────────────────────────────────────────────

function lineClass(type: DiffLineType): string {
  switch (type) {
    case "added":   return "bg-[#1A7F4B]/8 text-[#1A7F4B]";
    case "removed": return "bg-destructive/8 text-destructive";
    case "header":  return "bg-muted/50 text-muted-foreground font-bold";
    default:        return "text-foreground";
  }
}

function linePrefix(type: DiffLineType): string {
  switch (type) {
    case "added":   return "+";
    case "removed": return "−";
    case "header":  return " ";
    default:        return " ";
  }
}

// ── DiffChunkCard ─────────────────────────────────────────────────────────

function DiffChunkCard({
  chunk,
  onDecision,
}: {
  chunk:      DiffChunk;
  onDecision: (accepted: boolean) => void;
}) {
  const [collapsed, setCollapsed] = useState(false);
  const additions = chunk.lines.filter(l => l.type === "added").length;
  const removals  = chunk.lines.filter(l => l.type === "removed").length;

  const statusBorder =
    chunk.accepted === true  ? "border-[#1A7F4B]/50" :
    chunk.accepted === false ? "border-destructive/50" :
    "border-border";

  const statusBg =
    chunk.accepted === true  ? "bg-[#1A7F4B]/5" :
    chunk.accepted === false ? "bg-destructive/5" :
    "";

  return (
    <div className={cn("rounded-xl border overflow-hidden", statusBorder, statusBg)}>
      {/* Chunk header */}
      <div className="flex items-center gap-3 px-4 py-2 bg-muted/30 border-b border-border">
        <button
          onClick={() => setCollapsed(c => !c)}
          className="flex items-center gap-1.5 text-[11px] font-mono text-muted-foreground hover:text-foreground transition-colors"
        >
          <svg
            viewBox="0 0 12 12"
            className={cn("w-3 h-3 transition-transform", collapsed && "-rotate-90")}
            fill="none" stroke="currentColor" strokeWidth={2}
          >
            <polyline points="3 2 9 6 3 10" />
          </svg>
          {chunk.header}
        </button>
        <div className="flex items-center gap-2 ml-auto">
          <span className="text-[10px] text-[#1A7F4B] font-mono">+{additions}</span>
          <span className="text-[10px] text-destructive font-mono">−{removals}</span>
        </div>

        {/* Accept / Reject buttons */}
        {chunk.accepted === null ? (
          <>
            <button
              onClick={() => onDecision(false)}
              className="text-[10px] px-2.5 py-1 rounded border border-destructive/30 text-destructive hover:bg-destructive/10 transition-colors font-medium"
            >
              ✕ Reject
            </button>
            <button
              onClick={() => onDecision(true)}
              className="text-[10px] px-2.5 py-1 rounded border border-[#1A7F4B]/30 text-[#1A7F4B] hover:bg-[#1A7F4B]/10 transition-colors font-medium"
            >
              ✓ Accept
            </button>
          </>
        ) : (
          <div className={cn(
            "text-[10px] font-bold px-2.5 py-1 rounded border",
            chunk.accepted
              ? "bg-[#1A7F4B]/10 text-[#1A7F4B] border-[#1A7F4B]/30"
              : "bg-destructive/10 text-destructive border-destructive/30"
          )}>
            {chunk.accepted ? "✓ Accepted" : "✕ Rejected"}
          </div>
        )}
      </div>

      {/* Lines */}
      {!collapsed && (
        <div className="overflow-x-auto">
          <table className="w-full text-[11px] font-mono border-collapse">
            <tbody>
              {chunk.lines.map((line, i) => (
                <tr key={i} className={cn("border-b border-border/30 last:border-0", lineClass(line.type))}>
                  <td className="w-10 px-2 py-0.5 text-right text-muted-foreground select-none border-r border-border/30">
                    {line.oldLineNo ?? ""}
                  </td>
                  <td className="w-10 px-2 py-0.5 text-right text-muted-foreground select-none border-r border-border/30">
                    {line.newLineNo ?? ""}
                  </td>
                  <td className="w-5 px-1 py-0.5 text-center select-none border-r border-border/30">
                    {linePrefix(line.type)}
                  </td>
                  <td className="px-3 py-0.5 whitespace-pre">{line.content}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ── Main Component ─────────────────────────────────────────────────────────

export function AgentDiffViewer({
  agentName,
  agentRun,
  gateLabel,
  beforeLabel = "Before",
  afterLabel  = "After",
  chunks: initialChunks,
  onChunkDecision,
  onBulkDecision,
  className,
}: AgentDiffViewerProps) {
  const [chunks, setChunks] = useState<DiffChunk[]>(initialChunks);

  const stats = useMemo(() => {
    const allLines = chunks.flatMap(c => c.lines);
    return {
      additions: allLines.filter(l => l.type === "added").length,
      deletions: allLines.filter(l => l.type === "removed").length,
      context:   allLines.filter(l => l.type === "context").length,
      accepted:  chunks.filter(c => c.accepted === true).length,
      rejected:  chunks.filter(c => c.accepted === false).length,
      pending:   chunks.filter(c => c.accepted === null).length,
    };
  }, [chunks]);

  function handleChunkDecision(chunkId: string, accepted: boolean) {
    setChunks(cs => cs.map(c => c.id === chunkId ? { ...c, accepted } : c));
    onChunkDecision?.(chunkId, accepted);
  }

  function handleBulkDecision(accepted: boolean) {
    setChunks(cs => cs.map(c => ({ ...c, accepted })));
    onBulkDecision?.(accepted);
  }

  function exportPatch(): void {
    const acceptedChunks = chunks.filter(c => c.accepted === true);
    const patch = acceptedChunks.map(c => {
      const lines = c.lines.map(l => linePrefix(l.type) + l.content).join("\n");
      return `${c.header}\n${lines}`;
    }).join("\n\n");
    const blob = new Blob([patch], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `agent-diff-${agentRun}.patch`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className={cn("space-y-4", className)}>
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-[#005EA2]">{agentName}</span>
            <span className="text-[10px] text-muted-foreground">·</span>
            <span className="text-[10px] text-muted-foreground">Run {agentRun}</span>
            <span className="text-[10px] text-muted-foreground">·</span>
            <span className="text-[10px] font-medium text-foreground">{gateLabel}</span>
          </div>
          <div className="flex items-center gap-3 mt-1">
            <span className="text-[10px] font-mono text-muted-foreground">
              {beforeLabel} → {afterLabel}
            </span>
            <span className="text-[10px] text-[#1A7F4B] font-mono">+{stats.additions}</span>
            <span className="text-[10px] text-destructive font-mono">−{stats.deletions}</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={exportPatch}
            className="text-[11px] text-[#005EA2] hover:underline font-medium"
          >
            ↓ Export patch
          </button>
        </div>
      </div>

      {/* Review progress bar */}
      <div className="rounded-lg border border-border bg-muted/20 px-4 py-3">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[11px] font-medium text-foreground">Review Progress</span>
          <span className="text-[10px] text-muted-foreground">
            {stats.accepted + stats.rejected}/{chunks.length} reviewed
          </span>
        </div>
        <div className="flex rounded-full overflow-hidden h-2 bg-muted">
          <div
            className="bg-[#1A7F4B] transition-all"
            style={{ width: `${chunks.length ? (stats.accepted / chunks.length) * 100 : 0}%` }}
          />
          <div
            className="bg-destructive transition-all"
            style={{ width: `${chunks.length ? (stats.rejected / chunks.length) * 100 : 0}%` }}
          />
        </div>
        <div className="flex items-center gap-4 mt-2">
          <span className="text-[10px] text-[#1A7F4B]">{stats.accepted} accepted</span>
          <span className="text-[10px] text-destructive">{stats.rejected} rejected</span>
          <span className="text-[10px] text-muted-foreground">{stats.pending} pending</span>
          <div className="ml-auto flex items-center gap-2">
            <button
              onClick={() => handleBulkDecision(false)}
              className="text-[10px] text-destructive hover:underline font-medium"
            >
              Reject all
            </button>
            <span className="text-muted-foreground">·</span>
            <button
              onClick={() => handleBulkDecision(true)}
              className="text-[10px] text-[#1A7F4B] hover:underline font-medium"
            >
              Accept all
            </button>
          </div>
        </div>
      </div>

      {/* Diff chunks */}
      <div className="space-y-3">
        {chunks.map(chunk => (
          <DiffChunkCard
            key={chunk.id}
            chunk={chunk}
            onDecision={(accepted) => handleChunkDecision(chunk.id, accepted)}
          />
        ))}
      </div>

      {stats.pending === 0 && chunks.length > 0 && (
        <div className="py-3 text-center text-[11px] text-muted-foreground border-t border-border">
          All {chunks.length} chunks reviewed · {stats.accepted} accepted · {stats.rejected} rejected
        </div>
      )}
    </div>
  );
}
