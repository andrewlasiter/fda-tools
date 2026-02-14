# Expert Evaluation Guide
## For Medical Device Professionals (Non-Technical)

**Welcome!** Thank you for participating in the FDA Tools plugin evaluation. This guide will help you assess whether this tool is valuable for your work.

---

## What You'll Be Doing (60 minutes)

You'll compare two approaches to a real-world task:
1. **Approach A:** Using Claude AI normally (no special tools)
2. **Approach B:** Using the FDA Tools plugin

Then you'll tell us which was better and why.

**No technical expertise required!** We'll guide you step-by-step.

---

## Before You Start

### What You Need
- ✓ Access to Claude Code (we'll help you set this up if needed)
- ✓ 60 minutes of uninterrupted time
- ✓ A device or product code you're familiar with
- ✓ Honest opinions (we want the truth, not politeness!)

### What You DON'T Need
- ✗ Programming knowledge
- ✗ Command line experience
- ✗ Claude Code expertise
- ✗ Technical documentation skills

---

## The Evaluation Process

### Step 1: Tell Us About You (5 minutes)

We'll ask you some simple questions:
- What's your primary role? (Regulatory Affairs, Clinical, Quality, etc.)
- How many years have you worked in medical devices?
- What types of devices do you work with?
- What's frustrating about your current workflow?

**Why?** This helps us show you scenarios relevant to YOUR work.

### Step 2: Try It the Normal Way (15 minutes)

We'll give you a realistic scenario from your field. For example:

**If you're in Regulatory Affairs:**
> "Find 3 suitable predicate devices for a cardiovascular catheter that were cleared in the last 2 years."

**If you're in Clinical:**
> "Find clinical trials testing similar devices and summarize the endpoints used."

**If you're in Quality:**
> "Check if any of the predicates for device K240123 have been recalled."

You'll solve this using Claude AI normally - just ask questions like you usually would. We'll time how long it takes and note what you found.

**Important:** Work naturally! Don't try to be perfect. We want to see the real process.

### Step 3: Try It with the Plugin (15 minutes)

Now you'll solve the SAME scenario, but we'll show you ONE simple command to use.

For example:
```
/fda-tools:research --product-code DQY --years 2023-2024
```

**That's it!** Just copy and paste the command we give you.

The plugin will automatically:
- Search FDA databases
- Extract relevant information
- Organize results in tables
- Provide citations and links
- Flag potential issues

We'll time this too and see what the plugin found.

### Step 4: Rate Your Experience (10 minutes)

We'll ask you to rate 6 things on a simple scale:

#### 1. Accuracy
*"Were the plugin's results correct?"*
- Highly accurate (90-100%)
- Mostly accurate (70-89%)
- Somewhat accurate (50-69%)
- Inaccurate (<50%)

#### 2. Time Savings
*"Did the plugin save you time?"*
- Saved 75%+ time
- Saved 50-75% time
- Saved 25-50% time
- No significant time savings

#### 3. Completeness
*"Did you get all the info you needed?"*
- Complete - nothing missing
- Mostly complete - minor gaps
- Incomplete - significant gaps
- Missing critical information

#### 4. Ease of Use
*"Was it easy to use without technical training?"*
- Very easy - intuitive
- Easy - minimal learning curve
- Moderate - required some help
- Difficult - too complex

#### 5. Data Quality
*"Was the output professional quality?"*
- Professional quality - submission ready
- Good quality - minor edits needed
- Acceptable - significant edits needed
- Poor quality - extensive work needed

#### 6. Value vs. Normal AI
*"Was the plugin better than just using Claude normally?"*
- Transformative - couldn't do this with raw AI
- Significant - major improvement
- Moderate - some improvement
- Minimal - not worth the complexity

**No right answers!** Just give us your honest opinion.

### Step 5: Tell Us More (10 minutes)

We'll ask you some open-ended questions:

1. **What worked well?**
   Tell us what you liked. What impressed you?

2. **What didn't work?**
   Tell us what frustrated you. What failed to meet your expectations?

3. **What's missing?**
   What features or data would make this more useful for YOUR work?

4. **What would you change?**
   If you could redesign one thing, what would it be?

5. **Would you actually use this?**
   Would you incorporate this into your regular workflow? Why or why not?

**Be brutally honest!** We need to know what's broken so we can fix it.

### Step 6: Domain-Specific Questions (10 minutes)

Depending on your field, we'll ask specialized questions:

**Regulatory Affairs:**
- Are the predicates defensible for an FDA submission?
- Is the SE comparison table format what you'd expect?
- Are the regulatory citations accurate and current?

**Clinical/Medical:**
- Is the clinical data detection accurate?
- Are the trial search results relevant?
- Does the safety analysis match your clinical judgment?

**Quality/Compliance:**
- Is the guidance mapping comprehensive?
- Are the compliance checks thorough?
- Does the warning letter analysis catch the right patterns?

**R&D Engineering:**
- Are the testing standards complete?
- Is the technical comparison table useful?
- Are the performance requirements accurate?

**Safety/Post-Market:**
- Is the MAUDE analysis actionable?
- Is the recall history assessment complete?
- Are risk flags identified correctly?

---

## What Happens Next

After your evaluation:

1. **We generate a report** - Your feedback is compiled into a structured report
2. **We aggregate results** - After 5-10 experts, we combine all feedback
3. **We identify improvements** - Common themes become our roadmap
4. **We implement changes** - High-priority issues get fixed first
5. **We follow up with you** - You'll hear what improvements we made based on YOUR feedback

---

## Example Scenario (Regulatory Affairs)

Let's walk through what an actual evaluation looks like:

### Background
**Expert:** Sarah, RA Manager, 12 years experience, works with cardiovascular devices

### Scenario Given
> "Find 3 suitable predicates for a drug-eluting balloon catheter (product code DQY) cleared in 2024. Assess their recall history and identify what testing standards they followed."

### Approach A: Normal Claude AI (15 minutes)

Sarah asks Claude:
- "What predicates exist for DQY in 2024?"
- "Which ones are drug-eluting balloons?"
- "Have any been recalled?"
- "What testing standards did they use?"

**Results:**
- Found 2 potentially suitable devices (missed 1 good option)
- Couldn't verify recall status (had to manually check FDA website)
- Testing standards were generic guesses
- Total time: 18 minutes

### Approach B: Plugin (5 minutes)

Sarah uses one command:
```
/fda-tools:research --product-code DQY --years 2024
```

**Results:**
- Plugin automatically found 8 devices, ranked by similarity
- Highlighted 3 best predicates with confidence scores
- Recall status shown inline (0 recalls for top 3)
- Testing standards extracted from each 510(k) summary
- Organized in comparison table
- Total time: 5 minutes

### Sarah's Ratings

| Dimension | Score | Comment |
|-----------|-------|---------|
| Accuracy | 9/10 | "All predicates were defensible, one minor error in IFU comparison" |
| Time Savings | 10/10 | "Saved 72% of my time" |
| Completeness | 8/10 | "Had everything except shelf life data" |
| Ease of Use | 10/10 | "One command - couldn't be simpler" |
| Data Quality | 9/10 | "Table was almost submission-ready" |
| Value vs. Raw AI | 10/10 | "Raw AI couldn't pull actual testing standards from summaries" |

**Total Score:** 56/60 (Excellent)

### Sarah's Feedback

**What worked well:**
> "The automatic ranking saved me so much time. Instead of reading 8 summaries myself, the plugin highlighted the best 3 and explained why. The recall check was instant - normally I'd have to search each K-number manually on the FDA website."

**What didn't work:**
> "I wished it pulled shelf life data from the summaries. That's always buried deep in the PDF and I still had to find it manually."

**What's missing:**
> "It would be amazing if it could flag when predicates are from the same manufacturer (potential conflicts of interest for substantial equivalence arguments)."

**Would you use this?**
> "Absolutely. This would save me 5-10 hours every single week. I'd use it for every predicate search going forward."

---

## Frequently Asked Questions

### "What if I don't understand the command?"
**Don't worry!** We'll show you exactly what to type, character by character. Just copy and paste.

### "What if something breaks?"
**That's valuable feedback!** Tell us what went wrong. That's what we need to know.

### "What if the results are wrong?"
**Perfect!** That's exactly what we're testing. Tell us what was wrong and what should have happened.

### "Can I take breaks during the evaluation?"
**Yes!** The whole session is ~60 minutes, but you can pause between sections.

### "Will my feedback be anonymous?"
**Your choice!** We can anonymize your report or include attribution - you decide.

### "What if I'm not sure about an answer?"
**Just tell us!** "I don't know" is a valid answer. Uncertainty is useful feedback.

### "Do I get anything for participating?"
**Yes!** You get:
- Early access to improvements based on your feedback
- Direct line to development team for feature requests
- Credit in our acknowledgments (if you want it)
- Our eternal gratitude 🙏

---

## How to Start

### Option 1: Guided Setup (Recommended for Non-Technical Users)

Send an email to: [evaluation@fda-tools.com]

We'll schedule a 60-minute Zoom call where we:
1. Screen share and walk you through setup
2. Guide you through the evaluation live
3. Answer questions in real-time
4. Capture your feedback as we go

**No preparation needed!** We handle all the technical stuff.

### Option 2: Self-Service (For Comfortable Users)

1. Open Claude Code
2. Type: `/fda-tools:expert-eval`
3. Press Enter
4. Follow the prompts

The agent will guide you step-by-step through the entire evaluation.

### Option 3: Hybrid (Best of Both)

Do the evaluation yourself, but join our Slack channel for real-time help if you get stuck:
[FDA Tools Evaluation Slack]

---

## Contact & Support

**Questions before starting?**
- Email: evaluation@fda-tools.com
- Slack: #expert-evaluations
- Phone: [Phone number]

**Technical issues during evaluation?**
- Slack: #expert-evaluations (fastest)
- Email: support@fda-tools.com

**Want to schedule a guided session?**
- Calendar: [Calendly link]
- Email: evaluation@fda-tools.com

---

## Thank You!

Your expertise is invaluable. Medical device regulatory work is complex, and we can only make this tool truly useful with feedback from professionals like you.

**Your 60 minutes of feedback could save thousands of hours for the entire medical device community.**

We're grateful for your time and honest assessment.

---

**Ready to start?**

Choose your approach:
- [ ] **Guided Zoom Session** - Email evaluation@fda-tools.com
- [ ] **Self-Service** - Type `/fda-tools:expert-eval` in Claude Code
- [ ] **Hybrid with Slack Support** - Join #expert-evaluations

---

*This evaluation is for FDA Tools plugin v5.22.0*
*Last updated: 2026-02-14*
