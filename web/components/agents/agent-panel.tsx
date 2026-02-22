"use client";

import * as React from "react";
import {
  Bot,
  RefreshCw,
  Play,
  Square,
  RotateCcw,
  ChevronDown,
  ChevronUp,
  Clock,
  AlertTriangle,
  CheckCircle2,
  Loader2,
  Minus,
  Wifi,
  WifiOff,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { AgentStatusChip, type AgentStatus } from "@/components/ui/agent-status-chip";
import { cn, timeAgo } from "@/lib/utils";
import {
  useAgents,
  useHealth,
  useMetrics,
  type AgentRun,
} from "@/lib/api-client";

// ── Status summary counts ────────────────────────────────────────────────────

function StatusPill({
  label,
  count,
  colorClass,
}: {
  label: string;
  count: number;
  colorClass: string;
}) {
  return (
    <div className={cn("flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium", colorClass)}>
      <span className="tabular-nums font-bold">{count}</span>
      <span className="capitalize">{label}</span>
    </div>
  );
}

// ── Duration display ─────────────────────────────────────────────────────────

function AgentDuration({ agent }: { agent: AgentRun }) {
  const [elapsed, setElapsed] = React.useState<string>("");

  React.useEffect(() => {
    if (!agent.started_at) { setElapsed("—"); return; }
    if (agent.duration_ms != null) {
      setElapsed(formatDuration(agent.duration_ms));
      return;
    }
    // Live elapsed for running/waiting agents
    const tick = () => {
      const ms = Date.now() - new Date(agent.started_at!).getTime();
      setElapsed(formatDuration(ms));
    };
    tick();
    const interval = setInterval(tick, 1000);
    return () => clearInterval(interval);
  }, [agent.started_at, agent.duration_ms]);

  return <span className="tabular-nums text-xs text-muted-foreground">{elapsed}</span>;
}

function formatDuration(ms: number): string {
  const s = Math.floor(ms / 1000);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ${s % 60}s`;
  const h = Math.floor(m / 60);
  return `${h}h ${m % 60}m`;
}

// ── Agent row ────────────────────────────────────────────────────────────────

function AgentRow({ agent }: { agent: AgentRun }) {
  const [expanded, setExpanded] = React.useState(false);

  return (
    <>
      <tr
        className={cn(
          "border-b border-border hover:bg-muted/30 transition-colors cursor-pointer",
          agent.status === "running" && "bg-blue-50/40 dark:bg-blue-950/20",
          agent.status === "failed"  && "bg-red-50/40 dark:bg-red-950/20",
        )}
        onClick={() => agent.output && setExpanded(!expanded)}
      >
        {/* Agent name + status */}
        <td className="px-4 py-3">
          <div className="flex items-center gap-2">
            <Bot className="w-3.5 h-3.5 text-muted-foreground flex-shrink-0" />
            <span className="text-sm font-medium text-foreground truncate max-w-[180px]">
              {agent.name}
            </span>
          </div>
        </td>

        {/* Status chip */}
        <td className="px-4 py-3">
          <AgentStatusChip status={agent.status as AgentStatus} />
        </td>

        {/* Task */}
        <td className="px-4 py-3 hidden md:table-cell">
          <span className="text-xs text-muted-foreground truncate max-w-[240px] block">
            {agent.task ?? "—"}
          </span>
        </td>

        {/* Duration */}
        <td className="px-4 py-3 hidden sm:table-cell">
          <AgentDuration agent={agent} />
        </td>

        {/* Score */}
        <td className="px-4 py-3 hidden lg:table-cell">
          {agent.score != null ? (
            <span className={cn(
              "text-xs font-semibold tabular-nums",
              agent.score >= 0.8 ? "text-success-DEFAULT" :
              agent.score >= 0.5 ? "text-warning-DEFAULT" : "text-destructive",
            )}>
              {(agent.score * 100).toFixed(0)}%
            </span>
          ) : (
            <span className="text-muted-foreground text-xs">—</span>
          )}
        </td>

        {/* Actions */}
        <td className="px-4 py-3 text-right">
          <div className="flex items-center justify-end gap-1">
            {(agent.status === "running" || agent.status === "waiting") && (
              <Button
                size="icon"
                variant="ghost"
                className="h-6 w-6"
                title="Cancel"
                onClick={(e) => { e.stopPropagation(); /* TODO: cancel API */ }}
              >
                <Square className="w-3 h-3" />
              </Button>
            )}
            {agent.status === "failed" && (
              <Button
                size="icon"
                variant="ghost"
                className="h-6 w-6"
                title="Retry"
                onClick={(e) => { e.stopPropagation(); /* TODO: retry API */ }}
              >
                <RotateCcw className="w-3 h-3" />
              </Button>
            )}
            {agent.output && (
              <Button
                size="icon"
                variant="ghost"
                className="h-6 w-6"
                title={expanded ? "Collapse" : "Expand"}
                onClick={(e) => { e.stopPropagation(); setExpanded(!expanded); }}
              >
                {expanded ? (
                  <ChevronUp className="w-3 h-3" />
                ) : (
                  <ChevronDown className="w-3 h-3" />
                )}
              </Button>
            )}
          </div>
        </td>
      </tr>

      {/* Expanded output row */}
      {expanded && agent.output && (
        <tr className="border-b border-border bg-muted/20">
          <td colSpan={6} className="px-4 pb-3 pt-2">
            <ScrollArea className="max-h-40 rounded border border-border p-3 bg-background">
              <pre className="text-xs font-mono text-muted-foreground whitespace-pre-wrap break-words">
                {agent.output}
              </pre>
            </ScrollArea>
          </td>
        </tr>
      )}
    </>
  );
}

// ── Status icon helper ───────────────────────────────────────────────────────

function HealthIcon({ status }: { status: "healthy" | "degraded" | undefined }) {
  if (!status) return <WifiOff className="w-4 h-4 text-muted-foreground" />;
  return status === "healthy"
    ? <Wifi className="w-4 h-4 text-success-DEFAULT" />
    : <AlertTriangle className="w-4 h-4 text-warning-DEFAULT" />;
}

// ── Agent table ──────────────────────────────────────────────────────────────

function AgentTable({ agents }: { agents: AgentRun[] }) {
  if (agents.length === 0) {
    return (
      <div className="py-16 text-center">
        <Bot className="w-12 h-12 text-muted-foreground mx-auto mb-3 opacity-50" />
        <p className="text-muted-foreground text-sm">No agents found.</p>
        <p className="text-xs text-muted-foreground/70 mt-1">
          Spawn an agent from a project to see it here.
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left">
        <thead>
          <tr className="border-b border-border">
            <th className="px-4 py-2.5 text-xs font-semibold text-muted-foreground uppercase tracking-wide">Agent</th>
            <th className="px-4 py-2.5 text-xs font-semibold text-muted-foreground uppercase tracking-wide">Status</th>
            <th className="px-4 py-2.5 text-xs font-semibold text-muted-foreground uppercase tracking-wide hidden md:table-cell">Task</th>
            <th className="px-4 py-2.5 text-xs font-semibold text-muted-foreground uppercase tracking-wide hidden sm:table-cell">Duration</th>
            <th className="px-4 py-2.5 text-xs font-semibold text-muted-foreground uppercase tracking-wide hidden lg:table-cell">Score</th>
            <th className="px-4 py-2.5 text-xs font-semibold text-muted-foreground uppercase tracking-wide text-right">Actions</th>
          </tr>
        </thead>
        <tbody>
          {agents.map((agent) => (
            <AgentRow key={agent.id} agent={agent} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Metrics bar ──────────────────────────────────────────────────────────────

function MetricsBar() {
  const { data: metrics } = useMetrics();
  if (!metrics) return null;

  return (
    <div className="flex flex-wrap items-center gap-4 px-4 py-2 bg-muted/40 rounded-lg text-xs text-muted-foreground">
      <span className="flex items-center gap-1">
        <Clock className="w-3 h-3" />
        Uptime: {Math.round(metrics.uptime_seconds / 60)}m
      </span>
      <span>Req/total: {metrics.requests.total}</span>
      <span>Error rate: {metrics.requests.error_rate_pct.toFixed(1)}%</span>
      <span>p95: {metrics.response_time_ms.p95}ms</span>
      <span>{metrics.sessions.active} sessions</span>
      {metrics.alerts_active > 0 && (
        <span className="text-warning-DEFAULT flex items-center gap-1">
          <AlertTriangle className="w-3 h-3" />
          {metrics.alerts_active} alert{metrics.alerts_active !== 1 ? "s" : ""}
        </span>
      )}
    </div>
  );
}

// ── Main panel ───────────────────────────────────────────────────────────────

export function AgentPanel() {
  const { data: agentsData, isLoading, isError, dataUpdatedAt, refetch } = useAgents();
  const { data: health } = useHealth();

  const agents: AgentRun[] = agentsData?.agents ?? [];

  // Status counts
  const counts = React.useMemo(() => ({
    idle:    agents.filter((a) => a.status === "idle").length,
    running: agents.filter((a) => a.status === "running").length,
    waiting: agents.filter((a) => a.status === "waiting").length,
    done:    agents.filter((a) => a.status === "done").length,
    failed:  agents.filter((a) => a.status === "failed").length,
  }), [agents]);

  const activeAgents  = agents.filter((a) => a.status === "running" || a.status === "waiting");
  const allAgents     = agents;
  const historyAgents = agents.filter((a) => a.status === "done" || a.status === "failed");

  const lastUpdated = dataUpdatedAt
    ? new Date(dataUpdatedAt).toLocaleTimeString()
    : null;

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6 animate-fade-in">
      {/* ── Header ──────────────────────────────────────────────────── */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-heading font-bold text-foreground flex items-center gap-2">
            <Bot className="w-6 h-6 text-primary" />
            Agent Orchestration
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Mission control — real-time agent status and management
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Health indicator */}
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <HealthIcon status={health?.status} />
            <span className="capitalize">{health?.status ?? "connecting"}</span>
          </div>

          {lastUpdated && (
            <span className="text-xs text-muted-foreground hidden sm:block">
              Updated {lastUpdated}
            </span>
          )}

          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            disabled={isLoading}
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <RefreshCw className="w-4 h-4" />
            )}
            Refresh
          </Button>

          <Button size="sm" disabled title="Spawn agent (coming in Sprint 4)">
            <Play className="w-4 h-4" />
            Spawn Agent
          </Button>
        </div>
      </div>

      {/* ── Status summary pills ────────────────────────────────────── */}
      <div className="flex flex-wrap gap-2">
        <StatusPill label="running" count={counts.running}
          colorClass="bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300" />
        <StatusPill label="waiting" count={counts.waiting}
          colorClass="bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300" />
        <StatusPill label="done"    count={counts.done}
          colorClass="bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300" />
        <StatusPill label="failed"  count={counts.failed}
          colorClass="bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300" />
        <StatusPill label="idle"    count={counts.idle}
          colorClass="bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400" />
        <Badge variant="outline" className="text-xs self-center">
          {agents.length} total
        </Badge>
      </div>

      {/* ── Metrics bar (server-level) ───────────────────────────────── */}
      <MetricsBar />

      {/* ── Main table ──────────────────────────────────────────────── */}
      <Tabs defaultValue="active">
        <div className="flex items-center justify-between">
          <TabsList>
            <TabsTrigger value="active">
              Active
              {activeAgents.length > 0 && (
                <Badge variant="default" className="ml-1.5 h-4 min-w-4 px-1 text-[10px]">
                  {activeAgents.length}
                </Badge>
              )}
            </TabsTrigger>
            <TabsTrigger value="all">All</TabsTrigger>
            <TabsTrigger value="history">History</TabsTrigger>
          </TabsList>

          {counts.failed > 0 && (
            <span className="text-xs text-destructive flex items-center gap-1">
              <AlertTriangle className="w-3.5 h-3.5" />
              {counts.failed} failed
            </span>
          )}
        </div>

        {isError ? (
          <Card className="mt-4">
            <CardContent className="py-12 text-center">
              <WifiOff className="w-10 h-10 text-muted-foreground mx-auto mb-3 opacity-50" />
              <p className="text-sm text-muted-foreground">
                Cannot connect to the agent API.
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                Make sure the bridge server is running on port 18790.
              </p>
              <Button size="sm" variant="outline" className="mt-4" onClick={() => refetch()}>
                Try again
              </Button>
            </CardContent>
          </Card>
        ) : (
          <>
            <TabsContent value="active">
              <Card>
                <CardContent className="p-0">
                  {isLoading ? (
                    <div className="py-8 flex items-center justify-center gap-2 text-muted-foreground text-sm">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Loading agents…
                    </div>
                  ) : (
                    <AgentTable agents={activeAgents} />
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="all">
              <Card>
                <CardContent className="p-0">
                  <AgentTable agents={allAgents} />
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="history">
              <Card>
                <CardContent className="p-0">
                  <AgentTable agents={historyAgents} />
                </CardContent>
              </Card>
            </TabsContent>
          </>
        )}
      </Tabs>

      {/* ── Performance cards (ORCH-010 data — FDA-218) ─────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { icon: CheckCircle2, label: "Completed today", value: counts.done, color: "text-success-DEFAULT" },
          { icon: AlertTriangle, label: "Failed today",   value: counts.failed, color: "text-destructive" },
          { icon: Minus,        label: "Avg score",       value: agents.filter(a => a.score != null).length
              ? `${(agents.filter(a => a.score != null).reduce((s, a) => s + (a.score ?? 0), 0) / agents.filter(a => a.score != null).length * 100).toFixed(0)}%`
              : "—",
            color: "text-foreground" },
          { icon: Clock,        label: "Avg duration",    value: agents.filter(a => a.duration_ms != null).length
              ? formatDuration(agents.filter(a => a.duration_ms != null).reduce((s, a) => s + (a.duration_ms ?? 0), 0) / agents.filter(a => a.duration_ms != null).length)
              : "—",
            color: "text-foreground" },
        ].map(({ icon: Icon, label, value, color }) => (
          <Card key={label}>
            <CardContent className="pt-4 pb-4">
              <Icon className={cn("w-5 h-5 mb-2", color)} />
              <p className={cn("text-xl font-heading font-bold tabular-nums", color)}>{value}</p>
              <p className="text-xs text-muted-foreground mt-0.5">{label}</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
