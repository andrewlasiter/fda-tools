# CDRH Portal Submission Guide

Reference for submitting premarket submissions to FDA via the CDRH Premarket Review Submission Portal.

## Portal Access

- **URL**: `https://ccp.fda.gov/prweb/PRAuth/app/default/extsso`
- **Account**: Okta-based identity verification; any individual may register
- **Support**: ccp@fda.hhs.gov (portal issues), eSubPilot@fda.hhs.gov (eSTAR questions), DICE@fda.hhs.gov (document issues)

## Eligible Submission Types

| Submission Type | eSTAR Template | eSTAR Status | Effective Date |
|----------------|---------------|-------------|----------------|
| 510(k) | nIVD v6 or IVD v6 | **Mandatory** | October 1, 2023 |
| De Novo | nIVD v6 or IVD v6 | **Mandatory** | October 1, 2025 |
| PMA / PMA Supplement | nIVD v6 or IVD v6 | Voluntary | — |
| Pre-Submission (Q-Sub) | PreSTAR v2 | Voluntary | — |
| IDE (Investigational Device Exemption) | PreSTAR v2 | Voluntary | — |
| 513(g) Request for Information | PreSTAR v2 | Voluntary | — |
| Small Business Determination Request | Online form (mandatory) | N/A | November 1, 2024 |

## File Size Limits

- **Total submission**: 4 GB maximum per upload
- **Individual attachment**: 1 GB maximum per file
- **Oversized file fallback**: Mail physical media (USB/CD) to CDRH Document Control Center:
  ```
  CDRH Document Control Center (DCC)
  10903 New Hampshire Avenue
  Building 66, Room G609
  Silver Spring, MD 20993-0002
  ```

## Processing Timeline

- Submissions received **before 4:00 PM ET**: Processed same business day
- Submissions received **after 4:00 PM ET**: Processed next business day
- Confirmation email sent upon successful receipt

## Tracking and Status

- **Real-time dashboard**: Available to the official correspondent and authorized delegates
- Submission status updates tracked through the portal
- Email notifications at key milestones (receipt, review initiation, additional information requests)

## CDRH vs CBER Routing

Not all medical devices are reviewed by CDRH. Biological and blood-related devices are reviewed by CBER.

| Center | Device Types | Submission Method |
|--------|-------------|-------------------|
| **CDRH** | Most medical devices, IVDs, radiation-emitting products | CDRH Portal or mail to DCC |
| **CBER** | Blood establishment devices, cellular therapy devices, tissue-related devices | FDA ESG (Electronic Submissions Gateway) or mail |

**How to determine routing:**
- Check the product code classification at `https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfPCD/classification.cfm`
- If the review panel code starts with "IM" (Immunology) or "HE" (Hematology), check whether CBER has jurisdiction
- When in doubt, contact DICE@fda.hhs.gov for routing guidance

## Official Correspondent Identification

The official correspondent is the person authorized to communicate with FDA on behalf of the submitter:

- Identified in the **eSTAR Contact section** (Cover Letter page)
- Also documented on **FDA Form 3514** (Section C — Correspondent Information)
- Must be a US-based agent if the applicant is a foreign entity
- Delegates can be added via the CDRH Portal dashboard after submission

## Submission Best Practices

1. **Pre-upload checklist:**
   - Verify all attachments are under 1 GB each and total is under 4 GB
   - Ensure no PDF passwords are set (blocks FDA redaction workflow)
   - Confirm eSTAR template passes built-in validation (no red X indicators)
   - Check that the official correspondent email is correct (receives all correspondence)

2. **File naming:**
   - Use descriptive names: `TestReport_Biocompatibility_ISO10993.pdf`
   - Avoid special characters in filenames (use hyphens/underscores)
   - Combine similar attachments into single PDFs where possible

3. **After submission:**
   - Save the confirmation number from the portal
   - Monitor the dashboard for status updates
   - Respond to Additional Information (AI) requests within the timeframe specified

## Early Technical Screening

FDA performs Early Technical Screening on eSTAR submissions:
- Checks for completeness of required sections and attachments
- If the eSTAR fails screening, a **180-day hold** is placed on the submission
- The submitter must correct deficiencies and resubmit within the hold period
- Prevention: Use `/fda:pre-check` to simulate FDA review before submitting

## Integration with Plugin Workflow

After using `/fda:assemble` or `/fda:export` to prepare the submission package:

```
1. /fda:export --project NAME --format zip    Generate eSTAR package
2. Open official eSTAR template in Adobe Acrobat
3. Import XML data via Form > Import Data
4. Add attachments (test reports, labeling, etc.)
5. Run eSTAR built-in validation (check for red X)
6. Submit via CDRH Portal: https://ccp.fda.gov/prweb/PRAuth/app/default/extsso
7. Save confirmation number and monitor dashboard
```
