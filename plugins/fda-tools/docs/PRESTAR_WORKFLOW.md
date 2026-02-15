# PreSTAR XML Generation Workflow

Complete guide for generating FDA-compliant PreSTAR XML for Pre-Submission meetings.

## Overview

The PreSTAR workflow generates three outputs:
1. **presub_plan.md** - Human-readable Pre-Sub meeting request
2. **presub_metadata.json** - Structured meeting data
3. **presub_prestar.xml** - FDA eSTAR XML for FDA Form 5064 import

## Quick Start

### Basic Usage

```bash
/fda-tools:presub DQY --project my_device \
  --device-description "Single-use catheter for vascular access" \
  --intended-use "To provide temporary vascular access for medication delivery"
```

### With Project Data

If you have an existing project with predicates and testing data:

```bash
/fda-tools:presub DQY --project catheter_510k
```

The command will auto-populate fields from:
- `device_profile.json` - Device specifications, materials, sterilization
- `review.json` - Accepted predicates
- `guidance_cache/` - Applicable FDA guidance documents
- `standards_lookup.json` - FDA-recognized consensus standards

## Meeting Types (6 Types)

The command auto-detects the appropriate meeting type based on:
- Number of questions (≥4 → formal, 1-3 → written, 0 → info-only)
- Device characteristics (clinical study → pre-ide, pathway questions → administrative)
- Novel features (first-of-kind → formal)

### 1. Formal Pre-Submission Meeting

**When to Use**: Complex devices, novel technology, 4+ regulatory questions

**Example**:
```bash
/fda-tools:presub OVE --project cervical_fusion \
  --device-description "Cervical fusion device with novel locking mechanism" \
  --intended-use "Cervical spine fusion in skeletally mature patients"
```

**Generates**: 12 sections including comprehensive testing strategy, predicate analysis, risk management

### 2. Written Response (Q-Sub)

**When to Use**: Straightforward devices, 1-3 well-scoped technical questions

**Example**:
```bash
/fda-tools:presub DQY --project catheter_simple \
  --device-description "Single-use catheter" \
  --intended-use "Vascular access" \
  --meeting-type written
```

**Generates**: Streamlined 9-section format focused on specific questions

### 3. Informational Meeting

**When to Use**: Early-stage devices, technology overview, no formal FDA feedback expected

**Example**:
```bash
/fda-tools:presub QKQ --project pathology_ai \
  --device-description "AI-based digital pathology system" \
  --intended-use "Automated analysis of tissue samples" \
  --meeting-type info
```

### 4. Pre-IDE Meeting

**When to Use**: Clinical study planning, IDE protocol discussion

**Example**:
```bash
/fda-tools:presub CFR --project implant_clinical \
  --device-description "Novel implantable cardiac monitor" \
  --intended-use "Continuous cardiac rhythm monitoring" \
  --meeting-type pre-ide
```

**Generates**: 14 sections including study design, endpoints, sample size, DSMB plan

### 5. Administrative Meeting

**When to Use**: Pathway determination (510(k) vs De Novo vs PMA), classification questions

**Example**:
```bash
/fda-tools:presub NEW --project novel_device \
  --device-description "First-of-kind robotic surgical system" \
  --intended-use "Minimally invasive surgery assistance" \
  --meeting-type administrative
```

### 6. Info-Only Submission

**When to Use**: FYI to FDA, no meeting or feedback requested

**Example**:
```bash
/fda-tools:presub DQY --project catheter_fyi \
  --device-description "Modified catheter design" \
  --intended-use "Vascular access" \
  --meeting-type info-only
```

## Question Selection

### Auto-Triggers

Questions are automatically selected based on device description keywords:

| Trigger | Keywords | Questions Added |
|---------|----------|-----------------|
| **patient_contacting** | "patient contact", "contacting", "skin contact" | Biocompatibility (ISO 10993-5, -10, -11) |
| **sterile_device** | "sterile", "sterilization", "sterilized" | Sterilization validation, Shelf life |
| **powered_device** | "powered", "electrical", "electronic", "battery" | Electrical safety (IEC 60601-1, -1-2) |
| **software_device** | "software", "algorithm", "ai", "machine learning" | Software V&V (IEC 62304, 62366) |
| **implant_device** | "implant", "implantable", "permanent" | Long-term biocompatibility, MRI compatibility |
| **reusable_device** | "reusable", "reprocessing", "cleaning" | Reprocessing validation |
| **novel_technology** | "novel", "first-of-kind", "unprecedented" | Novel feature discussion |

### Example: Auto-Trigger Selection

**Device Description**: "Sterile, single-use catheter with novel locking mechanism"

**Auto-Triggers Fired**:
- `sterile_device` → Adds sterilization + shelf life questions
- `novel_technology` → Adds novel feature questions

**Questions Selected** (5 total):
1. PRED-001: Predicate selection
2. CLASS-001: Classification confirmation
3. TEST-STER-001: Sterilization validation approach
4. TEST-SHELF-001: Shelf life claim and testing
5. NOVEL-001: Novel locking mechanism discussion

### Manual Question Selection

Override auto-selection by editing `presub_metadata.json` after generation:

```json
{
  "questions_generated": ["PRED-001", "TEST-BIO-001", "CUSTOM-Q1"],
  "question_count": 3
}
```

Then regenerate XML:
```bash
python3 scripts/estar_xml.py generate --project my_device --template PreSTAR
```

## FDA eSTAR Import Workflow

### Step-by-Step Instructions

1. **Generate PreSTAR XML**:
   ```bash
   /fda-tools:presub DQY --project my_device \
     --device-description "..." \
     --intended-use "..."
   ```

2. **Verify Output Files**:
   ```bash
   ls ~/fda-510k-data/projects/my_device/
   # Should show:
   # - presub_plan.md
   # - presub_metadata.json
   # - presub_prestar.xml
   ```

3. **Review presub_plan.md**:
   - Open in markdown viewer or text editor
   - Review auto-selected questions (Section 5)
   - Verify device description (Section 2)
   - Check placeholder fields marked `[TODO: Company-specific — ...]`

4. **Download FDA Form 5064**:
   - Visit [FDA eSTAR Forms](https://www.fda.gov/medical-devices/premarket-submissions/electronic-submission-template-and-resource-estar)
   - Download "PreSTAR Template (FDA 5064)"
   - Save as `FDA_5064_PreSTAR.pdf`

5. **Import XML into FDA Form**:
   - Open `FDA_5064_PreSTAR.pdf` in **Adobe Acrobat** (not Acrobat Reader)
   - Go to: **Form** > **Import Data**
     - OR: **Tools** > **Prepare Form** > **Import Data**
   - Select: `~/fda-510k-data/projects/my_device/presub_prestar.xml`
   - Click **Open**

6. **Verify Field Population**:
   - **Administrative Information** (Page 1):
     - Applicant Name: `[TODO: Company Name]` (fill manually)
     - Contact Name: `[TODO: First Last]` (fill manually)
     - Email: `[TODO: email@company.com]` (fill manually)
     - Phone: `[TODO: Phone]` (fill manually)

   - **Device Description** (Page 2):
     - Trade Name: `[TODO: Device Trade Name]` (fill manually)
     - Device Description: Auto-populated from device_description

   - **Indications for Use** (Page 3):
     - IFU Text: Auto-populated from intended_use

   - **Classification** (Page 4):
     - Product Code: Auto-populated (e.g., "DQY")

   - **Submission Characteristics** (Page 5):
     - Meeting Type: Auto-populated (e.g., "Formal Pre-Submission Meeting")
     - Selection Rationale: Auto-populated
     - Device Description Summary: Auto-populated

   - **Questions for FDA** (Page 6):
     - Question 1: Auto-populated
     - Question 2: Auto-populated
     - ... (up to 7 questions)

7. **Fill Remaining Fields**:
   - Replace all `[TODO: ...]` placeholders with actual company information
   - Add attachments (device photos, predicate comparison tables, test protocols)

8. **Save and Submit**:
   - Save as `PreSub_[DeviceName]_[Date].pdf`
   - Submit to FDA via eSTAR portal or email to assigned reviewer

## XML Field Mapping

### QPTextField110 (Questions for FDA)

**Format**:
```
Question 1:
PRED-001: Does FDA agree that K123456 (Device Name) is an appropriate predicate device for our catheter system? If not, can FDA recommend alternative predicate(s)?

Question 2:
TEST-BIO-001: We propose ISO 10993-5 (cytotoxicity), -10 (sensitization), and -11 (systemic toxicity) biocompatibility testing. Does FDA agree this testing strategy is sufficient, or does FDA recommend additional testing?
```

**Source**: `presub_metadata.json` → `questions_generated` array

### SCTextField110 (Submission Characteristics)

**Format**:
```
Meeting Type: Formal Pre-Submission Meeting
Selection Rationale: 5 questions → formal meeting recommended
Number of Questions: 5

Device Description:
Single-use catheter for vascular access with novel locking mechanism...

Proposed Indications for Use:
To provide temporary vascular access for medication delivery in adult patients...
```

**Source**: `presub_metadata.json` → `meeting_type`, `device_description`, `intended_use`, `detection_rationale`

## Troubleshooting

### XML Import Fails

**Problem**: Adobe Acrobat shows "Import failed" error

**Solutions**:
1. Verify you're using Adobe Acrobat (not Acrobat Reader)
2. Check XML file is valid:
   ```bash
   xmllint --noout presub_prestar.xml
   # Should show no errors
   ```
3. Regenerate XML with `--format real` flag:
   ```bash
   python3 scripts/estar_xml.py generate --project my_device --template PreSTAR --format real
   ```

### Fields Not Populating

**Problem**: XML imports but fields are empty

**Solutions**:
1. Check `presub_metadata.json` exists and has data:
   ```bash
   cat ~/fda-510k-data/projects/my_device/presub_metadata.json
   ```
2. Verify `questions_generated` array is not empty
3. Regenerate metadata:
   ```bash
   /fda-tools:presub DQY --project my_device --device-description "..." --intended-use "..."
   ```

### Wrong Meeting Type Selected

**Problem**: Auto-detection selected wrong meeting type (e.g., formal instead of written)

**Solution**: Override with `--meeting-type` flag:
```bash
/fda-tools:presub DQY --project my_device \
  --meeting-type written \
  --device-description "..." \
  --intended-use "..."
```

### Missing Questions

**Problem**: Expected questions not selected (e.g., biocompatibility questions for patient-contacting device)

**Solution**: Check device description includes trigger keywords:
```bash
# BAD (no triggers):
--device-description "Catheter"

# GOOD (triggers sterile_device + patient_contacting):
--device-description "Sterile catheter with patient contact during use"
```

## Advanced Usage

### Custom Question Bank

Edit `data/question_banks/presub_questions.json` to add custom questions:

```json
{
  "id": "CUSTOM-001",
  "category": "custom_category",
  "priority": 80,
  "text": "Your custom question text here",
  "applicable_meeting_types": ["formal", "written"],
  "required_data": [],
  "auto_populate": false,
  "rationale": "Why this question matters",
  "fda_guidance": "Applicable FDA guidance"
}
```

### Batch PreSTAR Generation

Generate PreSTAR for multiple projects:

```bash
for PROJECT in catheter_a catheter_b catheter_c; do
  /fda-tools:presub DQY --project $PROJECT
done
```

### Integration with Testing Workflow

1. Run research and review:
   ```bash
   /fda-tools:research --product-code DQY --years 2024 --project my_device
   /fda-tools:review
   ```

2. Generate testing plan:
   ```bash
   /fda-tools:test-plan
   ```

3. Generate Pre-Sub with enriched data:
   ```bash
   /fda-tools:presub DQY --project my_device
   ```

4. PreSTAR XML now includes:
   - Accepted predicates from review.json
   - Testing strategy from guidance_cache
   - Standards from standards_lookup.json

## Related Documentation

- [CHANGELOG.md](../CHANGELOG.md) - v5.25.0 release notes
- [README.md](../README.md) - Plugin overview and command reference
- [estar-workflow.md](estar-workflow.md) - eSTAR XML generation guide
- FDA Resources:
  - [Pre-Submission Program Guidance](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/requests-feedback-and-meetings-medical-device-submissions-q-submission-program)
  - [eSTAR Forms](https://www.fda.gov/medical-devices/premarket-submissions/electronic-submission-template-and-resource-estar)
  - [FDA Form 5064 (PreSTAR)](https://www.fda.gov/about-fda/reports/forms-fda)

## Support

Issues or questions? File an issue at: https://github.com/andrewlasiter/fda-predicate-assistant/issues
