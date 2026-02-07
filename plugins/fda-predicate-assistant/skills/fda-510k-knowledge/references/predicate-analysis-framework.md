# Predicate Analysis Framework

Comprehensive methodology for deep predicate analysis in Pre-Submission packages and submission planning. This reference provides the structured approach for Section 4.2 of `/fda:presub` and supports `/fda:propose` and `/fda:compare-se`.

## 1. IFU Comparison Methodology

### Extraction

Extract Indications for Use (IFU) text from predicate devices using these priority sources:

1. **Form FDA 3881** — The official IFU statement form (most authoritative)
2. **IFU section header** — Look for "Indications for Use", "Intended Use", "Indications"
3. **510(k) Summary IFU paragraph** — Typically in the first 2 pages of a 510(k) summary
4. **openFDA device_name field** — Last resort; very abbreviated

See `section-patterns.md` for regex patterns to locate IFU text in extracted PDF content.

### Comparison Method

**Side-by-Side Comparison Table:**

```markdown
| Aspect | Subject Device | Predicate ({K-number}) | Assessment |
|--------|---------------|----------------------|------------|
| Target population | {subject population} | {predicate population} | Same/Different |
| Clinical indication | {subject indication} | {predicate indication} | Same/Different |
| Anatomical site | {subject site} | {predicate site} | Same/Different |
| Duration of use | {subject duration} | {predicate duration} | Same/Different |
| Use environment | {subject environment} | {predicate environment} | Same/Different |
```

**Keyword Overlap Analysis:**
- Extract medical/regulatory keywords from both IFU texts
- Compute Jaccard similarity coefficient
- Classify: >60% = Strong overlap, 35-60% = Moderate, <35% = Low
- Flag keywords present in subject but not predicate (expansion risk)
- Flag keywords present in predicate but not subject (narrowing — generally acceptable)

### IFU Difference Categories

| Category | Risk Level | FDA Response |
|----------|-----------|-------------|
| Identical IFU | None | Strongest SE basis |
| Same indication, different wording | Low | Generally acceptable |
| Same indication, broader population | Moderate | May need clinical justification |
| Same indication, narrower population | Low | Generally acceptable (subset) |
| Different indication, same device type | High | Weak SE basis — consider De Novo |
| Different anatomical site | High | New questions of safety/effectiveness |

## 2. Technological Characteristics Comparison

### Comparison Dimensions

For each predicate, compare these technological characteristics against the subject device:

| Dimension | What to Compare | Source |
|-----------|----------------|--------|
| Materials | Composition, alloys, polymers, coatings | Device description section |
| Principle of operation | Sensing, actuation, therapeutic mechanism | Device description |
| Energy source | Battery, mains, passive, radioactive | Device description |
| Software | IEC 62304 class, AI/ML, connectivity | Software section |
| Dimensions | Size, weight, form factor | Device description |
| Sterilization | Method, SAL, residuals | Sterilization section |
| Biocompatibility | Contact type, duration, ISO 10993 battery | Biocompatibility section |
| Shelf life | Duration, storage conditions | Shelf life section |
| Packaging | Sterile barrier, transport | Device description |
| Accessories | Required ancillary devices | Device description/IFU |

### Difference Classification

| Classification | Definition | SE Impact |
|---------------|-----------|-----------|
| **Same** | Identical or functionally equivalent | Supports SE |
| **Similar, no new questions** | Different but doesn't raise new safety/effectiveness questions | Supports SE with justification |
| **Similar, new questions** | Different and raises new questions answerable by bench data | SE possible with testing |
| **Different** | Fundamentally different technology | SE not possible for this characteristic |

### Device-Type Templates

Cross-reference with device-type comparison templates in `compare-se.md`:
- CGM: MARD, sensor duration, calibration, reportable range
- Wound dressings: MVTR, absorption, antimicrobial agent, contact layer
- Orthopedic: fatigue life, materials, fixation method, surface treatment
- Cardiovascular: hemodynamic performance, contact duration, MRI safety
- Software/SaMD: classification level, algorithm type, input/output data

## 3. Regulatory History Analysis

### Per-Predicate Assessment

For each predicate, evaluate regulatory history:

**MAUDE Event Analysis:**
- Query openFDA device/event for the predicate's product code
- Count events by type (Malfunction, Injury, Death)
- Compute event rate: events / years since clearance
- Compare to product code average event rate
- Flag outliers (>2x average rate)

**Recall History:**
- Query openFDA device/recall for the predicate's K-number
- Classify by recall class (I = most serious, III = least)
- Identify root cause categories
- Assess whether recall reason is relevant to subject device

**Risk Assessment Matrix:**

| Factor | Low Risk | Moderate Risk | High Risk |
|--------|---------|---------------|-----------|
| MAUDE events | <10 total | 10-100 | >100 or any deaths |
| Recalls | None | Class II/III | Class I |
| Predicate age | <5 years | 5-10 years | >10 years |
| Decision type | SESE (standard) | SESD (conditions) | SESU (unknown) |
| Product code match | Exact match | Same panel | Different panel |

**Per-Predicate Risk Score (0-100):**
- 80-100: Low regulatory risk — strong predicate choice
- 50-79: Moderate risk — viable but address concerns
- 20-49: Elevated risk — consider alternatives
- 0-19: High risk — strongly reconsider

## 4. Predicate Chain Analysis

### Chain Health Assessment

Trace the predicate lineage 2 generations deep (predicate's predicate's predicate):

```
Subject Device → Predicate (K123456) → Predicate's Predicate (K098765) → K087654
```

**Data Sources for Chain:**
1. Predicate's 510(k) summary/SE section — extract cited predicates
2. openFDA 510k endpoint — may list predicates in older records
3. PDF text extraction — search for K-numbers in predicate's document

**Chain Health Indicators:**

| Indicator | Healthy | Concerning |
|-----------|---------|------------|
| Chain length | 2-5 generations | >10 generations (predicate creep) |
| Chain breaks | All devices still on market | Recalled/withdrawn device in chain |
| IFU drift | Consistent IFU across chain | Progressive IFU expansion |
| Technology drift | Similar technology across chain | Major tech changes without clinical data |
| Time span | <20 years total | >30 years (ancestor relevance questionable) |

**Chain Health Score (0-100):**
- Deduct 10 pts per recalled device in chain
- Deduct 15 pts if chain exceeds 8 generations
- Deduct 20 pts if IFU significantly differs from chain ancestor
- Deduct 10 pts per technology change without supporting data
- Deduct 5 pts per decade of total chain span beyond 10 years

### Simplified Output Format

```markdown
#### Predicate Chain: K123456

K123456 (2023) ← K098765 (2018) ← K087654 (2014)
Chain length: 3 generations | Span: 9 years
Chain health: 85/100 — Healthy

Issues: None identified
```

## 5. Gap Analysis Decision Tree

### Identify SE Gaps

For each technological difference between subject and predicate:

```
Is the characteristic SAME?
  → YES: No gap. Document as "Same."
  → NO: Continue ↓

Does the difference raise new questions of safety or effectiveness?
  → NO: Document as "Similar — no new questions." Provide brief justification.
  → YES: Continue ↓

Can the new questions be answered by bench testing alone?
  → YES: Gap type = TESTING_GAP. Identify specific tests needed.
  → NO: Continue ↓

Can the new questions be answered by non-clinical data (bench + literature)?
  → YES: Gap type = DATA_GAP. Identify data sources.
  → NO: Continue ↓

Does the difference require clinical data?
  → YES: Gap type = CLINICAL_GAP. This is a Pre-Sub discussion topic.
  → NO (it's a fundamental difference):
    → Gap type = SE_BARRIER. This characteristic may prevent SE.
```

### Gap-to-Question Mapping

| Gap Type | Pre-Sub Question Template |
|----------|--------------------------|
| TESTING_GAP | "We propose to test {characteristic} using {standard/method}. Does FDA agree this is sufficient?" |
| DATA_GAP | "We plan to support {characteristic} with {bench data + literature}. Is clinical data required?" |
| CLINICAL_GAP | "What clinical study design does FDA recommend to address {difference}?" |
| SE_BARRIER | "Given the difference in {characteristic}, does FDA agree the 510(k) pathway remains appropriate?" |

## 6. Predicate Justification Narrative Template

### Structure

For each predicate, generate a 1-2 paragraph narrative:

**Paragraph 1 — Predicate identification and relevance:**
> {K-number} ({device_name}, {applicant}, cleared {date}) is proposed as a predicate device because it shares the same intended use as the subject device: {shared IFU summary}. The predicate is classified under product code {code} (21 CFR {regulation}, Class {class}), which is {the same as / related to} the subject device's classification. {If same applicant: "The predicate was cleared by the same applicant."} {If recent: "The predicate was recently cleared, demonstrating current FDA acceptance of this device type."}

**Paragraph 2 — SE basis and differences:**
> The subject device and predicate share {same/similar} technological characteristics including {list key shared features}. {If differences exist: "The subject device differs from the predicate in {difference list}. These differences {do not raise / raise addressable} new questions of safety and effectiveness because {justification}. {If testing planned: "Additional testing per {standard} will demonstrate equivalence for {characteristic}."}"}

### Narrative Quality Checklist

- [ ] Identifies predicate by K-number, name, applicant, clearance date
- [ ] States shared intended use explicitly
- [ ] References classification and regulation number
- [ ] Lists key shared technological characteristics
- [ ] Addresses each significant difference
- [ ] Explains why differences don't raise new questions (or how they'll be addressed)
- [ ] References specific testing standards if applicable
- [ ] Professional regulatory tone (no marketing language)

## Cross-References

- `confidence-scoring.md` — Scoring algorithm for predicate confidence
- `section-patterns.md` — Regex patterns for extracting device data from PDFs
- `guidance-lookup.md` — Cross-cutting guidance requirements
- `predicate-lineage.md` — Lineage tracing methodology
- `risk-management-framework.md` — Risk analysis integration
- `openfda-api.md` — API endpoints and field mappings
