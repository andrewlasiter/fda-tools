"use client";

/**
 * FDA-294 [DASH-001] — /dashboard page
 * ======================================
 * Home Dashboard: KPI cards + project pipeline + agent feed + SRI trend.
 * Wires the existing DashboardContent component with the full page shell.
 */

import React, { useState } from "react";
import { cn } from "@/lib/utils";

// ── Types ──────────────────────────────────────────────────────────────────

type ProjectStage =
  | "CONCEPT" | "CLASSIFY" | "PREDICATE" | "PATHWAY" | "PRESUB"
  | "TESTING" | "DRAFTING" | "REVIEW" | "SUBMIT"
  | "FDA_REVIEW" | "CLEARED" | "POST_MARKET";

type ProjectStatus = "on_track" | "at_risk" | "blocked" | "cleared";

interface Project {
  id:          string;
  name:        string;
  device:      string;
  stage:       ProjectStage;
  status:      ProjectStatus;
  sri:         number;   // 0–100
  deadline:    string;   // ISO date
  daysLeft:    number;
}

interface AgentActivity {
  id:        string;
  agent:     string;
  task:      string;
  status:    "running" | "done" | "error";
  ts:        string;
}

// ── Demo data ───────────────────────────────────────────────────────────────

const PROJECTS: Project[] = [
  { id: "p1", name: "InfuFlow 510(k)", device: "SmartFlow Infusion Pump", stage: "DRAFTING",     status: "on_track", sri: 74, deadline: "2026-04-30", daysLeft: 67 },
  { id: "p2", name: "ScanMate 510(k)", device: "Optical Coherence Tomography", stage: "PREDICATE", status: "at_risk",  sri: 48, deadline: "2026-03-15", daysLeft: 21 },
  { id: "p3", name: "NeuroStim PMA",  device: "Spinal Cord Stimulator",   stage: "PRESUB",     status: "blocked",  sri: 61, deadline: "2026-06-01", daysLeft: 99 },
  { id: "p4", name: "WoundGuard 510k",device: "Antimicrobial Wound Dressing",stage: "CLEARED",  status: "cleared",  sri: 92, deadline: "2025-12-15", daysLeft: 0  },
];

const AGENT_FEED: AgentActivity[] = [
  { id: "a1", agent: "fda-predicate-search",  task: "Cosine search for FRN predicates (top 20)",  status: "done",    ts: "2m ago" },
  { id: "a2", agent: "signal-detector",       task: "CUSUM analysis on MAUDE FRN 2022–2025",      status: "done",    ts: "5m ago" },
  { id: "a3", agent: "guidance-embedder",     task: "Re-indexing 3 updated guidance PDFs",         status: "running", ts: "8m ago" },
  { id: "a4", agent: "consistency-checker",   task: "Cross-checking SE table vs device description", status: "running", ts: "12m ago" },
  { id: "a5", agent: "maude-classifier",      task: "Narrative classification: batch 240 events",  status: "error",   ts: "15m ago" },
];

// ── Helpers ─────────────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<ProjectStatus, { label: string; color: string; dot: string }> = {
  on_track: { label: "On Track", color: "#1A7F4B", dot: "bg-[#1A7F4B]" },
  at_risk:  { label: "At Risk",  color: "#B45309", dot: "bg-[#B45309]" },
  blocked:  { label: "Blocked",  color: "#C5191B", dot: "bg-[#C5191B]" },
  cleared:  { label: "Cleared",  color: "#005EA2", dot: "bg-[#005EA2]" },
};

const AGENT_STATUS_CONFIG = {
  running: { label: "Running", color: "#005EA2", pulse: true  },
  done:    { label: "Done",    color: "#1A7F4B", pulse: false },
  error:   { label: "Error",   color: "#C5191B", pulse: false },
};

// ── Components ───────────────────────────────────────────────────────────────

function KpiCard({ label, value, sub, color = "text-foreground" }: {
  label: string; value: string; sub?: string; color?: string;
}) {
  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <p className={cn("text-2xl font-bold font-mono", color)}>{value}</p>
      <p className="text-[11px] font-semibold text-foreground mt-0.5">{label}</p>
      {sub && <p className="text-[10px] text-muted-foreground mt-0.5">{sub}</p>}
    </div>
  );
}

function SriRing({ score }: { score: number }) {
  const r = 10; const circ = 2 * Math.PI * r;
  const color = score >= 75 ? "#1A7F4B" : score >= 50 ? "#B45309" : "#C5191B";
  return (
    <svg viewBox="0 0 26 26" className="w-7 h-7 flex-shrink-0 -rotate-90">
      <circle cx={13} cy={13} r={r} fill="none" stroke="currentColor" strokeWidth={3} className="text-muted/30" />
      <circle cx={13} cy={13} r={r} fill="none" stroke={color} strokeWidth={3}
        strokeDasharray={`${(score / 100) * circ} ${circ}`} strokeLinecap="round" />
      <text x={13} y={17} textAnchor="middle" fontSize={7} fontWeight="bold"
        fill={color} style={{ transform: "rotate(90deg)", transformOrigin: "13px 13px" }}>{score}</text>
    </svg>
  );
}

function ProjectCard({ project }: { project: Project }) {
  const scfg = STATUS_CONFIG[project.status];
  return (
    <div className="rounded-xl border border-border bg-card p-4 hover:border-[#005EA2]/30 transition-colors cursor-pointer">
      <div className="flex items-start gap-3">
        <SriRing score={project.sri} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[12px] font-bold text-foreground">{project.name}</span>
            <span className="flex items-center gap-1">
              <span className={cn("w-1.5 h-1.5 rounded-full flex-shrink-0", scfg.dot)} />
              <span className="text-[9px] font-medium" style={{ color: scfg.color }}>{scfg.label}</span>
            </span>
          </div>
          <p className="text-[10px] text-muted-foreground mt-0.5 truncate">{project.device}</p>
          <div className="flex items-center gap-3 mt-2">
            <span className="text-[9px] font-mono text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
              {project.stage.replace("_", " ")}
            </span>
            {project.daysLeft > 0 ? (
              <span className="text-[9px] text-muted-foreground">{project.daysLeft}d until deadline</span>
            ) : (
              <span className="text-[9px] text-[#1A7F4B] font-medium">Cleared</span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function AgentFeedItem({ item }: { item: AgentActivity }) {
  const cfg = AGENT_STATUS_CONFIG[item.status];
  return (
    <div className="flex items-start gap-2 py-2 border-b border-border/50 last:border-0">
      <div className="flex-shrink-0 mt-0.5 relative">
        <div className="w-2 h-2 rounded-full" style={{ background: cfg.color }} />
        {cfg.pulse && (
          <div className="absolute inset-0 rounded-full animate-ping" style={{ background: cfg.color, opacity: 0.3 }} />
        )}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-[10px] font-mono font-semibold text-foreground">{item.agent}</p>
        <p className="text-[10px] text-muted-foreground truncate">{item.task}</p>
      </div>
      <span className="text-[9px] text-muted-foreground flex-shrink-0">{item.ts}</span>
    </div>
  );
}

// ── Mini SRI sparkline (SVG) ────────────────────────────────────────────────

function SriSparkline() {
  const data = [42, 47, 53, 58, 61, 65, 68, 72, 74, 71, 76, 78];
  const W = 300, H = 60, PAD = 8;
  const max = Math.max(...data); const min = Math.min(...data);
  const xS = (i: number) => PAD + (i / (data.length - 1)) * (W - PAD * 2);
  const yS = (v: number) => PAD + (1 - (v - min) / (max - min || 1)) * (H - PAD * 2);
  const path = data.map((v, i) => `${i === 0 ? "M" : "L"} ${xS(i)} ${yS(v)}`).join(" ");
  const area = `${path} L ${xS(data.length - 1)} ${H - PAD} L ${xS(0)} ${H - PAD} Z`;
  return (
    <svg width="100%" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
      <defs>
        <linearGradient id="sri-grad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#1A7F4B" stopOpacity="0.3" />
          <stop offset="100%" stopColor="#1A7F4B" stopOpacity="0.03" />
        </linearGradient>
      </defs>
      <path d={area} fill="url(#sri-grad)" />
      <path d={path} fill="none" stroke="#1A7F4B" strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
      <circle cx={xS(data.length - 1)} cy={yS(data[data.length - 1])} r={3} fill="#1A7F4B" />
    </svg>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const activeProjects = PROJECTS.filter(p => p.status !== "cleared");
  const avgSri = Math.round(PROJECTS.reduce((s, p) => s + p.sri, 0) / PROJECTS.length);
  const inFdaReview = PROJECTS.filter(p => p.stage === "FDA_REVIEW" || p.stage === "SUBMIT").length;

  return (
    <div className="min-h-screen bg-background">
      {/* Page header */}
      <div className="border-b border-border px-6 py-4">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div>
            <h1 className="text-lg font-bold text-foreground">Dashboard</h1>
            <p className="text-[11px] text-muted-foreground mt-0.5">
              Medical Device Regulatory Platform — active projects and agent status
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button className="text-[11px] px-4 py-2 bg-[#005EA2] text-white rounded-lg font-semibold hover:bg-[#005EA2]/90 transition-colors cursor-pointer">
              + New Project
            </button>
            <button className="text-[11px] px-4 py-2 border border-border rounded-lg text-muted-foreground hover:bg-muted transition-colors cursor-pointer">
              Run Research
            </button>
          </div>
        </div>
      </div>

      <div className="px-6 py-5 space-y-6 max-w-7xl mx-auto">
        {/* KPI row */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <KpiCard label="Active Projects"     value={activeProjects.length.toString()}       sub="in pipeline"                    />
          <KpiCard label="In FDA Review"       value={inFdaReview.toString()}                 sub="awaiting decision"              />
          <KpiCard label="Avg SRI Score"       value={`${avgSri}/100`}                        sub="submission readiness"           color="text-[#1A7F4B]" />
          <KpiCard label="Agents Running"
            value={AGENT_FEED.filter(a => a.status === "running").length.toString()}
            sub="background tasks"            color="text-[#005EA2]" />
        </div>

        {/* Main layout: projects (left) + agent feed (right) */}
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-5">
          {/* Projects */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-[13px] font-semibold text-foreground">Projects</h2>
              <a href="/projects" className="text-[10px] text-[#005EA2] hover:underline cursor-pointer">
                View all →
              </a>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {PROJECTS.map(p => <ProjectCard key={p.id} project={p} />)}
            </div>
          </div>

          {/* Right column: agent feed + SRI trend */}
          <div className="space-y-4">
            {/* Agent activity */}
            <div className="rounded-xl border border-border bg-card p-4">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-[13px] font-semibold text-foreground">Agent Activity</h2>
                <a href="/agents" className="text-[10px] text-[#005EA2] hover:underline cursor-pointer">
                  Mission control →
                </a>
              </div>
              <div>
                {AGENT_FEED.map(a => <AgentFeedItem key={a.id} item={a} />)}
              </div>
            </div>

            {/* SRI trend */}
            <div className="rounded-xl border border-border bg-card p-4">
              <div className="flex items-center justify-between mb-2">
                <h2 className="text-[13px] font-semibold text-foreground">SRI Trend</h2>
                <span className="text-[10px] text-[#1A7F4B] font-mono font-bold">{avgSri}/100</span>
              </div>
              <p className="text-[10px] text-muted-foreground mb-3">Submission Readiness Index — last 12 months</p>
              <SriSparkline />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
