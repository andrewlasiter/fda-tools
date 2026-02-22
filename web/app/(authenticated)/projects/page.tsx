"use client";

/**
 * Projects list page — /projects
 * Routes to /projects/[id] for individual NPD Workspaces.
 */

import React from "react";
import Link from "next/link";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const PROJECTS = [
  { id:"p1", name:"NextGen Glucose Monitor",   code:"DQY", class:"II", stage:"TESTING",   sri:78, status:"on-track"       },
  { id:"p2", name:"Laparoscopic Grasper v2",   code:"GEI", class:"II", stage:"PREDICATE", sri:52, status:"at-risk"        },
  { id:"p3", name:"Cardiac Ablation Catheter", code:"DQY", class:"III",stage:"TESTING",   sri:84, status:"on-track"       },
  { id:"p4", name:"AI Pathology Platform",     code:"QKQ", class:"II", stage:"CLASSIFY",  sri:41, status:"needs-attention"},
];

const STATUS_LABELS: Record<string, string> = {
  "on-track":        "On Track",
  "at-risk":         "At Risk",
  "needs-attention": "Needs Attention",
};

export default function ProjectsPage() {
  return (
    <div className="p-6 max-w-[1200px] mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold font-heading text-foreground">Projects</h1>
          <p className="text-sm text-muted-foreground mt-0.5">{PROJECTS.length} active NPD projects</p>
        </div>
        <Button className="bg-[#005EA2] hover:bg-[#003E73] text-white" size="sm">+ New Project</Button>
      </div>

      <div className="grid gap-3">
        {PROJECTS.map(p => (
          <Link key={p.id} href={`/projects/${p.id}`}>
            <Card className="hover:shadow-md transition-shadow cursor-pointer">
              <CardContent className="py-4 px-5">
                <div className="flex items-center gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="text-sm font-semibold text-foreground">{p.name}</h3>
                      <Badge variant="secondary" className="text-[9px]">Class {p.class}</Badge>
                    </div>
                    <p className="text-xs text-muted-foreground">Stage: {p.stage} · Code: {p.code}</p>
                  </div>
                  <div className="flex items-center gap-4 flex-shrink-0">
                    <div className="text-right">
                      <p className={cn("text-lg font-bold font-heading",
                        p.sri >= 70 ? "text-[#1A7F4B]" : p.sri >= 50 ? "text-[#B45309]" : "text-destructive"
                      )}>{p.sri}</p>
                      <p className="text-[10px] text-muted-foreground">SRI</p>
                    </div>
                    <Badge
                      variant={p.status === "on-track" ? "success" : p.status === "at-risk" ? "warning" : "destructive"}
                      className="text-[10px]"
                    >
                      {STATUS_LABELS[p.status]}
                    </Badge>
                  </div>
                </div>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
