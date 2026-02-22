/**
 * FDA-242  [FE-009] Guidance Document Dendrogram Visualization
 * ============================================================
 * Renders the scipy Ward-linkage dendrogram returned by GET /research/clusters
 * using plain SVG + React (no D3 layout needed — scipy pre-computes icoord/dcoord).
 *
 * Features
 * --------
 * - Vertical dendrogram: leaves at bottom, root at top
 * - Color-coded branches by cluster assignment
 * - Hover tooltip: document title + cluster label
 * - Click legend chip or leaf to filter (calls onClusterSelect)
 * - Zoom + pan via CSS transform + wheel/drag
 * - Responsive SVG container with horizontal scroll
 */

"use client";

import { useRef, useState, useCallback } from "react";
import { useClusters, type GuidanceCluster, type ClusterDoc } from "@/lib/api-client";
import { Button }  from "@/components/ui/button";
import { Badge }   from "@/components/ui/badge";
import { AlertCircle, RefreshCw, ZoomIn, ZoomOut, Maximize2 } from "lucide-react";

// ── Cluster colour palette ────────────────────────────────────────────────────

const CLUSTER_COLORS = [
  "#2563eb", "#16a34a", "#dc2626", "#9333ea",
  "#ea580c", "#0891b2", "#d97706", "#be185d",
  "#059669", "#7c3aed", "#db2777", "#65a30d",
];

function clusterColor(id: number): string {
  return CLUSTER_COLORS[id % CLUSTER_COLORS.length];
}

// ── SVG layout constants ──────────────────────────────────────────────────────

const PAD_TOP    = 24;
const PAD_BOTTOM = 130;  // room for rotated leaf labels
const PAD_LEFT   = 32;
const PAD_RIGHT  = 16;
const PLOT_H     = 340;  // height of the dendrogram body

// ── Props ─────────────────────────────────────────────────────────────────────

interface Props {
  /** Callback when user selects / deselects a cluster. null = "show all". */
  onClusterSelect?: (clusterId: number | null) => void;
}

// ── Component ────────────────────────────────────────────────────────────────

export function DendrogramViz({ onClusterSelect }: Props) {
  const { data, isLoading, error, refetch } = useClusters();

  // Zoom + pan state
  const [zoom,       setZoom]       = useState(1.0);
  const [pan,        setPan]        = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart,  setDragStart]  = useState({ x: 0, y: 0 });

  // Hover / selection state
  const [hoveredDoc,       setHoveredDoc]       = useState<string | null>(null);
  const [selectedCluster,  setSelectedCluster]  = useState<number | null>(null);
  const [tooltipPos,       setTooltipPos]       = useState({ x: 0, y: 0 });

  const containerRef = useRef<HTMLDivElement>(null);

  // ── Cluster selection ───────────────────────────────────────────────────────

  const handleClusterClick = useCallback((clusterId: number) => {
    const next = selectedCluster === clusterId ? null : clusterId;
    setSelectedCluster(next);
    onClusterSelect?.(next);
  }, [selectedCluster, onClusterSelect]);

  // ── Zoom / pan handlers ─────────────────────────────────────────────────────

  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    const factor = e.deltaY > 0 ? 0.85 : 1.18;
    setZoom(z => Math.min(6, Math.max(0.25, z * factor)));
  }, []);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    setIsDragging(true);
    setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  }, [pan]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!isDragging) return;
    setPan({ x: e.clientX - dragStart.x, y: e.clientY - dragStart.y });
  }, [isDragging, dragStart]);

  const handleMouseUp = useCallback(() => setIsDragging(false), []);

  const resetView = useCallback(() => { setZoom(1); setPan({ x: 0, y: 0 }); }, []);

  // ── Loading / error states ──────────────────────────────────────────────────

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center text-sm text-muted-foreground">
        <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
        Building guidance clusters…
      </div>
    );
  }

  if (error || !data) {
    const msg = error instanceof Error ? error.message : "Failed to load clusters";
    return (
      <div className="flex h-64 flex-col items-center justify-center gap-3">
        <AlertCircle className="h-8 w-8 text-destructive" />
        <p className="text-sm text-muted-foreground">{msg}</p>
        <Button variant="outline" size="sm" onClick={() => refetch()}>
          <RefreshCw className="mr-1 h-4 w-4" /> Retry
        </Button>
      </div>
    );
  }

  // ── Coordinate scaling ──────────────────────────────────────────────────────

  const { icoord, dcoord, labels } = data.dendrogram;
  const n = labels.length;

  // scipy leaf x-positions: 5, 15, 25, … step=10
  const xMin = 5;
  const xMax = xMin + (n - 1) * 10;
  const yMin = 0;
  const yMax = Math.max(...dcoord.flat());

  // Per-document SVG width (minimum 18 px per leaf)
  const leafW = Math.max(18, Math.min(32, 900 / Math.max(n, 1)));
  const svgW  = PAD_LEFT + PAD_RIGHT + n * leafW;
  const svgH  = PAD_TOP  + PLOT_H + PAD_BOTTOM;

  const scaleX = (x: number) =>
    PAD_LEFT + ((x - xMin) / (xMax - xMin || 1)) * (svgW - PAD_LEFT - PAD_RIGHT);

  // Dendrogram grows upward: y=0 (leaves) at the bottom of PLOT_H
  const scaleY = (y: number) =>
    PAD_TOP + PLOT_H - ((y - yMin) / (yMax - yMin || 1)) * PLOT_H;

  // ── Build doc-title → cluster mapping ──────────────────────────────────────

  const titleToCluster = new Map<string, GuidanceCluster>();
  data.clusters.forEach(c => {
    c.docs.forEach((d: ClusterDoc) => titleToCluster.set(d.doc_title, c));
  });

  // ── Leaf circle positions ───────────────────────────────────────────────────

  const leaves = labels.map((label, i) => {
    const x    = scaleX(xMin + i * 10);
    const y    = scaleY(0);
    const cl   = titleToCluster.get(label);
    const cid  = cl?.cluster_id ?? 0;
    return { label, x, y, cid, clusterLabel: cl?.label ?? `Cluster ${cid}` };
  });

  // ── Determine branch colour by cluster membership ───────────────────────────
  // Each merge node gets the colour of the cluster if both children are the same cluster.
  // Mixed merges get a neutral grey.

  // Build a simple label→cid lookup, then colour each path by checking endpoints
  const pathColors = icoord.map((xs, i) => {
    const leftLabel  = leaves.find(l => Math.abs(l.x - scaleX(xs[0])) < 2);
    const rightLabel = leaves.find(l => Math.abs(l.x - scaleX(xs[3])) < 2);
    if (leftLabel && rightLabel && leftLabel.cid === rightLabel.cid) {
      return clusterColor(leftLabel.cid);
    }
    return "#94a3b8"; // slate-400 for cross-cluster merges
  });

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <div className="rounded-xl border bg-card shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between border-b px-4 py-3">
        <div>
          <p className="text-sm font-semibold">Guidance Document Clusters</p>
          <p className="mt-0.5 text-xs text-muted-foreground">
            {data.k} clusters · {data.n_docs} documents · Ward linkage
          </p>
        </div>
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="icon" className="h-7 w-7"
            onClick={() => setZoom(z => Math.min(6, z * 1.25))} title="Zoom in">
            <ZoomIn className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="icon" className="h-7 w-7"
            onClick={() => setZoom(z => Math.max(0.25, z * 0.8))} title="Zoom out">
            <ZoomOut className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="icon" className="h-7 w-7"
            onClick={resetView} title="Reset view">
            <Maximize2 className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="icon" className="h-7 w-7"
            onClick={() => refetch()} title="Refresh">
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Cluster legend */}
      <div className="flex flex-wrap gap-1.5 px-4 py-2">
        {data.clusters.map(c => {
          const active  = selectedCluster === c.cluster_id;
          const dimmed  = selectedCluster !== null && !active;
          return (
            <button
              key={c.cluster_id}
              onClick={() => handleClusterClick(c.cluster_id)}
              className={[
                "flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs transition-all",
                active  ? "ring-2 ring-offset-1 font-medium" : "",
                dimmed  ? "opacity-40" : "opacity-90 hover:opacity-100",
              ].join(" ")}
              style={{
                borderColor:     clusterColor(c.cluster_id),
                backgroundColor: active ? clusterColor(c.cluster_id) + "18" : "transparent",
                ringColor:       clusterColor(c.cluster_id),
              }}
            >
              <span
                className="inline-block h-2 w-2 rounded-full"
                style={{ backgroundColor: clusterColor(c.cluster_id) }}
              />
              {c.label}
              <Badge variant="secondary" className="ml-0.5 h-4 px-1 text-[10px]">
                {c.doc_count}
              </Badge>
            </button>
          );
        })}
        {selectedCluster !== null && (
          <button
            onClick={() => { setSelectedCluster(null); onClusterSelect?.(null); }}
            className="rounded-full border px-2.5 py-0.5 text-xs text-muted-foreground hover:bg-muted"
          >
            × Clear
          </button>
        )}
      </div>

      {/* SVG viewport */}
      <div
        ref={containerRef}
        className={[
          "overflow-hidden border-t",
          isDragging ? "cursor-grabbing" : "cursor-grab",
        ].join(" ")}
        style={{ height: 420 }}
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        <svg
          width={svgW}
          height={svgH}
          style={{
            transform:       `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
            transformOrigin: "top left",
            transition:      isDragging ? "none" : "transform 0.08s ease-out",
            display:         "block",
          }}
        >
          {/* ── Dendrogram U-paths ── */}
          {icoord.map((xs, i) => {
            const ys   = dcoord[i];
            const x0   = scaleX(xs[0]);
            const x3   = scaleX(xs[3]);
            const yBot0 = scaleY(ys[0]);
            const yTop  = scaleY(ys[1]); // ys[1] == ys[2] (merge height)
            const yBot3 = scaleY(ys[3]);
            const d = `M ${x0} ${yBot0} L ${x0} ${yTop} L ${x3} ${yTop} L ${x3} ${yBot3}`;
            return (
              <path
                key={i}
                d={d}
                fill="none"
                stroke={pathColors[i]}
                strokeWidth={1.8}
                strokeLinecap="round"
                strokeLinejoin="round"
                opacity={
                  selectedCluster !== null &&
                  leaves.some(l => Math.abs(l.x - x0) < 2 || Math.abs(l.x - x3) < 2) &&
                  !leaves.some(l =>
                    (Math.abs(l.x - x0) < 2 || Math.abs(l.x - x3) < 2) &&
                    l.cid === selectedCluster
                  )
                    ? 0.2
                    : 1
                }
              />
            );
          })}

          {/* ── Leaf nodes ── */}
          {leaves.map(({ label, x, y, cid, clusterLabel }) => {
            const dimmed = selectedCluster !== null && selectedCluster !== cid;
            const hovered = hoveredDoc === label;
            return (
              <g
                key={label}
                transform={`translate(${x}, ${y})`}
                onClick={() => handleClusterClick(cid)}
                onMouseEnter={e => {
                  setHoveredDoc(label);
                  setTooltipPos({ x: e.clientX, y: e.clientY });
                }}
                onMouseLeave={() => setHoveredDoc(null)}
                style={{ cursor: "pointer" }}
              >
                {/* Leaf dot */}
                <circle
                  r={hovered ? 5 : 3.5}
                  fill={clusterColor(cid)}
                  opacity={dimmed ? 0.2 : 1}
                  style={{ transition: "r 0.1s" }}
                />
                {/* Rotated label */}
                <text
                  transform="rotate(-55)"
                  textAnchor="end"
                  fontSize={9}
                  fill={dimmed ? "#cbd5e1" : clusterColor(cid)}
                  dx={-6}
                  dy={3}
                  style={{ userSelect: "none" }}
                >
                  {label.length > 28 ? `${label.slice(0, 25)}…` : label}
                </text>
              </g>
            );
          })}

          {/* ── SVG tooltip (shown near hovered leaf) ── */}
          {(() => {
            if (!hoveredDoc) return null;
            const leaf = leaves.find(l => l.label === hoveredDoc);
            if (!leaf) return null;
            const tx = Math.min(leaf.x + 12, svgW - 220);
            const ty = Math.max(leaf.y - 60, PAD_TOP + 4);
            return (
              <g transform={`translate(${tx}, ${ty})`} pointerEvents="none">
                <rect
                  x={0} y={0} width={215} height={46}
                  rx={5} ry={5}
                  fill="white"
                  stroke="#e2e8f0"
                  strokeWidth={1}
                  filter="drop-shadow(0 1px 3px rgba(0,0,0,0.12))"
                />
                {/* Colour accent bar */}
                <rect
                  x={0} y={0} width={4} height={46}
                  rx={5}
                  fill={clusterColor(leaf.cid)}
                />
                <text x={12} y={17} fontSize={10} fontWeight="600" fill="#0f172a">
                  {leaf.label.length > 30 ? `${leaf.label.slice(0, 27)}…` : leaf.label}
                </text>
                <text x={12} y={32} fontSize={9} fill="#64748b">
                  {leaf.clusterLabel}
                </text>
                <text x={12} y={43} fontSize={9} fill="#94a3b8">
                  Click to filter · scroll to zoom
                </text>
              </g>
            );
          })()}
        </svg>
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between border-t px-4 py-2 text-xs text-muted-foreground">
        <span>Cached: {new Date(data.generated_at).toLocaleString()}</span>
        <span>Scroll to zoom · drag to pan · click to filter</span>
      </div>
    </div>
  );
}
