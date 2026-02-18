---
description: Regulatory calculators — shelf life (ASTM F1980 accelerated aging), sample size (statistical), and sterilization dose
allowed-tools: Bash, Read, Write
argument-hint: "shelf-life|sample-size [parameters]"
---

# FDA Regulatory Calculators

> **Important**: This command assists with FDA regulatory workflows but does not provide regulatory advice. Output should be reviewed by qualified regulatory professionals before being relied upon for submission decisions.

> For external API dependencies and connection status, see [CONNECTORS.md](../CONNECTORS.md).

## Resolve Plugin Root

**Before running any bash commands that reference `$FDA_PLUGIN_ROOT`**, resolve the plugin install path:

```bash
FDA_PLUGIN_ROOT=$(python3 -c "
import json, os
f = os.path.expanduser('~/.claude/plugins/installed_plugins.json')
if os.path.exists(f):
    d = json.load(open(f))
    for k, v in d.get('plugins', {}).items():
        if k.startswith('fda-tools@'):
            for e in v:
                p = e.get('installPath', '')
                if os.path.isdir(p):
                    print(p); exit()
print('')
")
echo "FDA_PLUGIN_ROOT=$FDA_PLUGIN_ROOT"
```

---

You are providing regulatory calculation utilities for 510(k) submissions.

## Parse Arguments

From `$ARGUMENTS`, extract the subcommand and parameters:

### Subcommand: `shelf-life`

Calculate accelerated aging duration per ASTM F1980 "Standard Guide for Accelerated Aging of Sterile Barrier Systems and Medical Device Packages."

**Parameters:**
- `--ambient TEMP` — Ambient storage temperature in Celsius (default: 25)
- `--accelerated TEMP` — Accelerated aging temperature in Celsius (default: 55)
- `--q10 FACTOR` — Q10 temperature coefficient (default: 2.0)
- `--shelf-life DURATION` — Desired real-time shelf life (e.g., "2years", "3years", "18months")
- `--packaging-type TYPE` — Packaging type for adjusted Q10 calculation (optional: standard|moisture-barrier|breathable|rigid)
- `--project NAME` — Save calculation to project folder
- `--save` — Save results

### Subcommand: `sample-size`

Calculate minimum sample size for common test designs.

**Parameters:**
- `--success-rate RATE` — Expected/target success rate as decimal (e.g., 0.95)
- `--margin DELTA` — Acceptable margin/difference (e.g., 0.10)
- `--alpha LEVEL` — Significance level (default: 0.05)
- `--power LEVEL` — Statistical power (default: 0.80)
- `--design one-sample|two-sample|non-inferiority` — Study design (default: one-sample)
- `--dropout RATE` — Expected dropout rate as decimal (default: 0.10)

## Shelf Life Calculator

### ASTM F1980 Accelerated Aging Formula

The Accelerated Aging Factor (AAF) is calculated as:

```
AAF = Q10 ^ ((T_accelerated - T_ambient) / 10)
```

Accelerated aging duration:

```
t_accelerated = t_real / AAF
```

Where:
- `Q10` = temperature coefficient (default 2.0, conservative; 1.8-2.5 range per ASTM F1980)
- `T_accelerated` = accelerated aging temperature (Celsius)
- `T_ambient` = ambient storage temperature (Celsius)
- `t_real` = desired real-time shelf life
- `t_accelerated` = required accelerated aging duration

### Packaging Type Configuration (Optional)

The Q10 value should be selected based on the dominant degradation mechanism for your device/packaging system. The following are common starting points for Q10 selection based on packaging configuration:

**Packaging Configurations:**
- **standard** → Q10 = 2.0 (industry default, conservative)
- **moisture-barrier** (foil pouch, Tyvek) → Q10 = 2.0-2.5 (if moisture sensitivity is the rate-limiting degradation pathway)
- **breathable** (paper/plastic, unwrapped) → Q10 = 1.8-2.0 (accounts for environmental exposure uncertainty)
- **rigid** (tray, box) → Q10 = 2.0-2.2 (structural protection, limited moisture barrier)

**IMPORTANT:** These Q10 values must be justified by the submitter based on material-specific data or published literature per ASTM F1980 Section 7.2.1. Higher Q10 values (>2.0) result in shorter accelerated test durations and require stronger justification. When in doubt, use Q10=2.0.

### Calculation

```bash
python3 << 'PYEOF'
import math

# Parameters (replace with actual values from argument parsing)
T_ambient = 25      # Celsius
T_accelerated = 55  # Celsius
packaging_type = "standard"  # Replace with parsed value: standard|moisture-barrier|breathable|rigid
shelf_life_months = 24  # Replace with parsed value

# Packaging-specific Q10 values (guidance only - must be justified)
packaging_configs = {
    "standard": {"q10": 2.0, "description": "Standard packaging (baseline)"},
    "moisture-barrier": {"q10": 2.5, "description": "Moisture barrier (foil pouch, Tyvek)"},
    "breathable": {"q10": 1.8, "description": "Breathable packaging (paper/plastic)"},
    "rigid": {"q10": 2.2, "description": "Rigid container (tray, box)"}
}

# Get packaging configuration
if packaging_type not in packaging_configs:
    packaging_type = "standard"  # Default fallback

config = packaging_configs[packaging_type]
Q10 = config["q10"]
packaging_desc = config["description"]

# Calculate AAF
AAF = Q10 ** ((T_accelerated - T_ambient) / 10)

# Calculate accelerated aging duration
accel_months = shelf_life_months / AAF
accel_weeks = accel_months * 4.33
accel_days = accel_months * 30.44

print(f"INPUT_AMBIENT:{T_ambient}")
print(f"INPUT_ACCELERATED:{T_accelerated}")
print(f"INPUT_PACKAGING_TYPE:{packaging_type}")
print(f"INPUT_Q10:{Q10}")
print(f"INPUT_SHELF_LIFE:{shelf_life_months} months")
print(f"AAF:{AAF:.3f}")
print(f"ACCEL_MONTHS:{accel_months:.2f}")
print(f"ACCEL_WEEKS:{accel_weeks:.1f}")
print(f"ACCEL_DAYS:{accel_days:.0f}")
print(f"PACKAGING_DESC:{packaging_desc}")
PYEOF
```

### Output Format

```
  ASTM F1980 Accelerated Aging Calculator
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Generated: {date} | v5.22.0

INPUT PARAMETERS
────────────────────────────────────────
  Ambient temperature:       {T_ambient} C
  Accelerated temperature:   {T_accelerated} C
  Packaging type:            {packaging_type} ({packaging_desc})
  Q10 factor:                {Q10}
  Desired shelf life:        {shelf_life}

RESULTS
────────────────────────────────────────
  AAF:                                 {AAF}
  Required aging duration:             {months} months ({weeks} weeks / {days} days)
  Equivalent real-time:                {shelf_life_months} months

FORMULA
────────────────────────────────────────
  AAF = Q10^((T_accel - T_ambient) / 10)
      = {Q10}^(({T_accelerated} - {T_ambient}) / 10)
      = {AAF}

  t_accelerated = {shelf_life_months} months / {AAF} = {accel_months} months

PACKAGING TYPE GUIDANCE (Q10 Selection)
────────────────────────────────────────
  Standard (Q10=2.0):          Industry default, conservative baseline
  Moisture Barrier (Q10=2.0-2.5):  If moisture is rate-limiting degradation pathway
  Breathable (Q10=1.8-2.0):    Accounts for environmental exposure uncertainty
  Rigid (Q10=2.0-2.2):         Structural protection, limited moisture barrier

  IMPORTANT: Q10 values >2.0 must be justified with material-specific data or
  published literature per ASTM F1980 Section 7.2.1. When in doubt, use Q10=2.0.

NOTES
────────────────────────────────────────
  - Q10 = 2.0 is conservative baseline per ASTM F1980
  - Higher Q10 results in shorter accelerated test duration
  - Real-time aging must be conducted concurrently with accelerated aging
  - Results from accelerated aging are preliminary until confirmed by real-time data
  - For sensitivity analysis, consider testing at Q10 ± 0.2 range

REFERENCE
────────────────────────────────────────
  ASTM F1980 — Standard Guide for Accelerated Aging of
  Sterile Barrier Systems and Medical Device Packages

────────────────────────────────────────
  This calculation is AI-generated.
  Verify independently. Not regulatory advice.
────────────────────────────────────────
```

## Sample Size Calculator

### One-Sample Binomial (Performance Goal)

For demonstrating a minimum success rate:

```bash
python3 << 'PYEOF'
import math

# Parameters (replace with actual)
p0 = 0.90          # Target success rate
delta = 0.05       # Margin (acceptance criterion below p0)
alpha = 0.05       # Significance level (one-sided)
power = 0.80       # Statistical power
dropout = 0.10     # Expected dropout rate

# Z-scores
z_alpha = 1.645    # One-sided 0.05
z_beta = 0.842     # Power = 0.80

# --- Method selection based on parameters ---
use_exact = (p0 >= 0.95 or p0 <= 0.05 or delta < 0.05)

if use_exact:
    # Exact binomial method (Clopper-Pearson) for edge cases:
    # - Proportions near 0 or 1 (p0 >= 0.95 or p0 <= 0.05)
    # - Very small margins (delta < 0.05)
    # - Normal approximation is unreliable in these regions
    #
    # Find smallest n such that:
    #   P(X >= k | p = p0) >= power, where k is the critical value
    #   satisfying P(X >= k | p = p0 - delta) <= alpha
    from math import comb, ceil

    def binom_cdf(k, n, p):
        """Exact binomial CDF: P(X <= k)."""
        return sum(comb(n, i) * p**i * (1-p)**(n-i) for i in range(k+1))

    p_null = p0 - delta  # Null hypothesis proportion
    n_exact = 2
    found = False
    for n_try in range(2, 5000):
        # Find critical value k: smallest k such that P(X >= k | p_null) <= alpha
        for k in range(n_try, -1, -1):
            reject_prob_null = 1 - binom_cdf(k - 1, n_try, p_null) if k > 0 else 1.0
            if reject_prob_null <= alpha:
                # Check power: P(X >= k | p = p0) >= power
                power_achieved = 1 - binom_cdf(k - 1, n_try, p0) if k > 0 else 1.0
                if power_achieved >= power:
                    n_exact = n_try
                    found = True
                    break
                else:
                    break  # Increasing k won't help
        if found:
            break

    n_evaluable = n_exact
    method = "exact binomial (Clopper-Pearson)"
else:
    # Normal approximation — valid when n*p and n*(1-p) both > 5
    n_normal = math.ceil(((z_alpha * math.sqrt(p0 * (1 - p0)) + z_beta * math.sqrt(p0 * (1 - p0))) / delta) ** 2)
    # Simpler conservative estimate
    n_simple = math.ceil((z_alpha ** 2 * p0 * (1 - p0)) / (delta ** 2))
    n_evaluable = max(n_normal, n_simple)
    method = "normal approximation"

n_enrolled = math.ceil(n_evaluable / (1 - dropout))

# Validation check
np_check = n_evaluable * p0
nq_check = n_evaluable * (1 - p0)
approx_valid = np_check > 5 and nq_check > 5

print(f"DESIGN:one-sample binomial (performance goal)")
print(f"METHOD:{method}")
print(f"SUCCESS_RATE:{p0}")
print(f"MARGIN:{delta}")
print(f"ALPHA:{alpha}")
print(f"POWER:{power}")
print(f"N_EVALUABLE:{n_evaluable}")
print(f"DROPOUT:{dropout}")
print(f"N_ENROLLED:{n_enrolled}")
print(f"NORMAL_APPROX_VALID:{'yes' if approx_valid else 'no (n*p={:.0f}, n*q={:.0f})'.format(np_check, nq_check)}")
if use_exact:
    print(f"NOTE:Exact method used because {'p near 0/1' if (p0 >= 0.95 or p0 <= 0.05) else 'small margin'}")
PYEOF
```

**Method selection logic:**
- **Normal approximation**: Used when n*p > 5, n*(1-p) > 5, and margin >= 0.05 — fast, standard
- **Exact binomial**: Used when proportions are near 0 or 1 (>=0.95 or <=0.05), or margin < 0.05 — accurate for edge cases where normal approximation breaks down

> **IMPORTANT**: For pivotal clinical studies, consult a qualified biostatistician. These calculators provide preliminary estimates suitable for planning and feasibility. Final sample size determination for pivotal studies should account for the specific study design, endpoint definitions, interim analyses, and regulatory requirements for your device type.

### Output Format

```
  Statistical Sample Size Calculator
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Generated: {date} | v5.22.0

DESIGN
────────────────────────────────────────
  Study design:        {design}
  Calculation method:  {normal approximation | exact binomial}
  Target success rate: {p0}
  Margin (delta):      {delta}
  Significance level:  {alpha}
  Power:               {power}

RESULTS
────────────────────────────────────────
  Minimum evaluable:   {N_evaluable}
  Expected dropout:    {dropout}%
  Required enrollment: {N_enrolled}
  Normal approx valid: {yes/no}

LIMITATIONS
────────────────────────────────────────
  - Normal approximation requires n*p > 5 and n*(1-p) > 5
  - Exact binomial is used automatically when proportions near 0/1
  - For pivotal studies: consult a qualified biostatistician
  - Consider regulatory requirements for specific device types
  - FDA may require larger samples for high-risk or novel devices
  - These estimates do not account for interim analyses or adaptive designs

────────────────────────────────────────
  This calculation is AI-generated.
  Verify independently. Not regulatory advice.
────────────────────────────────────────
```

## Save Results (--save / --project)

If `--save` or `--project` specified, write calculation to `$PROJECTS_DIR/$PROJECT_NAME/calculations/`:

- `shelf_life_calc.json` — Shelf life calculation with all parameters and results
- `sample_size_calc.json` — Sample size calculation with all parameters and results

## Error Handling

- **No subcommand**: Show usage with available calculators
- **Invalid parameters**: "Temperature must be numeric. Example: `/fda:calc shelf-life --ambient 25 --accelerated 55`"
- **Q10 out of range**: "Q10 should be between 1.5 and 3.0. ASTM F1980 recommends 2.0 as conservative default."
- **Accelerated <= ambient**: "Accelerated temperature must be higher than ambient temperature."
