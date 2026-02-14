---
description: Generate regulatory prose drafts for 510(k) submission sections — device description, SE discussion, performance summary, testing rationale, predicate justification
allowed-tools: Bash, Read, Glob, Grep, Write, WebFetch, WebSearch
argument-hint: "<section> --project NAME [--device-description TEXT] [--intended-use TEXT] [--output FILE]"
---

# FDA 510(k) Section Draft Generator

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

---

You are generating regulatory prose drafts for specific sections of a 510(k) submission. Unlike outline/template commands, this produces first-draft regulatory prose that requires professional review, verification, and refinement before submission.

> **WARNING: LLM-generated prose carries confabulation risk.** Every factual claim, citation, and regulatory reference in the output must be independently verified by a qualified regulatory affairs professional before use in any submission. `[Source: ...]` tags reference internal plugin data files, not authoritative regulatory citations.

**KEY PRINCIPLE: Every claim must cite its source.** Use project data (review.json, guidance_cache, se_comparison.md) to substantiate every assertion. Mark unverified claims as `[CITATION NEEDED]`.

## Parse Arguments

From `$ARGUMENTS`, extract:

- **Section name** (required) — One of: `device-description`, `se-discussion`, `performance-summary`, `testing-rationale`, `predicate-justification`, `510k-summary`, `labeling`, `sterilization`, `shelf-life`, `biocompatibility`, `software`, `emc-electrical`, `clinical`, `cover-letter`, `truthful-accuracy`, `financial-certification`, `doc`, `human-factors`, `form-3881`, `reprocessing`, `combination-product`
- `--project NAME` (required) — Project with pipeline data
- `--device-description TEXT` — Description of the user's device
- `--intended-use TEXT` — Proposed indications for use
- `--product-code CODE` — Product code (auto-detect from project if not specified)
- `--output FILE` — Write draft to file (default: draft_{section}.md in project folder)
- `--infer` — Auto-detect product code from project data
- `--revise` — Revise an existing draft: regenerate AI content while preserving user edits (see Revision Workflow below)
- `--na` — Mark a section as "Not Applicable" with rationale template (see N/A Section Handling below)

## Step 0.5: Load All Project Data

**Before generating ANY section**, load and parse all available project data. This ensures every section can cross-reference sibling files instead of generating content in isolation.

```bash
python3 << 'PYEOF'
import json, os, re, glob

settings_path = os.path.expanduser('~/.claude/fda-predicate-assistant.local.md')
projects_dir = os.path.expanduser('~/fda-510k-data/projects')
if os.path.exists(settings_path):
    with open(settings_path) as f:
        m = re.search(r'projects_dir:\s*(.+)', f.read())
        if m: projects_dir = os.path.expanduser(m.group(1).strip())

project = "PROJECT"  # Replace with actual project name
pdir = os.path.join(projects_dir, project)

# Load all available data files
data_sources = {}

# device_profile.json → device_description, intended_use, materials
dp = os.path.join(pdir, 'device_profile.json')
if os.path.exists(dp):
    with open(dp) as f:
        data_sources['device_profile'] = json.load(f)
    print("LOADED:device_profile.json")

# review.json → accepted predicates, K-numbers, scores
rj = os.path.join(pdir, 'review.json')
if os.path.exists(rj):
    with open(rj) as f:
        data_sources['review'] = json.load(f)
    print("LOADED:review.json")

# se_comparison.md → predicate specs, sterilization method, materials
se = os.path.join(pdir, 'se_comparison.md')
if os.path.exists(se):
    with open(se) as f:
        data_sources['se_comparison'] = f.read()
    print("LOADED:se_comparison.md")
    # Extract sterilization method from SE comparison
    steril = re.search(r'[Ss]teriliz\w*[^|]*\|[^|]*\|[^|]*?(\bEO\b|ethylene oxide|gamma|radiation|steam|autoclave|electron beam)', data_sources['se_comparison'], re.I)
    if steril:
        print(f"SE_STERILIZATION:{steril.group(1)}")
    # Extract materials
    mat_section = re.findall(r'[Mm]aterial[^|]*\|([^|]+)\|', data_sources['se_comparison'])
    if mat_section:
        print(f"SE_MATERIALS:{'; '.join(m.strip() for m in mat_section)}")

# standards_lookup.json → all applicable standards
sl = os.path.join(pdir, 'standards_lookup.json')
if os.path.exists(sl):
    with open(sl) as f:
        data_sources['standards_lookup'] = json.load(f)
    count = len(data_sources['standards_lookup']) if isinstance(data_sources['standards_lookup'], list) else len(data_sources['standards_lookup'].keys())
    print(f"LOADED:standards_lookup.json ({count} standards)")

# test_plan.md → test categories, acceptance criteria
tp = os.path.join(pdir, 'test_plan.md')
if os.path.exists(tp):
    with open(tp) as f:
        data_sources['test_plan'] = f.read()
    print("LOADED:test_plan.md")

# calculations/ → shelf life AAF, sample sizes
calc_dir = os.path.join(pdir, 'calculations')
if os.path.isdir(calc_dir):
    for cf in glob.glob(os.path.join(calc_dir, '*.json')):
        fname = os.path.basename(cf)
        with open(cf) as f:
            data_sources[f'calc_{fname}'] = json.load(f)
        print(f"LOADED:calculations/{fname}")

# literature_cache.json → PubMed articles, evidence categories
lc = os.path.join(pdir, 'literature_cache.json')
if os.path.exists(lc):
    with open(lc) as f:
        data_sources['literature_cache'] = json.load(f)
    print("LOADED:literature_cache.json")

# safety data (if cached) → MAUDE event counts, failure modes
sc_dir = os.path.join(pdir, 'safety_cache')
if os.path.isdir(sc_dir):
    for sf in glob.glob(os.path.join(sc_dir, '*.json')):
        fname = os.path.basename(sf)
        with open(sf) as f:
            data_sources[f'safety_{fname}'] = json.load(f)
        print(f"LOADED:safety_cache/{fname}")

# import_data.json → imported eSTAR data
imp = os.path.join(pdir, 'import_data.json')
if os.path.exists(imp):
    with open(imp) as f:
        data_sources['import_data'] = json.load(f)
    print("LOADED:import_data.json")

# source_device_text_*.txt → raw PDF text (fallback when extracted_sections is empty)
for stf in glob.glob(os.path.join(pdir, 'source_device_text_*.txt')):
    fname = os.path.basename(stf)
    with open(stf) as f:
        text = f.read()
    data_sources[f'source_text_{fname}'] = text
    k_match = re.search(r'K\d{6}', fname)
    k_id = k_match.group(0) if k_match else 'unknown'
    print(f"LOADED:{fname} ({len(text)} chars, source K#{k_id})")

# Check data richness — flag sparse data for fallback handling
dp_data = data_sources.get('device_profile', {})
extracted = dp_data.get('extracted_sections', {})
has_description = bool(extracted.get('device_description', '').strip())
has_ifu = bool(dp_data.get('intended_use', '').strip()) and '[TODO' not in dp_data.get('intended_use', '')
has_materials = bool(dp_data.get('materials', []))
if not has_description and not has_ifu:
    print("SPARSE_DATA:true — extracted_sections empty, no IFU. Will use classification definition and source text as fallback.")
    # Try to get classification definition as fallback device description
    class_name = dp_data.get('classification_device_name', '')
    if class_name:
        print(f"FALLBACK_DEVICE_NAME:{class_name}")

# Existing drafts (for cross-referencing)
drafts_dir = os.path.join(pdir, 'drafts')
if os.path.isdir(drafts_dir):
    for df in glob.glob(os.path.join(drafts_dir, 'draft_*.md')):
        fname = os.path.basename(df)
        print(f"EXISTING_DRAFT:{fname}")

print(f"TOTAL_SOURCES:{len(data_sources)}")
PYEOF
```

**Data Threading Rules**: When generating any section, use the loaded project data according to these priority rules:

1. **User-provided arguments** (`--device-description`, `--intended-use`) take highest priority
2. **Project-specific files** (`device_profile.json`, `import_data.json`) take second priority
3. **Pipeline outputs** (`se_comparison.md`, `standards_lookup.json`, `test_plan.md`) take third priority
4. **Inferred from FDA data** (openFDA, predicate PDFs) take lowest priority
5. If no data source provides a value → use `[TODO: Company-specific — {description}]`

**CRITICAL**: Never generate a value in one section that contradicts data already stated in another project file. If `se_comparison.md` says "EO sterilized", the sterilization draft MUST say "EO" — not `[TODO: EO or Radiation]`.

**SPARSE DATA FALLBACK**: If `SPARSE_DATA:true` was reported in Step 0.5 (no extracted_sections, no IFU):
1. Read `source_device_text_*.txt` files — these contain raw 510(k) summary PDF text that may have device descriptions, IFU, and specs even when the regex parser couldn't extract structured sections
2. Use the `classification_device_name` field from device_profile.json as the device type identifier
3. Use the FDA classification `definition` text (from openFDA) as a fallback device description foundation
4. If peer devices are listed in review.json or device_profile.json, reference their device names and applicants to establish the product landscape
5. Generate more [TODO] placeholders than usual, but still provide structural frameworks (section headings, table templates, standard references) based on the product code and review panel

## Step 0.75: Brand Name Validation

**After loading project data (Step 0.5) and before generating any section**, validate that the applicant's identity is consistent with the device data:

1. Extract the `applicant` (or `applicant_name`, `company_name`) field from `device_profile.json`, `import_data.json`, or `review.json`
2. Scan the `intended_use`, `device_description`, and `extracted_sections` fields in `device_profile.json` for company/brand names
3. Compare: if a well-known competitor brand name appears as the *manufacturer* or *applicant* of the subject device (not as a predicate reference), this indicates peer-mode data leakage where predicate device data was incorrectly attributed to the subject device

**Known company name patterns to check:**
`KARL STORZ`, `Boston Scientific`, `Medtronic`, `Abbott`, `Johnson & Johnson`, `Ethicon`, `Stryker`, `Zimmer Biomet`, `Smith & Nephew`, `B. Braun`, `Cook Medical`, `Edwards Lifesciences`, `Becton Dickinson`, `BD`, `Baxter`, `Philips`, `GE Healthcare`, `Siemens Healthineers`, `Olympus`, `Hologic`, `Intuitive Surgical`, `Teleflex`, `ConvaTec`, `Coloplast`, `3M Health Care`, `Cardinal Health`, `Danaher`, `Integra LifeSciences`, `NuVasive`, `Globus Medical`, `DePuy Synthes`

**Detection logic:**
```python
applicant = device_profile.get('applicant', '') or device_profile.get('applicant_name', '') or ''
ifu_text = device_profile.get('intended_use', '')
desc_text = device_profile.get('device_description', '') or str(device_profile.get('extracted_sections', {}).get('device_description', ''))

known_companies = ["KARL STORZ", "Boston Scientific", "Medtronic", "Abbott", ...]  # full list above

for company in known_companies:
    if company.lower() != applicant.lower() and company.lower() in (ifu_text + ' ' + desc_text).lower():
        # Check if it appears as the subject device manufacturer (not just a predicate reference)
        # Predicate references are acceptable: "compared to {company}'s K123456"
        # Subject device claims are NOT: "manufactured by {company}" or "{company} {device_name}"
        print(f"BRAND_MISMATCH:{company}")
```

**If brand mismatch detected:**
- **WARN** the user: `"⚠ BRAND NAME MISMATCH: '{detected_company}' found in device data but applicant is '{applicant}'. This may indicate predicate data was incorrectly attributed to the subject device (peer-mode data leakage)."`
- In ALL generated sections, replace instances of the mismatched company name with `[TODO: Replace '{detected_company}' with your company name]` when it appears as the subject device manufacturer
- Do NOT replace company names that appear in predicate device references (e.g., "The predicate device, manufactured by {company}..." is fine)

---

## Available Sections

### 1. device-description

Generates Section 6 of the eSTAR: Device Description.

**Required data**: `--device-description` or device info from query.json
**Enriched by**: openFDA classification, guidance_cache

**Output structure**:
```markdown
## Device Description

### 6.1 Device Overview
{Synthesized from --device-description, enriched with classification data}

### 6.2 Principle of Operation
{Inferred from device description and product code classification}

### 6.3 Components and Materials (Bill of Materials)

{If --materials flag provided or import_data.json contains materials data, generate structured BOM:}

| # | Component | Material | Patient-Contacting | Supplier | Specification |
|---|-----------|----------|--------------------|----------|---------------|
| 1 | {component_name} | {material} | {Yes/No} | [TODO: Company-specific] | [TODO: Company-specific] |

{Auto-populate from project import_data.json materials array if available.}
{Cross-reference patient-contacting materials with biocompatibility requirements:}
{If patient-contacting → flag: "Biocompatibility testing required per ISO 10993-1:2025 — see `/fda:draft biocompatibility`"}

[TODO: Company-specific — provide detailed component list and materials of construction]

### 6.4 Accessories and Packaging
[TODO: Company-specific — list accessories, packaging components, and sterilization barrier]

### 6.4.1 Compatible Equipment

{Auto-detect: If device description or se_comparison contains keywords "generator", "console", "controller", "power supply", "light source", "camera head", "processor", "power unit", "energy source", generate this subsection. Otherwise omit.}

| # | Equipment | Function | Compatibility Requirements | Specification |
|---|-----------|----------|---------------------------|---------------|
| 1 | [TODO: e.g., Electrosurgical Generator] | [TODO: Primary function] | [TODO: Power range, connector type] | [TODO: Model numbers or specifications] |

[TODO: Company-specific — List all equipment required for device operation. For each, specify:
- Equipment type and model numbers
- Required power/energy settings
- Connector compatibility (proprietary vs. universal)
- Whether the equipment is included or sold separately
- Regulatory status of each compatible equipment item]

{Cross-reference: If se_comparison.md lists compatible equipment for the predicate, include a comparison note:}
> **Predicate Reference:** The predicate device ({K-number}) is compatible with {predicate_equipment}. [Source: se_comparison.md]

### 6.5 Illustrations
[TODO: Company-specific — attach device photographs, diagrams, and schematics]
```

### 2. se-discussion

Generates Section 7 narrative: Substantial Equivalence Discussion.

**Required data**: review.json (accepted predicates), se_comparison.md
**Enriched by**: predicate PDF text, openFDA data

**Output structure**:
```markdown
## Substantial Equivalence Discussion

### 7.1 Predicate Device Selection
The subject device is compared to {predicate K-number(s)} as the primary predicate device(s).
{Predicate K-number} was selected because: {rationale from review.json}.
[Source: review.json, confidence score: {score}/100]

### 7.2 Intended Use Comparison
The subject device and predicate share the same intended use: {IFU text}.
[Source: openFDA 510k API, predicate IFU from PDF text]

### 7.3 Technological Characteristics Comparison
{For each row in se_comparison.md where Comparison != "Same":}
The subject device differs from the predicate in {characteristic}:
- Subject: {value}
- Predicate: {value}
This difference does not raise new questions of safety or effectiveness because {justification}.
[Source: se_comparison.md]

### 7.4 Conclusion
Based on the comparison above, the subject device is substantially equivalent to {predicate(s)}
as defined under Section 513(i)(1)(A) of the Federal Food, Drug, and Cosmetic Act.
```

### 3. performance-summary

Generates performance testing summary from test-plan and guidance data.

**Required data**: test_plan.md or guidance_cache
**Enriched by**: predicate precedent from review.json

### 4. testing-rationale

Generates testing strategy rationale — why each test was selected.

**Required data**: guidance_cache, test_plan.md
**Enriched by**: predicate testing precedent

### 5. predicate-justification

Generates detailed predicate selection justification narrative.

**Required data**: review.json (accepted predicates with scores)
**Enriched by**: openFDA data, se_comparison.md, lineage.json

### 6. 510k-summary

Generates the full 510(k) Summary (per 21 CFR 807.92) — combines device description, IFU, SE discussion, and performance summary into a single document.

**Required data**: Multiple project files
**Enriched by**: All available pipeline data

### 7. labeling

Generates Section 9 of the eSTAR: Labeling (package label, IFU, patient labeling).

**Required data**: indications_for_use from import_data.json or `--intended-use`
**Enriched by**: openFDA classification, guidance_cache, predicate IFU, **UDI/GUDID data**

**Output structure**: See `references/draft-templates.md` Section 09. Includes:
- 9.1 Package Label template with UDI, Rx symbol, storage conditions
- 9.2 Instructions for Use with IFU text, contraindications, warnings, precautions, directions
- 9.3 Patient Labeling (if applicable)
- 9.4 Promotional Materials (if applicable)

**Artwork File Tracking**: If `--artwork-dir PATH` is specified, scan the directory for label artwork files (PDF, PNG, SVG, AI, EPS) and generate a manifest:

```markdown
### Artwork Files

| # | File | Format | Dimensions | Revision | Status |
|---|------|--------|------------|----------|--------|
| 1 | {filename} | {ext} | [TODO: Verify] | [TODO: Rev letter] | [TODO: Approved/Draft/Under Review] |
```

If no `--artwork-dir` specified, include:
```
[TODO: Company-specific — Provide label artwork files. Use --artwork-dir PATH to reference artwork directory.]
```

**UDI Integration**: When drafting the labeling section, auto-query the openFDA UDI endpoint to populate device properties:

```bash
python3 << 'PYEOF'
import urllib.request, urllib.parse, json, os, re

settings_path = os.path.expanduser('~/.claude/fda-predicate-assistant.local.md')
api_key = os.environ.get('OPENFDA_API_KEY')
if os.path.exists(settings_path):
    with open(settings_path) as f:
        content = f.read()
    if not api_key:
        m = re.search(r'openfda_api_key:\s*(\S+)', content)
        if m and m.group(1) != 'null':
            api_key = m.group(1)

product_code = "PRODUCT_CODE"  # Replace with actual
company = "COMPANY_NAME"       # Replace with actual or None

search_parts = []
if product_code and product_code != "None":
    search_parts.append(f'product_codes.code:"{product_code}"')
if company and company != "None":
    search_parts.append(f'company_name:"{company}"')

if not search_parts:
    print("UDI_SKIP:no_search_criteria")
    exit(0)

search = "+AND+".join(search_parts)
params = {"search": search, "limit": "100"}
if api_key:
    params["api_key"] = api_key

url = f"https://api.fda.gov/device/udi.json?{urllib.parse.urlencode(params)}"
headers = {"User-Agent": "Mozilla/5.0 (FDA-Plugin/5.21.0)"}

try:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
        for r in data.get("results", []):
            print(f"UDI_BRAND:{r.get('brand_name', 'N/A')}")
            print(f"UDI_RX:{r.get('is_rx', 'N/A')}")
            print(f"UDI_OTC:{r.get('is_otc', 'N/A')}")
            print(f"UDI_STERILE:{r.get('is_sterile', 'N/A')}")
            print(f"UDI_SINGLE_USE:{r.get('is_single_use', 'N/A')}")
            print(f"UDI_MRI:{r.get('mri_safety', 'N/A')}")
            print(f"UDI_LATEX:{r.get('is_labeled_as_nrl', 'N/A')}")
            for ident in r.get("identifiers", []):
                if ident.get("type") == "Primary":
                    print(f"UDI_PRIMARY_DI:{ident.get('id', 'N/A')}|{ident.get('issuing_agency', 'N/A')}")
            break  # Use first matching record
except Exception as e:
    print(f"UDI_SKIP:{e}")
PYEOF
```

Use UDI data to auto-populate in the labeling draft:
- **UDI placeholder**: Include the primary DI format and issuing agency
- **Rx/OTC symbol**: Based on `is_rx` / `is_otc` flags
- **Sterility marking**: Based on `is_sterile` flag
- **MRI safety marking**: Based on `mri_safety` field
- **Latex statement**: Based on `is_labeled_as_nrl` field
- **Single-use symbol**: Based on `is_single_use` flag

If UDI data is unavailable, include `[TODO: Verify UDI requirements — run /fda:udi --product-code CODE]` placeholders.

**Data threading from project files:**
- If `safety_cache/` exists with MAUDE data, generate a device-type-appropriate contraindications and warnings framework based on observed failure modes. For example, if MAUDE shows needle breakage events, include a warning about needle breakage risk in the IFU.
- Pull IFU text from `device_profile.json` `intended_use` field if available, and use it as the basis for the IFU section rather than generating generic placeholder text
- If `se_comparison.md` has predicate labeling information, reference it for labeling consistency

### 8. sterilization

Generates Section 10 of the eSTAR: Sterilization.

**Required data**: sterilization_method from import_data.json or test_plan.md
**Enriched by**: guidance_cache sterilization requirements

**Output structure**: See `references/draft-templates.md` Section 10. Includes:
- 10.1 Sterilization Method (EO, radiation, steam, or N/A)
- 10.2 SAL target
- 10.3 Validation summary (auto-selects standard by method: ISO 11135/11137/17665)
- 10.4 EO residuals (if applicable, per ISO 10993-7)
- 10.5 Packaging validation (ISO 11607)

Auto-detect if sterilization is applicable from device description keywords: "sterile", "sterilized", "implant", "surgical", "invasive".

**Data threading from project files:**
- Check `se_comparison.md` — if predicate sterilization method is stated (e.g., "EO sterilized", "gamma irradiation"), default to that method for the subject device instead of writing `[TODO: EO or Radiation]`
- Check `standards_lookup.json` — if ISO 11135 is listed, default to EO; if ISO 11137, default to radiation; if ISO 17665, default to steam
- Check `import_data.json` for `sterilization_method` field
- If multiple sources agree → use the agreed method
- If sources conflict → flag the conflict and use `[TODO: Resolve sterilization method — SE comparison says {X}, standards lookup implies {Y}]`

**Standards in sterilization drafts**: When listing "Applicable Standards" at the end of the sterilization section, list validation/process standards (ISO 17665, ISO 11737, AAMI TIR30, AAMI ST91, ANSI/AAMI ST77, etc.) as "Referenced Standards for Validation" — NOT as formal conformity declarations. This prevents duplication with and misalignment against the DoC (Section 08). The DoC contains the formal list; the sterilization section references standards it uses for validation.

### 9. shelf-life

Generates Section 11 of the eSTAR: Shelf Life.

**Required data**: shelf_life_claim from import_data.json or test_plan.md
**Enriched by**: guidance_cache

**Output structure**: See `references/draft-templates.md` Section 11. Includes:
- 11.1 Claimed shelf life
- 11.2 Aging study design (accelerated per ASTM F1980 + real-time)
- 11.3 Testing protocol (package integrity, sterility, functionality)
- 11.4 Results summary

For accelerated aging parameter calculations, reference `/fda:calc shelf-life`. The ASTM F1980 Q10 formula: `AAF = Q10^((T_accel - T_ambient)/10)`.

**Data threading from project files:**
- If `calculations/shelf_life_calc.json` exists, auto-populate AAF value, accelerated test duration, ambient/accelerated temperatures, and claimed shelf life from that file
- If no calculation file, check `se_comparison.md` for predicate shelf life claim and use it as a reference point: "The predicate device claims a shelf life of {X}. The subject device targets [TODO: specify claimed shelf life]."
- If `test_plan.md` mentions shelf life testing, pull the test protocol details into the draft

### 10. biocompatibility

Generates Section 12 of the eSTAR: Biocompatibility.

**Required data**: biocompat_contact_type, biocompat_materials from import_data.json or test_plan.md
**Enriched by**: guidance_cache, predicate materials from se_comparison.md

**Output structure**: See `references/draft-templates.md` Section 12. Includes:
- 12.1 Contact classification per ISO 10993-1:2025 (or ISO 10993-1:2018 during transition)
- 12.2 Biological evaluation plan with endpoint matrix
- 12.3 Testing summary
- 12.4 Predicate material equivalence justification (if applicable)

Auto-determine required endpoints based on contact type and duration.

**Data threading from project files:**
- Parse `drafts/draft_device-description.md` for all materials listed under "Materials of Construction", "Key Components", or the BOM table. Enumerate EACH specific material (e.g., "PTFE catheter", "stainless steel needle", "polycarbonate hub") in the contact classification table — do not use generic descriptions like "polymer" or "metal"
- If `se_comparison.md` lists predicate materials, include a comparison row showing material equivalence or differences
- If `import_data.json` has `biocompat_materials` or `materials` data, use it as the primary source for the materials list
- Cross-reference patient-contacting status from device_profile.json or import_data.json

### 11. software

Generates Section 13 of the eSTAR: Software/Cybersecurity.

**Required data**: software_doc_level from import_data.json or device description
**Enriched by**: guidance_cache, cybersecurity-framework.md

**Output structure**: See `references/draft-templates.md` Section 13. Includes:
- 13.1 Software classification (IEC 62304 Class A/B/C)
- 13.2 Software description
- 13.3 Software testing
- 13.4 Cybersecurity documentation (if Section 524B applies)

Auto-detect if cybersecurity applies from keywords: "wireless", "bluetooth", "wifi", "connected", "cloud", "network", "usb data", "usb communication".

### 12. emc-electrical

Generates Section 14 of the eSTAR: EMC/Electrical Safety.

**Required data**: Device description indicating electrical/electronic device
**Enriched by**: guidance_cache, standards-tracking.md

**Output structure**: See `references/draft-templates.md` Section 14. Includes:
- 14.1 Applicable standards table (IEC 60601-1, 60601-1-2, particular standards)
- 14.2 EMC testing summary
- 14.3 Electrical safety testing summary
- 14.4 Declaration of Conformity

Auto-detect applicability from keywords: "powered", "electronic", "electrical", "battery", "AC/DC".

### 13. clinical

Generates Section 16 of the eSTAR: Clinical Evidence.

**Required data**: literature.md from `/fda:literature`, safety_report.md from `/fda:safety`
**Enriched by**: review.json (predicate clinical data precedent), guidance_cache, **clinical-study-framework.md**

**Output structure**: See `references/draft-templates.md` Section 16. Includes:
- 16.1 Clinical evidence strategy (data/literature/exemption)
- 16.2 Clinical data summary with literature review
- 16.3 Adverse event analysis from MAUDE data
- 16.4 Clinical conclusion

Auto-determine strategy: if predicates had no clinical data, default to "no clinical data needed" with predicate precedent rationale.

**Data threading from project files:**
- If `literature_cache.json` exists, reference the clinical evidence found: list PubMed article titles, evidence categories (supportive/neutral/contradictory), and relevance scores. Include a structured literature summary table rather than leaving the clinical evidence section empty.
- If safety data exists (`safety_cache/` files), reference MAUDE event counts and failure mode categories. Use event rates as supporting evidence for bench-testing-only justification: "Post-market surveillance data from MAUDE shows {N} events over {period}, with the most common failure mode being {mode}. This low adverse event rate supports the adequacy of bench testing."
- If `review.json` indicates predicates were cleared without clinical data, cite this as precedent: "Predicate {K-number} was cleared without clinical data, establishing precedent for a bench-testing pathway."

**Clinical Study Design Framework**: When clinical data is needed, provide study design guidance from `references/clinical-study-framework.md`:
- Decision tree for whether clinical data is needed
- Study type recommendation (pivotal, feasibility, literature-based, retrospective)
- Sample size guidance (reference `/fda:calc sample-size` for calculations)
- Common clinical endpoints for the device type
- FDA clinical guidance references

### 14. cover-letter

Generates Section 1 of the eSTAR: Cover Letter. **This is a MANDATORY RTA section — every 510(k) must include it.**

**Required data**: product code, predicate list from review.json, device name from query.json or device_profile.json
**Enriched by**: openFDA classification (for CDRH division/OHT), import_data.json (for applicant info)
**Fallback**: If import_data.json is absent (peer-mode projects), use `[TODO: Company-specific — ...]` for applicant name, address, contact. Still generate the full letter structure.

**Output structure**: See `references/draft-templates.md` Section 01. Formal letter addressed to appropriate CDRH division. Auto-populate:
- Division name from review panel (e.g., CV → Division of Cardiovascular Devices)
- Device trade name: from query.json `device_name` or `[TODO: Company-specific — Trade Name]`
- Product code: from query.json
- Predicate device(s): from review.json accepted predicates with K-numbers
- List of enclosed eSTAR sections: reference all drafted sections
- Submission type: Traditional 510(k) (default unless otherwise specified)
- Applicant: from import_data.json or `[TODO: Company-specific — Applicant Name]`

### 15. truthful-accuracy

Generates Section 4 of the eSTAR: Truthful and Accuracy Statement. **This is a MANDATORY RTA section — every 510(k) must include it.**

**Required data**: None — this is a standard template per 21 CFR 807.87(l)
**Enriched by**: applicant_name from import_data.json or device_profile.json
**Fallback**: If no applicant name available, use `[TODO: Company-specific — Authorized Representative]`

**Output**: Standard certification text. Auto-populate applicant name if available. Include signature block with Name, Title, Date, Signature lines.

### 16. financial-certification

Generates Section 5 of the eSTAR: Financial Certification/Disclosure.

**Required data**: None (template-only)
**Output**: Template referencing FDA Forms 3454/3455 and 21 CFR Part 54. Indicates which form applies based on whether clinical data is submitted.

### 17. doc

Generates a Declaration of Conformity (DoC) for applicable standards.

**Required data**: test_plan.md or test results indicating which standards were tested against
**Enriched by**: guidance_cache, standards-tracking.md, `/fda:standards` data

**Output structure**: One consolidated DoC or individual DoCs per standard:

```markdown
## Declaration of Conformity

### Manufacturer Information
- Company: [TODO: Company-specific — Legal entity name]
- Address: [TODO: Company-specific — Full address]
- Authorized Representative: [TODO: Company-specific — Name and title]

### Device Identification
- Device Trade Name: {trade_name or [TODO]}
- Product Code: {product_code}
- Device Class: {class}
- Regulation Number: 21 CFR {regulation}

### Standards Declared

| Standard | Edition | Title | Conformity Status |
|----------|---------|-------|-------------------|
| {standard} | {edition} | {title} | [TODO: Full/Partial/N-A] |

{Auto-populate from project's test_plan.md or guidance requirements:}
{For each standard in the test plan, add a row}

### Declaration Statement
[TODO: Company-specific — We, {company_name}, declare under sole responsibility that the device identified above conforms to the standards listed. This declaration is based on testing and evaluation conducted by [accredited lab name].]

### Signature
Name: ___________________________________
Title: ___________________________________
Date: ___________________________________
Signature: ________________________________
```

Auto-populate standards list from (in priority order):
1. **`standards_lookup.json`** (if available from `/fda:standards`) — use ALL standards from this file, not just a subset. This file contains the complete list of applicable standards for the product code. Populate every standard from this file into the DoC table.
2. Project's `test_plan.md` (if available) — extract all ISO/IEC/ASTM standards cited as supplementary
3. `references/standards-tracking.md` — verify current editions for any standard listed
4. `/fda:standards` output (if available) — FDA recognized consensus standards

**CRITICAL**: If `standards_lookup.json` lists 14 standards, the DoC table MUST have at least 14 rows — not a truncated subset of 7. Every applicable standard from the lookup should appear in the declaration.

**Separating Formal Declarations from Referenced Standards**: Standards fall into two categories:
- **Formal conformity declarations** — Standards from `standards_lookup.json` that the device is tested against. These go in the main "Standards Declared" table with a conformity status column.
- **Referenced process standards** — Standards cited in specialized sections (e.g., ISO 17665 for sterilization validation, ISO 11737 for bioburden, AAMI TIR30/ST91 for reprocessing) that relate to manufacturing/validation processes rather than direct device conformity. These should appear in a separate "Referenced Standards (Informational)" subsection below the formal declaration table, clearly marked as not requiring a formal DoC entry.

This prevents the consistency check (Check 13) from flagging process standards as misaligned, and avoids over-declaring conformity to standards that apply to the validation process rather than the device itself.

### 18. human-factors

Generates Section 17 of the eSTAR: Human Factors / Usability Engineering.

**Required data**: device description, intended use
**Enriched by**: MAUDE data (use error patterns), `references/human-factors-framework.md`

**Applicability auto-detection**: Scan device description for keywords that trigger HFE requirements:
- "user interface", "display", "touchscreen", "control panel"
- "home use", "patient-operated", "self-administered"
- "injection", "infusion", "inhaler", "autoinjector"
- "alarm", "alert", "notification"
- "software", "app", "mobile", "connected"

If no keywords found, note: "HFE may not be required for this device. Document rationale per IEC 62366-1:2015."

**Output structure**: See `references/human-factors-framework.md` eSTAR Section 17 template.

```markdown
## Human Factors / Usability Engineering

### 17.1 Use Environment
[TODO: Company-specific — Describe the intended use environment(s):
- Clinical setting (hospital, clinic, physician office)
- Home environment (if applicable)
- Environmental conditions (lighting, noise, temperature)
- Other use environments]

### 17.2 User Profile
[TODO: Company-specific — Describe intended users:
- Healthcare professionals (type, training level)
- Patients/caregivers (if home use)
- Other users (biomedical technicians, etc.)
- Physical/cognitive requirements]

### 17.3 Critical Tasks
[TODO: Company-specific — List all critical tasks:
- Tasks where use error could cause serious harm
- Tasks requiring high accuracy or precision
- Tasks performed under stress or time pressure]

### 17.4 Use-Related Risk Analysis Summary
[TODO: Company-specific — Summarize use-related risk analysis:
- Identified use errors and hazardous situations
- Risk controls implemented (design, labeling, training)
- Residual risks and mitigations]

### 17.5 Formative Study Summary
[TODO: Company-specific — Summarize formative studies:
- Study type (cognitive walkthrough, heuristic evaluation, simulated use)
- Number of participants
- Key findings and design changes made]

### 17.6 Summative (Validation) Study Summary
[TODO: Company-specific — Summarize validation study:
- Study design and protocol
- Number of participants per user group (minimum 15 per group recommended by FDA)
- Critical task results (success/failure)
- Use errors and close calls observed
- Conclusion: device can be used safely and effectively]
```

Cross-reference:
- `/fda:safety` MAUDE data to identify use error patterns for the product code
- `references/human-factors-framework.md` for IEC 62366-1:2015 process and FDA guidance references

### 19. form-3881

Generates FDA Form 3881 (Indications for Use) — **a MANDATORY RTA section required for ALL 510(k) submissions**. Its absence causes immediate RTA rejection.

**Required data**: intended_use from device_profile.json, import_data.json, or `--intended-use`
**Enriched by**: openFDA classification, review.json (predicate IFU for reference)

**Output structure**:
```markdown
## FDA Form 3881 — Indications for Use

⚠ DRAFT — AI-generated regulatory document. Review with regulatory affairs team before submission.
Generated: {date} | Project: {name} | Plugin: fda-predicate-assistant v5.22.0

---

### Device Information

- **510(k) Number:** [TODO: Assigned after submission — leave blank for initial submission]
- **Device Name:** {trade_name from device_profile.json, else [TODO: Device Trade Name]}
- **Indications for Use:**

{IFU text from device_profile.json intended_use field, import_data.json, or --intended-use argument}

{If no IFU text available: [TODO: Company-specific — Enter the complete Indications for Use statement. This must match exactly across all submission documents (labeling, 510(k) summary, SE discussion).]}

### Prescription Use and/or Over-The-Counter Use

- [ ] Prescription Use (Part 21 CFR 801 Subpart D)
- [ ] Over-The-Counter Use (Part 21 CFR 801 Subpart C)

{Auto-detect from UDI data if available: if is_rx=true → check Prescription; if is_otc=true → check OTC}
{If neither available: [TODO: Check the appropriate box]}

{For combination products (Class U or drug-containing): If OTC, include note about OTC Drug Facts panel requirement}

### Classification

- **Product Code:** {product_code}
- **Device Class:** {device_class from openFDA}
- **Regulation Number:** {regulation_number or "Unclassified" for Class U}

### Predicate Device Reference

{For each accepted predicate from review.json:}
- **Predicate K-Number:** {K-number}
- **Predicate Device Name:** {device_name}
- **Predicate IFU:** {predicate IFU text if available from PDF extraction or openFDA}

{If predicate IFU available, add comparison note:}
> **IFU Consistency Note:** Compare the subject device IFU above with the predicate IFU. Any broadening of intended use beyond the predicate may trigger additional review. [Source: review.json, predicate PDF text]

### Certification

I certify that I am the {[TODO: Title]} of {[TODO: Company Legal Name]} and that the indications for use stated above are accurate and complete.

**Signature:** _________________________________ **Date:** ___________
**Typed Name:** [TODO: Authorized Representative Name]
```

**Data threading:**
- Pull IFU text from `device_profile.json` → `intended_use` field first
- Fall back to `import_data.json` → `indications_for_use` or `sections.ifu_text`
- Fall back to `--intended-use` CLI argument
- If all empty: generate [TODO] placeholder with guidance
- Cross-reference predicate IFU from `review.json` accepted predicates and PDF text to provide side-by-side comparison
- Rx/OTC determination from UDI data query (see labeling section UDI Integration)

### 20. reprocessing

Generates reprocessing validation documentation for reusable medical devices.

**Required data**: device description indicating reusable device
**Enriched by**: guidance_cache, AAMI TIR30/ST91 requirements

**Applicability auto-detection**: Scan device description for keywords: "reusable", "reprocessing", "reprocessed", "autoclave", "multi-use", "non-disposable", "cleaning validation", "endoscope", "instrument tray".

**Output structure**:
```markdown
## Reprocessing Validation

⚠ DRAFT — AI-generated regulatory prose. Review with regulatory affairs team before submission.
Generated: {date} | Project: {name} | Plugin: fda-predicate-assistant v5.22.0

### Reprocessing Overview

The {device_name or [TODO: Device Name]} is a reusable medical device intended for multiple uses following validated reprocessing procedures.

[Source: device_profile.json device_description]

### Cleaning Validation (per AAMI TIR30)

#### Point-of-Use Pre-Cleaning
[TODO: Company-specific — Describe point-of-use pre-cleaning instructions (e.g., flush lumens, wipe external surfaces)]

#### Manual Cleaning Protocol
| Step | Action | Agent/Solution | Time | Temperature |
|------|--------|---------------|------|-------------|
| 1 | Pre-soak | [TODO: enzymatic detergent] | [TODO: min] | [TODO: °C] |
| 2 | Manual brush | [TODO: brush type/size] | [TODO: min] | N/A |
| 3 | Rinse | [TODO: water quality] | [TODO: min] | [TODO: °C] |
| 4 | Dry | [TODO: method] | [TODO: min] | N/A |

#### Automated Cleaning (if applicable)
[TODO: Company-specific — Describe automated washer-disinfector cycle parameters]

#### Cleaning Validation Test Results
| Test | Method | Soil Challenge | Acceptance Criteria | Result |
|------|--------|---------------|---------------------|--------|
| Protein residual | [TODO: method] | Worst-case organic load | < 6.4 μg/cm² | [TODO] |
| Hemoglobin residual | [TODO: method] | Worst-case blood soil | < 2.2 μg/cm² | [TODO] |
| Endotoxin | [TODO: method] | Post-cleaning | < 20 EU/device | [TODO] |
| TOC | [TODO: method] | Post-cleaning | [TODO: limit] | [TODO] |

### Disinfection/Sterilization Between Uses

[TODO: Company-specific — Specify the terminal reprocessing step:]
- High-level disinfection (for semi-critical devices): [TODO: agent, concentration, time, temperature]
- Steam sterilization (for critical devices): [TODO: cycle parameters per ISO 17665]

### Lifecycle/Durability Testing

| Test | Standard | Cycles | Acceptance Criteria | Result |
|------|----------|--------|---------------------|--------|
| Repeated reprocessing | [TODO] | [TODO: N cycles] | No degradation of function | [TODO] |
| Material compatibility | [TODO] | [TODO: N cycles] | No cracking, discoloration, corrosion | [TODO] |
| Functional performance | [TODO] | After max cycles | Meets original performance specs | [TODO] |

**Maximum number of reprocessing cycles:** [TODO: specify — typically 100-1000 depending on device]

### Reprocessing IFU Validation

[TODO: Company-specific — Confirm that the reprocessing instructions provided in the IFU have been validated through simulated-use testing with worst-case soil conditions]

### Referenced Standards (Informational)

| Standard | Title | Applicability |
|----------|-------|---------------|
| AAMI TIR30 | A compendium of processes, materials, test methods, and acceptance criteria for cleaning reusable medical devices | Cleaning validation |
| AAMI ST91 | Flexible and semi-rigid endoscope processing in health care facilities | Endoscope reprocessing (if applicable) |
| ANSI/AAMI ST77 | Containment devices for reusable medical device sterilization | Instrument trays (if applicable) |
| ISO 17664 | Processing of health care products — Information to be provided by the medical device manufacturer | Reprocessing IFU |
```

### 21. combination-product

Generates combination product documentation for devices with drug or biological components.

**Required data**: device description indicating drug/biological component
**Enriched by**: 21 CFR Part 3/4, OCP guidance

**Applicability auto-detection**: Scan for keywords: "drug", "pharmaceutical", "active ingredient", "drug-eluting", "antimicrobial agent", "antibiotic", "medicated", "drug-device", "combination product", "biologic", "drug component", "active pharmaceutical", "OTC drug", "Drug Facts".

**Output structure**:
```markdown
## Combination Product Documentation

⚠ DRAFT — AI-generated regulatory prose. Review with regulatory affairs team before submission.
Generated: {date} | Project: {name} | Plugin: fda-predicate-assistant v5.22.0

### Primary Mode of Action (PMOA) Determination

Per 21 CFR Part 3, the PMOA of this combination product is determined to be:

- [ ] **Device** — The primary mode of action is achieved through the device component
- [ ] **Drug** — The primary mode of action is achieved through the drug/pharmaceutical component
- [ ] **Biologic** — The primary mode of action is achieved through the biological component

[TODO: Company-specific — Provide PMOA determination rationale. Reference FDA's "Classification of Products as Drugs and Devices & Additional Product Classification Issues" guidance]

{If PMOA is device: "This product is regulated as a device with a drug component under 21 CFR Part 4. The submission is to CDRH with CDER consultation."}
{If PMOA is drug: "This product is regulated as a drug with a device component. The primary submission is to CDER, not CDRH."}

### 21 CFR Part 3/4 Compliance

| Requirement | Status | Reference |
|-------------|--------|-----------|
| PMOA determination | [TODO: Complete/Pending] | 21 CFR 3.2(m) |
| Lead center assignment | [TODO: CDRH/CDER/CBER] | 21 CFR 3.4 |
| Intercenter consultation | [TODO: Required/N/A] | 21 CFR 4.4 |
| cGMP compliance (device) | [TODO: 21 CFR 820] | 21 CFR 4.4(b) |
| cGMP compliance (drug) | [TODO: 21 CFR 211] | 21 CFR 4.4(b) |

### Drug Component Characterization

| Property | Value |
|----------|-------|
| Drug name (generic) | [TODO: e.g., silver sulfadiazine, chlorhexidine] |
| Drug name (trade) | [TODO: if applicable] |
| Drug class | [TODO: e.g., antimicrobial, analgesic, hemostatic] |
| Concentration/Dose | [TODO: e.g., 1% w/w, 0.5 mg/cm²] |
| Route of delivery | [TODO: topical, transdermal, implanted] |
| Release kinetics | [TODO: immediate, sustained, controlled — include elution profile if available] |
| Pharmacological testing | [TODO: describe drug characterization testing] |

### Drug-Device Interaction Testing

[TODO: Company-specific — Describe testing of drug-device interactions:]
- Drug stability within the device matrix
- Drug release profile/elution kinetics
- Effect of sterilization on drug potency
- Shelf life impact on drug component

### OTC Drug Facts Panel (if OTC)

{If device_class == "U" or is_otc == true or OTC keywords detected:}

```
Drug Facts
Active ingredient(s)                          Purpose
[TODO: ingredient] [TODO: concentration] .... [TODO: purpose]

Uses
[TODO: uses/indications]

Warnings
[TODO: required warnings per 21 CFR 201.66]

Directions
[TODO: directions for use]

Other information
[TODO: storage conditions, etc.]

Inactive ingredients
[TODO: list inactive ingredients]
```

{If not OTC: "OTC Drug Facts panel not applicable — device is prescription use only."}

### Regulatory Pathway Considerations

[TODO: Company-specific — Address the following:]
- Is a pre-submission (Q-Sub) meeting with both CDRH and CDER/CBER recommended?
- Has a Request for Designation (RFD) been filed if PMOA is ambiguous?
- Are there predicate combination products with established review precedent?
```

## Revision Workflow (--revise)

When `--revise` is specified, the command regenerates a section draft while preserving user edits:

### Step 1: Load Existing Draft

Read the existing `draft_{section}.md` file from the project directory.

If no existing draft exists, output: `"No existing draft found for '{section}'. Use /fda:draft {section} --project NAME without --revise to generate an initial draft."`

### Step 2: Identify User Edits

Scan the existing draft for user-edited content. User edits are identified by:

1. **Lines that do NOT contain** `[Source:`, `[TODO:`, `[CITATION NEEDED]`, or `v5.` version tags — these are likely user-written
2. **Lines between `<!-- USER EDIT START -->` and `<!-- USER EDIT END -->`** markers — explicitly marked by user
3. **Content that doesn't match the original template structure** — paragraphs that differ from template patterns

### Step 3: Regenerate AI Content

Regenerate the section using current project data (which may have changed since the original draft). During regeneration:

- **Preserve** all content between `<!-- USER EDIT START -->` and `<!-- USER EDIT END -->` markers exactly as-is
- **Preserve** any paragraph that doesn't match the original AI template patterns (likely user-written)
- **Update** `[Source: ...]` tagged content with latest project data
- **Update** `[TODO: ...]` items only if project data now has the information to fill them
- **Update** the generation timestamp and version tag
- **Preserve** `[CITATION NEEDED]` items that the user has not yet resolved

### Step 4: Output Revision

Write the revised draft and report:

```
Revision complete: {section}
Output: {file_path}

Changes:
  Updated: {N} AI-generated paragraphs (re-sourced from current data)
  Preserved: {N} user-edited paragraphs
  Resolved: {N} [TODO:] items (now filled from project data)
  Remaining: {N} [TODO:] items still pending

Next: Review the updated draft and verify preserved content is intact.
```

### User Edit Markers

Users can protect their edits by wrapping content with markers:

```markdown
<!-- USER EDIT START -->
This paragraph was written by the regulatory team and should
be preserved exactly during revision.
<!-- USER EDIT END -->
```

Content between these markers is **never** overwritten by `--revise`.

---

## N/A Section Handling (--na)

When `--na` is specified, mark the section as "Not Applicable" instead of generating content:

### Write N/A Template

Write `draft_{section}.md` with:

```markdown
## {Section Title}

**Status: Not Applicable**

### Rationale

[TODO: Company-specific — Provide rationale for why this section does not apply to your device. Common rationale examples below.]

{Auto-generated rationale suggestions based on section type:}

{For sterilization:} "The subject device is supplied non-sterile and is not intended to be sterilized by the user or at the point of care."
{For biocompatibility:} "The subject device has no direct or indirect patient contact. Per ISO 10993-1, biocompatibility evaluation is not required for devices with no body contact."
{For software:} "The subject device does not contain software, firmware, or programmable components."
{For emc-electrical:} "The subject device is not electrically powered and contains no electronic components."
{For clinical:} "Clinical data is not required. The subject device is substantially equivalent to the predicate based on bench performance testing alone, consistent with FDA clearance precedent for product code {code}."
{For shelf-life:} "The subject device does not degrade over time and has no expiration-dated components."
{For human-factors:} "Per IEC 62366-1:2015 and FDA guidance, a formal human factors evaluation is not required for this device based on its simplicity of use and low risk of use error. [TODO: Verify this determination with your HFE team.]"

### Reference

This section was marked as N/A using `/fda:draft {section} --project {name} --na` on {date}.
Per FDA eSTAR guidance, sections that do not apply should include a brief explanation of why they are not applicable rather than being left blank.
```

Report:
```
Section marked as N/A: {section}
Output: {file_path}

The N/A rationale template has been generated. Fill in the [TODO:] with your
specific justification. FDA reviewers expect a brief explanation for each
section marked as not applicable.
```

---

## Generation Rules

1. **Regulatory tone**: Formal, factual, third-person. Use standard FDA regulatory language patterns.
2. **Citations required**: Every factual claim must reference its data source in `[Source: ...]` format.
3. **DRAFT disclaimer**: Every generated section starts with:
   ```
   ⚠ DRAFT — AI-generated regulatory prose. Review with regulatory affairs team before submission.
   Generated: {date} | Project: {name} | Plugin: fda-predicate-assistant v5.22.0
   ```
4. **Unverified claims**: Anything that cannot be substantiated from project data gets `[CITATION NEEDED]` or `[TODO: Company-specific — verify]`.
5. **No fabrication**: Never invent test results, clinical data, or device specifications. If data isn't available, say so.
6. **Standard references**: Use proper CFR/ISO/ASTM citation format (e.g., "per 21 CFR 807.87(f)", "ISO 10993-1:2025").

## Device-Type Adaptive Section Selection

When running a multi-section pipeline (not a single section), auto-detect the device type and recommend critical sections:

**SaMD / Software-Only Devices** (detected by: `review_panel` = "PA" or "RA", or `classification_device_name` contains "software", "SaMD", "algorithm", "digital", "AI/ML", or product_code in [QKQ, NJS, OIR, PEI, QAS, QDQ, QMT, QFM], or device_profile has no `materials` and no `sterilization_method`):
- **CRITICAL**: `software` section MUST be drafted — this is the primary technical evidence for SaMD
- **CRITICAL**: `performance-summary` should focus on algorithm validation, not bench testing
- Mark N/A with rationale: `sterilization`, `biocompatibility`, `emc-electrical`, `shelf-life`
- `labeling` should include cybersecurity labeling if Section 524B applies
- **Auto-queue rule**: Automatically include `software` in the section queue. If `software` would otherwise be omitted, add it with a note: `"Auto-queued: software section required for SaMD device (product code {code})"`

**Wireless/Connected Devices — Software + EMC Auto-Trigger** (detected by: product_code in [DPS, QMT] OR `classification_device_name` or device description contains "wireless", "Bluetooth", "WiFi", "connected", "IoT", "cellular", "RF transmit", "app-based", "mobile", "telemetry", "remote monitoring"):
- **CRITICAL**: `software` section MUST be drafted — wireless devices have firmware/software requiring IEC 62304 documentation and Section 524B cybersecurity
- **CRITICAL**: `emc-electrical` section MUST be drafted — wireless devices require EMC testing per IEC 60601-1-2 and FCC compliance
- Auto-queue BOTH `software` AND `emc-electrical` sections

**Powered/Electronic Devices — EMC Auto-Trigger** (detected by: device description contains "powered", "electronic", "electrical", "battery", "AC power", "generator", "motor", "laser", "ultrasound", "RF energy" OR review_panel in [CV, RA, SU] with electronic indicators):
- **CRITICAL**: `emc-electrical` section MUST be drafted for any powered device
- Auto-queue `emc-electrical`

**Combination Products** (detected by: `classification_device_name` contains "drug", or device_profile `device_description` mentions drug/active ingredient/pharmaceutical/medicated/drug-eluting/antimicrobial agent/OTC drug, or product_code associated with combination products):
- Flag 21 CFR Part 3/4 PMOA determination as a required consideration
- `biocompatibility` must address drug component toxicity/pharmacology
- `labeling` must address drug labeling requirements (OTC Drug Facts if applicable)
- **Auto-queue rule**: Automatically include `combination-product` section. Add note: `"Auto-queued: combination-product section required for device with drug/biological component"`

**Sterile Devices — Shelf Life Auto-Trigger** (detected by: `sterilization_method` is not empty in device_profile/se_comparison/import_data, OR shelf life mentioned in se_comparison.md, OR `calculations/shelf_life_*.json` exists, OR keywords "sterile", "shelf life", "expiration", "expiry" in device description):
- **Auto-queue rule**: Automatically include `shelf-life` section without explicit request. Add note: `"Auto-queued: shelf-life section required for sterile device with expiration dating"`

**Reusable Devices — Reprocessing Auto-Trigger** (detected by: keywords "reusable", "reprocessing", "reprocessed", "autoclave", "multi-use", "non-disposable", "endoscope", "instrument tray", "surgical instrument" in device description, OR sterilization_method is "steam" for facility-sterilized devices, OR classification_device_name contains "instrument" and review_panel in [SU, GU, OR]):
- **Auto-queue rule**: Automatically include `reprocessing` section. Add note: `"Auto-queued: reprocessing section required for reusable medical device"`

**Surgical/Procedural Devices — Human Factors Auto-Trigger** (detected by: `review_panel` in [SU, GU, OR, HO, AN] AND device is NOT a passive-implant-only device — i.e., device has an active user interface, requires procedural steps, or involves patient interaction beyond simple implantation; OR device description contains "home use", "OTC", "lay user", "patient-operated", "over-the-counter"):
- **Auto-queue rule**: Automatically include `human-factors` section unless the device is a passive implant with no user interface (e.g., a bone screw, plate, or mesh with no electronic/software component). Add note: `"Auto-queued: human-factors section recommended for surgical device (review panel {panel})"`
- Passive implant exemption: if `classification_device_name` contains ONLY implant-related terms (screw, plate, rod, cage, mesh, stent, valve, graft) and NO active terms (powered, electronic, software, display, console, generator), skip the auto-queue
- Home use / OTC devices ALWAYS get human-factors (no exemption) — lay users require IEC 62366-1 evaluation

**Unclassified Devices (Class U)** (detected by: `device_class` = "U" or regulation_number is empty):
- Note missing regulation number throughout — do not fabricate one
- Pre-check should not penalize for missing regulation (it doesn't exist)
- DoC should note "Unclassified" rather than leave regulation blank

## Output

Write the draft to `$PROJECTS_DIR/$PROJECT_NAME/draft_{section}.md`.

Report:
```
Section draft generated: {section}
Output: {file_path}

Data sources used:
  {list of files and APIs consulted}

Completeness:
  Auto-populated: {N} paragraphs
  [TODO:] items: {N} (require company-specific data)
  [CITATION NEEDED]: {N} (need verification)

Next steps:
  1. Review draft for accuracy
  2. Fill in [TODO:] items with company-specific data
  3. Verify [CITATION NEEDED] items
  4. Have regulatory team review for compliance

> **Disclaimer:** This draft is AI-generated from public FDA data.
> Verify independently. Not regulatory advice.
```

## Audit Logging

After each section is drafted, log the generation decision using `fda_audit_logger.py`:

### Log section drafted

```bash
python3 "$FDA_PLUGIN_ROOT/scripts/fda_audit_logger.py" \
  --project "$PROJECT_NAME" \
  --command draft \
  --action section_drafted \
  --subject "$SECTION_NAME" \
  --decision "drafted" \
  --mode interactive \
  --decision-type auto \
  --rationale "Section $SECTION_NAME drafted using data from: $SOURCES_USED" \
  --data-sources "$SOURCES_USED" \
  --files-written "$PROJECTS_DIR/$PROJECT_NAME/drafts/draft_$SECTION_NAME.md"
```

### Log content decisions (when multiple sources conflict)

```bash
python3 "$FDA_PLUGIN_ROOT/scripts/fda_audit_logger.py" \
  --project "$PROJECT_NAME" \
  --command draft \
  --action content_decision \
  --subject "$SECTION_NAME" \
  --decision "$CHOSEN_SOURCE" \
  --mode interactive \
  --decision-type auto \
  --rationale "Used $CHOSEN_SOURCE over $ALTERNATIVE_SOURCE because: $REASON" \
  --alternatives "[\"$CHOSEN_SOURCE\",\"$ALTERNATIVE_SOURCE\"]" \
  --exclusions "{\"$ALTERNATIVE_SOURCE\":\"$REASON\"}"
```

## Error Handling

- **Unknown section name**: "Unknown section '{name}'. Available: device-description, se-discussion, performance-summary, testing-rationale, predicate-justification, 510k-summary, labeling, sterilization, shelf-life, biocompatibility, software, emc-electrical, clinical, cover-letter, truthful-accuracy, financial-certification, doc, human-factors, form-3881, reprocessing, combination-product"
- **No project data**: "Project '{name}' has no pipeline data. Run /fda:pipeline first to generate data for draft generation."
- **Insufficient data for section**: Generate what's possible, mark rest as [TODO]. Note which commands to run for more complete drafts.
