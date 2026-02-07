---
description: Regulatory calculators — shelf life (ASTM F1980 accelerated aging), sample size (statistical), and sterilization dose
allowed-tools: Bash, Read, Write
argument-hint: "shelf-life|sample-size [parameters]"
---

# FDA Regulatory Calculators

## Resolve Plugin Root

**Before running any bash commands that reference `$FDA_PLUGIN_ROOT`**, resolve the plugin install path:

```bash
FDA_PLUGIN_ROOT=$(python3 -c "
import json, os
f = os.path.expanduser('~/.claude/plugins/installed_plugins.json')
if os.path.exists(f):
    d = json.load(open(f))
    for k, v in d.get('plugins', {}).items():
        if k.startswith('fda-predicate-assistant@'):
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

### Calculation

```bash
python3 << 'PYEOF'
import math

# Parameters (replace with actual values)
T_ambient = 25      # Celsius
T_accelerated = 55  # Celsius
Q10 = 2.0
shelf_life_months = 24  # Replace with parsed value

# Calculate AAF
AAF = Q10 ** ((T_accelerated - T_ambient) / 10)

# Calculate accelerated aging duration
accel_months = shelf_life_months / AAF
accel_weeks = accel_months * 4.33
accel_days = accel_months * 30.44

print(f"INPUT_AMBIENT:{T_ambient}")
print(f"INPUT_ACCELERATED:{T_accelerated}")
print(f"INPUT_Q10:{Q10}")
print(f"INPUT_SHELF_LIFE:{shelf_life_months} months")
print(f"AAF:{AAF:.2f}")
print(f"ACCEL_MONTHS:{accel_months:.1f}")
print(f"ACCEL_WEEKS:{accel_weeks:.1f}")
print(f"ACCEL_DAYS:{accel_days:.0f}")
PYEOF
```

### Output Format

```
  ASTM F1980 Accelerated Aging Calculator
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Generated: {date} | v5.0.0

INPUT PARAMETERS
────────────────────────────────────────
  Ambient temperature:       {T_ambient} C
  Accelerated temperature:   {T_accelerated} C
  Q10 factor:                {Q10}
  Desired shelf life:        {shelf_life}

RESULTS
────────────────────────────────────────
  Accelerated Aging Factor (AAF):  {AAF}
  Required aging duration:         {months} months ({weeks} weeks / {days} days)
  Equivalent real-time:            {shelf_life_months} months

FORMULA
────────────────────────────────────────
  AAF = Q10^((T_accel - T_ambient) / 10)
  AAF = {Q10}^(({T_accelerated} - {T_ambient}) / 10)
  AAF = {AAF}

  t_accelerated = {shelf_life_months} months / {AAF} = {accel_months} months

NOTES
────────────────────────────────────────
  - Q10 = 2.0 is conservative per ASTM F1980
  - Real-time aging must also be conducted concurrently
  - Results from accelerated aging are preliminary until confirmed by real-time data
  - Consider using Q10 = 1.8 for worst-case sensitivity analysis

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
alpha = 0.05       # Significance level (one-sided)
power = 0.80       # Statistical power
dropout = 0.10     # Expected dropout rate

# Normal approximation for one-sample binomial
z_alpha = 1.645    # One-sided 0.05
z_beta = 0.842     # Power = 0.80

# Sample size using normal approximation (conservative)
n = math.ceil((z_alpha * math.sqrt(p0 * (1 - p0))) ** 2 / ((1 - p0) ** 2) * (1 / (1 - p0)))
# More accurate: exact binomial approach
# n = ceil((z_alpha + z_beta)^2 * p0 * (1-p0) / delta^2)
# For performance goal: we need n such that P(reject H0 | p=p0) >= power

# Simple conservative estimate
n_simple = math.ceil((z_alpha ** 2 * p0 * (1 - p0)) / (0.05 ** 2))
n_enrolled = math.ceil(n_simple / (1 - dropout))

print(f"DESIGN:one-sample binomial (performance goal)")
print(f"SUCCESS_RATE:{p0}")
print(f"ALPHA:{alpha}")
print(f"POWER:{power}")
print(f"N_EVALUABLE:{n_simple}")
print(f"DROPOUT:{dropout}")
print(f"N_ENROLLED:{n_enrolled}")
PYEOF
```

### Output Format

```
  Statistical Sample Size Calculator
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Generated: {date} | v5.0.0

DESIGN
────────────────────────────────────────
  Study design:        {design}
  Target success rate: {p0}
  Significance level:  {alpha}
  Power:               {power}

RESULTS
────────────────────────────────────────
  Minimum evaluable:   {N_evaluable}
  Expected dropout:    {dropout}%
  Required enrollment: {N_enrolled}

NOTES
────────────────────────────────────────
  - Sample size calculated using normal approximation
  - Verify with exact binomial calculation for final protocol
  - Consider regulatory requirements for specific device types
  - FDA may require larger samples for high-risk devices

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
