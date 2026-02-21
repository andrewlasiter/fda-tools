# Example 1 — Basic 510(k): Percutaneous Cardiovascular Catheter

**Product code:** DQY (Catheter, Percutaneous)
**Device class:** II
**Regulation:** 21 CFR 870.1250
**Review panel:** CV (Cardiovascular Devices)
**Pathway:** Traditional 510(k)

This example demonstrates the most common FDA 510(k) submission scenario: a
Class II hardware device with straightforward predicate matching.

---

## Project Structure

```
01-basic-510k-catheter/
├── device_profile.json      # Device specs, intended use, materials, dimensions
├── review.json              # Accepted predicates and SE conclusion
├── drafts/
│   └── 510k-summary.md     # Example 510(k) Summary section (Section 4)
└── README.md                # This file
```

---

## Step-by-Step Workflow

### Step 1 — Create the project

```bash
# No project directory exists yet — the tool will create it
/fda-tools:start --project my-catheter --product-code DQY
```

Expected output: Project directory created at `~/.fda-510k-data/projects/my-catheter/`

### Step 2 — Fetch predicate devices

```bash
/fda-tools:b --product-codes DQY --years 3 --project my-catheter
# or with the alias:
/fda-tools:batchfetch --product-codes DQY --years 3 --project my-catheter
```

Expected output: CSV with ~40–80 DQY clearances from the past 3 years.
Runtime: ~15–30 seconds.

### Step 3 — Research and select predicates

```bash
/fda-tools:r DQY --project my-catheter \
  --device-description "4 Fr single-use percutaneous delivery catheter, 45 cm, 0.014-in GW compatible" \
  --intended-use "percutaneous cardiovascular delivery"
```

Expected output: Ranked list of predicate candidates with similarity scores.
Recommended predicate: K241335 (Amplatzer Piccolo Delivery System, 2024).

### Step 4 — Run pre-submission readiness check

```bash
/fda-tools:pc --project my-catheter --depth standard
```

Expected output: SRI score ~65–75/100. Key gaps for a new project:
- Performance testing data not yet populated
- Shelf life testing evidence needed
- Biocompatibility table needs completion

### Step 5 — Draft the 510(k) summary

```bash
/fda-tools:d 510k-summary --project my-catheter
```

Expected output: Filled `drafts/510k-summary.md` (similar to `drafts/510k-summary.md`
in this example directory).

### Step 6 — Run consistency check

```bash
/fda-tools:consistency --project my-catheter
```

Expected output: Report identifying any mismatches between device description,
labeling, and predicate comparison table. Target: 0 critical issues.

---

## Key Files Reference

### `device_profile.json`

| Field | Description |
|-------|-------------|
| `product_code` | FDA product code (DQY) |
| `intended_use` | IFU statement |
| `materials` | List of materials for ISO 10993 evaluation |
| `sterilization_method` | "EO", "gamma", "steam", "radiation", or "N/A" |
| `peer_devices` | Pre-populated list of known cleared predicates |

### `review.json`

| Field | Description |
|-------|-------------|
| `accepted_predicates` | List of selected predicate devices |
| `se_conclusion` | Substantial equivalence argument summary |
| `sri_score` | Submission Readiness Index (0–100) |

---

## Expected Review Time

Based on recent DQY clearances (2023–2025): **77–120 days** from submission to
decision (median ~90 days for traditional pathway).

---

## Common Pitfalls for Catheter Devices

1. **EO residuals** — include ISO 10993-7 residuals data even if EO sterilization
   is standard; reviewers look for this explicitly.
2. **Shelf life** — accelerated aging per ASTM F1980 is expected; 36-month minimum
   recommended for consumable catheters.
3. **Guidewire compatibility** — if 0.014-inch GW compatible, include worst-case
   GW tip load and rotational torque data.
4. **Radiopacity** — if the device has radiopaque markers, include fluoroscopy
   visibility data (ASTM F640 or equivalent protocol).
