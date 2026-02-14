---
description: Feature-based predicate discovery — search ALL sections of 510(k) summaries for materials, technologies, testing methods, or any keyword
allowed-tools: Bash, Read, Glob, Write
argument-hint: "--features 'wireless, Bluetooth' [--product-codes DQY,DSM] [--min-confidence N] [--limit N]"
---

# FDA Predicate Feature Search

> Search across ALL sections of 510(k) summaries (not just SE sections) to find predicates by material, technology, feature, or keyword.

## Parse Arguments

From `$ARGUMENTS`, extract:

- `--features "keyword1, keyword2, ..."` — Features/keywords to search for (comma-separated)
- `--product-codes CODE1,CODE2` — Filter to specific product codes (optional)
- `--min-confidence N` — Minimum confidence score (default: 10)
- `--limit N` — Max results to return (default: 20)
- `--project NAME` — Write results to a project folder (optional)
- `--export csv|json|md` — Export format (default: md)

## Examples

```bash
# Material search
/fda:search-predicates --features "PEEK, titanium, cobalt-chrome"

# Technology search
/fda:search-predicates --features "wireless, Bluetooth, RF communication" --product-codes DQY,DSM

# Testing method search
/fda:search-predicates --features "fatigue testing, torsion testing" --product-codes OVE

# Clinical data search
/fda:search-predicates --features "clinical study, pivotal trial" --product-codes QKQ
```

## Resolve Plugin Root

```bash
FDA_PLUGIN_ROOT=$(python3 -c "
import json, os
f = os.path.expanduser('~/.claude/plugins/installed_plugins.json')
if os.path.exists(f):
    d = json.load(open(f))
    for k, v in d.get('plugins', {}).items():
        if k.startswith('fda-predicate-assistant@'):
            for e in v:
                p = e.get('installPath', '')
                if os.path.isdir(p):
                    print(p); exit()
print('')
")
```

## Step 1: Run Full-Text Search

Use the full_text_search.py module to search across ALL sections:

```bash
python3 "$FDA_PLUGIN_ROOT/scripts/full_text_search.py" \
  --features "$FEATURE1" "$FEATURE2" "$FEATURE3" \
  --product-codes "$CODE1" "$CODE2" \
  --min-confidence "$MIN_CONFIDENCE" \
  --limit "$LIMIT"
```

This searches:
- **SE sections** (40 pts confidence)
- **Testing sections** (25 pts)
- **Device description** (20 pts)
- **General text** (10 pts)

## Step 2: Parse Results

The output is JSON with:
```json
{
  "K123456": {
    "features_found": ["wireless", "Bluetooth"],
    "feature_count": 2,
    "sections": ["device_description", "performance_testing"],
    "confidence": 25,
    "match_count": 5,
    "snippets": [
      {
        "feature": "wireless",
        "section": "device_description",
        "snippet": "...device incorporates wireless communication via Bluetooth..."
      }
    ]
  }
}
```

## Step 3: Present Results

```
  FDA Feature Search Results
  Features: wireless, Bluetooth
  Product Codes: DQY, DSM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Found {N} predicates with matching features

TOP PREDICATES
────────────────────────────────────────

1. K241335 (Confidence: 40/40) — STRONGEST
   Features found: wireless, Bluetooth (2/2 features)
   Sections: device_description, predicate_se, performance_testing
   Match count: 8 mentions

   Snippets:
   • [device_description] "...device incorporates wireless communication..."
   • [predicate_se] "...same wireless technology as predicate K234567..."
   • [performance_testing] "...wireless coexistence testing per IEC..."

2. K238901 (Confidence: 25/40) — STRONG
   Features found: wireless (1/2 features)
   Sections: performance_testing, electrical_safety
   Match count: 3 mentions

   ⚠ Only found "wireless", missing "Bluetooth"

...

CROSS-PRODUCT-CODE RESULTS
────────────────────────────────────────

Your features have limited precedent in the primary product code.
Secondary predicates from adjacent product codes:

K234567 (Product Code: OVF) — wireless cervical disc prosthesis
  - Supports your wireless claim
  - Different product code but same anatomical site

FEATURE ANALYSIS
────────────────────────────────────────

Feature prevalence in results:
  wireless:   found in 8/10 predicates
  Bluetooth:  found in 3/10 predicates

⚠ "Bluetooth" has limited precedent — consider:
  - Using a secondary predicate from another product code
  - Providing additional testing data for Bluetooth specifically

NEXT STEPS
────────────────────────────────────────

1. Review top 3-5 predicates for formal selection:
   `/fda:validate --k-numbers K241335,K238901,K235678`

2. Compare your device to the top predicate:
   `/fda:compare-se --predicates K241335 --device-description "your device"`

3. Check safety/recall history:
   `/fda:safety --k-numbers K241335,K238901`
```

## Step 4: Write Results to Project (if --project specified)

If `--project NAME` is provided, write the search results to:

```
$PROJECTS_DIR/$PROJECT_NAME/feature_search_results.json
$PROJECTS_DIR/$PROJECT_NAME/feature_search_results.md  (human-readable)
```

Also add the top predicates to a `feature_predicate_candidates.txt` file for easy reference.

## Step 5: Export

If `--export` is specified, export results in the requested format:

- **csv**: K-number, features_found, confidence, sections, match_count
- **json**: Full structured data
- **md**: Formatted markdown report

## Error Handling

- **No structured cache**: "No structured text cache found. Run `/fda:extract` to populate the cache first, or the cache will be built on first search."
- **No matches**: "No predicates found with the specified features. Try broadening your search terms or removing product code filters."
- **Invalid product code**: "Product code {CODE} not found in database."

## Output Format

Always include:
1. Total predicates found
2. Top predicates with confidence scores
3. Feature prevalence analysis
4. Cross-product-code recommendations if applicable
5. Next steps

## Notes

- This searches ALL text, not just SE sections (unlike standard extraction)
- Confidence scoring reflects section context (SE=40, testing=25, general=10)
- Results sorted by: feature count (most features first), then confidence
- Cross-product-code search automatically triggers if <3 results in primary code
