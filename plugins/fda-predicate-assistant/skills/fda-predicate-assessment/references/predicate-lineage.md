# Predicate Lineage Analysis Reference

## Background

Research published in *The Lancet Digital Health* (2023) demonstrated that 510(k) predicate networks form complex, multi-generational chains. Some devices trace their substantial equivalence back through 10+ generations to devices cleared decades ago, sometimes with recalled intermediaries.

Understanding the predicate lineage is critical for:
1. **Risk assessment**: Recalled ancestors may indicate design flaws propagated through the chain
2. **FDA scrutiny**: FDA increasingly examines predicate chains during review
3. **Predicate selection defense**: A strong, well-documented lineage strengthens your SE argument

## Chain Health Scoring

### Scoring Components (0-100)

| Factor | Max Points | Criteria |
|--------|-----------|----------|
| No recalled ancestors | 30 | Full 30 if clean chain; -10 per Class II/III recall; -20 per Class I recall |
| Product code consistency | 20 | Full 20 if all same code; -5 per code deviation; 0 if >3 different codes |
| Chain completeness | 15 | Full 15 if all generations traced; proportional if partial |
| Recency | 15 | Average ancestor decision_date: <5yr=15, 5-10yr=10, 10-15yr=5, >15yr=2 |
| No revoked clearances | 10 | Full 10 if none revoked; 0 if any revoked |
| Chain diversity | 10 | Full 10 if multiple independent paths; 5 if linear; 0 if single-thread |

### Interpretation

| Score | Rating | Guidance |
|-------|--------|----------|
| 80-100 | Strong | Low regulatory risk. Predicate chain is well-established. |
| 50-79 | Moderate | Some concerns. Consider discussing chain in Pre-Sub. Document mitigations for any recalled ancestors. |
| 25-49 | Weak | High risk. Consider alternative predicates. If no alternatives, prepare detailed justification. |
| 0-24 | Critical | Chain has serious issues (multiple recalls, revoked clearances). Strongly recommend alternative predicates or De Novo pathway. |

## Common Lineage Patterns

### Healthy Patterns
- **Wide tree**: Multiple predicates at each generation, providing redundancy
- **Recent chain**: Most ancestors <10 years old
- **Same-company chain**: Manufacturer has history of cleared devices in this space
- **Consistent product code**: All ancestors share the same code

### Risk Patterns
- **Single-thread**: Each generation cites only one predicate — if any link is weak, the whole chain fails
- **Ancient root**: Chain traces back to a pre-amendments device (N-number) — technology may have evolved significantly
- **Cross-code jumps**: Predicates from different product codes — may indicate creative predicate selection that FDA scrutinizes
- **Recalled intermediary**: A device in the chain was recalled but its descendants continue to be cited
- **Predicate stacking**: Using multiple predicates to cover different aspects — legitimate but requires careful SE justification

## Visualization Format

### Text Tree
```
K241335 (2024) — Device A [CLEAN]
├── K200123 (2020) — Device B [CLEAN]
│   ├── K170456 (2017) — Device C [RECALLED-II]
│   │   └── K120789 (2012) — Device D [CLEAN]
│   └── K180999 (2018) — Device E [CLEAN]
└── K190555 (2019) — Device F [CLEAN]
    └── K150333 (2015) — Device G [CLEAN]
```

### JSON Structure
See `lineage.json` schema in the `/fda:lineage` command documentation.

## Data Sources for Lineage Tracing

In order of preference:
1. **PDF text extraction**: Most reliable — parse predicates from actual 510(k) summary PDFs
2. **Project output.csv**: From previous extraction runs
3. **openFDA API**: For device metadata (names, dates, product codes, recalls)
4. **Flat files (pmn*.txt)**: For K-number validation

## Limitations

- openFDA does not store predicate relationships directly — these must be extracted from PDFs
- Older devices (pre-2000) may not have accessible PDF summaries
- Some devices cite predicates in tables/images that text extraction may miss
- Pre-amendments devices (N-numbers) have limited metadata available
