---
description: Start expert evaluation session (for medical device professionals to assess plugin value)
allowed-tools:
  - Task
argument-hint: "[--domain RA|Clinical|Quality|Engineering|Safety]"
---

# Expert Evaluation Session

You are helping a medical device industry expert evaluate the FDA Tools plugin.

## Command Purpose

This command launches a guided evaluation session for domain experts to assess:
1. **Accuracy** - Are results correct and reliable?
2. **Performance** - Does it save time vs. manual work?
3. **Value** - Is it better than using raw AI alone?

## Target Users

- Regulatory Affairs professionals
- Clinical/Medical specialists
- Quality/Compliance engineers
- R&D engineers
- Safety/Post-Market specialists

**Important:** These experts may NOT be technical. Keep it simple.

## Execution Steps

### Step 1: Launch Expert Evaluator Agent

Use the Task tool to launch the expert-evaluator agent:

```
subagent_type: "fda-tools:expert-evaluator"
prompt: "Guide an expert through plugin evaluation. Their domain is: [domain from argument or ask if not provided]"
description: "Expert evaluation session"
```

### Step 2: Agent Takes Over

The expert-evaluator agent will:
1. Ask about their background (domain, experience, devices)
2. Present a relevant scenario
3. Have them try it with raw AI first
4. Guide them through the plugin solution
5. Collect structured feedback
6. Generate evaluation report

### Step 3: Save Results

The agent will automatically save the evaluation report to:
```
~/fda-510k-data/expert-evaluations/[expert-name]_[domain]_[date].md
```

## Examples

### Example 1: Regulatory Affairs Expert
```bash
/fda-tools:expert-eval --domain RA
```

### Example 2: No domain specified (agent will ask)
```bash
/fda-tools:expert-eval
```

### Example 3: Clinical Specialist
```bash
/fda-tools:expert-eval --domain Clinical
```

## What the Expert Will Experience

1. **Introduction** (2 min)
   - Brief overview of evaluation purpose
   - Background questions

2. **Baseline Scenario** (15 min)
   - Try solving a real-world problem with raw Claude AI
   - Document time, process, results

3. **Plugin-Assisted Scenario** (15 min)
   - Solve the SAME problem using plugin
   - Agent guides through simple command
   - Document time, process, results

4. **Structured Feedback** (10 min)
   - Rate 6 dimensions on scale
   - Multiple choice questions (easy!)

5. **Open Feedback** (10 min)
   - What worked well?
   - What didn't work?
   - What's missing?
   - Would you use this?

6. **Domain-Specific Questions** (10 min)
   - Questions specific to their expertise
   - Technical accuracy assessment

**Total Time:** ~60 minutes

## Output

The agent generates a comprehensive evaluation report with:
- Quantitative scores (6 dimensions)
- Qualitative feedback
- Scenario comparison (plugin vs. raw AI)
- Improvement recommendations
- Domain-specific insights

## For Plugin Developers

After collecting 5-10 evaluations, run aggregation:

```bash
/fda-tools:analyze-expert-evals
```

This generates:
- Aggregated scores by dimension
- Common themes and patterns
- Prioritized improvement roadmap
- Domain-specific insights

## Important Notes

- **Be patient** - Experts may not be technical
- **One step at a time** - Don't rush
- **Show value quickly** - First impression matters
- **Honest feedback only** - Create safe space for criticism
- **Document everything** - Every evaluation is valuable

## Success Criteria

A good evaluation session results in:
- ✓ Clear comparison (plugin vs. raw AI)
- ✓ Quantitative ratings
- ✓ Honest qualitative feedback
- ✓ Actionable improvement suggestions
- ✓ Expert would (or wouldn't) use in workflow - and why
