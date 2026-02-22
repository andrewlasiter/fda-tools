import * as React from "react";
import { cn } from "@/lib/utils";

export type AgentStatus = "idle" | "running" | "waiting" | "done" | "failed";

const STATUS_CONFIG: Record<
  AgentStatus,
  { label: string; dotClass: string; chipClass: string }
> = {
  idle:    { label: "Idle",    dotClass: "bg-slate-400",  chipClass: "agent-idle" },
  running: { label: "Running", dotClass: "bg-blue-500 animate-pulse", chipClass: "agent-running" },
  waiting: { label: "Waiting", dotClass: "bg-amber-500",  chipClass: "agent-waiting" },
  done:    { label: "Done",    dotClass: "bg-green-500",  chipClass: "agent-done" },
  failed:  { label: "Failed",  dotClass: "bg-red-500",    chipClass: "agent-failed" },
};

interface AgentStatusChipProps {
  status: AgentStatus;
  className?: string;
  showDot?: boolean;
}

export function AgentStatusChip({
  status,
  className,
  showDot = true,
}: AgentStatusChipProps) {
  const config = STATUS_CONFIG[status];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium",
        config.chipClass,
        className
      )}
    >
      {showDot && (
        <span className={cn("w-1.5 h-1.5 rounded-full flex-shrink-0", config.dotClass)} />
      )}
      {config.label}
    </span>
  );
}
