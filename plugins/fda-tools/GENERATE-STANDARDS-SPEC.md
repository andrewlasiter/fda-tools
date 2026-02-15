# Generate-Standards Command Specification

**Version:** 5.26.0
**Date:** 2026-02-15
**Purpose:** Knowledge-Based FDA Recognized Consensus Standards Generation

---

## ⚠️ IMPORTANT DISCLAIMER

**RESEARCH USE ONLY - NOT PRODUCTION-READY**

This tool is approved for **research and regulatory planning only**. It is **NOT approved for direct FDA submission use** without independent verification by qualified regulatory affairs professionals.

**Key Limitations:**
- Standards determinations use keyword matching and rule-based logic, not AI/ML
- Accuracy has NOT been independently validated across all device types
- Database contains 54 standards (3.5% of ~1,900 FDA-recognized standards)
- Does NOT analyze actual 510(k) predicate clearance patterns
- Requires expert review and verification before use in submissions

**User Responsibility:** All output must be independently verified against current FDA guidance, recognized standards databases, and cleared predicates before inclusion in regulatory submissions.

---

## Executive Summary

The `/fda-tools:generate-standards` command uses knowledge-based analysis to identify potentially applicable FDA Recognized Consensus Standards for medical device product codes. It processes device classification data and generates structured standards determinations with regulatory justification based on embedded rules and patterns.

---

## What It Does

### Core Functionality

**Input:** FDA product codes (specific codes, top N by volume, or all ~7000 codes)

**Process:**
1. Retrieves device classification from FDA database (class, regulation, device name)
2. Analyzes device characteristics (contact type, power source, software, sterilization)
3. Applies knowledge-based standards determination logic using pattern matching rules
4. Generates structured JSON output with standards list and reasoning
5. Validates output through multi-agent quality framework

**Output:**
- Individual JSON files per product code with standards determinations
- HTML validation reports with coverage and quality metrics
- Markdown summaries with regulatory context

### Key Capabilities

1. **Knowledge-Based Analysis**
   - Autonomous agent analyzes device characteristics using rule-based logic
   - Identifies potentially applicable standards based on embedded regulatory knowledge
   - Provides reasoning for each standard determination

2. **Flexible Scope**
   - Process specific product codes: `DQY OVE GEI`
   - Process top N high-volume codes: `--top 100`
   - Process all FDA codes: `--all` (~7000 codes, 4-6 hours)

3. **Resilient Processing**
   - Checkpoint every 10 codes for resume capability
   - Exponential backoff retry (3 attempts: 2s, 4s, 8s delays)
   - Auto-resume on restart if checkpoint exists
   - Force restart option: `--force-restart`

4. **Multi-Agent Validation**
   - Coverage auditor: Ensures ≥99.5% weighted coverage threshold
   - Quality reviewer: Validates ≥95% appropriateness of determinations
   - Consensus framework: Cross-validates agent outputs

5. **Progress Tracking**
   - Real-time progress display (X/Y codes, Z% complete)
   - Live ETA calculation based on processing rate
   - Category breakdown every 50 codes
   - Summary statistics at completion

6. **External Standards Database**
   - 54 FDA Recognized Consensus Standards
   - 10 regulatory categories (biocompatibility, electrical, sterilization, etc.)
   - User customization support for proprietary standards
   - Versioned database (1.0.0) with update tracking

---

## Standards Knowledge Base

### Categories Covered (10)

1. **Universal** (2 standards)
   - ISO 13485:2016 - QMS
   - ISO 14971:2019 - Risk Management

2. **Biocompatibility** (4 standards)
   - ISO 10993-1, -5, -10, -11

3. **Electrical Safety** (4 standards)
   - IEC 60601-1, -1-2, -1-8, -1-11

4. **Sterilization** (5 standards)
   - ISO 11135 (EO), 11137 (Radiation), 17665 (Steam)
   - ANSI/AAMI ST72, ASTM F1980

5. **Software** (5 standards)
   - IEC 62304, 82304-1, 62366-1
   - AAMI TIR57, IEC 62443-4-1

6. **Cardiovascular** (5 standards)
   - ISO 11070, 25539-1, 5840-1, 14708-1
   - ASTM F2394

7. **Orthopedic** (6 standards)
   - ASTM F1717, F2077, F2346, F136
   - ISO 5832-3, 5833

8. **IVD Diagnostic** (5 standards)
   - ISO 18113-1, 15189
   - CLSI EP05, EP06, EP07

9. **Neurological** (3 standards)
   - IEC 60601-2-10, ISO 14708-3, ASTM F2182

10. **Surgical/Robotic/Dental** (15 standards total)
    - Surgical instruments: ISO 7153-1, 13402, AAMI ST79
    - Robotic: ISO 13482, IEC 80601-2-77
    - Dental: ISO 14801, ASTM F3332, ISO 6872

---

## Standards Determination Logic

### Device Characteristic Triggers

The system applies rule-based logic using keyword matching and device classification patterns:

**Contact-Based Triggers:**
- Patient-contacting device → ISO 10993-1 (Biocompatibility Part 1)
- Skin contact → ISO 10993-10 (Irritation/sensitization)
- Blood/tissue contact → ISO 10993-5, -11 (Cytotoxicity, systemic toxicity)
- Bone contact → Material standards (ISO 5832-3, ASTM F136)

**Power-Based Triggers:**
- Any electrical component → IEC 60601-1 (Electrical safety)
- Line-powered or battery → IEC 60601-1-2 (EMC)
- Home use electrical → IEC 60601-1-11
- Alarms → IEC 60601-1-8

**Software Triggers:**
- Embedded software → IEC 62304
- Standalone SaMD → IEC 82304-1
- User interface → IEC 62366-1
- Network connectivity → AAMI TIR57

**Sterilization Triggers:**
- Labeled "sterile" + EO → ISO 11135
- Labeled "sterile" + radiation → ISO 11137
- Labeled "sterile" + steam → ISO 17665
- Shelf life validation → ASTM F1980

**Device-Type Specific:**
- Catheter keywords → ISO 11070, ASTM F2394
- Spinal keywords → ASTM F1717, F2077
- Implant keywords → Material standards
- IVD keywords → ISO 18113-1, CLSI series

---

## Output Format

### Individual Standards JSON

```json
{
  "product_code": "DQY",
  "device_name": "Catheter, Intravascular, Therapeutic, Short-Term",
  "device_class": "II",
  "regulation_number": "21 CFR 880.5200",
  "determination_date": "2026-02-15T10:30:00Z",
  "standards": [
    {
      "number": "ISO 13485:2016",
      "title": "Medical devices - Quality management systems",
      "category": "universal",
      "applicability": "ALL medical devices",
      "confidence": "HIGH",
      "reasoning": "Required by 21 CFR 820 (QMS regulation)",
      "fda_recognized": true
    },
    {
      "number": "ISO 10993-1:2018",
      "title": "Biological evaluation - Part 1: Evaluation and testing",
      "category": "biocompatibility",
      "applicability": "Blood-contacting device",
      "confidence": "HIGH",
      "reasoning": "Device has direct blood contact (intravascular catheter)",
      "fda_recognized": true
    }
  ],
  "metadata": {
    "total_standards": 12,
    "high_confidence": 10,
    "medium_confidence": 2,
    "agent_version": "standards-ai-analyzer:1.0",
    "validation_status": "passed"
  }
}
```

### Validation Report (HTML)

- Coverage matrix: Standards coverage across all processed codes
- Quality metrics: Appropriateness scores, confidence distribution
- Category breakdown: Standards by regulatory category
- Recommendations: Suggested improvements or gaps

---

## Use Cases

### For Regulatory Affairs Professionals

**Use Case 1: New Device Development**
- Input: Single product code for new device
- Output: Initial standards list for review with regulatory justification
- Value: Starting point for standards identification requiring expert verification
- Note: Output must be verified against actual cleared predicates and current FDA guidance

**Use Case 2: Competitive Intelligence**
- Input: Top 100 product codes in target market
- Output: Standards landscape overview across device categories
- Value: Identify potential standards patterns for further investigation
- Note: Does not replace analysis of actual 510(k) summary documents

**Use Case 3: Portfolio Assessment**
- Input: All product codes in company portfolio
- Output: Cross-device standards overview for initial planning
- Value: Identify potential shared testing infrastructure needs
- Note: Requires validation against device-specific designs and requirements

**Use Case 4: Pre-Submission Planning**
- Input: Specific product code for upcoming 510(k)
- Output: Preliminary standards list for verification
- Value: Research starting point requiring predicate analysis
- Note: Must be verified against accepted predicates in same product code

---

## Limitations and Disclaimers

### What It Does NOT Do

1. **Not a Replacement for Regulatory Judgment**
   - Knowledge-based determinations require expert review
   - Standards applicability depends on specific device design
   - All determinations require verification against cleared predicates

2. **Not Legally Binding**
   - Output is for research and planning purposes only
   - FDA may require additional standards not in database
   - Final standards list must be independently verified by RA professionals

3. **Not Real-Time Updated**
   - Standards database version 1.0.0 (2026-02-15)
   - Contains 54 standards (3.5% of ~1,900 FDA-recognized standards)
   - FDA Recognized Consensus Standards list changes quarterly
   - Users must verify standards are current before submission

4. **Not Device-Specific**
   - Analyzes at product code level (hundreds of devices per code)
   - Cannot account for unique device features
   - Proprietary designs may require additional standards
   - Does not analyze actual cleared predicate standards

5. **Not a Testing Provider**
   - Identifies potentially applicable standards only
   - Does not conduct testing or validation
   - Does not generate test protocols or reports
   - Does not provide sample sizes, costs, or lead times

6. **Not Validated for Accuracy**
   - Accuracy has NOT been independently verified
   - No published validation study exists
   - Expert panel review found significant gaps in coverage
   - Requires independent verification before regulatory use

### Verification Requirements

**Before using any standards determination in a regulatory submission:**
- Cross-check against actual cleared 510(k) summaries in same product code
- Verify against current FDA Recognized Consensus Standards database
- Consult qualified regulatory affairs professionals
- Document verification in Design History File (DHF) per 21 CFR 820.30

### Regulatory Status

- **FDA Approval:** NOT FDA-cleared or approved
- **Intended Use:** Research and regulatory planning tool
- **User Responsibility:** Independent verification required before FDA submission
- **Compliance Status:** Conditional approval for research use only (per RA-6 disclaimer)

---

## Technical Architecture

### Agent System

**Primary Agent: standards-ai-analyzer**
- Analyzes device classification data
- Applies standards determination logic
- Generates JSON output with reasoning

**Validation Agent 1: standards-coverage-auditor**
- Audits standards coverage completeness
- Validates ≥99.5% weighted coverage threshold
- Identifies missing universal/critical standards

**Validation Agent 2: standards-quality-reviewer**
- Reviews standards appropriateness
- Validates ≥95% quality threshold
- Flags over-application or under-application

### Workflow

1. User invokes `/fda-tools:generate-standards [ARGS]`
2. Command enumerates product codes (specific, top N, or all)
3. For each code:
   a. Fetch classification from FDA API
   b. Launch standards-ai-analyzer agent via Task tool
   c. Agent generates JSON file
   d. Checkpoint after every 10 codes
4. At completion:
   a. Launch coverage auditor
   b. Launch quality reviewer
   c. Generate HTML validation report
5. Output summary to user

### Data Sources

- **FDA Device Classification Database** (via openFDA API)
- **FDA Recognized Consensus Standards Database** (embedded in agent knowledge)
- **External Standards Database** (data/fda_standards_database.json)

---

## Questions for Regulatory Experts

### Value Proposition

1. Does this tool address a real pain point in your regulatory workflow?
2. Would AI-generated standards determinations save meaningful time?
3. What confidence level would you need to trust the output?

### Accuracy Concerns

4. Are 95% accuracy expectations realistic for regulatory work?
5. What types of edge cases are most likely to be misclassified?
6. How would you verify AI determinations before using them?

### Practical Utility

7. Would you use this for Pre-Submission planning?
8. Would you use this for competitive intelligence?
9. Would you use this for internal portfolio assessment?

### Integration Needs

10. What additional context would make determinations more useful?
11. Should it integrate with specific standards libraries (e.g., IHS, TechStreet)?
12. Should it generate standards rationales for 510(k) sections?

### Regulatory Compliance

13. Is the disclaimer language sufficient for regulatory use?
14. Should output be marked "AI-generated" in metadata?
15. What verification workflow would you implement?

---

## Success Metrics

### If This Tool Is Valuable, You Would:

1. Use it at the start of every new device project
2. Trust it enough to skip some manual standards research
3. Share it with other RA professionals on your team
4. Recommend it to external consultants or partners
5. Pay for it if it were a commercial product

### If This Tool Is NOT Valuable, You Would:

1. Still manually research every standard
2. Not trust the AI determinations without full verification
3. Find the output format unhelpful for your workflow
4. Prefer existing commercial standards databases
5. See it as "nice to have" but not essential

---

**End of Specification**
