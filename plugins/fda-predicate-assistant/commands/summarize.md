---
description: Summarize sections from 510(k) summary PDFs — compare indications, testing, device descriptions, or any section across filtered documents
allowed-tools: Read, Glob, Grep, Bash
argument-hint: "[--project NAME] [--product-codes CODE] [--years RANGE] [--sections NAMES]"
---

# FDA 510(k) Section Summarization

You are summarizing and comparing sections from 510(k) summary PDF documents. The full text of processed PDFs is stored in `pdf_data.json`. You will filter documents by user criteria, detect section structure, and produce cross-document summaries.

## Parse Arguments

Parse filters and section selection from `$ARGUMENTS`:

- `--product-codes CODE[,CODE]` — Filter by product code(s)
- `--years RANGE` — Year or range (e.g., `2020-2025` or `2023`)
- `--applicants NAME[;NAME]` — Filter by applicant/company name (semicolon-separated)
- `--committees CODE[,CODE]` — Advisory committee codes
- `--sections NAME[,NAME]` — Which sections to summarize (or `all`)
- `--project NAME` — Use data from a specific project folder
- `--knumbers K123456[,K234567]` — Specific K-numbers to analyze
- Free text query — Interpret as a natural language request (e.g., "clinical testing for KGN devices 2020-2024")

If no arguments provided, ask the user what they want to summarize.

## Step 1: Locate Data Sources

### If `--project NAME` is provided — Use project folder

```bash
PROJECTS_DIR="/mnt/c/510k/Python/510k_projects"  # or from settings
ls "$PROJECTS_DIR/$PROJECT_NAME/pdf_data.json" "$PROJECTS_DIR/$PROJECT_NAME/510k_download.csv" "$PROJECTS_DIR/$PROJECT_NAME/output.csv" 2>/dev/null
cat "$PROJECTS_DIR/$PROJECT_NAME/query.json" 2>/dev/null
```

Use the project's data files. The `query.json` tells you what filters were already applied, so additional filtering may not be needed.

### If no project — Use legacy locations

```bash
ls -la /mnt/c/510k/Python/PredicateExtraction/pdf_data.json 2>/dev/null
ls -la /mnt/c/510k/Python/510kBF/510k_download.csv 2>/dev/null
ls -la /mnt/c/510k/Python/PredicateExtraction/output.csv 2>/dev/null
```

### Also check for projects that match the filter criteria

If no `--project` but `--product-codes` is specified, check if a matching project exists:
```bash
ls /mnt/c/510k/Python/510k_projects/*/query.json 2>/dev/null
```

If found, suggest using that project's data.

**Required**: `pdf_data.json` must exist (in project or legacy location). If not, tell the user to run `/fda:extract stage2` first.

**Helpful**: `510k_download.csv` provides metadata (product code, applicant, decision date, Statement vs Summary) for filtering. If unavailable, filtering is limited to filename patterns.

## Step 2: Identify Matching Documents

### If `510k_download.csv` exists — Use metadata filtering

Read the CSV header and filter rows matching user criteria:

```bash
head -1 /mnt/c/510k/Python/510kBF/510k_download.csv
```

Apply filters:
- Product code: column PRODUCTCODE
- Year: parse from DECISIONDATE column
- Applicant: column APPLICANT (case-insensitive partial match)
- Committee: column REVIEWADVISECOMM
- Statement vs Summary: column STATEORSUMM — **only Summaries have detailed sections**

Extract the list of matching K-numbers.

### If only `pdf_data.json` exists — Use filename matching

K-numbers are embedded in PDF filenames. Search for matching entries:

```bash
grep -o '"[^"]*\.pdf"' /mnt/c/510k/Python/PredicateExtraction/pdf_data.json | head -20
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

For each matched document, read its text from `pdf_data.json` and identify which sections are present by searching for section headers. Use case-insensitive regex patterns like:

- `(?i)(indications?\s+for\s+use|intended\s+use)`
- `(?i)(device\s+description|product\s+description)`
- `(?i)(substantial\s+equivalence|predicate\s+comparison|comparison\s+to\s+predicate|technological\s+characteristics)`
- `(?i)(non[- ]?clinical\s+testing|performance\s+(testing|data)|bench\s+testing)`
- `(?i)(clinical\s+(testing|data|studies|evidence|information))`
- `(?i)(biocompatib|biological\s+evaluation)`
- `(?i)(sterilization|sterility)`
- `(?i)(software\s+(description|validation|documentation))`
- `(?i)(electrical\s+safety|iec\s+60601)`
- `(?i)(shelf\s+life|stability|package\s+testing)`

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

Structure the output as:

1. **Filter Summary** — What was searched and how many documents matched
2. **Section Coverage** — Which sections found, frequency across documents
3. **Synthesis** — The actual summary/comparison content
4. **Notable Findings** — Anything unusual, interesting, or important
5. **Recommendations** — Suggested next steps (deeper analysis, additional filters, related commands)

## Tips

- `pdf_data.json` can be large. Use Grep to search for specific K-numbers rather than reading the whole file
- For very large result sets (>20 documents), summarize in batches and then synthesize
- Cross-reference with `510k_download.csv` to enrich summaries with metadata (applicant, decision date, review time)
- If a section is not found in a document, note it as "Section not present" rather than omitting silently
- Offer to export findings to a file if the summary is lengthy
