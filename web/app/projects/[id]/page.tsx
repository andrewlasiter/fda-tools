"use client";

/**
 * FDA-240 — NPD Workspace  /projects/[id]
 *
 * 3-panel layout:
 *  ┌─────────────────────────────────────────────────────────┐
 *  │ [PipelineNavigator 200px] │ [StageContent flex-1] │ [AI] │
 *  └─────────────────────────────────────────────────────────┘
 *
 * State:
 * - selectedStage: the stage currently visible in the main panel (may differ
 *   from project.stage which represents the *current* NPD progress stage)
 * - wizardMode: Wizard (guided checklist) vs Power (raw data)
 *
 * The right AI panel collapses on mobile/small viewports.
 */

import * as React from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { useProject } from "@/lib/api-client";
import type { NpdStage } from "@/lib/api-client";
import { PipelineNavigator, NPD_STAGES } from "@/components/workspace/pipeline-navigator";
import { StageContent } from "@/components/workspace/stage-content";
import { AIAssistantPanel } from "@/components/workspace/ai-assistant-panel";
import { SRIScoreRing } from "@/components/ui/sri-score-ring";

export default function ProjectWorkspacePage() {
  const params   = useParams();
  const router   = useRouter();
  const projectId = typeof params.id === "string" ? params.id : "";

  const { data: projectData, isLoading } = useProject(projectId);
  const project = projectData ?? null;

  // Selected stage defaults to the project's current stage once loaded
  const [selectedStage, setSelectedStage] = React.useState<NpdStage>("CONCEPT");
  const [wizardMode, setWizardMode]       = React.useState(true);

  // Sync selectedStage to the project's current stage on first load
  React.useEffect(() => {
    if (project?.stage) {
      setSelectedStage(project.stage as NpdStage);
    }
  }, [project?.stage]);

  const stageIdx   = NPD_STAGES.findIndex((s) => s.stage === selectedStage);
  const isFirst    = stageIdx === 0;
  const isLast     = stageIdx === NPD_STAGES.length - 1;

  function goNext() {
    if (!isLast) setSelectedStage(NPD_STAGES[stageIdx + 1].stage);
  }

  function goPrev() {
    if (!isFirst) setSelectedStage(NPD_STAGES[stageIdx - 1].stage);
  }

  // ── Loading skeleton ─────────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-48 rounded bg-muted animate-pulse" />
          <div className="h-4 w-32 rounded bg-muted animate-pulse" />
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Top bar */}
      <header className="flex items-center justify-between gap-4 px-4 py-3 border-b border-border bg-background/90 backdrop-blur supports-[backdrop-filter]:bg-background/60 flex-shrink-0">
        <div className="flex items-center gap-3 min-w-0">
          <Link
            href="/dashboard"
            className="p-1 rounded hover:bg-muted transition-colors flex-shrink-0"
            title="Back to Dashboard"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div className="min-w-0">
            <h1 className="font-heading font-semibold text-foreground truncate text-sm sm:text-base">
              {project?.name ?? projectId}
            </h1>
            {project?.product_code && (
              <p className="text-xs text-muted-foreground">
                Product code: {project.product_code}
              </p>
            )}
          </div>
        </div>

        <div className="flex items-center gap-3 flex-shrink-0">
          {project && (
            <SRIScoreRing
              score={project.sri_score}
              size={40}
              strokeWidth={4}
              showLabel={false}
            />
          )}
        </div>
      </header>

      {/* 3-panel body */}
      <div className="flex flex-1 min-h-0 overflow-hidden">
        {/* Left: Pipeline navigator */}
        <aside className="hidden md:flex flex-col w-52 flex-shrink-0 border-r border-border bg-background overflow-y-auto">
          <PipelineNavigator
            currentStage={(project?.stage as NpdStage | undefined) ?? "CONCEPT"}
            selectedStage={selectedStage}
            onStageChange={setSelectedStage}
          />
        </aside>

        {/* Center: Stage content */}
        <main className="flex-1 min-w-0 overflow-hidden bg-muted/20">
          <StageContent
            stage={selectedStage}
            project={project}
            wizardMode={wizardMode}
            onWizardToggle={() => setWizardMode((m) => !m)}
            onNextStage={goNext}
            onPrevStage={goPrev}
            isFirst={isFirst}
            isLast={isLast}
          />
        </main>

        {/* Right: AI assistant */}
        <AIAssistantPanel
          stage={selectedStage}
          projectName={project?.name}
          className="hidden lg:flex flex-col w-72 flex-shrink-0"
        />
      </div>
    </div>
  );
}
