# FDA Tools — Example Projects

Three fully worked example projects demonstrating common 510(k) submission scenarios.
All data is fictional and sanitized — no real company names, PII, or proprietary
information.

---

## Examples at a Glance

| Example | Product Code | Device Type | Highlights |
|---------|-------------|-------------|-----------|
| [01 — Basic 510(k) Catheter](01-basic-510k-catheter/) | DQY | Percutaneous catheter (hardware) | Textbook predicate match, EO sterilization, shelf life |
| [02 — SaMD Digital Pathology](02-samd-digital-pathology/) | QKQ | AI/ML software (SaMD) | IEC 62304, cybersecurity docs, clinical validation stats |
| [03 — Combination Product](03-combination-product-wound-dressing/) | FRO | Wound dressing + drug | Device-led combination, OTC monograph, Class U |

---

## Quick Start

### Try Example 1 (fastest — ~5 minutes)

```bash
# 1. Install fda-tools if not already installed
pip install -e ".[dev]"

# 2. Load the example device profile
cp examples/01-basic-510k-catheter/device_profile.json \
   ~/.fda-510k-data/projects/example-catheter/device_profile.json

# 3. Run a pre-submission readiness check
/fda-tools:pre-check --project example-catheter

# 4. Explore predicate matching
/fda-tools:batchfetch --product-codes DQY --years 2 --project example-catheter
```

Expected: Pre-check SRI score ~65–75/100. Batchfetch retrieves ~25–50 DQY records.

---

## File Structure of Each Example

```
examples/<name>/
├── device_profile.json    ← Start here: device specs, materials, intended use
├── review.json            ← Predicate selections and SE conclusion
├── drafts/
│   └── 510k-summary.md   ← Example draft output from /fda-tools:draft
└── README.md              ← Step-by-step workflow + tips for this device type
```

---

## How to Use These Examples

### Option A — Read-only reference

Browse the JSON and markdown files to understand the expected data structure before
starting a real project. The device profiles are good templates for the fields your
project needs.

### Option B — Load into a live project

```bash
# Copy the example to your project directory
PROJECT="my-project"
EXAMPLE="examples/01-basic-510k-catheter"

mkdir -p ~/.fda-510k-data/projects/$PROJECT
cp $EXAMPLE/device_profile.json ~/.fda-510k-data/projects/$PROJECT/
cp $EXAMPLE/review.json ~/.fda-510k-data/projects/$PROJECT/

# Then run the tool against it
/fda-tools:status --project $PROJECT
/fda-tools:pre-check --project $PROJECT
```

### Option C — Regenerate the example output

Use the examples as inputs to see what the tool produces end-to-end:

```bash
/fda-tools:pipeline DQY \
  --project my-catheter \
  --device-description "4 Fr single-use percutaneous delivery catheter" \
  --full-auto
```

---

## Adding Your Own Example

To contribute a new example:

1. Create a new directory `examples/NN-short-name/`
2. Provide `device_profile.json`, `review.json`, `drafts/`, and `README.md`
3. Ensure all data is fictional — no real company names, K-numbers from public FDA
   records are fine (they are public domain), but do not include proprietary
   submission text
4. Submit a PR with the example and a note in `examples/README.md`

See [CONTRIBUTING.md](../CONTRIBUTING.md) for the PR process.

---

## Data Notes

- All company names, trade names, and contact information are fictional
- K-numbers referenced in predicate lists are real FDA-cleared devices (public record)
- Device descriptions are illustrative and should not be copied verbatim into real
  submissions — consult your regulatory affairs team
- These examples do not constitute regulatory advice

> ⚠️ These examples are for **learning and tool validation only**. Do not use this
> data in actual FDA submissions without independent review by a qualified RA
> professional.
