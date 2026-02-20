---
description: Analyze aggregated expert evaluation results and generate improvement roadmap
allowed-tools:
  - Read
  - Write
  - Glob
  - Grep
  - Bash
argument-hint: "[--min-evals N] [--output-format html|md|both]"
---

# Analyze Expert Evaluations

Aggregate and analyze expert evaluation reports to generate actionable insights and improvement roadmap.

## Prerequisites

Requires at least 3 expert evaluation reports in:
```
~/fda-510k-data/expert-evaluations/*.md
```

## Execution Steps

### Step 1: Discover Evaluation Reports

Use Glob to find all expert evaluation reports:

```bash
pattern: "*/expert-evaluations/*.md"
```

Exclude the aggregated results file itself:
```
!AGGREGATED_RESULTS.md
```

### Step 2: Parse Each Evaluation

For each report, extract:

#### Quantitative Data
- Overall score (X/60)
- Individual dimension scores (Accuracy, Time Savings, etc.)
- Domain
- Experience level
- Time comparison (plugin vs. raw AI)

#### Qualitative Data
- What worked well (themes)
- What didn't work (issues)
- What's missing (feature requests)
- Would use in workflow (yes/no/maybe)

### Step 3: Calculate Aggregate Statistics

#### Overall Metrics
```
Average Total Score: [sum of all scores] / [number of evals]
Score Distribution: Excellent (50-60), Good (40-49), Fair (30-39), Poor (<30)
Completion Rate: [evals completed] / [evals started]
```

#### Dimension Averages
For each of 6 dimensions:
```
Average Score: [sum] / [N]
Range: [min] - [max]
Top Rating %: [count of 9-10 ratings] / [N] * 100
```

#### Domain Breakdown
Group scores by domain:
```
Regulatory Affairs: [avg score], [N evals]
Clinical/Medical: [avg score], [N evals]
Quality/Compliance: [avg score], [N evals]
R&D Engineering: [avg score], [N evals]
Safety/Post-Market: [avg score], [N evals]
```

### Step 4: Identify Themes

#### Strengths (Mentioned by ≥50% of experts)
Use pattern matching to find common positive themes:
- "time sav*"
- "accurate"
- "easy to use"
- "comprehensive"
- "automated"

Count frequency and rank by prevalence.

#### Weaknesses (Mentioned by ≥30% of experts)
Use pattern matching for negative themes:
- "missing"
- "slow"
- "error"
- "confusing"
- "incomplete"

#### Feature Requests (≥30% of experts)
Extract explicit feature requests:
- "would be better if"
- "wish it could"
- "missing feature"
- "should add"

### Step 5: Domain-Specific Insights

For each domain, identify:
1. **Top Use Case** - Most common scenario tested
2. **Most Valuable Feature** - Highest-rated capability
3. **Critical Gap** - Most frequently mentioned missing feature

### Step 6: Time Savings Analysis

Calculate average time savings by domain:
```
Time Saved (%) = (Raw AI Time - Plugin Time) / Raw AI Time * 100
```

Group by:
- Domain
- Scenario type
- Expert experience level

### Step 7: Adoption Likelihood

Calculate percentages:
```
Would use in regular workflow: [count "yes"] / [N] * 100%
Would recommend to colleagues: [count "yes" in feedback] / [N] * 100%
Would pay for this tool: [count "yes" if asked] / [N] * 100%
```

### Step 8: Build Improvement Roadmap

Categorize improvements by urgency:

#### Must-Have (Blockers for >50% of experts)
Issues preventing adoption or causing major problems.

**Criteria:**
- Mentioned by >50% of experts
- Rated as "critical" or "blocker"
- Required for specific domain use

#### Should-Have (Requested by 30-50% of experts)
Important improvements that significantly enhance value.

**Criteria:**
- Mentioned by 30-50% of experts
- Rated as "high priority"
- Solves common pain points

#### Nice-to-Have (Requested by <30% of experts)
Enhancements that add polish or niche value.

**Criteria:**
- Mentioned by <30% of experts
- Rated as "nice to have"
- Domain-specific or edge cases

### Step 9: Generate Aggregated Report

Create comprehensive report:

**File:** `~/fda-510k-data/expert-evaluations/AGGREGATED_RESULTS.md`

Include:
1. Executive Summary (1 page)
2. Quantitative Results (scores, distributions, rankings)
3. Qualitative Insights (themes, quotes, patterns)
4. Domain-Specific Analysis (by expert type)
5. Improvement Roadmap (prioritized list)
6. Plugin vs. Raw AI Comparison (when to use each)
7. Representative Quotes (impactful feedback)
8. Conclusions and Recommendations

### Step 10: Generate Visual Dashboard (Optional)

If `--output-format html` or `--output-format both`:

**File:** `~/fda-510k-data/expert-evaluations/AGGREGATED_RESULTS.html`

Include:
- Bar charts for dimension scores
- Pie charts for domain distribution
- Scatter plots for time savings
- Word clouds for common themes
- Interactive filtering by domain

## Output Structure

### Markdown Report

```markdown
# Aggregated Expert Evaluation Results

**Total Evaluations:** [N]
**Evaluation Period:** [Start Date] - [End Date]
**Plugin Version:** 5.22.0

## Executive Summary

[3-5 sentence summary of key findings]

**Overall Score:** [X/60] ([Excellent/Good/Fair/Poor])
**Top Strength:** [Most praised aspect]
**Top Weakness:** [Most criticized aspect]
**Adoption Rate:** [X%] would use in regular workflow

## Expert Demographics

| Domain | Count | Avg Experience | Avg Score |
|--------|-------|----------------|-----------|
| Regulatory Affairs | [N] | [X years] | [Y/60] |
| Clinical/Medical | [N] | [X years] | [Y/60] |
| Quality/Compliance | [N] | [X years] | [Y/60] |
| R&D Engineering | [N] | [X years] | [Y/60] |
| Safety/Post-Market | [N] | [X years] | [Y/60] |
| **TOTAL** | **[N]** | **[X years]** | **[Y/60]** |

## Overall Scores

### Score Distribution

| Category | Range | Count | Percentage |
|----------|-------|-------|------------|
| Excellent | 50-60 | [N] | [X%] |
| Good | 40-49 | [N] | [X%] |
| Fair | 30-39 | [N] | [X%] |
| Poor | <30 | [N] | [X%] |

### Dimension Averages

| Dimension | Avg Score | Range | Top Rating % | Trend |
|-----------|-----------|-------|--------------|-------|
| Accuracy | [X/10] | [min-max] | [X%] | [↑/→/↓] |
| Time Savings | [X/10] | [min-max] | [X%] | [↑/→/↓] |
| Completeness | [X/10] | [min-max] | [X%] | [↑/→/↓] |
| Ease of Use | [X/10] | [min-max] | [X%] | [↑/→/↓] |
| Data Quality | [X/10] | [min-max] | [X%] | [↑/→/↓] |
| Value vs. Raw AI | [X/10] | [min-max] | [X%] | [↑/→/↓] |

## Key Findings

### Strengths (≥50% of experts)

1. **[Strength 1]** - [X%] of experts
   - "[Representative quote]"
   - Domains: [List]

2. **[Strength 2]** - [X%] of experts
   - "[Representative quote]"
   - Domains: [List]

3. **[Strength 3]** - [X%] of experts
   - "[Representative quote]"
   - Domains: [List]

### Weaknesses (≥30% of experts)

1. **[Weakness 1]** - [X%] of experts
   - "[Representative quote]"
   - Domains: [List]
   - Severity: [Critical/High/Medium]

2. **[Weakness 2]** - [X%] of experts
   - "[Representative quote]"
   - Domains: [List]
   - Severity: [Critical/High/Medium]

### Missing Features (≥30% of experts)

1. **[Feature 1]** - [X%] of experts
   - "[What they want]"
   - Use case: [Description]
   - Requesting domains: [List]

2. **[Feature 2]** - [X%] of experts
   - "[What they want]"
   - Use case: [Description]
   - Requesting domains: [List]

## Domain-Specific Insights

[For each domain with ≥2 evaluations]

### [Domain] ([N] experts, Avg: [X/60])

**Demographics:**
- Experience range: [min-max] years
- Common device types: [list]

**Top Use Case:** [Most tested scenario]

**Most Valuable Feature:** [Highest-rated capability]
- Average rating: [X/10]
- Quote: "[representative quote]"

**Critical Gap:** [Most requested feature]
- Requested by: [X%] of [domain] experts
- Description: [what's missing]

**Unique Insights:**
- [Insight 1]
- [Insight 2]

## Time Savings Analysis

### Average Time Saved by Domain

| Domain | Raw AI Time | Plugin Time | Time Saved | % Saved |
|--------|-------------|-------------|------------|---------|
| Regulatory Affairs | [X min] | [Y min] | [Z min] | [P%] |
| Clinical/Medical | [X min] | [Y min] | [Z min] | [P%] |
| Quality/Compliance | [X min] | [Y min] | [Z min] | [P%] |
| R&D Engineering | [X min] | [Y min] | [Z min] | [P%] |
| Safety/Post-Market | [X min] | [Y min] | [Z min] | [P%] |

### Time Savings by Scenario Type

| Scenario | Avg Time Saved | % of Experts |
|----------|----------------|--------------|
| Predicate research | [X min] | [Y%] |
| Clinical evidence search | [X min] | [Y%] |
| Safety analysis | [X min] | [Y%] |
| Standards lookup | [X min] | [Y%] |
| Guidance review | [X min] | [Y%] |

## Adoption Likelihood

**Would use in regular workflow:** [X%]
- Yes: [N experts]
- Maybe: [N experts]
- No: [N experts]

**Primary reasons for "Yes":**
1. [Reason 1] - [X% of "yes" responses]
2. [Reason 2] - [X% of "yes" responses]

**Primary reasons for "No":**
1. [Reason 1] - [X% of "no" responses]
2. [Reason 2] - [X% of "no" responses]

**Would recommend to colleagues:** [X%]

**Would pay for this tool:** [X%]
- Estimated acceptable price point: $[X-Y]/month (from feedback)

## Improvement Roadmap

### Must-Have (Blocker for >50% of experts)

**Priority 1.1:** [Improvement]
- **Requested by:** [X%] of experts ([N] experts)
- **Domains:** [List]
- **Impact:** [Description]
- **Effort:** [Low/Medium/High]
- **Quote:** "[representative quote]"

**Priority 1.2:** [Improvement]
- **Requested by:** [X%] of experts
- **Domains:** [List]
- **Impact:** [Description]
- **Effort:** [Low/Medium/High]

### Should-Have (Requested by 30-50% of experts)

**Priority 2.1:** [Improvement]
- **Requested by:** [X%] of experts
- **Domains:** [List]
- **Impact:** [Description]
- **Effort:** [Low/Medium/High]

### Nice-to-Have (Requested by <30% of experts)

**Priority 3.1:** [Improvement]
- **Requested by:** [X%] of experts
- **Domains:** [List]
- **Impact:** [Description]
- **Effort:** [Low/Medium/High]

## Plugin vs. Raw AI Comparison

### When Experts Chose Plugin

**Preferred for:**
1. **[Task type]** - [X%] of experts
   - Why: [Reason]
   - Example: "[quote]"

2. **[Task type]** - [X%] of experts
   - Why: [Reason]
   - Example: "[quote]"

### When Experts Chose Raw AI

**Preferred for:**
1. **[Task type]** - [X%] of experts
   - Why: [Reason]
   - Example: "[quote]"

### Plugin Advantages Identified

1. **[Advantage]** - Mentioned by [X%]
2. **[Advantage]** - Mentioned by [X%]
3. **[Advantage]** - Mentioned by [X%]

### Plugin Disadvantages Identified

1. **[Disadvantage]** - Mentioned by [X%]
2. **[Disadvantage]** - Mentioned by [X%]

## Representative Quotes

### Most Impactful Positive Feedback

> "[Quote highlighting key value]"
>
> — [Expert], [Domain], [Experience]

### Most Critical Feedback

> "[Quote highlighting key issue]"
>
> — [Expert], [Domain], [Experience]

### Most Insightful Suggestion

> "[Quote with actionable insight]"
>
> — [Expert], [Domain], [Experience]

## Conclusions

### Key Takeaways

1. [Takeaway 1]
2. [Takeaway 2]
3. [Takeaway 3]

### Recommended Next Steps

1. **Immediate** (1-2 weeks)
   - [Action 1]
   - [Action 2]

2. **Short-term** (1-2 months)
   - [Action 3]
   - [Action 4]

3. **Long-term** (3-6 months)
   - [Action 5]
   - [Action 6]

### Overall Assessment

[Summary paragraph: Is the plugin valuable? What needs to change? What's the path forward?]

---

**Report Generated:** [Date]
**Total Evaluations:** [N]
**Plugin Version:** 5.22.0
```

## Examples

### Example 1: Analyze all evaluations
```bash
/fda-tools:analyze-expert-evals
```

### Example 2: Require minimum 5 evaluations
```bash
/fda-tools:analyze-expert-evals --min-evals 5
```

### Example 3: Generate both MD and HTML
```bash
/fda-tools:analyze-expert-evals --output-format both
```

## Success Criteria

A successful analysis includes:
- ✓ Clear quantitative metrics (scores, percentages)
- ✓ Identified themes (strengths, weaknesses, requests)
- ✓ Domain-specific insights
- ✓ Prioritized improvement roadmap
- ✓ Actionable next steps
- ✓ Representative quotes for context

## Important Notes

- Requires at least 3 evaluations (use `--min-evals` to override)
- Anonymizes expert names unless they opted in for attribution
- Generates both summary and detailed analysis
- Updates automatically as new evaluations are added
- Can be re-run anytime to get updated aggregation
