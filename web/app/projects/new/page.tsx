"use client";

/**
 * New Project form  /projects/new
 * Creates a new MDRP NPD project and redirects to the workspace.
 */

import * as React from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, FlaskConical, Loader2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { AppShell } from "@/components/layout/app-shell";

const PRODUCT_CODE_EXAMPLES = [
  { code: "DQY", desc: "Vascular catheter" },
  { code: "QKQ", desc: "Digital pathology software" },
  { code: "OVE", desc: "Spinal implant" },
  { code: "GEI", desc: "Electrosurgical device" },
];

export default function NewProjectPage() {
  const router = useRouter();
  const [name, setName]               = React.useState("");
  const [productCode, setProductCode] = React.useState("");
  const [submitting, setSubmitting]   = React.useState(false);
  const [error, setError]             = React.useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;

    setSubmitting(true);
    setError(null);

    try {
      // POST to bridge /projects (wired to backend in Sprint 5+)
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:18790"}/projects`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name:         name.trim(),
            product_code: productCode.trim().toUpperCase() || null,
            stage:        "CONCEPT",
          }),
        },
      );

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error((body as { detail?: string }).detail ?? `HTTP ${res.status}`);
      }

      const project = (await res.json()) as { id: string };
      router.push(`/projects/${project.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create project");
      setSubmitting(false);
    }
  }

  return (
    <AppShell>
      <div className="p-6 max-w-2xl mx-auto animate-fade-in">
        <div className="mb-6 flex items-center gap-3">
          <Link href="/projects" className="p-1 rounded hover:bg-muted transition-colors">
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <h1 className="text-2xl font-heading font-bold text-foreground">New Project</h1>
            <p className="text-sm text-muted-foreground">
              Start an NPD workflow for a new medical device
            </p>
          </div>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FlaskConical className="w-5 h-5 text-primary" />
              Device Details
            </CardTitle>
            <CardDescription>
              Enter your device name and product code to begin. You can update these later.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-5">
              {/* Device name */}
              <div className="space-y-1.5">
                <label htmlFor="name" className="text-sm font-medium text-foreground">
                  Device Name <span className="text-destructive">*</span>
                </label>
                <input
                  id="name"
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                  placeholder="e.g., SmartFlow Infusion Pump"
                  className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                />
              </div>

              {/* Product code */}
              <div className="space-y-1.5">
                <label htmlFor="product_code" className="text-sm font-medium text-foreground">
                  FDA Product Code
                  <span className="ml-1 text-xs text-muted-foreground">(optional)</span>
                </label>
                <input
                  id="product_code"
                  type="text"
                  value={productCode}
                  onChange={(e) => setProductCode(e.target.value.toUpperCase().slice(0, 3))}
                  placeholder="e.g., DQY"
                  maxLength={3}
                  className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm uppercase placeholder:text-muted-foreground placeholder:normal-case focus:outline-none focus:ring-2 focus:ring-ring font-mono"
                />
                <div className="flex flex-wrap gap-2 mt-1.5">
                  {PRODUCT_CODE_EXAMPLES.map(({ code, desc }) => (
                    <button
                      key={code}
                      type="button"
                      onClick={() => setProductCode(code)}
                      className="text-xs border border-border rounded px-2 py-1 hover:bg-muted transition-colors text-muted-foreground"
                    >
                      {code} — {desc}
                    </button>
                  ))}
                </div>
              </div>

              {/* Error */}
              {error && (
                <p className="text-sm text-destructive rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2">
                  {error}
                </p>
              )}

              {/* Submit */}
              <div className="flex items-center gap-3 pt-2">
                <Button type="submit" disabled={submitting || !name.trim()}>
                  {submitting ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Creating…
                    </>
                  ) : (
                    <>
                      <FlaskConical className="w-4 h-4 mr-2" />
                      Create Project
                    </>
                  )}
                </Button>
                <Button variant="ghost" asChild>
                  <Link href="/projects">Cancel</Link>
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}
