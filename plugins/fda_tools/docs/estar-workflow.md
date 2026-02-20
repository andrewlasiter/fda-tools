# eSTAR Workflow: From Plugin to FDA Submission

## Overview

The plugin generates **eSTAR-compatible XML** that can be imported into the official FDA eSTAR PDF templates. This workflow bridges the gap between AI-drafted content and the FDA's submission system.

---

## Step 1: Draft Your Submission

```bash
# Complete the normal plugin workflow:
/fda:research --code OVE
/fda:review
/fda:compare-se
/fda:draft --all
/fda:consistency
/fda:pre-check
```

**Result:** Project directory with `device_profile.json`, `review.json`, and `drafts/` folder

---

## Step 2: Generate eSTAR XML

### Supported Templates

| Template | FDA Form | Use Case |
|----------|----------|----------|
| **nIVD** | FDA 4062 | Most medical devices (non-IVD) |
| **IVD** | FDA 4078 | In vitro diagnostic devices |
| **PreSTAR** | FDA 5064 | Pre-Submission meeting requests |

### Command

```bash
# Navigate to your project
cd /home/linux/fda-510k-data/projects/your_project

# Generate XML
python3 /path/to/estar_xml.py generate \
  --project your_project_name \
  --template nIVD \
  --format real \
  --output submission.xml
```

### What Gets Auto-Populated

The XML generation maps your project data to **143 FDA form fields**:

| Section | Auto-Populated Fields | Source |
|---------|----------------------|--------|
| **Applicant Information** | Company name, contact, address | `device_profile.json` |
| **Device Description** | Trade name, model, description text | `device_profile.json` |
| **Classification** | Product code, regulation #, class | `review.json` |
| **Indications for Use** | Full IFU statement | `device_profile.json` |
| **Predicates** | K-number, name, manufacturer | `review.json` |
| **510(k) Summary** | Applicant, device, regulation, summary text | `drafts/draft_510k-summary.md` |
| **Declaration of Conformity** | Company name, device name | `device_profile.json` |
| **Truthful & Accuracy** | Certifying individual capacity | `device_profile.json` |
| **Labeling** | Labeling text | `drafts/draft_labeling.md` |
| **Biocompatibility** | Contact type, duration, materials | `device_profile.json` |
| **Sterilization** | Sterilization method | `device_profile.json` |
| **Shelf Life** | Shelf life claim | `device_profile.json` |
| **Software/Cybersecurity** | Software version, SaMD classification | `device_profile.json` |

**Field population rate:** Typically 25-40% on first generation (improves as you fill in project data)

---

## Step 3: Import XML into eSTAR PDF

### Download Official Template

Get the latest eSTAR template from FDA:
- **nIVD eSTAR v6.1**: https://www.fda.gov/medical-devices/premarket-submissions-selecting-and-preparing-correct-submission/estar-submission-program
- Plugin includes templates in: `plugins/fda-tools/estar/`

### Import Process (Adobe Acrobat Required)

1. Open the **blank eSTAR PDF** in Adobe Acrobat Pro DC or Reader DC
2. Go to **Form → Import Data** (or **Tools → Prepare Form → Import Data**)
3. Select your generated XML file (`submission.xml`)
4. Click **Open**

**Result:** All mapped fields auto-populate with your data!

### Verify Population

Check these key fields are populated:
- ✅ Section 1: Applicant Information (company name, contact)
- ✅ Section 2: Device Description (trade name, description)
- ✅ Section 3: Indications for Use (IFU statement)
- ✅ Section 4: Classification (product code, regulation)
- ✅ Section 5: Predicates (K-number, device name, manufacturer)
- ✅ Section 6: 510(k) Summary (summary text)

---

## Step 4: Add Attachments to eSTAR

### Where to Attach Files

The eSTAR PDF has **attachment points in every section**. Common attachment locations:

| Section | Attachment Field | What to Attach |
|---------|-----------------|----------------|
| **Section 6: Device Description** | "Additional Description" | Device diagrams, schematics, photos |
| **Section 8: Declaration of Conformity** | "DoC Attachment" | Standards testing certificates (PDF) |
| **Section 9: Labeling** | "Label Images" | Label artwork, IFU PDF |
| **Section 10: Sterilization** | "Sterilization Data" | Sterilization validation report |
| **Section 11: Shelf Life** | "Shelf Life Data" | ASTM F1980 AAF calculation, stability testing |
| **Section 12: Biocompatibility** | "Biocompatibility Reports" | ISO 10993 test reports |
| **Section 13: Software** | "Software Documentation" | Software description, V&V summary |
| **Section 14: EMC/Electrical** | "Test Reports" | IEC 60601-1, IEC 60601-1-2 reports |
| **Section 15: Performance Testing** | "Test Reports" | Bench test reports, validation data |
| **Section 16: Clinical** | "Clinical Data" | Clinical study reports, literature |
| **Section 17: Human Factors** | "HF Reports" | IEC 62366-1 validation report |

### How to Attach (Adobe Acrobat)

**Method 1: Click attachment icon in PDF**
1. Navigate to the section (e.g., Section 15: Performance Testing)
2. Click the **paperclip icon** or "Add Attachment" button in that section
3. Select your PDF file (e.g., `Bench_Test_Report.pdf`)
4. Click **Open**

**Method 2: Tools menu**
1. Go to **Tools → Edit PDF → More → Attach File**
2. Select the file
3. PDF embeds the attachment

**File Requirements:**
- Format: **PDF only** (FDA does not accept Word, Excel, or other formats)
- Size: Max 100 MB per file (200 MB total per submission)
- Naming: Use descriptive names (e.g., `IEC60601-1_Test_Report_v2.pdf`)

### Attachment Checklist

```
Performance Testing (Section 15):
 ☐ ASTM F2077 static compression report
 ☐ ASTM F2077 fatigue testing report
 ☐ ASTM F2077 compression-shear report
 ☐ ASTM F2267 subsidence testing report

Biocompatibility (Section 12):
 ☐ ISO 10993-5 cytotoxicity report
 ☐ ISO 10993-10 irritation/sensitization report
 ☐ Material certificates (PEEK-OPTIMA, Ti-6Al-4V)

EMC/Electrical (Section 14):
 ☐ IEC 60601-1 electrical safety report
 ☐ IEC 60601-1-2 EMC report
 ☐ IEC 60601-2-XX particular standard report

Sterilization (Section 10):
 ☐ Sterilization validation report (ISO 11135/14937)
 ☐ Sterility assurance level (SAL) documentation

Software (Section 13):
 ☐ Software description document
 ☐ Software verification & validation summary
 ☐ Cybersecurity risk assessment (if applicable)

Labeling (Section 9):
 ☐ Label artwork (all configurations)
 ☐ Instructions for Use (IFU) PDF
 ☐ Patient implant card (if implantable)
```

---

## Step 5: Validate eSTAR Package

### Before Submission

1. **Check field population rate**
   ```bash
   # Count populated vs. empty fields
   grep -o "<[^>]*>[^<>]*</[^>]*>" submission.xml | wc -l
   ```

2. **Verify required sections**
   - Cover Letter (Section 1) ✅
   - Form 3514 (Section 2) ✅
   - Form 3881 (Section 3) ✅
   - Truthful & Accuracy (Section 4) ✅

3. **Check attachment count**
   - Adobe Acrobat: **File → Properties → Description** shows attachment count

4. **Run final consistency check**
   ```bash
   /fda:consistency --project your_project
   ```

### eSTAR Submission Checklist (FDA RTA Requirements)

```
☐ All required sections completed (1-9 mandatory)
☐ Form 3514 (CDRH Premarket Review Cover Sheet) signed
☐ Form 3881 (Indications for Use) signed
☐ Truthful & Accuracy Statement signed
☐ 510(k) Summary included
☐ Predicate device clearly identified
☐ SE comparison table complete
☐ Performance testing reports attached
☐ Labeling (labels + IFU) attached
☐ No placeholder text ([TODO], [COMPANY], etc.)
☐ Device description matches across all sections
☐ IFU consistent in Form 3881, Labeling, Summary
☐ File size <200 MB total
```

---

## Step 6: Export Final eSTAR Package

### Option 1: Submit PDF Directly (eSTAR Portal)

1. Save the populated PDF: **File → Save As → submission_estar.pdf**
2. Upload to FDA eSTAR portal: https://www.fda.gov/industry/fda-estar-electronic-submission-template-and-resource
3. FDA validates the PDF and extracts embedded attachments

### Option 2: Generate Submission ZIP (Legacy)

If using older submission methods:

```bash
# Use the plugin's assemble command
/fda:assemble --project your_project --format zip

# Creates:
submission_package.zip
├── estar_submission.pdf
├── attachments/
│   ├── Section_15_Performance_Testing.pdf
│   ├── Section_12_Biocompatibility.pdf
│   └── ...
└── manifest.json
```

---

## Automation Level Summary

| Task | Manual | Semi-Automated | Fully Automated |
|------|--------|----------------|-----------------|
| Field population | ❌ | ✅ (25-40% auto) | Future (80%+) |
| Section drafting | ❌ | ✅ (18+ sections) | ✅ Done |
| Attachment identification | ❌ | ✅ (checklist) | ❌ |
| Attachment upload | ❌ | ❌ | ❌ Must be manual |
| XML generation | ❌ | ❌ | ✅ Done |
| eSTAR import | ❌ | ✅ (one-click) | ✅ Done |

**Current bottleneck:** Attachment PDFs must be generated/collected manually (test reports, certificates)

---

## Advanced: Increasing Auto-Population Rate

### Current: 25-40% populated

To reach **80%+** population:

1. **Fill in company-specific data in `device_profile.json`:**
   ```json
   {
     "applicant_name": "Your Company Inc.",
     "contact_first_name": "Jane",
     "contact_last_name": "Doe",
     "email": "jane.doe@company.com",
     "phone": "+1-555-0100",
     "address_street": "123 Medical Device Lane",
     "address_city": "Boston",
     "address_state": "MA",
     "address_zip": "02101",
     "device_trade_name": "Your Device Name",
     "device_model": "Model ABC-100",
     "sterilization_method": "Ethylene Oxide (EO)",
     "shelf_life_claim": "5 years"
   }
   ```

2. **Complete drafts for all sections**
   - The XML generator reads `drafts/*.md` files
   - More complete drafts → more populated XML fields

3. **Add standards to `standards_lookup.json`**
   - The DoC section pulls from this file

4. **Future enhancement:** Direct openFDA API calls to populate predicate data automatically

---

## Troubleshooting

### "No fields populated after import"

**Cause:** XML format mismatch or template version mismatch

**Fix:**
1. Verify template version matches:
   ```bash
   # Check template type in XML
   grep "Form FDA" submission.xml
   ```
2. Ensure using `--format real` (not legacy)
3. Download latest eSTAR PDF from FDA (v6.1 for nIVD/IVD)

### "Attachment won't attach"

**Cause:** File format not PDF or file too large

**Fix:**
1. Convert all docs to PDF first
2. Compress large PDFs: **File → Print → Save as PDF** (in Adobe)
3. Split reports >100 MB into multiple attachments

### "Fields show [TODO] or [COMPANY]"

**Cause:** Plugin drafts still contain placeholders

**Fix:**
1. Run `/fda:consistency` to identify all placeholders
2. Search/replace in draft files:
   ```bash
   # Find all TODOs
   grep -r "\[TODO" drafts/
   ```
3. Fill in company-specific data
4. Regenerate XML

---

## Next Steps: Further Automation

**Planned enhancements:**
1. ✅ XML generation (Done)
2. ⚠️ Predicate auto-fetch from openFDA (In progress)
3. ⚪ Attachment manifest generation (identifies what to attach)
4. ⚪ Standards certificate auto-fetch (from NSF, UL, TÜV databases)
5. ⚪ Direct eSTAR portal API submission (when FDA provides API)

---

## Summary: Plugin Value

**Without plugin:**
- Manual data entry for 143 form fields
- No validation or consistency checking
- Ad-hoc predicate research
- Section drafting from scratch
- No submission readiness assessment

**With plugin:**
- **25-40% fields auto-populated** (improves to 80%+ with complete project data)
- **18+ sections auto-drafted** with device-type adaptive logic
- **Consistency validation** across all documents
- **FDA review simulation** (RTA checklist, SRI scoring)
- **One-click XML import** into eSTAR PDF

**Time savings estimate:**
- Manual 510(k): 200-400 hours
- With plugin: 60-120 hours (70% reduction)
- Primarily saves time on: predicate research, SE table generation, section drafting, consistency checking
