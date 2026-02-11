# FDA Recognized Consensus Standards Database (RCSD)

## Overview

The FDA maintains a searchable database of recognized consensus standards at:
https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfStandards/search.cfm

Manufacturers may use recognized consensus standards in premarket submissions to support a presumption of conformity (21 CFR Part 514(d)(1) for drugs; 21 CFR 861 for devices).

## Key Concepts

### Recognition Status
- **Recognized**: FDA has determined the standard is suitable for regulatory submissions
- **Partially Recognized**: FDA recognizes specific sections/clauses only
- **Withdrawn**: Previously recognized but no longer current — submissions citing this version may need justification

### Standard vs. FDA Recognized Version
A standard may exist in multiple editions, but FDA only recognizes specific versions. For example:
- ISO 10993-1 exists as 2009, 2018, and 2025 editions
- FDA may recognize the 2025 edition while accepting the 2018 edition during a transition period

### Transition Periods
When FDA recognizes a new edition, a transition period (typically 2-3 years) allows manufacturers to:
1. Continue citing the old edition during transition
2. Update testing protocols to the new edition
3. Plan for submissions after transition deadline

## Query Patterns

### By Standard Number
Search the RCSD for a specific standard:
```
URL: https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfStandards/search.cfm
Parameters: standard_number={number}
```

### By Product Code / Regulation Number
Standards are linked to device classifications through their regulation numbers (21 CFR sections). To find applicable standards:
1. Look up the device's regulation number from classification data
2. Search RCSD for standards associated with that regulation
3. Also check cross-cutting standards applicable to the device class

### Common Standard Associations by Device Type

**All Medical Devices**:
- ISO 14971 (Risk Management)
- ISO 13485 (QMS)

**Patient-Contacting Devices**:
- ISO 10993 series (biological evaluation — part selection per contact type and duration)

**Sterile Devices**:
- ISO 11135 (EO sterilization)
- ISO 11137 (radiation sterilization)
- ISO 17665 (moist heat)
- ISO 11737 (bioburden/sterility testing)
- ISO 11607 (packaging)

**Powered Devices**:
- IEC 60601-1 (general safety)
- IEC 60601-1-2 (EMC)
- IEC 60601-1-6 (usability) or IEC 62366-1

**Software Devices**:
- IEC 62304 (software lifecycle)
- IEC 82304-1 (health software)
- AAMI TIR57 / IEC 81001-5-1 (cybersecurity, if connected)

**IVD Devices**:
- ISO 15189 (lab quality)
- Device-specific performance standards

## De Novo and Recognized Standards

De Novo classified devices may have special controls that reference specific consensus standards. These special controls are published in the Federal Register and serve as the testing roadmap for subsequent 510(k) submissions under that product code.

## Supersession Tracking

Key recent supersessions to monitor:

| Old Edition | New Edition | FDA Recognition | Transition Deadline |
|-------------|-------------|-----------------|---------------------|
| ISO 10993-1:2018 | ISO 10993-1:2025 | 2025-11-18 | 2027-11-18 |
| ISO 11137-1:2006/A2:2019 | ISO 11137-1:2025 | 2025-06-01 | 2027-06-01 |
| ISO 17665-1:2006 | ISO 17665:2024 | 2024-12-01 | 2026-12-01 |

## Integration Points

- `/fda:standards` — Primary query command for this database
- `/fda:test-plan` — Cross-references standards when building test plans
- `/fda:guidance` — FDA guidance documents cite specific standards
- `/fda:monitor --watch-standards` — Monitors for standard updates
- `/fda:traceability` — Maps standards to requirements in traceability matrix
