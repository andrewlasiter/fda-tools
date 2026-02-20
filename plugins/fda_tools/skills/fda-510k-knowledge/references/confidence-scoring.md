# Predicate Confidence Scoring Algorithm

Single source of truth for scoring extracted predicates. Used by `/fda:review` and referenced by `/fda:research`.

## Scoring Components (100 points total)

### 1. Section Context (40 points)

Where in the PDF was this device number found?

| Context | Points | Description |
|---------|--------|-------------|
| SE section only | 40 | Found in Substantial Equivalence / Predicate Comparison section |
| SE + general text | 40 | Found in SE section AND general text (SE presence dominates) |
| Mixed sections | 25 | Found in a testing/clinical section header area but not formal SE section |
| General text only | 10 | Found only in body text (literature, background, adverse events) |
| Table/image OCR | 15 | Found via OCR from a table or image (lower confidence in extraction accuracy) |

**SE section detection** uses the regex from `references/section-patterns.md`:
```regex
(?i)(substantial\s+equivalence|se\s+comparison|predicate\s+(comparison|device|analysis|identification)|comparison\s+to\s+predicate|technological\s+characteristics|comparison\s+(table|chart|matrix)|similarities\s+and\s+differences|comparison\s+of\s+(the\s+)?(features|technological|device))
```

SE window: 2000 characters after the SE header match.

### 2. Citation Frequency (20 points)

How many different source documents cite this device?

| Citations | Points | Interpretation |
|-----------|--------|----------------|
| 5+ sources | 20 | Widely recognized predicate in this product code |
| 3-4 sources | 15 | Well-established predicate |
| 2 sources | 10 | Moderately cited |
| 1 source | 5 | Single citation — verify manually |

Only count unique source documents. If the same source PDF mentions a device 10 times, that is still 1 citation.

**Weighted citations**: Citations from SE sections count as 1 full citation. Citations from general text only count as 0.5 citations for scoring purposes.

### 3. Product Code Match (15 points)

Does this device share a product code with the source document(s)?

| Match | Points | Description |
|-------|--------|-------------|
| Same product code | 15 | Device has the same 3-letter FDA product code as the citing device |
| Adjacent product code | 8 | Different code but same advisory committee / review panel |
| Different product code | 0 | Different panel — may be a reference device, not a predicate |

**Lookup**: Query `foiaclass.txt` or openFDA `/device/classification` to determine product code and review panel for both the cited device and the source device.

### 4. Recency (15 points)

How recently was this device cleared/approved?

| Age | Points | Description |
|-----|--------|-------------|
| < 5 years | 15 | Recent — strong predicate choice |
| 5-10 years | 10 | Moderately recent — acceptable |
| 10-15 years | 5 | Older — may raise reviewer questions about technology evolution |
| > 15 years | 2 | Very old — consider finding a more recent alternative |
| Unknown date | 5 | Cannot determine age (default to moderate) |

**Calculate from**: Decision date in `pmn*.txt` flat files or openFDA `/device/510k` endpoint `decision_date` field. For DEN-prefixed numbers, try the `/device/510k` endpoint first (some DEN numbers are indexed there); if not found, use FDA's De Novo database at accessdata.fda.gov (there is no dedicated `/device/denovo` API endpoint).

### 5. Clean Regulatory History (10 points)

Does this device have recalls, high adverse event counts, or other regulatory concerns?

| History | Points | Description |
|---------|--------|-------------|
| Clean | 10 | No recalls, reasonable adverse event rate |
| Minor concerns | 5 | Class II recall (voluntary), or moderate adverse event count |
| Major concerns | 0 | Class I recall, or death events > 0, or HIGH_MAUDE flag |

**Data sources**:
- openFDA `/device/recall` — check for any recalls matching this K-number or device name + applicant
- openFDA `/device/event` — count adverse events for the product code (device-level if possible)

## Composite Score Interpretation

| Score Range | Label | Recommendation |
|-------------|-------|----------------|
| 80-100 | **Strong** | High-confidence predicate — safe to accept |
| 60-79 | **Moderate** | Reasonable predicate — review context before accepting |
| 40-59 | **Weak** | Marginal predicate — likely a reference device or needs manual verification |
| 20-39 | **Poor** | Probably not an actual predicate — likely incidental mention |
| 0-19 | **Reject** | Almost certainly not a predicate — auto-reject unless user overrides |

## Risk Flags

Risk flags are independent of the confidence score. A device can have a high confidence score (it IS a predicate) but also carry risk flags (it has regulatory concerns).

| Flag | Trigger | API Source | Severity |
|------|---------|------------|----------|
| `RECALLED` | Any recall found for this specific device (K-number match) | `/device/recall` search by `k_numbers` (plural) or `res_event_number` | HIGH |
| `RECALLED_CLASS_I` | Class I recall (most serious) | `/device/enforcement` where `classification:"Class I"` (note: recall API has no classification field) | CRITICAL |
| `PMA_ONLY` | Device number starts with P (PMA, not 510(k)) | Number format check | MEDIUM |
| `CLASS_III` | Device classification is Class III | `/device/classification` or `foiaclass.txt` | MEDIUM |
| `OLD` | Decision date > 10 years ago | Decision date from database | LOW |
| `HIGH_MAUDE` | > 100 adverse events for this product code | `/device/event` count by product code | MEDIUM |
| `DEATH_EVENTS` | Any death events reported for this product code | `/device/event` where `event_type:"Death"` | HIGH |
| `EXCLUDED` | Device is on the user's exclusion list | Local `exclusion_list.json` file | USER |
| `STATEMENT_ONLY` | Only a 510(k) Statement filed (no Summary — limited public data) | `statement_or_summary` field | LOW |
| `SUPPLEMENT` | Device number has a supplement suffix (e.g., K123456/S001) | Number format check | LOW |
| `DEN_DEVICE` | Device is a De Novo authorization (DEN-prefix) — first-generation, no predicate chain | DEN-prefix number format check or `/device/510k` lookup | INFO |
| `DEN_NO_PREDICATES` | De Novo device had no predicate by definition — chain starts here | De Novo classification | INFO |

### Flag Display Format

```
K241335 (Score: 85/100 — Strong)
  Flags: RECALLED (Class II, 2024-03), OLD (cleared 2014)
```

Flags with severity CRITICAL or HIGH should be displayed prominently with a warning icon.

## Exclusion List Format

Users can maintain a local exclusion list of device numbers they want to automatically flag or skip during review. Managed via `/fda:configure --add-exclusion K123456 "reason"`.

**File location**: Configurable via `exclusion_list` setting in `~/.claude/fda-tools.local.md`. Default: `~/fda-510k-data/exclusion_list.json`.

**JSON format**:

```json
{
  "version": 1,
  "devices": {
    "K123456": {
      "reason": "Recalled in 2024 — Class I recall for manufacturing defect",
      "added": "2026-01-15T10:30:00Z",
      "added_by": "manual"
    },
    "K234567": {
      "reason": "Company no longer in business — predicate chain dead end",
      "added": "2026-01-20T14:00:00Z",
      "added_by": "review"
    }
  }
}
```

**Fields**:
- `reason` (required): Human-readable explanation for the exclusion
- `added` (required): ISO 8601 timestamp when added
- `added_by`: `"manual"` (via configure command), `"review"` (during review session), `"auto"` (automated safety scan)

## Reclassification Logic

The extraction script (`predicate_extractor.py`) classifies devices based on product code match only. The review command applies **section-aware reclassification** as a post-processing layer:

| Original Classification | SE Section Found | General Text Only | Reclassification |
|------------------------|------------------|-------------------|------------------|
| Predicate | Yes | — | **Predicate** (confirmed, high confidence) |
| Predicate | No | Yes | **Uncertain** (may be reference device — review needed) |
| Reference | Yes | — | **Predicate** (reclassify up — likely misclassified) |
| Reference | No | Yes | **Reference** (confirmed) |
| (new device found) | Yes | — | **Predicate** (new finding from SE section) |
| (new device found) | No | Yes | **Reference** (new finding from general text) |

### DEN Number Handling

DEN-prefixed device numbers require special treatment:
- **Lookup**: Try openFDA `/device/510k` endpoint first (some DEN numbers are indexed there). DEN numbers do not appear in `pmn*.txt` flat files. There is no dedicated `/device/denovo` API endpoint; for devices not found via `/device/510k`, use FDA's De Novo database at accessdata.fda.gov.
- **Reclassification**: DEN devices are valid predicates for subsequent 510(k) submissions. If a DEN number is found in an SE section, classify it as a predicate.
- **No chain penalty**: De Novo devices are by definition chain starters — they had no predicate. Do not penalize chain depth = 0 for DEN devices (see Extended Scoring below).

This reclassification uses the same SE_HEADER + SE_WINDOW=2000 + SE_WEIGHT=3x logic proven in `research.md`.

## Extended Scoring Components (v2.1)

The base 5-component scoring (100 pts) can be extended with additional defensibility metrics. These bonus points (up to +20) provide differentiation among similarly-scored predicates.

### Predicate Chain Depth Score (+5 pts max)

Predicates with longer citation chains are more defensible — they represent established regulatory acceptance.

| Chain Depth | Bonus Points | Rationale |
|-------------|-------------|-----------|
| 3+ generations (cited by devices that are also cited as predicates) | +5 | Deep regulatory lineage |
| 2 generations (cited by at least 1 device as predicate) | +3 | Moderate lineage |
| 1 generation (cited but not as predicate by others) | +1 | Minimal lineage |
| 0 (not cited by any other device) | +0 | No chain evidence |
| DEN device (chain starter by definition — De Novo had no predicate) | +3 | Chain origin — no penalty for depth=0 |

### SE Table Presence Score (+5 pts max)

Predicates whose summary documents contain a visible SE/comparison table are easier to compare against and provide stronger precedent.

| Condition | Bonus Points |
|-----------|-------------|
| Predicate has a detailed SE comparison table in its summary | +5 |
| Predicate has minimal comparison section | +2 |
| No comparison section found | +0 |

### Applicant Similarity Score (+5 pts max)

Predicates from the same company as the user's device are stronger (demonstrates product line evolution).

| Condition | Bonus Points |
|-----------|-------------|
| Same applicant as user's company | +5 |
| Same parent company (subsidiary match) | +3 |
| Different company | +0 |

### IFU Overlap Score (+5 pts max)

Text similarity between the subject device's intended use and the predicate's cleared IFU.

| Overlap Level | Bonus Points |
|--------------|-------------|
| High overlap (>80% keyword match) | +5 |
| Moderate overlap (50-80% keyword match) | +3 |
| Low overlap (20-50% keyword match) | +1 |
| Minimal overlap (<20%) | +0 |

### Updated Total Score Range

With extended components: **0 to 120 points** (100 base + 20 bonus)

Thresholds should be applied to the base 100-point score. Bonus points are used for tiebreaking and ranking differentiation.

## Score Disambiguation

This plugin uses two distinct scoring systems. They measure different things and should never be confused:

| Attribute | Predicate Confidence Score (PCS) | Submission Readiness Index (SRI) |
|-----------|--------------------------------|--------------------------------|
| **What it measures** | How likely an extracted device is a true predicate | How complete a 510(k) submission package is |
| **Scale** | 0-100 base + 20 bonus | 0-100 |
| **Used by** | `/fda:review`, `/fda:propose`, `/fda:research` | `/fda:pre-check`, `review-simulator` agent |
| **Inputs** | PDF section context, citation frequency, product code match, recency, regulatory history | RTA checklist, predicate quality, SE comparison, testing coverage, deficiency count, documentation |
| **Labels** | Strong / Moderate / Weak / Poor / Reject | Ready / Nearly Ready / Significant Gaps / Not Ready / Early Stage |
| **Display prefix** | "Score:" or "PCS:" | "SRI:" |

When displaying either score, always include the label to prevent ambiguity.
