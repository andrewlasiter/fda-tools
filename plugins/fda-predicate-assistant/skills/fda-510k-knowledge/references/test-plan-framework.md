# Testing Plan Framework Reference

## Risk-Based Testing Prioritization

### ISO 14971 Risk Categories for Testing

| Risk Level | Description | Testing Implication |
|-----------|-------------|---------------------|
| Critical | Device failure could cause serious injury or death | Testing REQUIRED before submission |
| Major | Device failure could cause non-serious injury | Testing STRONGLY RECOMMENDED |
| Standard | Device failure causes inconvenience/discomfort | Testing RECOMMENDED (predicate precedent) |
| Informational | No patient safety impact | Testing OPTIONAL (strengthens submission) |

## Common Testing Categories by Device Type

### Orthopedic Implants (OVE, MAX, etc.)
- Mechanical testing: ASTM F2077 (static/dynamic), ASTM F1717 (spinal), ASTM F2267 (cervical)
- Fatigue testing: ASTM F2077 Annex (dynamic fatigue)
- Wear testing: ASTM F2423
- Corrosion: ASTM F2129
- Biocompatibility: ISO 10993-1, -5, -10, -11, -12
- Sterilization: ISO 11135 (EO) or ISO 11137 (gamma)
- Shelf life: ASTM F1980
- MRI safety: ASTM F2052, F2213, F2182

### Wound Dressings (KGN, FRO)
- Fluid handling: EN 13726
- MVTR: ASTM E96
- Adhesion: ASTM D3330
- Biocompatibility: ISO 10993-1, -5, -10
- Antimicrobial (if claimed): AATCC 100, ASTM E2149
- Sterilization: ISO 11135/11137
- Shelf life: ASTM F1980

### CGM/IVD (QBJ, SBA)
- Analytical performance: ISO 15197
- Accuracy (MARD): Per FDA CGM guidance
- Precision: EP05-A3
- Linearity: EP06-A
- Interference: EP07-A3
- Biocompatibility: ISO 10993-1, -5, -10
- Software: IEC 62304
- Electrical safety: IEC 60601-1
- Cybersecurity: FDA cybersecurity guidance

## Timeline Estimates

| Test Category | Typical Duration | Dependencies |
|--------------|-----------------|-------------|
| Biocompatibility | 8-16 weeks | Final materials |
| Mechanical/Performance | 4-12 weeks | Design freeze |
| Sterilization validation | 6-12 weeks | Final packaging |
| Shelf life (accelerated) | 4-8 weeks | Final packaging |
| Software V&V | 4-8 weeks | Design freeze |
| Clinical study | 6-24 months | IRB, protocol |
