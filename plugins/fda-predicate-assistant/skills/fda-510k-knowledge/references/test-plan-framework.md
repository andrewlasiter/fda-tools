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
- Mechanical testing: ASTM F2077 (static/dynamic), ASTM F1717 (spinal), ASTM F2267 (subsidence)
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

### Cardiovascular Devices (DQY, DTB, DXY)
- Burst/rupture pressure: Per device-specific guidance
- Compliance/distensibility: ASTM standards
- Fatigue testing: Simulated use with clinically relevant cycling
- Corrosion resistance: ASTM F2129
- Thrombogenicity: ISO 10993-4
- Biocompatibility: ISO 10993-1, -4, -5, -6, -10, -11
- Sterilization: ISO 11135 (EO) or ISO 11137 (gamma)
- Shelf life: ASTM F1980
- MRI safety: ASTM F2052, F2213, F2182 (if implantable)
- Electrical safety: IEC 60601-1 (if powered)

### Software / SaMD (QMT, QAS)
- Software documentation level: Basic or Enhanced per FDA guidance
- Software description and architecture
- Hazard analysis: Per IEC 62304:2006+A1:2015
- Verification and validation: IEC 62304 lifecycle activities
- Usability/human factors: IEC 62366-1:2015
- Cybersecurity: FDA cybersecurity guidance, AAMI TIR57, IEC 81001-5-1
- Clinical performance: Per device-specific guidance (CADe/CADx: sensitivity, specificity, AUC)
- Interoperability: If device exchanges data with other systems
- Algorithm validation: Training/test dataset characterization (AI/ML)

### Dental Devices (EBP, HQF)
- Mechanical testing: Bond strength (shear, tensile), fracture resistance
- Corrosion resistance: ISO 10271 (metallic), ASTM standards
- Biocompatibility: ISO 10993-1, -5, -10 (all dental devices); -11, -6 (implants)
- Sterilization: ISO 11135/11137 (if provided sterile)
- Shelf life: ASTM F1980 (if expiration date)
- Dimensional accuracy: Per device specifications
- Color stability: ASTM D2244 (if aesthetic claims)

### General Surgery Instruments (GEI, FZP)
- Mechanical performance: Cut/grip/clamp force testing
- Durability/fatigue: Repeated use simulation
- Reprocessing validation: Cleaning, disinfection, sterilization per ISO 17664
- Biocompatibility: ISO 10993-1, -5, -10 (patient-contacting surfaces)
- Corrosion resistance: ASTM F2129 (if metallic)
- Sterilization: ISO 17665 (steam), ISO 11135 (EO), or ISO 11137 (radiation)
- Shelf life: ASTM F1980 (if single-use, sterile)
- Electrical safety: IEC 60601-1 (if powered)

### Ophthalmic Devices (HQD, MQG)
- Optical performance: Transmittance, refractive power, resolution
- Biocompatibility: ISO 10993-1, -5, -10 (contact lens); -5, -10, -11 (intraocular)
- Cytotoxicity (ocular): ISO 10993-5 with ocular-relevant cell lines
- Sterility: ISO 11135/11137 (intraocular devices)
- Shelf life: ASTM F1980, real-time aging
- Dimensional testing: Per ISO standards for lenses
- UV/light filtering: Per applicable optical standards
- Extractables/leachables: ISO 10993-12, -18 (contact lens materials)

### Respiratory / Anesthesia Devices (BTK, CBF)
- Flow accuracy: Per device-specific standards
- Pressure performance: Delivery pressure accuracy, relief valve testing
- Electrical safety: IEC 60601-1, IEC 60601-1-2 (EMC)
- Alarm testing: IEC 60601-1-8 (medical alarms)
- Biocompatibility: ISO 10993-1, -5, -10 (breathing circuit materials)
- Sterilization/reprocessing: ISO 17664 (reusable), ISO 11135/11137 (single-use)
- Software: IEC 62304 (if software-controlled)
- Human factors: IEC 62366-1 (critical for alarm management)
- Gas pathway testing: Leak, resistance to flow, dead space

### Infusion Pumps (FRN, MEB)
- Flow rate accuracy: IEC 60601-2-24 (infusion pump particular standard)
- Alarm testing: IEC 60601-1-8, IEC 60601-2-24
- Occlusion detection: Pressure, response time
- Bolus accuracy: Volume delivered vs. programmed
- Electrical safety: IEC 60601-1, IEC 60601-1-2 (EMC)
- Software: IEC 62304 (all infusion pumps contain software)
- Cybersecurity: FDA cybersecurity guidance (network-connected pumps)
- Human factors: IEC 62366-1 (critical — programming errors are a major hazard)
- Biocompatibility: ISO 10993-1, -5, -10 (fluid path materials)
- Shelf life: ASTM F1980 (disposable sets)

### Electrical / Powered Devices (General)
- Electrical safety: IEC 60601-1:2005+A1:2012+A2:2020
- EMC: IEC 60601-1-2:2014+A1:2020
- Wireless: Per applicable standard (e.g., IEEE 802.11, Bluetooth SIG)
- Software: IEC 62304 (if contains software)
- Essential performance: Per applicable IEC 60601-2-* particular standard
- Mechanical: Drop, impact, vibration per IEC 60601-1
- Thermal: Surface temperature limits per IEC 60601-1
- Home use: IEC 60601-1-11 (if intended for home environment)
- Emergency transport: IEC 60601-1-12 (if for EMS/transport use)
- Alarms: IEC 60601-1-8 (if device has alarm functions)

## Cross-Cutting Testing Categories

### Human Factors / Usability (applies across many device types)
- Use-related risk analysis (uFMEA): Per IEC 62366-1:2015
- Formative usability studies: Iterative design evaluation
- Summative (validation) usability study: With representative users in simulated use environment
- **When required:** FDA increasingly expects HF/usability for devices with complex user interfaces, safety-critical user tasks, or home use

### Software V&V (applies to any software-containing device)
- Software documentation level determination: Basic or Enhanced
- Software risk analysis (as part of hazard analysis)
- V&V per IEC 62304:2006+A1:2015 software lifecycle
- Unit, integration, and system testing
- Cybersecurity testing (if connected)
- **Note:** Software documentation level determines depth of required V&V evidence

### GLP Requirements
- Tests intended to support safety (biocompatibility, sterilization validation) generally must be conducted under GLP (21 CFR 58)
- Performance/engineering tests do not require GLP but should follow documented protocols
- Clinical studies require IRB approval and compliance with 21 CFR 812 (IDE regulations)

## Timeline Estimates

| Test Category | Typical Duration | Dependencies |
|--------------|-----------------|-------------|
| Biocompatibility | 8-16 weeks | Final materials |
| Mechanical/Performance | 4-12 weeks | Design freeze |
| Sterilization validation | 6-12 weeks | Final packaging |
| Shelf life (accelerated) | 4-8 weeks | Final packaging |
| Software V&V | 4-8 weeks | Design freeze |
| Clinical study | 6-24 months | IRB, protocol |
