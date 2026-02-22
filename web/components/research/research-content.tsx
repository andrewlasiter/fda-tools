"use client";

/**
 * FDA-241  [FE-008] Research Hub — Unified semantic search
 * =========================================================
 * Single page that combines 510(k) clearances, FDA guidance (semantic),
 * MAUDE adverse events, and recalls into one debounced search experience.
 *
 * Architecture:
 *  - Source toggles control which data streams are active
 *  - Guidance uses POST /research/search (pgvector cosine similarity)
 *  - Other sources use GET /research?q= (unified backend, Sprint 6+)
 *  - Recent searches stored in localStorage
 *  - Debounced 300 ms to avoid hammering the API on every keystroke
 */

import * as React from "react";
import {
  Search,
  X,
  ExternalLink,
  Clock,
  AlertTriangle,
  FileText,
  Database,
  Activity,
  BookOpen,
  Loader2,
  ChevronRight,
  BarChart2,
  Shield,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  useGuidanceSearch,
  useResearch,
  type GuidanceChunkResult,
  type ResearchResult,
} from "@/lib/api-client";
import { cn } from "@/lib/utils";

// ── Types ─────────────────────────────────────────────────────────────────────

type SourceKey = "guidance" | "k510" | "maude" | "recall" | "pubmed";

interface SourceConfig {
  key:   SourceKey;
  label: string;
  icon:  React.ElementType;
  color: string;
}

const SOURCES: SourceConfig[] = [
  { key: "guidance", label: "Guidance",  icon: BookOpen,      color: "text-blue-600 dark:text-blue-400" },
  { key: "k510",     label: "510(k)",    icon: FileText,      color: "text-green-600 dark:text-green-400" },
  { key: "maude",    label: "MAUDE",     icon: Activity,      color: "text-orange-600 dark:text-orange-400" },
  { key: "recall",   label: "Recalls",   icon: Shield,        color: "text-red-600 dark:text-red-400" },
  { key: "pubmed",   label: "PubMed",    icon: Database,      color: "text-purple-600 dark:text-purple-400" },
];

const SOURCE_BADGE_CLASSES: Record<SourceKey, string> = {
  guidance: "bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-950 dark:text-blue-300",
  k510:     "bg-green-50 text-green-700 border-green-200 dark:bg-green-950 dark:text-green-300",
  maude:    "bg-orange-50 text-orange-700 border-orange-200 dark:bg-orange-950 dark:text-orange-300",
  recall:   "bg-red-50 text-red-700 border-red-200 dark:bg-red-950 dark:text-red-300",
  pubmed:   "bg-purple-50 text-purple-700 border-purple-200 dark:bg-purple-950 dark:text-purple-300",
};

// ── Recent searches (localStorage) ───────────────────────────────────────────

const STORAGE_KEY = "mdrp-recent-searches";
const MAX_RECENT  = 8;

function loadRecent(): string[] {
  if (typeof window === "undefined") return [];
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "[]");
  } catch {
    return [];
  }
}

function saveRecent(query: string): void {
  if (typeof window === "undefined") return;
  const prev    = loadRecent().filter((q) => q !== query);
  const updated = [query, ...prev].slice(0, MAX_RECENT);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
}

// ── Sub-components ────────────────────────────────────────────────────────────

function SourceToggle({
  source,
  active,
  onToggle,
}: {
  source:   SourceConfig;
  active:   boolean;
  onToggle: (key: SourceKey) => void;
}) {
  const Icon = source.icon;
  return (
    <button
      type="button"
      onClick={() => onToggle(source.key)}
      className={cn(
        "flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium border transition-all",
        active
          ? cn(SOURCE_BADGE_CLASSES[source.key], "border-current")
          : "border-border text-muted-foreground hover:bg-accent"
      )}
    >
      <Icon className="w-3 h-3" />
      {source.label}
    </button>
  );
}

function GuidanceCard({ result }: { result: GuidanceChunkResult }) {
  return (
    <Card className="hover:shadow-sm transition-shadow">
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className={cn("text-xs font-medium border rounded-full px-2 py-0.5", SOURCE_BADGE_CLASSES.guidance)}>
                Guidance
              </span>
              <span className="text-xs text-muted-foreground">
                {(result.similarity * 100).toFixed(0)}% match
              </span>
              {result.chunk_index > 0 && (
                <span className="text-xs text-muted-foreground">
                  §{result.chunk_index + 1}
                </span>
              )}
            </div>
            <h3 className="font-medium text-sm text-foreground truncate">
              {result.doc_title}
            </h3>
            <p className="text-xs text-muted-foreground mt-1 line-clamp-3">
              {result.content}
            </p>
          </div>
          <div className="flex-shrink-0 flex flex-col items-end gap-2">
            {/* Similarity bar */}
            <div className="w-20 h-1.5 bg-muted rounded-full overflow-hidden">
              <div
                className="h-full bg-blue-500 rounded-full"
                style={{ width: `${result.similarity * 100}%` }}
              />
            </div>
            {result.doc_url && (
              <a
                href={result.doc_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-muted-foreground hover:text-foreground transition-colors"
              >
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function UnifiedResultCard({ result }: { result: ResearchResult }) {
  const source = result.source as SourceKey;
  const cfg    = SOURCES.find((s) => s.key === source);
  const Icon   = cfg?.icon ?? FileText;

  return (
    <Card className="hover:shadow-sm transition-shadow">
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span
                className={cn(
                  "text-xs font-medium border rounded-full px-2 py-0.5",
                  SOURCE_BADGE_CLASSES[source] ?? SOURCE_BADGE_CLASSES.k510
                )}
              >
                <span className="flex items-center gap-1">
                  <Icon className="w-2.5 h-2.5 inline" />
                  {cfg?.label ?? source}
                </span>
              </span>
              <span className="text-xs text-muted-foreground">
                {(result.score * 100).toFixed(0)}% relevance
              </span>
            </div>
            <h3 className="font-medium text-sm text-foreground">{result.title}</h3>
            <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
              {result.snippet}
            </p>
          </div>
          <div className="flex-shrink-0 flex flex-col items-end gap-2">
            <div className="w-20 h-1.5 bg-muted rounded-full overflow-hidden">
              <div
                className={cn("h-full rounded-full", cfg?.color.replace("text-", "bg-").replace(" dark:text-", " dark:bg-") ?? "bg-green-500")}
                style={{ width: `${result.score * 100}%` }}
              />
            </div>
            {result.url && (
              <a
                href={result.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-muted-foreground hover:text-foreground transition-colors"
              >
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function EmptyState({ query }: { query: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <Search className="w-10 h-10 text-muted-foreground/30 mb-4" />
      {query ? (
        <>
          <p className="text-sm font-medium text-foreground">No results found</p>
          <p className="text-xs text-muted-foreground mt-1">
            Try adjusting your search or toggling different sources
          </p>
        </>
      ) : (
        <>
          <p className="text-sm font-medium text-foreground">Start your search</p>
          <p className="text-xs text-muted-foreground mt-1">
            Search across FDA guidance, 510(k) clearances, MAUDE events, recalls, and PubMed
          </p>
        </>
      )}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export function ResearchContent() {
  const [inputValue, setInputValue] = React.useState("");
  const [debouncedQuery, setDebouncedQuery] = React.useState("");
  const [activeSources, setActiveSources] = React.useState<Set<SourceKey>>(
    new Set(["guidance", "k510", "maude"])
  );
  const [recentSearches, setRecentSearches] = React.useState<string[]>([]);
  const [showRecent, setShowRecent] = React.useState(false);
  const inputRef = React.useRef<HTMLInputElement>(null);

  // Load recent on mount (avoids SSR mismatch)
  React.useEffect(() => {
    setRecentSearches(loadRecent());
  }, []);

  // Debounce input → query
  React.useEffect(() => {
    const id = setTimeout(() => setDebouncedQuery(inputValue.trim()), 300);
    return () => clearTimeout(id);
  }, [inputValue]);

  // Guidance semantic search (POST)
  const guidanceSearch = useGuidanceSearch();

  // Unified search (GET, other sources — Sprint 6+ backend)
  const unifiedSearch = useResearch(
    activeSources.has("k510") || activeSources.has("maude") || activeSources.has("recall") || activeSources.has("pubmed")
      ? debouncedQuery
      : "",
  );

  // Trigger guidance search when query changes and guidance is active
  React.useEffect(() => {
    if (debouncedQuery.length >= 2 && activeSources.has("guidance")) {
      guidanceSearch.mutate({
        query:     debouncedQuery,
        top_k:     10,
        threshold: 0.65,
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedQuery, activeSources.has("guidance")]);

  function handleSubmit(q: string) {
    if (!q.trim()) return;
    setInputValue(q);
    setDebouncedQuery(q.trim());
    saveRecent(q.trim());
    setRecentSearches(loadRecent());
    setShowRecent(false);
    if (activeSources.has("guidance")) {
      guidanceSearch.mutate({ query: q.trim(), top_k: 10, threshold: 0.65 });
    }
  }

  function toggleSource(key: SourceKey) {
    setActiveSources((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        if (next.size > 1) next.delete(key);  // keep at least one active
      } else {
        next.add(key);
      }
      return next;
    });
  }

  function clearSearch() {
    setInputValue("");
    setDebouncedQuery("");
    guidanceSearch.reset();
    inputRef.current?.focus();
  }

  const isLoading  = guidanceSearch.isPending || unifiedSearch.isLoading;
  const hasQuery   = debouncedQuery.length >= 2;
  const guidanceResults = guidanceSearch.data?.results ?? [];
  const unifiedResults  = (unifiedSearch.data?.results ?? []).filter(
    (r) => activeSources.has(r.source as SourceKey)
  );
  const totalCount = guidanceResults.length + unifiedResults.length;
  const hasError   = guidanceSearch.isError || unifiedSearch.isError;

  return (
    <div className="flex flex-col h-full">
      {/* ── Header ──────────────────────────────────────────────────────────── */}
      <div className="border-b border-border bg-card px-6 py-5">
        <div className="max-w-4xl mx-auto">
          <div className="mb-4">
            <h1 className="text-2xl font-heading font-bold text-foreground">
              Regulatory Research Hub
            </h1>
            <p className="text-sm text-muted-foreground mt-0.5">
              Semantic search across FDA guidance, 510(k) clearances, MAUDE, recalls, and PubMed
            </p>
          </div>

          {/* Search input */}
          <div className="relative">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <input
              ref={inputRef}
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onFocus={() => setShowRecent(true)}
              onBlur={() => setTimeout(() => setShowRecent(false), 150)}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleSubmit(inputValue);
                if (e.key === "Escape") { clearSearch(); setShowRecent(false); }
              }}
              placeholder="Search guidance documents, predicates, safety signals…"
              className="w-full rounded-xl border border-input bg-background pl-10 pr-10 py-3 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring transition-shadow"
            />
            {isLoading ? (
              <Loader2 className="absolute right-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground animate-spin" />
            ) : inputValue ? (
              <button
                type="button"
                onClick={clearSearch}
                className="absolute right-3.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            ) : null}

            {/* Recent searches dropdown */}
            {showRecent && recentSearches.length > 0 && !inputValue && (
              <div className="absolute top-full left-0 right-0 mt-1 bg-popover border border-border rounded-xl shadow-lg z-50 overflow-hidden">
                <div className="px-3 py-2 text-xs text-muted-foreground font-medium border-b border-border">
                  Recent searches
                </div>
                {recentSearches.map((q) => (
                  <button
                    key={q}
                    type="button"
                    onMouseDown={() => handleSubmit(q)}
                    className="w-full text-left flex items-center gap-2 px-3 py-2 text-sm hover:bg-accent transition-colors"
                  >
                    <Clock className="w-3.5 h-3.5 text-muted-foreground flex-shrink-0" />
                    <span className="truncate">{q}</span>
                    <ChevronRight className="w-3 h-3 text-muted-foreground ml-auto flex-shrink-0" />
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Source toggles */}
          <div className="flex flex-wrap gap-2 mt-3">
            {SOURCES.map((src) => (
              <SourceToggle
                key={src.key}
                source={src}
                active={activeSources.has(src.key)}
                onToggle={toggleSource}
              />
            ))}
          </div>
        </div>
      </div>

      {/* ── Results area ────────────────────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto px-6 py-5">

          {/* Error banner */}
          {hasError && hasQuery && (
            <div className="mb-4 flex items-center gap-2 rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
              <AlertTriangle className="w-4 h-4 flex-shrink-0" />
              <span>Search partially failed — some sources may be unavailable.</span>
            </div>
          )}

          {/* Result count */}
          {hasQuery && !isLoading && totalCount > 0 && (
            <div className="flex items-center justify-between mb-4">
              <p className="text-sm text-muted-foreground">
                {totalCount} result{totalCount !== 1 ? "s" : ""} for{" "}
                <span className="font-medium text-foreground">"{debouncedQuery}"</span>
              </p>
              <div className="flex items-center gap-3 text-xs text-muted-foreground">
                {unifiedSearch.data?.duration_ms != null && (
                  <span>{unifiedSearch.data.duration_ms} ms</span>
                )}
                {guidanceSearch.data && (
                  <span className="flex items-center gap-1">
                    <BookOpen className="w-3 h-3" />
                    {guidanceSearch.data.model}
                  </span>
                )}
              </div>
            </div>
          )}

          {/* Loading skeleton */}
          {isLoading && (
            <div className="space-y-3">
              {[1, 2, 3, 4].map((i) => (
                <div
                  key={i}
                  className="h-24 rounded-xl bg-muted animate-pulse"
                  style={{ opacity: 1 - i * 0.15 }}
                />
              ))}
            </div>
          )}

          {/* No results / empty state */}
          {!isLoading && totalCount === 0 && <EmptyState query={debouncedQuery} />}

          {/* Guidance results section */}
          {!isLoading && guidanceResults.length > 0 && activeSources.has("guidance") && (
            <div className="mb-6">
              <h2 className="text-sm font-semibold text-foreground flex items-center gap-2 mb-3">
                <BookOpen className="w-4 h-4 text-blue-500" />
                FDA Guidance Documents
                <Badge className="ml-1 text-xs">{guidanceResults.length}</Badge>
              </h2>
              <div className="space-y-2">
                {guidanceResults.map((r) => (
                  <GuidanceCard key={r.id} result={r} />
                ))}
              </div>
            </div>
          )}

          {/* Guidance error / empty notice */}
          {!isLoading && guidanceSearch.data?.error && activeSources.has("guidance") && (
            <div className="mb-6 rounded-lg border border-amber-200 bg-amber-50 dark:border-amber-900 dark:bg-amber-950/40 px-4 py-3 text-sm text-amber-700 dark:text-amber-300 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 flex-shrink-0" />
              Guidance semantic search unavailable: {guidanceSearch.data.error}
            </div>
          )}

          {/* Unified results (510k / MAUDE / recalls / PubMed) */}
          {!isLoading && unifiedResults.length > 0 && (
            <div>
              <h2 className="text-sm font-semibold text-foreground flex items-center gap-2 mb-3">
                <BarChart2 className="w-4 h-4 text-green-500" />
                Other Sources
                <Badge className="ml-1 text-xs">{unifiedResults.length}</Badge>
              </h2>
              <div className="space-y-2">
                {unifiedResults.map((r) => (
                  <UnifiedResultCard key={r.id} result={r} />
                ))}
              </div>
            </div>
          )}

          {/* Placeholder for Sprint 6+ sources */}
          {!isLoading && hasQuery && unifiedResults.length === 0 && totalCount > 0 && (
            <div className="mt-6 rounded-xl border border-border bg-muted/30 px-5 py-4 text-center">
              <p className="text-xs text-muted-foreground">
                510(k), MAUDE, recall, and PubMed search coming in Sprint 6
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
