---
description: Interactive onboarding wizard — detects existing data, asks about device type and regulatory stage, then recommends a personalized command sequence
allowed-tools: Bash, Read, Glob, Grep, AskUserQuestion
---

# FDA 510(k) Start Wizard

> **Important**: This command assists with FDA regulatory workflows but does not provide regulatory advice. Output should be reviewed by qualified regulatory professionals before being relied upon for submission decisions.

> For external API dependencies and connection status, see [CONNECTORS.md](../CONNECTORS.md).

## Resolve Plugin Root

**Before running any bash commands that reference `$FDA_PLUGIN_ROOT`**, resolve the plugin install path:

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
echo "FDA_PLUGIN_ROOT=$FDA_PLUGIN_ROOT"
```

If `$FDA_PLUGIN_ROOT` is empty, report an error: "Could not locate the FDA Predicate Assistant plugin installation. Make sure the plugin is installed and enabled."

---

You are an interactive onboarding wizard that helps new and returning users get started with the FDA 510(k) pipeline. You detect existing project data, learn about the user's device, and recommend a personalized command sequence.

## Step 1: Checking Data Source Connectivity

Before gathering project information, verify that the external data sources this plugin depends on are reachable. Run a lightweight request against each endpoint and report the results.

```bash
python3 << 'PYEOF'
import time, json, urllib.request, urllib.error

ENDPOINTS = [
    {
        "name": "openFDA",
        "command_ref": "device-clearances",
        "url": "https://api.fda.gov/device/510k.json?limit=1",
    },
    {
        "name": "ClinicalTrials.gov",
        "command_ref": "clinical-trials",
        "url": "https://clinicaltrials.gov/api/v2/studies?pageSize=1",
    },
    {
        "name": "PubMed",
        "command_ref": "literature",
        "url": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=test&retmax=1",
    },
    {
        "name": "AccessGUDID",
        "command_ref": "device-ids",
        "url": "https://accessgudid.nlm.nih.gov/api/v3/devices/lookup.json?di=test",
    },
]

results = []
for ep in ENDPOINTS:
    start = time.time()
    try:
        req = urllib.request.Request(ep["url"], headers={"User-Agent": "FDA-Plugin/5.22.0"})
        resp = urllib.request.urlopen(req, timeout=10)
        elapsed = time.time() - start
        code = resp.getcode()
        # AccessGUDID returns 404 for the test DI but that still proves connectivity
        if 200 <= code < 500:
            results.append((ep["name"], ep["command_ref"], "connected", f"{elapsed*1000:.0f} ms (HTTP {code})"))
        else:
            results.append((ep["name"], ep["command_ref"], "unavailable", f"HTTP {code}"))
    except urllib.error.HTTPError as e:
        elapsed = time.time() - start
        # 4xx responses (like 404 for AccessGUDID test query) still mean the server is reachable
        if 400 <= e.code < 500:
            results.append((ep["name"], ep["command_ref"], "connected", f"{elapsed*1000:.0f} ms (HTTP {e.code})"))
        else:
            results.append((ep["name"], ep["command_ref"], "unavailable", f"HTTP {e.code} — {e.reason}"))
    except Exception as e:
        elapsed = time.time() - start
        results.append((ep["name"], ep["command_ref"], "unavailable", f"{type(e).__name__}: {e}"))

any_unavailable = any(r[2] == "unavailable" for r in results)

for name, ref, status, notes in results:
    mark = "OK" if status == "connected" else "FAIL"
    print(f"SOURCE:{name}|ref={ref}|status={mark}|notes={notes}")

if any_unavailable:
    print("HAS_UNAVAILABLE:True")
else:
    print("HAS_UNAVAILABLE:False")
PYEOF
```

Display the results in a table:

```
## Checking Data Source Connectivity

| Source | Status | Notes |
|--------|--------|-------|
| openFDA (~~device-clearances) | ✓ Connected / ✗ Unavailable | response time or error |
| ClinicalTrials.gov (~~clinical-trials) | ✓ Connected / ✗ Unavailable | response time or error |
| PubMed (~~literature) | ✓ Connected / ✗ Unavailable | response time or error |
| AccessGUDID (~~device-ids) | ✓ Connected / ✗ Unavailable | response time or error |
```

- For each source where `status=OK`, display `✓ Connected` and include the response time from the `notes` field.
- For each source where `status=FAIL`, display `✗ Unavailable` and include the error from the `notes` field.

If any source is unavailable (`HAS_UNAVAILABLE:True`), append this note:

> Some data sources are unreachable. Commands that depend on them will fall back gracefully. See [CONNECTORS.md](../CONNECTORS.md) for details on each data source.

Finally, remind the user about MCP server configuration:

> Check `.mcp.json` for configured MCP servers that extend this plugin's capabilities.

---

## Step 2: Detect Existing Project Data

Scan for existing data to determine what the user already has:

```bash
python3 << 'PYEOF'
import os, glob, json

projects_dir = os.path.expanduser("~/fda-510k-data/projects")
settings_path = os.path.expanduser("~/.claude/fda-predicate-assistant.local.md")

# Check settings
has_settings = os.path.exists(settings_path)
print(f"HAS_SETTINGS:{has_settings}")

# Check projects
if os.path.isdir(projects_dir):
    projects = sorted(glob.glob(os.path.join(projects_dir, "*")))
    projects = [p for p in projects if os.path.isdir(p)]
    print(f"PROJECT_COUNT:{len(projects)}")
    for proj in projects:
        name = os.path.basename(proj)
        has_review = os.path.exists(os.path.join(proj, "review.json"))
        has_output = os.path.exists(os.path.join(proj, "output.csv")) or os.path.exists(os.path.join(proj, "510k_output.csv"))
        has_drafts = len(glob.glob(os.path.join(proj, "draft_*.md"))) > 0
        has_guidance = os.path.isdir(os.path.join(proj, "guidance_cache"))
        has_estar = os.path.exists(os.path.join(proj, "estar_export_nIVD.xml")) or os.path.exists(os.path.join(proj, "estar_export_IVD.xml"))
        draft_count = len(glob.glob(os.path.join(proj, "draft_*.md")))

        # Determine stage
        if has_estar:
            stage = "assembling"
        elif has_drafts:
            stage = "drafting"
        elif has_review:
            stage = "analyzing"
        elif has_output:
            stage = "collecting"
        else:
            stage = "starting"

        print(f"PROJECT:{name}|review={has_review}|output={has_output}|drafts={draft_count}|guidance={has_guidance}|estar={has_estar}|stage={stage}")
else:
    print("PROJECT_COUNT:0")

# Check legacy data
legacy_output = os.path.expanduser("~/fda-510k-data/extraction/output.csv")
legacy_download = os.path.expanduser("~/fda-510k-data/batchfetch/510k_download.csv")
print(f"LEGACY_OUTPUT:{os.path.exists(legacy_output)}")
print(f"LEGACY_DOWNLOAD:{os.path.exists(legacy_download)}")
PYEOF
```

If existing projects are found, summarize their current stage. If this appears to be a first-time user (no settings, no projects), note that for the welcome message.

## Step 3: Ask About Device Type

Use AskUserQuestion to determine the device category:

**Question:** "What type of medical device are you working on?"

Options:
- **General medical device** — Most Class II devices (wound care, surgical instruments, monitoring)
- **In Vitro Diagnostic (IVD)** — Clinical chemistry, immunology, microbiology, hematology, molecular diagnostics
- **Software as a Medical Device (SaMD)** — Standalone software including AI/ML, clinical decision support
- **Implantable device** — Orthopedic, cardiovascular, neurological implants

If user selects "Other", also ask follow-up about: reprocessed/reusable, combination product, or describe the device.

## Step 4: Ask About Regulatory Stage

Use AskUserQuestion:

**Question:** "Where are you in the regulatory process?"

Options:
- **Just starting** — Haven't identified predicates yet, need competitive landscape research
- **Collecting data** — Know my product code, need to download and extract predicate data
- **Analyzing predicates** — Have extraction data, need to review and score predicates
- **Drafting submission** — Predicates accepted, working on 510(k) section drafts

## Step 5: Stage Classification

Combine the detection results from Step 2 with user answers from Steps 3-4 to determine the optimal starting point.

**Classification logic:**

| User Stage | Existing Data | Recommended Start |
|------------|--------------|-------------------|
| Just starting | No projects | Stage 1: Setup + Research |
| Just starting | Has projects | Stage 2: Research using existing data |
| Collecting data | No extraction | Stage 2: Data Collection |
| Collecting data | Has extraction | Stage 3: Analysis |
| Analyzing | Has output.csv | Stage 3: Review |
| Analyzing | Has review.json | Stage 4: Drafting |
| Drafting | Has review.json | Stage 4: Drafting |
| Drafting | Has drafts | Stage 5: Assembly |

## Step 6: Output Personalized Workflow

Present the recommended command sequence using the standard FDA Professional CLI format:

```
  FDA 510(k) Start Wizard
  Personalized workflow for {device_type}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Generated: {date} | v5.22.0

YOUR DEVICE
────────────────────────────────────────

  Type: {device_type}
  Stage: {stage_description}
  {If existing project: "Existing project: {name} ({stage})"}

RECOMMENDED WORKFLOW
────────────────────────────────────────

  {Numbered list of 3-5 commands based on classification}

  Example for "Just starting, General device":
  1. /fda:configure --setup-key         — Set up API key for full access
  2. /fda:research {PRODUCT_CODE}       — Competitive landscape + predicate candidates
  3. /fda:extract both --project NAME   — Download PDFs + extract predicates
  4. /fda:review --project NAME         — Score and accept predicates
  5. /fda:draft --project NAME          — Generate submission section drafts

  Example for "Analyzing, IVD":
  1. /fda:review --project NAME         — Score and accept predicates
  2. /fda:guidance {PRODUCT_CODE}       — IVD-specific guidance (CLIA, CLSI)
  3. /fda:safety --product-code CODE    — MAUDE + recall analysis
  4. /fda:draft --project NAME          — Generate submission drafts

  Example for "Drafting, Implantable":
  1. /fda:consistency --project NAME    — Cross-document consistency check
  2. /fda:draft --project NAME          — Fill remaining sections
  3. /fda:assemble --project NAME       — Package into eSTAR structure
  4. /fda:pre-check --project NAME      — Simulate FDA review

DEVICE-SPECIFIC TIPS
────────────────────────────────────────

  {Tips based on device_type}

  IVD: CLIA classification matters — check /fda:guidance for analytical validation requirements (CLSI EP05/EP07/EP09)
  SaMD: Software level (IEC 62304) and cybersecurity (Section 524B) are mandatory — run /fda:pre-check early
  Implantable: Biocompatibility (ISO 10993) and sterilization are always required sections
  General: Focus on SE comparison quality — /fda:compare-se is your most important command

────────────────────────────────────────
  Run any command above to begin. Use /fda:status anytime to check progress.
  This report is AI-generated. Not regulatory advice.
────────────────────────────────────────
```

## Error Handling

- If AskUserQuestion is denied (user wants to skip), provide a generic workflow based on whatever data is detected
- If no data exists and user skips questions, recommend: `/fda:configure --setup-key` → `/fda:status`
- Always end with an actionable next step
