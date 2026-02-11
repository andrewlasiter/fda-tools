# Clinical Data Decision Framework

## When Is Clinical Data Required in a 510(k)?

Clinical data is not always required for a 510(k). The decision depends on whether technological differences between the subject device and predicate raise new questions of safety or effectiveness that cannot be resolved with bench data alone.

**Regulatory basis:** Section 513(i) of the FD&C Act and FDA guidance "The 510(k) Program: Evaluating Substantial Equivalence in Premarket Notifications" (2014).

## Decision Tree

```
Does the subject device have the SAME technological characteristics as the predicate?
├── YES → Bench data sufficient (clinical data typically NOT needed)
│         Performance equivalence can be demonstrated with bench/analytical testing
│
└── NO → Do the DIFFERENT technological characteristics raise NEW questions
          of safety or effectiveness?
          ├── NO → Bench data sufficient
          │         Different technology but performance/risk profile is equivalent
          │         Document why differences don't raise new questions
          │
          └── YES → Can new questions be resolved with bench data alone?
                    ├── YES → Bench data sufficient (with strong justification)
                    │         Performance testing demonstrates equivalent safety/effectiveness
                    │
                    └── NO → Clinical data likely needed
                              Choose from: clinical study, literature review,
                              or real-world evidence
```

## Types of Clinical Evidence

| Type | Strength | When to Use | Effort |
|------|----------|-------------|--------|
| Pivotal clinical study | Highest | New clinical claims, no literature, FDA requires | 6-24+ months, highest cost |
| Feasibility/pilot study | Moderate | Generate preliminary data, refine endpoints before pivotal | 3-12 months |
| Literature review | Moderate | Published data supports safety/effectiveness for this technology | 4-8 weeks |
| Real-world evidence (RWE) | Variable | Post-market registries, EHR data for established technology | Varies |
| Predicate clinical precedent | Supporting | Predicate's clearance included clinical data for similar claims | Research only |

## Bench Data Alone — When Sufficient

Clinical data is typically NOT needed when:
- Subject and predicate use the same technology and materials
- Differences are limited to dimensions, aesthetics, or non-functional features
- Performance equivalence can be demonstrated through bench testing
- Predicate precedent shows FDA accepted bench-only submissions for this device type
- The device type has a well-established safety profile (many clearances, low MAUDE events)

**Examples:**
- Modified wound dressing with same materials, different shape → bench data (fluid handling, adhesion)
- Orthopedic implant with updated surface finish, same material/design → bench data (mechanical, biocompatibility)
- Software update adding display feature, no change to algorithm → software V&V

## Literature Review — When It Substitutes for Clinical Study

A literature review may substitute for an original clinical study when:
1. Published clinical data exists for substantially similar devices
2. The data addresses the specific safety/effectiveness questions raised by technological differences
3. Study populations and endpoints are relevant to the subject device's intended use
4. Data quality is adequate (peer-reviewed, adequate sample sizes, appropriate study designs)

**FDA expectations for literature reviews:**
- Systematic search strategy (documented, reproducible)
- Inclusion/exclusion criteria stated
- Quality assessment of included studies
- Analysis addressing specific SE questions
- Clear connection between literature findings and subject device

**Use `/fda:literature` to conduct a structured literature search with gap analysis.**

## Clinical Data Likely Needed

Clinical data is typically needed when:
- Different technological characteristics raise new safety questions (e.g., new energy source, new biological interaction)
- Clinical claims go beyond predicate's cleared claims
- Device has a new mechanism of action
- FDA guidance for the device type recommends clinical data
- Device-specific special controls require clinical performance data
- The device area has significant MAUDE events or recalls suggesting clinical risk

## Pathway-Specific Expectations

### Traditional 510(k)
- Clinical data required only if technological differences cannot be resolved with bench data
- Literature review may suffice if published evidence covers the technology
- FDA may request clinical data during review (AI letter) even if not initially included

### Special 510(k)
- Clinical data rarely needed — modification to own device, design controls primary evidence
- Only needed if modification introduces a new clinical risk not assessed in original clearance

### Abbreviated 510(k)
- Relies on conformance to standards and guidance
- Clinical data expectations defined by applicable guidance/special controls
- If guidance requires clinical, must include it

### De Novo
- Risk-benefit analysis required — clinical data strengthens the case
- Literature review often sufficient for low-risk De Novo
- Pivotal study more common for moderate-risk De Novo
- FDA may negotiate clinical expectations through Pre-Sub

## Pre-Sub Strategy for Clinical Data Uncertainty

If you are uncertain whether clinical data is needed:

1. **Prepare a Pre-Sub** with specific questions:
   - "Given the technological differences between our device and the proposed predicate, does FDA expect clinical data?"
   - "If clinical data is needed, what endpoints and study design would FDA recommend?"
   - "Would a literature review of published data for [technology type] be sufficient?"
2. Include your proposed testing strategy (bench + clinical plan) for FDA to comment on
3. FDA's written feedback is not binding but provides strong direction

**Use `/fda:presub` to generate a Pre-Sub package with clinical data questions.**

## Device Categories — Typical Clinical Data Expectations

| Category | Clinical Data Typical? | Notes |
|----------|----------------------|-------|
| Simple mechanical devices (surgical instruments, dressings) | Rarely | Bench data usually sufficient |
| Orthopedic implants | Sometimes | Depends on novelty; well-established designs may not need clinical |
| Cardiovascular | Often | High-risk area; clinical data common even for 510(k) |
| Software/SaMD (diagnostic) | Often | Clinical performance (sensitivity/specificity) usually required |
| IVD | Sometimes | Analytical performance may suffice; clinical correlation studies for novel analytes |
| Dental | Rarely | Bench data usually sufficient for most dental devices |
| Ophthalmic (contact lenses) | Often | Clinical comfort and fitting studies common |
| Electrical stimulation | Often | Clinical effectiveness data for therapeutic claims |
| AI/ML algorithms | Usually | Clinical validation dataset performance required |

## Clinical Study Requirements Reference

If a clinical study is needed:
- **ISO 14155:2020** — Clinical investigation of medical devices for human subjects
- **21 CFR 812** — Investigational Device Exemptions (IDE) regulations
- **IRB approval** required for all clinical studies with human subjects
- **Informed consent** required per 21 CFR 50
- **IDE requirements**: Significant risk devices need FDA-approved IDE; non-significant risk may proceed with IRB approval only
- **GCP compliance**: Studies must follow Good Clinical Practice
