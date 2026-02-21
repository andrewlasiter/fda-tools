# Example 2 — SaMD 510(k): Digital Pathology AI Software

**Product code:** QKQ (Medical Image Analyzer)
**Device class:** II
**Regulation:** 21 CFR 892.2050
**Review panel:** RA (Radiology Devices)
**Pathway:** Traditional 510(k)

This example demonstrates a Software as a Medical Device (SaMD) submission with an
AI/ML component. SaMD submissions require additional software lifecycle documentation
(IEC 62304) and cybersecurity documentation beyond what hardware-only devices need.

---

## Project Structure

```
02-samd-digital-pathology/
├── device_profile.json      # Software specs, AI model description, intended use
├── review.json              # Accepted predicates and SE conclusion
├── drafts/
│   └── 510k-summary.md     # Example 510(k) Summary with software and clinical validation
└── README.md                # This file
```

---

## Step-by-Step Workflow

### Step 1 — Create the project

```bash
/fda-tools:start --project pathsight-ai --product-code QKQ
```

### Step 2 — Fetch predicate devices

```bash
/fda-tools:b --product-codes QKQ --years 5 --project pathsight-ai
```

Expected output: CSV with ~15–25 QKQ clearances. The pool is smaller than hardware
device codes; more years are needed to find comparable predicates.
Runtime: ~20–40 seconds.

### Step 3 — Research predicates

```bash
/fda-tools:r QKQ --project pathsight-ai \
  --device-description "Whole-slide image viewer with AI-assisted ROI detection for H&E-stained pathology slides" \
  --intended-use "decision support for pathologist review"
```

Tip: QKQ devices vary widely in modality (radiology, pathology, dermatology). Filter
results to pathology-specific devices for the most relevant predicates.

### Step 4 — Run pre-submission readiness check

```bash
/fda-tools:pc --project pathsight-ai --depth deep --focus all
```

Expected output: SRI score ~55–65/100 for a new SaMD project. Key gaps:
- Software documentation (IEC 62304 records) not yet uploaded
- Cybersecurity documentation (threat model, SBOM) needed
- Clinical validation dataset and statistics pending

### Step 5 — Draft software section

```bash
/fda-tools:d software --project pathsight-ai
```

Expected output: Software documentation section with IEC 62304 lifecycle checklist,
anomaly resolution table, and cybersecurity documentation requirements.

### Step 6 — Draft 510(k) summary

```bash
/fda-tools:d 510k-summary --project pathsight-ai
```

---

## SaMD-Specific Requirements

### IEC 62304 Software Lifecycle Documentation

For Safety Class B software (this example), the following records are required:

| Document | IEC 62304 Section |
|----------|-------------------|
| Software development plan | 5.1 |
| Software requirements specification | 5.2 |
| Software architecture | 5.3 |
| Detailed design | 5.4 |
| Unit/integration/system test records | 5.5–5.7 |
| Software release records | 5.8 |
| Problem resolution records | 9 |

### Cybersecurity Documentation (FDA 2023 Guidance)

Required for network-connected devices and cloud-based AI:
- Software Bill of Materials (SBOM)
- Threat model and risk analysis
- Cybersecurity testing summary
- Patch management plan
- Vulnerability disclosure policy

### AI/ML Clinical Validation

FDA expects validation on an **independent test set** (not used in training):
- ≥200 cases recommended; ≥500 for robust confidence intervals
- Sensitivity, specificity, PPV, NPV with 95% confidence intervals
- Subgroup analysis (age, institution, staining protocol)
- Comparison to reader (pathologist) performance

---

## Expected Review Time

Based on recent QKQ clearances (2022–2025): **120–200 days** (median ~150 days).
SaMD submissions typically take longer due to software documentation review.

---

## Common Pitfalls for SaMD Devices

1. **Training/test data overlap** — FDA will ask if validation data was used in
   training. Maintain strict data split documentation.
2. **Predicate claim mismatch** — If your AI claims higher accuracy than the predicate,
   reviewers may require more extensive clinical data.
3. **Cybersecurity** — As of 2023, cybersecurity documentation is mandatory for all
   network-connected devices. SBOM must list all third-party software components.
4. **Intended use scope** — "Decision support only" language is expected. Do not claim
   the device provides independent diagnoses.
