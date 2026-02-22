"use client";

/**
 * Projects list page — /projects
 * Shows all NPD projects with stage, SRI score, and quick-action links.
 */

import * as React from "react";
import Link from "next/link";
import { Plus, FlaskConical, Clock, Search, ChevronRight } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { SRIScoreRing } from "@/components/ui/sri-score-ring";
import { timeAgo } from "@/lib/utils";
import { useProjects } from "@/lib/api-client";
import type { Project } from "@/lib/api-client";

function ProjectCard({ project }: { project: Project }) {
  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardContent className="py-4">
        <div className="flex items-center justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <Link
                href={`/projects/${project.id}`}
                className="font-heading font-semibold text-foreground hover:text-primary transition-colors truncate"
              >
                {project.name}
              </Link>
              {project.product_code && (
                <Badge variant="outline" className="text-xs">
                  {project.product_code}
                </Badge>
              )}
              <span className="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold bg-primary/10 text-primary">
                {project.stage.replace("_", " ")}
              </span>
            </div>
            <p className="text-xs text-muted-foreground mt-1.5 flex items-center gap-1">
              <Clock className="w-3 h-3" />
              Updated {timeAgo(project.updated_at)}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <SRIScoreRing score={project.sri_score} size={48} strokeWidth={5} showLabel={false} />
            <Link
              href={`/projects/${project.id}`}
              className="p-1 rounded hover:bg-muted transition-colors"
              title="Open workspace"
            >
              <ChevronRight className="w-4 h-4 text-muted-foreground" />
            </Link>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export function ProjectsContent() {
  const [search, setSearch] = React.useState("");
  const { data, isLoading, isError } = useProjects();
  const projects: Project[] = data?.projects ?? [];

  const filtered = projects.filter(
    (p) =>
      !search ||
      p.name.toLowerCase().includes(search.toLowerCase()) ||
      (p.product_code ?? "").toLowerCase().includes(search.toLowerCase()),
  );

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-heading font-bold text-foreground">Projects</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            {projects.length} active project{projects.length !== 1 ? "s" : ""}
          </p>
        </div>
        <Button size="sm" asChild>
          <Link href="/projects/new">
            <Plus className="w-4 h-4" />
            New Project
          </Link>
        </Button>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
        <input
          type="search"
          placeholder="Search projects…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full rounded-lg border border-input bg-background pl-9 pr-4 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
        />
      </div>

      {/* List */}
      <div className="space-y-3">
        {isLoading ? (
          Array.from({ length: 4 }).map((_, i) => (
            <Card key={i}>
              <CardContent className="py-4">
                <div className="flex items-center justify-between gap-4">
                  <div className="flex-1 space-y-2">
                    <div className="h-4 w-48 rounded bg-muted animate-pulse" />
                    <div className="h-3 w-24 rounded bg-muted animate-pulse" />
                  </div>
                  <div className="h-12 w-12 rounded-full bg-muted animate-pulse" />
                </div>
              </CardContent>
            </Card>
          ))
        ) : isError ? (
          <Card>
            <CardContent className="py-10 text-center text-sm text-muted-foreground">
              Could not load projects. Check the API connection.
            </CardContent>
          </Card>
        ) : filtered.length === 0 ? (
          <Card>
            <CardContent className="py-16 text-center">
              <FlaskConical className="w-12 h-12 text-muted-foreground/30 mx-auto mb-3" />
              <p className="text-muted-foreground text-sm">
                {search ? "No projects match your search." : "No projects yet."}
              </p>
              {!search && (
                <Button size="sm" className="mt-4" asChild>
                  <Link href="/projects/new">Create your first project</Link>
                </Button>
              )}
            </CardContent>
          </Card>
        ) : (
          filtered.map((project) => <ProjectCard key={project.id} project={project} />)
        )}
      </div>
    </div>
  );
}
