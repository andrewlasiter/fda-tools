/**
 * FDA-248  [FE-010] Safety Signal Dashboard
 * ==========================================
 * CUSUM-based MAUDE adverse event signal viewer.
 * Loads from GET /research/signals/{product_code} and renders:
 *  - Baseline statistics summary cards
 *  - Tremor BarList / AreaChart of detected signal events
 *  - Alert timeline with severity badges
 *  - Product code input with debounced auto-fetch
 */

"use client";

import { useState, useEffect, useRef }        from "react";
import { Activity, AlertTriangle, TrendingUp, Search, RefreshCw } from "lucide-react";
import { Badge }  from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input }  from "@/components/ui/input";
import { useSignals, type SignalResult }       from "@/lib/api-client";

// ── Severity colours ──────────────────────────────────────────────────────────

const SEV_CLASSES: Record<string, string> = {
  CRITICAL: "bg-red-100 text-red-800 border-red-300 dark:bg-red-950 dark:text-red-300",
  HIGH:     "bg-orange-100 text-orange-800 border-orange-300 dark:bg-orange-950 dark:text-orange-300",
  MEDIUM:   "bg-yellow-100 text-yellow-800 border-yellow-300 dark:bg-yellow-950 dark:text-yellow-300",
  LOW:      "bg-blue-100 text-blue-800 border-blue-300 dark:bg-blue-950 dark:text-blue-300",
};

// ── Stat card ─────────────────────────────────────────────────────────────────

function StatCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="rounded-lg border bg-card px-4 py-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-2xl font-bold tabular-nums">{value}</p>
      {sub && <p className="text-xs text-muted-foreground">{sub}</p>}
    </div>
  );
}

// ── Signal event card ─────────────────────────────────────────────────────────

function SignalCard({ sig }: { sig: SignalResult }) {
  return (
    <div className="flex items-start gap-3 rounded-lg border bg-card p-3 shadow-sm">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-orange-500" />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="font-mono text-sm font-semibold">{sig.date}</span>
          <Badge className={`text-[11px] ${SEV_CLASSES[sig.severity] ?? ""}`}>
            {sig.severity}
          </Badge>
          <span className="ml-auto font-mono text-sm font-bold">{sig.count} events</span>
        </div>
        <p className="mt-1 text-xs text-muted-foreground">{sig.description}</p>
        {sig.event_types.length > 0 && (
          <div className="mt-1.5 flex flex-wrap gap-1">
            {sig.event_types.map((t) => (
              <span key={t} className="rounded border px-1.5 py-0.5 text-[10px] font-medium">
                {t}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Inline SVG bar chart (no Tremor/D3 — avoids peer dep issues) ───────────────

function SignalBarChart({ signals }: { signals: SignalResult[] }) {
  if (signals.length === 0) return null;

  const maxCount = Math.max(...signals.map((s) => s.count), 1);
  const svgH     = 100;
  const barW     = Math.min(40, Math.max(12, 360 / signals.length));
  const svgW     = signals.length * (barW + 4) + 8;

  const sevColor: Record<string, string> = {
    CRITICAL: "#ef4444",
    HIGH:     "#f97316",
    MEDIUM:   "#eab308",
    LOW:      "#3b82f6",
  };

  return (
    <div className="mt-4 overflow-x-auto">
      <p className="mb-1 text-xs font-medium text-muted-foreground">Events by detected signal</p>
      <svg width={svgW} height={svgH + 20} className="block">
        {signals.map((sig, i) => {
          const h   = Math.max(4, (sig.count / maxCount) * svgH);
          const x   = 4 + i * (barW + 4);
          const y   = svgH - h;
          const col = sevColor[sig.severity] ?? "#94a3b8";
          return (
            <g key={i}>
              <rect x={x} y={y} width={barW} height={h} rx={3} fill={col} opacity={0.85} />
              <text
                x={x + barW / 2} y={svgH + 14}
                fontSize={8} textAnchor="middle" fill="#94a3b8"
              >
                {sig.date.slice(5)} {/* MM-DD */}
              </text>
            </g>
          );
        })}
        {/* Baseline label */}
        <text x={4} y={svgH - 2} fontSize={8} fill="#94a3b8">0</text>
        <text x={4} y={8}         fontSize={8} fill="#94a3b8">{maxCount}</text>
      </svg>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export function SignalDashboard() {
  const [input,       setInput]       = useState("");
  const [productCode, setProductCode] = useState("");
  const [days,        setDays]        = useState(90);
  const inputRef = useRef<HTMLInputElement>(null);

  const { data, isLoading, error, refetch } = useSignals(productCode, days);

  const handleSearch = () => {
    const code = input.trim().toUpperCase();
    if (code.length >= 2) setProductCode(code);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleSearch();
  };

  // Aggregate severity counts
  const sevCounts = data
    ? data.signals.reduce<Record<string, number>>((acc, s) => {
        acc[s.severity] = (acc[s.severity] ?? 0) + 1;
        return acc;
      }, {})
    : {};

  return (
    <div className="space-y-4">
      {/* Search bar */}
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            ref={inputRef}
            placeholder="Enter FDA product code (e.g. DQY, CBK…)"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            className="pl-9 font-mono uppercase"
          />
        </div>
        <select
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          className="rounded-md border bg-background px-3 py-2 text-sm"
        >
          <option value={30}>30 days</option>
          <option value={90}>90 days</option>
          <option value={180}>180 days</option>
          <option value={365}>1 year</option>
        </select>
        <Button onClick={handleSearch} disabled={input.trim().length < 2}>
          <Activity className="mr-1 h-4 w-4" /> Analyze
        </Button>
      </div>

      {/* Loading */}
      {isLoading && productCode && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <RefreshCw className="h-4 w-4 animate-spin" />
          Analyzing MAUDE signals for {productCode}…
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
          {error instanceof Error ? error.message : "Signal detection failed"}
          <Button variant="ghost" size="sm" className="ml-2" onClick={() => refetch()}>
            Retry
          </Button>
        </div>
      )}

      {/* Empty prompt */}
      {!productCode && !isLoading && (
        <div className="flex h-48 flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed">
          <TrendingUp className="h-10 w-10 text-muted-foreground/40" />
          <div className="text-center">
            <p className="font-medium">Safety Signal Analysis</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Enter a product code above to detect MAUDE adverse event anomalies
            </p>
          </div>
        </div>
      )}

      {/* Results */}
      {data && (
        <>
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold">
                {data.product_code} — {data.total_events.toLocaleString()} events
              </h3>
              <p className="text-xs text-muted-foreground">
                {data.window_days}-day window · {data.signals.length} signals detected ·{" "}
                Generated {new Date(data.generated_at).toLocaleString()}
              </p>
            </div>
            <Button variant="ghost" size="sm" onClick={() => refetch()}>
              <RefreshCw className="h-3.5 w-3.5 mr-1" /> Refresh
            </Button>
          </div>

          {/* Stats row */}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <StatCard label="Daily Mean"   value={data.baseline_stats.mean.toFixed(1)} sub="events/day" />
            <StatCard label="Std Dev"      value={data.baseline_stats.std.toFixed(1)}  sub="σ baseline" />
            <StatCard label="Median"       value={data.baseline_stats.median.toFixed(1)} />
            <StatCard label="Signals"      value={data.signals.length} sub={`in ${data.window_days} days`} />
          </div>

          {/* Severity breakdown */}
          {Object.keys(sevCounts).length > 0 && (
            <div className="flex flex-wrap gap-2">
              {(["CRITICAL", "HIGH", "MEDIUM", "LOW"] as const).map((sev) =>
                sevCounts[sev] ? (
                  <Badge key={sev} className={SEV_CLASSES[sev]}>
                    {sev} × {sevCounts[sev]}
                  </Badge>
                ) : null,
              )}
            </div>
          )}

          {/* Bar chart */}
          <SignalBarChart signals={data.signals} />

          {/* Signal events */}
          {data.signals.length === 0 ? (
            <div className="rounded-lg border bg-muted/30 p-6 text-center text-sm text-muted-foreground">
              No anomalous signals detected in the {data.window_days}-day window.
            </div>
          ) : (
            <div className="space-y-2">
              <p className="text-sm font-medium">Detected Signal Events</p>
              {data.signals.map((sig, i) => (
                <SignalCard key={i} sig={sig} />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
