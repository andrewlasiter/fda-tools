"use client";

/**
 * FDA-240 — StageContent
 * Main content panel of the NPD Workspace.  Renders stage-specific UI:
 * - Wizard mode: guided prompts, checklists, next-step CTAs
 * - Power mode:  raw agent output, command panel, all project data visible
 *
 * Content per stage will be populated by backend agents in Sprint 5+.
 * For now the panel shows the stage-appropriate placeholder, checklist,
 * and any existing project data passed via props.
 */

import * as React from "react";
import {
  ChevronRight,
  ChevronLeft,
  FlaskConical,
  FileSearch,
  Target,
  Map,
  MessageSquare,
  TestTube2,
  PenLine,
  CheckSquare,
  Upload,
  Building2,
  PartyPopper,
  BarChart3,
  Wand2,
  Terminal,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import type { NpdStage, Project } from "@/lib/api-client";
import { NPD_STAGES, type StageInfo } from "./pipeline-navigator";

// ── Stage icon map ────────────────────────────────────────────────────────────

const STAGE_ICONS: Record<NpdStage, React.ElementType> = {
  CONCEPT:     FlaskConical,
  CLASSIFY:    FileSearch,
  PREDICATE:   Target,
  PATHWAY:     Map,
  PRESUB:      MessageSquare,
  TESTING:     TestTube2,
  DRAFTING:    PenLine,
  REVIEW:      CheckSquare,
  SUBMIT:      Upload,
  FDA_REVIEW:  Building2,
  CLEARED:     PartyPopper,
  POST_MARKET: BarChart3,
};

// ── Checklist items per stage ─────────────────────────────────────────────────

const STAGE_CHECKLIST: Partial<Record<NpdStage, string[]>> = {
  CONCEPT: [
    "Define intended use and indications for use",
    "Identify target patient population",
    "Draft initial design inputs list",
    "Assess competitive landscape",
  ],
  CLASSIFY: [
    "Determine device class (I, II, III)",
    "Identify applicable CFR part",
    "Check product code via FDA Device Classification database",
    "Confirm regulatory pathway",
  ],
  PREDICATE: [
    "Search FDA 510(k) database for predicates",
    "Evaluate substantial equivalence criteria",
    "Document technology comparison",
    "Build SE comparison table",
  ],
  PATHWAY: [
    "Confirm 510(k) / De Novo / PMA pathway",
    "Identify applicable guidance documents",
    "Review similar cleared devices",
    "Plan pre-submission meeting if needed",
  ],
  PRESUB: [
    "Draft Q-Sub questions",
    "Schedule pre-submission meeting",
    "Prepare device overview slides",
    "Document FDA feedback",
  ],
  TESTING: [
    "Identify required standards (IEC, ISO, ASTM)",
    "Plan biocompatibility per ISO 10993-1",
    "Design electrical safety testing (IEC 60601)",
    "Schedule testing lab",
  ],
  DRAFTING: [
    "Complete 510(k) Summary (Section 01)",
    "Draft Substantial Equivalence (Section 09)",
    "Write Device Description (Section 10)",
    "Compile Performance Testing (Section 14)",
  ],
  REVIEW: [
    "RA lead review of all 21 sections",
    "QA sign-off on test reports",
    "Legal review of labeling",
    "Run consistency check",
  ],
  SUBMIT: [
    "Assemble eSTAR package",
    "Validate all section IDs",
    "Submit via FDA eSTAR portal",
    "Record submission date and tracking number",
  ],
  FDA_REVIEW: [
    "Monitor FDA acknowledgment letter",
    "Respond to Additional Information (AI) requests",
    "Track review clock days",
    "Prepare deficiency response drafts",
  ],
  CLEARED: [
    "Review clearance letter and clearance order",
    "Update labeling per clearance conditions",
    "Issue press release / customer notification",
    "Update PMS plan",
  ],
  POST_MARKET: [
    "File MDRs within required timeframes",
    "Conduct periodic safety reviews",
    "Track complaints and CAPAs",
    "Submit Annual Reports",
  ],
};

// ── Props ─────────────────────────────────────────────────────────────────────

interface StageContentProps {
  stage: NpdStage;
  project: Project | null;
  wizardMode: boolean;
  onWizardToggle: () => void;
  onNextStage: () => void;
  onPrevStage: () => void;
  isFirst: boolean;
  isLast: boolean;
  className?: string;
}

// ── Component ─────────────────────────────────────────────────────────────────

export function StageContent({
  stage,
  project,
  wizardMode,
  onWizardToggle,
  onNextStage,
  onPrevStage,
  isFirst,
  isLast,
  className,
}: StageContentProps) {
  const stageInfo  = NPD_STAGES.find((s) => s.stage === stage) as StageInfo;
  const Icon       = STAGE_ICONS[stage];
  const checklist  = STAGE_CHECKLIST[stage] ?? [];

  const [checked, setChecked] = React.useState<Set<number>>(new Set());

  function toggleCheck(idx: number) {
    setChecked((prev) => {
      const next = new Set(prev);
      next.has(idx) ? next.delete(idx) : next.add(idx);
      return next;
    });
  }

  return (
    <div className={cn("flex flex-col gap-6 h-full overflow-y-auto p-6", className)}>
      {/* Stage header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="flex-shrink-0 w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
            <Icon className="w-5 h-5 text-primary" />
          </div>
          <div>
            <h2 className="text-xl font-heading font-bold text-foreground">
              {stageInfo.label}
            </h2>
            <p className="text-sm text-muted-foreground">{stageInfo.description}</p>
          </div>
        </div>

        {/* Mode toggle */}
        <button
          onClick={onWizardToggle}
          className="flex items-center gap-1.5 rounded-full border border-border px-3 py-1.5 text-xs font-medium hover:bg-muted transition-colors flex-shrink-0"
          title={wizardMode ? "Switch to Power Mode" : "Switch to Wizard Mode"}
        >
          {wizardMode ? (
            <>
              <Wand2 className="w-3.5 h-3.5 text-primary" />
              Wizard
            </>
          ) : (
            <>
              <Terminal className="w-3.5 h-3.5 text-muted-foreground" />
              Power
            </>
          )}
        </button>
      </div>

      {/* Wizard mode: guided checklist */}
      {wizardMode && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Stage Checklist</CardTitle>
            <CardDescription>
              Complete these items before advancing to the next stage
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="space-y-3">
              {checklist.map((item, idx) => (
                <li
                  key={idx}
                  className="flex items-start gap-3 cursor-pointer group"
                  onClick={() => toggleCheck(idx)}
                >
                  <span
                    className={cn(
                      "flex-shrink-0 mt-0.5 w-5 h-5 rounded border-2 flex items-center justify-center transition-colors",
                      checked.has(idx)
                        ? "bg-primary border-primary"
                        : "border-muted-foreground/40 group-hover:border-primary/60",
                    )}
                    aria-hidden
                  >
                    {checked.has(idx) && (
                      <svg
                        className="w-3 h-3 text-primary-foreground"
                        fill="none"
                        viewBox="0 0 12 12"
                        stroke="currentColor"
                        strokeWidth={2.5}
                      >
                        <polyline points="2,6 5,9 10,3" />
                      </svg>
                    )}
                  </span>
                  <span
                    className={cn(
                      "text-sm leading-relaxed",
                      checked.has(idx)
                        ? "line-through text-muted-foreground"
                        : "text-foreground",
                    )}
                  >
                    {item}
                  </span>
                </li>
              ))}
            </ul>

            {/* Progress indicator */}
            {checklist.length > 0 && (
              <div className="mt-4 flex items-center gap-3">
                <div className="flex-1 h-2 rounded-full bg-muted overflow-hidden">
                  <div
                    className="h-full rounded-full bg-primary transition-all"
                    style={{ width: `${(checked.size / checklist.length) * 100}%` }}
                  />
                </div>
                <span className="text-xs text-muted-foreground w-14 text-right">
                  {checked.size}/{checklist.length}
                </span>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Power mode: raw project data */}
      {!wizardMode && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Terminal className="w-4 h-4" />
              Project Data — {stage}
            </CardTitle>
            <CardDescription>
              Raw project state for this stage. Agent outputs appear here as they run.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {project ? (
              <pre className="text-xs bg-muted rounded-lg p-4 overflow-auto max-h-64 text-muted-foreground">
                {JSON.stringify(
                  {
                    id:           project.id,
                    name:         project.name,
                    stage:        project.stage,
                    product_code: project.product_code,
                    sri_score:    project.sri_score,
                    updated_at:   project.updated_at,
                  },
                  null,
                  2,
                )}
              </pre>
            ) : (
              <div className="flex items-center gap-2 text-sm text-muted-foreground py-4">
                <Loader2 className="w-4 h-4 animate-spin" />
                Loading project data…
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Agent output placeholder (Sprint 5+ fills this) */}
      <Card className="flex-1 min-h-[200px]">
        <CardHeader>
          <CardTitle className="text-base">Agent Output</CardTitle>
          <CardDescription>
            AI-generated content for this stage will appear here
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-10 text-center">
            <FlaskConical className="w-10 h-10 text-muted-foreground/30 mb-3" />
            <p className="text-sm text-muted-foreground">
              No output yet. Run an agent to generate content for this stage.
            </p>
            <Button variant="outline" size="sm" className="mt-4" disabled>
              <Loader2 className="w-3.5 h-3.5 mr-1.5 opacity-50" />
              Run Agent (Sprint 5)
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Navigation buttons */}
      <div className="flex items-center justify-between pt-2">
        <Button
          variant="outline"
          size="sm"
          onClick={onPrevStage}
          disabled={isFirst}
        >
          <ChevronLeft className="w-4 h-4 mr-1" />
          Previous
        </Button>
        <Button
          size="sm"
          onClick={onNextStage}
          disabled={isLast}
        >
          Next
          <ChevronRight className="w-4 h-4 ml-1" />
        </Button>
      </div>
    </div>
  );
}
