---
description: Generate FDA Substantial Equivalence comparison tables for 510(k) submissions — device-type specific rows, multi-predicate support, auto-populated from FDA data
allowed-tools: Read, Glob, Grep, Bash, Write, WebFetch, WebSearch, AskUserQuestion
argument-hint: "--predicates K241335[,K234567] [--references K345678] [--product-code CODE] [--infer]"
---

# FDA Substantial Equivalence Comparison Table Generator

> **Important**: This command assists with FDA regulatory workflows but does not provide regulatory advice. Output should be reviewed by qualified regulatory professionals before being relied upon for submission decisions.

> For external API dependencies and connection status, see [CONNECTORS.md](../CONNECTORS.md).

Generate a structured SE comparison table per FDA 21 CFR 807.87(f) for inclusion in a 510(k) submission. The table compares the user's subject device against one or more predicate devices and optional reference devices.

**KEY PRINCIPLE: Auto-populate predicate and reference columns from FDA data.** Fetch and extract predicate/reference device information yourself — the user should only need to fill in their own device's details.

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

## Parse Arguments

From the arguments, extract:

- `--predicates K123456[,K234567,P170019]` (required) -- One or more predicate device numbers (K-numbers or P-numbers), comma-separated
- `--references K345678[,K456789,P200024]` (optional) -- Reference devices (not predicates, but cited for specific features). Supports both K-numbers and P-numbers.
- `--product-code CODE` (optional) -- 3-letter FDA product code. If omitted, detect from first predicate
- `--device-description TEXT` (optional) -- Brief description of the subject device
- `--intended-use TEXT` (optional) -- Subject device intended use / IFU
- `--output FILE` (optional) -- Write table to a file (markdown or CSV)
- `--depth quick|standard|deep` (optional, default: standard)
- `--infer` -- Auto-detect predicates from project data instead of requiring explicit input

**PMA Predicate Support (TICKET-003 Phase 1.5):** The `--predicates` and `--references` arguments now accept P-numbers (PMA approvals) in addition to K-numbers. When a P-number is detected, the command uses the unified predicate interface to retrieve PMA data from SSED sections and map it to SE table rows. Mixed K-number and P-number comparisons are fully supported.

If no `--predicates` provided:
- If `--infer` AND `--project NAME` specified, use this fallback chain (try each in order, stop at first success):
  1. Check `$PROJECTS_DIR/$PROJECT_NAME/review.json` for accepted predicates -- use top 3 by score
     - **Also check for `reference_devices` key** in review.json. If present, auto-populate the `--references` argument with those device numbers. This ensures reference devices declared via `/fda:propose` carry through to SE comparison.
  2. Check `$PROJECTS_DIR/$PROJECT_NAME/output.csv` -- find most-cited predicates (top 3 by citation count across all source documents)
  3. Check `$PROJECTS_DIR/$PROJECT_NAME/pdf_data.json` or extraction cache -- grep for any K-numbers or P-numbers found in SE sections
  4. If all three fail: **ERROR**: "Could not infer predicates from project data. No accepted predicates in review.json, no citations in output.csv, and no device numbers in extraction cache. Provide --predicates K123456 or --predicates P170019 explicitly."
  **NEVER fall back to asking the user when `--infer` is set.** The `--infer` flag means "figure it out from data or fail."
- If no `--infer` and no `--predicates` and NOT `--full-auto`: ask the user. If they're unsure, suggest running `/fda:research` first.
- If no `--infer` and no `--predicates` and `--full-auto`: **ERROR**: "In --full-auto mode, predicates must be provided via --predicates or inferred via --infer. Cannot prompt for predicates."

## Step 0.5: Classify Device Numbers (TICKET-003 Phase 1.5)

Before processing predicates, classify each device number to determine the data retrieval strategy:

```bash
python3 << 'PYEOF'
import sys, os, json
sys.path.insert(0, os.path.join(os.environ.get("FDA_PLUGIN_ROOT", ""), "scripts"))
from unified_predicate import UnifiedPredicateAnalyzer

analyzer = UnifiedPredicateAnalyzer()

# All predicate and reference device numbers
all_devices = os.environ.get("ALL_DEVICE_NUMBERS", "").split(",")
all_devices = [d.strip() for d in all_devices if d.strip()]

classified = analyzer.classify_device_list(all_devices)
k_numbers = classified.get("510k", [])
p_numbers = classified.get("pma", [])

print(f"CLASSIFIED_K:{','.join(k_numbers)}")
print(f"CLASSIFIED_P:{','.join(p_numbers)}")
print(f"TOTAL_DEVICES:{len(all_devices)}")
print(f"HAS_PMA:{'yes' if p_numbers else 'no'}")

# For PMA devices, retrieve SE-compatible data
for pma_num in p_numbers:
    se_data = analyzer.get_pma_se_table_data(pma_num)
    if "error" not in se_data:
        print(f"PMA_SE_DATA:{pma_num}|{json.dumps(se_data)}")
    else:
        print(f"PMA_SE_ERROR:{pma_num}|{se_data.get('error','unknown')}")
PYEOF
```

Use K-numbers with the standard 510(k) PDF fetch approach. Use P-numbers with the unified predicate PMA data (SSED sections mapped to SE table fields).

## Step 1: Identify Product Code & Select Template

### Detect product code
If `--product-code` not provided, look up the first predicate. For K-numbers, use the local flat file. For P-numbers, use the unified predicate interface:
```bash
# For K-numbers:
grep "KNUMBER" ~/fda-510k-data/extraction/pmn96cur.txt 2>/dev/null | head -1
```
Extract the product code field.

### Select device-type template

Based on product code, select the appropriate row template. The template determines which characteristics (rows) are relevant for this device type.

**CGM / Glucose Monitors** (SBA, QBJ, QLG, QDK, NBW, CGA, LFR, SAF):
Rows: Intended Use, Indications for Use, Measurement Principle, Measurand/Analyte, Sample Type, Reportable Range, Accuracy (MARD), Sensor Duration/Life, Calibration, Sensor Placement, Data Display/Communication, Wireless/Connectivity, AID Compatibility, Biocompatibility, Sterilization, Shelf Life, Software/Firmware, Electrical Safety, MRI Safety, Clinical Data

**Wound Dressings** (KGN, FRO, MGP):
Rows: Intended Use, Indications for Use, Dressing Type/Category, Materials/Composition, Layer Structure, Contact Layer, Adhesive Border, Sizes Available, Fluid Handling/Absorption, MVTR, Antimicrobial Agent (if applicable), Antimicrobial Testing, Biocompatibility, Sterilization, Shelf Life, Clinical Data

**Orthopedic — Joint Arthroplasty** (hip: HCE/HCF/HDO/HDP/HEA/HEB; knee: HFK/HFG; shoulder: HNS/HNT):
Rows: Intended Use, Indications for Use, Prosthesis Type/Configuration, Anatomical Site, Fixation Method (cemented/uncemented/hybrid), Materials (bearing surfaces, stem/shell alloy), Surface Treatment (porous coating, HA, 3D-printed), Fatigue Testing (ASTM F2068/ISO 7206 hip, ASTM F1800 knee), Wear Testing (ISO 14242 hip/ISO 14243 knee — cycles, wear rate, debris), Corrosion (ASTM F2129, F1875 taper), Material Characterization (ASTM F136/F1537/F648), MRI Safety (ASTM F2052/F2213/F2182/F2119), Biocompatibility (permanent implant — ISO 10993 extended battery), Sterilization, Shelf Life, Clinical Data

**Orthopedic — Spinal Devices** (MQP, MAX, NKB):
Rows: Intended Use, Indications for Use, Device Type (pedicle screw/interbody cage/disc replacement), Configuration, Materials, Fatigue Testing (ASTM F1717 constructs, ASTM F2077 IBF), Subsidence Testing, Radiolucency/Radiopacity, MRI Safety, Biocompatibility, Sterilization, Shelf Life, Clinical Data (fusion rate)

**Orthopedic — Fracture Fixation** (HRS, HRX, HOV):
Rows: Intended Use, Indications for Use, Device Type (plate/screw/nail/wire), Anatomical Site, Materials, Fatigue Testing (ASTM F382 plates, ASTM F543 screws), Corrosion Testing (ASTM F2129), MRI Safety, Biocompatibility, Sterilization, Shelf Life, Clinical Data

**Cardiovascular — Intravascular Stents** (DXY, NIQ):
Rows: Intended Use, Indications for Use, Stent Design (open/closed cell, self/balloon-expanding), Materials, Dimensions (diameter, length), Radial Strength/Recoil, Fatigue Testing (ASTM F2477 — ≥4×10^8 cycles), Corrosion (ASTM F2129), Coating (drug-eluting: drug, dose, elution kinetics), Hemocompatibility (ISO 10993-4), Biocompatibility, Delivery System, MRI Safety, Sterilization, Shelf Life, Clinical Data

**Cardiovascular — Cardiac Implantable Electronic Devices** (DTB, DXA, LWS):
Rows: Intended Use, Indications for Use, Device Type (pacemaker/ICD/CRT-D/CRT-P), Lead Configuration, Pulse Generator, Sensing/Pacing Parameters, Battery Technology/Longevity, EMC (IEC 60601-2-31/-2-4), MRI Safety (ISO/TS 10974), Software (IEC 62304 Class C), Cybersecurity, Biocompatibility, Sterilization, Shelf Life, Clinical Data

**Cardiovascular — Heart Valves** (DTK, MVB):
Rows: Intended Use, Indications for Use, Valve Type (mechanical/bioprosthetic/TAVR), Materials, Hemodynamic Performance (ISO 5840 — EOA, regurgitation), Durability Testing (≥200M cycles), Delivery System (if TAVR), Biocompatibility, Hemocompatibility (ISO 10993-4), MRI Safety, Sterilization, Shelf Life, Clinical Data

**Cardiovascular — General** (other CV product codes):
Rows: Intended Use, Indications for Use, Device Design, Materials, Contact Duration, Blood Contact, Hemodynamic Performance, Hemocompatibility (ISO 10993-4), Biocompatibility, Sterilization, Shelf Life, MRI Safety, Clinical Data

**Radiological — X-Ray Systems** (IYO, JAK, IYN):
Rows: Intended Use, Indications for Use, X-ray Generator Type, Tube Assembly (focal spot, HU rating), Detector Type (flat panel/CR/II+CCD), Image Matrix/Pixel Pitch, AEC, Dose Indices (DAP, entrance skin dose), 21 CFR 1020.30-31 Compliance, DICOM Conformance, Collimation/Beam Limitation, Pediatric Protocols, IEC 60601-2-54, Software, Electrical Safety

**Radiological — CT Scanners** (JAK):
Rows: Intended Use, Indications for Use, Detector Configuration (rows, slice thickness), Rotation Speed, CTDIvol/DLP at Reference Protocols, Spatial Resolution (MTF), Low-Contrast Detectability, Reconstruction Algorithms (FBP/iterative/DL), Scan Range/Coverage Speed, Dual-Energy Capability, ECG Gating, Pediatric Dose Protocols, 21 CFR 1020.33 Compliance, IEC 60601-2-44, NEMA XR 25/29, DICOM/RDSR, Software, Electrical Safety

**Radiological — MRI Systems** (IZL, LNH, LNI):
Rows: Intended Use, Indications for Use, Field Strength, Gradient Performance (amplitude, slew rate), RF Coil Configuration, Bore Size, SAR Limits/Monitoring, dB/dt Limits, Acoustic Noise Levels, Pulse Sequences, Imaging Speed (parallel imaging, compressed sensing), IEC 60601-2-33, DICOM, Software, Electrical Safety

**Radiological — Diagnostic Ultrasound** (IYO):
Rows: Intended Use, Indications for Use, Transducer Types (linear/curved/phased), Frequency Range, Imaging Modes (B-mode/M-mode/Doppler/3D/4D), MI/TI Display and Limits (ODS/IEC 62359), Image Quality (spatial/contrast resolution), Frame Rate, IEC 60601-2-37, DICOM, Software, Electrical Safety

**Radiological — AI/ML Software** (QAS, QIH, QMT):
Rows: Intended Use, Indications for Use, Algorithm Type (DNN/CNN/ensemble), Target Pathology/Body Region, Compatible Imaging Modalities, Training Dataset (size, sources, demographics), Standalone Performance (sensitivity, specificity, AUC), Reader Study Results, Processing Time/Latency, PCCP (if applicable), Software (IEC 62304), Cybersecurity (Section 524B)

**Surgical — Electrosurgical** (GEI, GEX):
Rows: Intended Use, Indications for Use, Device Type (monopolar/bipolar/vessel sealing), Output Modes, Output Power Range, Frequency, IEC 60601-2-2 Compliance, Thermal Spread, Neutral Electrode Monitoring, Software, Biocompatibility, Sterilization, Clinical Data

**Surgical — Staplers** (GAT, GBD):
Rows: Intended Use, Indications for Use, Staple Configuration, Staple Leg Length, Tissue Thickness Range, Firing Force, Staple Line Hemostasis, Human Factors (per reclassification), Labeling (per FDA stapler guidance), Biocompatibility, Sterilization, Shelf Life

**Surgical — Mesh** (ORC, OPK):
Rows: Intended Use, Indications for Use, Mesh Type (synthetic/biologic), Material/Composition, Pore Size, Weight (g/m²), Burst Strength, Tear Resistance, Suture Pull-Out Strength, Absorbable Component (if applicable), Biocompatibility (permanent implant), Labeling (per hernia mesh guidance 2024), Sterilization, Shelf Life, Clinical Data

**Neurological — Neurostimulators** (GWB, PFC, QBH):
Rows: Intended Use, Indications for Use, Stimulation Type (TMS/tDCS/TENS/DBS/VNS/SCS), Output Parameters (waveform, frequency, amplitude, pulse width), Maximum Output, Safety Cutoffs, IEC 60601-2-10 (if TENS/NMES), Electrode Configuration, Biocompatibility, Software (IEC 62304), MRI Safety (if implantable), Clinical Data (sham-controlled)

**Neurological — CSF Shunts** (LYA, KEB):
Rows: Intended Use, Indications for Use, Valve Type (fixed/programmable), Pressure-Flow Characterization, Opening/Closing Pressure, Programmability (if applicable — magnetic adjustment, MRI setting retention), Catheter Properties (tensile, kink resistance, radiopacity), Biocompatibility (permanent CNS implant), MRI Safety, Sterilization, Shelf Life

**Gastroenterology/Urology — Endoscopes** (FDS, FDT, FGB):
Rows: Intended Use, Indications for Use, Endoscope Type (gastroscope/colonoscope/duodenoscope), Imaging (resolution, FOV, depth of field), Illumination, Working Channel(s), IEC 60601-2-18 Compliance, Reprocessing Validation (AAMI ST91, AAMI TIR30), Biocompatibility, Electrical Safety, Software

**Obstetrics — Fetal Monitors** (HEL, HGM):
Rows: Intended Use, Indications for Use, Monitoring Type (external/internal), FHR Detection Accuracy, Alarm Sensitivity/Specificity, Signal Quality (maternal movement, obesity, multiple gestation), IEC 60601-2-37 (ultrasound output), Biocompatibility, Electrical Safety, Software, Clinical Data

**Obstetrics — Intrauterine Devices** (HBL, HIH):
Rows: Intended Use, Indications for Use, IUD Type (copper/hormonal/inert), Dimensions, Retention Mechanism, Radiopacity, Removal Force, Drug Release Kinetics (if hormonal — 21 CFR Part 4), Corrosion/Ion Release (if copper), Biocompatibility (permanent mucosal), Sterilization, Shelf Life, Clinical Data

**General Hospital — Infusion Pumps** (FRN, MEB, MEA):
Rows: Intended Use, Indications for Use, Pump Type (large volume/syringe/ambulatory/PCA), Flow Rate Range, Flow Rate Accuracy (IEC 60601-2-24 trumpet curve), Bolus Accuracy, Alarm System (IEC 60601-1-8), Air-in-Line Detection, Occlusion Detection, Free-Flow Protection, Software (Enhanced Documentation Level per TPLC), Cybersecurity (if networked), Human Factors (IEC 62366-1), Battery Backup, Electrical Safety, Biocompatibility

**Dental — Implants** (various 872.3xxx):
Rows: Intended Use, Indications for Use, Implant Type (endosseous/subperiosteal), Material, Surface Treatment (roughness, chemistry), Implant-Abutment Connection, Fatigue Testing (ISO 14801 — ≥5M cycles at 30°), Corrosion (ASTM F2129), Biocompatibility (ISO 7405 + ISO 10993), MRI Safety, Sterilization, Shelf Life, Clinical Data (≥2yr follow-up)

**Dental — Restorative Materials** (various 872.3xxx):
Rows: Intended Use, Indications for Use, Material Type (ceramic/composite/cement), Flexural Strength (ISO 6872 or ISO 4049), Color Stability, Wear Resistance, Water Sorption/Solubility (ISO 4049), Radiopacity, Biocompatibility (ISO 7405 + ISO 10993-5), Shelf Life

**ENT — Hearing Aids** (various 874.3xxx):
Rows: Intended Use, Indications for Use, Type (OTC/prescription), Style (BTE/ITE/CIC/RIC), Electroacoustic Performance (ANSI S3.22 — OSPL90, HFA-FOG, THD, equivalent input noise), Output Limits (111/117 dB SPL per 21 CFR 800.30), IEC 60601-2-66, Wireless/Bluetooth, Biocompatibility, Battery/Charging, Human Factors, Labeling (21 CFR 801.420-422), Self-Fitting Algorithm (if applicable)

**ENT — Sleep Apnea Oral Appliances** (QBE, QDM):
Rows: Intended Use, Indications for Use, Mandibular Advancement Range, Titratability, Biocompatibility (ISO 7405 + ISO 10993), Dental Side Effects, Efficacy (AHI/RDI reduction), Human Factors (home use), Clinical Data

**Anesthesia — Workstations/Ventilators** (BSZ, BTD, BZD):
Rows: Intended Use, Indications for Use, Device Type (anesthesia workstation/ventilator/CPAP/BiPAP), Ventilation Modes (VCV/PCV/PSV/SIMV), Tidal Volume/Pressure/Flow Accuracy, Agent Delivery Accuracy (if anesthesia), Alarm System (IEC 60601-1-8), Hypoxia Prevention, ISO 80601-2-13 (anesthesia) or ISO 80601-2-12 (critical care) or ISO 80601-2-70 (sleep), Connector Compliance (ISO 5356-1/ISO 80369-6), Battery Backup, Software (IEC 62304), Cybersecurity, Electrical Safety

**Anesthesia — Pulse Oximeters** (DQA, MUD):
Rows: Intended Use, Indications for Use, SpO2 Accuracy (70-100% range), Low Perfusion Performance, Motion Artifact Performance, Skin Pigmentation Testing, Sensor Type, Alarm System, ISO 80601-2-61, Electrical Safety, Software

**Ophthalmic — Intraocular Lenses** (HQL, HQF, HQH):
Rows: Intended Use, Indications for Use, IOL Type (monofocal/multifocal/toric/EDOF), Material (hydrophobic/hydrophilic acrylic, silicone), Optical Performance (ISO 11979-2 — MTF, spectral transmittance, power tolerance), Haptic Design (ISO 11979-3 — compression force, loop memory), Biocompatibility (ISO 11979-5 — uveal, LEC, PCO), Endotoxin Testing (≥0.2 EU/mL), Injector System Compatibility, Glistening Evaluation, Sterilization, Shelf Life, Clinical Data

**Ophthalmic — Contact Lenses** (LPL, MRC, MQI):
Rows: Intended Use, Indications for Use, Lens Type (daily wear/extended/ortho-k), Material, Dk/Dk(t) (ISO 18369-4), Water Content, Dimensional Tolerances (ISO 18369-3), Spectral/UV Transmittance (ISO 18369-2), Extractables/Leachables, Biocompatibility, Performance Criteria Pathway (2023), Care System Compatibility, Labeling (21 CFR 801), Clinical Data

**Physical Medicine — Powered Wheelchairs** (IOR, ITB):
Rows: Intended Use, Indications for Use, Wheelchair Type (power/power-assist/scooter), Drive Configuration, Maximum Speed, Range per Charge, Weight Capacity, Stability (ISO 7176-1 static, ISO 7176-2 dynamic), Braking (ISO 7176-3), Fatigue/Strength (ISO 7176-8), Obstacle Climbing (ISO 7176-10), Control Interface, Battery (IEC 62133), EMC (IEC 60601-1-2), Software, Human Factors, Electrical Safety

**Physical Medicine — TENS/NMES** (ILY, NUH):
Rows: Intended Use, Indications for Use, Stimulation Type (TENS/NMES/FES), Waveform, Output Channels, Max Output Current/Voltage, Frequency Range, Pulse Width Range, IEC 60601-2-10 Compliance, Electrode Type, Biocompatibility (electrode contact), Power Source, EMC, Human Factors (home use), Labeling

**Physical Medicine — Prosthetic Limbs** (ISF, ITN):
Rows: Intended Use, Indications for Use, Prosthetic Type (foot/ankle/knee/hip), Mechanism (passive/energy-storing/microprocessor), Weight Limit, Activity Level (K0-K4), Structural Testing (ISO 10328), Fatigue Testing (ISO 22675), Materials, Biocompatibility (socket interface), Software (if microprocessor), Battery (if powered), Waterproof Rating

**IVD — Clinical Chemistry Analyzers** (CZD, CRJ, CHN):
Rows: Intended Use, Indications for Use, Analyte(s) Measured, Measurement Methodology, Sample Types, Reportable Range, Precision (CV% per CLSI EP05), Accuracy/Bias (CLSI EP09), Linearity (CLSI EP06), LOD/LOQ (CLSI EP17), Interference Panel (HIL per CLSI EP07), Calibration Traceability (NIST/WHO/IFCC), CLIA Complexity, Throughput, Sample Volume, Reagent System, Software, Electrical Safety

**IVD — Hematology Analyzers** (JHR, JJX):
Rows: Intended Use, Indications for Use, CBC Parameters, WBC Differential (3-part/5-part/6-part), Measurement Technology (impedance/optical/fluorescence), Flagging Capabilities, Sample Type, Precision (CLSI EP05), Accuracy (CLSI H15/H20), Carryover, Linearity, Reagent System, Throughput, Software, Electrical Safety

**IVD — Immunoassay Systems** (various IM codes):
Rows: Intended Use, Indications for Use, Analyte(s), Assay Methodology (chemiluminescent/ELISA/lateral flow), Sample Types, Measuring Range, Precision (CLSI EP05), Accuracy (CLSI EP09), LOD/LOQ, Hook Effect, Heterophilic Ab Interference, Biotin Interference, Cross-Reactivity, Standardization (reference material), Clinical Performance, CLIA Complexity, Throughput, Software

**IVD — Molecular Diagnostics** (QKO and MI-panel codes):
Rows: Intended Use, Indications for Use, Assay Technology (PCR/isothermal/hybridization/NGS), Target Organisms/Analytes, Specimen Types, LOD (copies/mL or CFU/mL), Inclusivity, Exclusivity/Cross-Reactivity, Clinical Sensitivity (PPA), Clinical Specificity (NPA), Time to Result, Internal Controls, CLIA Complexity, Throughput, Software

**IVD — AST Systems** (various MI codes):
Rows: Intended Use, Indications for Use, AST Methodology (broth dilution/disk diffusion/automated), Organism-Drug Combinations, Essential Agreement (≥90%), Categorical Agreement (≥90%), VME Rate (<1.5%), ME Rate (<3%), Breakpoints (CLSI M100 edition), PCCP for Breakpoint Updates, Software

**IVD — NGS/Genomics** (PA-panel codes):
Rows: Intended Use, Indications for Use, Panel/Gene Coverage, Variant Types (SNV/indel/CNV/fusion/MSI/TMB), Sequencing Platform, LOD (VAF), Accuracy (vs. orthogonal methods), Precision, Bioinformatics Pipeline, Specimen Types (FFPE/fresh/liquid biopsy), DNA/RNA Input, Reference Materials, CDx Claims, Turnaround Time, CLIA Complexity, Software

**IVD — Drugs of Abuse Rapid Tests** (various TX codes):
Rows: Intended Use, Indications for Use, Drug Panels, Assay Technology (lateral flow/immunoassay), Cutoff Concentrations (per SAMHSA), Specimen Type (urine/oral fluid/blood), Sensitivity (PPA), Specificity (NPA), Cross-Reactivity, Near-Cutoff Precision, Time to Result, Read Window, CLIA Complexity, Visual Read Agreement, Specimen Validity Testing, Confirmation Method Referenced

**IVD — Coagulation** (GKM, JKA):
Rows: Intended Use, Indications for Use, Analyte(s) (PT/INR, APTT, fibrinogen, D-dimer), Methodology, ISI/INR Calibration Traceability, Heparin Sensitivity (APTT), Precision (CLSI EP05), Accuracy (CLSI EP09), Sample Types, CLIA Complexity, Throughput, Software

**General Hospital — Examination Gloves** (LYY, LYZ):
Rows: Intended Use, Indications for Use, Material (nitrile/latex/vinyl), Physical Dimensions (ASTM D3578/D6319), Tensile Strength/Elongation (before/after aging), AQL, Barrier Integrity (ASTM F1671), Biocompatibility (ISO 10993-5/-10), Protein Allergen (ASTM D5712 if NRL), Powder-Free Verification, Shelf Life

**Default (Unknown Product Code)**:
Rows: Intended Use, Indications for Use, Device Description, Technology/Principle of Operation, Materials, Key Performance Characteristics, Biocompatibility, Sterilization, Shelf Life, Software (if applicable), Electrical Safety (if applicable), Clinical Data

## Step 1.5: Source Subject Device Specifications

Before populating the subject device column, check for existing project data to avoid fabricating specs:

1. Read `$PROJECTS_DIR/$PROJECT_NAME/device_profile.json` for device specs (dimensions, materials, configurations)
2. Read `$PROJECTS_DIR/$PROJECT_NAME/drafts/draft_device-description.md` for component details and materials of construction
3. Read `$PROJECTS_DIR/$PROJECT_NAME/se_comparison.md` for any prior comparison data (subject device column)
4. Read `$PROJECTS_DIR/$PROJECT_NAME/import_data.json` for any imported eSTAR data

```bash
python3 << 'PYEOF'
import json, os, re

projects_dir = os.path.expanduser('~/fda-510k-data/projects')
settings_path = os.path.expanduser('~/.claude/fda-predicate-assistant.local.md')
if os.path.exists(settings_path):
    with open(settings_path) as f:
        m = re.search(r'projects_dir:\s*(.+)', f.read())
        if m: projects_dir = os.path.expanduser(m.group(1).strip())

project = "PROJECT"  # Replace with actual project name
pdir = os.path.join(projects_dir, project)

# Collect all subject device specs from project files
specs = {}

# 1. device_profile.json
dp = os.path.join(pdir, 'device_profile.json')
if os.path.exists(dp):
    with open(dp) as f:
        profile = json.load(f)
    print(f"SOURCE:device_profile.json")
    for k, v in profile.items():
        if v and str(v).strip():
            print(f"SPEC:{k}={v}")

# 2. draft_device-description.md
dd = os.path.join(pdir, 'drafts', 'draft_device-description.md')
if os.path.exists(dd):
    with open(dd) as f:
        desc_text = f.read()
    print(f"SOURCE:draft_device-description.md")
    # Extract gauges, dimensions, materials
    gauges = re.findall(r'\b(\d+)\s*[Gg](?:auge)?\b', desc_text)
    if gauges:
        print(f"SPEC:gauges={','.join(sorted(set(gauges)))}")
    materials = re.findall(r'(?:made of|composed of|material[s]?[:\s]+)([^\n.]+)', desc_text, re.I)
    if materials:
        print(f"SPEC:materials={'; '.join(m.strip() for m in materials)}")

# 3. import_data.json
imp = os.path.join(pdir, 'import_data.json')
if os.path.exists(imp):
    with open(imp) as f:
        idata = json.load(f)
    print(f"SOURCE:import_data.json")
    for k in ['device_description', 'materials', 'sterilization_method', 'dimensions']:
        v = idata.get(k) or idata.get('sections', {}).get(k)
        if v:
            print(f"SPEC:{k}={v}")

if not any(os.path.exists(os.path.join(pdir, f)) for f in ['device_profile.json', 'drafts/draft_device-description.md', 'import_data.json']):
    print("SOURCE:none")
PYEOF
```

**CRITICAL RULE: Never fabricate specific numerical values for the subject device.**

When populating the subject device column in the SE comparison table:

- **If a spec is found in project data** → use it exactly as stated (cite the source file)
- **If a spec is NOT found in project data** → write `[TODO: Verify — typical range for {product_code} is {X-Y}]` instead of inventing a plausible value
- **Predicate device specs** may be inferred from FDA data (510(k) summaries, GUDID, openFDA) — this is acceptable because those are public regulatory records
- **Subject device specs** MUST come from the user's own project data or be explicitly marked as TODO placeholders
- **Never mix** predicate-sourced data into the subject device column without explicit project data confirmation

After populating the table, add a sourcing comment:
```markdown
<!-- Subject device specs sourced from: {comma-separated list of project files used, or "no project data — all values marked [TODO]"} -->
```

**Example of CORRECT behavior:**
- Project data says "23G and 25G needles" → Subject column: "23G and 25G"
- No project data on needle gauge → Subject column: `[TODO: Verify — specify needle gauge(s)]`

**Example of INCORRECT behavior (DO NOT DO THIS):**
- No project data on needle gauge → Subject column: "19G, 22G, and 25G" ← FABRICATED

## Step 1.75: Material Extraction from Source PDFs

After Step 1.5 (sourcing subject device specs), if the `materials` array in `device_profile.json` is empty AND no materials were found in draft_device-description.md, attempt to extract materials from source PDF text:

```python
import re, os, glob

pdir = os.path.join(projects_dir, project)

# Check if materials are already known
dp = os.path.join(pdir, 'device_profile.json')
has_materials = False
if os.path.exists(dp):
    import json
    with open(dp) as f:
        profile = json.load(f)
    has_materials = bool(profile.get('materials', []))

if not has_materials:
    # Scan source_device_text_*.txt for material keywords
    material_keywords = [
        r'\bstainless\s+steel\b', r'\btitanium\b', r'\bPEEK\b', r'\bPTFE\b',
        r'\bsilicone\b', r'\bnitinol\b', r'\bcobalt[- ]?chromium\b', r'\bpolyurethane\b',
        r'\bpolycarbonate\b', r'\bnylon\b', r'\bpolyethylene\b', r'\bpolypropylene\b',
        r'\bUHMWPE\b', r'\bHDPE\b', r'\bFEP\b', r'\bacrylic\b', r'\bceramic\b',
        r'\bhydroxyapatite\b', r'\btungsten\b', r'\bnickel\b', r'\bPVC\b',
        r'\blatex\b', r'\bepoxy\b', r'\bparylene\b', r'\bhydrogel\b',
        r'\bcollagen\b', r'\bgold\b', r'\bplatinum\b', r'\biridium\b',
    ]

    found_materials = set()
    source_file = None

    for stf in glob.glob(os.path.join(pdir, 'source_device_text_*.txt')):
        with open(stf) as f:
            text = f.read()
        for pattern in material_keywords:
            matches = re.findall(pattern, text, re.I)
            for m in matches:
                found_materials.add(m.strip().title())
        if found_materials and not source_file:
            source_file = os.path.basename(stf)

    if found_materials:
        print(f"EXTRACTED_MATERIALS:{', '.join(sorted(found_materials))}")
        print(f"MATERIAL_SOURCE:{source_file}")
        print("NOTE:Materials extracted from source PDF text — present as inferred, not verified specs")
```

**If materials extracted:**
- Populate the "Materials" row in the subject device column with: `{material_list} [Inferred from source PDF — verify with manufacturer]`
- Add footnote: `† Materials extracted from {source_file} — not verified manufacturer specs. Confirm with actual BOM.`
- Do NOT present extracted materials as confirmed specifications

**If no materials found:** Leave as `[TODO: Specify materials of construction]`

## Step 1.85: Predicate PDF Stub Detection

After fetching or loading predicate PDF text (Step 2 below), classify the quality of each predicate's text data:

```python
def classify_predicate_text(text, k_number):
    """Classify predicate PDF text quality."""
    if not text or len(text.strip()) == 0:
        return "UNAVAILABLE", "No PDF text available"
    elif len(text.strip()) < 500:
        return "STUB", f"Only {len(text.strip())} chars — likely a cover page or corrupted extraction"
    elif len(text.strip()) < 2000:
        return "SPARSE", f"{len(text.strip())} chars — limited content, may be missing key sections"
    else:
        return "ADEQUATE", f"{len(text.strip())} chars"
```

**For each predicate, report classification:**
```
PREDICATE_QUALITY:{K-number}|{UNAVAILABLE|STUB|SPARSE|ADEQUATE}|{char_count}
```

**Apply quality-based handling:**
- **UNAVAILABLE**: Mark ALL predicate column cells as `[Data unavailable — manual entry required]`
- **STUB** (<500 chars): Mark predicate column cells as `[Inferred from openFDA metadata]` where openFDA data is used. Add footer warning: `"⚠ Predicate {K-number} has minimal PDF text ({N} chars). Predicate data inferred from openFDA database records only — may be incomplete."`
- **SPARSE** (<2000 chars): Mark specific cells where data was not found as `[Not found in summary — verify manually]`
- **ADEQUATE** (≥2000 chars): Normal extraction

**If ALL predicates are STUB or UNAVAILABLE**, add a prominent notice at the top of the SE table:
```markdown
> ⚠ **Limited Predicate Data**: All predicate device summaries had minimal or no PDF text available.
> Predicate columns are populated from openFDA database records only and may be incomplete.
> Manual verification against the actual 510(k) summary documents is strongly recommended.
```

## Step 2: Load Predicate & Reference Device Data

### PMA Device Data Retrieval (TICKET-003 Phase 1.5)

For any P-numbers identified in Step 0.5, retrieve SE-compatible data from the PMA SSED sections using the unified predicate interface. This data will be used to populate the predicate columns in the SE table.

```bash
python3 << 'PYEOF'
import sys, os, json
sys.path.insert(0, os.path.join(os.environ.get("FDA_PLUGIN_ROOT", ""), "scripts"))
from unified_predicate import UnifiedPredicateAnalyzer

analyzer = UnifiedPredicateAnalyzer()

# Process each PMA predicate
p_numbers = os.environ.get("PMA_PREDICATES", "").split(",")
p_numbers = [p.strip() for p in p_numbers if p.strip()]

for pma_num in p_numbers:
    se_data = analyzer.get_pma_se_table_data(pma_num)
    if "error" not in se_data:
        # Extract key fields for SE table population
        print(f"PMA_DEVICE_NAME:{pma_num}|{se_data.get('device_name', '')}")
        print(f"PMA_APPLICANT:{pma_num}|{se_data.get('applicant', '')}")
        print(f"PMA_PRODUCT_CODE:{pma_num}|{se_data.get('product_code', '')}")
        print(f"PMA_DECISION_DATE:{pma_num}|{se_data.get('decision_date', '')}")
        print(f"PMA_INTENDED_USE:{pma_num}|{se_data.get('intended_use', '')[:500]}")
        print(f"PMA_DEVICE_DESC:{pma_num}|{se_data.get('device_description', '')[:500]}")
        print(f"PMA_CLINICAL:{pma_num}|{se_data.get('clinical_data', '')[:500]}")
        print(f"PMA_BIOCOMPAT:{pma_num}|{se_data.get('biocompatibility', '')[:200]}")
        print(f"PMA_STERILIZATION:{pma_num}|{se_data.get('sterilization', '')[:200]}")
        print(f"PMA_SAFETY:{pma_num}|{se_data.get('safety_profile', '')[:300]}")
        print(f"PMA_DATA_SOURCE:{pma_num}|{se_data.get('data_source', 'unknown')}")
        print(f"PMA_QUALITY:{pma_num}|{se_data.get('section_quality', 0)}")
        print(f"PMA_STATUS:{pma_num}|{se_data.get('regulatory_status', '')}")
    else:
        print(f"PMA_ERROR:{pma_num}|{se_data.get('error', 'unknown')}")
PYEOF
```

**PMA data for SE table:** When a PMA device is used as a predicate in an SE table, populate the predicate column using the SSED-extracted data above. Map SSED sections to SE table rows:
- SSED "Indications for Use" -> SE "Intended Use / Indications for Use" row
- SSED "Device Description" -> SE "Device Description / Materials" rows
- SSED "Clinical Studies" -> SE "Clinical Data" row
- SSED "Nonclinical Testing" -> SE "Performance Testing" rows
- SSED "Biocompatibility" -> SE "Biocompatibility" row
- SSED "Manufacturing" -> SE "Sterilization" row

If SSED sections are unavailable (data_source == "api_metadata"), note in the table: "[PMA data limited to API metadata -- SSED not extracted. Run `/fda-tools:pma-intelligence --pma {P-number} --download-ssed --extract-sections` for full data.]"

### Check PDF text cache (for K-numbers)

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

# Batch lookup: single OR query for ALL predicate and reference K-numbers (1 call instead of N)
all_knumbers = ["KNUMBER1", "KNUMBER2"]  # Replace with all predicate + reference K-numbers

if api_enabled and all_knumbers:
    batch_search = "+OR+".join(f'k_number:"{kn}"' for kn in all_knumbers)
    params = {"search": batch_search, "limit": str(len(all_knumbers))}
    if api_key:
        params["api_key"] = api_key
    # Fix URL encoding: replace + with space before urlencode
    params["search"] = params["search"].replace("+", " ")
    url = f"https://api.fda.gov/device/510k.json?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (FDA-Plugin/5.21.0)"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            results_by_k = {r.get("k_number", ""): r for r in data.get("results", [])}
            for knumber in all_knumbers:
                r = results_by_k.get(knumber)
                if r:
                    print(f"=== {knumber} ===")
                    print(f"APPLICANT:{r.get('applicant', 'N/A')}")
                    print(f"DEVICE_NAME:{r.get('device_name', 'N/A')}")
                    print(f"DECISION_DATE:{r.get('decision_date', 'N/A')}")
                    print(f"DECISION_CODE:{r.get('decision_code', 'N/A')}")
                    print(f"PRODUCT_CODE:{r.get('product_code', 'N/A')}")
                    print(f"CLEARANCE_TYPE:{r.get('clearance_type', 'N/A')}")
                    print(f"STATEMENT_OR_SUMMARY:{r.get('statement_or_summary', 'N/A')}")
                    print(f"SOURCE:api")
                else:
                    print(f"=== {knumber} ===")
                    print("SOURCE:fallback")
    except:
        for knumber in all_knumbers:
            print(f"=== {knumber} ===")
            print("SOURCE:fallback")
else:
    for knumber in all_knumbers:
        print(f"=== {knumber} ===")
        print("SOURCE:fallback")
PYEOF
```

If the API returned `SOURCE:fallback`, use flat files:

```bash
grep "KNUMBER" ~/fda-510k-data/extraction/pmn96cur.txt 2>/dev/null
```

Extract: applicant, decision date, product code, decision code, review time, submission type, summary/statement.

## Step 3: Extract Key Characteristics from Predicate Text

For each predicate/reference device text, apply the **3-tier section detection system from `references/section-patterns.md`** to extract sections. **Note:** Predicate PDFs (especially older or poor-quality scans) often require Tier 2 OCR-tolerant matching — apply the OCR substitution table before giving up on a heading.

### Universal extraction (all device types):

1. **Indications for Use** — Look for IFU section, extract the full IFU text
2. **Device Description** — Extract description section, summarize into 2-3 sentences
3. **SE Comparison** — If the predicate itself has an SE table, extract it (contains its own predicate chain info)
4. **Biocompatibility** — Extract ISO 10993 tests performed and results
5. **Sterilization** — Method, standard, SAL level
6. **Shelf Life** — Duration, storage conditions
7. **Clinical Data** — Study type, N, key results

### Device-type specific extraction:

Apply the device-specific patterns from the 3-tier section detection system in `references/section-patterns.md`. For example, for CGM devices, also extract:
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

**When `--device-description` and/or `--intended-use` provided:**
- Auto-populate the Subject Device column cells using the provided text
- For "Intended Use" row: use `--intended-use` text directly
- For "Device Description" row: use `--device-description` text directly
- For other rows: extract relevant details from `--device-description` if possible, otherwise use `[YOUR DEVICE: specify {specific detail needed}]`
- Mark auto-populated cells as `{value} [auto-populated from --device-description]` so user knows to verify

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

## Step 4a: Conditional Row Injection

After selecting the device-type template rows (Step 1) and before generating the table, inject additional rows based on detected device characteristics:

### Reusable Device Rows

**Detection:** Scan device description, se_comparison, and device_profile for reusable indicators: "reusable", "reprocessing", "autoclave", "multi-use", "non-disposable", "endoscope", "instrument tray".

**If reusable device detected, inject these rows after "Sterilization":**

| Row | What to Extract | Where to Find |
|-----|----------------|---------------|
| Reprocessing Method | "Manual cleaning + steam sterilization" | Device Description, Labeling |
| Maximum Reprocessing Cycles | "Validated for 100 cycles" | Performance Testing |
| Cleaning Agents | "Enzymatic detergent, neutral pH" | Labeling, Reprocessing IFU |

### Powered Accessory / Equipment-Dependent Device Rows

**Detection:** Scan device description for: "generator", "console", "controller", "power supply", "light source", "camera head", "processor", "power unit", "energy source", "compatible with".

**If compatible equipment detected, inject these rows after "Device Description":**

| Row | What to Extract | Where to Find |
|-----|----------------|---------------|
| Compatible Equipment | "Model XYZ Generator" | Device Description, Labeling |
| Power Requirements | "120V/240V AC, 50-60 Hz" | Device Description, Electrical Safety |

### Shelf Life Row Expansion

**Detection:** Scan se_comparison, device_profile, calculations/ for shelf life claims.

**If shelf life claim detected, expand the single "Shelf Life" row into 4 sub-rows:**

| Row | What to Extract | Where to Find |
|-----|----------------|---------------|
| Shelf Life — Claimed Duration | "3 years from date of sterilization" | Labeling, Shelf Life section |
| Shelf Life — Aging Methodology | "Accelerated per ASTM F1980 + real-time initiated" | Shelf Life section, calculations/ |
| Shelf Life — Q10 Value | "2.0 (conservative)" | calculations/shelf_life_calc.json |
| Shelf Life — Package Type | "Tyvek/PETG thermoformed tray, double sterile barrier" | Package Design, Shelf Life section |

**Data threading for shelf life expansion:**
- If `calculations/shelf_life_calc.json` exists: extract Q10, AAF, claimed duration, ambient/accelerated temperatures
- If `se_comparison.md` mentions predicate shelf life: extract for predicate column
- If no shelf life data available: use standard rows with `[TODO: specify]`

## Step 4b: Materials Comparison (BOM Integration)

If the subject device's project contains BOM/materials data (from `import_data.json` materials array or `draft_device-description.md`), add a detailed **Materials Comparison** row:

```markdown
| Materials / BOM | Subject: {material_list} | Predicate: {extracted_materials} | Comparison |
```

**Auto-compare materials logic:**
- Extract materials from predicate text (look for "materials", "composition", "construction", "alloy", "polymer" sections)
- Compare subject BOM against predicate materials
- Flag differences that may require additional biocompatibility testing:
  - New material not in predicate → `Different: New material ({material}) not in predicate. Biocompatibility testing per ISO 10993-1:2025 may be required.`
  - Same material family, different grade → `Similar: Same material family. Verify equivalent biocompatibility.`
  - Identical materials → `Same`
- For patient-contacting materials, always note: "Patient-contacting: {Yes/No}"

If no BOM data available, the standard "Materials" row from the device-type template is used with `[YOUR DEVICE: specify materials of construction]`.

## Step 5: Format and Output

### Console output (default)

Present the table in clean markdown format (see `references/output-formatting.md`). Add header and footer:

```markdown
# Substantial Equivalence Comparison Table
**Subject Device:** {device_description or "[To be specified]"}
**Predicate Device(s):** {K-numbers with device names}
**Reference Device(s):** {K-numbers with device names, or "None"}
**Product Code:** {CODE} — {Device Name} (Class {class})
**Generated:** {date} | v5.22.0

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

> **Disclaimer:** This comparison table is AI-generated from public FDA data.
> Verify independently. Not regulatory advice.
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

**IMPORTANT: Skip this entire step if `--full-auto` is active OR if both `--device-description` and `--intended-use` were provided.** In those cases, the table is as complete as it can be — proceed directly to Step 7.

### If NOT --full-auto AND missing device details: Interactive Refinement

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

## Audit Logging

After generating the SE comparison table, write audit log entries using `fda_audit_logger.py`. Only log if `--project` is specified.

### Log template selection (after Step 1)

```bash
python3 "$FDA_PLUGIN_ROOT/scripts/fda_audit_logger.py" \
  --project "$PROJECT_NAME" \
  --command compare-se \
  --action template_selected \
  --subject "$PRODUCT_CODE" \
  --decision "$TEMPLATE_NAME" \
  --mode "$MODE" \
  --decision-type auto \
  --rationale "Selected $TEMPLATE_NAME template for product code $PRODUCT_CODE ($DEVICE_TYPE)" \
  --data-sources "openFDA classification" \
  --alternatives "$TEMPLATE_ALTERNATIVES_JSON" \
  --metadata "{\"product_code\":\"$PRODUCT_CODE\",\"template_rows\":$ROW_COUNT}"
```

### Log predicate inference (after Step 2, if --infer used)

```bash
python3 "$FDA_PLUGIN_ROOT/scripts/fda_audit_logger.py" \
  --project "$PROJECT_NAME" \
  --command compare-se \
  --action predicate_inferred \
  --subject "$PREDICATE_LIST" \
  --decision "inferred" \
  --mode "$MODE" \
  --decision-type auto \
  --rationale "Inferred $PRED_COUNT predicates from $INFER_SOURCE" \
  --data-sources "$INFER_SOURCE" \
  --alternatives "$ALL_CANDIDATES_JSON" \
  --exclusions "$EXCLUDED_CANDIDATES_JSON"
```

### Log cell auto-population summary (after Step 4)

```bash
python3 "$FDA_PLUGIN_ROOT/scripts/fda_audit_logger.py" \
  --project "$PROJECT_NAME" \
  --command compare-se \
  --action cell_auto_populated \
  --subject "$PRODUCT_CODE" \
  --decision "populated" \
  --mode "$MODE" \
  --rationale "$FILLED_COUNT/$TOTAL_CELLS cells auto-populated, $REVIEW_COUNT require review" \
  --data-sources "openFDA 510k API,510k summary PDFs" \
  --metadata "{\"total_cells\":$TOTAL_CELLS,\"auto_filled\":$FILLED_COUNT,\"need_review\":$REVIEW_COUNT,\"need_input\":$INPUT_COUNT}"
```

### Log comparison decisions (after Step 4)

```bash
python3 "$FDA_PLUGIN_ROOT/scripts/fda_audit_logger.py" \
  --project "$PROJECT_NAME" \
  --command compare-se \
  --action comparison_decision \
  --subject "$PRODUCT_CODE" \
  --decision "completed" \
  --mode "$MODE" \
  --rationale "SE comparison: $SAME_COUNT Same, $SIMILAR_COUNT Similar, $DIFFERENT_COUNT Different across $ROW_COUNT rows" \
  --metadata "{\"same\":$SAME_COUNT,\"similar\":$SIMILAR_COUNT,\"different\":$DIFFERENT_COUNT,\"rows\":$ROW_COUNT}"
```

### Log table generation (at completion)

```bash
python3 "$FDA_PLUGIN_ROOT/scripts/fda_audit_logger.py" \
  --project "$PROJECT_NAME" \
  --command compare-se \
  --action table_generated \
  --subject "$PRODUCT_CODE" \
  --decision "generated" \
  --mode "$MODE" \
  --rationale "SE table generated: $ROW_COUNT rows, $PRED_COUNT predicates, $REF_COUNT references" \
  --metadata "{\"row_count\":$ROW_COUNT,\"predicate_count\":$PRED_COUNT,\"reference_count\":$REF_COUNT}" \
  --files-written "$OUTPUT_PATH"
```

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

**Generated:** {date} | v5.22.0
**Predicates:** {K-numbers}
**Cells requiring input:** {count}
**Cells requiring review:** {count}
```

Also update the Submission Readiness Summary table in the outline to mark SE Comparison as "✓".



## Output Format

### Sources Checked

Append a sources table to every output showing which external APIs were queried and their status. See [CONNECTORS.md](../CONNECTORS.md) for the standard format. Only include rows for sources this command actually uses.



- **NEVER recommend** "Use /fda:extract" or "Run another command to get this data". Fetch what you need.
- If a PDF fetch fails, note it gracefully: "K234567 summary PDF was not accessible; predicate data populated from FDA database records only."
- The table is a **starting point** — users MUST review and edit before submitting to FDA.
- For **multiple predicates**, each gets its own column. If comparing >3 devices total (subject + predicates + references), consider splitting into separate tables.
- The Comparison column should reference the PRIMARY predicate. If using multiple predicates for different claims, note which predicate each "Same/Different" applies to.
