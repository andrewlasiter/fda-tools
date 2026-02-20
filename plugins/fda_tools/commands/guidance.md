---
description: Look up FDA guidance documents for a device type — extract requirements, map to testing needs, and compare against predicate precedent
allowed-tools: Bash, Read, Glob, Grep, Write, WebFetch, WebSearch
argument-hint: "<product-code> [--regulation NUMBER] [--save] [--infer]"
---

# FDA Guidance Document Lookup

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
        if k.startswith('fda-tools@'):
            for e in v:
                p = e.get('installPath', '')
                if os.path.isdir(p):
                    print(p); exit()
print('')
")
echo "FDA_PLUGIN_ROOT=$FDA_PLUGIN_ROOT"
```

If `$FDA_PLUGIN_ROOT` is empty, report an error: "Could not locate the FDA Predicate Assistant plugin installation. Make sure the plugin is installed and enabled."

## Check Available Data

Before making API calls, check what data already exists for this project:

```bash
python3 $FDA_PLUGIN_ROOT/scripts/fda_data_store.py --project "$PROJECT_NAME" --show-manifest 2>/dev/null
```

If the manifest shows cached classification data for the same product code (not expired), **use the cached summary** instead of re-querying. This prevents redundant API calls and ensures consistency across commands.

---

You are looking up FDA guidance documents applicable to a device type, extracting requirements, and mapping them to testing needs.

**KEY PRINCIPLE: Provide actionable guidance mappings, not just links.** Extract specific requirements and map them to tests the user needs to plan. Use the centralized tables in `references/guidance-lookup.md` for cross-cutting guidance logic and standards mapping.

## Parse Arguments

From `$ARGUMENTS`, extract:

- **Product code** (required) — 3-letter FDA product code (e.g., KGN, DXY, QAS)
- `--regulation NUMBER` — Override regulation number lookup (e.g., `878.4018`)
- `--device-description TEXT` — User's device description (triggers additional cross-cutting guidance)
- `--project NAME` — Associate with a project folder for caching
- `--save` — Cache guidance data locally for reuse
- `--depth quick|standard|deep` — Level of analysis (default: standard)
- `--infer` — Auto-detect product code from project data instead of requiring explicit input

If no product code provided:
- If `--infer` AND `--project NAME` specified:
  1. Check `$PROJECTS_DIR/$PROJECT_NAME/query.json` for `product_codes` field → use first code
  2. Check `$PROJECTS_DIR/$PROJECT_NAME/output.csv` → find most-common product code in data
  3. Check `~/fda-510k-data/guidance_cache/` for directory names matching product codes
  4. If inference succeeds: log "Inferred product code: {CODE} from {source}"
  5. If inference fails: **ERROR** (not prompt): "Could not infer product code. Provide --product-code CODE or run /fda:extract first."
- If `--infer` without `--project`: check if exactly 1 project exists in projects_dir and use it
- If no `--infer` and no product code: ask the user for it. If they're unsure, help them find it using foiaclass.txt or the openFDA classification API.

## Step 1: Get Device Classification

### Cache Fallback

If the openFDA API is unreachable or returns an error, check for cached classification data:

```bash
python3 << 'PYEOF'
import json, os, re

# Determine project dir
settings_path = os.path.expanduser('~/.claude/fda-tools.local.md')
projects_dir = os.path.expanduser('~/fda-510k-data/projects')
if os.path.exists(settings_path):
    with open(settings_path) as f:
        m = re.search(r'projects_dir:\s*(.+)', f.read())
        if m:
            projects_dir = os.path.expanduser(m.group(1).strip())

# Check for cached guidance_index.json
product_code = "PRODUCTCODE"  # Replace
project_name = "PROJECT_NAME"  # Replace or empty

# Try project-specific cache first
if project_name:
    index_path = os.path.join(projects_dir, project_name, 'guidance_cache', 'guidance_index.json')
    if os.path.exists(index_path):
        with open(index_path) as f:
            index = json.load(f)
        print(f"CACHED:true")
        print(f"DEVICE_NAME:{index.get('device_name', 'N/A')}")
        print(f"DEVICE_CLASS:{index.get('device_class', 'N/A')}")
        print(f"REGULATION:{index.get('regulation_number', 'N/A')}")
        print(f"CACHED_AT:{index.get('cached_at', 'N/A')}")
        exit(0)

# Check all projects for this product code
import glob
for idx_path in glob.glob(os.path.join(projects_dir, '*/guidance_cache/guidance_index.json')):
    with open(idx_path) as f:
        idx = json.load(f)
    if idx.get('product_code') == product_code:
        print(f"CACHED:true")
        print(f"CACHE_PATH:{idx_path}")
        print(f"DEVICE_NAME:{idx.get('device_name', 'N/A')}")
        print(f"DEVICE_CLASS:{idx.get('device_class', 'N/A')}")
        print(f"REGULATION:{idx.get('regulation_number', 'N/A')}")
        exit(0)

print("CACHED:false")
PYEOF
```

If no cache found, **fall back to skill reference data**:

1. Read the `references/guidance-lookup.md` skill reference file (via `$FDA_PLUGIN_ROOT/skills/fda-510k-knowledge/references/guidance-lookup.md`)
2. Match the product code family/panel to generic cross-cutting guidance recommendations from the reference tables
3. Generate a "Reference-Based Guidance Summary" with the following banner at the top:

```
⚠ REFERENCE-BASED GUIDANCE — Generated from bundled reference data, NOT from current FDA guidance documents.
Verify all recommendations against current FDA guidance at fda.gov before use in any submission.
Last reference update: [date from reference file header or "unknown"]
```

4. Include all applicable cross-cutting guidance from the reference tables (biocompatibility, sterilization, etc.) based on device class and known characteristics
5. Mark all entries as `[Reference-based]` instead of having specific guidance document URLs

This ensures the cache fallback always produces useful output, even without a prior `--save` cache. Only fail with an error if the reference file itself is missing (plugin installation issue).

### Online: Query openFDA Classification API

Query the classification endpoint via the project data store (caches results for cross-command reuse):

```bash
python3 "$FDA_PLUGIN_ROOT/scripts/fda_data_store.py" \
  --project "$PROJECT_NAME" \
  --query classification \
  --product-code "$PRODUCT_CODE"
```

The output includes DEVICE_NAME, DEVICE_CLASS, REGULATION, PANEL, DEFINITION, IMPLANT_FLAG, LIFE_SUSTAIN fields. If the API is unavailable, falls back to flat files automatically.

If `--regulation NUMBER` is provided, use that instead of the API result.

Store the classification data — you'll need `device_name`, `device_class`, `regulation_number`, `review_panel`, `implant_flag`, and `life_sustain_support_flag` for subsequent steps.

## Step 1.5: Query AccessGUDID for Device Characteristics

**Skip if the product code is not found or if using cache fallback.**

Query AccessGUDID for authoritative device characteristics (sterilization method, single-use status, MRI safety, latex). These API flags take priority over keyword guessing in Step 3.

```bash
python3 << 'PYEOF'
import urllib.request, json

product_code = "PRODUCTCODE"  # Replace with actual product code from Step 1

url = f"https://accessgudid.nlm.nih.gov/api/v3/devices/lookup.json?product_code={product_code}"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (FDA-Plugin/5.21.0)"})
try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
        if data.get("gudid"):
            device = data["gudid"].get("device", {})
            sterilization = device.get("sterilization", {})
            print(f"GUDID_STERILE:{sterilization.get('is_sterile', False)}")
            print(f"GUDID_STERILE_PRIOR_USE:{sterilization.get('is_sterilization_prior_use', False)}")
            methods = sterilization.get("sterilization_methods", [])
            for m in methods:
                print(f"STERILIZATION_METHOD:{m}")
            print(f"GUDID_SINGLE_USE:{device.get('is_single_use', 'N/A')}")
            print(f"GUDID_MRI_SAFETY:{device.get('mri_safety', 'N/A')}")
            print(f"GUDID_LATEX:{device.get('is_labeled_as_nrl', 'N/A')}")
            print(f"GUDID_RX:{device.get('is_rx', 'N/A')}")
        else:
            print("GUDID_FOUND:false")
except Exception as e:
    print(f"GUDID_ERROR:{e}")
PYEOF
```

Store the GUDID results — `gudid_is_sterile`, `gudid_sterilization_methods`, `gudid_single_use`, `gudid_mri_safety`, and `gudid_latex_nrl` will be used by the 3-tier trigger logic in Step 3. If GUDID query fails, these flags default to `None` and Tier 2 keyword matching handles them instead.

## Step 2: Search for Device-Specific Guidance

**Skip for `--depth quick` or if using cache fallback.**

### 2A: Bundled Guidance Index Lookup (Primary)

First, check the bundled curated guidance index for known device-specific guidance:

```
Read the reference file: $FDA_PLUGIN_ROOT/skills/fda-510k-knowledge/references/fda-guidance-index.md
```

1. Search Section 9 ("Regulation Number → Guidance Quick Lookup") for the device's regulation number
2. Search Section 5 ("Device-Category Specific Guidance") for the regulation number prefix (e.g., `870.*` → Cardiovascular)
3. Check Section 1 ("Cross-Cutting Guidance") for universally applicable documents
4. Check Section 8 ("Recently Finalized / Upcoming") for new guidance that may apply

If the index contains device-specific guidance for this regulation number, record those documents. If the index marks the device as "No" specific guidance, note that only cross-cutting guidance applies.

### 2B: Structured FDA Guidance Database Search (Online Enhancement)

For `--depth standard` or `--depth deep`, supplement the index with live web search:

```
WebFetch: url="https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfCFR/CFRSearch.cfm?fr={regulation_number}" prompt="Extract the device classification name, class, and any referenced special controls or guidance documents from this CFR section."
```

### 2C: WebSearch Fallback

If the index has no match AND structured search returns no results, fall back to WebSearch:

**Query 1** (always): Regulation-specific guidance
```
WebSearch: "{regulation_number}" guidance site:fda.gov/medical-devices
```

**Query 2** (always): Special controls guidance (for Class II)
```
WebSearch: "{device_name}" "special controls" OR "class II" guidance site:fda.gov
```

**Query 3** (standard/deep): Testing guidance
```
WebSearch: "{device_name}" "510(k)" guidance testing requirements site:fda.gov
```

**Query 4** (deep only): Recent draft guidance
```
WebSearch: "{device_name}" "draft guidance" site:fda.gov 2024 OR 2025 OR 2026
```

### Process search results

For each guidance document found:
1. Record the title, URL, status (final/draft), and publication year
2. Categorize: device-specific, special controls, or general
3. Note if it supersedes or replaces another guidance

## Step 3: Identify Cross-Cutting Guidance

Apply the trigger rules from `references/guidance-lookup.md`. Use the classification data from Step 1 and the user's `--device-description` (if provided) to determine which cross-cutting guidances apply.

```python
import re

# ── Helper: word-boundary keyword matching with negation awareness ──
def kw_match(desc, keywords):
    """Word-boundary matching that avoids false positives from substrings.
    Returns True if any keyword matches as a whole word AND is NOT preceded
    by a negation phrase within 20 characters."""
    for kw in keywords:
        pattern = r'\b' + re.escape(kw) + r'\b'
        match = re.search(pattern, desc, re.IGNORECASE)
        if match:
            prefix = desc[max(0, match.start()-20):match.start()].lower()
            if not any(neg in prefix for neg in ['not ', 'non-', 'non ', 'no ', 'without ', "doesn't ", "does not "]):
                return True
    return False

# ── Build combined description from user input + API definition field ──
desc = " ".join(filter(None, [
    (device_description or "").lower(),
    (api_definition or "").lower()    # from Step 1 classification API
]))

# ══════════════════════════════════════════════════════════════════════
#  TIER 1 — API-Authoritative Flags (always checked first)
# ══════════════════════════════════════════════════════════════════════
triggers = []

# Always applicable
triggers.append(("Biocompatibility", "Use of ISO 10993-1", "all_devices"))
triggers.append(("510(k) SE Determination", "The 510(k) Program: Evaluating Substantial Equivalence", "all_510k"))

# Class-based
if device_class == "2":
    triggers.append(("Special Controls", f"Special controls for {regulation_number}", "class_ii"))
if device_class == "3":
    triggers.append(("PMA-Level Scrutiny", "Clinical data likely required for Class III device", "class_iii"))

# API implant flag (from openFDA classification)
if implant_flag == "Y":
    triggers.append(("Implantable", "ISO 10993 extended + fatigue + MRI safety", "api_implant"))
    triggers.append(("MRI Safety", "Assessment of MRI Effects", "api_implant"))

# API life-sustaining flag
if life_sustain_flag == "Y":
    triggers.append(("Life-Sustaining", "Enhanced clinical review for life-sustaining device", "api_life_sustain"))

# AccessGUDID sterilization flags (from Step 1.5)
if gudid_is_sterile == True:
    triggers.append(("Sterilization", "Submission and Review of Sterility Information", "gudid_sterile"))
    triggers.append(("Shelf Life", "Shelf Life of Medical Devices", "gudid_sterile"))
    # Map specific sterilization method to correct standard
    for method in gudid_sterilization_methods:
        method_lower = method.lower() if method else ""
        if "ethylene oxide" in method_lower or "eo" in method_lower:
            triggers.append(("Sterilization-EO", "Ethylene Oxide Sterilization — ISO 11135", "gudid_method"))
        elif "radiation" in method_lower or "gamma" in method_lower or "e-beam" in method_lower:
            triggers.append(("Sterilization-Radiation", "Radiation Sterilization — ISO 11137", "gudid_method"))
        elif "steam" in method_lower or "autoclave" in method_lower:
            triggers.append(("Sterilization-Steam", "Steam Sterilization — ISO 17665", "gudid_method"))

# AccessGUDID single-use flag
if gudid_single_use == True:
    # NOTE: Single-use devices are not intended for reprocessing by the manufacturer,
    # but third-party reprocessors (per 21 CFR 820.3(p)) may reprocess them. If the
    # user's device is a reprocessed single-use device, reprocessing guidance STILL applies.
    # Log a note rather than silently suppressing.
    triggers.append(("Single-Use Note", "Labeled single-use; reprocessing guidance suppressed unless third-party reprocessing applies", "gudid_single_use_note"))
elif gudid_single_use == False:
    triggers.append(("Reprocessing", "Reprocessing Medical Devices in Health Care Settings", "gudid_reusable"))

# AccessGUDID MRI safety flag (even for non-implants)
if gudid_mri_safety and gudid_mri_safety != "N/A":
    triggers.append(("MRI Safety", "Assessment of MRI Effects", "gudid_mri"))

# AccessGUDID latex flag
if gudid_latex_nrl == True:
    triggers.append(("Latex", "Latex labeling + ISO 10993 extended panel", "gudid_latex"))

# IVD review panels
IVD_PANELS = ["clinical chemistry", "microbiology", "hematology", "immunology", "toxicology", "pathology"]
if any(panel in (review_panel or "").lower() for panel in IVD_PANELS):
    triggers.append(("IVD", "IVD-specific guidance (CLSI standards)", "api_ivd"))

# ══════════════════════════════════════════════════════════════════════
#  TIER 2 — Enhanced Keyword Matching (word-boundary, negation-aware)
# ══════════════════════════════════════════════════════════════════════
# Only fires if the corresponding TIER 1 flag did NOT already trigger.

# Sterilization (if not already triggered by GUDID)
if not any(t[0].startswith("Sterilization") for t in triggers):
    if kw_match(desc, ["sterile", "sterilized", "sterilization", "aseptic", "terminally sterilized",
                        "gamma irradiated", "gamma sterilized", "eo sterilized", "ethylene oxide",
                        "e-beam sterilized", "radiation sterilized", "steam sterilized"]):
        triggers.append(("Sterilization", "Submission and Review of Sterility Information", "kw_sterile"))
        triggers.append(("Shelf Life", "Shelf Life of Medical Devices", "kw_sterile"))

# Software (precise terms — avoids "digital thermometer" false positive)
if kw_match(desc, ["software", "algorithm", "mobile app", "software app", "firmware", "samd",
                    "software as a medical device", "digital health", "software function",
                    "machine learning algorithm", "cloud-based software"]):
    triggers.append(("Software", "Content of Premarket Submissions for Device Software Functions", "kw_software"))

# AI/ML (precise terms — "ai" alone would match "drain", "air", etc.)
if kw_match(desc, ["artificial intelligence", "ai-enabled", "ai-based", "ai/ml",
                    "machine learning", "deep learning", "neural network",
                    "computer-aided detection", "computer-aided diagnosis", "cadx", "cade"]):
    triggers.append(("AI/ML", "AI and ML in Software as a Medical Device", "kw_aiml"))

# Wireless/Connected/USB (precise terms — "connected" alone too broad; "rf" alone matches "rf wound")
# NOTE: USB connectivity triggers cybersecurity per cybersecurity-framework.md but NOT EMC/wireless
if kw_match(desc, ["wireless", "bluetooth", "wifi", "wi-fi", "network-connected", "cloud-connected",
                    "internet of things", "iot device", "rf communication", "rf wireless",
                    "radio frequency", "cellular", "zigbee", "lora", "near-field communication", "nfc"]):
    # Disambiguation: "radio frequency" false-positives for therapeutic RF ablation devices (CV, NE).
    # If ablation-related terms are present, this is a therapeutic RF device, not a wireless device.
    rf_ablation = kw_match(desc, ["ablation", "rf ablation", "radiofrequency ablation", "catheter ablation"])
    triggers.append(("Cybersecurity", "Cybersecurity in Medical Devices", "kw_wireless"))
    if not rf_ablation:
        triggers.append(("EMC/Wireless", "Radio Frequency Wireless Technology in Medical Devices", "kw_wireless"))

# USB connectivity — triggers cybersecurity only (not EMC/wireless)
if kw_match(desc, ["usb data", "usb communication", "usb port", "usb connectivity",
                    "usb interface", "usb connection"]):
    if not any(t[0] == "Cybersecurity" for t in triggers):
        triggers.append(("Cybersecurity", "Cybersecurity in Medical Devices", "kw_usb"))

# Combination products (precise terms — "drug" alone matches "drug-free")
if kw_match(desc, ["combination product", "drug-device", "drug-eluting", "drug-coated",
                    "biologic-device", "antimicrobial agent", "drug delivery device",
                    "drug-impregnated", "bioresorbable drug"]):
    triggers.append(("Combination Product", "Classification of Products as Drugs and Devices", "kw_combination"))

# Implantable (if not already triggered by API flag)
if not any(t[0] == "Implantable" for t in triggers):
    if kw_match(desc, ["implant", "implantable", "permanent implant", "indwelling",
                        "prosthesis", "prosthetic", "endoprosthesis"]):
        triggers.append(("Implantable", "ISO 10993 extended + fatigue + MRI safety", "kw_implant"))
        triggers.append(("MRI Safety", "Assessment of MRI Effects", "kw_implant"))

# Reusable (if not already triggered by GUDID)
if not any(t[0] == "Reprocessing" for t in triggers):
    if kw_match(desc, ["reusable", "reprocessing", "reprocessed", "multi-use",
                        "cleaning validation", "disinfection"]):
        # Suppression: capsule endoscopy and ingestible devices are single-use by nature.
        # The "endoscop" substring can false-positive from device descriptions that mention
        # "capsule endoscopy" as a procedure context, not as a reprocessable instrument.
        capsule_endo_suppressed = (
            kw_match(desc, ["capsule endoscop", "ingestible"]) and gudid_single_use == True
        )
        if not capsule_endo_suppressed:
            triggers.append(("Reprocessing", "Reprocessing Medical Devices in Health Care Settings", "kw_reusable"))

# ── New categories (v5.22.0) ──

# 3D Printing / Additive Manufacturing
if kw_match(desc, ["3d print", "3d-printed", "3d printed",
                    "additive manufactur", "additively manufactured",
                    "selective laser sintering", "selective laser melting",
                    "electron beam melting", "fused deposition", "binder jetting"]):
    triggers.append(("3D Printing", "Technical Considerations for Additive Manufactured Medical Devices", "kw_3dprint"))

# Animal-Derived Materials
if kw_match(desc, ["collagen", "gelatin", "bovine", "porcine", "animal-derived",
                    "animal tissue", "equine", "ovine", "decellularized",
                    "xenograft", "biologic matrix"]):
    triggers.append(("Animal-Derived", "BSE/TSE Guidance for Animal-Derived Materials", "kw_animal"))

# Home Use
if kw_match(desc, ["home use", "over-the-counter", "otc device", "patient self-test",
                    "lay user", "home monitoring", "self-administered",
                    "consumer use", "non-professional use"]):
    triggers.append(("Home Use", "Design Considerations for Devices Intended for Home Use", "kw_home"))

# Pediatric
if kw_match(desc, ["pediatric", "neonatal", "infant", "children", "child",
                    "neonate", "newborn", "adolescent"]):
    triggers.append(("Pediatric", "Premarket Assessment of Pediatric Medical Devices", "kw_pediatric"))

# Latex (if not already triggered by GUDID)
if not any(t[0] == "Latex" for t in triggers):
    if kw_match(desc, ["latex", "natural rubber", "natural rubber latex"]):
        triggers.append(("Latex", "Latex labeling + ISO 10993 extended panel", "kw_latex"))

# Electrical Safety (non-wireless powered devices)
if kw_match(desc, ["battery-powered", "battery powered", "ac mains", "rechargeable",
                    "electrically powered", "mains-powered", "line-powered",
                    "lithium battery", "power supply", "electrical stimulation"]):
    triggers.append(("Electrical Safety", "IEC 60601-1 Electrical Safety Guidance", "kw_electrical"))

# ── Specialty keyword categories (v5.22.0) ──
# These enhance guidance specificity. Tier 3 reg family mapping provides the safety net.

# Cardiovascular (points to Section 5.1 in guidance index)
if kw_match(desc, ["stent", "coronary stent", "drug-eluting stent", "bare-metal stent",
                    "catheter", "guiding catheter", "guidewire", "balloon catheter",
                    "oxygenator", "cardiopulmonary bypass", "heart-lung machine",
                    "ablation catheter", "cardiac ablation",
                    "heart valve", "transcatheter valve", "prosthetic valve",
                    "vascular graft", "endograft", "stent graft",
                    "pacemaker", "defibrillator", "icd", "cardiac resynchronization",
                    "cardiac lead", "pacing lead",
                    "pta balloon", "angioplasty",
                    "septal occluder", "laa closure",
                    "ecmo", "extracorporeal membrane oxygenation",
                    "hemocompatibility", "perfusion"]):
    triggers.append(("Cardiovascular", "Cardiovascular device guidance (Section 5.1)", "kw_cv"))

# Orthopedic (points to Section 5.2 in guidance index)
if kw_match(desc, ["arthroplasty", "joint replacement", "hip replacement", "knee replacement",
                    "pedicle screw", "spinal screw", "spinal rod",
                    "spinal fusion", "interbody fusion", "vertebral body",
                    "bone cement", "bone void filler", "bone graft",
                    "fracture fixation", "bone plate", "bone screw", "intramedullary nail",
                    "disc replacement", "artificial disc",
                    "wear testing", "fatigue testing",
                    "orthopedic implant", "orthopedic",
                    "total hip", "total knee", "total shoulder",
                    "acetabular", "femoral stem", "tibial tray"]):
    triggers.append(("Orthopedic", "Orthopedic device guidance (Section 5.2)", "kw_or"))

# Gastroenterology / Urology (points to Section 5.14 in guidance index)
if kw_match(desc, ["endoscope", "colonoscope", "gastroscope", "duodenoscope",
                    "lithotripter", "lithotripsy", "eswl", "shock wave",
                    "dialysis", "hemodialysis", "peritoneal dialysis", "dialyzer",
                    "foley catheter", "urinary catheter", "urethral catheter",
                    "ureteral stent", "biliary stent",
                    "ureteroscope", "cystoscope", "nephroscope",
                    "stone basket", "stone retrieval",
                    "capsule endoscopy", "video capsule"]):
    triggers.append(("Gastroenterology/Urology", "GU device guidance (Section 5.14)", "kw_gu"))

# Dental (points to Section 5.5 in guidance index)
if kw_match(desc, ["dental implant", "endosseous implant", "dental abutment",
                    "dental ceramic", "dental porcelain", "dental restoration",
                    "orthodontic", "orthodontic bracket", "orthodontic wire",
                    "dental composite", "dental resin",
                    "intraoral scanner", "dental cad/cam", "dental milling",
                    "dental handpiece", "dental drill",
                    "dental bone graft", "alveolar bone",
                    "dental laser",
                    "dental cement", "dental luting",
                    "dentifrice", "toothbrush",
                    "dental impression", "dental alginate",
                    "root canal", "endodontic",
                    "dental curing light"]):
    triggers.append(("Dental", "Dental device guidance (Section 5.5)", "kw_de"))

# ENT / Ear, Nose, Throat (points to Section 5.13 in guidance index)
if kw_match(desc, ["hearing aid", "otc hearing aid", "air-conduction hearing",
                    "cochlear implant", "cochlear",
                    "tympanostomy", "ear tube", "myringotomy",
                    "otoscope", "audiometer", "tympanometer",
                    "laryngoscope", "sinuscope", "nasopharyngoscope",
                    "sinus", "nasal",
                    "sleep apnea", "oral appliance", "mandibular advancement",
                    "bone-anchored hearing", "baha",
                    "middle ear implant"]):
    triggers.append(("ENT", "ENT device guidance (Section 5.13)", "kw_en"))

# Anesthesia / Respiratory (points to Section 5.8 in guidance index)
if kw_match(desc, ["anesthesia", "anaesthesia", "anesthesia machine", "anesthesia workstation",
                    "ventilator", "mechanical ventilation", "positive pressure ventilation",
                    "cpap", "bipap", "continuous positive airway pressure",
                    "capnograph", "capnometry", "end-tidal co2",
                    "vaporizer", "anesthetic vaporizer",
                    "breathing circuit", "breathing system",
                    "laryngeal mask", "supraglottic airway",
                    "endotracheal tube", "tracheal tube",
                    "gas monitor", "anesthetic gas",
                    "humidifier", "heated humidifier",
                    "oxygen concentrator", "oxygen therapy"]):
    triggers.append(("Anesthesia/Respiratory", "Anesthesia/respiratory device guidance (Section 5.8)", "kw_an"))

# Neurological (points to Section 5.11 in guidance index)
if kw_match(desc, ["neurostimulator", "deep brain stimulation", "dbs",
                    "eeg", "electroencephalograph",
                    "tens", "transcutaneous electrical nerve",
                    "tms", "transcranial magnetic stimulation",
                    "vagus nerve stimulator", "vns",
                    "seizure detection", "seizure monitor",
                    "intracranial", "cranial",
                    "brain-computer interface", "bci",
                    "spinal cord stimulator", "scs",
                    "cerebrospinal fluid shunt", "csf shunt",
                    "digital therapeutics", "prescription digital therapeutic"]):
    triggers.append(("Neurological", "Neurological device guidance (Section 5.11)", "kw_ne"))

# Ophthalmic (points to Section 5.6 in guidance index)
if kw_match(desc, ["intraocular lens", "iol", "phakic iol",
                    "contact lens", "soft contact lens", "rgp contact lens",
                    "oct", "optical coherence tomography",
                    "fundus camera", "fundus imaging",
                    "glaucoma", "migs", "minimally invasive glaucoma",
                    "phacoemulsification", "phaco",
                    "ophthalmic viscosurgical", "ovd", "viscoelastic",
                    "keratoprosthesis",
                    "excimer laser", "corneal",
                    "retinal", "vitrectomy",
                    "slit lamp", "perimeter", "visual field",
                    "tonometer", "intraocular pressure"]):
    triggers.append(("Ophthalmic", "Ophthalmic device guidance (Section 5.6)", "kw_op"))

# General/Plastic Surgery (points to Section 5.12 in guidance index)
if kw_match(desc, ["electrosurgical", "electrocautery", "radiofrequency surgery",
                    "surgical stapler", "stapling device",
                    "suture", "surgical suture", "absorbable suture",
                    "hemostatic", "hemostatic agent", "fibrin sealant",
                    "tissue adhesive", "tissue sealant", "cyanoacrylate",
                    "surgical mesh", "hernia mesh",
                    "sterilant", "high-level disinfectant", "chemical sterilant",
                    "surgical robot", "robotic surgery", "robotic-assisted",
                    "laparoscopic", "trocar",
                    "surgical gown", "surgical drape", "surgical mask"]):
    triggers.append(("Surgery", "Surgical device guidance (Section 5.12)", "kw_su"))

# Physical Medicine (points to Section 5.16 in guidance index)
if kw_match(desc, ["wheelchair", "powered wheelchair", "motorized wheelchair",
                    "exoskeleton", "powered exoskeleton",
                    "prosthetic limb", "prosthetic leg", "prosthetic arm",
                    "muscle stimulator", "nmes", "neuromuscular electrical",
                    "continuous passive motion", "cpm",
                    "rehabilitation device", "gait trainer",
                    "orthotic", "orthosis"]):
    triggers.append(("Physical Medicine", "Physical medicine device guidance (Section 5.16)", "kw_pm"))

# General Hospital (points to Section 5.9 in guidance index)
if kw_match(desc, ["infusion pump", "syringe pump", "iv pump",
                    "patient monitor", "physiological monitor", "vital signs monitor",
                    "hospital bed", "medical bed",
                    "examination glove", "surgical glove", "medical glove",
                    "compression device", "sequential compression", "pneumatic compression",
                    "thermometer", "clinical thermometer"]):
    triggers.append(("General Hospital", "General hospital device guidance (Section 5.9)", "kw_ho"))

# Obstetrics / Gynecology (points to Section 5.15 in guidance index)
if kw_match(desc, ["fetal monitor", "fetal heart rate", "cardiotocograph",
                    "uterine", "endometrial",
                    "iud", "intrauterine device", "intrauterine contraceptive",
                    "hysteroscope", "colposcope",
                    "morcellator", "morcellation",
                    "cervical dilator",
                    "pelvic mesh", "transvaginal mesh",
                    "breast implant",
                    "obstetric", "gynecologic"]):
    triggers.append(("Obstetrics/Gynecology", "OB/GYN device guidance (Section 5.15)", "kw_ob"))

# Expanded IVD keywords (enhance existing IVD trigger at Tier 1)
# Note: The basic IVD trigger already fires via Tier 1 (review panel check).
# These keywords help when the device description mentions IVD-specific terms
# but the API panel data hasn't been fetched yet.
if not any(t[0] == "IVD" for t in triggers):
    if kw_match(desc, ["blood gas", "blood gas analyzer",
                        "point-of-care", "poct", "point of care testing",
                        "hba1c", "hemoglobin a1c", "glycated hemoglobin",
                        "cholesterol", "lipid panel",
                        "coagulation", "prothrombin", "inr", "aptt",
                        "next-generation sequencing", "ngs", "genomic",
                        "flow cytometry", "flow cytometer",
                        "drugs of abuse", "doa", "drug screening",
                        "immunoassay", "elisa", "lateral flow",
                        "molecular diagnostic", "pcr", "nucleic acid",
                        "clinical analyzer", "chemistry analyzer",
                        "hematology analyzer", "cell counter",
                        "urinalysis", "urine test strip",
                        "blood bank", "crossmatch", "blood typing"]):
        triggers.append(("IVD", "IVD-specific guidance (CLSI standards)", "kw_ivd_expanded"))

# Radiology / Imaging (points to Section 5.10 in guidance index)
if kw_match(desc, ["x-ray", "x ray", "radiograph", "radiographic",
                    "computed tomography", "ct scan", "ct scanner",
                    "mri", "magnetic resonance", "magnetic resonance imaging",
                    "ultrasound", "ultrasonic", "sonography", "transducer",
                    "mammograph", "mammography", "digital mammography",
                    "fluoroscop", "fluoroscopy",
                    "linac", "linear accelerator", "radiation therapy",
                    "dicom", "pacs",
                    "cade", "cadx", "computer-aided detection",
                    "image display", "medical display",
                    "dose management", "dose monitoring"]):
    triggers.append(("Radiology/Imaging", "Imaging device guidance (Section 5.10)", "kw_ra"))

# ══════════════════════════════════════════════════════════════════════
#  TIER 3 — Classification Heuristics (safety net)
# ══════════════════════════════════════════════════════════════════════
# Regulation number family mapping — catches devices missed by Tiers 1-2
reg_prefix = (regulation_number or "")[:3]
REG_FAMILY_TRIGGERS = {
    "862": "Clinical chemistry (possible IVD)",
    "864": "Hematology/pathology (possible IVD)",
    "866": "Immunology/microbiology (possible IVD)",
    "868": "Anesthesia/respiratory devices (21 CFR 868)",
    "870": "Cardiovascular guidance (21 CFR 870)",
    "872": "Dental devices (21 CFR 872)",
    "874": "Ear, nose, throat devices (21 CFR 874)",
    "876": "Gastroenterology/urology devices (21 CFR 876)",
    "878": "General/plastic surgery guidance (21 CFR 878)",
    "880": "General hospital devices (21 CFR 880)",
    "884": "Obstetrics/gynecology devices (21 CFR 884)",
    "888": "Orthopedic guidance (21 CFR 888)",
    "892": "Radiology guidance (21 CFR 892)",
}
if reg_prefix in REG_FAMILY_TRIGGERS:
    triggers.append(("Regulation Family", REG_FAMILY_TRIGGERS[reg_prefix], "tier3_reg_family"))

# If Class II and NO specific guidance found after Tiers 1-2, flag for web search
if device_class == "2" and len([t for t in triggers if t[2] not in ["all_devices", "all_510k", "class_ii", "tier3_reg_family"]]) == 0:
    triggers.append(("Web Search Recommended", "No characteristic-specific triggers found — consider WebSearch for applicable guidance", "tier3_fallback"))
```

Only include cross-cutting guidance where the trigger condition is met. Do NOT list every possible cross-cutting guidance for every device.

## Step 4: Extract Requirements (Standard/Deep Depth)

### For `--depth standard`

For the most relevant device-specific guidance found in Step 2, summarize the key requirements based on the search result content and your regulatory knowledge:

- Testing categories required
- Specific standards referenced
- Special submission requirements
- Any clinical data expectations

### For `--depth deep`

Use WebFetch to retrieve the actual guidance document page and extract detailed requirements:

```
WebFetch: url="{guidance_url}" prompt="Extract all specific testing requirements, performance criteria, recommended standards (ISO, ASTM, IEC), and submission content expectations from this FDA guidance document. Organize by testing category."
```

For each extracted requirement, map to a testing category using the mapping table in `references/guidance-lookup.md`.

## Step 5: Map to Standards and Testing Needs

### Build Requirements Matrix

Combine device-specific guidance requirements, cross-cutting guidance requirements, and recognized consensus standards into a structured matrix:

```
REQUIREMENTS MATRIX
────────────────────────────────────────

| Category | Requirement | Source | Standard | Priority |
|----------|-------------|--------|----------|----------|
| Biocompatibility | ISO 10993 evaluation | Cross-cutting | ISO 10993-1, -5, -10 | Required |
| Sterilization | EO validation | Cross-cutting | ISO 11135 | Required |
| Performance | Fluid handling | Device-specific guidance | EN 13726 | Required |
| Performance | MVTR testing | Device-specific guidance | ASTM E96 | Required |
| Antimicrobial | Zone of inhibition | Device-specific guidance | AATCC 100 | If claimed |
| Shelf Life | Accelerated aging | Cross-cutting | ASTM F1980 | Required |
| Software | V&V documentation | Cross-cutting (if applicable) | IEC 62304 | If applicable |
```

### Standards List

List all applicable recognized consensus standards with their purpose:

```
APPLICABLE STANDARDS
────────────────────────────────────────

Required:
  • ISO 10993-1 — Biological evaluation framework
  • ISO 10993-5 — Cytotoxicity testing
  • ISO 10993-10 — Sensitization
  • ISO 10993-23 — Irritation
  • ISO 11135 — EO sterilization validation
  • ASTM F1980 — Accelerated aging
  • ISO 14971 — Risk management

Recommended (based on predicate precedent):
  • EN 13726 — Wound dressing test methods
  • ASTM D1777 — Thickness measurement
  • AATCC 100 — Antimicrobial assessment

If Applicable:
  • IEC 62304 — Software lifecycle (if device contains software)
  • IEC 60601-1 — Electrical safety (if powered)
```

## Step 6: Output

### Report format

Use the standard FDA Professional CLI format (see `references/output-formatting.md`):

```
  FDA Guidance Analysis
  {PRODUCT_CODE} — {DEVICE_NAME}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Generated: {date} | Class: {class} | 21 CFR {regulation} | v5.22.0

DEVICE CLASSIFICATION
────────────────────────────────────────

  Product Code: {CODE}
  Device Name: {name}
  Class: {class}
  Regulation: 21 CFR {regulation_number}
  Panel: {review_panel}

DEVICE-SPECIFIC GUIDANCE
────────────────────────────────────────

  [If found]:
  ✓ "{Guidance Title}" ({Year}, {Status})
    {URL}
    Key Requirements:
    - {requirement 1}
    - {requirement 2}
    - {requirement 3}

  [If not found]:
  ✗ No device-specific guidance found for regulation {regulation_number}
    → Submission should rely on predicate precedent and general guidance

CROSS-CUTTING GUIDANCE
────────────────────────────────────────

  - Biocompatibility: "Use of ISO 10993-1" (2023, Final)
    → ISO 10993-5, -10 required; -11 if prolonged contact
  - Sterilization: "Sterility Information in 510(k) Submissions" (2016, Final)
    → Validate per ISO 11135 (EO) or ISO 11137 (radiation)

REQUIREMENTS MATRIX
────────────────────────────────────────

  [Structured pipe table from Step 5]

APPLICABLE STANDARDS
────────────────────────────────────────

  [Standards list from Step 5]

NOTES
────────────────────────────────────────

  - {Any special considerations for this device type}
  - {Any recent draft guidance that may affect requirements}

NEXT STEPS
────────────────────────────────────────

  1. Plan testing to requirements — `/fda:test-plan {CODE}`
  2. Research predicate testing precedent — `/fda:research {CODE}`
  3. Build traceability matrix — `/fda:traceability --project NAME`

────────────────────────────────────────
  This report is AI-generated from public FDA data.
  Verify independently. Not regulatory advice.
────────────────────────────────────────
```

## Step 7: Save to Cache (if `--save`)

If `--save` is specified, write guidance data to the project's guidance cache:

```bash
python3 << 'PYEOF'
import json, os, re
from datetime import datetime

# Determine cache directory
settings_path = os.path.expanduser('~/.claude/fda-tools.local.md')
projects_dir = os.path.expanduser('~/fda-510k-data/projects')
if os.path.exists(settings_path):
    with open(settings_path) as f:
        m = re.search(r'projects_dir:\s*(.+)', f.read())
        if m:
            projects_dir = os.path.expanduser(m.group(1).strip())

project_name = "PROJECT_NAME"  # Replace
product_code = "PRODUCTCODE"    # Replace

cache_dir = os.path.join(projects_dir, project_name, 'guidance_cache', product_code)
os.makedirs(os.path.join(cache_dir, 'device_specific'), exist_ok=True)
os.makedirs(os.path.join(cache_dir, 'cross_cutting'), exist_ok=True)

print(f"Cache directory created: {cache_dir}")
PYEOF
```

Write `guidance_index.json` with the structure defined in `references/guidance-lookup.md`.

Write individual guidance content files (`.md`) for each guidance document that was fetched.

Write `requirements_matrix.json` with the structured requirements data.

Write `standards_list.json` with the applicable standards.

Report to the user:
```
Guidance data cached to: ~/fda-510k-data/projects/{PROJECT_NAME}/guidance_cache/
Cached data will be used automatically on subsequent runs.
```

If no `--project` was specified, ask the user if they want to save to a specific project or to a global cache at `~/fda-510k-data/guidance_cache/{PRODUCT_CODE}/`.

## Audit Logging

After guidance matching is complete, log each match and exclusion using `fda_audit_logger.py`:

### Log each matched guidance

```bash
python3 "$FDA_PLUGIN_ROOT/scripts/fda_audit_logger.py" \
  --project "$PROJECT_NAME" \
  --command guidance \
  --action guidance_matched \
  --subject "$GUIDANCE_TITLE" \
  --decision "matched" \
  --mode interactive \
  --decision-type auto \
  --rationale "Matched via $TRIGGER_TIER: $TRIGGER_REASON" \
  --data-sources "openFDA classification,fda-guidance-index.md,AccessGUDID" \
  --metadata "{\"trigger_tier\":\"$TIER\",\"trigger_source\":\"$SOURCE\",\"guidance_status\":\"$STATUS\"}"
```

### Log excluded guidance (where relevant)

For guidance documents that were evaluated but excluded (e.g., sterilization guidance for non-sterile device):

```bash
python3 "$FDA_PLUGIN_ROOT/scripts/fda_audit_logger.py" \
  --project "$PROJECT_NAME" \
  --command guidance \
  --action guidance_excluded \
  --subject "$GUIDANCE_TITLE" \
  --decision "excluded" \
  --mode interactive \
  --decision-type auto \
  --rationale "Not applicable: $REASON (e.g., device is not sterile per GUDID, not software-based)"
```

## Error Handling

- **Product code not found**: "Product code '{CODE}' not found in FDA classification database. Check the code and try again, or use `--regulation NUMBER` to specify the regulation directly."
- **No guidance found**: "No device-specific guidance found for this product code. Cross-cutting guidance still applies — see the requirements matrix above."
- **WebSearch/WebFetch fails**: Fall back to known guidance from `references/guidance-lookup.md` cross-cutting table. Note: "Web search unavailable — guidance analysis based on device characteristics and known cross-cutting requirements."
- **API unavailable**: Use flat files for classification. Note which data was API-derived vs. flat-file-derived.
