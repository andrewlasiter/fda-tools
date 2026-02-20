# How to Create Linear Issues from Review

This guide explains how to automatically create all 113 Linear issues from the comprehensive multi-agent review.

## Prerequisites ✅

- ✅ Linear API key stored in `.env` file
- ✅ `requests` library installed (already installed)
- ✅ `python-dotenv` library installed (already installed)
- ✅ `LINEAR_ISSUES_MANIFEST.json` file exists

## Quick Start

### Step 1: Verify Environment

```bash
# Navigate to project root
cd /home/linux/.claude/plugins/marketplaces/fda-tools

# Verify .env file exists and contains API key
cat .env | grep LINEAR_API_KEY
# Should show: LINEAR_API_KEY=lin_api_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

### Step 2: Run the Script

```bash
# From project root
python3 plugins/fda-tools/scripts/create_linear_issues_from_manifest.py
```

### Step 3: Review Results

The script will:
1. Load your Linear API key from `.env`
2. Connect to Linear and find your "FDA Tools" team
3. Create issues from the critical path sections:
   - Foundation issues (ARCH-001, ARCH-002)
   - Security issues (SEC-001, SEC-002, SEC-003, SEC-004)
   - Regulatory issues (REG-001, REG-002, REG-006, REG-008)
   - Testing issues (QA-001, QA-002)
   - DevOps issues (DEVOPS-001, DEVOPS-003, DEVOPS-004)
4. Save results to `linear_issues_created.json`
5. Show summary report

## What the Script Does

### Issue Creation
For each issue, the script creates:
- **Title:** `{ISSUE_ID}: {Description}` (e.g., "SEC-001: Fix XSS vulnerability...")
- **Description:** Formatted markdown with:
  - Category, priority, story points
  - Assigned team
  - CWE/regulatory citations (if applicable)
  - Affected files
  - Dependencies (blocks/requires)
  - Links to review documents
- **Priority:** Maps P0→Urgent, P1→High, P2→Normal
- **Estimate:** Story points (1-64 scale)

### Rate Limiting
- Waits 0.5 seconds between API calls
- Respects Linear's ~100 requests/minute limit
- Total time: ~30-60 seconds for all issues

### Error Handling
- Retries on network errors
- Logs failures with detailed error messages
- Continues creating remaining issues if one fails
- Saves both successful and failed issues to JSON

## Expected Output

```
======================================================================
FDA Tools Plugin - Linear Issue Creator
======================================================================
✓ API key loaded from environment
✓ Found team: FDA Tools (ID: abc123...)
✓ Found manifest: /home/linux/.claude/plugins/marketplaces/fda-tools/LINEAR_ISSUES_MANIFEST.json

🚀 Creating Linear issues...

📋 Foundation Issues:
   Must complete before any other work
  ✓ FDA-1: ARCH-001: Convert to proper Python package...
  ✓ FDA-2: ARCH-002: Centralize configuration...

📋 Security Issues:
   Security vulnerabilities requiring immediate attention
  ✓ FDA-3: SEC-001: Fix XSS vulnerability...
  ✓ FDA-4: SEC-002: User-Agent spoofing...
  ✓ FDA-5: SEC-003: Migrate API keys to keyring...
  ✓ FDA-6: SEC-004: Add file path validation...

📋 Regulatory Issues:
   21 CFR Part 11 compliance requirements
  ✓ FDA-7: REG-001: Implement electronic signatures...
  ✓ FDA-8: REG-002: Complete audit trail...
  ✓ FDA-9: REG-006: Add user authentication...
  ✓ FDA-10: REG-008: Tamper-evident audit logs...

📋 Testing Issues:
   Critical test infrastructure and failures
  ✓ FDA-11: QA-001: Create E2E test infrastructure...
  ✓ FDA-12: QA-002: Fix 47 failing tests...

📋 DevOps Issues:
   Production deployment infrastructure
  ✓ FDA-13: DEVOPS-001: Add Docker containerization...
  ✓ FDA-14: DEVOPS-003: CI/CD pipeline...
  ✓ FDA-15: DEVOPS-004: Production monitoring...

💾 Saving results to: linear_issues_created.json
✓ Results saved

======================================================================
SUMMARY
======================================================================
✓ Issues created: 15
✗ Issues failed:  0
📊 Total:         15

🎉 Successfully created 15 Linear issues!

📋 View created issues in Linear:
   https://linear.app/

📄 Issue details saved to: linear_issues_created.json

======================================================================
```

## Output Files

### `linear_issues_created.json`
Contains details of all created issues:
```json
{
  "created": 15,
  "failed": 0,
  "total": 15,
  "created_issues": [
    {
      "manifest_id": "ARCH-001",
      "linear_id": "abc123...",
      "linear_identifier": "FDA-1",
      "title": "Convert to proper Python package...",
      "url": "https://linear.app/fda-tools/issue/FDA-1",
      "priority": "P0",
      "points": 21,
      "category": "Foundation"
    },
    ...
  ],
  "failed_issues": []
}
```

## Troubleshooting

### Error: "LINEAR_API_KEY not found"
```bash
# Check .env file exists
ls -la .env

# Check .env contains API key
cat .env | grep LINEAR_API_KEY

# Make sure you're running from project root
pwd
# Should be: /home/linux/.claude/plugins/marketplaces/fda-tools
```

### Error: "Team 'FDA Tools' not found"
The script will automatically use your first available team. If you want to use a specific team, you can modify the script or create a team named "FDA Tools" in Linear.

### Error: "API Error - ..."
- Check your Linear API key is valid
- Verify you have permission to create issues
- Check Linear workspace status

### Rate Limiting
If you hit rate limits, the script will automatically wait. You can also adjust `RATE_LIMIT_DELAY` in the script (currently 0.5 seconds).

## Next Steps After Creation

1. **Review Issues in Linear:**
   - Go to https://linear.app/
   - Navigate to your FDA Tools project
   - Review all created issues

2. **Set Up Dependencies:**
   - The script creates issue descriptions with "Blocks:" and "Requires:" fields
   - Manually set up Linear relationships for critical path tracking

3. **Assign Team Members:**
   - Issues are created without assignees
   - Assign based on team recommendations in `LINEAR_ISSUES_BY_TEAM.md`

4. **Create Sprint Milestones:**
   - Sprint 1: Foundation & Security (89 points, issues FDA-1 through FDA-8)
   - Sprint 2: Core Infrastructure (102 points)
   - Sprint 3: Compliance & Integration (89 points)
   - Sprint 4: Quality & DevOps (76 points)

5. **Start Sprint 1:**
   - Begin with ARCH-001 and ARCH-002 (foundation issues)
   - These unblock most other work

## Notes

- **Critical Path Issues Only:** The script currently creates only the 15 critical path issues from the manifest
- **Full Issue Set:** To create all 113 issues, you can modify the script or use the full `issues_summary` section
- **Customization:** Edit the script to adjust priorities, add labels, or modify descriptions

## Support

For issues or questions:
- Review the script source: `plugins/fda-tools/scripts/create_linear_issues_from_manifest.py`
- Check the manifest: `LINEAR_ISSUES_MANIFEST.json`
- Read detailed descriptions: `LINEAR_ISSUES_BY_TEAM.md`
