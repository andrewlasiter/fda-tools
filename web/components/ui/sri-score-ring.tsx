"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

interface SRIScoreRingProps {
  score: number;        // 0–100
  size?: number;        // SVG diameter in px (default 80)
  strokeWidth?: number; // (default 8)
  className?: string;
  showLabel?: boolean;
}

/**
 * Circular progress ring for Submission Readiness Index (SRI) scores.
 *
 * Color logic:
 *   0–39  → red (not ready)
 *   40–69 → amber (partial)
 *   70–89 → blue (good)
 *   90–100 → green (submission ready)
 */
export function SRIScoreRing({
  score,
  size = 80,
  strokeWidth = 8,
  className,
  showLabel = true,
}: SRIScoreRingProps) {
  const clampedScore = Math.max(0, Math.min(100, score));
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (clampedScore / 100) * circumference;

  const color =
    clampedScore >= 90 ? "#1A7F4B" :  // success green
    clampedScore >= 70 ? "#005EA2" :  // FDA blue
    clampedScore >= 40 ? "#B45309" :  // warning amber
                         "#C0152A";   // danger red

  const label =
    clampedScore >= 90 ? "Ready" :
    clampedScore >= 70 ? "Good" :
    clampedScore >= 40 ? "Partial" :
                         "Not ready";

  return (
    <div className={cn("flex flex-col items-center gap-1", className)}>
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        role="img"
        aria-label={`SRI Score: ${clampedScore} / 100 — ${label}`}
      >
        {/* Background track */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth={strokeWidth}
          className="text-muted"
          opacity={0.2}
        />
        {/* Progress arc */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          style={{ transform: "rotate(-90deg)", transformOrigin: "center" }}
        />
        {/* Score text */}
        <text
          x="50%"
          y="50%"
          dominantBaseline="middle"
          textAnchor="middle"
          fontSize={size * 0.22}
          fontWeight="700"
          fontFamily="Plus Jakarta Sans, system-ui, sans-serif"
          fill={color}
        >
          {clampedScore}
        </text>
      </svg>
      {showLabel && (
        <span className="text-xs font-medium text-muted-foreground">{label}</span>
      )}
    </div>
  );
}
