---
description: Simulate expert panel evaluation with AI regulatory experts from diverse medical device domains
allowed-tools:
  - Task
  - Write
  - Read
  - Bash
argument-hint: "[--domains all|RA,Clinical,Quality] [--device-types all|cardio,ortho,diagnostic] [--count N]"
---

# Simulate Expert Panel Evaluation

Generate simulated expert evaluations from AI regulatory professionals representing diverse medical device domains and device types.

## Purpose

Before recruiting real experts, simulate a diverse expert panel to:
1. **Test the evaluation framework** - Ensure questions work and make sense
2. **Generate example outputs** - Show what real evaluation reports look like
3. **Identify potential issues** - Find confusing questions or unclear scenarios
4. **Create baseline data** - Establish comparison benchmarks
5. **Demonstrate diversity** - Show how different domains view the plugin

## Expert Personas

Create realistic expert personas with:
- **Domain expertise** (Regulatory Affairs, Clinical, Quality, Engineering, Safety)
- **Device specialization** (Cardiovascular, Orthopedic, Diagnostic, Software, Combination)
- **Experience level** (Junior 2-4 years, Mid 5-9 years, Senior 10+ years)
- **Company type** (Startup, Mid-size, Enterprise)
- **Geographic perspective** (US, EU, International)

## Default Expert Panel (9 Experts)

### 1. Sarah Chen - Senior RA Manager (Cardiovascular)
- **Domain:** Regulatory Affairs
- **Experience:** 12 years
- **Device Types:** Drug-eluting stents, catheters, heart valves (DQY, DTK, NIQ)
- **Company:** Large medical device manufacturer (Boston Scientific type)
- **Expertise:** Predicate strategy, SE analysis, complex 510(k)s
- **Pain Points:** Time-consuming predicate research, tracking standards changes
- **Scenario:** "Find predicates for a drug-eluting balloon catheter (DQY) cleared in 2024"

### 2. Dr. Michael Torres - Clinical Research Director (Orthopedic)
- **Domain:** Clinical/Medical
- **Experience:** 15 years (8 clinical practice + 7 industry)
- **Device Types:** Hip/knee implants, spinal fusion, trauma (KWP, MAX, MNH)
- **Company:** Mid-size orthopedic company
- **Expertise:** Clinical trial design, safety data interpretation, surgeon feedback
- **Pain Points:** Finding relevant clinical evidence, adverse event context
- **Scenario:** "Assess clinical data requirements for a cervical fusion device (MAX)"

### 3. Jennifer Park - Quality/Compliance Manager (Diagnostic IVD)
- **Domain:** Quality/Compliance
- **Experience:** 9 years
- **Device Types:** In vitro diagnostics, point-of-care tests (JJE, LCX)
- **Company:** Diagnostic startup
- **Expertise:** FDA guidance interpretation, warning letter analysis, CAPA
- **Pain Points:** Keeping up with guidance updates, compliance checking
- **Scenario:** "Check compliance requirements for an IVD test system (LCX)"

### 4. David Kim - R&D Engineering Lead (Software/SaMD)
- **Domain:** R&D Engineering
- **Experience:** 10 years
- **Device Types:** AI/ML diagnostic software, clinical decision support (QIH, QJT)
- **Company:** Software-as-Medical-Device startup
- **Expertise:** Software validation, cybersecurity, algorithm transparency
- **Pain Points:** Standards for AI/ML, predicate finding for novel algorithms
- **Scenario:** "Identify testing standards for AI-powered radiology software (QIH)"

### 5. Dr. Rachel Martinez - Post-Market Safety Specialist (General Surgery)
- **Domain:** Safety/Post-Market
- **Experience:** 11 years
- **Device Types:** Surgical staplers, energy devices, access ports (GEI, FRN, KOB)
- **Company:** Large surgical device manufacturer (Ethicon type)
- **Expertise:** MAUDE analysis, recall management, complaint trending
- **Pain Points:** Manual MAUDE searches, predicate recall tracking
- **Scenario:** "Analyze adverse events for electrosurgical devices (GEI) over 5 years"

### 6. Thomas Weber - Junior RA Specialist (Cardiovascular)
- **Domain:** Regulatory Affairs
- **Experience:** 3 years
- **Device Types:** Pacemakers, ICDs, vascular grafts (DSI, DXH, MJR)
- **Company:** Enterprise medical device company (Medtronic type)
- **Expertise:** eSTAR preparation, document assembly, basic predicate research
- **Pain Points:** Learning curve steep, unclear SE requirements
- **Scenario:** "Create SE comparison table for a pacemaker lead (DXH)"

### 7. Dr. Priya Sharma - Clinical Affairs Manager (Combination Products)
- **Domain:** Clinical/Medical
- **Experience:** 7 years (PhD + industry)
- **Device Types:** Drug-eluting devices, biologics on devices (FRO, MQP)
- **Company:** Combination product company
- **Expertise:** Drug-device integration, clinical endpoints, biocompatibility
- **Pain Points:** Finding combination product predicates, dual FDA pathways
- **Scenario:** "Research combination product precedents for drug-eluting wound dressing (FRO)"

### 8. Carlos Rodriguez - Senior Quality Engineer (Orthopedic Robotics)
- **Domain:** Quality/Compliance
- **Experience:** 14 years
- **Device Types:** Surgical robotics, navigation systems (QBH, OZO)
- **Company:** Robotics startup (Intuitive Surgical type)
- **Expertise:** Risk management, IEC 62304, human factors, cybersecurity
- **Pain Points:** Rapidly evolving standards, complex system integration
- **Scenario:** "Validate guidance requirements for robotic surgical system (QBH)"

### 9. Lisa Anderson - R&D Test Engineer (Neurology)
- **Domain:** R&D Engineering
- **Experience:** 6 years
- **Device Types:** Neurostimulators, EEG monitors, brain-computer interfaces (GZB, OLO)
- **Company:** Neurotech mid-size company
- **Expertise:** Electrical safety testing, EMC, MRI compatibility
- **Pain Points:** Standards interpretation, test protocol development
- **Scenario:** "Find performance testing standards for neurostimulator (GZB)"

## Execution Steps

### Step 1: Create Expert Personas

For each expert, define:
```json
{
  "name": "Sarah Chen",
  "title": "Senior RA Manager",
  "domain": "Regulatory Affairs",
  "experience_years": 12,
  "device_types": ["Cardiovascular"],
  "product_codes": ["DQY", "DTK", "NIQ"],
  "company_type": "Enterprise",
  "expertise": ["Predicate strategy", "SE analysis", "Complex 510(k)s"],
  "pain_points": ["Time-consuming predicate research", "Tracking standards changes"],
  "scenario": "Find predicates for a drug-eluting balloon catheter (DQY) cleared in 2024",
  "baseline_command": "Describe the device and ask Claude to find predicates",
  "plugin_command": "/fda-tools:research --product-code DQY --years 2024"
}
```

### Step 2: Run Baseline Scenario (Raw AI)

For each expert persona, simulate their baseline approach:

**Prompt Template:**
```
You are [Name], a [Title] with [X] years of experience in [Domain],
specializing in [Device Types].

Scenario: [Scenario description]

Using Claude AI WITHOUT any special plugins or tools, how would you solve this?
What would you ask Claude? How long would it take? What would you get?

Simulate the realistic process and results.
```

**Capture:**
- Time estimate (realistic)
- Process steps
- Quality of results
- What was difficult
- What was missing

### Step 3: Run Plugin-Assisted Scenario

For the same expert persona, simulate using the plugin:

**Prompt Template:**
```
You are [Name], a [Title] with [X] years of experience in [Domain].

Same scenario: [Scenario description]

Now you have access to: [Plugin Command]

What results do you get? How does it compare to the baseline approach?
What's better? What's still missing?

Be realistic - plugins aren't perfect. What would a real expert notice?
```

**Capture:**
- Time saved
- Quality improvement
- What worked well
- What didn't work
- What's still missing

### Step 4: Structured Ratings

For each expert persona, generate realistic ratings based on their domain and scenario results:

#### Accuracy (0-10)
- High (9-10) if domain-appropriate data
- Medium (7-8) if some gaps
- Low (5-6) if significant issues

Consider:
- RA experts: Predicate defensibility matters most
- Clinical experts: Safety data accuracy critical
- Quality experts: Compliance completeness key
- Engineering experts: Technical specs precision important

#### Time Savings (0-10)
Calculate realistic time difference:
- Baseline: 15-30 min typical
- Plugin: 3-10 min typical
- 75%+ savings = 9-10 rating
- 50-75% savings = 7-8 rating

#### Completeness (0-10)
Domain-specific completeness:
- RA: Predicate data, SE table, citations
- Clinical: Trial data, endpoints, safety
- Quality: Guidance, warnings, compliance
- Engineering: Standards, specs, tests

#### Ease of Use (0-10)
Experience-level adjustment:
- Senior (10+ years): May rate lower (want more control)
- Mid (5-9 years): Rate higher (appreciate automation)
- Junior (2-4 years): Rate highest (need guidance)

#### Data Quality (0-10)
Professional standards:
- Submission-ready formatting
- Proper citations
- Complete tables
- Professional language

#### Value vs. Raw AI (0-10)
Key differentiator:
- Can raw AI extract from 510(k) PDFs? No → High value
- Can raw AI check recalls automatically? No → High value
- Can raw AI generate SE tables? Not well → High value

### Step 5: Qualitative Feedback

Generate realistic feedback based on expert persona:

**What Worked Well:**
- RA expert: "Automatic predicate ranking saved hours"
- Clinical expert: "Trial endpoint comparison was instant"
- Quality expert: "Warning letter patterns identified quickly"
- Engineering expert: "Standards extraction from summaries valuable"
- Safety expert: "MAUDE trend analysis actionable"

**What Didn't Work:**
- RA expert: "Missing shelf life data extraction"
- Clinical expert: "No statistical analysis of trial outcomes"
- Quality expert: "Guidance mapping incomplete for new devices"
- Engineering expert: "Some standards references outdated"
- Safety expert: "MAUDE data lacks root cause categorization"

**What's Missing:**
Domain-specific requests:
- RA: "Flag manufacturer conflicts in predicates"
- Clinical: "Link to published literature from trials"
- Quality: "Auto-check against RTA checklist"
- Engineering: "Performance spec comparison table"
- Safety: "Predictive analytics for emerging issues"

**Would Use in Workflow?**
Realistic adoption based on persona:
- Senior experts (10+ years): 70% yes (appreciate efficiency but cautious)
- Mid-level (5-9 years): 90% yes (see clear value)
- Junior (2-4 years): 95% yes (need the help)

### Step 6: Generate Individual Reports

For each expert, create evaluation report:

**File:** `~/fda-510k-data/expert-evaluations/simulated/[expert-name]_[domain]_[date].md`

Use same format as real expert evaluations.

### Step 7: Run Aggregation

After generating all 9 (or custom count) evaluations:

```bash
/fda-tools:analyze-expert-evals --path ~/fda-510k-data/expert-evaluations/simulated/
```

Generate aggregated report showing:
- Average scores by dimension
- Domain-specific insights
- Common themes across personas
- Improvement priorities

## Diversity Considerations

### Device Type Distribution
- **Cardiovascular:** 22% (2/9 experts)
- **Orthopedic:** 22% (2/9 experts)
- **Diagnostic:** 11% (1/9 experts)
- **Software/SaMD:** 11% (1/9 experts)
- **Surgical:** 11% (1/9 experts)
- **Combination:** 11% (1/9 experts)
- **Robotics:** 11% (1/9 experts)

### Domain Distribution
- **Regulatory Affairs:** 22% (2/9)
- **Clinical/Medical:** 22% (2/9)
- **Quality/Compliance:** 22% (2/9)
- **R&D Engineering:** 22% (2/9)
- **Safety/Post-Market:** 11% (1/9)

### Experience Distribution
- **Junior (2-4 years):** 11% (1/9)
- **Mid (5-9 years):** 44% (4/9)
- **Senior (10+ years):** 44% (4/9)

### Company Type Distribution
- **Startup:** 33% (3/9)
- **Mid-size:** 33% (3/9)
- **Enterprise:** 33% (3/9)

## Expected Outcomes

### Average Scores (Simulated)
Based on realistic expert personas:

| Dimension | Expected Avg | Range |
|-----------|--------------|-------|
| Accuracy | 8.5/10 | 7-10 |
| Time Savings | 9.0/10 | 8-10 |
| Completeness | 7.5/10 | 6-9 |
| Ease of Use | 9.0/10 | 8-10 |
| Data Quality | 8.0/10 | 7-9 |
| Value vs. Raw AI | 9.0/10 | 8-10 |
| **TOTAL** | **51/60** | **44-58** |

### Common Themes (Expected)

**Strengths:**
1. Time savings (90%+ of experts)
2. Automated data extraction (80%+)
3. Ease of use (95%+)

**Weaknesses:**
1. Missing shelf life data (60%+)
2. Incomplete standards in some domains (40%+)
3. Limited statistical analysis (30%+)

**Feature Requests:**
1. IFU comparison section (50%+)
2. Manufacturer conflict flagging (40%+)
3. Performance spec comparison (30%+)

## Implementation

Use Task tool to launch simulation agent:

```
subagent_type: "fda-tools:expert-evaluator"
prompt: "Simulate expert panel evaluation with 9 diverse medical device regulatory experts:
1. Sarah Chen - Senior RA (Cardiovascular, 12y)
2. Dr. Michael Torres - Clinical Director (Orthopedic, 15y)
3. Jennifer Park - Quality Manager (Diagnostic IVD, 9y)
4. David Kim - R&D Lead (Software/SaMD, 10y)
5. Dr. Rachel Martinez - Safety Specialist (General Surgery, 11y)
6. Thomas Weber - Junior RA (Cardiovascular, 3y)
7. Dr. Priya Sharma - Clinical Affairs (Combination, 7y)
8. Carlos Rodriguez - Sr Quality (Robotics, 14y)
9. Lisa Anderson - Test Engineer (Neurology, 6y)

For each expert:
1. Create realistic persona with domain expertise
2. Run baseline scenario (raw AI approach)
3. Run plugin-assisted scenario (single command)
4. Generate realistic ratings based on their domain perspective
5. Provide qualitative feedback (what worked/didn't/missing)
6. Assess adoption likelihood

Generate individual evaluation reports for all 9 experts, then aggregate results.
Save to: ~/fda-510k-data/expert-evaluations/simulated/"
```

## Examples

### Example 1: Simulate full 9-expert panel
```bash
/fda-tools:simulate-expert-panel
```

### Example 2: Simulate only RA experts
```bash
/fda-tools:simulate-expert-panel --domains RA --count 3
```

### Example 3: Simulate cardiovascular device experts
```bash
/fda-tools:simulate-expert-panel --device-types cardio --count 5
```

### Example 4: Quick test with 3 experts
```bash
/fda-tools:simulate-expert-panel --count 3
```

## Validation

Compare simulated results with real expert results (when available):

**Metrics to Compare:**
- Average scores by dimension
- Score distribution patterns
- Common themes and requests
- Domain-specific insights
- Adoption likelihood

**Expected Alignment:**
- Scores should be within ±10% of real experts
- Top 3 strengths should match
- Top 3 weaknesses should overlap
- Feature requests should be similar

**Discrepancies indicate:**
- Simulation too optimistic/pessimistic
- Missing real-world pain points
- Unrealistic expert personas
- Need to adjust simulation parameters

## Benefits of Simulation

1. **Test Framework** - Validate evaluation questions work
2. **Example Outputs** - Show what reports look like
3. **Identify Issues** - Find confusing or ambiguous questions
4. **Training Material** - Use for recruiting real experts
5. **Baseline Data** - Compare against actual expert feedback
6. **Diversity Preview** - See how different domains view plugin
7. **Risk-Free** - No real expert time wasted on broken process

## Limitations

**Simulated experts are NOT substitutes for real experts:**
- ❌ Cannot validate actual accuracy
- ❌ Cannot identify real-world edge cases
- ❌ Cannot provide genuine adoption intent
- ❌ Cannot surface unknown pain points
- ❌ Cannot validate against actual FDA submission experience

**Simulation is useful for:**
- ✓ Testing the evaluation framework
- ✓ Generating example outputs
- ✓ Demonstrating diversity of perspectives
- ✓ Identifying obvious issues
- ✓ Creating baseline expectations

## Next Steps After Simulation

1. **Review simulated results** - Do they make sense?
2. **Refine evaluation questions** - Fix any issues found
3. **Use as recruiting material** - Show examples to real experts
4. **Recruit real experts** - Start with 5-10 actual practitioners
5. **Compare results** - Validate simulation vs. reality
6. **Adjust roadmap** - Real expert feedback takes priority

## Success Criteria

Simulation is successful if:
- ✓ All 9 experts complete evaluation (100% completion)
- ✓ Scores distributed realistically (not all 10s or all 5s)
- ✓ Qualitative feedback is domain-appropriate
- ✓ Common themes emerge across experts
- ✓ Improvement roadmap is actionable
- ✓ Reports are clear and professional

The simulation should feel like realistic expert feedback, not obviously AI-generated responses.
