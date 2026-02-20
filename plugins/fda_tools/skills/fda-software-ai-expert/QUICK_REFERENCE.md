# FDA Software/AI Expert - Quick Reference

## When to Use This Expert

**Primary Use Cases:**
- Software validation assessment (IEC 62304 compliance)
- AI/ML algorithm transparency and bias evaluation
- Cybersecurity documentation review (FDA 2023 Premarket Guidance)
- V&V protocol and Requirements Traceability Matrix (RTM) review
- Test coverage analysis and gap identification
- PCCP (Predetermined Change Control Plan) development for adaptive algorithms
- SBOM (Software Bill of Materials) generation and CVE assessment
- OTS (Off-the-Shelf) software validation per GAMP 5
- Clinical decision support software evaluation

**Priority Issues Addressed:**
- FDA-29: Software validation gaps
- FDA-28: AI/ML algorithm transparency and bias
- FDA-22: Cybersecurity documentation
- FDA-26: Clinical decision support software
- FDA-25: OTS software validation
- FDA-58: PCCP for continuous learning algorithms

## Expert Profile at a Glance

**Dr. Michael Torres, PhD, RAC**
- **FDA**: 15 years, CDRH Digital Health Center of Excellence
- **Industry**: 12 years SaMD, AI/ML, clinical decision support
- **Submissions Reviewed**: 250+ SaMD (510(k), De Novo, PMA)
- **Cybersecurity Assessments**: 80+ vulnerability assessments
- **FDA 483s Issued**: 60+ for software validation deficiencies

**Key Expertise:**
- IEC 62304 medical device software lifecycle
- AI/ML SaMD and PCCP development
- FDA 2023 Cybersecurity Premarket Guidance
- Algorithmic bias mitigation and fairness
- Software Bill of Materials (SBOM)
- Threat modeling and penetration testing

## Key Workflows (7 Total)

### 1. Software Lifecycle Assessment (IEC 62304)
- Safety classification (Class A/B/C)
- Software Development Plan (SDP)
- Software Requirements Specification (SRS)
- Architecture and detailed design
- V&V protocols and traceability

### 2. AI/ML Algorithm Transparency
- Training data bias assessment
- Performance stratification by demographics
- Algorithm explainability (SHAP, LIME, Grad-CAM)
- PCCP for continuous learning algorithms
- Clinical decision support validation

### 3. Cybersecurity Assessment (FDA 2023)
- SBOM generation (CycloneDX, SPDX)
- Threat modeling (STRIDE)
- Vulnerability assessment (CVE remediation)
- Penetration testing review
- Coordinated disclosure policy

### 4. V&V Completeness Review
- Requirements Traceability Matrix (RTM)
- Test coverage analysis (≥80% Class B, ≥85% Class C)
- Verification independence
- Edge case and error handling testing

### 5. OTS Software Validation
- SOUP identification per IEC 62304
- GAMP 5 validation approach
- Open-source license compliance
- OTS version control

### 6. Software Change Control
- Impact analysis per 21 CFR 820.30(i)
- Regression testing
- Version control and configuration management

### 7. Software Problem Resolution
- Problem reporting and tracking
- Trend analysis for systemic issues
- Maintenance planning

## Common Critical Deficiencies (Top 10)

1. **SBOM Missing** - FDA 2023 requirement for networked devices
2. **Training Data Bias Not Assessed** - AI/ML performance not stratified by demographics
3. **Incomplete RTM** - Requirements not traceable to tests
4. **Test Coverage <80%** - Insufficient for Class B/C software
5. **OTS Software Not Validated** - Libraries/frameworks without GAMP 5 validation
6. **No PCCP for Continuous Learning** - Adaptive algorithms require FDA-cleared change control
7. **Known CVEs Not Remediated** - Critical/High vulnerabilities in SBOM components
8. **V&V Not Independent** - Developers performing own validation
9. **No Penetration Testing** - Networked devices without security assessment
10. **Unencrypted PHI** - Patient data without AES/TLS encryption

## Scoring System

**Software Validation Readiness Score: X/100**
- IEC 62304 lifecycle: X/25
- V&V completeness: X/25
- AI/ML transparency: X/15 (N/A if not AI/ML)
- Cybersecurity: X/20
- OTS validation: X/10
- Change control: X/5

**Readiness Thresholds:**
- **≥85**: Ready for submission (minor gaps only)
- **70-84**: Nearly ready (address MAJOR deficiencies)
- **50-69**: Not ready (CRITICAL gaps exist)
- **<50**: Significant rework required

## Output Format

**Standard Assessment Includes:**
- Device Software Summary (type, IEC 62304 class, AI/ML characteristics)
- Lifecycle compliance status
- V&V assessment with test coverage metrics
- AI/ML transparency and bias evaluation (if applicable)
- Cybersecurity assessment with CVE count
- OTS validation status
- Deficiency summary (CRITICAL/MAJOR/MINOR)
- RTA risk assessment
- Prioritized corrective actions with timelines
- Software Validation Readiness Score

## Key FDA Guidance Documents

**Must-Know 2023 Guidance:**
- Content of Premarket Submissions for Device Software Functions (2023)
- Cybersecurity in Medical Devices: Premarket Submissions (2023)
- PCCP for AI/ML-Enabled Device Software Functions (2023)
- Clinical Decision Support Software (2022)

**Classic Guidance (Still Valid):**
- General Principles of Software Validation (2002)
- Off-The-Shelf Software Use in Medical Devices (1999)

## Standards Framework

**Core Standards:**
- **IEC 62304:2015** - Medical device software lifecycle (Class A/B/C)
- **IEC 82304-1:2016** - Health software product safety
- **ISO 14971:2019** - Risk management for medical devices
- **IEC 62366-1:2015** - Usability engineering

**Cybersecurity Standards:**
- **IEC 62443** - Industrial cybersecurity
- **AAMI TIR57** - Medical device security principles
- **NIST Cybersecurity Framework**
- **OWASP Top 10** - Web/mobile app security

**OTS Validation:**
- **GAMP 5** - Good Automated Manufacturing Practice

## Example Scenarios

### Scenario 1: AI/ML Diagnostic Algorithm
**Issue**: Diabetic retinopathy screening algorithm, 75% white patients in training data, no bias assessment
**Output**: CRITICAL - Training data bias, performance not stratified by race/ethnicity (FDA expects demographic analysis)
**Action**: Re-analyze test set by demographics, document disparities or augment training data (4 weeks)

### Scenario 2: Continuous Learning Algorithm
**Issue**: Sepsis prediction with online learning, no PCCP
**Output**: CRITICAL - Continuous learning requires PCCP per FDA 2023 guidance (violates 21 CFR 820.30(i))
**Action**: Develop PCCP with SPS + ACP, submit before 510(k) (12 weeks)

### Scenario 3: Networked Device
**Issue**: Cloud-connected CGM without SBOM
**Output**: CRITICAL - SBOM mandatory for networked devices (FDA 2023)
**Action**: Generate SBOM in CycloneDX format, remediate Critical/High CVEs (2-4 weeks)

## Integration with Other Experts

**Complement with:**
- **fda-quality-expert** - For broader QMS review (21 CFR 820, ISO 13485)
- **fda-safety-signal-triage** - For post-market surveillance data integration
- **fda-predicate-assessment** - For software SE comparison in 510(k)s

**Software Expert Focuses On:**
- IEC 62304 lifecycle compliance (Quality expert covers broader 21 CFR 820)
- AI/ML transparency and bias (Quality expert covers general risk management)
- Cybersecurity specifics (Quality expert covers Part 11 electronic records)
- SBOM and CVE management (Quality expert covers supplier audits)

## Tips for Best Results

**For AI/ML Reviews:**
- Provide training dataset demographics
- Share algorithm performance metrics (sensitivity, specificity by subgroup)
- Include model architecture and explainability methods

**For Cybersecurity:**
- Share existing SBOM or list of OTS components
- Provide penetration test reports if available
- List known CVEs and remediation status

**For V&V:**
- Provide RTM or requirements → test traceability
- Share test coverage reports (statement, branch, path)
- Include V&V protocol and test results

**For PCCP Development:**
- Define SaMD Pre-Specifications (SPS) - what changes are anticipated
- Describe Algorithm Change Protocol (ACP) - how updates will be validated
- Establish performance guardrails and rollback criteria

## Contact & Resources

**Expert Invocation:**
```
@fda-software-ai-expert Please review our [SaMD/AI-ML/cybersecurity] documentation for [510(k)/De Novo/PMA] submission readiness.

Device: [Name]
Software Type: [SaMD/Embedded/Mobile App]
IEC 62304 Class: [A/B/C]
AI/ML: [Yes - Locked/Continuous Learning / No]
Focus Areas: [V&V/Bias/Cybersecurity/OTS/PCCP]
```

**Learn More:**
- FDA Digital Health Center of Excellence: https://www.fda.gov/medical-devices/digital-health-center-excellence
- IEC 62304 Standard: https://www.iso.org/standard/38421.html
- FDA AI/ML Action Plan: https://www.fda.gov/medical-devices/software-medical-device-samd/artificial-intelligence-and-machine-learning-aiml-enabled-medical-devices

---

**Version:** 1.0.0
**Last Updated:** 2026-02-16
**Regulatory Framework:** FDA 2023 Guidance, IEC 62304:2015, ISO 14971:2019
