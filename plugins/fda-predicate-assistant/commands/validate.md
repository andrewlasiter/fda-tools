---
description: Validate FDA device numbers against official databases
allowed-tools: Bash, Read, Grep
argument-hint: "<number> [number2] [number3] ..."
---

# FDA Device Number Validation

You are validating FDA device numbers against the official FDA database files.

## Device Number Formats

- **K-numbers (510(k))**: K + 6 digits (e.g., K240717, K991234)
- **P-numbers (PMA)**: P + 6 digits (e.g., P190001)
- **N-numbers (De Novo)**: DEN + digits (e.g., DEN200001)

## Validation Process

1. **Parse the input numbers** from `$ARGUMENTS`

2. **For each number, search the appropriate database:**

   For K-numbers (510(k)):
   ```bash
   grep -i "^$KNUMBER" "${CLAUDE_PLUGIN_ROOT}/../pmn*.txt" 2>/dev/null || echo "Not found in 510(k) database"
   ```

   For P-numbers (PMA):
   ```bash
   grep -i "^$PNUMBER" "${CLAUDE_PLUGIN_ROOT}/../pma.txt" 2>/dev/null || echo "Not found in PMA database"
   ```

3. **Report results for each number:**
   - Found: Show the full database record
   - Invalid format: Explain correct format
   - Not found: May be too new, typo, or OCR error

## OCR Error Suggestions

If a number is not found, suggest possible OCR corrections:
- O → 0 (letter O to zero)
- I → 1 (letter I to one)
- S → 5 (letter S to five)
- B → 8 (letter B to eight)

Example: K24O717 might be K240717

## Output Format

For each number, provide:
- **Number**: The device number
- **Details**: Database record if found, or suggestions if not found
