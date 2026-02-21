# Example 3 — Combination Product 510(k): Antimicrobial Wound Dressing

**Product code:** FRO (Wound Dressing, Absorbent)
**Device class:** U (combination product — device primary mode of action)
**Regulation:** N/A (Class U — unclassified combination product)
**Review panel:** SU (General and Plastic Surgery Devices)
**Pathway:** Traditional 510(k)

This example demonstrates a combination product submission where the device component
(wound dressing) provides the primary mode of action and the drug component (silver
sulfadiazine 1%) is OTC-monograph compliant.

---

## Project Structure

```
03-combination-product-wound-dressing/
├── device_profile.json      # Dressing specs, drug component info, materials
├── review.json              # Accepted predicates and SE conclusion
├── drafts/
│   └── 510k-summary.md     # Example 510(k) Summary with combination product sections
└── README.md                # This file
```

---

## Step-by-Step Workflow

### Step 1 — Create the project

```bash
/fda-tools:start --project healguard-ag --product-code FRO
```

### Step 2 — Fetch predicate devices

```bash
/fda-tools:b --product-codes FRO --years 5 --project healguard-ag
```

Expected output: CSV with ~20–40 FRO clearances.

### Step 3 — Research predicates

```bash
/fda-tools:r FRO --project healguard-ag \
  --device-description "Polyurethane foam wound dressing with 1% silver sulfadiazine drug component" \
  --intended-use "antimicrobial primary wound dressing for burns and chronic wounds"
```

### Step 4 — Run pre-submission readiness check

```bash
/fda-tools:pc --project healguard-ag --depth deep
```

Expected output: SRI ~50–60/100. Key gaps for a new combination product:
- Drug component documentation (OTC monograph citation)
- Shelf life and stability data for drug component
- Biocompatibility for drug-containing contact layer

### Step 5 — Draft combination product section

```bash
/fda-tools:d combination-product --project healguard-ag
```

Expected output: Drug-device combination section including:
- Mode-of-action determination (device-led vs. drug-led)
- Drug regulatory basis (OTC monograph vs. NDA/ANDA)
- Lead FDA center justification

### Step 6 — Draft 510(k) summary

```bash
/fda-tools:d 510k-summary --project healguard-ag
```

---

## Combination Product Requirements

### Mode of Action Determination

For wound dressings with antimicrobial drug components:

| Component | Mode of Action | Primary? |
|-----------|----------------|----------|
| Polyurethane foam | Physical wound coverage, fluid management | **Yes** |
| Silver sulfadiazine | Antimicrobial (reduces bioburden) | No |

**Conclusion:** Device-led combination product → CDRH is the lead center.

### Drug Component Documentation

For OTC-monograph compliant drugs (like 1% SSD per 21 CFR 333 Subpart D),
a full NDA/ANDA is NOT required. Instead, include:
- Citation of the applicable OTC monograph
- Confirmation drug concentration matches monograph requirements
- Stability testing data showing drug potency maintained through shelf life

### Class U Devices

Class U (unclassified) applies when:
- The device is a novel combination with no established classification
- The device is otherwise equivalent to a cleared predicate in the same unclassified category

Key implications:
- No regulation number in the submission form (leave blank)
- Pre-submission meeting (Q-submission) recommended for novel combination products
- Predicate selection based on device function, not classification

---

## Expected Review Time

Based on recent FRO clearances (2022–2025): **90–140 days** (median ~110 days).
Combination product review can take longer if drug documentation is incomplete.

---

## Common Pitfalls for Combination Products

1. **Drug monograph compliance** — Confirm the drug concentration exactly matches the
   monograph. For SSD, the monograph specifies 1.0% (not 0.5%, not 2%).
2. **Stability of drug in device** — The drug can degrade in the dressing during
   shelf life; include real-time or accelerated aging stability data showing drug
   potency is maintained.
3. **Separate labeling review** — Drug labeling (OTC directions) and device labeling
   must both comply; FDA reviews both. Ensure "Drug Facts" panel is correct.
4. **Biocompatibility of drug-loaded contact layer** — ISO 10993 cytotoxicity testing
   should be done on the drug-impregnated material, not the foam alone.
