# eCTD Overview (Informational Reference)

## Important: eCTD Is NOT Required for 510(k) Submissions

FDA does **not** require eCTD (electronic Common Technical Document) format for 510(k) submissions. The required format for 510(k) is **eSTAR** (electronic Submission Template And Resource).

This reference is provided for informational context only.

## When eCTD Is Used

| Submission Type | Format Required |
|----------------|-----------------|
| 510(k) | **eSTAR** (NOT eCTD) |
| De Novo | eSTAR |
| PMA (Premarket Approval) | eCTD |
| IDE (Investigational Device Exemption) | eCTD |
| HDE (Humanitarian Device Exemption) | eCTD |
| Drug applications (NDA, ANDA, BLA) | eCTD |

## eCTD Structure (5 Modules)

For reference only — not applicable to 510(k):

| Module | Content |
|--------|---------|
| Module 1 | Administrative Information (regional) |
| Module 2 | Common Technical Document Summaries |
| Module 3 | Quality (CMC) |
| Module 4 | Nonclinical Study Reports |
| Module 5 | Clinical Study Reports |

## How eSTAR Differs from eCTD

| Feature | eSTAR | eCTD |
|---------|-------|------|
| Applicable to | 510(k), De Novo | PMA, IDE, drugs |
| Format | PDF form with XML data | XML backbone with linked documents |
| Sections | 20 eSTAR sections | 5 modules |
| Submission portal | eSTAR Portal | FDA ESG (Electronic Submissions Gateway) |
| Mandatory since | October 1, 2023 | Varies by submission type |

## FDA ESG (Electronic Submissions Gateway)

PMA and IDE submissions using eCTD are submitted via the FDA ESG:
- Portal: `https://www.fda.gov/industry/electronic-submissions-gateway`
- Uses eCTD v4.0 format
- Requires ESG account and digital certificates

## Integration Notes

- `/fda:export` generates eSTAR XML — NOT eCTD format
- For PMA submissions requiring eCTD: consult FDA ESG guidance directly
- This plugin focuses on 510(k)/De Novo submissions (eSTAR format)
