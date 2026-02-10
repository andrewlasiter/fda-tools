# FDA Professional CLI — Output Formatting Guide

This reference defines the standard formatting rules for all FDA Predicate Assistant command output. Every terminal-display command MUST follow these rules. Document-format commands (presub, compare-se, draft, etc.) follow markdown conventions instead but share the same disclaimer and status indicator standards.

## Design Language Rules

| Rule | Element | Standard |
|------|---------|----------|
| R1 | **Title Block** | Line 1: `  FDA {Report Type}` Line 2: `  {context}` Line 3: `━` heavy separator (56 chars) Line 4: `  Generated: {date} \| v5.22.0` |
| R2 | **Section Headings** | ALL CAPS, left-aligned, followed by `─` light separator (40 chars) |
| R3 | **Content Indent** | All body text and tables indented 2 spaces |
| R4 | **Tables** | Markdown pipe tables only (no box-drawing). Indented 2 spaces |
| R5 | **Status Indicators** | `✓` pass/present, `✗` fail/missing, `○` pending/unknown, `⚠` warning/degraded |
| R6 | **Scores** | `{score}/100 ({Rating})` — Strong (80-100), Moderate (50-79), Weak (0-49) |
| R7 | **Bar Charts** | `█` filled, `░` empty, max 20 chars wide |
| R8 | **Emphasis** | `**bold**` for field labels, backticks for paths/commands, plain for K-numbers |
| R9 | **Disclaimer** | Standard 4-line block: light separator, 2-line text, light separator |
| R10 | **Next Steps** | Every report ends with `NEXT STEPS` section, numbered list with `/fda:command` refs |
| R11 | **Documents vs Reports** | File-output commands use markdown format. Terminal-display commands use the CLI report format |
| R12 | **Errors** | `ERROR: {message}` then `  → {action to fix}` indented on next line |

## Standard Report Template

Use this for terminal-display commands (status, safety, validate, pipeline, pathway, review, lineage, monitor, portfolio, analyze, ask, consistency, summarize, extract post-summary):

```
  FDA {REPORT TYPE}
  {product_code} — {device_name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Generated: {date} | Project: {name} | v5.22.0

SECTION NAME
────────────────────────────────────────

  {Content indented 2 spaces}

  | Column 1 | Column 2 |
  |----------|----------|
  | value    | value    |

NEXT STEPS
────────────────────────────────────────

  1. {action} — `/fda:command`
  2. {action} — `/fda:command`

────────────────────────────────────────
  This report is AI-generated from public FDA data.
  Verify independently. Not regulatory advice.
────────────────────────────────────────
```

### Element Details

#### R1 — Title Block

The title block is 4 lines. Heavy separator is exactly 56 `━` characters.

```
  FDA Safety Intelligence Report
  QBJ — Bone Void Filler
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Generated: 2026-02-05 | Project: QBJ_2026 | v5.22.0
```

If there is no project context, omit `| Project: {name}`:

```
  Generated: 2026-02-05 | v5.22.0
```

#### R2 — Section Headings

Section headings are ALL CAPS with no indent, followed by a light separator of exactly 40 `─` characters on the next line.

```
ADVERSE EVENT SUMMARY
────────────────────────────────────────
```

#### R3 — Content Indent

All body content is indented 2 spaces. This includes text, tables, lists, and bar charts.

```
DEVICE CLASSIFICATION
────────────────────────────────────────

  Product Code: QBJ
  Device Name: Bone Void Filler
  Class: II
  Regulation: 21 CFR 888.3045
```

#### R4 — Tables

Use markdown pipe tables. Indent 2 spaces. No box-drawing characters (`┌─┬─┐│└─┴─┘├─┼─┤`).

```
  | Event Type   | Count | % of Total |
  |--------------|-------|------------|
  | Malfunction  | 1,245 | 68%        |
  | Injury       | 510   | 28%        |
  | Death        | 72    | 4%         |
```

#### R5 — Status Indicators

Use exactly these 4 symbols:

- `✓` — Pass, present, clean, done, found
- `✗` — Fail, missing, not found, error
- `○` — Pending, unknown, not checked, disabled, skipped
- `⚠` — Warning, degraded, partial, concerning

```
  predicate_extractor.py   ✓  Available
  batchfetch.py            ✓  Available
  foiaclass.txt            ✗  Not found
  openFDA API              ○  Disabled
  Stage 2 dependencies     ⚠  Partially installed
```

#### R6 — Scores

Format: `{score}/100 ({Rating})` with these thresholds:

- 80-100: Strong
- 50-79: Moderate
- 0-49: Weak

```
  Chain Health Score: 72/100 (Moderate)
  Confidence Score: 85/100 (Strong)
```

#### R7 — Bar Charts

Use `█` for filled and `░` for empty. Max width 20 characters. Scale to the maximum value.

```
  2020    125  ████████░░░░░░░░░░░░
  2021    198  ████████████░░░░░░░░
  2022    312  ████████████████████
  2023    245  ████████████████░░░░
```

#### R9 — Standard Disclaimer

Every report ends with the same 4-line disclaimer block. The light separator is 40 `─` characters.

```
────────────────────────────────────────
  This report is AI-generated from public FDA data.
  Verify independently. Not regulatory advice.
────────────────────────────────────────
```

#### R10 — Next Steps

Every report has a NEXT STEPS section before the disclaimer. Use numbered list with `/fda:command` references.

```
NEXT STEPS
────────────────────────────────────────

  1. Review accepted predicates — `/fda:review --project NAME`
  2. Run safety analysis — `/fda:safety --product-code CODE`
  3. Generate SE comparison — `/fda:compare-se --predicates K123456`
```

#### R12 — Error Format

```
ERROR: Product code not found in FDA classification database
  → Check the code and try again, or use --regulation NUMBER
```

## Document-Format Commands

Commands that write to files (presub, compare-se, draft, test-plan, traceability, submission-outline, pccp) use standard markdown headings (`#`, `##`, `###`) but MUST:

1. Use the same status indicators (R5) in any status tables
2. Use the same score format (R6)
3. End with the standard disclaimer text (R9), formatted as a markdown blockquote:

```markdown
> **Disclaimer:** This document is AI-generated from public FDA data.
> Verify independently. Not regulatory advice.
```

4. Include a Next Steps section (R10) as a markdown heading
