"use client";

/**
 * FDA-273 [FE-019] — NPD Workspace Page
 * =======================================
 * /projects/[id] — 12-stage NPD pipeline workspace.
 *
 * 3-panel layout:
 *   LEFT  (240px) — Stage navigator with status dots
 *   MAIN  (flex)  — Stage content panel (AI output + documents)
 *   RIGHT (300px) — AI assistant chat + context sources
 */

import React, { useState } from "react";
import { useParams } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

// ── Types & constants ─────────────────────────────────────────────────────

type StageStatus = "completed" | "active" | "pending";

interface NpdStage {
  key:         string;
  label:       string;
  description: string;
  status:      StageStatus;
  sri:         number;
  completion:  number;
}

const NPD_STAGES: NpdStage[] = [
  { key:"CONCEPT",     label:"Concept",        description:"Define device concept, intended use, and initial risk classification",   status:"completed", sri:10, completion:100 },
  { key:"CLASSIFY",    label:"Classify",       description:"Determine device class (I/II/III) and regulatory pathway",              status:"completed", sri:8,  completion:100 },
  { key:"PREDICATE",   label:"Predicate",      description:"Identify and validate predicate 510(k) devices for SE argument",       status:"completed", sri:20, completion:100 },
  { key:"PATHWAY",     label:"Pathway",        description:"Select regulatory pathway: Traditional 510(k), Abbreviated, Special",   status:"completed", sri:5,  completion:100 },
  { key:"PRESUB",      label:"Pre-Sub",        description:"Prepare and submit Q-Sub for FDA feedback on key regulatory questions", status:"completed", sri:8,  completion:100 },
  { key:"TESTING",     label:"Testing",        description:"Design and execute performance, safety, and biocompat testing",         status:"active",    sri:20, completion:55 },
  { key:"DRAFTING",    label:"Drafting",       description:"Draft all 510(k) submission sections (SE table, IFU, labeling, eSTAR)",status:"pending",   sri:15, completion:0  },
  { key:"REVIEW",      label:"Internal Review",description:"RA team quality review — SRI check, RTA screening, completeness gate", status:"pending",   sri:5,  completion:0  },
  { key:"SUBMIT",      label:"Submit",         description:"eCopy submission via FDA CDRH ePortal — generate eCopy, track receipt", status:"pending",  sri:0,  completion:0  },
  { key:"FDA_REVIEW",  label:"FDA Review",     description:"Track FDA review clock, respond to AI and deficiency letters",         status:"pending",   sri:0,  completion:0  },
  { key:"CLEARED",     label:"Cleared",        description:"510(k) clearance received — archive submission, update device profile",status:"pending",   sri:0,  completion:0  },
  { key:"POST_MARKET", label:"Post-Market",    description:"MDR monitoring, recall tracking, complaint handling, MAUDE surveillance",status:"pending", sri:0,  completion:0  },
];

// ── Mock data ─────────────────────────────────────────────────────────────

const MOCK_PROJECT = {
  id:       "p1",
  name:     "NextGen Glucose Monitor",
  code:     "DQY",
  class:    "II",
  pathway:  "Traditional 510(k)",
  deadline: "2026-03-15",
  sri:      78,
};

const MOCK_STAGE_CONTENT: Record<string, { title: string; items: string[] }> = {
  TESTING: {
    title: "Testing Protocols & Evidence",
    items: [
      "Biocompatibility testing matrix (ISO 10993-1) — 8/12 studies complete",
      "Electrical safety (IEC 60601-1) — bench testing in progress",
      "EMC testing (IEC 60601-1-2) — scheduled for 2026-02-28",
      "Accuracy testing (ISO 15197) — 3 studies complete, 2 pending",
      "Sterilization validation (ISO 11137) — N/A (single-use, non-sterile)",
    ],
  },
  DRAFTING: {
    title: "Submission Sections",
    items: [
      "Section 1: Indications for Use — Draft ready",
      "Section 2: Device Description — In progress",
      "Section 3: SE Table — AI draft generated",
      "Section 4: Performance Testing — Pending test reports",
      "Section 5: Labeling — Not started",
    ],
  },
};

const MOCK_CHAT = [
  {
    role: "assistant" as const,
    text: "Welcome to the NextGen Glucose Monitor workspace. You're currently in the **TESTING** stage. I can see 8/12 biocompatibility studies are complete. What would you like to work on?",
  },
  {
    role: "user" as const,
    text: "What's blocking us from reaching SRI 80?",
  },
  {
    role: "assistant" as const,
    text: "Your current SRI is **78/100**. The 3 main gaps to reach 80:\n\n1. **EMC test report** missing (IEC 60601-1-2) — worth +4 pts\n2. **SE table gaps**: electrode material specs differ from predicate K193726 — fix adds +2 pts\n3. **Accuracy study** CNT-2024-003 not uploaded yet — +2 pts\n\nFixing gap #1 alone will push you to 82.",
  },
];

const MOCK_SOURCES = [
  { label: "IEC 60601-1-2:2014",       type: "Standard",  href: "#" },
  { label: "K193726 — GlucoSense Pro",  type: "Predicate", href: "#" },
  { label: "ISO 15197:2013",            type: "Standard",  href: "#" },
  { label: "FDA Guidance: CGM 2016",    type: "Guidance",  href: "#" },
];

// ── Sub-components ────────────────────────────────────────────────────────

function StageNav({
  stages,
  activeKey,
  onSelect,
}: {
  stages: NpdStage[];
  activeKey: string;
  onSelect: (key: string) => void;
}) {
  return (
    <nav className="overflow-y-auto">
      {stages.map((stage, idx) => {
        const isActive = stage.key === activeKey;
        return (
          <button
            key={stage.key}
            onClick={() => onSelect(stage.key)}
            className={cn(
              "w-full flex items-start gap-3 px-4 py-3 text-left transition-all border-l-2",
              isActive
                ? "border-[#005EA2] bg-[#005EA2]/5"
                : "border-transparent hover:bg-muted/50",
            )}
          >
            {/* Stage number + status dot */}
            <div className="flex flex-col items-center gap-1 mt-0.5">
              <div className={cn(
                "w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 text-[9px] font-bold",
                stage.status === "completed" ? "bg-[#1A7F4B] text-white" :
                stage.status === "active"    ? "bg-[#005EA2] text-white ring-2 ring-[#005EA2]/30" :
                "bg-muted text-muted-foreground"
              )}>
                {stage.status === "completed" ? "✓" : idx + 1}
              </div>
              {/* Connector line */}
              {idx < stages.length - 1 && (
                <div className={cn(
                  "w-0.5 h-4",
                  stage.status === "completed" ? "bg-[#1A7F4B]/40" : "bg-border"
                )} />
              )}
            </div>

            {/* Stage info */}
            <div className="flex-1 min-w-0 pb-1">
              <p className={cn(
                "text-xs font-medium leading-tight",
                isActive ? "text-[#005EA2]" : stage.status === "completed" ? "text-foreground" : "text-muted-foreground"
              )}>
                {stage.label}
              </p>
              {isActive && (
                <div className="mt-1">
                  <div className="flex items-center justify-between text-[9px] text-muted-foreground mb-0.5">
                    <span>{stage.completion}%</span>
                    <span>SRI +{stage.sri}</span>
                  </div>
                  <div className="h-1 bg-border rounded-full overflow-hidden">
                    <div
                      className="h-full bg-[#005EA2] rounded-full transition-all"
                      style={{ width: `${stage.completion}%` }}
                    />
                  </div>
                </div>
              )}
            </div>
          </button>
        );
      })}
    </nav>
  );
}

function StageContent({ stage }: { stage: NpdStage }) {
  const content = MOCK_STAGE_CONTENT[stage.key];

  return (
    <div className="p-6 space-y-6">
      {/* Stage header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Badge
              variant={stage.status === "active" ? "default" : stage.status === "completed" ? "success" : "secondary"}
              className="text-[10px]"
            >
              {stage.status === "completed" ? "Complete" : stage.status === "active" ? "In Progress" : "Pending"}
            </Badge>
            <span className="text-xs text-muted-foreground">Stage {NPD_STAGES.findIndex(s => s.key === stage.key) + 1} of {NPD_STAGES.length}</span>
          </div>
          <h2 className="text-xl font-bold font-heading text-foreground">{stage.label}</h2>
          <p className="text-sm text-muted-foreground mt-1 max-w-prose">{stage.description}</p>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <Button variant="outline" size="sm" className="text-xs h-8">Run Agent</Button>
          <Button size="sm" className="bg-[#005EA2] hover:bg-[#003E73] text-white text-xs h-8">Generate Draft</Button>
        </div>
      </div>

      {/* Progress */}
      {stage.status === "active" && (
        <div>
          <div className="flex items-center justify-between text-xs text-muted-foreground mb-1.5">
            <span>Stage completion</span>
            <span className="font-medium text-foreground">{stage.completion}%</span>
          </div>
          <div className="h-2 bg-muted rounded-full overflow-hidden">
            <div
              className="h-full bg-[#005EA2] rounded-full transition-all duration-500"
              style={{ width: `${stage.completion}%` }}
            />
          </div>
        </div>
      )}

      {/* Content items */}
      {content ? (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">{content.title}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {content.items.map((item, i) => (
              <div key={i} className="flex items-start gap-2.5 py-2 border-b border-border last:border-0">
                <div className={cn(
                  "w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0",
                  item.includes("complete") || item.includes("ready") ? "bg-[#1A7F4B]" :
                  item.includes("progress") || item.includes("in progress") ? "bg-[#005EA2]" :
                  item.includes("N/A") ? "bg-muted-foreground/40" :
                  "bg-[#B45309]"
                )} />
                <p className="text-sm text-foreground">{item}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      ) : (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center justify-center py-16 text-center">
            <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center mb-4">
              <span className="text-2xl">🔒</span>
            </div>
            <h3 className="text-sm font-medium text-foreground mb-1">Stage Locked</h3>
            <p className="text-xs text-muted-foreground max-w-xs">
              Complete the preceding stages to unlock {stage.label}. Current stage: <strong>Testing</strong>.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function AiAssistant({
  messages,
  sources,
}: {
  messages: (typeof MOCK_CHAT);
  sources: typeof MOCK_SOURCES;
}) {
  const [input, setInput] = useState("");

  return (
    <div className="flex flex-col h-full">
      <div className="px-4 py-3 border-b border-border">
        <p className="text-xs font-semibold text-foreground">AI Assistant</p>
        <p className="text-[10px] text-muted-foreground">Context-aware regulatory guidance</p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={cn(
              "text-xs leading-relaxed rounded-lg p-3",
              msg.role === "assistant"
                ? "bg-[#005EA2]/5 border border-[#005EA2]/10"
                : "bg-muted ml-4"
            )}
          >
            {msg.role === "assistant" && (
              <p className="text-[9px] font-bold text-[#005EA2] mb-1 uppercase tracking-wider">FDA Assistant</p>
            )}
            <p className="text-foreground whitespace-pre-line">{msg.text}</p>
          </div>
        ))}
      </div>

      {/* Suggested questions */}
      <div className="px-4 py-2 border-t border-border">
        <p className="text-[9px] text-muted-foreground uppercase tracking-wider mb-1.5">Suggested</p>
        <div className="space-y-1">
          {["What's blocking SRI 80?","Generate test protocol","Check SE completeness"].map(q => (
            <button
              key={q}
              onClick={() => setInput(q)}
              className="block w-full text-left text-[10px] text-muted-foreground hover:text-foreground px-2 py-1 rounded hover:bg-muted transition-colors"
            >
              → {q}
            </button>
          ))}
        </div>
      </div>

      {/* Input */}
      <div className="px-4 py-3 border-t border-border">
        <div className="flex gap-2">
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            placeholder="Ask about this stage..."
            className="flex-1 text-xs bg-muted rounded-md px-3 py-2 outline-none border border-transparent focus:border-[#005EA2] transition-colors"
          />
          <Button size="sm" className="h-8 bg-[#005EA2] hover:bg-[#003E73] text-white px-3 text-xs">
            Send
          </Button>
        </div>
      </div>

      {/* Context sources */}
      <div className="px-4 pb-4">
        <p className="text-[9px] text-muted-foreground uppercase tracking-wider mb-2">Sources</p>
        <div className="space-y-1">
          {sources.map(src => (
            <div key={src.label} className="flex items-center gap-2">
              <Badge variant="outline" className="text-[9px] h-4 px-1">{src.type}</Badge>
              <span className="text-[10px] text-muted-foreground truncate">{src.label}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────

export default function ProjectWorkspacePage() {
  const { id } = useParams<{ id: string }>();
  const [activeStageKey, setActiveStageKey] = useState<string>("TESTING");
  const activeStage = NPD_STAGES.find(s => s.key === activeStageKey)!;

  return (
    <div className="flex h-full overflow-hidden">

      {/* ── Left: Stage navigator ──────────────────────────────────── */}
      <aside className="w-[220px] flex-shrink-0 border-r border-border overflow-y-auto bg-muted/20">
        {/* Project header */}
        <div className="px-4 py-4 border-b border-border">
          <p className="text-xs font-semibold text-foreground truncate">{MOCK_PROJECT.name}</p>
          <div className="flex items-center gap-1.5 mt-1">
            <Badge variant="secondary" className="text-[9px] h-4 px-1">Class {MOCK_PROJECT.class}</Badge>
            <span className="text-[10px] text-muted-foreground">{MOCK_PROJECT.code}</span>
          </div>
        </div>
        {/* Pipeline stages */}
        <StageNav
          stages={NPD_STAGES}
          activeKey={activeStageKey}
          onSelect={setActiveStageKey}
        />
      </aside>

      {/* ── Center: Stage content ──────────────────────────────────── */}
      <main className="flex-1 overflow-y-auto min-w-0">
        <StageContent stage={activeStage} />
      </main>

      {/* ── Right: AI assistant ────────────────────────────────────── */}
      <aside className="w-[280px] flex-shrink-0 border-l border-border overflow-hidden flex flex-col bg-muted/10">
        <AiAssistant messages={MOCK_CHAT} sources={MOCK_SOURCES} />
      </aside>
    </div>
  );
}
