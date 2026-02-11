# FDA Regulatory Pathway Decision Tree

## Decision Flow

```
Is the device exempt from 510(k)?
+-- YES -> No 510(k) required (verify exemption limitations)
|         Check: 21 CFR regulation for your product code
|         Note: Exempt devices still must comply with general controls
|
+-- NO -> Is the device Class III?
    +-- YES -> PMA (unless reclassified or De Novo eligible)
    |         Consider: Breakthrough Device Designation for priority review
    |
    +-- NO -> Does a legally marketed predicate exist?
        +-- YES -> Is this a modification of your own cleared device?
        |   +-- YES -> Does the modification change intended use or raise
        |   |          new safety/effectiveness questions?
        |   |   +-- YES -> Traditional 510(k) (modification too significant for Special)
        |   |   +-- NO -> Special 510(k)
        |   +-- NO -> Does device-specific guidance with special controls exist?
        |       +-- YES -> Consider Abbreviated 510(k)
        |       +-- NO -> Traditional 510(k) (default)
        |               Consider: Third-Party Review (APDP) for eligible devices
        +-- NO -> Is the device low-to-moderate risk?
            +-- YES -> De Novo Classification Request
            +-- NO -> PMA
```

## Pathway Characteristics

### Traditional 510(k)
- **When**: Standard predicate comparison
- **Timeline**: 3-6 months FDA review (90-day MDUFA performance goal, not a legal deadline)
- **Fee**: Verify current fees at [FDA MDUFA fee schedule](https://www.fda.gov/medical-devices/device-advice-comprehensive-regulatory-assistance/medical-device-user-fee-amendments-mdufa). Standard 510(k) fees are typically $15,000-$25,000; small businesses pay a reduced rate (~40-60% of standard).
- **Key requirement**: Demonstrate substantial equivalence to predicate
- **FDA citation**: 21 CFR 807 Subpart E

### Special 510(k)
- **When**: Modifying your own previously cleared device
- **Timeline**: 30-day FDA review target
- **Fee**: Same as Traditional
- **Key requirement**: Design controls documentation for modification
- **FDA citation**: "The New 510(k) Paradigm" guidance

### Abbreviated 510(k)
- **When**: Strong guidance/special controls/standards cover the device
- **Timeline**: 3-6 months
- **Fee**: Same as Traditional
- **Key requirement**: Conformance to recognized standards and special controls
- **FDA citation**: "The New 510(k) Paradigm" guidance

### De Novo
- **When**: No predicate exists, but device is low-to-moderate risk
- **Timeline**: 6-12 months
- **Fee**: Verify current fees at [FDA MDUFA fee schedule](https://www.fda.gov/medical-devices/device-advice-comprehensive-regulatory-assistance/medical-device-user-fee-amendments-mdufa). De Novo fees are substantially higher than 510(k) fees (historically $100,000+); small business reductions apply.
- **Key requirement**: Risk-benefit analysis, proposed classification
- **FDA citation**: 21 CFR 860.260

### PMA
- **When**: Class III, high risk, life-sustaining/supporting
- **Timeline**: 12-24+ months
- **Fee**: Verify current fees at [FDA MDUFA fee schedule](https://www.fda.gov/medical-devices/device-advice-comprehensive-regulatory-assistance/medical-device-user-fee-amendments-mdufa). PMA fees are the highest MDUFA fees (historically $400,000+); small business reductions apply.
- **Key requirement**: Clinical evidence of safety and effectiveness
- **FDA citation**: 21 CFR 814

### 510(k) Exempt Devices
- **When**: Device's 21 CFR regulation includes an exemption from 510(k) (most Class I and some Class II devices)
- **Verify**: Check `foiaclass.txt` or openFDA classification — `510k_exempt` field
- **Limitations**: Exemptions typically have limitations (e.g., device must not be labeled/promoted for a use different from the exempted use, cannot have a different intended use, must comply with general controls)
- **No fee**: No MDUFA user fee for exempt devices
- **Still required**: Establishment registration, device listing, QMS compliance, MDR

### Third-Party Review (Accredited Persons / APDP)
- **When**: Device eligible for third-party review per FDA's Accredited Persons program
- **Timeline**: Typically faster than direct FDA review (30-day FDA decision after third-party review)
- **Fee**: Third-party reviewer fees (set by the reviewer, not FDA) PLUS reduced MDUFA fee
- **Eligible devices**: Specific product codes listed by FDA; generally lower-risk Class II devices
- **Key advantage**: Faster review timeline with independent qualified review
- **FDA citation**: Section 523 of the FD&C Act (Accredited Persons program)

### Breakthrough Device Designation
- **When**: Device provides more effective treatment/diagnosis of life-threatening or irreversibly debilitating conditions AND meets one of: (a) represents breakthrough technology, (b) no approved alternative exists, (c) offers significant advantages, (d) is in best interest of patients
- **Applies to**: Any pathway (510(k), De Novo, PMA) — accelerates whichever pathway applies
- **Benefits**: Priority review, interactive communication with FDA, senior management involvement, flexible clinical study design
- **FDA citation**: Section 515B of the FD&C Act

### Letter to File (LTF)
- **When**: A change to your own previously cleared device does NOT require a new 510(k)
- **Criteria** (per FDA guidance "Deciding When to Submit a 510(k) for a Change to an Existing Device"):
  - Change does not affect intended use
  - Change does not alter fundamental scientific technology
  - Change does not create new risks or significantly affect existing risks
- **Documentation**: Written evaluation documenting that the change does not trigger a new 510(k), maintained in design history file
- **Risk**: If FDA disagrees with the LTF determination, the device may be considered adulterated/misbranded

## Scoring Weights

| Factor | Weight | Rationale |
|--------|--------|-----------|
| Predicate availability | 30% | Foundation of 510(k) pathway |
| Guidance/standard coverage | 25% | Reduces review uncertainty |
| Technology novelty | 25% | Novel features may require new pathway |
| Clinical data need | 20% | Drives timeline and cost |
