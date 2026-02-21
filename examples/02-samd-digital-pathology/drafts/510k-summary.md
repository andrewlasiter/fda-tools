# 510(k) Summary — PathSight AI Digital Pathology Software

**Submission Type:** Traditional 510(k)
**Submitter:** Example Digital Health Inc.
**Date Prepared:** 2026-02-01
**Product Code:** QKQ — Medical Image Analyzer
**Regulation:** 21 CFR 892.2050
**Device Class:** II

---

## I. Submitter Information

| Field | Value |
|-------|-------|
| Company | Example Digital Health Inc. |
| Address | 456 Tech Boulevard, Suite 200, Silicon Valley, CA 94025 |
| Contact | [TODO: Insert contact name and phone] |
| FDA Establishment Number | [TODO: Insert FEI number] |

---

## II. Device Name

**510(k) Device Name:** Digital Pathology Viewer and AI Analysis Software
**Trade/Proprietary Name:** PathSight AI

---

## III. Indications for Use

PathSight AI is intended to digitize, store, manage, and display whole-slide pathology
images and to provide AI-assisted identification of regions of interest (ROIs) for
review by a qualified pathologist. The software is not intended to replace pathologist
interpretation and is intended as a decision-support tool only.

**Rx:** Prescription use — for use by or on the order of a licensed pathologist.

---

## IV. Description of Device

PathSight AI is a Software as a Medical Device (SaMD) operating on validated Windows
10/11 workstations (≥32 GB RAM, dedicated GPU). Key components:

1. **WSI Viewer** — DICOM-compliant whole-slide image display with pan, zoom, rotation,
   and multi-resolution tiling. Supports SVS, NDPI, MRXS, and TIFF formats.
2. **AI Inference Engine** — U-Net deep learning model identifies ROIs in H&E-stained
   slides. Outputs probability heat maps overlaid on slide image. Model trained on
   50,000 de-identified slides from 12 institutions.
3. **Case Management Module** — Workflow integration, DICOM-SR report generation,
   HL7 FHIR export.
4. **Audit Trail** — 21 CFR Part 11 compliant logging of all user actions and
   diagnostic interpretations.

**Software Safety Class:** B (per IEC 62304)
**Cybersecurity:** Implemented per FDA Cybersecurity Guidance (2023)

---

## V. Substantial Equivalence Summary

### Predicate Device

**K242244** — FullFocus Digital Pathology System (Philips Healthcare, July 2024)

| Comparison Point | PathSight AI | Predicate (K242244) |
|-----------------|--------------|---------------------|
| Intended use | WSI viewer + AI ROI detection | WSI viewer + AI ROI detection |
| Product code | QKQ | QKQ |
| Regulation | 21 CFR 892.2050 | 21 CFR 892.2050 |
| Software lifecycle | IEC 62304 Class B | IEC 62304 Class B |
| AI component | Yes (H&E ROI detection) | Yes |
| Decision support only | Yes | Yes |
| Cybersecurity documentation | FDA 2023 guidance | FDA 2022 guidance |

**Conclusion:** PathSight AI has the same intended use and equivalent technological
characteristics as K242244. The AI architecture difference (U-Net vs. predicate's
convolutional approach) does not raise new safety or effectiveness questions given
equivalent clinical validation methodology.

---

## VI. Summary of Software Documentation

| Document | Standard | Status |
|----------|----------|--------|
| Software development plan | IEC 62304 §5.1 | Complete |
| Software requirements specification | IEC 62304 §5.2 | Complete |
| Software architecture design | IEC 62304 §5.3 | Complete |
| Software detailed design | IEC 62304 §5.4 | Complete |
| Software unit/integration testing | IEC 62304 §5.5-5.7 | Complete |
| Anomaly resolution records | IEC 62304 §9 | Complete |
| Cybersecurity bill of materials | FDA 2023 guidance | Complete |
| Threat model | FDA 2023 guidance | Complete |

---

## VII. Clinical Validation Summary

**Test Set:** 500 de-identified H&E slides (independent, not used in training)
**Comparator:** 3-pathologist consensus read

| Metric | PathSight AI | 95% CI |
|--------|-------------|--------|
| Sensitivity (ROI detection) | 94.2% | [91.8%, 96.1%] |
| Specificity (ROI detection) | 97.1% | [95.3%, 98.4%] |
| Positive predictive value | 96.4% | [94.4%, 97.9%] |
| Negative predictive value | 95.2% | [92.9%, 97.0%] |
