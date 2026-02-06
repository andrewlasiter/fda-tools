---
description: Summarize sections from 510(k) summary PDFs — compare indications, testing, device descriptions, or any section across filtered documents
allowed-tools: Read, Glob, Grep, Bash
argument-hint: "[--project NAME] [--product-codes CODE] [--years RANGE] [--sections NAMES] [--output FILE]"
---

# FDA 510(k) Section Summarization

You are summarizing and comparing sections from 510(k) summary PDF documents. The full text of processed PDFs is stored in a per-device cache (`cache/index.json` + `cache/devices/*.json`) or legacy `pdf_data.json`. You will filter documents by user criteria, detect section structure using centralized patterns from `references/section-patterns.md`, and produce cross-document summaries.

## Parse Arguments

Parse filters and section selection from `$ARGUMENTS`:

- `--product-codes CODE[,CODE]` — Filter by product code(s)
- `--years RANGE` — Year or range (e.g., `2020-2025` or `2023`)
- `--applicants NAME[;NAME]` — Filter by applicant/company name (semicolon-separated)
- `--committees CODE[,CODE]` — Advisory committee codes
- `--sections NAME[,NAME]` — Which sections to summarize (or `all`)
- `--project NAME` — Use data from a specific project folder
- `--knumbers K123456[,K234567]` — Specific K-numbers to analyze
- `--output FILE` — Write summary to file instead of (or in addition to) console output
- Free text query — Interpret as a natural language request (e.g., "clinical testing for KGN devices 2020-2024")

If no arguments provided, ask the user what they want to summarize.

## Step 1: Locate Data Sources

### If `--project NAME` is provided — Use project folder

```bash
PROJECTS_DIR="~/fda-510k-data/projects"  # or from settings
ls "$PROJECTS_DIR/$PROJECT_NAME/pdf_data.json" "$PROJECTS_DIR/$PROJECT_NAME/510k_download.csv" "$PROJECTS_DIR/$PROJECT_NAME/output.csv" 2>/dev/null
cat "$PROJECTS_DIR/$PROJECT_NAME/query.json" 2>/dev/null
```

Use the project's data files. The `query.json` tells you what filters were already applied, so additional filtering may not be needed.

### If no project — Use default locations

Check for per-device cache first (scalable), then fall back to legacy monolithic file:

```bash
# Per-device cache (preferred — scalable to 30K+ devices)
ls -la ~/fda-510k-data/extraction/cache/index.json 2>/dev/null

# Legacy monolithic file (fallback)
ls -la ~/fda-510k-data/extraction/pdf_data.json 2>/dev/null

# Metadata sources
ls -la ~/fda-510k-data/batchfetch/510k_download.csv 2>/dev/null
ls -la ~/fda-510k-data/extraction/output.csv 2>/dev/null
```

**Per-device cache structure**: `cache/index.json` maps K-numbers to file paths. Each device has its own JSON file at `cache/devices/K241335.json` containing `{"text": "...", "extraction_method": "...", "page_count": N}`. This is faster and more memory-efficient than loading a monolithic JSON file.

### Also check for projects that match the filter criteria

If no `--project` but `--product-codes` is specified, check if a matching project exists:
```bash
ls ~/fda-510k-data/projects/*/query.json 2>/dev/null
```

If found, suggest using that project's data.

**Required**: PDF text must be available — either per-device cache (`cache/index.json`) or legacy `pdf_data.json` (in project or default location). If neither exists, tell the user: "No PDF text is available for analysis yet. Use `/fda:extract` to download and process PDFs for this product code."

**Helpful**: `510k_download.csv` provides metadata (product code, applicant, decision date, Statement vs Summary) for filtering. If unavailable, filtering is limited to filename patterns.

## Step 2: Identify Matching Documents

### If `510k_download.csv` exists — Use metadata filtering

Read the CSV header and filter rows matching user criteria:

```bash
head -1 ~/fda-510k-data/batchfetch/510k_download.csv
```

Apply filters:
- Product code: column PRODUCTCODE
- Year: parse from DECISIONDATE column
- Applicant: column APPLICANT (case-insensitive partial match)
- Committee: column REVIEWADVISECOMM
- Statement vs Summary: column STATEORSUMM — **only Summaries have detailed sections**

Extract the list of matching K-numbers.

### If only per-device cache or pdf_data.json exists — Use K-number matching

**Per-device cache**: Read `cache/index.json` to get all available K-numbers. Filter by criteria.

**Legacy pdf_data.json**: K-numbers are embedded in filenames:
```bash
grep -o '"[^"]*\.pdf"' ~/fda-510k-data/extraction/pdf_data.json | head -20
```

Filter by K-number patterns if `--knumbers` provided.

### Report to user

Tell the user how many documents matched their filter before proceeding. If more than 50 documents match, suggest narrowing the filter.

## Step 3: Detect Section Structure

510(k) summary documents typically contain these standard sections (though naming varies):

| Common Section Name | Alternate Names |
|---------------------|-----------------|
| Indications for Use | Intended Use, IFU |
| Device Description | Product Description, Description of the Device |
| Substantial Equivalence Comparison | Predicate Comparison, Comparison to Predicate, SE Comparison, Technological Characteristics |
| Non-Clinical Testing | Performance Testing, Bench Testing, Performance Data |
| Clinical Testing | Clinical Data, Clinical Studies, Clinical Evidence, Clinical Information |
| Biocompatibility | Biological Evaluation, Biocompatibility Testing |
| Sterilization | Sterilization Validation, Sterility |
| Software | Software Description, Software Validation, Software Documentation |
| Electrical Safety | Electrical Safety Testing, IEC 60601 |
| Shelf Life | Stability, Package Testing, Shelf Life Testing |
| Labeling | Labels, Labeling Review |

For each matched document, read its text from the per-device cache (load `cache/devices/{knumber}.json`) or legacy `pdf_data.json`, and identify which sections are present by searching for section headers.

**Use the centralized patterns from `references/section-patterns.md`** for robust fuzzy matching. These patterns handle variations across years, sponsors, and document styles. Key patterns include:

- **Indications for Use**: `(?i)(indications?\s+for\s+use|intended\s+use|ifu|indication\s+statement|device\s+indications?|clinical\s+indications?|approved\s+use)`
- **Device Description**: `(?i)(device\s+description|product\s+description|description\s+of\s+(the\s+)?device|device\s+characteristics|physical\s+description|device\s+composition|device\s+components|system\s+description|system\s+overview)`
- **SE Comparison**: `(?i)(substantial\s+equivalence|se\s+comparison|predicate\s+(comparison|device|analysis|identification)|comparison\s+to\s+predicate|technological\s+characteristics|comparison\s+(table|chart|matrix)|similarities\s+and\s+differences)`
- **Non-Clinical Testing**: `(?i)(non[-]?clinical\s+(testing|studies|data|performance)|performance\s+(testing|data|evaluation|characteristics|bench)|bench\s+(testing|top\s+testing)|in\s+vitro\s+(testing|studies)|mechanical\s+(testing|characterization)|laboratory\s+testing|verification\s+(testing|studies)|validation\s+testing|analytical\s+performance)`
- **Clinical Testing**: `(?i)(clinical\s+(testing|trial|study|studies|data|evidence|information|evaluation|investigation|performance)|human\s+(subjects?|study|clinical)|patient\s+study|pivotal\s+(study|trial)|feasibility\s+study|literature\s+(review|search|summary|based)|clinical\s+experience)`
- **Biocompatibility**: `(?i)(biocompatib(ility|le)?|biological\s+(evaluation|testing|safety|assessment)|iso\s*10993|cytotoxicity|sensitization\s+test|irritation\s+test|systemic\s+toxicity|genotoxicity|implantation\s+(testing|studies|study)|hemocompatibility|material\s+characterization|extractables?\s+and\s+leachables?)`
- **Sterilization**: `(?i)(steriliz(ation|ed|ing)|sterility\s+(assurance|testing|validation)|ethylene\s+oxide|eto|gamma\s+(radiation|irradiation|steriliz)|electron\s+beam|steam\s+steriliz|autoclave|iso\s*11135|iso\s*11137|sal\s+10)`
- **Software**: `(?i)(software\s+(description|validation|verification|documentation|testing|v&v|lifecycle|architecture|design)|firmware|algorithm\s+(description|validation)|cybersecurity|iec\s*62304)`
- **Electrical Safety**: `(?i)(electrical\s+safety|iec\s*60601|electromagnetic\s+(compatibility|interference|disturbance)|emc|emi|wireless\s+(coexistence|testing))`
- **Shelf Life**: `(?i)(shelf[-]?life|stability\s+(testing|studies|data)|accelerated\s+aging|real[-]?time\s+aging|package\s+(integrity|testing|validation|aging)|astm\s*f1980|expiration\s+dat(e|ing)|storage\s+condition)`

Also apply **device-type-specific patterns** from `references/section-patterns.md` based on the product code (CGM, wound dressings, orthopedic, cardiovascular, IVD).

**Section extraction strategy** (from `references/section-patterns.md`):
1. Try header matching first — scan for patterns at start of lines or after page breaks
2. Handle numbered sections (`1.`, `I.`, `Section 1:`)
3. Handle ALL CAPS headers
4. Handle table-formatted SE sections (look for `|` or tab-delimited structures)
5. Fallback to semantic detection — if no header match, scan for keyword density (3+ domain keywords within 200 words)
6. Handle very short sections (<50 words) — check next 30 lines for continuation
7. Multi-page sections — skip page break indicators

### Present available sections

Show the user which sections were found and how many documents contain each:

```
Sections found across 23 matched documents:
  Indications for Use              23/23 documents
  Device Description               23/23 documents
  Substantial Equivalence          22/23 documents
  Non-Clinical Testing             20/23 documents
  Clinical Testing                  8/23 documents
  Biocompatibility                 15/23 documents
  Sterilization                    12/23 documents
  Software                          3/23 documents
```

If the user specified `--sections`, proceed directly. If not, ask which section(s) they want summarized.

## Step 4: Extract Section Text

For each matched document and selected section:

1. Find the section start (header match)
2. Find the section end (next section header or end of document)
3. Extract the text between start and end

Handle edge cases:
- Some documents have numbered sections (e.g., "4. Non-Clinical Testing")
- Some use ALL CAPS headers
- Some have no clear section breaks — extract best-effort paragraphs around keywords
- Very short sections (< 50 words) may indicate the section exists but lacks detail

## Step 5: Produce Summary

Based on the number of documents and sections:

### Single section, multiple documents → Cross-document comparison

Produce a synthesis that identifies:
- **Common patterns**: What do most documents describe similarly?
- **Variations**: Where do documents differ?
- **Trends over time**: If spanning multiple years, note evolution
- **Key details**: Specific test methods, standards cited, endpoints measured, sample sizes
- **Table format**: When comparing specific attributes (e.g., indications for use), use a comparison table

### Multiple sections, single document → Document deep-dive

Summarize each section of that document in sequence, preserving the narrative flow.

### Multiple sections, multiple documents → Comprehensive matrix

Create a matrix: rows = documents (identified by K-number + applicant), columns = sections. Fill each cell with a brief summary. Then provide cross-cutting analysis for each section.

### For specific section types, extract structured data:

**Indications for Use**:
- Target patient population
- Anatomical site
- Clinical condition
- Duration of use (permanent, temporary, transient)
- Prescription vs OTC

**Non-Clinical/Performance Testing**:
- Test methods and standards (ASTM, ISO, etc.)
- Sample sizes
- Pass/fail criteria
- Key results/endpoints

**Clinical Testing**:
- Study type (retrospective, prospective, literature review)
- Patient count
- Endpoints and follow-up duration
- Key outcomes and adverse events

**Biocompatibility**:
- ISO 10993 endpoints evaluated
- Testing laboratory
- Materials tested
- Results summary

**Substantial Equivalence Comparison**:
- Predicate device(s) cited
- Similarities acknowledged
- Differences identified
- How differences were addressed

## Output Format

Present the summary using the standard FDA Professional CLI format (see `references/output-formatting.md`):

```
  FDA Section Comparison Report
  {product_code} — {section_name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Generated: {date} | Documents: {N} matched | v4.0.0

FILTER SUMMARY
────────────────────────────────────────

  Product Codes: {codes}
  Years:         {range}
  Sections:      {section_names}
  Documents:     {N} matched, {N} with requested section

SECTION COVERAGE
────────────────────────────────────────

  | Section                  | Present | Coverage |
  |--------------------------|---------|----------|
  | Indications for Use      | {N}/{N} | ████████████████████ |
  | Device Description       | {N}/{N} | ██████████████████░░ |
  | Non-Clinical Testing     | {N}/{N} | ████████████████░░░░ |
  | Clinical Testing         | {N}/{N} | ████████░░░░░░░░░░░░ |

SYNTHESIS
────────────────────────────────────────

  {The actual summary/comparison content}

NOTABLE FINDINGS
────────────────────────────────────────

  {Anything unusual, interesting, or important}

NEXT STEPS
────────────────────────────────────────

  1. Compare specific sections — `/fda:summarize --sections "Non-Clinical Testing"`
  2. Run full research — `/fda:research PRODUCT_CODE`
  3. Generate SE comparison — `/fda:compare-se --predicates K123456`

────────────────────────────────────────
  This report is AI-generated from public FDA data.
  Verify independently. Not regulatory advice.
────────────────────────────────────────
```

## Step 6: Write Output

If `--output FILE` specified, write the summary to the specified file using the Write tool.

If `--project NAME` is specified but no `--output`, auto-write to:
`$PROJECTS_DIR/$PROJECT_NAME/summaries/summary_{sections}_{timestamp}.md`

Create the summaries directory if it doesn't exist:
```bash
mkdir -p "$PROJECTS_DIR/$PROJECT_NAME/summaries"
```

Report: "Summary written to {output_path}"

## Tips

- **Per-device cache** (`cache/devices/*.json`): Load individual device files directly — no need to parse the entire dataset
- **Legacy pdf_data.json**: Can be large. Use Grep to search for specific K-numbers rather than reading the whole file
- For very large result sets (>20 documents), summarize in batches and then synthesize
- Cross-reference with `510k_download.csv` to enrich summaries with metadata (applicant, decision date, review time)
- If a section is not found in a document, note it as "Section not present" rather than omitting silently
- Offer to export findings to a file if the summary is lengthy
- Consult `references/section-patterns.md` for the full set of fuzzy patterns and device-type-specific patterns
