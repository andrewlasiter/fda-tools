"use client";

import * as React from "react";
import Link from "next/link";
import {
  Plus,
  Search,
  Activity,
  FlaskConical,
  Clock,
  ChevronRight,
  RefreshCw,
} from "lucide-react";
import { AreaChart } from "@tremor/react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { SRIScoreRing } from "@/components/ui/sri-score-ring";
import { AgentStatusChip, type AgentStatus } from "@/components/ui/agent-status-chip";
import { timeAgo } from "@/lib/utils";
import { useProjects, useAgents } from "@/lib/api-client";
import type { Project, AgentRun } from "@/lib/api-client";

// ── Stage badge ─────────────────────────────────────────────────────────────

const STAGE_COLORS: Record<string, string> = {
  CONCEPT:     "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
  CLASSIFY:    "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300",
  PREDICATE:   "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
  PATHWAY:     "bg-cyan-100 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-300",
  PRESUB:      "bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-300",
  TESTING:     "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300",
  DRAFTING:    "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300",
  REVIEW:      "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300",
  SUBMIT:      "bg-primary/10 text-primary dark:bg-primary/20",
  FDA_REVIEW:  "bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300",
  CLEARED:     "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300",
  POST_MARKET: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300",
};

function StageBadge({ stage }: { stage: string }) {
  const colorClass = STAGE_COLORS[stage] ?? "bg-slate-100 text-slate-700";
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${colorClass}`}>
      {stage.replace("_", " ")}
    </span>
  );
}

// ── Skeleton ─────────────────────────────────────────────────────────────────

function SkeletonCard() {
  return (
    <Card>
      <CardContent className="pt-4 pb-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 space-y-2">
            <div className="h-4 w-40 rounded bg-muted animate-pulse" />
            <div className="h-3 w-28 rounded bg-muted animate-pulse" />
          </div>
          <div className="h-14 w-14 rounded-full bg-muted animate-pulse" />
        </div>
      </CardContent>
    </Card>
  );
}

// ── SRI trend (static baseline — enhanced by backend in Sprint 4+) ────────────

const SRI_TREND = [
  { date: "Sep", SRI: 28 },
  { date: "Oct", SRI: 34 },
  { date: "Nov", SRI: 41 },
  { date: "Dec", SRI: 49 },
  { date: "Jan", SRI: 57 },
  { date: "Feb", SRI: 65 },
];

// ── Dashboard ─────────────────────────────────────────────────────────────────

export function DashboardContent() {
  const {
    data: projectsData,
    isLoading: projectsLoading,
    isError: projectsError,
    refetch: refetchProjects,
  } = useProjects();

  const {
    data: agentsData,
    isLoading: agentsLoading,
  } = useAgents();

  const projects: Project[] = projectsData?.projects ?? [];
  const agents: AgentRun[]  = agentsData?.agents ?? [];

  const avgSRI  = projects.length
    ? Math.round(projects.reduce((s, p) => s + p.sri_score, 0) / projects.length)
    : 0;
  const running = agents.filter((a) => a.status === "running").length;

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6 animate-fade-in">
      {/* ── Header ────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-heading font-bold text-foreground">Dashboard</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Medical Device Regulatory Platform
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => refetchProjects()}
            title="Refresh projects"
          >
            <RefreshCw className="w-4 h-4" />
          </Button>
          <Button variant="outline" size="sm" asChild>
            <Link href="/research">
              <Search className="w-4 h-4" />
              Research
            </Link>
          </Button>
          <Button size="sm" asChild>
            <Link href="/projects/new">
              <Plus className="w-4 h-4" />
              New Project
            </Link>
          </Button>
        </div>
      </div>

      {/* ── Metric cards ──────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Active Projects</p>
                <p className="text-3xl font-heading font-bold text-foreground mt-1">
                  {projectsLoading ? (
                    <span className="inline-block h-8 w-8 rounded bg-muted animate-pulse" />
                  ) : projects.length}
                </p>
              </div>
              <FlaskConical className="w-8 h-8 text-primary opacity-70" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Agents Running</p>
                <p className="text-3xl font-heading font-bold text-foreground mt-1">
                  {agentsLoading ? (
                    <span className="inline-block h-8 w-8 rounded bg-muted animate-pulse" />
                  ) : running}
                </p>
              </div>
              <Activity className="w-8 h-8 text-primary opacity-70" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Avg SRI Score</p>
                <p className="text-3xl font-heading font-bold text-foreground mt-1">
                  {avgSRI > 0 ? (
                    <>
                      {avgSRI}
                      <span className="text-sm font-normal text-muted-foreground">/100</span>
                    </>
                  ) : (
                    <span className="text-muted-foreground text-xl">—</span>
                  )}
                </p>
              </div>
              <SRIScoreRing score={avgSRI} size={56} strokeWidth={6} showLabel={false} />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* ── Main grid ─────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Projects list — col-span-2 */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-heading font-semibold text-foreground">Projects</h2>
            <Link
              href="/projects"
              className="text-xs text-primary hover:underline flex items-center gap-1"
            >
              View all <ChevronRight className="w-3 h-3" />
            </Link>
          </div>

          {projectsLoading ? (
            <>
              <SkeletonCard />
              <SkeletonCard />
              <SkeletonCard />
            </>
          ) : projectsError ? (
            <Card>
              <CardContent className="py-8 text-center text-sm text-muted-foreground">
                Could not load projects. Check the API connection.
              </CardContent>
            </Card>
          ) : projects.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center">
                <FlaskConical className="w-10 h-10 text-muted-foreground mx-auto mb-3" />
                <p className="text-muted-foreground text-sm">No projects yet.</p>
                <Button size="sm" className="mt-4" asChild>
                  <Link href="/projects/new">Create your first project</Link>
                </Button>
              </CardContent>
            </Card>
          ) : (
            projects.slice(0, 5).map((project) => (
              <Card key={project.id} className="hover:shadow-md transition-shadow">
                <CardContent className="pt-4 pb-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <Link
                          href={`/projects/${project.id}`}
                          className="font-heading font-semibold text-foreground hover:text-primary transition-colors truncate"
                        >
                          {project.name}
                        </Link>
                        {project.product_code && (
                          <Badge variant="outline" className="text-xs">
                            {project.product_code}
                          </Badge>
                        )}
                        <StageBadge stage={project.stage} />
                      </div>
                      <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          Updated {timeAgo(project.updated_at)}
                        </span>
                      </div>
                    </div>
                    <SRIScoreRing
                      score={project.sri_score}
                      size={56}
                      strokeWidth={6}
                      showLabel={false}
                    />
                  </div>
                </CardContent>
              </Card>
            ))
          )}

          {/* SRI trend */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">SRI Trend</CardTitle>
              <CardDescription>Average submission readiness over time</CardDescription>
            </CardHeader>
            <CardContent>
              <AreaChart
                data={SRI_TREND}
                index="date"
                categories={["SRI"]}
                colors={["blue"]}
                valueFormatter={(v: number) => `${v}/100`}
                className="h-36"
                showLegend={false}
                showYAxis={false}
              />
            </CardContent>
          </Card>
        </div>

        {/* Agent activity feed — col-span-1 */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-heading font-semibold text-foreground">Agent Activity</h2>
            <Link
              href="/agents"
              className="text-xs text-primary hover:underline flex items-center gap-1"
            >
              Mission control <ChevronRight className="w-3 h-3" />
            </Link>
          </div>

          <Card>
            <CardContent className="pt-4 pb-2">
              {agentsLoading ? (
                <div className="space-y-3 py-2">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="flex items-start gap-2">
                      <div className="flex-1 space-y-1.5">
                        <div className="h-3 w-24 rounded bg-muted animate-pulse" />
                        <div className="h-3 w-36 rounded bg-muted animate-pulse" />
                      </div>
                      <div className="h-5 w-14 rounded-full bg-muted animate-pulse" />
                    </div>
                  ))}
                </div>
              ) : agents.length === 0 ? (
                <p className="text-sm text-muted-foreground py-4 text-center">No active agents.</p>
              ) : (
                <ul className="divide-y divide-border">
                  {agents.slice(0, 6).map((agent) => (
                    <li key={agent.id} className="py-3 first:pt-0 last:pb-0">
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0 flex-1">
                          <p className="text-xs font-medium text-foreground truncate">
                            {agent.name}
                          </p>
                          {agent.task && (
                            <p className="text-xs text-muted-foreground truncate mt-0.5">
                              {agent.task}
                            </p>
                          )}
                          {agent.started_at && (
                            <p className="text-xs text-muted-foreground/70 mt-0.5">
                              {timeAgo(agent.started_at)}
                            </p>
                          )}
                        </div>
                        <AgentStatusChip
                          status={agent.status as AgentStatus}
                          className="flex-shrink-0"
                        />
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
