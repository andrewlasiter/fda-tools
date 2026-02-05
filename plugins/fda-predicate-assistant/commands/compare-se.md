---
description: Generate FDA Substantial Equivalence comparison tables for 510(k) submissions — device-type specific rows, multi-predicate support, auto-populated from FDA data
allowed-tools: Read, Glob, Grep, Bash, Write, WebFetch, WebSearch
argument-hint: "--predicates K241335[,K234567] [--references K345678] [--product-code CODE]"
---

# FDA Substantial Equivalence Comparison Table Generator

Generate a structured SE comparison table per FDA 21 CFR 807.87(f) for inclusion in a 510(k) submission. The table compares the user's subject device against one or more predicate devices and optional reference devices.

**KEY PRINCIPLE: Auto-populate predicate and reference columns from FDA data.** Fetch and extract predicate/reference device information yourself — the user should only need to fill in their own device's details.

## Parse Arguments

From the arguments, extract:

- `--predicates K123456[,K234567]` (required) — One or more predicate K-numbers, comma-separated
- `--references K345678[,K456789]` (optional) — Reference devices (not predicates, but cited for specific features)
- `--product-code CODE` (optional) — 3-letter FDA product code. If omitted, detect from first predicate
- `--device-description TEXT` (optional) — Brief description of the subject device
- `--intended-use TEXT` (optional) — Subject device intended use / IFU
- `--output FILE` (optional) — Write table to a file (markdown or CSV)
- `--depth quick|standard|deep` (optional, default: standard)

If no `--predicates` provided, ask the user. If they're unsure, suggest running `/fda:research` first.

## Step 1: Identify Product Code & Select Template

### Detect product code
If `--product-code` not provided, look up the first predicate:
```bash
grep "KNUMBER" ~/fda-510k-data/extraction/pmn96cur.txt 2>/dev/null | head -1
```
Extract the product code field.

### Select device-type template

Based on product code, select the appropriate row template. The template determines which characteristics (rows) are relevant for this device type.

**CGM / Glucose Monitors** (SBA, QBJ, QLG, QDK, NBW, CGA, LFR, SAF):
Rows: Intended Use, Indications for Use, Measurement Principle, Measurand/Analyte, Sample Type, Reportable Range, Accuracy (MARD), Sensor Duration/Life, Calibration, Sensor Placement, Data Display/Communication, Wireless/Connectivity, AID Compatibility, Biocompatibility, Sterilization, Shelf Life, Software/Firmware, Electrical Safety, MRI Safety, Clinical Data

**Wound Dressings** (KGN, FRO, MGP):
Rows: Intended Use, Indications for Use, Dressing Type/Category, Materials/Composition, Layer Structure, Contact Layer, Adhesive Border, Sizes Available, Fluid Handling/Absorption, MVTR, Antimicrobial Agent (if applicable), Antimicrobial Testing, Biocompatibility, Sterilization, Shelf Life, Clinical Data

**Orthopedic Implants** (various):
Rows: Intended Use, Indications for Use, Device Configuration, Materials, Anatomical Site, Fixation Method, Surface Treatment, Mechanical Testing (fatigue, compression, etc.), Biocompatibility, Sterilization, Shelf Life, Clinical Data

**Cardiovascular** (DXY, DTB, etc.):
Rows: Intended Use, Indications for Use, Device Design, Materials, Contact Duration, Blood Contact, Hemodynamic Performance, Biocompatibility, Sterilization, Shelf Life, MRI Safety, Clinical Data

**Default (Unknown Product Code)**:
Rows: Intended Use, Indications for Use, Device Description, Technology/Principle of Operation, Materials, Key Performance Characteristics, Biocompatibility, Sterilization, Shelf Life, Software (if applicable), Electrical Safety (if applicable), Clinical Data

## Step 2: Load Predicate & Reference Device Data

### Check PDF text cache

For each predicate and reference K-number, check if text is available:

```python
import json, os

# Try per-device cache first
cache_dir = os.path.expanduser('~/fda-510k-data/extraction/cache')
index_file = os.path.join(cache_dir, 'index.json')

if os.path.exists(index_file):
    with open(index_file) as f:
        index = json.load(f)
    for knumber in all_devices:
        if knumber in index:
            device_path = os.path.join(os.path.expanduser('~/fda-510k-data/extraction'), index[knumber]['file_path'])
            with open(device_path) as f:
                device_data = json.load(f)
            text = device_data['text']
else:
    # Legacy: monolithic pdf_data.json
    pdf_json = os.path.expanduser('~/fda-510k-data/extraction/pdf_data.json')
    if os.path.exists(pdf_json):
        with open(pdf_json) as f:
            data = json.load(f)
        for knumber in all_devices:
            key = f'{knumber}.pdf'
            if key in data:
                entry = data[key]
                text = entry.get('text', '') if isinstance(entry, dict) else str(entry)
```

### Fetch missing PDFs from FDA

**CRITICAL: Do NOT ask the user to download PDFs.** Use the BatchFetch download method:

```bash
python3 << 'PYEOF'
import requests, sys, os, tempfile

knumber = "KNUMBER"  # Replace per device
yy = knumber[1:3]

urls = [
    f"https://www.accessdata.fda.gov/cdrh_docs/pdf{yy}/{knumber}.pdf",
    f"https://www.accessdata.fda.gov/cdrh_docs/reviews/{knumber}.pdf",
]

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
})
session.cookies.update({'fda_gdpr': 'true', 'fda_consent': 'true'})

for url in urls:
    try:
        response = session.get(url, timeout=60, allow_redirects=True)
        if response.status_code == 200 and 'application/pdf' in response.headers.get('Content-Type', ''):
            tmp = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
            tmp.write(response.content)
            tmp.close()
            import fitz
            doc = fitz.open(tmp.name)
            text = "\n".join(page.get_text() for page in doc)
            doc.close()
            os.unlink(tmp.name)
            if len(text.strip()) > 100:
                print(f"SUCCESS:{len(text)}")
                print(text)
                sys.exit(0)
    except Exception as e:
        print(f"FAILED:{url}:{e}")
print("FAILED:all")
sys.exit(1)
PYEOF
```

If fetch fails, fall back to WebSearch for key details. If that also fails, mark the column as "[Data unavailable — manual entry required]".

Add a 5-second delay between downloads if fetching multiple PDFs.

### Also load FDA database records

**Try the openFDA API first** (richer data), then fall back to flat files:

```bash
python3 << 'PYEOF'
import urllib.request, urllib.parse, json, os, re

settings_path = os.path.expanduser('~/.claude/fda-predicate-assistant.local.md')
api_key = os.environ.get('OPENFDA_API_KEY')  # Env var takes priority (never enters chat)
api_enabled = True
if os.path.exists(settings_path):
    with open(settings_path) as f:
        content = f.read()
    if not api_key:  # Only check file if env var not set
        m = re.search(r'openfda_api_key:\s*(\S+)', content)
        if m and m.group(1) != 'null':
            api_key = m.group(1)
    m = re.search(r'openfda_enabled:\s*(\S+)', content)
    if m and m.group(1).lower() == 'false':
        api_enabled = False

knumber = "KNUMBER"  # Replace per device

if api_enabled:
    params = {"search": f'k_number:"{knumber}"', "limit": "1"}
    if api_key:
        params["api_key"] = api_key
    url = f"https://api.fda.gov/device/510k.json?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (FDA-Plugin/1.0)"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            if data.get("results"):
                r = data["results"][0]
                print(f"APPLICANT:{r.get('applicant', 'N/A')}")
                print(f"DEVICE_NAME:{r.get('device_name', 'N/A')}")
                print(f"DECISION_DATE:{r.get('decision_date', 'N/A')}")
                print(f"DECISION_CODE:{r.get('decision_code', 'N/A')}")
                print(f"PRODUCT_CODE:{r.get('product_code', 'N/A')}")
                print(f"CLEARANCE_TYPE:{r.get('clearance_type', 'N/A')}")
                print(f"STATEMENT_OR_SUMMARY:{r.get('statement_or_summary', 'N/A')}")
                print(f"SOURCE:api")
            else:
                print("SOURCE:fallback")
    except:
        print("SOURCE:fallback")
else:
    print("SOURCE:fallback")
PYEOF
```

If the API returned `SOURCE:fallback`, use flat files:

```bash
grep "KNUMBER" ~/fda-510k-data/extraction/pmn96cur.txt 2>/dev/null
```

Extract: applicant, decision date, product code, decision code, review time, submission type, summary/statement.

## Step 3: Extract Key Characteristics from Predicate Text

For each predicate/reference device text, use the section patterns from `references/section-patterns.md` to extract:

### Universal extraction (all device types):

1. **Indications for Use** — Look for IFU section, extract the full IFU text
2. **Device Description** — Extract description section, summarize into 2-3 sentences
3. **SE Comparison** — If the predicate itself has an SE table, extract it (contains its own predicate chain info)
4. **Biocompatibility** — Extract ISO 10993 tests performed and results
5. **Sterilization** — Method, standard, SAL level
6. **Shelf Life** — Duration, storage conditions
7. **Clinical Data** — Study type, N, key results

### Device-type specific extraction:

Apply the device-specific patterns from `references/section-patterns.md`. For example, for CGM devices, also extract:
- MARD value
- Reportable range
- Sensor duration
- Calibration requirements
- Matched pairs count
- Study sites

For each extracted characteristic:
- Use the **exact text** from the predicate when possible (for IFU, key specs)
- **Summarize** longer sections into 1-2 sentences (for descriptions, testing)
- Mark as "[Not specified in summary]" if the information isn't found

## Step 4: Generate the Comparison Table

### Table Structure

```
| Characteristic | Subject Device | Predicate: {K-number} ({Company}) | [Predicate 2 if multiple] | [Reference: {K-number}] | Comparison |
```

### Column Rules

**Subject Device column:**
- If `--device-description` or `--intended-use` provided, use that text
- Otherwise, mark each cell as `[YOUR DEVICE: specify]`
- Always provide guidance on what to fill in: `[YOUR DEVICE: e.g., "14-day subcutaneous glucose sensor"]`

**Predicate columns:**
- Auto-fill from extracted PDF text
- Use exact quoted text for IFU and key specs
- Summarize longer sections
- Include specific numbers (MARD values, test sample sizes, etc.)

**Reference Device columns** (if --references provided):
- Same as predicate columns but labeled differently
- Include a note explaining WHY this device is cited as a reference (e.g., "Referenced for antimicrobial claim precedent")

**Comparison column:**
- **Same** — Identical characteristic
- **Similar** — Minor differences that don't raise new safety/effectiveness questions
- **Different** — Requires justification. Add brief explanation: "Different: Subject device uses 14-day sensor vs predicate 365-day. Addressed by [testing type]."
- `[REVIEW NEEDED]` — Couldn't determine automatically; user must assess

### Auto-comparison logic

```python
def auto_compare(subject_text, predicate_text):
    if not subject_text or subject_text.startswith('[YOUR DEVICE'):
        return '[REVIEW NEEDED — fill in subject device first]'

    subject_lower = subject_text.lower().strip()
    pred_lower = predicate_text.lower().strip()

    # Exact or near-exact match
    if subject_lower == pred_lower:
        return 'Same'

    # Check for common "same" patterns
    same_patterns = [
        ('iso 10993', 'iso 10993'),  # Both reference same standard family
        ('ethylene oxide', 'ethylene oxide'),  # Same sterilization
        ('interstitial fluid', 'interstitial fluid'),  # Same sample type
    ]
    for s_pat, p_pat in same_patterns:
        if s_pat in subject_lower and p_pat in pred_lower:
            return 'Same'

    # If both mention the same standards/methods, likely similar
    # Otherwise mark for review
    return '[REVIEW NEEDED]'
```

## Step 5: Format and Output

### Console output (default)

Present the table in clean markdown format. Add header and footer:

```markdown
# Substantial Equivalence Comparison Table
**Subject Device:** {device_description or "[To be specified]"}
**Predicate Device(s):** {K-numbers with device names}
**Reference Device(s):** {K-numbers with device names, or "None"}
**Product Code:** {CODE} — {Device Name} (Class {class})
**Generated:** {date}

---

{THE TABLE}

---

## Auto-populated from FDA data:
- {K123456}: 510(k) Summary ({text_length} chars) — fetched {date}
- {K234567}: FDA Review ({text_length} chars) — fetched {date}

## Cells requiring your input: {count}
Look for `[YOUR DEVICE: ...]` cells — these need your device specifications.

## Cells requiring your review: {count}
Look for `[REVIEW NEEDED]` cells — verify the auto-generated comparison is correct.

## Next Steps:
1. Fill in all `[YOUR DEVICE: ...]` cells with your device specifications
2. Review all `[REVIEW NEEDED]` cells and update the Comparison column
3. For any "Different" characteristics, add justification explaining how differences don't raise new questions of safety/effectiveness
4. Have your regulatory team review for completeness per 21 CFR 807.87(f)

⚠ IMPORTANT: This comparison table is AI-generated from publicly available
FDA data. Accuracy is not guaranteed — verify all entries independently.
This is not regulatory advice. Do not include private or IP-protected
information in your inputs. Anything you send may be used for Anthropic
model training depending on your account settings.
```

### File output (--output)

If `--output FILE` specified:
- `.md` extension: Write markdown table
- `.csv` extension: Write CSV with proper quoting
- No extension: Default to markdown

```bash
# Write to file
cat << 'EOF' > /path/to/output.md
{FULL TABLE WITH HEADERS AND FOOTERS}
EOF
echo "SE comparison table written to /path/to/output.md"
```

## Step 6: Interactive Refinement

After generating the initial table, offer:

```markdown
The SE comparison table has been generated. You can:

1. **Fill in your device details** — I'll walk you through each `[YOUR DEVICE]` cell
2. **Add a row** — Specify an additional characteristic to compare
3. **Remove a row** — If a characteristic isn't relevant to your device
4. **Change a predicate** — Swap or add a predicate/reference device
5. **Export** — Save to a file (markdown or CSV)

What would you like to do?
```

If the user asks to fill in their device details, go through each `[YOUR DEVICE]` cell one at a time using AskUserQuestion, presenting the predicate's value as context:

```
For "Sensor Duration": The predicate (K241335) specifies "Up to 1 year".
What is your device's sensor duration?
```

## Device-Type Template Details

### CGM Template Rows

| Row | What to Extract | Where to Find |
|-----|----------------|---------------|
| Intended Use | Full IFU text | IFU section or Form FDA 3881 |
| Measurement Principle | Sensing technology | Device Description section |
| Measurand | "Glucose in interstitial fluid" | IFU or Device Description |
| Sample Type | Interstitial fluid, blood, etc. | Device Description |
| Reportable Range | "40-400 mg/dL" | Analytical Performance |
| Accuracy (MARD) | "MARD: 9.1%" | Clinical/Accuracy section |
| Within 20/20% | "92.1%" | Accuracy tables |
| Sensor Duration | "Up to 1 year" | IFU or Device Description |
| Sensor Placement | "Subcutaneous, upper arm" | Device Description |
| Calibration | "Factory calibrated" or "User calibration" | Device Description |
| Warm-up Time | "24 hours" or "30 minutes" | Performance section |
| Data Display | "Mobile app via BLE" | Device Description |
| AID Compatibility | "Compatible with AID systems" | IFU |
| Alerts | "Hypo/hyper alerts, predictive alerts" | IFU or Device Description |
| MRI Safety | "MR Conditional / MR Unsafe" | Special Conditions |
| Transmitter | Battery life, recharging | Device Description |
| Biocompatibility | ISO 10993 parts tested | Biocompatibility section |
| Sterilization | Method, standard, SAL | Sterilization section |
| Shelf Life | Duration, storage conditions | Shelf Life section |
| Software | IEC 62304, cybersecurity | Software section |
| Electrical Safety | IEC 60601-1 | Electrical Safety section |
| Clinical Data | Study name, N, design | Clinical section |

### Wound Dressing Template Rows

| Row | What to Extract | Where to Find |
|-----|----------------|---------------|
| Intended Use | Full IFU text | IFU section |
| Wound Types | "Partial/full thickness, pressure ulcers..." | IFU |
| Dressing Type | "Foam", "Hydrocolloid", "Collagen" | Device Description |
| Materials | "Polyurethane foam, silicone adhesive..." | Device Description |
| Layers | "3-layer: contact, absorbent, backing" | Device Description |
| Contact Layer | "Non-adherent silicone" | Device Description |
| Adhesive Border | "Yes, silicone-based" | Device Description |
| Sizes | "10x10cm, 15x15cm, 20x20cm" | Device Description or Labeling |
| Fluid Handling | "Absorption: X g/100cm2" | Performance Testing |
| MVTR | "X g/m2/24hr" | Performance Testing |
| Antimicrobial | "Silver ion, X mg/cm2" | Device Description |
| Antimicrobial Testing | "AATCC 100: S. aureus, P. aeruginosa" | Performance Testing |
| Biocompatibility | ISO 10993 parts tested | Biocompatibility section |
| Sterilization | Method, standard | Sterilization section |
| Shelf Life | Duration, conditions | Shelf Life section |
| Clinical Data | Study type, N, outcomes | Clinical section |

## Step 7: Integration with Submission Outline

After generating the SE comparison table, check if a `submission_outline.md` exists in the project folder:

```bash
ls "$PROJECTS_DIR/$PROJECT_NAME/submission_outline.md" 2>/dev/null
```

If found, offer to export the SE table as a section for the submission:

```
A submission outline exists for this project. Would you like to:
1. Export this SE table as Section 9 of the submission outline
2. Keep the SE table as a standalone file
3. Both — save standalone and update the outline
```

If the user chooses to export, append or replace the SE Comparison section in `submission_outline.md`:

```markdown
### 9. Substantial Equivalence Comparison
**Applicable:** Yes
**Status:** Ready

{THE FULL SE COMPARISON TABLE}

**Generated:** {date}
**Predicates:** {K-numbers}
**Cells requiring input:** {count}
**Cells requiring review:** {count}
```

Also update the Submission Readiness Summary table in the outline to mark SE Comparison as "✓".

## Important Notes

- **NEVER recommend** "Use /fda:extract" or "Run another command to get this data". Fetch what you need.
- If a PDF fetch fails, note it gracefully: "K234567 summary PDF was not accessible; predicate data populated from FDA database records only."
- The table is a **starting point** — users MUST review and edit before submitting to FDA.
- For **multiple predicates**, each gets its own column. If comparing >3 devices total (subject + predicates + references), consider splitting into separate tables.
- The Comparison column should reference the PRIMARY predicate. If using multiple predicates for different claims, note which predicate each "Same/Different" applies to.
