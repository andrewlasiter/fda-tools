"use client";

/**
 * FDA-292 [RH-005] — SignalDashboard
 * ====================================
 * Safety signal monitoring panel.
 * CUSUM trend chart + anomaly annotations + severity breakdown.
 *
 * Features:
 *   - Monthly MAUDE event count trend (Tremor AreaChart stub)
 *   - CUSUM threshold band overlay (horizontal alarm line)
 *   - Anomaly markers: spike detection with tooltip annotations
 *   - Product-code multi-select filter
 *   - Date range picker (12 / 24 / 60 months)
 *   - Severity breakdown: Critical / Serious / Non-serious stacked bars
 *   - CSV export of visible data
 */

import React, { useState, useMemo, useCallback } from "react";
import { cn } from "@/lib/utils";

// ── Types ──────────────────────────────────────────────────────────────────

export type SeverityLevel = "critical" | "serious" | "non_serious";

export interface SignalDataPoint {
  month:       string;      // "YYYY-MM"
  productCode: string;
  critical:    number;
  serious:     number;
  non_serious: number;
  cusum:       number;      // cumulative sum statistic
  isAnomaly:   boolean;     // CUSUM threshold exceeded
  anomalyNote?: string;     // optional note for the anomaly
}

export interface SignalDashboardProps {
  signals:      SignalDataPoint[];
  productCodes: string[];        // all available product codes
  cusumAlarm?:  number;          // CUSUM alarm threshold (default 5)
  onExport?:    () => void;
  className?:   string;
}

// ── Config ─────────────────────────────────────────────────────────────────

const SEVERITY_CONFIG: Record<SeverityLevel, { label: string; color: string; bg: string }> = {
  critical:    { label: "Critical",    color: "#C5191B", bg: "bg-[#C5191B]/15" },
  serious:     { label: "Serious",     color: "#B45309", bg: "bg-[#B45309]/15" },
  non_serious: { label: "Non-Serious", color: "#005EA2", bg: "bg-[#005EA2]/15" },
};

const WINDOW_OPTIONS = [
  { label: "12 mo",  value: 12 },
  { label: "24 mo",  value: 24 },
  { label: "60 mo",  value: 60 },
] as const;

// ── Mini bar chart (severity breakdown) ────────────────────────────────────

function SeverityBar({
  critical, serious, non_serious,
}: { critical: number; serious: number; non_serious: number }) {
  const total = critical + serious + non_serious;
  if (total === 0) return <span className="text-[9px] text-muted-foreground">—</span>;
  const pct = (n: number) => `${Math.round((n / total) * 100)}%`;
  return (
    <div className="flex items-center gap-1.5">
      <div className="flex h-2 w-24 rounded overflow-hidden gap-px">
        <div className="bg-[#C5191B] h-full" style={{ width: pct(critical) }} />
        <div className="bg-[#B45309] h-full" style={{ width: pct(serious) }} />
        <div className="bg-[#005EA2] h-full" style={{ width: pct(non_serious) }} />
      </div>
      <span className="text-[9px] text-muted-foreground">{total.toLocaleString()} total</span>
    </div>
  );
}

// ── Trend chart (SVG-based CUSUM sparkline) ──────────────────────────────

function CusumChart({
  points,
  alarm,
}: {
  points:  SignalDataPoint[];
  alarm:   number;
}) {
  const W = 520, H = 100, PAD = { t: 10, r: 8, b: 20, l: 36 };

  const totalCounts = points.map(p => p.critical + p.serious + p.non_serious);
  const maxCount    = Math.max(...totalCounts, 1);
  const maxCusum    = Math.max(...points.map(p => p.cusum), alarm * 1.2, 1);

  const xScale = (i: number) =>
    PAD.l + (i / Math.max(points.length - 1, 1)) * (W - PAD.l - PAD.r);
  const yCount = (v: number) =>
    PAD.t + (1 - v / maxCount) * (H - PAD.t - PAD.b);
  const yCusum = (v: number) =>
    PAD.t + (1 - v / maxCusum) * (H - PAD.t - PAD.b);

  // Area path for total count
  const areaPath = points.length < 2 ? "" : [
    `M ${xScale(0)} ${yCount(totalCounts[0])}`,
    ...points.slice(1).map((_, i) => `L ${xScale(i + 1)} ${yCount(totalCounts[i + 1])}`),
    `L ${xScale(points.length - 1)} ${H - PAD.b}`,
    `L ${xScale(0)} ${H - PAD.b} Z`,
  ].join(" ");

  // CUSUM line
  const cusumLine = points.length < 2 ? "" : [
    `M ${xScale(0)} ${yCusum(points[0].cusum)}`,
    ...points.slice(1).map((_, i) => `L ${xScale(i + 1)} ${yCusum(points[i + 1].cusum)}`),
  ].join(" ");

  const alarmY = yCusum(alarm);

  return (
    <svg width="100%" viewBox={`0 0 ${W} ${H}`} className="overflow-visible">
      <defs>
        <linearGradient id="count-grad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#005EA2" stopOpacity="0.25" />
          <stop offset="100%" stopColor="#005EA2" stopOpacity="0.02" />
        </linearGradient>
      </defs>

      {/* Area */}
      {areaPath && <path d={areaPath} fill="url(#count-grad)" />}

      {/* CUSUM alarm line */}
      <line
        x1={PAD.l} y1={alarmY} x2={W - PAD.r} y2={alarmY}
        stroke="#C5191B" strokeWidth={1} strokeDasharray="4 3" opacity={0.7}
      />
      <text x={PAD.l - 2} y={alarmY} fontSize={7} fill="#C5191B" textAnchor="end" dominantBaseline="middle">
        {alarm}
      </text>

      {/* CUSUM line */}
      {cusumLine && (
        <path d={cusumLine} fill="none" stroke="#B45309" strokeWidth={1.5} strokeLinejoin="round" />
      )}

      {/* Anomaly markers */}
      {points.map((p, i) => p.isAnomaly && (
        <g key={i} transform={`translate(${xScale(i)}, ${yCount(totalCounts[i])})`}>
          <circle r={3.5} fill="#C5191B" opacity={0.9} />
          <circle r={6} fill="#C5191B" opacity={0.15} />
        </g>
      ))}

      {/* X axis labels (every 4 months) */}
      {points.map((p, i) => {
        if (i % 4 !== 0) return null;
        return (
          <text
            key={i}
            x={xScale(i)} y={H - 4}
            fontSize={7} textAnchor="middle"
            fill="var(--muted-foreground)"
          >
            {p.month.slice(0, 7)}
          </text>
        );
      })}

      {/* Y axis label */}
      <text x={4} y={H / 2} fontSize={7} fill="var(--muted-foreground)"
        transform={`rotate(-90, 4, ${H / 2})`} textAnchor="middle">
        Events
      </text>
    </svg>
  );
}

// ── Anomaly card ────────────────────────────────────────────────────────────

function AnomalyCard({ point }: { point: SignalDataPoint }) {
  const total = point.critical + point.serious + point.non_serious;
  return (
    <div className="flex items-start gap-2 px-3 py-2 rounded-lg border border-[#C5191B]/30 bg-[#C5191B]/5">
      <div className="w-2 h-2 rounded-full bg-[#C5191B] flex-shrink-0 mt-0.5" />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-[10px] font-mono font-bold text-[#C5191B]">{point.month}</span>
          <span className="text-[10px] text-muted-foreground">
            {total.toLocaleString()} events · CUSUM {point.cusum.toFixed(1)}
          </span>
        </div>
        {point.anomalyNote && (
          <p className="text-[10px] text-foreground mt-0.5">{point.anomalyNote}</p>
        )}
      </div>
    </div>
  );
}

// ── Main Component ─────────────────────────────────────────────────────────

export function SignalDashboard({
  signals,
  productCodes,
  cusumAlarm = 5,
  onExport,
  className,
}: SignalDashboardProps) {
  const [selectedCodes, setSelectedCodes] = useState<string[]>(productCodes.slice(0, 3));
  const [windowMonths,  setWindowMonths]  = useState<number>(24);

  // Filter by product code + date window
  const visible = useMemo(() => {
    const cutoff = (() => {
      const d = new Date();
      d.setMonth(d.getMonth() - windowMonths);
      return d.toISOString().slice(0, 7); // "YYYY-MM"
    })();

    return signals.filter(
      s => (selectedCodes.length === 0 || selectedCodes.includes(s.productCode))
        && s.month >= cutoff,
    ).sort((a, b) => a.month.localeCompare(b.month));
  }, [signals, selectedCodes, windowMonths]);

  // Aggregate by month
  const monthly = useMemo(() => {
    const map = new Map<string, SignalDataPoint>();
    for (const s of visible) {
      const existing = map.get(s.month);
      if (existing) {
        existing.critical    += s.critical;
        existing.serious     += s.serious;
        existing.non_serious += s.non_serious;
        existing.cusum       = Math.max(existing.cusum, s.cusum);
        existing.isAnomaly   = existing.isAnomaly || s.isAnomaly;
      } else {
        map.set(s.month, { ...s });
      }
    }
    return Array.from(map.values()).sort((a, b) => a.month.localeCompare(b.month));
  }, [visible]);

  const anomalies  = monthly.filter(p => p.isAnomaly);
  const totalEvents = monthly.reduce((s, p) => s + p.critical + p.serious + p.non_serious, 0);
  const totCritical = monthly.reduce((s, p) => s + p.critical, 0);
  const totSerious  = monthly.reduce((s, p) => s + p.serious, 0);
  const totNonSer   = monthly.reduce((s, p) => s + p.non_serious, 0);

  const toggleCode = useCallback((code: string) => {
    setSelectedCodes(cs => cs.includes(code) ? cs.filter(c => c !== code) : [...cs, code]);
  }, []);

  function handleExport() {
    const lines = [
      "month,product_code,critical,serious,non_serious,cusum,is_anomaly",
      ...visible.map(s =>
        `${s.month},${s.productCode},${s.critical},${s.serious},${s.non_serious},${s.cusum},${s.isAnomaly}`
      ),
    ];
    const blob = new Blob([lines.join("\n")], { type: "text/csv" });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement("a");
    a.href = url;
    a.download = `safety-signals-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    onExport?.();
  }

  return (
    <div className={cn("flex flex-col h-full", className)}>
      {/* Header */}
      <div className="px-4 pt-3 pb-2 border-b border-border shrink-0 space-y-2">
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <div>
            <h3 className="text-sm font-semibold text-foreground">Safety Signals</h3>
            <p className="text-[10px] text-muted-foreground mt-0.5">
              MAUDE event trend + CUSUM anomaly detection
            </p>
          </div>
          <div className="flex items-center gap-2">
            {/* Window selector */}
            <div className="flex rounded-lg border border-border overflow-hidden">
              {WINDOW_OPTIONS.map(opt => (
                <button
                  key={opt.value}
                  onClick={() => setWindowMonths(opt.value)}
                  className={cn(
                    "text-[10px] px-2.5 py-1 font-medium transition-colors cursor-pointer",
                    windowMonths === opt.value
                      ? "bg-[#005EA2] text-white"
                      : "text-muted-foreground hover:bg-muted",
                  )}
                >
                  {opt.label}
                </button>
              ))}
            </div>
            <button
              onClick={handleExport}
              className="text-[10px] text-[#005EA2] hover:underline font-medium cursor-pointer"
            >
              ↓ CSV
            </button>
          </div>
        </div>

        {/* Product code chips */}
        <div className="flex items-center gap-1.5 flex-wrap">
          {productCodes.map(code => (
            <button
              key={code}
              onClick={() => toggleCode(code)}
              className={cn(
                "text-[9px] px-2 py-0.5 rounded-full border font-mono font-medium transition-colors cursor-pointer",
                selectedCodes.includes(code)
                  ? "bg-[#005EA2]/10 border-[#005EA2]/40 text-[#005EA2]"
                  : "border-border text-muted-foreground hover:bg-muted",
              )}
            >
              {code}
            </button>
          ))}
        </div>
      </div>

      {/* KPI row */}
      <div className="px-4 py-2 grid grid-cols-4 gap-3 border-b border-border shrink-0">
        {[
          { label: "Total Events", value: totalEvents.toLocaleString(), color: "text-foreground" },
          { label: "Critical",     value: totCritical.toLocaleString(), color: "text-[#C5191B]" },
          { label: "Serious",      value: totSerious.toLocaleString(),  color: "text-[#B45309]" },
          { label: "Anomalies",    value: anomalies.length.toString(),  color: anomalies.length > 0 ? "text-[#C5191B]" : "text-[#1A7F4B]" },
        ].map(kpi => (
          <div key={kpi.label} className="text-center">
            <p className={cn("text-base font-bold font-mono", kpi.color)}>{kpi.value}</p>
            <p className="text-[9px] text-muted-foreground">{kpi.label}</p>
          </div>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto">
        {/* Chart */}
        <div className="px-4 py-3">
          <div className="flex items-center gap-3 mb-2 flex-wrap">
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-0.5 bg-[#005EA2] opacity-40" />
              <span className="text-[9px] text-muted-foreground">Event count</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-0.5 bg-[#B45309]" />
              <span className="text-[9px] text-muted-foreground">CUSUM</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-0.5 border-t border-[#C5191B] border-dashed" />
              <span className="text-[9px] text-muted-foreground">Alarm ({cusumAlarm})</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-2 h-2 rounded-full bg-[#C5191B]" />
              <span className="text-[9px] text-muted-foreground">Anomaly</span>
            </div>
          </div>

          {monthly.length === 0 ? (
            <div className="h-24 flex items-center justify-center border border-dashed border-border rounded-lg text-[10px] text-muted-foreground">
              No signal data for the selected filters.
            </div>
          ) : (
            <CusumChart points={monthly} alarm={cusumAlarm} />
          )}
        </div>

        {/* Severity breakdown */}
        <div className="px-4 pb-3">
          <p className="text-[10px] font-semibold text-muted-foreground mb-2 uppercase tracking-wide">
            Severity breakdown
          </p>
          <div className="space-y-1.5">
            {(["critical", "serious", "non_serious"] as const).map(sev => {
              const scfg = SEVERITY_CONFIG[sev];
              const count = sev === "critical" ? totCritical : sev === "serious" ? totSerious : totNonSer;
              const pct   = totalEvents ? Math.round((count / totalEvents) * 100) : 0;
              return (
                <div key={sev} className="flex items-center gap-3">
                  <span
                    className={cn("text-[9px] font-bold px-1.5 py-0.5 rounded w-20 text-center flex-shrink-0", scfg.bg)}
                    style={{ color: scfg.color }}
                  >
                    {scfg.label}
                  </span>
                  <div className="flex-1 h-1.5 rounded-full bg-muted overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all"
                      style={{ width: `${pct}%`, background: scfg.color }}
                    />
                  </div>
                  <span className="text-[9px] font-mono text-muted-foreground w-16 text-right flex-shrink-0">
                    {count.toLocaleString()} ({pct}%)
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Anomaly list */}
        {anomalies.length > 0 && (
          <div className="px-4 pb-4">
            <p className="text-[10px] font-semibold text-muted-foreground mb-2 uppercase tracking-wide">
              Detected anomalies ({anomalies.length})
            </p>
            <div className="space-y-1.5">
              {anomalies.map(p => <AnomalyCard key={`${p.month}-${p.productCode}`} point={p} />)}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
