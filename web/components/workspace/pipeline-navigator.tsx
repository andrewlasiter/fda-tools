"use client";

/**
 * FDA-240 — PipelineNavigator
 * Left-sidebar 12-stage NPD stepper.  Clicking a stage emits onStageChange.
 * Completed stages show a check; the active stage is highlighted with the
 * FDA-Blue primary colour; future stages are muted.
 */

import * as React from "react";
import { CheckCircle2, Circle, Lock } from "lucide-react";
import { cn } from "@/lib/utils";
import type { NpdStage } from "@/lib/api-client";

// ── Stage metadata ────────────────────────────────────────────────────────────

export interface StageInfo {
  stage: NpdStage;
  label: string;
  shortLabel: string;
  description: string;
}

export const NPD_STAGES: StageInfo[] = [
  { stage: "CONCEPT",     label: "Concept",          shortLabel: "Concept",    description: "Define device concept and initial requirements" },
  { stage: "CLASSIFY",    label: "Classification",   shortLabel: "Classify",   description: "Determine device class and regulatory pathway" },
  { stage: "PREDICATE",   label: "Predicate Search", shortLabel: "Predicate",  description: "Identify predicate devices and SE basis" },
  { stage: "PATHWAY",     label: "Pathway",          shortLabel: "Pathway",    description: "Confirm 510(k), De Novo, or PMA pathway" },
  { stage: "PRESUB",      label: "Pre-Submission",   shortLabel: "PreSub",     description: "Q-Sub meeting or pre-submission feedback" },
  { stage: "TESTING",     label: "Testing",          shortLabel: "Testing",    description: "Biocompat, electrical safety, and bench testing" },
  { stage: "DRAFTING",    label: "Drafting",         shortLabel: "Drafting",   description: "Author submission sections with AI assistance" },
  { stage: "REVIEW",      label: "Internal Review",  shortLabel: "Review",     description: "RA and QA review of complete package" },
  { stage: "SUBMIT",      label: "Submit",           shortLabel: "Submit",     description: "eSTAR submission and CDRH receipt" },
  { stage: "FDA_REVIEW",  label: "FDA Review",       shortLabel: "FDA",        description: "Interactive review and AI/DI queries" },
  { stage: "CLEARED",     label: "Cleared",          shortLabel: "Cleared",    description: "510(k) clearance — post-market planning" },
  { stage: "POST_MARKET", label: "Post-Market",      shortLabel: "Post-Mkt",   description: "MDR, PMS, and annual reports" },
];

// ── Stage ordering for progress comparison ───────────────────────────────────

const STAGE_ORDER: Record<NpdStage, number> = Object.fromEntries(
  NPD_STAGES.map((s, i) => [s.stage, i]),
) as Record<NpdStage, number>;

function stageStatus(
  stage: NpdStage,
  currentStage: NpdStage,
): "done" | "active" | "upcoming" {
  const stageIdx   = STAGE_ORDER[stage];
  const currentIdx = STAGE_ORDER[currentStage];
  if (stageIdx < currentIdx)  return "done";
  if (stageIdx === currentIdx) return "active";
  return "upcoming";
}

// ── Props ─────────────────────────────────────────────────────────────────────

interface PipelineNavigatorProps {
  currentStage: NpdStage;
  selectedStage: NpdStage;
  onStageChange: (stage: NpdStage) => void;
  /** Percentage complete per stage — provided by backend in later sprints */
  stageProgress?: Partial<Record<NpdStage, number>>;
  className?: string;
}

// ── Component ─────────────────────────────────────────────────────────────────

export function PipelineNavigator({
  currentStage,
  selectedStage,
  onStageChange,
  stageProgress = {},
  className,
}: PipelineNavigatorProps) {
  return (
    <nav
      aria-label="NPD Pipeline stages"
      className={cn("flex flex-col gap-0.5 py-4", className)}
    >
      {NPD_STAGES.map((info, idx) => {
        const status   = stageStatus(info.stage, currentStage);
        const isActive = info.stage === selectedStage;
        const progress = stageProgress[info.stage] ?? 0;

        return (
          <button
            key={info.stage}
            onClick={() => onStageChange(info.stage)}
            aria-current={isActive ? "step" : undefined}
            className={cn(
              "group relative flex items-center gap-3 rounded-lg px-3 py-2.5 text-left transition-colors",
              isActive
                ? "bg-primary/10 text-primary"
                : "text-muted-foreground hover:bg-muted hover:text-foreground",
            )}
          >
            {/* Connector line (not for last item) */}
            {idx < NPD_STAGES.length - 1 && (
              <span
                aria-hidden
                className={cn(
                  "absolute left-[21px] top-[36px] w-px h-4",
                  status === "done" ? "bg-primary/40" : "bg-border",
                )}
              />
            )}

            {/* Stage icon */}
            <span className="flex-shrink-0 mt-0.5">
              {status === "done" ? (
                <CheckCircle2 className="w-4 h-4 text-primary" />
              ) : status === "active" ? (
                <Circle className="w-4 h-4 fill-primary text-primary" />
              ) : (
                <Circle className="w-4 h-4" />
              )}
            </span>

            {/* Label */}
            <span className="flex-1 min-w-0">
              <span className={cn(
                "block text-xs font-medium truncate",
                isActive && "font-semibold text-primary",
                status === "done" && "text-foreground/70",
              )}>
                {info.label}
              </span>

              {/* Progress bar for in-progress stages */}
              {status !== "upcoming" && progress > 0 && progress < 100 && (
                <span className="block mt-1 h-1 w-full rounded-full bg-muted overflow-hidden">
                  <span
                    className="block h-full rounded-full bg-primary/60 transition-all"
                    style={{ width: `${progress}%` }}
                  />
                </span>
              )}
            </span>

            {/* Lock for future stages */}
            {status === "upcoming" && (
              <Lock className="w-3 h-3 opacity-30 flex-shrink-0" aria-hidden />
            )}
          </button>
        );
      })}
    </nav>
  );
}
