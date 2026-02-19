# FDA Regulatory Workflow Examples

Comprehensive guide to using the Universal Multi-Agent Orchestrator for FDA medical device regulatory work, including 510(k) submissions, PMA reviews, MAUDE safety analysis, and clinical trial protocol reviews.

## Table of Contents

1. [510(k) Submission Review](#510k-submission-review)
2. [PMA Application Review](#pma-application-review)
3. [MAUDE Safety Analysis](#maude-safety-analysis)
4. [Clinical Trial Protocol Review](#clinical-trial-protocol-review)
5. [Regulatory Compliance Audit](#regulatory-compliance-audit)
6. [Predicate Device Analysis](#predicate-device-analysis)
7. [Standards Compliance Review](#standards-compliance-review)
8. [Risk Management Review](#risk-management-review)

---

## 510(k) Submission Review

Comprehensive review of a Traditional 510(k) submission package to identify gaps, deficiencies, and regulatory risks before FDA filing.

### Scenario
You've drafted a 510(k) submission for a cardiovascular diagnostic catheter (Product Code: DQY) and need comprehensive review before filing with FDA.

### Files to Review
- `device_profile.json` - Device specifications and indications
- `review.json` - Predicate selection and scoring
- `se_comparison.md` - Substantial equivalence table
- `estar/` - All 18 submission sections
- `estar.xml` - eSTAR form data

### Command

```bash
cd ~/fda-510k-data/projects/dqy_cardioflow/

python3 $FDA_PLUGIN_ROOT/scripts/universal_orchestrator.py execute \
  --task "Comprehensive 510(k) pre-submission review for Traditional 510(k) clearance - cardiovascular diagnostic catheter (DQY). Identify RTA deficiencies, SE comparison gaps, missing testing, and regulatory risks." \
  --files "device_profile.json,review.json,se_comparison.md,estar/01_Cover_Letter.md,estar/04_Indications_for_Use.md,estar/05_510k_Summary.md,estar/06_SE_Discussion.md,estar/09_Substantial_Equivalence_Data.md,estar/13_Performance_Testing.md,estar/14_Biocompatibility.md,estar/15_Sterility.md,estar/16_Shelf_Life.md" \
  --create-linear \
  --max-agents 12
```

### Expected Agent Team

**Core Agents (3):**
- `fda-quality-expert` (Delegate) - RTA validation, consistency checks
- `fda-510k-expert` (Assignee) - SE comparison, predicate analysis
- `voltagent-qa-sec:code-reviewer` - Data quality validation

**Specialist Agents (9):**
- `fda-biocompatibility-expert` - ISO 10993 compliance review
- `fda-sterility-expert` - ISO 11135/11137 validation review
- `fda-testing-expert` - Performance testing gap analysis
- `fda-software-ai-expert` - Software section review (if SaMD)
- `fda-clinical-expert` - Clinical data requirements
- `fda-labeling-expert` - IFU and labeling review
- `python-pro` - Data file structure validation
- `documentation-engineer` - Section completeness review
- `compliance-auditor` - 21 CFR 807.87 compliance

### Expected Findings

**CRITICAL (2-4 findings):**
- RTA-03: Form 3881 (Truthful and Accuracy Statement) missing standalone PDF
- Consistency Check #14: Brand name mismatch between IFU and device description
- Shelf life evidence: No accelerated aging data (ASTM F1980)
- Predicate PDF: K123456 summary unavailable (eSTAR extraction failed)

**HIGH (4-6 findings):**
- SE comparison: Missing reprocessing compatibility row
- Performance testing: Biocompatibility ISO 10993-5 data incomplete
- Sterilization: EO validation only mentions ISO 11135, missing cycle parameters
- IFU: TODO placeholders in contraindications section

**MEDIUM (6-10 findings):**
- Standards: ISO 10993-1:2018 listed but Declaration of Conformity table missing this standard
- Device description: Materials composition percentages not specified
- Compatible equipment: MRI compatibility not addressed
- Labeling: Storage conditions missing from IFU

**LOW (5-8 findings):**
- Minor formatting inconsistencies in section headings
- Page number references outdated
- Table of contents needs regeneration

### Linear Issues Created

```
✅ Created 18 Linear issues for 510(k) submission:

CRITICAL (3):
  FDA-102 [RTA] Form 3881 Missing Standalone PDF
  FDA-103 [CONSISTENCY] Brand Name Mismatch: IFU vs Device Description
  FDA-104 [SHELF LIFE] No ASTM F1980 Accelerated Aging Data

HIGH (5):
  FDA-105 [SE COMPARISON] Missing Reprocessing Compatibility Row
  FDA-106 [BIOCOMPATIBILITY] ISO 10993-5 Data Incomplete
  FDA-107 [STERILIZATION] EO Cycle Parameters Not Specified
  FDA-108 [IFU] TODO Placeholders in Contraindications
  FDA-109 [PREDICATE] K123456 PDF Unavailable for eSTAR Extraction

MEDIUM (7):
  FDA-110 [STANDARDS] ISO 10993-1:2018 Missing from DoC Table
  FDA-111 [DEVICE DESCRIPTION] Materials Percentages Not Specified
  FDA-112 [COMPATIBLE EQUIPMENT] MRI Compatibility Not Addressed
  FDA-113 [LABELING] Storage Conditions Missing from IFU
  FDA-114 [PERFORMANCE TESTING] Sterility validation incomplete
  FDA-115 [CONSISTENCY] Section cross-references broken
  FDA-116 [RTA] Comparative table formatting issues

LOW (3):
  FDA-117 [FORMATTING] Section heading inconsistencies
  FDA-118 [DOCUMENTATION] Page references outdated
  FDA-119 [TOC] Table of contents needs regeneration
```

### Recommended Actions

**Before Filing (CRITICAL):**
1. Generate Form 3881 standalone PDF (RTA requirement)
2. Fix brand name inconsistency across all sections
3. Conduct ASTM F1980 accelerated aging study (3 months minimum)
4. Download missing predicate PDFs or use alternate predicates

**High Priority (Within 1 Week):**
5. Add reprocessing compatibility row to SE table
6. Complete ISO 10993-5 cytotoxicity testing
7. Document EO sterilization cycle parameters
8. Replace all TODO placeholders in IFU

**Medium Priority (Within 2 Weeks):**
9. Update Declaration of Conformity table with all standards
10. Specify materials composition percentages
11. Address MRI compatibility or add contraindication
12. Add storage/handling conditions to IFU

---

## PMA Application Review

Comprehensive review of a PMA (Premarket Approval) application for a Class III cardiac valve replacement device.

### Scenario
You're finalizing a PMA application for a transcatheter aortic valve replacement (TAVR) device and need multi-disciplinary expert review.

### Files to Review
- `pma_application.pdf` - Complete PMA narrative
- `clinical_data/` - Clinical trial results (IDE study data)
- `manufacturing/` - Manufacturing processes and validation
- `device_master_file/` - Complete DMF documentation
- `risk_analysis/` - ISO 14971 risk management file

### Command

```bash
cd ~/fda-pma-data/projects/tavr_valve/

python3 $FDA_PLUGIN_ROOT/scripts/universal_orchestrator.py execute \
  --task "PMA pre-submission review for transcatheter aortic valve (TAVR) - Class III cardiac device. Focus on clinical data adequacy, manufacturing validation, risk management, and 21 CFR 814 compliance." \
  --files "pma_application.pdf,clinical_data/pivotal_trial_results.pdf,manufacturing/process_validation.pdf,risk_analysis/iso14971_fmea.xlsx" \
  --create-linear \
  --max-agents 15
```

### Expected Agent Team

**Core FDA Experts (5):**
- `fda-pma-expert` (Delegate) - PMA pathway compliance
- `fda-clinical-expert` (Assignee) - Clinical data review
- `fda-quality-expert` - Manufacturing compliance (21 CFR 820)
- `fda-risk-expert` - ISO 14971 risk management
- `fda-biocompatibility-expert` - Biocompatibility assessment

**Specialist Agents (10):**
- `fda-cardiovascular-expert` - Cardiac device-specific review
- `fda-testing-expert` - Bench and animal testing
- `fda-statistical-expert` - Clinical trial statistics
- `fda-manufacturing-expert` - Process validation review
- `data-scientist` - Clinical endpoint analysis
- `compliance-auditor` - 21 CFR 814.20 compliance
- `technical-writer` - PMA narrative quality review
- `risk-manager` - FMEA completeness review
- `qa-expert` - QMS documentation review
- `documentation-engineer` - Module organization review

### Expected Findings

**CRITICAL (PMA-specific):**
- Clinical trial primary endpoint: Non-inferiority margin not pre-specified in protocol
- Manufacturing validation: Sterilization validation study incomplete (no bioburden data)
- Risk management: Residual risks not adequately mitigated (high-severity hazards remain)
- Labeling: Contraindications missing documented clinical justification

**HIGH:**
- Clinical data: Follow-up data only 12 months (FDA expects 24+ months for TAVR)
- Manufacturing: Supplier qualification incomplete for 2 critical components
- Biocompatibility: ISO 10993-4 hemocompatibility data from alternate device, not actual TAVR valve
- Shelf life: Real-time aging only 6 months (claimed 24-month shelf life)

---

## MAUDE Safety Analysis

Analyze adverse events from FDA MAUDE database for predicate devices to assess safety profile and identify potential risks.

### Scenario
You're comparing safety profiles of 3 predicate devices for your cardiovascular catheter to demonstrate acceptable risk.

### Command

```bash
python3 $FDA_PLUGIN_ROOT/scripts/universal_orchestrator.py execute \
  --task "MAUDE adverse event analysis for cardiovascular diagnostic catheters (DQY) - Compare event rates, serious injury patterns, and recall history across 3 predicates (K123456, K234567, K345678). Identify safety signals and risk mitigation strategies." \
  --files "$FDA_DATA_ROOT/safety_cache/maude_K123456.json,$FDA_DATA_ROOT/safety_cache/maude_K234567.json,$FDA_DATA_ROOT/safety_cache/maude_K345678.json,$FDA_DATA_ROOT/safety_cache/recalls_DQY.json" \
  --create-linear \
  --max-agents 8
```

### Expected Agent Team

**FDA Safety Experts (4):**
- `fda-safety-expert` (Delegate) - MAUDE data interpretation
- `fda-risk-expert` (Assignee) - Risk-benefit analysis
- `fda-post-market-expert` - Post-market surveillance trends
- `fda-biocompatibility-expert` - Biological safety event analysis

**Data & Regulatory (4):**
- `data-analyst` - Statistical event rate analysis
- `voltagent-qa-sec:penetration-tester` - Data validation and anomaly detection
- `research-analyst` - Literature correlation with events
- `compliance-auditor` - MDR reporting compliance review

### Expected Findings

**Event Rate Analysis:**
- K123456: 12 events/year (6 serious injuries, 0 deaths)
- K234567: 8 events/year (3 serious injuries, 1 death)
- K345678: 15 events/year (10 serious injuries, 2 deaths)

**Common Event Types:**
- Device fracture during use (30% of events)
- Thrombosis at insertion site (25% of events)
- Contrast media leakage (20% of events)
- Allergic reaction to coating material (15% of events)
- Other (10%)

**Safety Signals Identified:**
1. K345678 has 2x higher serious injury rate than peers
2. All 3 predicates show device fracture events (design-related)
3. Thrombosis events correlate with extended dwell time >4 hours
4. Coating material reactions increasing year-over-year

**Recommended Risk Mitigation:**
- Add IFU warning about maximum dwell time (4 hours)
- Strengthen catheter shaft to reduce fracture risk
- Add allergy screening questionnaire to patient selection criteria
- Implement post-market surveillance plan for coating reactions

---

## Clinical Trial Protocol Review

Review a clinical trial protocol for IDE (Investigational Device Exemption) submission to FDA.

### Scenario
You're submitting an IDE application for a first-in-human study of a novel neurostimulation device.

### Command

```bash
cd ~/fda-ide-data/protocols/neurostim_001/

python3 $FDA_PLUGIN_ROOT/scripts/universal_orchestrator.py execute \
  --task "IDE clinical trial protocol review for neurostimulation device - Evaluate study design, endpoint selection, patient safety protections, statistical power, and 21 CFR 812 compliance." \
  --files "protocol_v2.0.pdf,informed_consent_v1.5.pdf,investigator_brochure.pdf,statistical_analysis_plan.pdf" \
  --create-linear \
  --max-agents 10
```

### Expected Agent Team

**FDA Clinical Experts (5):**
- `fda-clinical-expert` (Delegate) - IDE pathway compliance
- `fda-statistical-expert` (Assignee) - Statistical design review
- `fda-neurology-expert` - Device-specific clinical review
- `fda-risk-expert` - Patient safety assessment
- `fda-ide-expert` - 21 CFR 812 compliance

**Clinical & Research (5):**
- `clinical-trials-researcher` - Protocol design best practices
- `data-scientist` - Sample size and power analysis
- `biostatistician` - SAP adequacy review
- `ux-researcher` - Informed consent readability
- `compliance-auditor` - IRB submission requirements

### Expected Findings

**Protocol Design:**
- Primary endpoint appropriate (pain reduction VAS score)
- Sample size underpowered (n=20, need n=40 for 80% power)
- Follow-up duration too short (3 months, recommend 12 months)
- No stopping rules defined for safety events

**Patient Safety:**
- Inclusion criteria too broad (missing MRI contraindication exclusion)
- Adverse event reporting timeline not specified (FDA requires 10 working days)
- Device explantation procedure not described
- No Data Safety Monitoring Board (DSMB) planned

**21 CFR 812 Compliance:**
- Informed consent missing device risks (infection, lead migration)
- Investigator qualifications not documented
- Monitoring plan inadequate (only 1 site visit planned)

---

## Regulatory Compliance Audit

Comprehensive compliance audit of FDA submission data files and scripts for regulatory integrity.

### Command

```bash
cd $FDA_PLUGIN_ROOT

python3 scripts/universal_orchestrator.py execute \
  --task "Regulatory compliance audit of FDA plugin - Validate 21 CFR compliance, data integrity, API usage, and quality system adherence across all 68 commands and 30+ scripts." \
  --files "commands/*.md,scripts/*.py,lib/*.py,tests/test_*.py" \
  --create-linear \
  --max-agents 12
```

### Expected Agent Team

**Regulatory & QA (6):**
- `fda-quality-expert` (Delegate) - QMS compliance
- `compliance-auditor` (Assignee) - 21 CFR 11 (electronic records)
- `fda-cybersecurity-expert` - Data security and API key handling
- `qa-expert` - Test coverage and validation
- `fda-documentation-expert` - Documentation completeness
- `fda-risk-expert` - Risk analysis of plugin failures

**Technical (6):**
- `security-auditor` - Security vulnerability assessment
- `penetration-tester` - Input validation and injection risks
- `python-pro` - Code quality and best practices
- `test-automator` - Test automation adequacy
- `voltagent-dev-exp:refactoring-specialist` - Code maintainability
- `documentation-engineer` - User documentation quality

### Expected Findings

**21 CFR 11 Compliance:**
- Audit trail: Partial (command execution logged, but data modifications not tracked)
- Electronic signatures: Not implemented (N/A for research tool)
- Data integrity: Good (JSON schema validation, checksums)
- Access controls: Adequate (file system permissions)

**Security:**
- API key exposure: Low risk (environment variables used)
- Input validation: Needs improvement (some SQL injection risks)
- Rate limiting: Implemented (100 calls/min)
- Encryption: None (local file system only)

**Quality System:**
- Test coverage: 98% (722 tests passing)
- Documentation: 85% complete (some commands missing examples)
- Change control: Good (Git version control)
- Traceability: Adequate (requirements → tests mapping)

---

## Predicate Device Analysis

Analyze predicate device suitability for substantial equivalence claims.

### Command

```bash
python3 $FDA_PLUGIN_ROOT/scripts/universal_orchestrator.py execute \
  --task "Predicate device analysis for 510(k) SE comparison - Evaluate technical similarity, indications overlap, materials equivalence, and performance testing comparability for 5 candidate predicates." \
  --files "review.json,se_comparison.md,device_profile.json,predicates/*/extracted_sections.json" \
  --create-linear \
  --max-agents 8
```

### Expected Findings

**Predicate Ranking:**
1. K234567 (Score: 92/100) - Identical materials, similar indications
2. K123456 (Score: 85/100) - Same product code, minor design differences
3. K456789 (Score: 78/100) - Broader indications, acceptable
4. K567890 (Score: 65/100) - Different sterilization method, risky
5. K678901 (Score: 52/100) - Insufficient technical data, reject

**Gap Analysis:**
- Predicate K234567 missing shelf life data (need to request from manufacturer)
- Predicate K123456 has 3 recalls (need to justify acceptability)
- Predicate K456789 uses outdated standard (ISO 10993:2009 vs 2018)

---

## Standards Compliance Review

Review compliance with FDA-recognized consensus standards.

### Command

```bash
python3 $FDA_PLUGIN_ROOT/scripts/universal_orchestrator.py execute \
  --task "FDA consensus standards compliance review - Validate testing completeness and Declaration of Conformity accuracy for 12 applicable standards (ISO 10993, IEC 60601, ISO 11135, etc.)." \
  --files "standards_lookup.json,estar/14_Biocompatibility.md,estar/13_Performance_Testing.md,estar/17_Declaration_of_Conformity.md" \
  --create-linear \
  --max-agents 6
```

### Expected Findings

**Standards Compliance:**
- ISO 10993-1:2018 - PASS (biocompatibility evaluation plan complete)
- ISO 10993-5:2009 - FAIL (cytotoxicity test report missing)
- IEC 60601-1:2012 - PASS (electrical safety testing complete)
- ISO 11135:2014 - PARTIAL (EO validation incomplete)

**Declaration of Conformity:**
- 3 standards listed in DoC but missing from testing sections
- 2 standards tested but missing from DoC table
- Standard version mismatch: ISO 10993-5:2009 tested, but 2018 version is current

---

## Risk Management Review

Review ISO 14971 risk management file for completeness and adequacy.

### Command

```bash
python3 $FDA_PLUGIN_ROOT/scripts/universal_orchestrator.py execute \
  --task "ISO 14971 risk management review - Validate hazard analysis completeness, risk control adequacy, residual risk acceptability, and post-market surveillance plan." \
  --files "risk_analysis/fmea.xlsx,risk_analysis/hazard_analysis.pdf,risk_analysis/risk_management_report.pdf" \
  --create-linear \
  --max-agents 8
```

### Expected Findings

**FMEA Completeness:**
- 47 hazards identified (typical: 60-80 for Class II device)
- Risk Priority Numbers (RPN): 3 HIGH (>200), 12 MEDIUM (100-200), 32 LOW (<100)
- Missing hazards: Software failure modes, human factors errors

**Risk Control:**
- 42/47 hazards have risk controls implemented
- 5 hazards rely on IFU warnings only (weak control)
- No residual risk re-evaluation after controls applied

**Post-Market:**
- Post-market surveillance plan missing
- Complaint handling procedure not referenced
- CAPA (Corrective and Preventive Action) triggers not defined

---

## Summary

The Universal Multi-Agent Orchestrator provides comprehensive, multi-expert review for all stages of FDA regulatory work:

- **510(k) Submissions**: RTA validation, SE comparison, consistency checks
- **PMA Applications**: Clinical data review, manufacturing validation, risk assessment
- **Safety Analysis**: MAUDE event analysis, recall correlation, risk-benefit evaluation
- **Clinical Trials**: Protocol design review, statistical adequacy, patient safety
- **Compliance Audits**: 21 CFR compliance, data integrity, quality systems
- **Predicate Analysis**: Technical similarity, SE justification, gap identification
- **Standards Review**: Testing completeness, DoC accuracy, version currency
- **Risk Management**: ISO 14971 compliance, hazard analysis, risk control adequacy

**Key Benefits:**
- **Multi-dimensional review** from 8-15 specialized FDA and technical experts
- **Automated issue creation** in Linear with agent assignments
- **Prioritized findings** (CRITICAL → LOW) for efficient remediation
- **Regulatory intelligence** from 167-agent knowledge base
- **Comprehensive coverage** across all FDA submission types

---

**Last Updated:** 2026-02-19
**Version:** 1.0.0
