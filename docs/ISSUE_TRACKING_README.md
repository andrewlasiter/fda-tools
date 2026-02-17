# FDA Tools Plugin - Issue Tracking System

**Welcome!** This directory contains comprehensive issue tracking documentation for the FDA Tools Plugin project.

---

## What's Here?

This issue tracking system consolidates 71+ issues from multiple sources into a unified, maintainable format.

### Core Documents

#### 1. **ISSUE_TRACKING_INDEX.md** (Start Here!)
The master reference document with complete issue inventory.

- **Size:** 5,700+ lines
- **Content:** All 71+ issues, organized by priority and source
- **Best for:** Comprehensive reference, detailed issue information
- **Read time:** 20-30 minutes for full review
- **Sections:**
  - Executive summary
  - Issue inventory by source
  - Status dashboard with metrics
  - Timeline and effort estimates
  - Dependencies and blockers
  - Next actions

**How to use:**
- Bookmark this file as your primary reference
- Use Ctrl+F to search for specific issues
- Check § 2 for issues by source document
- See § 5 for timeline and effort estimates

---

#### 2. **ISSUE_TRACKING_QUICK_REFERENCE.md** (Quick Lookup)
Fast reference guide for finding specific issues.

- **Size:** 300+ lines
- **Content:** Summary tables, quick links, FAQ
- **Best for:** Quick lookups, common questions
- **Read time:** 5-10 minutes
- **Includes:**
  - At-a-glance status
  - Issue categories by effort level
  - Finding issues by status/type
  - Common Q&A
  - Monthly update checklist

**How to use:**
- Use this when you need a quick answer
- Start here before reading the full index
- Check the FAQ for common questions
- Use update checklists for regular maintenance

---

#### 3. **ISSUE_IMPORT_TEMPLATE.md** (Linear Integration)
Guidelines for importing issues into Linear.org project management.

- **Size:** 400+ lines
- **Content:** Templates, import procedures, sync guidance
- **Best for:** Project managers, Linear integration
- **Read time:** 15-20 minutes
- **Includes:**
  - Issue template format
  - Issue-by-issue import guide
  - 4-week sprint plan
  - Bulk import CSV format
  - Verification checklist
  - Labels schema

**How to use:**
- Follow the pre-import checklist
- Use templates when creating each Linear issue
- Import in priority order (URGENT → HIGH → MEDIUM → LOW)
- Run sync procedures monthly

---

#### 4. **ISSUE_TRACKING_IMPLEMENTATION_SUMMARY.md** (This Task)
Summary of what was delivered and how to use it.

- **Size:** 300+ lines
- **Content:** Deliverables overview, verification, next steps
- **Best for:** Understanding the complete system
- **Read time:** 10 minutes
- **Includes:**
  - What was created
  - Source document consolidation
  - Critical issues highlighted
  - Implementation timeline
  - Verification checklist

---

### Automation

#### **scripts/update_issue_index.py**
Python script to maintain the index automatically.

```bash
# View statistics
python3 scripts/update_issue_index.py --stats

# Scan all sources and count issues
python3 scripts/update_issue_index.py --scan

# Verify all cross-references
python3 scripts/update_issue_index.py --verify

# Generate full report
python3 scripts/update_issue_index.py --report

# Update timestamp to today
python3 scripts/update_issue_index.py --update-timestamp
```

---

## Issue Status at a Glance

**Total Issues:** 71+

| Priority | Count | Hours | Status | Deadline |
|----------|-------|-------|--------|----------|
| **URGENT** | 3 | 6-9 | NOT STARTED | This week |
| **HIGH** | 12 | 81-117 | NOT STARTED | Next sprint |
| **MEDIUM** | 18 | 62-87 | NOT STARTED | 3 months |
| **LOW** | 9 | 28-42 | NOT STARTED | Backlog |
| **FUTURE** | 10 | 30-45 | NOT STARTED | v5.37+ |
| **COMPLETED** | 6 | - | DONE | v5.25-v5.36 |

**Estimated Total Effort:** 195-270 hours remaining

---

## Three Urgent Issues (Fix This Week!)

### 1. GAP-034: Compliance Disclaimer
- **Issue:** Standards generation scripts don't show "RESEARCH USE ONLY" warning
- **Effort:** 1-2 hours
- **Risk:** Regulatory exposure
- **Action:** Add CLI banner to standards scripts

### 2. GAP-006: CI/CD Python 3.12
- **Issue:** Tests only run on Python 3.9-3.11, not production Python 3.12
- **Effort:** 3-4 hours
- **Risk:** Untested code path in production
- **Action:** Add Python 3.12 to GitHub Actions matrix

### 3. GAP-012: Atomic Manifest Writes
- **Issue:** Data loss if process crashes during manifest write
- **Effort:** 2-3 hours
- **Risk:** **CRITICAL - Data loss**
- **Action:** Implement write-temp-then-rename pattern

---

## Getting Started

### Step 1: Understand the System (10 minutes)
1. Read this file (you're reading it!)
2. Skim **ISSUE_TRACKING_QUICK_REFERENCE.md**
3. Browse the main index structure

### Step 2: Find Your Issue (5 minutes)
1. Check section 2 of **ISSUE_TRACKING_INDEX.md** for your area
2. Use Ctrl+F to search for specific issues
3. Click to the source document for full details

### Step 3: Plan Work (15 minutes)
1. Review URGENT issues (3 items, ~8 hours this week)
2. Plan HIGH priority for next sprint (12 items, ~100 hours)
3. Assign owners and create Linear issues

### Step 4: Track Progress (5 minutes monthly)
1. Run `python3 scripts/update_issue_index.py --stats`
2. Update Linear with progress
3. Note any new issues or priority changes

---

## Common Workflows

### "I'm a developer - where do I find work?"
1. Check **ISSUE_TRACKING_QUICK_REFERENCE.md** § "By Status"
2. Look at HIGH priority issues assigned to you
3. Open **ISSUE_TRACKING_INDEX.md** for full details
4. Reference source document (TODO.md or GAP-ANALYSIS-REPORT.md)

### "I'm a project manager - how do I track progress?"
1. Open **ISSUE_TRACKING_QUICK_REFERENCE.md** weekly
2. Run `python3 scripts/update_issue_index.py --report` monthly
3. Update Linear issue status
4. Review timeline projections in main index

### "I need to add a new issue - what do I do?"
1. Check **ISSUE_TRACKING_INDEX.md** to avoid duplicates
2. Determine priority (URGENT/HIGH/MEDIUM/LOW)
3. Add to source document (TODO.md or GAP-ANALYSIS-REPORT.md)
4. Create Linear issue using template from **ISSUE_IMPORT_TEMPLATE.md**

### "How do I keep the index updated?"
1. Monthly: Run automation script (`--scan`, `--stats`, `--update-timestamp`)
2. Quarterly: Run full `--report` and review
3. Per-release: Update version numbers and completion status
4. Per-issue: Update source documents, then re-run automation

---

## Document Map

```
                                Main Entry Points
                                    |
                    ____________________|____________________
                   |                    |                    |
                   v                    v                    v
            [I need help]      [I need to work]     [I need to manage]
                   |                    |                    |
                   v                    v                    v
        QUICK_REFERENCE.md    TODO.md + Index    IMPORT_TEMPLATE.md
              (5 min)          (20-30 min)           (15-20 min)
                   |                    |                    |
                   v                    v                    v
        [FAQ, Categories]    [Full details]      [Linear setup]
                   |                    |                    |
                   +----────────────────+────────────────────+
                                       |
                                       v
                            Automation Script
                       update_issue_index.py
                                       |
                    ___________________+___________________
                   |                   |                   |
                   v                   v                   v
            [--stats]          [--report]            [--verify]
            Monthly            Monthly              Before commits
```

---

## Source Documents

This system consolidates issues from multiple sources:

### 1. TODO.md
- Primary roadmap document
- 13 items tracked (6 complete, 7 active)
- TICKET-001 through TICKET-013
- Future enhancements FE-001 through FE-010
- **Status:** v5.36.0 current

### 2. GAP-ANALYSIS-REPORT.md
- Comprehensive gap analysis
- 42 new issues (GAP-001 through GAP-042)
- Never before tracked in tickets
- Categories: Code Quality, Testing, Security, CI/CD, Docs, Architecture, Data, Compliance
- **Status:** 2026-02-16

### 3. TESTING_SPEC.md
- Formal test specification
- 34 test cases (24/34 implemented)
- Marks for test types: smart, sim, integration, performance
- **Status:** 10 tests pending

### 4. TICKET-*.md Files
- Completion reports for delivered features
- Detailed implementation notes
- Test results
- **Status:** v5.25.0-v5.36.0 documented

---

## FAQ

### Q: Where's the complete issue list?
**A:** **ISSUE_TRACKING_INDEX.md** § 2.1 - 2.6 (sections sorted by source)

### Q: How much work is remaining?
**A:** 195-270 hours across 42 new issues + 10 future enhancements

### Q: What should we work on first?
**A:** See **ISSUE_TRACKING_QUICK_REFERENCE.md** § "Getting Started" or ISSUE_TRACKING_INDEX.md § 7 (Next Actions)

### Q: How do I report a new issue?
**A:** Add to TODO.md or GAP-ANALYSIS-REPORT.md, then use ISSUE_IMPORT_TEMPLATE.md to create Linear issue

### Q: Is there a blocker or dependency?
**A:** See **ISSUE_TRACKING_INDEX.md** § 6 - currently no blockers, all dependencies resolved

### Q: How do I keep the index updated?
**A:** See **ISSUE_TRACKING_QUICK_REFERENCE.md** § "Using the Automation Tool" (monthly/quarterly procedures)

### Q: Can I export this to Linear?
**A:** Yes! See **ISSUE_IMPORT_TEMPLATE.md** with templates and bulk import format

### Q: What's the current version?
**A:** v5.36.0 (Smart Auto-Update System). See TODO.md for version history.

---

## Integration Points

### With GitHub
- Issues can link to this index for reference
- PR descriptions can reference ISSUE_TRACKING_INDEX.md
- Automation script can run in Actions

### With Linear
- Templates provided in ISSUE_IMPORT_TEMPLATE.md
- 4-week sprint plan ready to import
- Labels schema defined
- Monthly sync procedures documented

### With CI/CD
- Automation script integrates with test runs
- Coverage metrics tracked
- Test markers align with test spec

---

## Maintenance Calendar

**Weekly:**
- Check QUICK_REFERENCE.md for status
- Update Linear with progress
- Review next actions

**Monthly:**
- Run `update_issue_index.py --scan --stats`
- Generate `--report`
- Update timestamp with `--update-timestamp`
- Commit changes

**Quarterly:**
- Run full `--report`
- Review priorities
- Recalculate effort estimates
- Update timeline projections
- Check for new issues

**Per Release:**
- Update version numbers
- Mark completed items
- Calculate velocity
- Project next release effort

---

## Support & Resources

### Need Help?
1. Check **ISSUE_TRACKING_QUICK_REFERENCE.md** § FAQ
2. Search **ISSUE_TRACKING_INDEX.md** with Ctrl+F
3. Review source documents (TODO.md, GAP-ANALYSIS-REPORT.md)
4. Run automation script for fresh data

### Want to Contribute?
1. Check if issue exists in index
2. Add to TODO.md or GAP-ANALYSIS-REPORT.md
3. Create Linear issue using template
4. Link to ISSUE_TRACKING_INDEX.md in description

### Found a Problem?
1. Check which document needs updating
2. Make correction
3. Run `update_issue_index.py --verify`
4. Commit changes with description

---

## Quick Links

- **Master Index:** [ISSUE_TRACKING_INDEX.md](./ISSUE_TRACKING_INDEX.md)
- **Quick Reference:** [ISSUE_TRACKING_QUICK_REFERENCE.md](./ISSUE_TRACKING_QUICK_REFERENCE.md)
- **Linear Template:** [ISSUE_IMPORT_TEMPLATE.md](./ISSUE_IMPORT_TEMPLATE.md)
- **Implementation Summary:** [ISSUE_TRACKING_IMPLEMENTATION_SUMMARY.md](./ISSUE_TRACKING_IMPLEMENTATION_SUMMARY.md)
- **Automation Script:** [../scripts/update_issue_index.py](../scripts/update_issue_index.py)
- **Roadmap:** [../TODO.md](../TODO.md)
- **Gap Analysis:** [./planning/GAP-ANALYSIS-REPORT.md](./planning/GAP-ANALYSIS-REPORT.md)

---

## Document Information

- **Created:** 2026-02-17
- **Version:** 1.0
- **Owner:** Technical Writer / Documentation Lead
- **License:** Same as parent project
- **Last Updated:** 2026-02-17

---

## Next Steps

1. **Read** this README (5 min) ✓
2. **Review** ISSUE_TRACKING_QUICK_REFERENCE.md (5 min)
3. **Check** ISSUE_TRACKING_INDEX.md for URGENT items (10 min)
4. **Import** issues into Linear using ISSUE_IMPORT_TEMPLATE.md (follow checklist)
5. **Set up** automation script for monthly updates
6. **Start** work on URGENT items (this week!)

**Time to productivity:** 30 minutes

---

**Happy tracking!** 🎯
