# FDA Regulatory Pathway Decision Tree

## Decision Flow

```
Is the device Class III?
+-- YES -> PMA (unless reclassified or De Novo eligible)
+-- NO -> Does a legally marketed predicate exist?
    +-- YES -> Is this a modification of your own cleared device?
    |   +-- YES -> Special 510(k)
    |   +-- NO -> Does device-specific guidance with special controls exist?
    |       +-- YES -> Consider Abbreviated 510(k)
    |       +-- NO -> Traditional 510(k) (default)
    +-- NO -> Is the device low-to-moderate risk?
        +-- YES -> De Novo Classification Request
        +-- NO -> PMA
```

## Pathway Characteristics

### Traditional 510(k)
- **When**: Standard predicate comparison
- **Timeline**: 3-6 months FDA review (90-day target)
- **Fee**: ~$21,760 (FY2026 standard, small business reduced)
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
- **Fee**: ~$130,000+ (FY2026)
- **Key requirement**: Risk-benefit analysis, proposed classification
- **FDA citation**: 21 CFR 860.260

### PMA
- **When**: Class III, high risk, life-sustaining/supporting
- **Timeline**: 12-24+ months
- **Fee**: ~$425,000+ (FY2026)
- **Key requirement**: Clinical evidence of safety and effectiveness
- **FDA citation**: 21 CFR 814

## Scoring Weights

| Factor | Weight | Rationale |
|--------|--------|-----------|
| Predicate availability | 30% | Foundation of 510(k) pathway |
| Guidance/standard coverage | 25% | Reduces review uncertainty |
| Technology novelty | 25% | Novel features may require new pathway |
| Clinical data need | 20% | Drives timeline and cost |
