# Draft Templates — All 18 Submission Sections

Prose templates for generating 510(k) submission section drafts. Each section includes `[TODO:]` placeholders for company-specific information.

## Section 01: Cover Letter

```markdown
[Date]

Division of {review_panel}
Office of {office}
Center for Devices and Radiological Health
Food and Drug Administration
10903 New Hampshire Avenue
Silver Spring, MD 20993

RE: 510(k) Premarket Notification — {device_trade_name}

Dear Sir/Madam:

{applicant_name} hereby submits this premarket notification under Section 510(k) of the Federal Food, Drug, and Cosmetic Act for our {device_common_name}, classified under product code {product_code} (21 CFR {regulation_number}, Class {device_class}).

The subject device is intended for {indications_for_use}.

We believe the subject device is substantially equivalent to {predicate_k_number(s)}, {predicate_device_name(s)}.

This submission includes the following sections as required by 21 CFR 807.87:
{numbered list of included sections}

[TODO: Company-specific — Additional context about the device or submission]

Sincerely,

[TODO: Company-specific — Authorized representative name and title]
{applicant_name}
[TODO: Company-specific — Address, phone, email]
```

## Section 03: 510(k) Summary (per 21 CFR 807.92)

```markdown
## 510(k) Summary

### Submitter Information
- **Applicant:** {applicant_name}
- **Address:** [TODO: Company-specific — Full address]
- **Contact:** [TODO: Company-specific — Name, title, phone, email]
- **Date Prepared:** {date}

### Device Information
- **Trade Name:** {device_trade_name}
- **Common Name:** {device_common_name}
- **Product Code:** {product_code}
- **Classification:** Class {device_class}, 21 CFR {regulation_number}

### Predicate Device(s)
{For each predicate:}
- **{k_number}**: {device_name} ({applicant}, cleared {date})

### Device Description
{device_description_text}
[Source: import_data.json or --device-description]

### Indications for Use
{indications_for_use}
[Source: import_data.json or --intended-use]

### Substantial Equivalence Comparison
{Summary of SE comparison highlighting same intended use and technological characteristics}
[Source: se_comparison.md]

### Summary of Testing
{Performance testing summary}
[Source: test_plan.md, guidance_cache]

### Conclusion
Based on the comparison of the subject device to the predicate device(s), {applicant_name} believes the subject device is substantially equivalent as defined under Section 513(i)(1)(A) of the Federal Food, Drug, and Cosmetic Act.
```

## Section 06: Device Description

```markdown
## Device Description

### 6.1 Device Overview
{If device_description_text available:}
{device_description_text}
[Source: import_data.json or --device-description]

{If not:}
[TODO: Company-specific — Provide a complete physical description of the device including:
- General device overview and intended purpose
- Principle of operation
- Key design features and innovations]

### 6.2 Components and Accessories
[TODO: Company-specific — List all components, accessories, and ancillary devices:
- Main device unit
- Disposable/reusable components
- Required accessories
- Optional accessories]

### 6.3 Materials of Construction
[TODO: Company-specific — List all materials, especially patient-contacting:
- Patient-contacting materials (link to biocompatibility in Section 12)
- Non-contacting structural materials
- Coatings, adhesives, or surface treatments]

### 6.4 Principle of Operation
{If principle_of_operation available:}
{principle_of_operation}
[Source: import_data.json]

{If not:}
[TODO: Company-specific — Describe how the device works:
- Sensing/therapeutic mechanism
- Energy source (if applicable)
- Software control (if applicable)]

### 6.5 Illustrations
[TODO: Company-specific — Include:
- Device photographs (multiple angles)
- Annotated diagrams
- Cross-sectional views (if relevant)
- Packaging images]
```

## Section 07: SE Discussion

```markdown
## Substantial Equivalence Discussion

### 7.1 Predicate Selection
{If predicates available from review.json:}
The primary predicate device is {predicate_k_number} ({predicate_device_name}, {predicate_applicant}, cleared {predicate_date}).
[Source: review.json]

{If not:}
[TODO: Company-specific — Identify predicate device(s) with K-number, device name, applicant, and clearance date]

### 7.2 Intended Use Comparison
{If indications_for_use available:}
| Aspect | Subject Device | Predicate Device |
|--------|---------------|-----------------|
| Intended use | {subject_ifu} | {predicate_ifu} |
| Target population | {subject_pop} | {predicate_pop} |
| Clinical indication | {subject_indication} | {predicate_indication} |
| Use environment | {subject_env} | {predicate_env} |

[Source: import_data.json, predicate PDF]

{If not:}
[TODO: Company-specific — Side-by-side comparison of intended use statements]

### 7.3 Technological Characteristics Comparison
{Auto-populate from se_comparison.md if available:}
{se_comparison_table}
[Source: se_comparison.md]

{If not:}
[TODO: Company-specific — Compare technological characteristics:
- Physical dimensions and form factor
- Materials of construction
- Energy source and power
- Software/firmware
- Delivery mechanism
- Performance specifications]

### 7.4 Discussion of Differences
[TODO: Company-specific — For each identified difference:
- Describe the difference
- Explain why it does not raise new questions of safety and effectiveness
- Reference testing that addresses the difference (link to Section 15)]

### 7.5 Conclusion
Based on the above comparison, {applicant_name} believes that the subject device has the same intended use and similar technological characteristics as the predicate device. Identified differences do not raise new questions of safety and effectiveness, as demonstrated by the performance testing described in Section 15.
```

## Section 09: Labeling

```markdown
## Labeling

### 9.1 Package Label
[TODO: Company-specific — Provide the proposed package label including:
- Device name (trade and common)
- Manufacturer name and address
- Catalog/model number
- Lot/serial number location
- Rx only symbol (if prescription)
- UDI barcode placement
- Storage conditions
- Expiration date or shelf life
- Sterilization indicator (if applicable)]

### 9.2 Instructions for Use (IFU)
{If IFU text available from import_data or --intended-use:}
**Indications for Use:**
{indications_for_use}
[Source: import_data.json]

**Contraindications:**
[TODO: Company-specific — List contraindications based on device type and clinical data]

**Warnings:**
[TODO: Company-specific — Warnings per applicable special controls and 21 CFR 801.109 (prescription device labeling)]

**Precautions:**
[TODO: Company-specific — Precautions for safe use]

**Directions for Use:**
[TODO: Company-specific — Step-by-step usage instructions]

### 9.3 Patient Labeling
[TODO: Company-specific — Patient-facing labeling if applicable (per 21 CFR Part 801)]

### 9.4 Promotional Materials
[TODO: Company-specific — Any promotional materials submitted per 21 CFR 807.87(e)]
```

## Section 10: Sterilization

```markdown
## Sterilization

### 10.1 Sterilization Method
{If sterilization_method available:}
The subject device is sterilized using {sterilization_method}.
[Source: import_data.json]

{If not:}
[TODO: Company-specific — Specify sterilization method (EO, radiation, steam, other, or "not applicable")]

### 10.2 Sterility Assurance Level (SAL)
The device is manufactured to a SAL of 10⁻⁶ per the applicable standard.
[TODO: Company-specific — Confirm SAL and validation approach]

### 10.3 Sterilization Validation
{If EO:}
Sterilization validation performed per ISO 11135 (EO sterilization).
{If radiation:}
Sterilization validation performed per ISO 11137-1:2025/-2:2013 (radiation sterilization).
{If steam:}
Sterilization validation performed per ISO 17665:2024 (moist heat sterilization).

**Validation Summary:**
[TODO: Company-specific — Summarize sterilization validation protocol and results:
- Method qualification
- Bioburden testing per ISO 11737-1
- Cycle development and validation
- Sterility testing per ISO 11737-2
- Parametric release criteria (if applicable)]

### 10.4 Residuals (EO Only)
{If EO sterilization:}
Residual EO and ECH levels comply with ISO 10993-7.
[TODO: Company-specific — Provide EO and ECH residual limits and test results]

### 10.5 Packaging Validation
Sterile barrier system validated per ISO 11607-1/-2.
[TODO: Company-specific — Summarize packaging validation:
- Seal strength testing
- Microbial barrier testing
- Distribution simulation
- Accelerated aging (linked to Section 11)]
```

## Section 11: Shelf Life

```markdown
## Shelf Life

### 11.1 Claimed Shelf Life
{If shelf_life_claim available:}
The claimed shelf life is {shelf_life_claim}.
[Source: import_data.json]

{If not:}
[TODO: Company-specific — State claimed shelf life (e.g., "2 years from date of manufacture")]

### 11.2 Aging Study Design
**Accelerated Aging:**
Accelerated aging performed per ASTM F1980 at {temperature}°C for {duration}.
[TODO: Company-specific — Specify:
- Aging temperature and Q10 factor
- Duration and equivalent real-time
- Sample sizes (n per time point)
- Acceptance criteria]

**Real-Time Aging:**
[TODO: Company-specific — Real-time aging study status:
- Start date
- Duration (must equal or exceed claimed shelf life)
- Completion date or estimated completion]

### 11.3 Testing Protocol
Post-aging testing includes:
- Package integrity (seal strength, dye penetration, or bubble leak)
- Sterility maintenance (if sterile device)
- Device functionality/performance
[TODO: Company-specific — Complete testing protocol details]

### 11.4 Results Summary
[TODO: Company-specific — Summarize aging study results:
- All acceptance criteria met? Y/N
- Any out-of-spec results? Explain
- Real-time data supporting accelerated results?]
```

## Section 12: Biocompatibility

```markdown
## Biocompatibility

### 12.1 Device Contact Classification
{If biocompat data available:}
- **Contact Type:** {biocompat_contact_type}
- **Contact Duration:** {biocompat_contact_duration}
- **Materials:** {biocompat_materials}
[Source: import_data.json]

{If not:}
[TODO: Company-specific — Classify per ISO 10993-1:2025:
- Surface device / External communicating / Implant
- Limited (<24h) / Prolonged (24h-30d) / Permanent (>30d)
- Patient-contacting materials list]

### 12.2 Biological Evaluation Plan
Per ISO 10993-1:2025 Table A.1 (or ISO 10993-1:2018 during transition period ending 2027-11-18), the following biological evaluation endpoints apply based on the device's contact type and duration:

| Endpoint | Required? | Method | Standard | Status |
|----------|-----------|--------|----------|--------|
| Cytotoxicity | Yes (all contact types) | In vitro | ISO 10993-5 | [TODO] |
| Sensitization | Yes (all contact types) | In vivo or in vitro (DPRA, KeratinoSens, h-CLAT) | ISO 10993-10 | [TODO] |
| Irritation or Intracutaneous Reactivity | Yes (all contact types) | In vivo or in vitro (EpiDerm, SkinEthic) | ISO 10993-23 | [TODO] |
| Material-Mediated Pyrogenicity | {Surface/External communicating/Implant} | In vitro (MAT or RPT) | ISO 10993-11 | [TODO] |
| Acute Systemic Toxicity | {External communicating ≥24h, Implant} | In vivo | ISO 10993-11 | [TODO] |
| Subacute/Subchronic Systemic Toxicity | {External communicating >30d, Implant >24h} | In vivo | ISO 10993-11 | [TODO] |
| Chronic Systemic Toxicity | {Implant >30d} | In vivo | ISO 10993-11 | [TODO] |
| Genotoxicity | {External communicating ≥24h, Implant} | In vitro battery (Ames, MLA/MN, chromosomal aberration) | ISO 10993-3 | [TODO] |
| Carcinogenicity | {Permanent implant >30d} | In vivo (or risk assessment) | ISO 10993-3 | [TODO] |
| Reproductive/Developmental Toxicity | {Permanent implant affecting reproductive organs} | In vivo (or risk assessment) | ISO 10993-3 | [TODO] |
| Implantation | {Implant devices} | In vivo, appropriate site | ISO 10993-6 | [TODO] |
| Hemocompatibility | {Blood-contacting devices} | Hemolysis, thrombosis, coagulation, complement, hematology | ISO 10993-4 | [TODO] |
| Degradation | {Absorbable/biodegradable devices} | In vitro and/or in vivo | ISO 10993-13, -14, -15, -16 | [TODO] |
| Chemical Characterization | Yes (all contact types) | E&L analysis (GC-MS, LC-MS, ICP-MS) | ISO 10993-18 | [TODO] |
| Toxicological Risk Assessment | Yes (all contact types) | TTC/PDE calculation from E&L data | ISO 10993-17 | [TODO] |

### 12.3 Biocompatibility Testing Summary
[TODO: Company-specific — For each test performed:
- Test lab (ISO/IEC 17025 accredited)
- Test article description
- Test method and acceptance criteria
- Results and conclusion]

### 12.4 Biocompatibility Justification
{If predicate uses same materials:}
The subject device uses the same patient-contacting materials as the predicate device ({predicate_k_number}). Per FDA guidance "Use of International Standard ISO 10993-1," a biocompatibility assessment leveraging predicate data is appropriate.
[Source: se_comparison.md materials row]

[TODO: Company-specific — If leveraging predicate, provide material equivalence justification. If novel materials, provide full testing rationale.]
```

## Section 13: Software/Cybersecurity

```markdown
## Software Documentation

### 13.1 Software Level of Concern
{If software_doc_level available:}
Software documentation level: {software_doc_level}
[Source: import_data.json]

{If SaMD:}
Per FDA guidance "Policy for Device Software Functions and Mobile Medical Applications" and IEC 62304, the software is classified as Class {A/B/C}.

[TODO: Company-specific — Determine level per IEC 62304:
- Class A: No injury possible
- Class B: Non-serious injury possible
- Class C: Death or serious injury possible]

### 13.2 Software Description
[TODO: Company-specific —
- Software architecture overview
- Programming language(s) and development environment
- Third-party software components (OTS/SOUP)
- Hardware platform requirements]

### 13.3 Software Testing
[TODO: Company-specific —
- Unit testing coverage
- Integration testing
- System testing
- Regression testing
- Traceability to requirements]

### 13.4 Cybersecurity (Section 524B)
{If device has connectivity:}
Per Section 524B of the FD&C Act (added by Section 3305 of the Consolidated Appropriations Act, 2023, effective March 29, 2023), cybersecurity documentation is required for cyber devices.

**Threat Model:**
[TODO: Company-specific — Provide threat model per FDA "Cybersecurity in Medical Devices" guidance]

**SBOM:**
[TODO: Company-specific — Software Bill of Materials per NTIA minimum elements]

**Vulnerability Management:**
[TODO: Company-specific — Post-market vulnerability monitoring and patching plan]

{If device has no connectivity:}
The subject device does not meet the definition of a "cyber device" under Section 524B. No cybersecurity documentation is required.
```

## Section 14: EMC/Electrical Safety

```markdown
## Electromagnetic Compatibility and Electrical Safety

### 14.1 Applicable Standards
{Auto-populate if product code indicates electrical device:}

| Standard | Edition | Title | Applicable? |
|----------|---------|-------|-------------|
| IEC 60601-1 | Ed. 3.2 | General requirements for safety | [TODO] |
| IEC 60601-1-2 | Ed. 4.1 | EMC requirements and tests | [TODO] |
| IEC 60601-1-6 | Ed. 3.2 | Usability | [TODO] |
| IEC 60601-1-8 | Ed. 2.2 | Alarm systems | [TODO] |
| IEC 60601-1-11 | Ed. 2.1 | Home healthcare environment | [TODO] |

[TODO: Company-specific — Add device-specific particular standards (60601-2-XX)]

### 14.2 EMC Testing Summary
[TODO: Company-specific —
- Test lab (ISO/IEC 17025 / A2LA accredited)
- Emissions testing results (CISPR 11)
- Immunity testing results (IEC 61000-4-X series)
- Essential performance maintained during immunity tests?
- Deviations or non-conformances?]

### 14.3 Electrical Safety Testing Summary
[TODO: Company-specific —
- Applied part classification (Type B/BF/CF)
- Means of protection (Class I/II)
- Dielectric strength
- Leakage current (earth, touch, patient)
- Mechanical and environmental tests]

### 14.4 Declaration of Conformity
[TODO: Company-specific — Attach or reference Declaration of Conformity to applicable standards]
```

## Predicate Justification

```markdown
## Predicate Justification

### Selection Rationale
{If predicates available from review.json:}
{For each predicate:}

#### {k_number} — {device_name} ({applicant}, cleared {date})

**Why this predicate was selected:**
{Auto-generate from review.json rationale and confidence score}
[Source: review.json]

**Key similarities:**
- Same intended use: {ifu_comparison}
- Same product code: {product_code}
- Same technological characteristics: {tech_summary}

**Clearance history:** {decision_type} — Class {class}
**Confidence score:** {score}/100 — {label}

{If not:}
[TODO: Company-specific — For each proposed predicate device:
1. Explain why this device was selected as a predicate
2. Describe the regulatory history and clearance basis
3. Detail the similarities in intended use
4. Detail the similarities in technological characteristics
5. Address any known differences]

### Alternative Predicates Considered
[TODO: Company-specific — List other devices evaluated and why they were not selected as the primary predicate]

### Predicate Chain Summary
{If lineage data available:}
{chain_visualization}
[Source: lineage analysis]

{If not:}
[TODO: Company-specific — Describe the predicate's own clearance history and predicate chain to demonstrate regulatory lineage]
```

## Testing Rationale

```markdown
## Testing Rationale

### Testing Strategy Overview
{If test_plan.md available:}
The testing strategy for the subject device addresses differences identified in the substantial equivalence comparison and requirements from applicable guidance documents.
[Source: test_plan.md]

{If not:}
[TODO: Company-specific — Describe the overall testing strategy and how it supports the SE determination]

### Mapping of Differences to Tests
{If se_comparison.md and test_plan.md available:}

| # | Identified Difference | Applicable Standard | Proposed Test | Rationale |
|---|----------------------|--------------------|--------------|-----------|
{For each difference in SE comparison:}
| {n} | {difference} | {standard} | {test} | {why this test addresses the difference} |

[Source: se_comparison.md, test_plan.md]

{If not:}
[TODO: Company-specific — For each technological difference identified in the SE comparison:
1. Reference the specific difference
2. Identify the applicable standard or guidance requirement
3. Describe the proposed test method
4. Explain why this test is sufficient to demonstrate equivalence]

### Guidance-Driven Requirements
{If guidance_cache available:}
The following tests are required by applicable FDA guidance documents:

| Guidance Document | Requirement | Test Method | Status |
|-------------------|-------------|-------------|--------|
{For each guidance requirement:}
| {guidance_title} | {requirement} | {method} | {Planned/Complete} |

[Source: guidance_cache]

{If not:}
[TODO: Run `/fda:guidance` to identify applicable guidance requirements, then map to testing]

### Predicate Precedent
{If predicate testing data available:}
The predicate device(s) demonstrated the following testing precedent:
{predicate_testing_summary}
[Source: predicate PDF analysis]

{If not:}
[TODO: Company-specific — Describe testing performed by predicate device(s) to establish precedent]
```

## Section 15: Performance Testing

```markdown
## Performance Testing Summary

### 15.1 Test Overview
{If performance testing data available:}
Performance testing was conducted to demonstrate that the subject device performs as intended and to address identified technological differences from the predicate device.

{If test_plan.md available:}
{Summary of test plan}
[Source: test_plan.md]

{If not:}
[TODO: Company-specific — Summarize performance testing program:
- Objectives
- Test articles and sample sizes
- Test conditions]

### 15.2 Bench Testing
[TODO: Company-specific — For each bench test:
- Test method and standard
- Sample size and acceptance criteria
- Results summary
- Pass/fail determination]

### 15.3 Comparison to Predicate Performance
[TODO: Company-specific — Compare subject device performance to predicate:
- Predicate testing precedent from 510(k) summary
- Subject device test results vs predicate
- Demonstration of equivalent or superior performance]

### 15.4 Performance Testing Conclusions
[TODO: Company-specific — Summarize overall performance testing conclusions:
- All acceptance criteria met
- Device performs as intended
- Performance equivalent to predicate]
```

## Section 16: Clinical

```markdown
## Clinical Evidence

### 16.1 Clinical Evidence Strategy
{Auto-determine based on available data:}
{If predicates had clinical data → "Clinical data provided to support specific performance claims."}
{If no clinical claims → "No clinical data submitted. Substantial equivalence demonstrated through non-clinical testing."}
{If literature-based → "Clinical evidence from published literature supports safety and effectiveness."}

### 16.2 Clinical Data Summary
{If literature from /fda:literature:}
A systematic literature review was conducted to identify relevant clinical evidence.

**Search Strategy:**
- Databases: PubMed, Google Scholar
- Search terms: {terms from literature.md}
- Date range: {range}
- Results: {N} articles identified, {N} included

**Key Findings:**
{Summary of relevant clinical evidence from literature.md}
[Source: literature.md]

{If no clinical data:}
[TODO: Company-specific — Describe clinical data strategy:
- Exemption from clinical data (reference predicate precedent)
- Literature-based clinical evaluation
- Clinical study summary (if conducted)]

### 16.3 Adverse Event Analysis
{If safety data available from /fda:safety:}
Analysis of MAUDE adverse event data for product code {product_code}:
- Total events: {count}
- Severity distribution: {malfunction/injury/death counts}
- Relevant patterns: {findings from safety_report.md}
[Source: safety_report.md]

[TODO: Company-specific — Risk-benefit analysis addressing any concerning adverse event patterns]

### 16.4 Clinical Conclusion
[TODO: Company-specific — Summarize clinical evidence conclusion:
- Evidence supports intended use claims
- No new safety concerns identified
- Clinical performance equivalent to predicate]
```

## Section 04: Truthful and Accuracy Statement

```markdown
## Truthful and Accuracy Statement

I certify that, in my capacity as {title} for {applicant_name}, this submission includes all information, published reports, and unpublished reports of data and information known to or which should reasonably be known to the submitter, relevant to this premarket notification, whether favorable or unfavorable, that relates to the safety or effectiveness of the device.

[TODO: Company-specific — Signed by authorized representative]

Name: ___________________________________
Title: ___________________________________
Date: ___________________________________
Signature: ________________________________
```

## Section 05: Financial Certification

```markdown
## Financial Certification / Disclosure

[TODO: Company-specific — Complete Form FDA 3454 or 3455:
- If no clinical data submitted: FDA 3454 (Certification)
- If clinical data submitted: FDA 3455 (Disclosure) for each clinical investigator]

This section addresses 21 CFR Part 54 — Financial Disclosure by Clinical Investigators.
```

## Section 08: Standards & Declarations of Conformity

```markdown
## Declaration of Conformity

### Manufacturer Information
| Field | Value |
|-------|-------|
| Company Name | [TODO: Company-specific — Legal entity name] |
| Address | [TODO: Company-specific — Full address] |
| Authorized Representative | [TODO: Company-specific — Name and title] |

### Device Identification
| Field | Value |
|-------|-------|
| Device Trade Name | {trade_name} |
| Product Code | {product_code} |
| Device Class | Class {class} |
| Regulation Number | 21 CFR {regulation} |

### Applicable Standards

| # | Standard | Edition | Title | Status | Test Lab |
|---|----------|---------|-------|--------|----------|
| 1 | {standard_1} | {year} | {title} | [TODO: Full Conformity / Partial / N-A] | [TODO: Lab name and accreditation] |
| 2 | {standard_2} | {year} | {title} | [TODO: Full Conformity / Partial / N-A] | [TODO: Lab name and accreditation] |

{Auto-populate from test_plan.md or guidance requirements}

### Declaration
We, [TODO: Company-specific — company name], declare under sole responsibility that the medical device identified above, when used in accordance with its intended purpose, conforms to the applicable standards listed above.

This declaration is based on the following evidence:
- Testing conducted by [TODO: Company-specific — accredited laboratory name(s)]
- Test reports: [TODO: Company-specific — report numbers and dates]

### Signature Block
| Field | Value |
|-------|-------|
| Name | [TODO: Company-specific] |
| Title | [TODO: Company-specific] |
| Date | [TODO: Company-specific] |
| Signature | ________________________________ |
```

## Section 17: Human Factors / Usability Engineering

```markdown
## Human Factors / Usability Engineering

### 17.1 Use Environment
[TODO: Company-specific — Describe the intended use environment(s):
- Clinical setting (hospital, clinic, physician office)
- Home environment (if applicable)
- Environmental conditions (lighting, noise, temperature)]

### 17.2 User Profile
| User Group | Training | Experience | Physical Requirements |
|-----------|----------|------------|----------------------|
| [TODO: Primary users] | [TODO] | [TODO] | [TODO] |
| [TODO: Secondary users] | [TODO] | [TODO] | [TODO] |

### 17.3 Critical Tasks
| # | Task | Use Error Risk | Severity | Mitigation |
|---|------|---------------|----------|------------|
| 1 | [TODO: Company-specific] | [TODO] | [TODO] | [TODO] |

### 17.4 Use-Related Risk Analysis Summary
{Auto-populate from MAUDE data if /fda:safety has been run:}
Known use error patterns for product code {product_code}:
- {event_type}: {count} events ({percentage}%)

[TODO: Company-specific — Complete use-related risk analysis per IEC 62366-1:2015]

### 17.5 Formative Study Summary
[TODO: Company-specific — Summarize formative evaluation studies:
- Cognitive walkthrough results
- Heuristic evaluation findings
- Simulated use study results
- Design changes implemented based on findings]

### 17.6 Summative (Validation) Study Summary
[TODO: Company-specific — Summarize summative evaluation:
- Study design and protocol
- Participants: {N} per user group (FDA recommends minimum 15)
- Critical task results

| Task | Participants | Successes | Use Errors | Close Calls |
|------|-------------|-----------|------------|-------------|
| [TODO] | {N} | {N} | {N} | {N} |

Conclusion: [TODO: The device can/cannot be used safely and effectively by the intended user population]]
```

## Section 11: Shelf Life — ASTM F1980 Reference

### Accelerated Aging Formula (ASTM F1980)

```
Accelerated Aging Factor (AAF) = Q10^((T_accelerated - T_ambient) / 10)
Accelerated Aging Duration = Real-Time Shelf Life / AAF
```

### Example Calculation

| Parameter | Value |
|-----------|-------|
| Ambient temperature (T_ambient) | 25 C |
| Accelerated temperature (T_accelerated) | 55 C |
| Q10 factor | 2.0 (conservative per ASTM F1980) |
| Desired shelf life | 24 months |
| **AAF** | **2.0^((55-25)/10) = 2.0^3 = 8.0** |
| **Required accelerated aging** | **24/8 = 3.0 months** |

### Notes
- Q10 = 2.0 is conservative default; range is 1.8-2.5
- Real-time aging must be conducted concurrently
- Accelerated aging results are preliminary until confirmed by real-time data
- For calculation: `/fda:calc shelf-life --ambient 25 --accelerated 55 --q10 2.0 --shelf-life 2years`
