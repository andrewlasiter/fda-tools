"use client";

/**
 * FDA-291 [RH-004] — GuidanceDendrogram
 * =======================================
 * Interactive Ward-linkage cluster tree for FDA guidance documents.
 * Pure SVG (no D3 dependency) — tree layout computed client-side.
 *
 * Tree structure: root (all guidance) → regulation-area clusters → doc leaves
 *
 * Features:
 *   - Expand/collapse subtrees on click
 *   - Hover tooltip: document title + applicability score
 *   - Zoom/pan via CSS transform + mouse wheel
 *   - Filter by regulation area chip-set
 *   - Selected node highlight + detail panel slot
 *   - Colour-coded by 21 CFR part area
 */

import React, { useState, useCallback, useRef, useEffect } from "react";
import { cn } from "@/lib/utils";

// ── Types ──────────────────────────────────────────────────────────────────

export type RegulationArea =
  | "general"       // 21 CFR Part 1–99
  | "devices"       // 21 CFR Part 800–899
  | "biologics"     // 21 CFR Part 600–699
  | "drugs"         // 21 CFR Part 200–499
  | "food"          // 21 CFR Part 100–199
  | "combination";  // combination products

export interface GuidanceDocument {
  id:               string;
  title:            string;
  area:             RegulationArea;
  applicability:    number;   // 0–100 score for the current project
  issueDate:        string;   // ISO date string
  cfr?:             string;   // e.g. "21 CFR 820"
}

export interface GuidanceCluster {
  id:       string;
  label:    string;
  area:     RegulationArea;
  docs:     GuidanceDocument[];
  children: GuidanceCluster[];
}

export interface GuidanceDendrogramProps {
  clusters:          GuidanceCluster[];
  onSelectDocument?: (id: string) => void;
  className?:        string;
}

// ── Config ─────────────────────────────────────────────────────────────────

const AREA_CONFIG: Record<RegulationArea, { label: string; color: string; bg: string }> = {
  general:     { label: "General",     color: "#005EA2", bg: "#005EA2" },
  devices:     { label: "Devices",     color: "#7C3AED", bg: "#7C3AED" },
  biologics:   { label: "Biologics",   color: "#1A7F4B", bg: "#1A7F4B" },
  drugs:       { label: "Drugs",       color: "#B45309", bg: "#B45309" },
  food:        { label: "Food",        color: "#C5191B", bg: "#C5191B" },
  combination: { label: "Combination", color: "#0891B2", bg: "#0891B2" },
};

// ── Tree node ───────────────────────────────────────────────────────────────

interface TreeNodeData {
  id:       string;
  label:    string;
  type:     "cluster" | "doc";
  area:     RegulationArea;
  score?:   number;
  date?:    string;
  cfr?:     string;
  children: TreeNodeData[];
}

function clusterToTree(c: GuidanceCluster): TreeNodeData {
  return {
    id:    c.id,
    label: c.label,
    type:  "cluster",
    area:  c.area,
    children: [
      ...c.children.map(clusterToTree),
      ...c.docs.map(d => ({
        id:       d.id,
        label:    d.title,
        type:     "doc" as const,
        area:     d.area,
        score:    d.applicability,
        date:     d.issueDate,
        cfr:      d.cfr,
        children: [],
      })),
    ],
  };
}

// ── Tooltip ─────────────────────────────────────────────────────────────────

function Tooltip({ node, x, y }: { node: TreeNodeData; x: number; y: number }) {
  return (
    <div
      className="fixed z-50 pointer-events-none bg-card border border-border rounded-lg shadow-lg px-3 py-2 text-[10px] max-w-[220px]"
      style={{ left: x + 12, top: y - 8 }}
    >
      <p className="font-semibold text-foreground line-clamp-2">{node.label}</p>
      {node.cfr && (
        <p className="text-muted-foreground mt-0.5 font-mono">{node.cfr}</p>
      )}
      {node.score !== undefined && (
        <div className="flex items-center gap-1.5 mt-1">
          <div className="w-12 h-1 rounded-full bg-muted overflow-hidden">
            <div
              className="h-full rounded-full"
              style={{
                width: `${node.score}%`,
                background: node.score >= 70 ? "#1A7F4B" : node.score >= 40 ? "#B45309" : "#C5191B",
              }}
            />
          </div>
          <span className="text-muted-foreground">{node.score}% applicable</span>
        </div>
      )}
      {node.date && (
        <p className="text-muted-foreground mt-0.5">{node.date.slice(0, 10)}</p>
      )}
    </div>
  );
}

// ── Tree rendering (recursive SVG) ──────────────────────────────────────────

const ROW_H  = 28;
const INDENT = 20;
const DOT_R  = 5;

interface FlatNode {
  node:   TreeNodeData;
  depth:  number;
  index:  number;
  parentIndex: number | null;
}

function flattenTree(
  node:   TreeNodeData,
  depth:  number,
  index:  number,
  parentIdx: number | null,
  collapsed: Set<string>,
  out:    FlatNode[],
): number {
  out.push({ node, depth, index, parentIndex: parentIdx });
  const myIdx = out.length - 1;
  if (!collapsed.has(node.id)) {
    for (const child of node.children) {
      index = flattenTree(child, depth + 1, out.length, myIdx, collapsed, out);
    }
  }
  return out.length;
}

function buildRoot(clusters: GuidanceCluster[]): TreeNodeData {
  return {
    id:       "__root__",
    label:    "All Guidance",
    type:     "cluster",
    area:     "general",
    children: clusters.map(clusterToTree),
  };
}

// ── Main Component ─────────────────────────────────────────────────────────

export function GuidanceDendrogram({
  clusters,
  onSelectDocument,
  className,
}: GuidanceDendrogramProps) {
  const [collapsed,   setCollapsed]   = useState<Set<string>>(new Set());
  const [selected,    setSelected]    = useState<string | null>(null);
  const [areaFilter,  setAreaFilter]  = useState<RegulationArea | "all">("all");
  const [tooltip,     setTooltip]     = useState<{ node: TreeNodeData; x: number; y: number } | null>(null);
  const [zoom,        setZoom]        = useState(1);
  const [pan,         setPan]         = useState({ x: 0, y: 0 });
  const dragging = useRef(false);
  const dragStart = useRef({ x: 0, y: 0, px: 0, py: 0 });

  // Filter clusters by area
  const visibleClusters = areaFilter === "all"
    ? clusters
    : clusters.filter(c => c.area === areaFilter || c.docs.some(d => d.area === areaFilter));

  const root = buildRoot(visibleClusters);

  // Start with root expanded, everything else collapsed
  const [initialised, setInitialised] = useState(false);
  useEffect(() => {
    if (!initialised && clusters.length > 0) {
      const c = new Set<string>();
      // collapse leaf clusters (depth ≥ 2) by default
      const collapseDeep = (n: TreeNodeData, depth: number): void => {
        if (depth >= 2) c.add(n.id);
        n.children.forEach(ch => collapseDeep(ch, depth + 1));
      };
      root.children.forEach(ch => collapseDeep(ch, 1));
      setCollapsed(c);
      setInitialised(true);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clusters.length]);

  const flat: FlatNode[] = [];
  flattenTree(root, 0, 0, null, collapsed, flat);

  const SVG_W = 560;
  const SVG_H = Math.max(flat.length * ROW_H + 20, 200);

  const toggleCollapse = useCallback((id: string) => {
    setCollapsed(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }, []);

  // Zoom on wheel
  const containerRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      setZoom(z => Math.min(2, Math.max(0.4, z - e.deltaY * 0.001)));
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, []);

  // Pan on drag
  const onMouseDown = (e: React.MouseEvent) => {
    dragging.current = true;
    dragStart.current = { x: e.clientX, y: e.clientY, px: pan.x, py: pan.y };
  };
  const onMouseMove = (e: React.MouseEvent) => {
    if (!dragging.current) return;
    setPan({
      x: dragStart.current.px + (e.clientX - dragStart.current.x),
      y: dragStart.current.py + (e.clientY - dragStart.current.y),
    });
  };
  const onMouseUp = () => { dragging.current = false; };

  const areas = Array.from(new Set(clusters.map(c => c.area)));

  return (
    <div className={cn("flex flex-col h-full", className)}>
      {/* Header + filter chips */}
      <div className="px-4 pt-3 pb-2 border-b border-border shrink-0 space-y-2">
        <div className="flex items-center justify-between gap-2">
          <h3 className="text-sm font-semibold text-foreground">Guidance Clusters</h3>
          <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
            <button
              onClick={() => setZoom(z => Math.min(2, z + 0.1))}
              className="px-1.5 py-0.5 border border-border rounded hover:bg-muted cursor-pointer"
            >+</button>
            <span className="font-mono">{Math.round(zoom * 100)}%</span>
            <button
              onClick={() => setZoom(z => Math.max(0.4, z - 0.1))}
              className="px-1.5 py-0.5 border border-border rounded hover:bg-muted cursor-pointer"
            >-</button>
            <button
              onClick={() => { setZoom(1); setPan({ x: 0, y: 0 }); }}
              className="px-1.5 py-0.5 border border-border rounded hover:bg-muted cursor-pointer"
            >Reset</button>
          </div>
        </div>

        <div className="flex items-center gap-1.5 flex-wrap">
          <button
            onClick={() => setAreaFilter("all")}
            className={cn(
              "text-[9px] px-2 py-0.5 rounded-full border font-medium transition-colors cursor-pointer",
              areaFilter === "all"
                ? "bg-foreground text-background border-foreground"
                : "border-border text-muted-foreground hover:bg-muted",
            )}
          >
            All areas
          </button>
          {areas.map(a => {
            const acfg = AREA_CONFIG[a];
            return (
              <button
                key={a}
                onClick={() => setAreaFilter(a)}
                className={cn(
                  "text-[9px] px-2 py-0.5 rounded-full border font-medium transition-colors cursor-pointer",
                  areaFilter === a
                    ? "text-white border-transparent"
                    : "border-border text-muted-foreground hover:bg-muted",
                )}
                style={areaFilter === a ? { background: acfg.color, borderColor: acfg.color } : {}}
              >
                {acfg.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* SVG canvas */}
      <div
        ref={containerRef}
        className="flex-1 overflow-hidden relative cursor-grab active:cursor-grabbing select-none"
        onMouseDown={onMouseDown}
        onMouseMove={onMouseMove}
        onMouseUp={onMouseUp}
        onMouseLeave={() => { dragging.current = false; setTooltip(null); }}
      >
        <div
          style={{
            transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
            transformOrigin: "top left",
            width: SVG_W,
            transition: dragging.current ? "none" : "transform 0.1s ease",
          }}
        >
          <svg
            width={SVG_W}
            height={SVG_H}
            style={{ overflow: "visible" }}
          >
            {/* Connector lines */}
            {flat.map((item, i) => {
              if (item.parentIndex === null) return null;
              const parent = flat[item.parentIndex];
              const px = parent.depth * INDENT + DOT_R;
              const py = item.parentIndex * ROW_H + 14 + 10;
              const cx = item.depth * INDENT + DOT_R;
              const cy = i * ROW_H + 14 + 10;
              return (
                <path
                  key={`line-${item.node.id}`}
                  d={`M ${px} ${py} L ${px} ${cy} L ${cx} ${cy}`}
                  fill="none"
                  stroke="var(--border)"
                  strokeWidth={1}
                />
              );
            })}

            {/* Nodes */}
            {flat.map((item, i) => {
              const { node, depth } = item;
              const acfg = AREA_CONFIG[node.area];
              const isSelected  = selected === node.id;
              const hasChildren = node.children.length > 0;
              const isCollapsed = collapsed.has(node.id);
              const x = depth * INDENT;
              const y = i * ROW_H + 10;
              const nodeColor = acfg.color;

              return (
                <g
                  key={node.id}
                  transform={`translate(${x}, ${y})`}
                  onClick={(e) => {
                    e.stopPropagation();
                    if (hasChildren) toggleCollapse(node.id);
                    setSelected(node.id);
                    if (node.type === "doc") onSelectDocument?.(node.id);
                  }}
                  onMouseEnter={(e) => setTooltip({ node, x: e.clientX, y: e.clientY })}
                  onMouseLeave={() => setTooltip(null)}
                  className="cursor-pointer"
                >
                  {/* Node dot */}
                  <circle
                    cx={DOT_R}
                    cy={4}
                    r={DOT_R}
                    fill={isSelected ? nodeColor : "var(--background)"}
                    stroke={nodeColor}
                    strokeWidth={2}
                  />

                  {/* Expand/collapse indicator */}
                  {hasChildren && (
                    <text x={DOT_R} y={8} textAnchor="middle" fontSize={7} fill={nodeColor} fontWeight="bold">
                      {isCollapsed ? "+" : "-"}
                    </text>
                  )}

                  {/* Label */}
                  <text
                    x={DOT_R * 2 + 6}
                    y={8}
                    fontSize={node.type === "cluster" ? 11 : 10}
                    fontWeight={node.type === "cluster" ? "600" : "400"}
                    fill={isSelected ? nodeColor : "var(--foreground)"}
                    className="select-none"
                  >
                    {node.label.length > 50 ? node.label.slice(0, 50) + "…" : node.label}
                  </text>

                  {/* Applicability score bar (docs only) */}
                  {node.type === "doc" && node.score !== undefined && (
                    <g transform={`translate(${DOT_R * 2 + 6}, 12)`}>
                      <rect width={32} height={2} rx={1} fill="var(--muted)" />
                      <rect
                        width={Math.round((node.score / 100) * 32)}
                        height={2}
                        rx={1}
                        fill={node.score >= 70 ? "#1A7F4B" : node.score >= 40 ? "#B45309" : "#C5191B"}
                      />
                    </g>
                  )}
                </g>
              );
            })}
          </svg>
        </div>

        {/* Empty state */}
        {flat.length <= 1 && (
          <div className="absolute inset-0 flex items-center justify-center text-[11px] text-muted-foreground">
            No guidance documents match the current filter.
          </div>
        )}
      </div>

      {/* Tooltip portal */}
      {tooltip && <Tooltip node={tooltip.node} x={tooltip.x} y={tooltip.y} />}
    </div>
  );
}
