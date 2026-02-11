# Complaint Handling Framework

## Regulatory Basis

- **21 CFR 820.198** — Complaint Files (pre-QMSR)
- **21 CFR Part 820 (QMSR)** — Incorporates ISO 13485:2016 complaint handling
- **21 CFR 803** — Medical Device Reporting (MDR)
- **ISO 13485:2016 Section 8.2.2** — Complaint handling

## Complaint Intake Template

### Required Information

| Field | Description | Required? |
|-------|-------------|-----------|
| Complaint ID | Unique identifier | Yes |
| Date received | Date complaint was received | Yes |
| Source | Customer, field, distributor, user | Yes |
| Product | Device name, model, lot/serial | Yes |
| Description | Detailed description of complaint | Yes |
| Patient involvement | Was a patient affected? | Yes |
| Injury/death | Did injury or death occur? | Yes |
| Device available? | Is the device available for investigation? | Yes |
| Complainant contact | Name, contact info | Recommended |

### Complaint Categories

| Category | Description | MDR Reportable? |
|----------|-------------|----------------|
| Malfunction | Device did not perform as intended | If could cause/contribute to death or serious injury |
| Injury | Patient or user was injured | Yes (if serious) |
| Death | Patient or user died | Yes (always) |
| Labeling | Missing/incorrect labeling | If could cause misuse leading to harm |
| Packaging | Packaging integrity compromise | If sterility affected |
| Cosmetic | Appearance issue, no functional impact | No |

## MDR Reportability Decision Tree

### Is This Event MDR Reportable?

1. **Did a death occur?**
   - Yes → **REPORTABLE** (5 working days for manufacturers, 10 working days for user facilities)
   - No → Continue

2. **Did a serious injury occur?**
   - Yes → **REPORTABLE** (30 calendar days for manufacturers, 10 working days for user facilities)
   - No → Continue

3. **Did a malfunction occur that COULD cause or contribute to death or serious injury if it were to recur?**
   - Yes → **REPORTABLE** (30 calendar days for manufacturers)
   - No → **NOT REPORTABLE** (document decision)

### Serious Injury Definition (21 CFR 803.3)

An injury that:
- Is life-threatening
- Results in permanent impairment of a body function or permanent damage to body structure
- Necessitates medical or surgical intervention to preclude either of the above

## Trend Analysis Template

### Quarterly Complaint Trend Report

| Quarter | Total | Malfunction | Injury | Death | MDR Filed |
|---------|-------|-------------|--------|-------|-----------|
| Q1 2026 | | | | | |
| Q2 2026 | | | | | |
| Q3 2026 | | | | | |
| Q4 2026 | | | | | |

### Trend Indicators

| Indicator | Threshold | Action |
|-----------|-----------|--------|
| Complaint rate increase | >50% quarter-over-quarter | Investigation required |
| New failure mode | First occurrence | Root cause analysis |
| Injury rate increase | Any increase | Immediate review |
| Death event | Any occurrence | Immediate escalation |

## MAUDE Data Integration

Use `/fda:safety` MAUDE data to:
1. **Benchmark complaint rates** against industry for your product code
2. **Identify known failure modes** in similar devices
3. **Support trend analysis** with external data context
4. **Inform risk management** with real-world adverse event patterns

## Integration with Plugin Commands

- `/fda:safety --product-code CODE` — MAUDE/recall data for this device category
- `/fda:safety --complaint-template` — Generate complaint handling procedure template
- `/fda:monitor --check` — Ongoing monitoring for new safety signals
- `/fda:test-plan` — Risk-based testing addressing complaint patterns
