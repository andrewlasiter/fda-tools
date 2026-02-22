import type { Metadata } from "next";
import { ProjectsContent } from "@/components/projects/projects-content";

export const metadata: Metadata = { title: "Projects | MDRP" };

export default function ProjectsPage() {
  return <ProjectsContent />;
}
