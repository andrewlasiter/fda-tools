---
description: "List all command aliases — show short aliases for FDA Tools commands"
allowed-tools: Read
argument-hint: "[--list]"
---

# FDA Tools — Command Aliases

The following short aliases are available. Each alias is fully equivalent to its
target command — all arguments and flags are passed through unchanged.

| Alias | Full Command | Description |
|-------|-------------|-------------|
| `/fda-tools:a` | `/fda-tools:analyze` | Analyze a project, file, product code, or K-number |
| `/fda-tools:asm` | `/fda-tools:assemble` | Assemble final 510(k) submission package |
| `/fda-tools:b` | `/fda-tools:batchfetch` | Interactive 510(k) data collection with filtering |
| `/fda-tools:d` | `/fda-tools:draft` | Draft 510(k) submission sections |
| `/fda-tools:g` | `/fda-tools:gap-analysis` | Identify regulatory gaps |
| `/fda-tools:p` | `/fda-tools:pipeline` | Run full end-to-end analysis pipeline |
| `/fda-tools:pc` | `/fda-tools:pre-check` | Pre-submission readiness check (SRI scoring) |
| `/fda-tools:r` | `/fda-tools:research` | Research and plan a 510(k) submission |
| `/fda-tools:sp` | `/fda-tools:search-predicates` | Fingerprint-based predicate search |
| `/fda-tools:v` | `/fda-tools:validate` | Validate FDA device numbers |

## Usage Examples

```
/fda-tools:b --product-codes DQY --years 3 --enrich
# same as:
/fda-tools:batchfetch --product-codes DQY --years 3 --enrich

/fda-tools:v K241335
# same as:
/fda-tools:validate K241335

/fda-tools:pc --project my-project --depth deep
# same as:
/fda-tools:pre-check --project my-project --depth deep
```

## Adding Aliases

Aliases are defined as thin command files in `plugins/fda_tools/commands/`.
To add a custom alias, create a new `<alias>.md` file with the same
`allowed-tools` and `argument-hint` as the target command, and include a
delegation note pointing to the target. See any existing alias file (e.g.,
`v.md`) as a template.
