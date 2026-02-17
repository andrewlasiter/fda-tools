# TICKET-005: IDE Pathway Support - Executive Summary

**Created:** 2026-02-17
**Business Analyst:** Claude Code
**Status:** Ready for Implementation

---

## Challenge

Build IDE (Investigational Device Exemption) pathway support from scratch **without direct FDA API access** for IDE approvals. The plugin must provide meaningful value using alternative data sources and regulatory frameworks.

---

## Strategic Recommendations

### 1. MVP-First Phased Approach ✅ RECOMMENDED

Break the 100-140 hour Epic into **5 implementable phases** with clear go/no-go decision points:

| Phase | Deliverable | Effort | Priority | Value |
|-------|------------|--------|----------|-------|
| **Phase 1** | SR/NSR Determination + IDE Pre-Sub | 20-30 hrs | **HIGH** | 40-60 hr time savings/study |
| **Phase 2** | IDE Protocol Generator + Consent Template | 30-40 hrs | **HIGH** | 20-30 hr time savings/study |
| **Phase 3** | Sample Size Calculator Enhancements | 15-20 hrs | MEDIUM | Enables Phase 2 quality |
| **Phase 4** | IRB Package Generator | 12-18 hrs | MEDIUM | 8-12 hr time savings/study |
| **Phase 5** | ClinicalTrials.gov Enhanced Integration | 8-12 hrs | MEDIUM | Incremental UX improvement |

**Total:** 93-132 hours (within original estimate)

---

## Key Features to Implement First

### Phase 1: SR vs NSR Determination Workflow (MVP Priority)

**Why This First:**
- Addresses #1 user pain point (risk classification uncertainty)
- Low complexity, immediate value
- Enables all downstream IDE workflows
- Only feature requiring validation (≥90% accuracy target)

**Deliverable:**
Command: `/fda-tools:ide-risk-assessment --product-code CODE`

Generates determination report with:
- Automated decision tree (21 CFR 812.3(m) - 4 risk criteria)
- Regulatory citations and rationale
- Confidence level (HIGH/MEDIUM/LOW)
- Recommendation (proceed vs FDA Pre-Sub for official determination)

**Validation Approach:**
Test against 20 known IDE studies with documented SR/NSR classifications
- Target: ≥90% agreement (18/20 correct)
- Method: ClinicalTrials.gov study records + published FDA guidance examples

**Integration:** Auto-populates IDE Pre-Sub template (existing `ide_presub.md` template ready)

---

### Phase 2: IDE Protocol Generator (High Value)

**Why This Second:**
- Saves 20-30 hours per IDE study (80% of manual protocol drafting eliminated)
- Highest ROI feature after SR/NSR determination
- Requires Phase 1 risk determination as input

**Deliverable:**
Command: `/fda-tools:ide-protocol --project NAME`

Generates 21 CFR 812.25-compliant Investigational Plan with 8 required sections:
1. Purpose of Investigation
2. Protocol (study design, sample size, endpoints, statistical plan)
3. Risk Analysis (auto-populated from MAUDE)
4. Device Description (from device_profile.json)
5. Monitoring Procedures (DSMB charter for SR devices)
6. Labeling
7. Informed Consent (21 CFR Part 50 template)
8. IRB Information

**Integration Points:**
- `/fda-tools:calc sample-size` → Auto-populate power analysis
- `/fda-tools:trials` → Extract precedent study designs and endpoints
- `/fda-tools:safety` → Device-specific risks from MAUDE
- `/fda-tools:standards` → Applicable standards (ISO 14155, ISO 14971)

---

## Data Sources (No FDA IDE API)

Since no FDA IDE API exists, we leverage:

### 1. Regulatory Framework (21 CFR 812) - PRIMARY SOURCE ✅
- SR/NSR criteria (21 CFR 812.3(m))
- IDE application requirements (21 CFR 812.20)
- Compliance obligations (21 CFR 812.150)
- Informed consent requirements (21 CFR Part 50)
- **Reliability:** 100% (statutory requirements)
- **Maintenance:** Monitor Federal Register quarterly

### 2. ClinicalTrials.gov API v2 - EXTERNAL API ✅
- IDE study discovery (SR devices must register per 42 CFR Part 11)
- Study design patterns and benchmarking
- Enrollment statistics and primary endpoints
- **Reliability:** 95%+ (mandatory registration for SR IDE studies)
- **Coverage Limitation:** NSR studies exempt from registration
- **Current Integration:** `/fda-tools:trials` command already functional

### 3. Existing Plugin Data - INTERNAL ✅
- MAUDE adverse events (device-specific risks)
- 510(k) predicate devices (risk precedents)
- Published literature (clinical evidence)
- Applicable standards (ISO 14155)
- **Reliability:** Reuses validated Phase 1-2 enrichment pipelines

### 4. FDA Guidance Documents - REFERENCE ✅
- *Significant Risk and Nonsignificant Risk Medical Device Studies* (2006)
- *IDEs for Early Feasibility Medical Device Clinical Studies* (2013)
- *Adaptive Designs for Medical Device Clinical Studies* (2016)
- **Reliability:** 100% (official FDA guidance)

---

## Critical Success Factors

### 1. SR/NSR Validation (≥90% Accuracy) 🎯

**Requirement:** Tool must achieve ≥90% agreement with FDA determinations

**Validation Plan:**
- Assemble 20 test cases (5 implantable, 5 life-supporting, 5 minimally invasive, 5 borderline)
- Compare tool output vs documented FDA determinations
- Calculate accuracy: (Correct) / (Total) × 100%
- If <90% → Refine decision tree and re-test

**Acceptance:** 18/20 correct classifications = 90% accuracy ✅

**Timeline:** Complete before Phase 1 release (Week 8)

**Budget:** $3K-5K for regulatory consultant validation study

---

### 2. Market Validation (5 Beta Users)

**Requirement:** Recruit ≥5 beta testers for Phase 1 before investing in Phase 2

**Target Segment:**
- Small-to-mid-sized device companies
- First-time IDE sponsors
- Budget: <$100K for clinical study consulting
- Pain Point: IDE risk classification uncertainty

**Beta Testing:**
- Phase 1 release to beta users (Week 9)
- Collect feedback on SR/NSR determination accuracy and usability
- Measure time savings vs manual process

**Go/No-Go Criteria:**
- ≥4/5 beta users find tool valuable
- ≥90% SR/NSR validation accuracy
- No critical bugs identified
- **If PASS:** Proceed to Phase 2-3
- **If FAIL:** Refine Phase 1, delay Phase 2

---

### 3. Regulatory Compliance & Disclaimers

**Critical:** Tool must NOT provide regulatory advice or create false confidence

**Disclaimers Required:**
```markdown
⚠️ **IMPORTANT DISCLAIMER**

This SR/NSR determination is AI-generated for preliminary planning only.
FDA is the final arbiter of SR vs NSR classification (21 CFR 812.66).

For borderline cases, submit a formal request to FDA for official determination
via Pre-Submission meeting.

NOT REGULATORY ADVICE. Verify independently with qualified regulatory professionals.
```

**Legal Risk Mitigation:**
- Prominent disclaimers on all outputs
- "Research tool" vs "regulatory decision-maker" positioning
- Liability insurance coverage
- Regulatory consultant review of templates

---

## Recommended Implementation Sequence

### Q2 2026: MVP Release (Phases 0-2)

**Weeks 1-3:** Phase 0 (Foundation) + Phase 1 (SR/NSR Determination)
- Establish IDE data structures
- Build SR/NSR decision tree
- Validate against 20 test cases
- Beta release to 5 users

**Weeks 4-6:** Phase 2 (IDE Protocol Generator)
- Build 21 CFR 812.25 template
- Integrate with existing commands (calc, safety, trials)
- Generate informed consent template

**Weeks 7-9:** Phase 3 (Sample Size Enhancements)
- Add superiority/equivalence/survival designs
- Validate formulas against FDA guidance
- Integrate into protocol generator

**Weeks 10-13:** Beta Testing, Validation, Refinement
- Collect user feedback
- Refine templates based on real-world usage
- Complete documentation

### Q3 2026: Production Release + Enhancements

**Week 14:** Production Release (Phases 0-3)
- Target: ≥25 active users
- User satisfaction: ≥4.0/5.0

**Weeks 15-18:** Phase 4 (IRB Package) + Phase 5 (ClinicalTrials.gov)
- IRB submission checklist and document assembly
- Enhanced IDE study pattern analysis
- Predicate study design recommendations

**Weeks 19-26:** Growth & Marketing
- User case studies
- Blog posts and webinars
- Enterprise feature development

---

## Business Value Proposition

### Time Savings Per IDE Study

**Current State (Manual):**
- SR/NSR determination: 6-10 hours
- Protocol drafting: 20-30 hours
- Informed consent creation: 4-6 hours
- IRB package assembly: 8-12 hours
- **Total:** 50-70 hours per IDE study

**Future State (With Tool):**
- SR/NSR determination: 30 minutes (using `/fda-tools:ide-risk-assessment`)
- Protocol drafting: 2 hours (tool generates 80% complete draft)
- Informed consent: 1 hour (auto-populated from protocol)
- IRB package: 1 hour (automated assembly)
- **Total:** 8-10 hours per IDE study

**Time Savings:** 40-60 hours (80-85% reduction) per IDE study

**Value:** At $200/hour RA consultant rate → **$8,000-12,000 savings per study**

---

### Market Sizing

**Total Addressable Market (TAM):**
- ~500 IDE studies initiated annually (FDA data)
- Primarily small-to-mid-sized companies (large companies have in-house expertise)
- Target: 5-10% market penetration = 25-50 users

**Revenue Potential:**
- Pricing: $1,000-2,000/year per user (10-20% of manual cost savings)
- Year 1 Target: 25 users × $1,500 = **$37,500 ARR**
- Year 2 Target: 50 users × $1,500 = **$75,000 ARR**

**Competitive Positioning:**
- **MasterControl Clinical Excellence:** $50K-100K/year (overkill for small studies)
- **Veeva Vault CTMS:** $100K+/year (enterprise-only)
- **Manual spreadsheets/Word:** Free but 50-70 hours per study
- **Our Tool:** $1K-2K/year, saves 40-60 hours

**Market Gap:** Only affordable IDE planning tool for small-to-mid-sized device companies

---

## Risk Assessment

### HIGH PRIORITY RISKS

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| **R1: SR/NSR validation <90% accuracy** | MEDIUM | HIGH | Pre-validation with 10 test cases; engage regulatory consultant if <90% |
| **R4: Limited market demand (IDE niche)** | MEDIUM | HIGH | Phase 1 MVP to gauge adoption; target ≥5 beta users before Phase 2 investment |
| **R5: Template legal liability** | LOW | HIGH | Prominent disclaimers; "not regulatory advice"; liability insurance |

### MEDIUM PRIORITY RISKS

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| **R6: IRB requirements vary by institution** | MEDIUM | MEDIUM | Generic templates + customization guide; support WIRB/Advarra (40% market) |
| **R8: Informed consent institutional policies** | MEDIUM | MEDIUM | Template provides federal minimum; users add institution-specific language |

### LOW PRIORITY RISKS

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| **R2: 21 CFR 812 amendment** | LOW | MEDIUM | Monitor Federal Register quarterly; version templates for rollback |
| **R3: ClinicalTrials.gov API rate limits** | LOW | LOW | Implement caching; 1 req/2 sec (well below 50 req/min limit) |

---

## Resource Requirements

### Development Team

| Role | Hours | Cost Estimate |
|------|-------|---------------|
| Developer | 91 hours | Internal resource |
| Business Analyst | 19 hours | Internal resource (this plan) |
| QA Engineer | 22 hours | Internal resource |
| **Total Internal:** | **132 hours** | **~$20K-30K** (at blended rate) |

### External Consultants

| Resource | Purpose | Cost | Timeline |
|----------|---------|------|----------|
| Regulatory Consultant | SR/NSR validation study | $3K-5K | Week 8 |
| Biostatistician | Sample size formula validation | $1K-2K | Week 7 |
| Beta Testers (5 users) | Phase 1 testing | FREE (incentivize with free license) | Weeks 9-13 |
| **Total External:** | | **$4K-7K** | |

**Total Budget:** $24K-37K (development + external validation)

**Payback Period:** 3-5 paid users × $1,500 = $4.5K-7.5K ARR → 3-8 months to breakeven

---

## Success Metrics

### Phase 1 (MVP) Success Criteria

| Metric | Target | Timeline |
|--------|--------|----------|
| SR/NSR Validation Accuracy | ≥90% (18/20 test cases) | Week 8 |
| Beta User Adoption | ≥5 users recruited | Week 9 |
| User Satisfaction | ≥4.0/5.0 rating | Week 13 |
| Time Savings (SR/NSR task) | ≥5 hours saved vs manual | Week 13 |

**Go/No-Go Decision:** If ≥90% accuracy + ≥4/5 users satisfied → Proceed to Phase 2

### Production Release Success Criteria

| Metric | Target | Timeline |
|--------|--------|----------|
| Active Users | ≥25 users | Week 26 (Q3 2026) |
| User Satisfaction | ≥4.0/5.0 rating | Week 26 |
| Time Savings (Full IDE workflow) | ≥40 hours saved/study | Week 26 |
| Critical Bugs | <5 critical issues | Ongoing |
| Revenue | $10K-25K ARR | Q4 2026 |

---

## Recommended Next Steps

### Immediate Actions (This Week)

1. ✅ **Review implementation plan** with Product Owner and Technical Lead
2. **Prioritize phases** - Confirm Phase 1-2 as MVP, defer Phase 4-5 if resource-constrained
3. **Recruit beta testers** - Identify 5 target companies for Phase 1 validation
4. **Schedule validation study** - Engage regulatory consultant for SR/NSR validation (Week 8)

### Short-Term Actions (Next 2 Weeks)

5. **Assign resources** - 1 developer + 1 QA for 11-week sprint
6. **Kick off Phase 0** - Establish IDE data structures and template architecture
7. **Assemble validation dataset** - Collect 20 IDE study test cases with known SR/NSR classifications

### Medium-Term Actions (Weeks 3-9)

8. **Develop Phase 1** - SR/NSR determination tool
9. **Execute validation study** - Test against 20 cases, refine if <90% accuracy
10. **Beta release** - Deploy to 5 beta users, collect feedback

### Long-Term Actions (Weeks 10-26)

11. **Develop Phase 2-3** - IDE protocol generator + sample size enhancements
12. **Production release** - Public launch with validated features
13. **User growth** - Marketing, case studies, enterprise sales

---

## Conclusion

TICKET-005 (IDE Pathway Support) is **feasible and valuable** despite the lack of FDA IDE API access. By leveraging:
- Regulatory frameworks (21 CFR 812)
- ClinicalTrials.gov API (existing integration)
- Plugin's existing data enrichment pipelines (MAUDE, literature, standards)

We can deliver a tool that saves **40-60 hours per IDE study** and addresses the #1 pain point (SR/NSR risk classification uncertainty) for small-to-mid-sized device companies.

**Recommended Approach:** Phased MVP-first implementation with validation at each stage.

**Critical Success Factor:** Achieve ≥90% SR/NSR determination accuracy validated by independent regulatory consultant.

**Business Case:** $24K-37K investment → $37.5K ARR (Year 1) → 3-8 month payback period.

**Risk Level:** MEDIUM (regulatory validation required, niche market, but clear value proposition)

**Recommendation:** ✅ **PROCEED** with Phase 0-1 (Foundation + SR/NSR Determination) as MVP, with go/no-go decision after beta testing.

---

## Document References

- **Full Implementation Plan:** `/TICKET-005-IDE-PATHWAY-IMPLEMENTATION-PLAN.md` (82 pages)
- **IDE Pathway Research:** `/docs/planning/IDE_PATHWAY_SPECIFICATION.md` (678 lines)
- **Original Ticket:** `/docs/planning/IMPLEMENTATION_TICKETS.md` (TICKET-005, lines 262-316)

**Contact:** Business Analyst Team
**Status:** READY FOR EXECUTIVE REVIEW & APPROVAL
**Next Action:** Product Owner decision on Phase 1 funding and resource allocation
