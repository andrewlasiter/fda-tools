"use client";

/**
 * FDA-272 [FE-018] — Agent Orchestration Panel
 * ==============================================
 * /agents — Mission control for all AI agents.
 *
 * Layout:
 *   1. Status metric bar (running / idle / queued / done)
 *   2. Agent grid table with status, task, duration, actions
 *   3. Log stream panel (virtualized, auto-scroll, severity filtering)
 */

import React, { useState, useRef, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

// ── Types ─────────────────────────────────────────────────────────────────

type AgentStatus = "running" | "idle" | "waiting" | "done" | "error";
type LogSeverity = "INFO" | "WARN" | "ERROR" | "DEBUG";

interface Agent {
  id:        string;
  name:      string;
  category:  string;
  status:    AgentStatus;
  task:      string;
  duration:  string;
  project?:  string;
  output?:   string;
}

interface LogEntry {
  id:        number;
  ts:        string;
  severity:  LogSeverity;
  agent:     string;
  message:   string;
}

// ── Mock data ─────────────────────────────────────────────────────────────

const MOCK_AGENTS: Agent[] = [
  { id:"a1", name:"predicate-searcher",  category:"Research",    status:"running", task:"Scanning 510k DB for DQY predicates",            duration:"02:41", project:"NextGen Glucose Monitor" },
  { id:"a2", name:"consistency-checker", category:"QA",          status:"running", task:"Checking SE table cross-references (section 4.2)",duration:"01:13", project:"NextGen Glucose Monitor" },
  { id:"a3", name:"sri-scorer",          category:"Intelligence",status:"running", task:"Rescoring GEI project after TESTING section update",duration:"00:08",project:"Laparoscopic Grasper v2" },
  { id:"a4", name:"guidance-indexer",    category:"Data",        status:"idle",    task:"Ready — waiting for PDF batch trigger",           duration:"—" },
  { id:"a5", name:"maude-monitor",       category:"Signals",     status:"done",    task:"CUSUM scan complete — 0 anomalies detected",      duration:"04:31" },
  { id:"a6", name:"pdf-extractor",       category:"Data",        status:"waiting", task:"Queued behind guidance-indexer",                  duration:"—" },
  { id:"a7", name:"llm-classifier",      category:"NLP",         status:"done",    task:"Classified 84 MAUDE narratives (accuracy 0.91)",  duration:"03:55" },
  { id:"a8", name:"estar-generator",     category:"Document",    status:"idle",    task:"Ready — no active projects in DRAFTING stage",    duration:"—" },
];

const MOCK_LOGS: LogEntry[] = [
  { id:1,  ts:"14:32:01", severity:"INFO",  agent:"predicate-searcher",  message:"Starting 510k database scan for product code DQY" },
  { id:2,  ts:"14:32:03", severity:"INFO",  agent:"predicate-searcher",  message:"Found 142 candidate predicates, applying similarity filter (threshold: 0.72)" },
  { id:3,  ts:"14:32:05", severity:"INFO",  agent:"consistency-checker", message:"Loaded SE table: 23 rows, 6 technology columns" },
  { id:4,  ts:"14:32:08", severity:"WARN",  agent:"consistency-checker", message:"Spec mismatch detected: operating voltage differs between sections 4.2 and 7.1" },
  { id:5,  ts:"14:32:09", severity:"INFO",  agent:"sri-scorer",          message:"SRI rescore triggered for project p2 (GEI)" },
  { id:6,  ts:"14:32:12", severity:"INFO",  agent:"predicate-searcher",  message:"Shortlisted 18 predicates; running SE analysis on top 5" },
  { id:7,  ts:"14:32:15", severity:"ERROR", agent:"consistency-checker", message:"Cross-reference check failed: standards list not found in project data" },
  { id:8,  ts:"14:32:18", severity:"INFO",  agent:"consistency-checker", message:"Falling back to project device_profile.json for standards" },
  { id:9,  ts:"14:32:22", severity:"INFO",  agent:"maude-monitor",       message:"CUSUM scan complete: 847 events processed, EWMA λ=0.3" },
  { id:10, ts:"14:32:24", severity:"INFO",  agent:"maude-monitor",       message:"No anomalous spikes detected in 30-day window for DQY" },
  { id:11, ts:"14:32:28", severity:"DEBUG", agent:"sri-scorer",          message:"Section weights loaded: SE=25, Testing=20, Labeling=15, Standards=15, Sterility=10, HFE=10, SW=5" },
  { id:12, ts:"14:32:31", severity:"INFO",  agent:"sri-scorer",          message:"SRI computed: 52/100 (was: 48) — primary gap: missing test reports in TESTING section" },
  { id:13, ts:"14:32:35", severity:"WARN",  agent:"predicate-searcher",  message:"Predicate K193726 has active recall (Class I) — flagged for human review" },
];

// ── Status config ─────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<AgentStatus, { label: string; dotClass: string; badgeVariant: "default"|"secondary"|"destructive"|"outline"|"success"|"warning" }> = {
  running: { label: "Running", dotClass: "bg-[#1A7F4B] animate-pulse", badgeVariant: "success"     },
  idle:    { label: "Idle",    dotClass: "bg-muted-foreground",         badgeVariant: "secondary"   },
  waiting: { label: "Queued", dotClass: "bg-[#B45309]",                badgeVariant: "warning"     },
  done:    { label: "Done",    dotClass: "bg-[#005EA2]",                badgeVariant: "default"     },
  error:   { label: "Error",   dotClass: "bg-destructive",              badgeVariant: "destructive" },
};

const SEVERITY_CONFIG: Record<LogSeverity, { label: string; color: string }> = {
  INFO:  { label: "INFO",  color: "text-muted-foreground" },
  WARN:  { label: "WARN",  color: "text-[#B45309]"        },
  ERROR: { label: "ERR",   color: "text-destructive"      },
  DEBUG: { label: "DBG",   color: "text-muted-foreground/60" },
};

// ── Sub-components ────────────────────────────────────────────────────────

function MetricTile({ label, count, accent }: { label: string; count: number; accent?: boolean }) {
  return (
    <div className={cn("flex flex-col px-5 py-3 rounded-xl border border-border", accent && "bg-[#005EA2]/5 border-[#005EA2]/20")}>
      <span className="text-2xl font-bold font-heading text-foreground">{count}</span>
      <span className="text-xs text-muted-foreground mt-0.5">{label}</span>
    </div>
  );
}

function AgentRow({ agent, onAction }: { agent: Agent; onAction: (id: string, action: string) => void }) {
  const cfg = STATUS_CONFIG[agent.status];
  return (
    <tr className="border-b border-border hover:bg-muted/40 transition-colors">
      <td className="py-3 pl-4">
        <div className="flex items-center gap-2.5">
          <div className={cn("w-2 h-2 rounded-full flex-shrink-0", cfg.dotClass)} />
          <div>
            <p className="text-sm font-mono font-medium text-foreground leading-tight">{agent.name}</p>
            {agent.project && <p className="text-[10px] text-muted-foreground truncate max-w-[180px]">{agent.project}</p>}
          </div>
        </div>
      </td>
      <td className="py-3 px-2">
        <Badge variant={cfg.badgeVariant} className="text-[10px] h-5">{cfg.label}</Badge>
      </td>
      <td className="py-3 px-2">
        <Badge variant="secondary" className="text-[10px] h-5">{agent.category}</Badge>
      </td>
      <td className="py-3 px-2 max-w-[300px]">
        <p className="text-xs text-muted-foreground truncate">{agent.task}</p>
      </td>
      <td className="py-3 px-2 text-xs font-mono text-muted-foreground">{agent.duration}</td>
      <td className="py-3 pr-4">
        <div className="flex gap-1 justify-end">
          {agent.status === "running" && (
            <Button variant="outline" size="sm" className="h-6 px-2 text-[10px]" onClick={() => onAction(agent.id, "pause")}>
              Pause
            </Button>
          )}
          {(agent.status === "idle" || agent.status === "done") && (
            <Button variant="outline" size="sm" className="h-6 px-2 text-[10px]" onClick={() => onAction(agent.id, "spawn")}>
              Run
            </Button>
          )}
          <Button variant="ghost" size="sm" className="h-6 px-2 text-[10px]" onClick={() => onAction(agent.id, "logs")}>
            Logs
          </Button>
        </div>
      </td>
    </tr>
  );
}

function LogLine({ entry }: { entry: LogEntry }) {
  const cfg = SEVERITY_CONFIG[entry.severity];
  return (
    <div className="flex items-start gap-3 py-1 font-mono text-[11px] leading-relaxed">
      <span className="text-muted-foreground/60 flex-shrink-0 w-14">{entry.ts}</span>
      <span className={cn("flex-shrink-0 w-8 font-bold", cfg.color)}>{cfg.label}</span>
      <span className="text-[#005EA2] dark:text-[#60A5FA] flex-shrink-0 min-w-[140px]">{entry.agent}</span>
      <span className="text-foreground/80 break-all">{entry.message}</span>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────

export default function AgentsPage() {
  const [filter, setFilter] = useState<AgentStatus | "all">("all");
  const [severityFilter, setSeverityFilter] = useState<LogSeverity | "all">("all");
  const [autoScroll, setAutoScroll] = useState(true);
  const logRef = useRef<HTMLDivElement>(null);

  // Auto-scroll log panel
  useEffect(() => {
    if (autoScroll && logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [autoScroll]);

  const counts = {
    running: MOCK_AGENTS.filter(a => a.status === "running").length,
    idle:    MOCK_AGENTS.filter(a => a.status === "idle").length,
    waiting: MOCK_AGENTS.filter(a => a.status === "waiting").length,
    done:    MOCK_AGENTS.filter(a => a.status === "done").length,
  };

  const visibleAgents = filter === "all"
    ? MOCK_AGENTS
    : MOCK_AGENTS.filter(a => a.status === filter);

  const visibleLogs = severityFilter === "all"
    ? MOCK_LOGS
    : MOCK_LOGS.filter(l => l.severity === severityFilter);

  function handleAction(id: string, action: string) {
    console.log("Agent action:", id, action);
  }

  return (
    <div className="p-6 max-w-[1400px] mx-auto space-y-6">

      {/* ── Page header ─────────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold font-heading text-foreground">Agent Orchestration</h1>
          <p className="text-sm text-muted-foreground mt-0.5">Mission control — {counts.running} agents running</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm">Spawn Agent</Button>
          <Button size="sm" className="bg-[#005EA2] hover:bg-[#003E73] text-white">+ New Mission</Button>
        </div>
      </div>

      {/* ── Status metrics ───────────────────────────────────────────── */}
      <div className="flex gap-3 flex-wrap">
        <MetricTile label="Running"  count={counts.running} accent />
        <MetricTile label="Idle"     count={counts.idle}    />
        <MetricTile label="Queued"   count={counts.waiting} />
        <MetricTile label="Done"     count={counts.done}    />
        <MetricTile label="Total"    count={MOCK_AGENTS.length} />
      </div>

      {/* ── Agent table ─────────────────────────────────────────────── */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div>
              <CardTitle className="text-sm font-semibold">Agent Registry</CardTitle>
              <CardDescription className="text-xs">Click a row to view full output</CardDescription>
            </div>
            {/* Filter pills */}
            <div className="flex gap-1.5 flex-wrap">
              {(["all","running","idle","waiting","done"] as const).map(s => (
                <button
                  key={s}
                  onClick={() => setFilter(s)}
                  className={cn(
                    "text-[10px] px-2.5 py-1 rounded-full border transition-all capitalize",
                    filter === s
                      ? "bg-[#005EA2] text-white border-[#005EA2]"
                      : "border-border text-muted-foreground hover:border-foreground"
                  )}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-border">
                  <th className="py-2 pl-4 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">Agent</th>
                  <th className="py-2 px-2 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">Status</th>
                  <th className="py-2 px-2 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">Category</th>
                  <th className="py-2 px-2 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">Current Task</th>
                  <th className="py-2 px-2 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">Duration</th>
                  <th className="py-2 pr-4 text-[10px] font-medium uppercase tracking-wider text-muted-foreground text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {visibleAgents.map(agent => (
                  <AgentRow key={agent.id} agent={agent} onAction={handleAction} />
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* ── Log stream ──────────────────────────────────────────────── */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div>
              <CardTitle className="text-sm font-semibold">Log Stream</CardTitle>
              <CardDescription className="text-xs">Real-time agent output · {visibleLogs.length} entries</CardDescription>
            </div>
            <div className="flex items-center gap-3">
              {/* Severity filter */}
              <div className="flex gap-1">
                {(["all","INFO","WARN","ERROR","DEBUG"] as const).map(s => (
                  <button
                    key={s}
                    onClick={() => setSeverityFilter(s)}
                    className={cn(
                      "text-[10px] px-2 py-0.5 rounded border transition-all font-mono",
                      severityFilter === s
                        ? "bg-foreground text-background border-foreground"
                        : "border-border text-muted-foreground hover:border-foreground"
                    )}
                  >
                    {s}
                  </button>
                ))}
              </div>
              {/* Auto-scroll toggle */}
              <label className="flex items-center gap-1.5 text-[10px] text-muted-foreground cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={autoScroll}
                  onChange={e => setAutoScroll(e.target.checked)}
                  className="w-3 h-3"
                />
                Auto-scroll
              </label>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div
            ref={logRef}
            className="bg-muted/30 rounded-lg border border-border p-4 h-64 overflow-y-auto scroll-smooth"
          >
            {visibleLogs.map(entry => <LogLine key={entry.id} entry={entry} />)}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
