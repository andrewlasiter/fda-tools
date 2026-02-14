# AI/ML Medical Device Intelligence

## Overview

FDA regulates AI/ML-enabled medical devices under existing frameworks (510(k), De Novo, PMA) with additional considerations for algorithm transparency, predetermined change control, and real-world performance monitoring.

## AI/ML-Associated Product Codes

These product codes are commonly associated with AI/ML-enabled devices:

| Product Code | Device Name | Class | Typical AI/ML Application |
|-------------|-------------|-------|--------------------------|
| QAS | Radiological Computer Assisted Detection/Diagnosis | II | CADe/CADx for imaging |
| QIH | Radiological Computer Aided Triage and Notification | II | AI triage for stroke, PE |
| QMT | Quantitative Imaging Software | II | Quantitative analysis of imaging |
| QJU | Computer-Assisted Detection Software — Mammography | II | AI mammography screening |
| QKQ | Electrocardiograph Analysis Software | II | AI ECG interpretation |
| QPN | Clinical Decision Support Software | II | CDS algorithms |
| QRZ | Ophthalmic AI/ML Software | II | Diabetic retinopathy screening |
| DXL | Monitoring System, Physiological | II | Patient monitoring algorithms |
| DPS | Electrocardiograph, Software | II | Arrhythmia detection |
| MYN | System, Surgical, Computer-Controlled | II | Surgical planning AI |
| OTB | Image Processing Software | II | General image processing |

## SaMD Classification

Software as a Medical Device (SaMD) classification per IMDRF framework:

| Significance of Information | Critical | Serious | Non-Serious |
|---------------------------|----------|---------|-------------|
| Treat or Diagnose | IV (Class III) | III (Class II) | II (Class II) |
| Drive Clinical Management | III (Class II) | II (Class II) | I (Class I) |
| Inform Clinical Management | II (Class II) | I (Class I) | I (Class I) |

## PCCP Eligibility Indicators

Devices eligible for Predetermined Change Control Plans (PCCPs) per FDA guidance:

- **Machine learning algorithms** that may be updated with new training data
- **Adaptive algorithms** that adjust performance parameters over time
- **Iterative improvement devices** where post-market data refines performance
- **Multi-version software** with planned update cycles

Not eligible:
- Changes that alter intended use
- Changes from prescription to OTC
- Changes that introduce new risks not covered by existing risk analysis

## AI/ML Clearance Trend Patterns

### By Year (approximate)
- 2018: ~30 AI/ML devices authorized
- 2019: ~50 AI/ML devices authorized
- 2020: ~65 AI/ML devices authorized
- 2021: ~100 AI/ML devices authorized
- 2022: ~170 AI/ML devices authorized
- 2023: ~200 AI/ML devices authorized
- 2024: ~240 AI/ML devices authorized (est.)
- 2025: Growing, especially in cardiology and radiology

### By Clinical Area
1. Radiology (75%+) — imaging AI dominant
2. Cardiology (10-15%) — ECG, cardiac monitoring
3. Ophthalmology (3-5%) — retinal screening
4. Pathology (2-3%) — digital pathology AI
5. Other (5-10%) — endoscopy, dermatology, neurology

## Key FDA Guidance for AI/ML

| Guidance | Year | Focus |
|----------|------|-------|
| Artificial Intelligence/Machine Learning (AI/ML)-Based Software as a Medical Device (SaMD) Action Plan | 2021 | Overall AI/ML regulatory framework |
| Marketing Submission Recommendations for a PCCP for AI/ML-Enabled Device Software Functions | 2023 | PCCP for AI/ML devices |
| Clinical Decision Support Software (Guidance for Industry and FDA Staff) | 2022 | CDS scope and exemptions |
| Computer-Assisted Detection/Diagnosis (CADe/CADx) — Premarket Guidance | 2022 | CADe/CADx specific requirements |
| Content of Premarket Submissions for Device Software Functions | 2023 | Software documentation (IEC 62304) |

## FDA-2022-D-2628 (PCCP Docket)

The PCCP guidance (docket FDA-2022-D-2628) describes:
- Description of Modifications (what may change)
- Modification Protocol (how changes are validated)
- Impact Assessment (risk analysis per modification)
- Performance specifications for algorithm updates
- Real-world performance monitoring plans

## Integration with Plugin Commands

- `/fda:research {CODE} --aiml` — AI/ML trend analysis for a product code
- `/fda:pccp` — Generate PCCP for AI/ML devices
- `/fda:pathway` — Pathway scoring includes AI/ML considerations
- `/fda:draft` — SaMD-specific draft sections
