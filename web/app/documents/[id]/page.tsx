/**
 * FDA-250 / FDA-251  [FE-012 + FE-013] Document Studio
 * ======================================================
 * Two-panel 510(k) section editor:
 *  - Left  (flex-1): TipTap rich-text editor with auto-save
 *  - Right (w-80):   AI inline suggestions panel (accept/reject)
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
 */

"use client";

import { useState, useCallback } from "react";
import { useParams }             from "next/navigation";
import Link                      from "next/link";
import {
  ArrowLeft, Download, FileCode2, Layers,
} from "lucide-react";
import { Button }          from "@/components/ui/button";
import { DocumentEditor }  from "@/components/editor/document-editor";
import {
  AiSuggestionsPanel,
  DEMO_SUGGESTIONS,
  type AiSuggestion,
} from "@/components/editor/ai-suggestions";

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

// ── Page ─────────────────────────────────────────────────────────────────────

export default function DocumentStudioPage() {
  const params     = useParams();
  const sectionId  = typeof params.id === "string" ? params.id : "default";
  const sectionName = getSectionName(sectionId);

  // Editor HTML content — shared between editor and suggestion applicator
  const [content,      setContent]      = useState("");
  const [suggestions,  setSuggestions]  = useState<AiSuggestion[]>(DEMO_SUGGESTIONS);
  const [isRefreshing, setIsRefreshing] = useState(false);

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

  // Auto-save (demo — in production: POST /documents/{sectionId})
  const handleSave = async (_html: string): Promise<void> => {
    await new Promise<void>((resolve) => setTimeout(resolve, 400));
  };

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
            <FileCode2 className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Preview XML</span>
          </Button>
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

      {/* ── Two-panel body ──────────────────────────────────────────────────── */}
      <div className="flex flex-1 min-h-0 overflow-hidden">

        {/* Left: rich text editor */}
        <main className="flex-1 min-w-0 overflow-y-auto bg-muted/10 p-4 sm:p-6">
          <DocumentEditor
            key={sectionId}
            initialContent={content}
            sectionType={sectionId}
            onSave={handleSave}
            onChange={setContent}
          />
        </main>

        {/* Right: AI suggestions panel */}
        <aside className="hidden lg:flex flex-col w-80 flex-shrink-0 border-l border-border bg-card overflow-y-auto p-4">
          <AiSuggestionsPanel
            suggestions={suggestions}
            isLoading={isRefreshing}
            onAccept={handleAccept}
            onReject={handleReject}
            onRefresh={handleRefresh}
          />
        </aside>
      </div>
    </div>
  );
}
