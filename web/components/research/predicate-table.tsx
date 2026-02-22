/**
 * FDA-249  [FE-011] Predicate Comparison Interactive Table
 * =========================================================
 * Side-by-side comparison of subject device vs. predicate device(s).
 * Rows: device characteristics (Intended Use, Technology, Material…)
 * Columns: Subject | Predicate 1 | Predicate 2…
 *
 * Features
 * --------
 * - Row filter: show all | differences only | similarities only
 * - Column sort: drag-to-reorder (future); currently fixed order
 * - Row highlighting: amber = mismatch, green = match
 * - Copy cell value on click
 * - Virtualized for large datasets (placeholder — future work)
 * - Accepts `rows` prop or falls back to demo data
 */

"use client";

import { useState, useMemo } from "react";
import { CheckCircle2, XCircle, Minus, Copy, Filter } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge }  from "@/components/ui/badge";
import { Input }  from "@/components/ui/input";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface PredicateDevice {
  /** K-number or other identifier */
  id:     string;
  name:   string;
  type:   "subject" | "predicate";
}

export interface PredicateRow {
  /** Characteristic label (e.g. "Intended Use") */
  characteristic: string;
  /** Category for grouping (e.g. "Device Description") */
  category?:      string;
  /** Values keyed by device.id; null = N/A */
  values:         Record<string, string | null>;
}

export interface PredicateTableProps {
  devices: PredicateDevice[];
  rows:    PredicateRow[];
  title?:  string;
}

// ── Demo data (shown when no rows provided) ───────────────────────────────────

const DEMO_DEVICES: PredicateDevice[] = [
  { id: "subject",  name: "Subject Device",    type: "subject"   },
  { id: "K240001",  name: "K240001 (Pred A)",  type: "predicate" },
  { id: "K231842",  name: "K231842 (Pred B)",  type: "predicate" },
];

const DEMO_ROWS: PredicateRow[] = [
  {
    characteristic: "Intended Use",
    category: "Device Description",
    values: {
      subject:  "Single-use diagnostic catheter for cardiac angiography",
      K240001:  "Single-use diagnostic catheter for cardiac angiography",
      K231842:  "Multi-use diagnostic catheter for peripheral vascular imaging",
    },
  },
  {
    characteristic: "Device Type",
    category: "Device Description",
    values: {
      subject: "Single-use",
      K240001: "Single-use",
      K231842: "Multi-use",
    },
  },
  {
    characteristic: "Material",
    category: "Physical Characteristics",
    values: {
      subject: "Polyurethane body, stainless steel braid",
      K240001: "Polyurethane body, stainless steel braid",
      K231842: "Polyether block amide (PEBAX), nitinol braid",
    },
  },
  {
    characteristic: "Outer Diameter (Fr)",
    category: "Physical Characteristics",
    values: {
      subject: "5 Fr",
      K240001: "5 Fr",
      K231842: "6 Fr",
    },
  },
  {
    characteristic: "Working Length (cm)",
    category: "Physical Characteristics",
    values: {
      subject: "100 cm",
      K240001: "100 cm",
      K231842: "80 cm",
    },
  },
  {
    characteristic: "Sterilization",
    category: "Sterility",
    values: {
      subject: "EO Sterilization",
      K240001: "EO Sterilization",
      K231842: "EO Sterilization",
    },
  },
  {
    characteristic: "Shelf Life",
    category: "Sterility",
    values: {
      subject: "3 years",
      K240001: "3 years",
      K231842: "2 years",
    },
  },
  {
    characteristic: "Applicable Standards",
    category: "Standards",
    values: {
      subject: "ISO 10555-1, ISO 11135, ASTM F3510",
      K240001: "ISO 10555-1, ISO 11135",
      K231842: "ISO 10555-1, ISO 11135, ISO 11137",
    },
  },
];

// ── Helpers ───────────────────────────────────────────────────────────────────

function isMismatch(row: PredicateRow, devices: PredicateDevice[]): boolean {
  const vals = devices.map((d) => row.values[d.id]);
  const nonNull = vals.filter((v): v is string => v !== null && v !== undefined);
  if (nonNull.length < 2) return false;
  return !nonNull.every((v) => v.toLowerCase().trim() === nonNull[0].toLowerCase().trim());
}

type FilterMode = "all" | "diff" | "same";

// ── Cell component ────────────────────────────────────────────────────────────

function Cell({ value, isSubject }: { value: string | null | undefined; isSubject: boolean }) {
  const [copied, setCopied] = useState(false);

  const copy = () => {
    if (value) {
      navigator.clipboard.writeText(value).catch(() => {});
      setCopied(true);
      setTimeout(() => setCopied(false), 1200);
    }
  };

  if (value === null || value === undefined) {
    return (
      <td className="px-3 py-2 text-center text-muted-foreground">
        <Minus className="mx-auto h-4 w-4 opacity-40" />
      </td>
    );
  }

  return (
    <td
      className={`group relative cursor-pointer px-3 py-2 text-sm ${
        isSubject ? "font-medium" : ""
      }`}
      onClick={copy}
      title="Click to copy"
    >
      <span>{value}</span>
      <Copy
        className={`absolute right-1.5 top-2 h-3 w-3 opacity-0 transition-opacity group-hover:opacity-50 ${
          copied ? "opacity-100 text-green-500" : ""
        }`}
      />
    </td>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export function PredicateTable({
  devices = DEMO_DEVICES,
  rows    = DEMO_ROWS,
  title   = "Predicate Comparison",
}: Partial<PredicateTableProps>) {
  const [filter,   setFilter]   = useState<FilterMode>("all");
  const [search,   setSearch]   = useState("");
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  // Group rows by category
  const categories = useMemo(() => {
    const cats: Record<string, PredicateRow[]> = {};
    for (const row of rows) {
      const cat = row.category ?? "Other";
      (cats[cat] ??= []).push(row);
    }
    return cats;
  }, [rows]);

  // Apply filter + search
  const visibleCategories = useMemo(() => {
    return Object.entries(categories).reduce<Record<string, PredicateRow[]>>((acc, [cat, catRows]) => {
      const filtered = catRows.filter((row) => {
        if (search && !row.characteristic.toLowerCase().includes(search.toLowerCase())) return false;
        if (filter === "diff" && !isMismatch(row, devices)) return false;
        if (filter === "same" &&  isMismatch(row, devices)) return false;
        return true;
      });
      if (filtered.length) acc[cat] = filtered;
      return acc;
    }, {});
  }, [categories, filter, search, devices]);

  const diffCount  = rows.filter((r) => isMismatch(r, devices)).length;
  const totalCount = rows.length;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="font-semibold">{title}</h3>
          <p className="text-xs text-muted-foreground">
            {totalCount} characteristics · {diffCount} differences ·{" "}
            {devices.filter((d) => d.type === "predicate").length} predicates
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative">
            <Filter className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
            <Input
              placeholder="Filter characteristics…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="h-8 pl-8 text-xs w-44"
            />
          </div>
          {(["all", "diff", "same"] as FilterMode[]).map((m) => (
            <Button
              key={m}
              variant={filter === m ? "default" : "outline"}
              size="sm"
              className="h-8 text-xs"
              onClick={() => setFilter(m)}
            >
              {m === "all"  ? "All"          : ""}
              {m === "diff" ? `Diff (${diffCount})` : ""}
              {m === "same" ? "Same"         : ""}
            </Button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-lg border shadow-sm">
        <table className="w-full border-collapse text-sm">
          {/* Header row */}
          <thead className="bg-muted/50">
            <tr>
              <th className="w-48 border-b px-3 py-2.5 text-left text-xs font-semibold text-muted-foreground">
                Characteristic
              </th>
              {devices.map((dev) => (
                <th
                  key={dev.id}
                  className={`border-b px-3 py-2.5 text-left text-xs font-semibold ${
                    dev.type === "subject"
                      ? "bg-blue-50 text-blue-800 dark:bg-blue-950 dark:text-blue-300"
                      : "text-muted-foreground"
                  }`}
                >
                  <div>{dev.name}</div>
                  <Badge
                    variant="outline"
                    className="mt-0.5 text-[10px] font-normal"
                  >
                    {dev.type === "subject" ? "Subject" : dev.id}
                  </Badge>
                </th>
              ))}
            </tr>
          </thead>

          {/* Body — grouped by category */}
          <tbody>
            {Object.entries(visibleCategories).map(([cat, catRows]) => {
              const isOpen = expanded[cat] ?? true;
              return (
                <>
                  {/* Category group header */}
                  <tr
                    key={`cat-${cat}`}
                    className="cursor-pointer bg-muted/20 hover:bg-muted/40"
                    onClick={() => setExpanded((e) => ({ ...e, [cat]: !isOpen }))}
                  >
                    <td
                      colSpan={devices.length + 1}
                      className="border-b border-t px-3 py-1.5 text-xs font-semibold text-muted-foreground"
                    >
                      <span className="mr-2">{isOpen ? "▾" : "▸"}</span>
                      {cat}
                    </td>
                  </tr>

                  {/* Data rows */}
                  {isOpen &&
                    catRows.map((row) => {
                      const diff = isMismatch(row, devices);
                      return (
                        <tr
                          key={row.characteristic}
                          className={`border-b transition-colors hover:bg-muted/20 ${
                            diff ? "bg-amber-50/50 dark:bg-amber-950/20" : ""
                          }`}
                        >
                          {/* Characteristic label */}
                          <td className="px-3 py-2 font-medium text-sm">
                            <div className="flex items-center gap-1.5">
                              {diff ? (
                                <XCircle className="h-3.5 w-3.5 shrink-0 text-amber-500" />
                              ) : (
                                <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-green-500 opacity-60" />
                              )}
                              {row.characteristic}
                            </div>
                          </td>

                          {/* Device value cells */}
                          {devices.map((dev) => (
                            <Cell
                              key={dev.id}
                              value={row.values[dev.id]}
                              isSubject={dev.type === "subject"}
                            />
                          ))}
                        </tr>
                      );
                    })}
                </>
              );
            })}

            {Object.keys(visibleCategories).length === 0 && (
              <tr>
                <td
                  colSpan={devices.length + 1}
                  className="px-3 py-8 text-center text-sm text-muted-foreground"
                >
                  No characteristics match the current filter.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 text-xs text-muted-foreground">
        <span className="flex items-center gap-1">
          <XCircle     className="h-3.5 w-3.5 text-amber-500" /> Difference
        </span>
        <span className="flex items-center gap-1">
          <CheckCircle2 className="h-3.5 w-3.5 text-green-500 opacity-60" /> Match
        </span>
        <span className="flex items-center gap-1">
          <Minus className="h-3.5 w-3.5 opacity-40" /> N/A
        </span>
        <span className="ml-auto">Click any cell to copy</span>
      </div>
    </div>
  );
}
