# Regulatory Timeline Update Procedure

**Document Version:** 1.0.0
**Last Updated:** 2026-02-17
**Effective Date:** 2026-02-17

## Purpose

This document provides step-by-step instructions for updating FDA PMA supplement review period timelines when FDA modifies regulatory requirements through CFR changes, guidance documents, or policy updates.

## Overview

The `regulatory_timelines.json` configuration file contains all timeline constants used by `supplement_tracker.py` for estimating review periods. When FDA changes review timelines, this configuration must be updated following the procedure below.

## When to Update

Update timelines when:

1. **CFR Regulation Changes** - FDA publishes final rule modifying 21 CFR 814.39 or related regulations
2. **Guidance Updates** - FDA issues new/revised guidance affecting review timelines
3. **Policy Announcements** - FDA announces modified review procedures (e.g., expedited programs)
4. **Performance Goals** - MDUFA (Medical Device User Fee Amendments) goal changes
5. **Annual Verification** - Quarterly review confirms no changes but updates verification dates

## Update Procedure

### Step 1: Identify Change Source

Document the regulatory change source:

- **CFR Change**: Federal Register citation (e.g., "88 FR 12345, March 1, 2024")
- **Guidance**: Guidance document title, date, and docket number
- **Policy**: FDA announcement, CDRH webpage, or notice
- **MDUFA**: User fee agreement version and effective date

**Required Information:**
- Change effective date
- Affected supplement types (180-day, 30-day, real-time, etc.)
- New review period duration (in days)
- CFR citation (if changed)
- Rationale for change

### Step 2: Verify Change Authenticity

**CRITICAL**: Only update based on official FDA sources.

**Acceptable Sources:**
- FDA.gov official guidance documents
- Federal Register (federalregister.gov)
- Electronic Code of Federal Regulations (ecfr.gov)
- Official FDA CDRH announcements
- MDUFA commitment letters

**Unacceptable Sources:**
- Third-party blogs or articles
- Unofficial summaries
- Industry association interpretations (without FDA confirmation)
- Draft guidance (not final)

**Verification Checklist:**
- [ ] Source is official FDA publication
- [ ] Effective date is clearly stated
- [ ] Change applies to PMA supplements (not 510(k) or other pathways)
- [ ] Numeric timeline values are explicitly stated (not inferred)
- [ ] Change is final (not proposed rule or draft guidance)

### Step 3: Backup Current Configuration

Before making changes:

```bash
# Create backup with timestamp
cp data/regulatory_timelines.json \
   data/regulatory_timelines.json.backup.$(date +%Y%m%d_%H%M%S)

# Verify backup
ls -lh data/regulatory_timelines.json.backup.*
```

### Step 4: Update Configuration File

**A. Archive Current Timeline to Historical Section**

1. Copy entire `current_timelines` object to `historical_timelines` array
2. Set `end` date in `effective_date_range` to day before new timeline effective date
3. Document changes in `changes_from_previous` field

**B. Update Current Timeline**

Edit `current_timelines.<supplement_type>` section:

```json
{
  "typical_review_days": <NEW_VALUE>,
  "cfr_citation": "<UPDATED_CFR_IF_CHANGED>",
  "effective_date": "<NEW_EFFECTIVE_DATE>",
  "last_verified": "<TODAY_DATE>",
  "regulatory_notes": "<ADD_NOTE_ABOUT_CHANGE>",
  "guidance_references": ["<ADD_NEW_GUIDANCE_IF_APPLICABLE>"]
}
```

**C. Update Metadata Section**

```json
{
  "metadata": {
    "version": "<INCREMENT_VERSION>",
    "last_updated": "<TODAY_DATE>",
    "effective_date": "<NEW_TIMELINE_EFFECTIVE_DATE>"
  }
}
```

**D. Add Update History Entry**

```json
{
  "update_history": [
    {
      "date": "<TODAY_DATE>",
      "version": "<NEW_VERSION>",
      "changes": "<DESCRIBE_WHAT_CHANGED>",
      "updated_by": "<YOUR_NAME_OR_ROLE>",
      "verification_status": "VERIFIED",
      "source": "<FDA_SOURCE_CITATION>",
      "federal_register_citation": "<FR_CITATION_IF_APPLICABLE>"
    }
  ]
}
```

### Step 5: Validate Configuration

Run validation script to ensure JSON integrity:

```bash
python3 -m json.tool data/regulatory_timelines.json > /dev/null && \
  echo "JSON valid" || echo "JSON INVALID - fix syntax errors"
```

**Manual Validation Checklist:**
- [ ] All `typical_review_days` values are positive integers
- [ ] All `cfr_citation` values match pattern `21 CFR XXX.XX(x)`
- [ ] All dates are ISO 8601 format (YYYY-MM-DD)
- [ ] `effective_date` is in the past (timeline is active)
- [ ] `last_verified` is today's date
- [ ] Historical timeline version incremented
- [ ] Update history entry added

### Step 6: Test Configuration Loading

Run supplement tracker with test PMA to verify configuration loads correctly:

```bash
cd /home/linux/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/scripts

python3 supplement_tracker.py --pma P170019 --json | \
  grep -A 5 "typical_review_days"
```

**Expected Output**: Should show new timeline values in supplement classification.

**Error Handling**: If errors occur:
1. Check Python console for error messages
2. Verify JSON syntax with validator
3. Restore backup if configuration is corrupted:
   ```bash
   cp data/regulatory_timelines.json.backup.YYYYMMDD_HHMMSS \
      data/regulatory_timelines.json
   ```

### Step 7: Run Test Suite

Execute automated tests to verify backward compatibility:

```bash
cd tests
pytest test_supplement_tracker.py -v -k timeline
```

**Required Tests to Pass:**
- `test_load_regulatory_timelines` - Configuration loads without errors
- `test_timeline_values_positive` - All review days > 0
- `test_cfr_citations_valid` - All CFR citations well-formed
- `test_backward_compatibility` - Fallback to defaults if config missing

### Step 8: Update Documentation

Update related documentation files:

**A. Update CHANGELOG.md:**
```markdown
## [Version X.Y.Z] - YYYY-MM-DD

### Regulatory Timeline Updates
- Updated [supplement_type] review period: OLD_DAYS → NEW_DAYS days
- Effective date: EFFECTIVE_DATE
- CFR citation: CITATION
- Source: FDA_SOURCE
```

**B. Update README (if applicable):**
- Note any breaking changes to API
- Document new timeline values in usage examples

**C. Update Version in supplement_tracker.py:**
```python
# Update module docstring version number
__version__ = "X.Y.Z"  # Increment version
```

### Step 9: Commit Changes

```bash
git add data/regulatory_timelines.json \
        data/REGULATORY_TIMELINE_UPDATE_PROCEDURE.md \
        scripts/supplement_tracker.py

git commit -m "Update regulatory timelines: [summary]

- Updated [supplement_type] review period per [CFR/Guidance]
- Effective date: YYYY-MM-DD
- Source: [FDA source citation]
- Archived previous timeline to historical section

FDA-XX (if applicable)"
```

### Step 10: Notify Stakeholders

**Internal Notification:**
- Update team via Slack/email about timeline changes
- Schedule code review if major changes
- Update Linear ticket (e.g., FDA-57) status

**External Notification (if applicable):**
- Update plugin release notes
- Notify users of changed behavior in next release
- Document breaking changes in migration guide

## Example: Updating 30-Day Notice Timeline

**Scenario**: FDA publishes guidance reducing 30-Day Notice review to 15 days effective 2026-04-01.

**Step-by-Step:**

1. **Source**: "Expedited Review of Low-Risk PMA Supplements" (FDA-2026-D-0123), published 2026-03-15

2. **Verify**: Confirmed on FDA.gov, final guidance (not draft)

3. **Backup**:
   ```bash
   cp data/regulatory_timelines.json \
      data/regulatory_timelines.json.backup.20260315_1430
   ```

4. **Update Configuration**:

   Archive current to historical:
   ```json
   {
     "historical_timelines": [
       {
         "version": "1.0",
         "effective_date_range": {
           "start": "1986-05-28",
           "end": "2026-03-31"
         },
         "changes_from_previous": "Initial version",
         "timelines": {
           "30_day_notice": {
             "typical_review_days": 30,
             "cfr_citation": "21 CFR 814.39(e)"
           }
         }
       },
       {
         "version": "2.0",
         "effective_date_range": {
           "start": "2026-04-01",
           "end": null
         },
         "changes_from_previous": "Reduced 30-day notice to 15 days per expedited review guidance",
         "timelines": {
           "30_day_notice": {
             "typical_review_days": 15,
             "cfr_citation": "21 CFR 814.39(e)"
           }
         }
       }
     ]
   }
   ```

   Update current timeline:
   ```json
   {
     "current_timelines": {
       "30_day_notice": {
         "typical_review_days": 15,
         "cfr_citation": "21 CFR 814.39(e)",
         "effective_date": "2026-04-01",
         "last_verified": "2026-03-15",
         "regulatory_notes": "Reduced to 15 days per Expedited Review guidance (2026). Device may be distributed after 15 days unless FDA requests additional information.",
         "guidance_references": [
           "Expedited Review of Low-Risk PMA Supplements (2026)"
         ]
       }
     }
   }
   ```

   Update metadata:
   ```json
   {
     "metadata": {
       "version": "2.0.0",
       "last_updated": "2026-03-15",
       "effective_date": "2026-04-01"
     }
   }
   ```

   Add update history:
   ```json
   {
     "update_history": [
       {
         "date": "2026-03-15",
         "version": "2.0.0",
         "changes": "Reduced 30-Day Notice review period from 30 to 15 days",
         "updated_by": "RA Professional",
         "verification_status": "VERIFIED",
         "source": "FDA Guidance: Expedited Review of Low-Risk PMA Supplements (2026)",
         "federal_register_citation": null
       }
     ]
   }
   ```

5. **Validate**: `python3 -m json.tool data/regulatory_timelines.json > /dev/null`

6. **Test**: `python3 supplement_tracker.py --pma P170019`

7. **Commit**:
   ```bash
   git commit -m "Update 30-day notice timeline to 15 days

   - Reduced review period per FDA Expedited Review guidance
   - Effective date: 2026-04-01
   - Source: FDA-2026-D-0123
   - Archived v1.0 timeline to historical section"
   ```

## Rollback Procedure

If update causes issues:

1. **Immediate Rollback**:
   ```bash
   # Restore from backup
   cp data/regulatory_timelines.json.backup.YYYYMMDD_HHMMSS \
      data/regulatory_timelines.json

   # Verify restoration
   python3 supplement_tracker.py --pma P170019
   ```

2. **Git Rollback**:
   ```bash
   # Revert to previous commit
   git log --oneline data/regulatory_timelines.json
   git checkout <COMMIT_HASH> -- data/regulatory_timelines.json
   ```

3. **Document Rollback**:
   ```json
   {
     "update_history": [
       {
         "date": "YYYY-MM-DD",
         "version": "X.Y.Z-rollback",
         "changes": "Rolled back to version X.Y.Z due to [reason]",
         "updated_by": "RA Professional",
         "verification_status": "ROLLBACK"
       }
     ]
   }
   ```

## Quarterly Verification Procedure

**Frequency**: Every 3 months (January, April, July, October)

**Purpose**: Ensure timelines remain current even if no changes occurred.

**Procedure**:

1. Review FDA sources for changes:
   - Check FDA.gov for new PMA guidance documents
   - Review Federal Register for 21 CFR 814 amendments
   - Check MDUFA commitments for timeline updates

2. If no changes found:
   - Update `last_verified` dates in all `current_timelines` entries
   - Update `metadata.last_updated`
   - Add verification entry to `update_history`:

   ```json
   {
     "date": "YYYY-MM-DD",
     "version": "X.Y.Z",
     "changes": "Quarterly verification - no timeline changes",
     "updated_by": "RA Professional",
     "verification_status": "VERIFIED_CURRENT"
   }
   ```

3. Commit verification:
   ```bash
   git commit -m "Quarterly timeline verification - no changes"
   ```

## Contact and Escalation

**For Questions:**
- Technical issues: Development team lead
- Regulatory interpretation: RA professional or regulatory affairs manager
- CFR citation verification: Legal/compliance team

**Escalation Criteria:**
- Conflicting FDA guidance on timelines
- Ambiguous CFR language requiring interpretation
- Timeline changes with immediate effective date (<30 days)
- Retroactive timeline changes affecting historical data

**Escalation Process:**
1. Document conflict/ambiguity
2. Contact RA manager for interpretation
3. If unresolved, contact FDA via Q-Submission
4. Document resolution in update history

## Compliance Notes

- **CRITICAL**: Only RA professionals or qualified personnel should update timelines
- Timeline changes must be based on official FDA sources
- All updates require independent verification before production deployment
- Historical timelines must never be modified (append-only)
- Configuration updates may affect regulatory strategy - stakeholder review required

## Version History

| Version | Date       | Changes                                      |
|---------|------------|----------------------------------------------|
| 1.0.0   | 2026-02-17 | Initial version - FDA-57 refactoring         |

## Appendix A: Configuration File Structure

```
regulatory_timelines.json
├── metadata                     # File metadata and versioning
├── current_timelines           # Active timelines (used by code)
│   ├── 180_day_supplement
│   ├── real_time_supplement
│   ├── 30_day_notice
│   ├── panel_track_supplement
│   ├── pas_related
│   ├── manufacturing_change
│   └── other_unclassified
├── historical_timelines        # Archived timelines (audit trail)
├── cfr_citations              # CFR reference metadata
├── update_history             # Change log
└── validation_rules           # Schema validation rules
```

## Appendix B: Timeline Type Mapping

| Configuration Key        | CFR Section      | Supplement Type              |
|-------------------------|------------------|------------------------------|
| 180_day_supplement      | 21 CFR 814.39(d) | 180-Day Supplement           |
| real_time_supplement    | 21 CFR 814.39(c) | Real-Time Supplement         |
| 30_day_notice           | 21 CFR 814.39(e) | 30-Day Notice                |
| panel_track_supplement  | 21 CFR 814.39(f) | Panel-Track Supplement       |
| pas_related             | 21 CFR 814.82    | Post-Approval Study Related  |
| manufacturing_change    | 21 CFR 814.39    | Manufacturing Change         |
| other_unclassified      | 21 CFR 814.39    | Other/Unclassified           |

## Appendix C: FDA Information Sources

**Official FDA Resources:**
- FDA CDRH Homepage: https://www.fda.gov/medical-devices
- PMA Guidance Documents: https://www.fda.gov/medical-devices/premarket-approval-pma
- Federal Register: https://www.federalregister.gov/
- Electronic CFR: https://www.ecfr.gov/current/title-21/chapter-I/subchapter-H/part-814
- MDUFA Performance Goals: https://www.fda.gov/industry/fda-user-fee-programs/medical-device-user-fee-amendments-mdufa

**Subscription Services:**
- FDA Email Updates: https://public.govdelivery.com/accounts/USFDA/subscriber/new
- Federal Register Daily Email: https://www.federalregister.gov/reader-aids/using-federalregister-gov/email-alerts

---

**Document Control:**
- Maintained by: Regulatory Affairs Team
- Review frequency: Annually or upon FDA regulatory changes
- Distribution: Internal RA team, development team, QA team
