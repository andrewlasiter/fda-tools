/**
 * FDA-250 / FDA-251 / FDA-252 / FDA-253  [FE-012–FE-015] Document Studio
 * =========================================================================
 * Three-panel 510(k) section editor (Sprint 7 + Sprint 8):
 *  - Left  (flex-1):   TipTap rich-text editor with auto-save (FDA-250)
 *  - Right (w-80):     Two-tab sidebar:
 *       "AI"      → AI inline suggestions, accept/reject (FDA-251)
 *       "History" → Version history with LCS diff view (FDA-253)
 *  - Bottom drawer:    eSTAR XML preview pane, collapsible (FDA-252)
 *
 * Suggestion application
 * ----------------------
 * When a suggestion is accepted the parent updates `content` state,
 * which flows into DocumentEditor as `initialContent`.  DocumentEditor
 * watches the prop and calls `editor.commands.setContent(html)` when it
 * detects a change (see its internal useEffect).
 *
 * - Non-empty originalText → regex-replace first match in current HTML
 * - Empty originalText     → append as a new paragraph
 *
 * Version capture
 * ---------------
 * `captureVersion(html)` is called from `handleSave` so every successful
 * save snapshots the document state for diffing.
 */

"use client";

import { useState, useCallback } from "react";
import { useParams }             from "next/navigation";
import Link                      from "next/link";
import {
  ArrowLeft, Download, Layers, Sparkles, Clock,
} from "lucide-react";
import { Button }          from "@/components/ui/button";
import { DocumentEditor }  from "@/components/editor/document-editor";
import {
  AiSuggestionsPanel,
  DEMO_SUGGESTIONS,
  type AiSuggestion,
} from "@/components/editor/ai-suggestions";
import { EstarPreview }    from "@/components/editor/estar-preview";
import {
  VersionHistory,
  useVersionHistory,
} from "@/components/editor/version-history";
import { cn } from "@/lib/utils";

// ── Section display names ─────────────────────────────────────────────────────

const SECTION_NAMES: Record<string, string> = {
  "intended-use":         "Intended Use",
  "device-desc":          "Device Description",
  "substantial-equiv":    "Substantial Equivalence",
  "performance-testing":  "Performance Testing",
  "biocompatibility":     "Biocompatibility",
  "sterility":            "Sterility",
  "labeling":             "Labeling",
};

function getSectionName(id: string): string {
  return SECTION_NAMES[id] ?? id.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

// ── Sidebar tab type ──────────────────────────────────────────────────────────

type SidebarTab = "ai" | "history";

// ── Page ─────────────────────────────────────────────────────────────────────

export default function DocumentStudioPage() {
  const params     = useParams();
  const sectionId  = typeof params.id === "string" ? params.id : "default";
  const sectionName = getSectionName(sectionId);

  // Editor HTML content — shared between editor, eSTAR preview, and suggestion applicator
  const [content,      setContent]      = useState("");
  const [suggestions,  setSuggestions]  = useState<AiSuggestion[]>(DEMO_SUGGESTIONS);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [sidebarTab,   setSidebarTab]   = useState<SidebarTab>("ai");

  // Version history
  const { versions, captureVersion } = useVersionHistory(20);

  // ── Suggestion handlers ───────────────────────────────────────────────────

  const handleAccept = useCallback((suggestion: AiSuggestion) => {
    // Mark as accepted
    setSuggestions((prev) =>
      prev.map((s) => s.id === suggestion.id ? { ...s, status: "accepted" as const } : s),
    );

    // Apply text to editor content
    setContent((prev) => {
      const base = prev || "";
      if (!suggestion.originalText) {
        // Insertion — append as new paragraph
        return base + `<p>${suggestion.proposedText}</p>`;
      }
      // Replacement — substitute first case-insensitive occurrence
      const escaped  = suggestion.originalText.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      const replaced = base.replace(new RegExp(escaped, "i"), suggestion.proposedText);
      // Fallback: if original text not found in current HTML, append
      return replaced !== base ? replaced : base + `<p>${suggestion.proposedText}</p>`;
    });
  }, []);

  const handleReject = useCallback((id: string) => {
    setSuggestions((prev) =>
      prev.map((s) => s.id === id ? { ...s, status: "rejected" as const } : s),
    );
  }, []);

  // Simulate re-generating suggestions (demo — resets to pending)
  const handleRefresh = () => {
    setIsRefreshing(true);
    setTimeout(() => {
      setSuggestions(DEMO_SUGGESTIONS.map((s) => ({ ...s, status: "pending" as const })));
      setIsRefreshing(false);
    }, 1200);
  };

  // ── Save handler: persists content + captures version snapshot ────────────

  const handleSave = async (html: string): Promise<void> => {
    // Production: POST /documents/{sectionId}
    await new Promise<void>((resolve) => setTimeout(resolve, 400));
    captureVersion(html);
  };

  // ── Restore from version history ─────────────────────────────────────────

  const handleRestore = useCallback(
    (version: { html: string }) => {
      setContent(version.html);
    },
    [],
  );

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <header className="flex-shrink-0 flex items-center justify-between gap-4 border-b border-border bg-background px-4 py-3">
        <div className="flex items-center gap-3 min-w-0">
          <Link
            href="/documents"
            className="rounded p-1 hover:bg-muted transition-colors flex-shrink-0"
            title="Back to documents"
          >
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <div className="min-w-0">
            <h1 className="font-heading font-semibold text-foreground truncate text-sm sm:text-base">
              {sectionName}
            </h1>
            <p className="text-xs text-muted-foreground">
              Document Studio · 510(k) Submission
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 flex-shrink-0">
          <Button variant="outline" size="sm" className="h-8 gap-1.5 text-xs">
            <Download className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Export</span>
          </Button>
          <Link href="/documents">
            <Button size="sm" variant="ghost" className="h-8 gap-1.5 text-xs">
              <Layers className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">All Sections</span>
            </Button>
          </Link>
        </div>
      </header>

      {/* ── Main area: editor + sidebar ─────────────────────────────────────── */}
      <div className="flex flex-1 min-h-0 overflow-hidden">

        {/* Left: rich text editor + eSTAR preview below */}
        <main className="flex-1 min-w-0 flex flex-col overflow-hidden bg-muted/10">
          {/* Editor scrolls independently */}
          <div className="flex-1 min-h-0 overflow-y-auto p-4 sm:p-6">
            <DocumentEditor
              key={sectionId}
              initialContent={content}
              sectionType={sectionId}
              onSave={handleSave}
              onChange={setContent}
            />
          </div>

          {/* eSTAR XML preview — collapsible panel anchored to bottom of editor area */}
          <div className="flex-shrink-0 border-t border-border px-4 py-3 bg-background">
            <EstarPreview
              htmlContent={content}
              sectionType={sectionId}
              deviceName="Subject Device"
              submissionId="K000000"
            />
          </div>
        </main>

        {/* Right: tabbed sidebar — AI suggestions + Version history */}
        <aside className="hidden lg:flex flex-col w-80 flex-shrink-0 border-l border-border bg-card overflow-hidden">
          {/* Sidebar tab bar */}
          <div className="flex-shrink-0 flex border-b border-border">
            <button
              onClick={() => setSidebarTab("ai")}
              className={cn(
                "flex-1 flex items-center justify-center gap-1.5 py-2.5 text-xs font-medium border-b-2 transition-colors",
                sidebarTab === "ai"
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground",
              )}
            >
              <Sparkles className="h-3.5 w-3.5" />
              AI Suggestions
            </button>
            <button
              onClick={() => setSidebarTab("history")}
              className={cn(
                "flex-1 flex items-center justify-center gap-1.5 py-2.5 text-xs font-medium border-b-2 transition-colors",
                sidebarTab === "history"
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground",
              )}
            >
              <Clock className="h-3.5 w-3.5" />
              History
            </button>
          </div>

          {/* Sidebar content */}
          <div className="flex-1 overflow-y-auto p-4">
            {sidebarTab === "ai" && (
              <AiSuggestionsPanel
                suggestions={suggestions}
                isLoading={isRefreshing}
                onAccept={handleAccept}
                onReject={handleReject}
                onRefresh={handleRefresh}
              />
            )}
            {sidebarTab === "history" && (
              <VersionHistory
                versions={versions}
                onRestore={handleRestore}
              />
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}
