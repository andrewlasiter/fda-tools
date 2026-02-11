# Clinical Study Design Framework for 510(k) Submissions

## When Is Clinical Data Needed?

### Decision Tree

1. **Does FDA guidance for this device require clinical data?**
   - Yes → Clinical data required (see guidance-specific requirements)
   - No → Continue to step 2

2. **Are there technological differences from predicate that raise new safety/effectiveness questions?**
   - Yes → Clinical data likely needed
   - No → Continue to step 3

3. **Is the intended use broader than predicate?**
   - Yes → Clinical data for new indications
   - No → Continue to step 4

4. **Did all predicates rely on bench testing only (no clinical)?**
   - Yes → Bench testing precedent supports no clinical data
   - No → Consider clinical data if predicates required it

5. **Does the device contact patients for extended periods?**
   - Yes → Clinical data recommended (implants, long-term contact)
   - No → Bench testing may be sufficient

### Regulatory References

- **21 CFR 807.87(j)**: "Any clinical data ... in the possession or otherwise available to the submitter"
- **FDA Guidance**: "Deciding When to Submit a 510(k) for a Change to an Existing Device" (K97-1)
- **FDA Guidance**: "The 510(k) Program: Evaluating Substantial Equivalence in Premarket Notifications"

## Study Types

### 1. Pivotal Clinical Study

**When needed**: New technology, expanded indications, high-risk device classes
**Design**: Randomized controlled trial (RCT) or single-arm with performance goals
**Requirements**:
- IRB approval
- IDE (Investigational Device Exemption) if significant risk
- Informed consent
- Statistical analysis plan (SAP)
- Monitoring plan

### 2. Feasibility/Pilot Study

**When needed**: Early-stage evidence, design optimization
**Design**: Small sample, often single-arm
**Requirements**:
- IRB approval
- IDE (abbreviated for non-significant risk)
- Focus on safety and preliminary effectiveness

### 3. Literature-Based Clinical Evidence

**When needed**: Well-established device type with published evidence
**Design**: Systematic literature review
**Requirements**:
- Documented search strategy (PubMed, Embase)
- Inclusion/exclusion criteria
- Quality assessment of studies
- Summary of evidence (PRISMA or similar)

### 4. Clinical Experience / Retrospective Data

**When needed**: Post-market data supports safety/effectiveness
**Design**: Retrospective chart review, registry data
**Requirements**:
- IRB approval (may be exempt)
- Data quality assessment
- Statistical methods

## Sample Size Considerations

### Performance Goal (Single-Arm) Studies

For binary endpoints (success/failure):
- **Target success rate**: p₀ (e.g., 95%)
- **Clinically meaningful difference**: δ (e.g., 5%)
- **Significance level**: α = 0.05 (one-sided)
- **Power**: 1 - β = 0.80

Example: To demonstrate ≥90% success rate with 80% power:
- N ≈ 73 subjects (exact binomial calculation)
- With 10% dropout: N ≈ 82 enrolled

### Comparative (Two-Arm) Studies

For non-inferiority with binary endpoint:
- **Expected rate**: p₁ ≈ p₂ (e.g., 95%)
- **Non-inferiority margin**: δ (e.g., 10%)
- **Significance level**: α = 0.025 (one-sided)
- **Power**: 1 - β = 0.80

Example: Non-inferiority with 10% margin:
- N ≈ 160 per arm
- With 15% dropout: N ≈ 188 per arm enrolled

## Clinical Endpoints

### Common Endpoint Categories

| Category | Primary Endpoints | Secondary Endpoints |
|----------|------------------|---------------------|
| Safety | Adverse event rate, serious AE rate | Device-related complications |
| Effectiveness | Clinical success (composite) | Individual success criteria |
| Performance | Technical success rate | Procedure time, ease of use |
| Patient-reported | Pain reduction (VAS) | Quality of life (SF-36, EQ-5D) |

### Device-Specific Endpoint Examples

| Device Type | Common Primary Endpoint |
|-------------|------------------------|
| Orthopedic implant | Fusion rate at 12-24 months |
| Wound dressing | Complete wound closure rate |
| Cardiac device | Major adverse cardiac events (MACE) |
| Diagnostic software | Sensitivity/specificity vs. reference standard |
| Surgical instrument | Procedure success rate |

## FDA Clinical Guidance Documents

| Guidance | Relevance |
|----------|-----------|
| Guidance for Industry: Providing Clinical Evidence for Diagnostic Tests | IVD devices |
| Reporting of Computational Modeling Studies in Medical Device Submissions | In silico evidence |
| Use of Real-World Evidence to Support Regulatory Decision-Making | RWE for devices |
| Clinical Performance Assessment: Considerations for Computer-Assisted Detection | CADe/CADx devices |
| De Novo Classification Process | Clinical evidence for novel devices |

## Integration with Plugin Commands

- `/fda:draft clinical` — Generate clinical evidence section (Section 16)
- `/fda:literature` — Systematic literature search for clinical evidence
- `/fda:safety` — MAUDE adverse event data as clinical context
- `/fda:test-plan` — Clinical testing included in comprehensive test plan
- `/fda:presub` — Clinical study design questions for Pre-Sub meeting
