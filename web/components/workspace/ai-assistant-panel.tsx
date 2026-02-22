"use client";

/**
 * FDA-240 — AIAssistantPanel
 * Collapsible right-side chat panel providing AI context assistance during
 * NPD workspace sessions.  The panel is collapsed to an icon strip on mobile.
 *
 * In Sprint 4+ this will wire to the /api/chat endpoint; for now it shows
 * a placeholder UI so the layout is complete.
 */

import * as React from "react";
import {
  Bot,
  ChevronRight,
  ChevronLeft,
  Send,
  Sparkles,
  ExternalLink,
  FileText,
  Search,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { NpdStage } from "@/lib/api-client";
import { NPD_STAGES } from "./pipeline-navigator";

// ── Types ─────────────────────────────────────────────────────────────────────

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: { title: string; url?: string }[];
  timestamp: Date;
}

interface AIAssistantPanelProps {
  stage: NpdStage;
  projectName?: string;
  className?: string;
}

// ── Suggested prompts per stage ───────────────────────────────────────────────

const STAGE_PROMPTS: Partial<Record<NpdStage, string[]>> = {
  CONCEPT:    ["Help me write device design inputs", "What are the intended use requirements?"],
  CLASSIFY:   ["Classify my device", "What CFR part applies?", "Is this Class II?"],
  PREDICATE:  ["Find predicate devices for me", "What makes a good predicate?"],
  PATHWAY:    ["Should I file 510(k) or De Novo?", "What is the Q-Sub process?"],
  PRESUB:     ["Draft my pre-sub questions", "What should I ask FDA?"],
  TESTING:    ["What standards apply to my device?", "Do I need biocompatibility?"],
  DRAFTING:   ["Draft my 510(k) summary", "Generate the device description section"],
  REVIEW:     ["Check my submission for completeness", "Run a consistency check"],
  SUBMIT:     ["How do I submit via eSTAR?", "What is the submission checklist?"],
  FDA_REVIEW: ["What are common AI queries for this device type?", "Draft an AI response"],
  CLEARED:    ["What labeling changes are needed?", "Generate clearance announcement"],
  POST_MARKET:["What MDRs are required?", "Set up PMS surveillance plan"],
};

// ── Component ─────────────────────────────────────────────────────────────────

export function AIAssistantPanel({
  stage,
  projectName,
  className,
}: AIAssistantPanelProps) {
  const [collapsed, setCollapsed] = React.useState(false);
  const [input, setInput]         = React.useState("");
  const [messages, setMessages]   = React.useState<ChatMessage[]>([]);
  const scrollRef                 = React.useRef<HTMLDivElement>(null);

  const stageInfo  = NPD_STAGES.find((s) => s.stage === stage);
  const prompts    = STAGE_PROMPTS[stage] ?? [];

  // Scroll to bottom on new messages
  React.useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  function sendMessage(text: string) {
    if (!text.trim()) return;

    const userMsg: ChatMessage = {
      id:        crypto.randomUUID(),
      role:      "user",
      content:   text.trim(),
      timestamp: new Date(),
    };

    // Placeholder assistant response (Sprint 5+ wires to real LLM)
    const assistantMsg: ChatMessage = {
      id:        crypto.randomUUID(),
      role:      "assistant",
      content:   `I'm analyzing your question about the **${stageInfo?.label}** stage for "${projectName ?? "this project"}". Full AI responses will be available when the LLM integration is enabled in Sprint 5.`,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setInput("");
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  }

  // ── Collapsed strip ──────────────────────────────────────────────────────────
  if (collapsed) {
    return (
      <aside
        className={cn(
          "flex flex-col items-center gap-4 py-4 px-2 border-l border-border bg-background",
          className,
        )}
      >
        <button
          onClick={() => setCollapsed(false)}
          className="p-1.5 rounded hover:bg-muted transition-colors"
          title="Expand AI Assistant"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>
        <Bot   className="w-5 h-5 text-primary"     title="AI Assistant" />
        <FileText className="w-5 h-5 text-muted-foreground" title="Sources" />
        <Search   className="w-5 h-5 text-muted-foreground" title="Search" />
      </aside>
    );
  }

  // ── Expanded panel ────────────────────────────────────────────────────────────
  return (
    <aside
      className={cn(
        "flex flex-col border-l border-border bg-background",
        className,
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-3 border-b border-border">
        <div className="flex items-center gap-2">
          <Bot className="w-4 h-4 text-primary" />
          <span className="text-sm font-semibold text-foreground">AI Assistant</span>
          <Sparkles className="w-3 h-3 text-amber-400" />
        </div>
        <button
          onClick={() => setCollapsed(true)}
          className="p-1 rounded hover:bg-muted transition-colors"
          title="Collapse"
        >
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>

      {/* Stage context chip */}
      <div className="px-3 py-2 border-b border-border bg-muted/30">
        <p className="text-xs text-muted-foreground">
          Context: <span className="font-medium text-foreground">{stageInfo?.label}</span>
        </p>
        <p className="text-xs text-muted-foreground mt-0.5 leading-tight">
          {stageInfo?.description}
        </p>
      </div>

      {/* Message list */}
      <ScrollArea className="flex-1" ref={scrollRef as React.RefObject<HTMLDivElement>}>
        <div className="flex flex-col gap-3 p-3">
          {messages.length === 0 ? (
            <div className="text-center py-6">
              <Bot className="w-8 h-8 text-muted-foreground mx-auto mb-2 opacity-50" />
              <p className="text-xs text-muted-foreground">
                Ask a question or choose a suggestion below
              </p>
            </div>
          ) : (
            messages.map((msg) => (
              <div
                key={msg.id}
                className={cn(
                  "rounded-lg px-3 py-2 text-sm max-w-[90%]",
                  msg.role === "user"
                    ? "self-end bg-primary text-primary-foreground ml-4"
                    : "self-start bg-muted text-foreground mr-4",
                )}
              >
                <p className="leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                {msg.sources && msg.sources.length > 0 && (
                  <ul className="mt-1.5 flex flex-col gap-1">
                    {msg.sources.map((src) => (
                      <li key={src.title}>
                        {src.url ? (
                          <a
                            href={src.url}
                            target="_blank"
                            rel="noreferrer"
                            className="flex items-center gap-1 text-xs text-primary underline"
                          >
                            <ExternalLink className="w-3 h-3 flex-shrink-0" />
                            {src.title}
                          </a>
                        ) : (
                          <span className="text-xs text-muted-foreground">
                            {src.title}
                          </span>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            ))
          )}
        </div>
      </ScrollArea>

      {/* Suggested prompts */}
      {prompts.length > 0 && messages.length === 0 && (
        <div className="px-3 pb-2 flex flex-wrap gap-1.5">
          {prompts.slice(0, 3).map((p) => (
            <button
              key={p}
              onClick={() => sendMessage(p)}
              className="text-xs border border-border rounded-full px-2.5 py-1 hover:bg-muted transition-colors text-muted-foreground hover:text-foreground truncate max-w-full"
            >
              {p}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <div className="px-3 pb-3 pt-2 border-t border-border">
        <div className="flex items-end gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask anything about this stage…"
            rows={2}
            className="flex-1 resize-none rounded-lg border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-0"
          />
          <Button
            size="icon"
            onClick={() => sendMessage(input)}
            disabled={!input.trim()}
            className="flex-shrink-0"
          >
            <Send className="w-4 h-4" />
            <span className="sr-only">Send</span>
          </Button>
        </div>
        <p className="mt-1.5 text-xs text-muted-foreground/60">
          Enter to send · Shift+Enter for newline
        </p>
      </div>
    </aside>
  );
}
