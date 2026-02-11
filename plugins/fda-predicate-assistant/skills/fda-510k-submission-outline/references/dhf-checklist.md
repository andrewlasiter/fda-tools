# Design History File (DHF) Completeness Checklist

## Regulatory Basis

- **21 CFR 820.30** — Design Controls (pre-QMSR)
- **21 CFR Part 820 (QMSR, effective Feb 2, 2026)** — Quality Management System Regulation incorporating ISO 13485:2016
- **ISO 13485:2016** — Medical devices — Quality management systems — Requirements for regulatory purposes

## DHF Sections Checklist

### 1. Design and Development Planning (820.30(b) / ISO 13485 7.3.2)

- [ ] Design plan with milestones and review points
- [ ] Resource allocation (personnel, equipment, facilities)
- [ ] Regulatory strategy document (pathway, predicate selection)
- [ ] Design phase gate criteria
- [ ] Team roles and responsibilities

### 2. Design Input (820.30(c) / ISO 13485 7.3.3)

- [ ] User needs and intended use statement
- [ ] Performance requirements (functional specifications)
- [ ] Safety requirements (from risk analysis)
- [ ] Regulatory requirements (from guidance analysis)
- [ ] Standards requirements (ISO, IEC, ASTM)
- [ ] Environmental and storage requirements
- [ ] Labeling requirements
- [ ] Interface requirements (hardware, software, user)
- [ ] Design input review and approval records

### 3. Design Output (820.30(d) / ISO 13485 7.3.4)

- [ ] Device specifications (drawings, materials, dimensions)
- [ ] Software specifications (if applicable)
- [ ] Manufacturing process specifications
- [ ] Packaging and labeling specifications
- [ ] Acceptance criteria for finished device
- [ ] Essential design outputs for device functioning

### 4. Design Review (820.30(e) / ISO 13485 7.3.5)

- [ ] Formal design review records at each phase gate
- [ ] Participants (including independent reviewer)
- [ ] Review of design inputs vs. outputs
- [ ] Issues identified and actions taken
- [ ] Design review approval records

### 5. Design Verification (820.30(f) / ISO 13485 7.3.6)

- [ ] Verification plan (what, how, acceptance criteria)
- [ ] Bench testing results
- [ ] Biocompatibility testing results (ISO 10993)
- [ ] Sterilization validation results (if applicable)
- [ ] Shelf life / packaging validation results
- [ ] EMC / electrical safety results (if applicable)
- [ ] Software testing results (if applicable)
- [ ] Performance testing results
- [ ] Verification summary and conclusions

### 6. Design Validation (820.30(g) / ISO 13485 7.3.7)

- [ ] Validation plan
- [ ] Clinical evidence (study, literature, or exemption rationale)
- [ ] Human factors validation (if applicable)
- [ ] Simulated use testing
- [ ] User acceptance testing
- [ ] Validation under actual or simulated use conditions
- [ ] Validation summary and conclusions

### 7. Design Transfer (820.30(h) / ISO 13485 7.3.8)

- [ ] Manufacturing process validation
- [ ] Process verification records
- [ ] Training records for manufacturing personnel
- [ ] Quality control procedures
- [ ] Production and process controls

### 8. Design Changes (820.30(i) / ISO 13485 7.3.9)

- [ ] Change control records
- [ ] Impact assessment for each change
- [ ] Re-verification and re-validation (as needed)
- [ ] Change approval records
- [ ] PCCP documentation (if applicable)

### 9. Risk Management (ISO 14971:2019)

- [ ] Risk management plan
- [ ] Hazard identification (all foreseeable hazards)
- [ ] Risk estimation (severity x probability)
- [ ] Risk evaluation (acceptability matrix)
- [ ] Risk control measures
- [ ] Residual risk evaluation
- [ ] Risk-benefit analysis (if residual risk not acceptable)
- [ ] Risk management report
- [ ] Production and post-production risk monitoring

### 10. Requirements Traceability

- [ ] Requirements traceability matrix (RTM)
- [ ] Each requirement traced to verification test
- [ ] Each hazard traced to risk control
- [ ] Each risk control traced to verification
- [ ] Gap analysis (requirements without tests)

## Status Indicators

| Status | Meaning |
|--------|---------|
| Complete | All required documents present and approved |
| In Progress | Documents being developed |
| Not Started | Section not yet addressed |
| N/A | Section not applicable to this device |
| Gap | Required document missing |

## QMSR Transition Notes

The FDA QMSR (effective February 2, 2026) incorporates ISO 13485:2016 by reference, replacing the original 21 CFR 820. Key changes:
- Design control requirements are now aligned with ISO 13485 Section 7.3
- Design and Development Planning requirements expanded
- Clinical evaluation explicitly referenced
- Risk management integration strengthened

## Integration with Plugin Commands

- `/fda:submission-outline --dhf` — Generate DHF checklist alongside submission outline
- `/fda:traceability` — Generate RTM (Section 10)
- `/fda:test-plan` — Map to verification plan (Section 5)
- `/fda:draft` — Generate design output documentation
- `/fda:presub` — Part of regulatory strategy (Section 1)
