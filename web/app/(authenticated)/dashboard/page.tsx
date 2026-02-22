"use client";

/**
 * FDA-271 [FE-017] — Home Dashboard Page
 * ========================================
 * /dashboard — Primary landing page for MDRP.
 *
 * Layout (top to bottom):
 *   1. Page header + quick actions
 *   2. KPI metric cards row  (4 tiles)
 *   3. SRI trend chart + project cards  (2-col grid)
 *   4. Agent activity feed + compliance scorecard  (2-col grid)
 */

import React, { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

// ── Mock data (hooks will replace when bridge is live) ────────────────────

const MOCK_KPI = [
  { label: "Active Projects",     value: "8",   delta: "+2 this week",   status: "neutral" },
  { label: "Agents Running",      value: "3",   delta: "5 idle",         status: "ok"      },
  { label: "Submissions Pending", value: "2",   delta: "Due in 14 days", status: "warning" },
  { label: "Avg SRI Score",       value: "71",  delta: "+4 vs last month",status: "good"   },
] as const;

const MOCK_SRI_TREND = [
  { week: "W1", score: 58 }, { week: "W2", score: 61 }, { week: "W3", score: 59 },
  { week: "W4", score: 65 }, { week: "W5", score: 63 }, { week: "W6", score: 68 },
  { week: "W7", score: 71 }, { week: "W8", score: 71 },
];

const MOCK_PROJECTS = [
  {
    id: "p1",
    name: "NextGen Glucose Monitor",
    code: "DQY",
    stage: "DRAFTING",
    stageIdx: 6,
    sri: 78,
    deadline: "2026-03-15",
    team: ["AS", "BR", "CM"],
    status: "on-track",
  },
  {
    id: "p2",
    name: "Laparoscopic Grasper v2",
    code: "GEI",
    stage: "PREDICATE",
    stageIdx: 2,
    sri: 52,
    deadline: "2026-04-01",
    team: ["JD", "KL"],
    status: "at-risk",
  },
  {
    id: "p3",
    name: "Cardiac Ablation Catheter",
    code: "DQY",
    stage: "TESTING",
    stageIdx: 5,
    sri: 84,
    deadline: "2026-05-20",
    team: ["MN", "OP", "QR"],
    status: "on-track",
  },
  {
    id: "p4",
    name: "AI Pathology Platform",
    code: "QKQ",
    stage: "CLASSIFY",
    stageIdx: 1,
    sri: 41,
    deadline: "2026-06-10",
    team: ["ST"],
    status: "needs-attention",
  },
] as const;

const MOCK_AGENTS = [
  { name: "predicate-searcher",   category: "Research",    status: "running",  task: "Scanning 510(k) DB for DQY predicates",  duration: "02:14" },
  { name: "consistency-checker",  category: "QA",          status: "running",  task: "Checking SE table for NGM project",       duration: "00:47" },
  { name: "sri-scorer",           category: "Intelligence",status: "running",  task: "Rescoring GEI after TESTING update",      duration: "00:08" },
  { name: "guidance-indexer",     category: "Data",        status: "idle",     task: "Waiting for new PDF batch",               duration: "—"     },
  { name: "maude-monitor",        category: "Signals",     status: "done",     task: "CUSUM scan complete — 0 spikes detected", duration: "04:31" },
] as const;

const NPD_STAGES = [
  "CONCEPT","CLASSIFY","PREDICATE","PATHWAY","PRESUB",
  "TESTING","DRAFTING","REVIEW","SUBMIT","FDA_REVIEW","CLEARED","POST_MARKET",
] as const;

// ── Sub-components ────────────────────────────────────────────────────────

/** Status color mapping */
const statusConfig = {
  "on-track":       { label: "On Track",       variant: "success"     },
  "at-risk":        { label: "At Risk",         variant: "warning"     },
  "needs-attention":{ label: "Needs Attention", variant: "destructive" },
} as const;

/** KPI metric card */
function KpiCard({
  label, value, delta, status,
}: {
  label: string; value: string; delta: string;
  status: "neutral" | "ok" | "warning" | "good";
}) {
  const accentMap = {
    neutral: "text-muted-foreground",
    ok:      "text-[#1A7F4B]",
    warning: "text-[#B45309]",
    good:    "text-[#005EA2]",
  } as const;

  return (
    <Card className="relative overflow-hidden">
      <CardContent className="pt-6 pb-5">
        <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground mb-1">{label}</p>
        <p className="text-3xl font-bold text-foreground font-heading">{value}</p>
        <p className={cn("text-xs mt-1", accentMap[status])}>{delta}</p>
      </CardContent>
      {/* Decorative corner accent */}
      <div className="absolute top-0 right-0 w-12 h-12 bg-gradient-to-bl from-[#005EA2]/5 to-transparent rounded-bl-[40px]" />
    </Card>
  );
}

/** Inline SRI trend sparkline (pure SVG, no chart library dependency) */
function SriSparkline({ data }: { data: typeof MOCK_SRI_TREND }) {
  const w = 520; const h = 120;
  const pad = 24;
  const xs = data.map((_, i) => pad + (i / (data.length - 1)) * (w - pad * 2));
  const min = 50; const max = 90;
  const ys = data.map(d => h - pad - ((d.score - min) / (max - min)) * (h - pad * 2));
  const pathD = xs.map((x, i) => `${i === 0 ? "M" : "L"}${x},${ys[i]}`).join(" ");
  const areaD = `${pathD} L${xs[xs.length - 1]},${h - pad} L${xs[0]},${h - pad} Z`;

  return (
    <div className="w-full">
      <svg viewBox={`0 0 ${w} ${h}`} className="w-full" preserveAspectRatio="none" style={{ height: 120 }}>
        <defs>
          <linearGradient id="sriGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#005EA2" stopOpacity="0.25"/>
            <stop offset="100%" stopColor="#005EA2" stopOpacity="0.02"/>
          </linearGradient>
        </defs>
        <path d={areaD} fill="url(#sriGrad)" />
        <path d={pathD} fill="none" stroke="#005EA2" strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />
        {xs.map((x, i) => (
          <circle key={i} cx={x} cy={ys[i]} r="3.5" fill="#005EA2" stroke="white" strokeWidth="1.5" />
        ))}
      </svg>
      <div className="flex justify-between px-6 text-[10px] text-muted-foreground mt-0.5">
        {data.map(d => <span key={d.week}>{d.week}</span>)}
      </div>
    </div>
  );
}

/** Project card */
function ProjectCard({ p }: { p: (typeof MOCK_PROJECTS)[number] }) {
  const cfg = statusConfig[p.status];
  const stageIdx = p.stageIdx;

  return (
    <Card className="hover:shadow-md transition-shadow cursor-pointer group">
      <CardContent className="pt-5 pb-4">
        {/* Header row */}
        <div className="flex items-start justify-between gap-2 mb-3">
          <div className="min-w-0">
            <p className="text-sm font-semibold text-foreground truncate group-hover:text-[#005EA2] transition-colors">
              {p.name}
            </p>
            <p className="text-xs text-muted-foreground mt-0.5">Code: <span className="font-mono">{p.code}</span></p>
          </div>
          <Badge variant={cfg.variant as "success" | "warning" | "destructive"} className="flex-shrink-0 text-[10px]">
            {cfg.label}
          </Badge>
        </div>

        {/* Pipeline mini-progress */}
        <div className="mb-3">
          <div className="flex items-center justify-between text-[10px] text-muted-foreground mb-1">
            <span>{p.stage}</span>
            <span>Stage {stageIdx + 1}/{NPD_STAGES.length}</span>
          </div>
          <div className="flex gap-0.5">
            {NPD_STAGES.map((_, i) => (
              <div
                key={i}
                className={cn(
                  "h-1 flex-1 rounded-full transition-colors",
                  i < stageIdx  ? "bg-[#1A7F4B]"       :
                  i === stageIdx ? "bg-[#005EA2]"        :
                  "bg-border"
                )}
              />
            ))}
          </div>
        </div>

        {/* Footer: SRI + deadline + team */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            <span>SRI <span className={cn("font-bold", p.sri >= 70 ? "text-[#1A7F4B]" : p.sri >= 50 ? "text-[#B45309]" : "text-destructive")}>{p.sri}</span></span>
            <span>Due {new Date(p.deadline).toLocaleDateString("en-US", { month: "short", day: "numeric" })}</span>
          </div>
          {/* Team avatars */}
          <div className="flex -space-x-1.5">
            {p.team.map(initials => (
              <div key={initials} className="w-6 h-6 rounded-full bg-[#005EA2]/15 border border-background flex items-center justify-center">
                <span className="text-[9px] font-bold text-[#005EA2]">{initials}</span>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

/** Agent status row */
function AgentRow({ agent }: { agent: (typeof MOCK_AGENTS)[number] }) {
  const statusDot = {
    running: "bg-[#1A7F4B] animate-pulse",
    idle:    "bg-muted-foreground",
    done:    "bg-[#005EA2]",
  } as const;

  return (
    <div className="flex items-start gap-3 py-3 border-b border-border last:border-0">
      <div className={cn("w-2 h-2 rounded-full mt-1.5 flex-shrink-0", statusDot[agent.status])} />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs font-semibold font-mono text-foreground">{agent.name}</span>
          <Badge variant="secondary" className="text-[9px] h-4 px-1">{agent.category}</Badge>
        </div>
        <p className="text-xs text-muted-foreground mt-0.5 truncate">{agent.task}</p>
      </div>
      <span className="text-[10px] text-muted-foreground flex-shrink-0 font-mono">{agent.duration}</span>
    </div>
  );
}

/** Compliance scorecard ring (pure SVG) */
function ComplianceRing({ score, label }: { score: number; label: string }) {
  const r = 40; const circumference = 2 * Math.PI * r;
  const offset = circumference - (score / 100) * circumference;
  const color = score >= 70 ? "#1A7F4B" : score >= 50 ? "#B45309" : "#C5191B";

  return (
    <div className="flex flex-col items-center gap-2">
      <svg width="100" height="100" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r={r} fill="none" stroke="hsl(var(--border))" strokeWidth="8" />
        <circle
          cx="50" cy="50" r={r} fill="none"
          stroke={color} strokeWidth="8"
          strokeDasharray={circumference} strokeDashoffset={offset}
          strokeLinecap="round"
          transform="rotate(-90 50 50)"
          style={{ transition: "stroke-dashoffset 1s ease" }}
        />
        <text x="50" y="54" textAnchor="middle" fontSize="18" fontWeight="700" fill={color} fontFamily="var(--font-heading)">
          {score}
        </text>
      </svg>
      <p className="text-xs text-muted-foreground text-center">{label}</p>
    </div>
  );
}

// ── Page component ────────────────────────────────────────────────────────

export default function DashboardPage() {
  const [currentTime, setCurrentTime] = useState<string>("");

  useEffect(() => {
    const fmt = () => new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
    setCurrentTime(fmt());
    const t = setInterval(() => setCurrentTime(fmt()), 60_000);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="p-6 max-w-[1400px] mx-auto space-y-6">

      {/* ── Page header ─────────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold font-heading text-foreground">Regulatory Dashboard</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            {new Date().toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" })}
            {currentTime && ` · ${currentTime}`}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm">Run Research</Button>
          <Button size="sm" className="bg-[#005EA2] hover:bg-[#003E73] text-white">+ New Project</Button>
        </div>
      </div>

      {/* ── KPI row ─────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {MOCK_KPI.map(kpi => <KpiCard key={kpi.label} {...kpi} />)}
      </div>

      {/* ── Middle row: SRI trend + Project cards ───────────────────── */}
      <div className="grid grid-cols-1 xl:grid-cols-[1fr_2fr] gap-4">

        {/* SRI Trend card */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold">SRI Trend</CardTitle>
            <CardDescription className="text-xs">Submission Readiness Index · 90-day rolling</CardDescription>
          </CardHeader>
          <CardContent className="pb-4">
            <SriSparkline data={MOCK_SRI_TREND} />
            <div className="mt-3 flex items-center justify-between px-1">
              <div>
                <p className="text-2xl font-bold font-heading text-[#005EA2]">71</p>
                <p className="text-xs text-muted-foreground">Current avg</p>
              </div>
              <Badge variant="success" className="text-xs">+4 pts this month</Badge>
            </div>
          </CardContent>
        </Card>

        {/* Project cards grid */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-foreground">Active Projects</h2>
            <Button variant="ghost" size="sm" className="text-xs h-7">View all →</Button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {MOCK_PROJECTS.map(p => <ProjectCard key={p.id} p={p} />)}
          </div>
        </div>
      </div>

      {/* ── Bottom row: Agent feed + Compliance ─────────────────────── */}
      <div className="grid grid-cols-1 xl:grid-cols-[1.5fr_1fr] gap-4">

        {/* Agent activity feed */}
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-sm font-semibold">Agent Activity</CardTitle>
                <CardDescription className="text-xs">Live status — refreshes every 10s</CardDescription>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="w-1.5 h-1.5 rounded-full bg-[#1A7F4B] animate-pulse" />
                <span className="text-[10px] text-muted-foreground">3 running</span>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="divide-y-0">
              {MOCK_AGENTS.map(agent => <AgentRow key={agent.name} agent={agent} />)}
            </div>
            <Button variant="outline" size="sm" className="w-full mt-3 text-xs h-8">
              Open Agent Control Panel →
            </Button>
          </CardContent>
        </Card>

        {/* Compliance scorecard */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold">Compliance Scorecard</CardTitle>
            <CardDescription className="text-xs">Portfolio-level regulatory health</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-2 py-2">
              <ComplianceRing score={71} label="Avg SRI" />
              <ComplianceRing score={88} label="RTA Ready" />
              <ComplianceRing score={64} label="SE Completeness" />
            </div>
            <div className="mt-4 space-y-2">
              {[
                { label: "Critical gaps",   value: "4",  color: "text-destructive" },
                { label: "Warnings",        value: "11", color: "text-[#B45309]"   },
                { label: "Resolved items",  value: "47", color: "text-[#1A7F4B]"   },
              ].map(row => (
                <div key={row.label} className="flex items-center justify-between text-xs">
                  <span className="text-muted-foreground">{row.label}</span>
                  <span className={cn("font-bold", row.color)}>{row.value}</span>
                </div>
              ))}
            </div>
            <Button variant="ghost" size="sm" className="w-full mt-3 text-xs h-8">
              View full audit report →
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
