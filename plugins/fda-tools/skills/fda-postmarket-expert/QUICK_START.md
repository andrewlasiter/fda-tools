# FDA Post-Market Expert - Quick Start Guide

**Expert:** Dr. James Wilson, PharmD, RAC
**Experience:** 19 years CDRH Office of Surveillance and Biometrics
**Specialties:** MDR reporting, recalls, PMA annual reports, 522 surveillance

---

## When to Use This Expert

Use **fda-postmarket-expert** for:

- ✅ MDR reportability assessments (death, serious injury, malfunction)
- ✅ PMA annual report preparation and completeness review
- ✅ Recall strategy and health hazard evaluation
- ✅ Section 522 post-market surveillance study design
- ✅ Complaint handling and trending analysis
- ✅ CAPA linkage to post-market events
- ✅ Warning Letter risk assessment for post-market violations

**Don't use for:**
- ❌ Pre-market design controls (use `fda-quality-expert`)
- ❌ Software validation (use `fda-software-ai-expert`)
- ❌ Regulatory strategy (use `fda-regulatory-strategy-expert`)

---

## Common Use Cases

### 1. MDR Reportability Question
**Prompt:**
```
I received a complaint about [device name] that [event description].
The patient [outcome]. Do I need to file an MDR?
```

**Expert Will Provide:**
- Decision tree walkthrough
- Reportability conclusion (30-day, 5-day, or no report)
- Report content requirements
- Filing deadline
- Action items

### 2. PMA Annual Report Review
**Prompt:**
```
I'm preparing my PMA annual report for [device name] (PMA P123456).
Review my draft for completeness per 21 CFR 814.84.
```

**Expert Will Provide:**
- Section-by-section checklist (A-F)
- Deficiency identification
- Compliance scoring
- Timeline for remediation
- Warning Letter risk assessment

### 3. Recall Decision Support
**Prompt:**
```
We discovered [defect description] in [device name].
[X units] distributed. [Y events] reported.
Should we initiate a recall? What class?
```

**Expert Will Provide:**
- Health hazard evaluation
- Recall classification (Class I/II/III)
- Correction strategy options
- Customer notification template
- Effectiveness check plan
- FDA notification timeline

### 4. Section 522 Study Protocol
**Prompt:**
```
FDA issued a 522 post-market surveillance order for [device name].
Help me design the study protocol.
```

**Expert Will Provide:**
- Study design framework
- Sample size recommendations
- Endpoint selection
- Data collection plan
- IRB/consent requirements
- Reporting schedule

### 5. Complaint Trending Analysis
**Prompt:**
```
Review our complaint data for [device name] over the last 12 months.
Do we have MDR reporting obligations or CAPA triggers?
```

**Expert Will Provide:**
- Statistical trending analysis
- MDR reportability review
- CAPA triggering criteria
- Trend direction assessment
- Preventive action recommendations

---

## Key Deliverables

### Standard Output Template Includes:
1. **Device Summary** (class, pathway, obligations)
2. **MDR Reporting Assessment** (compliance, timeliness, completeness)
3. **Section 522 Status** (if applicable)
4. **PMA Annual Report Review** (if applicable)
5. **Recall Assessment** (if active recalls)
6. **Complaint Handling Review** (trending, CAPA linkage)
7. **Deficiency Summary** (CRITICAL/MAJOR/MINOR)
8. **Warning Letter Risk** (Low/Medium/High)
9. **Compliance Score** (out of 100)
10. **Prioritized Next Steps** (with deadlines)

---

## Decision Trees Available

### MDR Reportability (21 CFR 803)
```
Event → Death? → YES → 5-Day Report
            ↓ NO
      Serious Injury? → YES → 30-Day Report
            ↓ NO
      Malfunction? → YES → Would recurrence cause death/injury?
                              → YES → 30-Day Malfunction Report
                              → NO → No MDR required
```

### Recall Classification (21 CFR 806)
```
Defect → Probability of serious harm/death?
         ├─ Reasonable → Class I
         ├─ Remote (but temporary harm) → Class II
         └─ Unlikely to cause harm → Class III
```

---

## Critical Timelines to Know

| Event Type | Deadline | Regulation |
|------------|----------|------------|
| MDR - Death | 5 work days | 21 CFR 803.53 |
| MDR - Serious Injury | 30 calendar days | 21 CFR 803.50 |
| MDR - Malfunction | 30 calendar days | 21 CFR 803.50 |
| Recall - FDA Notification | 10 work days | 21 CFR 806.10(c) |
| PMA Annual Report | 6 months post-approval | 21 CFR 814.84 |
| 522 Interim Reports | Per FDA order | 21 CFR 822 |

---

## Expert Tips from Dr. Wilson

### MDR Reporting:
> "The 'became aware' clock starts when ANY employee knows, not just QA/RA. Train your entire organization on MDR obligations."

### Recalls:
> "Always use the 'URGENT' subject line in customer notifications. FDA tracks recall effectiveness, and poor communication triggers Warning Letters."

### PMA Annual Reports:
> "Don't just count complaints - provide statistical trending with Pareto charts and control charts. That's what FDA reviewers expect."

### Section 522:
> "Underpowered studies are the #1 deficiency. Get a biostatistician to calculate sample size properly."

### Complaint Trending:
> "Use the 3-sigma rule: If complaint rates trend outside control limits, you need a CAPA. Don't wait for FDA to tell you."

---

## References & Resources

### FDA Regulations (Primary)
- **21 CFR 803** - Medical Device Reporting
- **21 CFR 806** - Recalls and Corrections
- **21 CFR 814.84** - PMA Annual Reports
- **21 CFR 822** - Postmarket Surveillance

### FDA Guidance (Essential)
- MDR for Manufacturers (2016)
- Recalls Guidance (2019)
- Section 522 Surveillance (2020)

### FDA Databases
- **MAUDE** - MDR search and trending
- **Recalls** - Active and historical recalls
- **522 Studies** - Surveillance order tracking
- **PMA Database** - Approval and annual report status

---

## Warning Letter Red Flags

The expert will flag these **CRITICAL** violations that trigger Warning Letters:

### MDR Reporting:
- ❌ Late 5-day or 30-day reports (even by 1 day)
- ❌ Failure to file baseline reports for new devices
- ❌ Missing follow-up reports after device evaluation
- ❌ Systematic under-reporting of serious injuries

### PMA Annual Reports:
- ❌ Late submission (>6 months post-approval)
- ❌ Incomplete complaint trending (no statistical analysis)
- ❌ Missing post-approval study updates

### Recalls:
- ❌ Late FDA notification (>10 work days)
- ❌ Inadequate health hazard evaluation (risk underestimated)
- ❌ Poor recall effectiveness (<90% customer response)

### Complaint Handling:
- ❌ No MDR reportability evaluation for serious events
- ❌ Complaints not linked to CAPA system
- ❌ Trending analysis missing (complaints reviewed in isolation)

---

## Output Quality Standards

Every expert assessment includes:

- ✅ **CFR Citations** - Specific regulation references
- ✅ **Risk Prioritization** - CRITICAL/MAJOR/MINOR categorization
- ✅ **Actionable Findings** - Every deficiency has a fix
- ✅ **Timeline Emphasis** - Critical deadlines highlighted
- ✅ **Compliance Scoring** - Quantitative assessment (out of 100)
- ✅ **Warning Letter Risk** - Low/Medium/High with drivers
- ✅ **Consent Decree Risk** - For repeat violations
- ✅ **Conservative Approach** - When in doubt, recommend reporting

---

## Example Prompts

### Quick Assessment:
```
Quick MDR reportability check: [brief event description]
```

### Deep Dive:
```
Comprehensive post-market compliance review for [device name].
Include MDR compliance, complaint trending, and CAPA linkage.
```

### Specific Guidance:
```
What are the required elements of a Class I recall notification letter
per 21 CFR 806.10?
```

### Regulatory Research:
```
What is the statistical trending methodology FDA expects
for PMA annual report complaint summaries?
```

---

## File Locations

- **Skill Definition:** `plugins/fda-tools/skills/fda-postmarket-expert/SKILL.md`
- **Agent Config:** `plugins/fda-tools/skills/fda-postmarket-expert/agent.yaml`
- **This Guide:** `plugins/fda-tools/skills/fda-postmarket-expert/QUICK_START.md`
- **Validation:** `plugins/fda-tools/skills/fda-postmarket-expert/VALIDATION_CHECKLIST.md`

---

## Getting Help

For questions about:
- **MDR reportability** → Use Case 1 in SKILL.md (line 673)
- **PMA annual reports** → Use Case 2 in SKILL.md (line 727)
- **Recall strategy** → Use Case 3 in SKILL.md (line 833)
- **General workflow** → Workflow section in SKILL.md (line 45)

---

**Last Updated:** 2026-02-16
**Regulatory Framework:** 21 CFR current as of 2026
**Knowledge Cutoff:** January 2025
