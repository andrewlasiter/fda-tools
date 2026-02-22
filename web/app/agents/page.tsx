import type { Metadata } from "next";
import { AgentPanel } from "@/components/agents/agent-panel";

export const metadata: Metadata = { title: "Agent Orchestration | MDRP" };

export default function AgentsPage() {
  return <AgentPanel />;
}
