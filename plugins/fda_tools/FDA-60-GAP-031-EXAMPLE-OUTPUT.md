# FDA-60 GAP-031: Example Output Comparison

## Before Fix: Silent Fallback

### CLI Output (Without sklearn, before fix)
```bash
$ python3 approval_probability.py --pma P170019
======================================================================
SUPPLEMENT APPROVAL PROBABILITY ANALYSIS
======================================================================
PMA Number:  P170019
Device:      Cardiac Pacemaker System
Applicant:   Example Medical Inc.
Total Supps: 5

--- Aggregate Analysis ---
  Avg Approval Probability: 87.5%
  Range: 75.0% - 95.0%
  Classification Accuracy: 80.0%

--- Supplement Scores ---
  S001   | labeling             | Prob:  94.0% [APPROVED] CORRECT
  S002   | design_change        | Prob:  85.0% [APPROVED] CORRECT
  S003   | manufacturing        | Prob:  93.0% [APPROVED] CORRECT
  S004   | panel_track          | Prob:  78.0% [DENIED] WRONG
  S005   | indication_expansion | Prob:  82.0% [APPROVED] CORRECT

======================================================================
Model: rule_based_baseline v1.0.0
Generated: 2026-02-17
This analysis is AI-generated from public FDA data.
Independent verification by qualified RA professionals required.
======================================================================
```

**PROBLEM:**
- ❌ No indication that sklearn is missing
- ❌ User doesn't know if ML or rule-based method was used
- ❌ No guidance on how to improve accuracy
- ❌ Silent degradation - appears normal but using suboptimal method

### JSON Output (Without sklearn, before fix)
```json
{
  "pma_number": "P170019",
  "device_name": "Cardiac Pacemaker System",
  "applicant": "Example Medical Inc.",
  "total_supplements": 5,
  "scored_supplements": [...],
  "aggregate_analysis": {
    "total_scored": 5,
    "avg_approval_probability": 87.5,
    "classification_accuracy": 80.0
  },
  "model_version": "1.0.0",
  "model_type": "rule_based_baseline",
  "generated_at": "2026-02-17T10:00:00Z"
}
```

**PROBLEM:**
- ❌ No `method_used` field
- ❌ Users parsing JSON can't tell if ML is active
- ❌ No programmatic way to detect degraded mode

---

## After Fix: Transparent Fallback

### CLI Output (Without sklearn, after fix)
```bash
$ python3 approval_probability.py --pma P170019

╔════════════════════════════════════════════════════════════════════╗
║ DEGRADED MODE: scikit-learn not available                         ║
║                                                                    ║
║ Using rule-based fallback scoring instead of ML predictions.      ║
║                                                                    ║
║ Install sklearn for ML-based predictions:                         ║
║   pip install scikit-learn>=1.3.0                                 ║
║                                                                    ║
║ Accuracy implications:                                            ║
║  • Rule-based: Uses empirical baseline rates (±5-10% accuracy)    ║
║  • ML-based: Learns from historical patterns (±3-5% accuracy)     ║
║                                                                    ║
║ Output includes 'method_used' field for transparency.             ║
╚════════════════════════════════════════════════════════════════════╝

======================================================================
SUPPLEMENT APPROVAL PROBABILITY ANALYSIS
======================================================================
PMA Number:  P170019
Device:      Cardiac Pacemaker System
Applicant:   Example Medical Inc.
Total Supps: 5

--- Aggregate Analysis ---
  Avg Approval Probability: 87.5%
  Range: 75.0% - 95.0%
  Classification Accuracy: 80.0%

--- Supplement Scores ---
  S001   | labeling             | Prob:  94.0% [APPROVED] CORRECT
  S002   | design_change        | Prob:  85.0% [APPROVED] CORRECT
  S003   | manufacturing        | Prob:  93.0% [APPROVED] CORRECT
  S004   | panel_track          | Prob:  78.0% [DENIED] WRONG
  S005   | indication_expansion | Prob:  82.0% [APPROVED] CORRECT

======================================================================
Model: rule_based_baseline v1.0.0
Method: Rule-based (rule_based)  ← NEW: Shows active method
Generated: 2026-02-17

This analysis is AI-generated from public FDA data.
Independent verification by qualified RA professionals required.
======================================================================
```

**IMPROVEMENTS:**
- ✅ Clear warning about degraded mode
- ✅ Installation instructions provided
- ✅ Accuracy implications explained
- ✅ Method indicator shows "Rule-based (rule_based)"
- ✅ User knows exactly what's happening

### JSON Output (Without sklearn, after fix)
```json
{
  "pma_number": "P170019",
  "device_name": "Cardiac Pacemaker System",
  "applicant": "Example Medical Inc.",
  "total_supplements": 5,
  "scored_supplements": [...],
  "aggregate_analysis": {
    "total_scored": 5,
    "avg_approval_probability": 87.5,
    "classification_accuracy": 80.0
  },
  "model_version": "1.0.0",
  "model_type": "rule_based_baseline",
  "method_used": "rule_based",  ← NEW: Explicit method indicator
  "generated_at": "2026-02-17T10:00:00Z"
}
```

**IMPROVEMENTS:**
- ✅ `method_used` field added
- ✅ Programmatically detectable
- ✅ API consumers know which method was used
- ✅ Can trigger alerts or fallback logic in client code

---

## With sklearn Installed (Optimal Mode)

### CLI Output (With sklearn, after fix)
```bash
$ python3 approval_probability.py --pma P170019
# No warning issued (sklearn available)

======================================================================
SUPPLEMENT APPROVAL PROBABILITY ANALYSIS
======================================================================
PMA Number:  P170019
Device:      Cardiac Pacemaker System
Applicant:   Example Medical Inc.
Total Supps: 5

--- Aggregate Analysis ---
  Avg Approval Probability: 89.2%
  Range: 78.0% - 96.0%
  Classification Accuracy: 95.0%  ← Better accuracy with ML

--- Supplement Scores ---
  S001   | labeling             | Prob:  95.5% [APPROVED] CORRECT
  S002   | design_change        | Prob:  87.2% [APPROVED] CORRECT
  S003   | manufacturing        | Prob:  94.8% [APPROVED] CORRECT
  S004   | panel_track          | Prob:  78.3% [DENIED] CORRECT  ← ML got this right
  S005   | indication_expansion | Prob:  83.7% [APPROVED] CORRECT

======================================================================
Model: sklearn_random_forest v1.0.0
Method: ML-based (ml)  ← Shows ML is active
Generated: 2026-02-17

This analysis is AI-generated from public FDA data.
Independent verification by qualified RA professionals required.
======================================================================
```

**BENEFITS WITH ML:**
- ✅ No warning (sklearn available)
- ✅ Better accuracy (95% vs 80%)
- ✅ Method shows "ML-based (ml)"
- ✅ More accurate probability predictions

### JSON Output (With sklearn, after fix)
```json
{
  "pma_number": "P170019",
  "device_name": "Cardiac Pacemaker System",
  "applicant": "Example Medical Inc.",
  "total_supplements": 5,
  "scored_supplements": [...],
  "aggregate_analysis": {
    "total_scored": 5,
    "avg_approval_probability": 89.2,
    "classification_accuracy": 95.0
  },
  "model_version": "1.0.0",
  "model_type": "sklearn_random_forest",
  "method_used": "ml",  ← Shows ML is active
  "generated_at": "2026-02-17T10:00:00Z"
}
```

---

## Hypothetical Supplement Scoring

### Without sklearn (after fix)
```json
{
  "approval_probability": 60.0,
  "approval_probability_raw": 0.6,
  "base_rate": 85.0,
  "risk_flags": [
    {
      "label": "No Clinical Data",
      "penalty": 0.1,
      "description": "Supplement lacks clinical data support",
      "mitigation": "Provide clinical evidence or literature support for the change."
    },
    {
      "label": "Prior Denial History",
      "penalty": 0.15,
      "description": "Applicant has prior denied supplements for this PMA",
      "mitigation": "Address all prior deficiency reasons in the new submission."
    }
  ],
  "positive_factors": [],
  "total_penalty": 25.0,
  "total_bonus": 0.0,
  "recommended_mitigations": [
    "Provide clinical evidence or literature support for the change.",
    "Address all prior deficiency reasons in the new submission."
  ],
  "confidence": "moderate",
  "model_version": "1.0.0",
  "model_type": "rule_based_baseline",
  "method_used": "rule_based"  ← Clear indicator
}
```

---

## Key Differences Summary

| Aspect | Before Fix | After Fix |
|--------|-----------|-----------|
| **Warning** | ❌ Silent | ✅ Clear boxed warning |
| **Installation Help** | ❌ None | ✅ Exact pip command provided |
| **Accuracy Info** | ❌ Unknown | ✅ ±5-10% vs ±3-5% documented |
| **Method Field** | ❌ Missing | ✅ `method_used: ml\|rule_based` |
| **CLI Indicator** | ❌ Hidden | ✅ "Method: Rule-based (rule_based)" |
| **JSON Field** | ❌ No indicator | ✅ Programmatically detectable |
| **User Experience** | ❌ Confusing | ✅ Transparent and helpful |
| **Debugging** | ❌ Difficult | ✅ Easy to verify mode |

---

## User Scenarios

### Scenario 1: Developer integrating via API
**Before:** "Why are my probabilities different from the docs?"
**After:** Check `method_used` field → sees "rule_based" → installs sklearn

### Scenario 2: RA professional running analysis
**Before:** Unaware of degraded accuracy
**After:** Sees warning → understands limitations → installs sklearn for critical decisions

### Scenario 3: CI/CD pipeline
**Before:** Tests pass but using suboptimal method silently
**After:** Can check `method_used` field → fail build if ML not available

### Scenario 4: Production monitoring
**Before:** No way to detect degraded mode
**After:** Monitor `method_used` field → alert if not "ml"

---

## Installation to Fix Degraded Mode

```bash
# Simple installation
pip install scikit-learn>=1.3.0

# Or install all FDA tools dependencies with ML enabled
cd plugins/fda-tools/scripts
# Uncomment sklearn line in requirements.txt
pip install -r requirements.txt
```

After installation, restart the script:
```bash
$ python3 approval_probability.py --pma P170019
# No warning - sklearn detected
# Method: ML-based (ml)
```
