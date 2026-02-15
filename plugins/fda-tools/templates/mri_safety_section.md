# Section 19: MRI Safety

## 19.1 MRI Safety Classification

The {{device_name}} ({{product_code}}) is classified as **{{mri_classification}}** in accordance with FDA guidance "Establishing Safety and Compatibility of Passive Implants in the Magnetic Resonance (MR) Environment" (August 2021) and ASTM F2503-20 "Standard Practice for Marking Medical Devices and Other Items for Safety in the Magnetic Resonance Environment."

**Classification Definition:**

{{#if mri_classification == "MR Conditional"}}
The device has been demonstrated to pose no known hazards in a specified MR environment with specified conditions of use. Patients with this device can be safely scanned in an MR system meeting the conditions specified in Section 19.3.

**MR Conditional Status:** Safe for MRI under the following conditions:
- Static magnetic field strength: ≤{{max_field_strength}} Tesla
- Maximum spatial gradient: ≤{{max_gradient}} T/m
- Maximum whole-body-averaged specific absorption rate (SAR): ≤{{max_sar}} W/kg
- MR scanning mode: Normal Operating Mode (per IEC 60601-2-33)
- Maximum continuous scan duration: {{max_scan_duration}} minutes

{{else if mri_classification == "MR Safe"}}
The device poses no known hazards in all MR environments. The device is non-conducting, non-metallic, and non-magnetic.

**Material Composition:** {{material_list}}

The device contains no metallic components and does not produce image artifacts or RF heating in the MR environment. Patients with this device can be safely scanned at any field strength without restrictions.

{{else if mri_classification == "MR Unsafe"}}
⚠️ **WARNING: The device is MR UNSAFE and poses unacceptable risk in all MR environments.**

The device contains ferromagnetic materials that are subject to significant displacement forces and/or torque in the magnetic field. **Patients with this device must NOT undergo MRI scanning under any circumstances.**

{{endif}}

## 19.2 ASTM F2182 Testing Summary

MRI safety testing was conducted in accordance with the following consensus standards:

- **ASTM F2182-19e2:** Standard Test Method for Measurement of Radio Frequency Induced Heating Near Passive Implants During Magnetic Resonance Imaging
- **ASTM F2052-21:** Standard Test Method for Measurement of Magnetically Induced Displacement Force on Medical Devices in the Magnetic Resonance Environment
- **ASTM F2119-07(2013):** Standard Test Method for Evaluation of MR Image Artifacts from Passive Implants
- **ASTM F2213-17:** Standard Test Method for Measurement of Magnetically Induced Torque on Medical Devices in the Magnetic Resonance Environment

### 19.2.1 RF-Induced Heating (ASTM F2182)

**Test Configuration:**
- **MRI Scanner:** {{scanner_manufacturer}} {{scanner_model}}
- **Field Strength:** {{field_strength}} Tesla
- **RF Transmit Coil:** {{coil_type}}
- **Phantom:** ASTM {{phantom_type}} (conductivity: {{conductivity}} S/m, permittivity: {{permittivity}})
- **Test Duration:** {{test_duration}} minutes continuous RF exposure
- **Whole-Body-Averaged SAR:** {{sar_level}} W/kg

**Temperature Measurement:**
- **Instrumentation:** {{temperature_probe_manufacturer}} fiber optic temperature probes (model {{probe_model}})
- **Probe Locations:** {{probe_locations}}
- **Baseline Temperature:** {{baseline_temp}}°C
- **Ambient Temperature:** {{ambient_temp}}°C

**Results:**

| Probe Location | Peak Temperature (°C) | Temperature Rise (ΔT, °C) | Time to Peak (min) |
|----------------|------------------------|---------------------------|---------------------|
| {{location_1}} | {{peak_temp_1}} | {{delta_t_1}} | {{time_to_peak_1}} |
| {{location_2}} | {{peak_temp_2}} | {{delta_t_2}} | {{time_to_peak_2}} |
| {{location_3}} | {{peak_temp_3}} | {{delta_t_3}} | {{time_to_peak_3}} |

**Maximum Temperature Rise:** ΔT = {{max_delta_t}}°C

**Acceptance Criteria:** Temperature rise ≤2.0°C for MR Conditional classification

**Conclusion:** The {{device_name}} produced a maximum temperature rise of {{max_delta_t}}°C under worst-case RF exposure conditions at {{field_strength}}T. This result {{#if max_delta_t <= 2.0}}meets{{else}}DOES NOT MEET{{endif}} the acceptance criteria for MR Conditional classification.

### 19.2.2 Magnetically Induced Displacement Force (ASTM F2052)

**Test Configuration:**
- **MRI Scanner:** {{scanner_manufacturer}} {{scanner_model}}
- **Field Strength:** {{field_strength}} Tesla
- **Spatial Gradient:** {{spatial_gradient}} T/m (measured at {{gradient_location}})
- **Test Method:** {{test_method_displacement}} (deflection angle or force transducer)

**Results:**

| Device Component | Deflection Angle (°) | Displacement Force (N) | Device Weight (N) | Force/Weight Ratio |
|------------------|----------------------|------------------------|-------------------|--------------------|
| {{component_1}} | {{angle_1}} | {{force_1}} | {{weight_1}} | {{ratio_1}} |
| {{component_2}} | {{angle_2}} | {{force_2}} | {{weight_2}} | {{ratio_2}} |

**Maximum Displacement Force:** {{max_force}} N

**Acceptance Criteria:**
- Translational force < device weight (force/weight ratio < 1.0)
- Deflection angle < 45° considered acceptable for most implants

**Conclusion:** The {{device_name}} exhibited a maximum displacement force of {{max_force}} N (force/weight ratio: {{max_ratio}}), which {{#if max_ratio < 1.0}}is below{{else}}EXCEEDS{{endif}} the device weight. The deflection angle of {{max_angle}}° indicates {{#if max_angle < 45}}acceptable{{else}}significant{{endif}} translational movement.

### 19.2.3 Magnetically Induced Torque (ASTM F2213)

**Test Configuration:**
- **MRI Scanner:** {{scanner_manufacturer}} {{scanner_model}}
- **Field Strength:** {{field_strength}} Tesla
- **Test Method:** {{torque_method}} (torsion balance or torque sensor)
- **Device Orientation:** Worst-case orientation ({{orientation_description}})

**Results:**

| Device Component | Torque (N·m) | Retention Force (N·m) | Safety Margin |
|------------------|--------------|------------------------|---------------|
| {{component_1}} | {{torque_1}} | {{retention_1}} | {{margin_1}}× |
| {{component_2}} | {{torque_2}} | {{retention_2}} | {{margin_2}}× |

**Maximum Torque:** {{max_torque}} N·m

**Acceptance Criteria:** Torque < retention forces of fixation (for orthopedic implants)

**Conclusion:** The {{device_name}} exhibited a maximum torque of {{max_torque}} N·m, which {{#if torque_acceptable}}is below{{else}}EXCEEDS{{endif}} the retention forces. The safety margin of {{min_margin}}× indicates {{#if min_margin >= 2.0}}acceptable{{else}}marginal{{endif}} rotational stability.

### 19.2.4 Image Artifact Characterization (ASTM F2119)

**Test Configuration:**
- **MRI Scanner:** {{scanner_manufacturer}} {{scanner_model}}
- **Field Strength:** {{field_strength}} Tesla
- **Phantom:** {{artifact_phantom}} (agar or saline gel)
- **Pulse Sequences Tested:**
  - T1-weighted spin echo (TR/TE: {{t1_tr}}/{{t1_te}} ms)
  - T2-weighted spin echo (TR/TE: {{t2_tr}}/{{t2_te}} ms)
  - Gradient echo (GRE) (TR/TE: {{gre_tr}}/{{gre_te}} ms, flip angle: {{gre_flip}}°)

**Results:**

| Pulse Sequence | Artifact Extent (mm) | Artifact Type | Impact on Diagnostic Imaging |
|----------------|----------------------|---------------|------------------------------|
| T1-weighted SE | {{t1_artifact}} | {{t1_type}} | {{t1_impact}} |
| T2-weighted SE | {{t2_artifact}} | {{t2_type}} | {{t2_impact}} |
| GRE | {{gre_artifact}} | {{gre_type}} | {{gre_impact}} |

**Maximum Artifact Extent:** {{max_artifact}} mm from implant center

**Artifact Description:** The device produces signal void (hypointense artifact) extending {{max_artifact}} mm from the implant surface, with mild susceptibility artifact on gradient echo sequences. The artifact does not significantly impair diagnostic imaging of {{anatomical_region}} structures more than {{diagnostic_distance}} mm from the implant.

**Conclusion:** Image artifact is consistent with metallic implants of similar size and composition. Radiologists should be aware of artifact extent when evaluating adjacent anatomical structures.

## 19.3 MR Conditional Labeling

{{#if mri_classification == "MR Conditional"}}

The {{device_name}} is **MR Conditional** and may be scanned safely under the following conditions:

### 19.3.1 Static Magnetic Field

- **Maximum Static Field Strength:** {{max_field_strength}} Tesla
- **Field Homogeneity:** Not specified (standard clinical MRI)

**Rationale:** Testing was conducted at {{test_field_strength}}T. The device demonstrated acceptable RF heating (ΔT ≤ {{max_delta_t}}°C) and displacement force ({{max_force}} N) at this field strength.

### 19.3.2 Spatial Gradient

- **Maximum Spatial Gradient:** {{max_gradient}} T/m or less

**Rationale:** Displacement force testing was conducted at {{test_gradient}} T/m spatial gradient, representing worst-case clinical MRI scanner configuration.

### 19.3.3 Radiofrequency (RF) Energy

- **Maximum Whole-Body-Averaged SAR:** {{max_sar}} W/kg for {{max_scan_duration}} minutes
- **MR Scanning Mode:** Normal Operating Mode only (per IEC 60601-2-33)
- **Operating Mode Restrictions:** First Level Controlled Operating Mode and higher SAR modes are contraindicated

**Rationale:** RF heating testing at {{sar_level}} W/kg for {{test_duration}} minutes resulted in maximum temperature rise of {{max_delta_t}}°C, below the 2.0°C safety threshold.

### 19.3.4 Scan Duration

- **Maximum Continuous Scan Duration:** {{max_scan_duration}} minutes
- **Minimum Wait Time Between Scans:** {{wait_time}} minutes (for temperature equilibration)

**Rationale:** Temperature rise plateaus at {{time_to_peak}} minutes. Maximum scan duration provides safety margin for thermal equilibration.

### 19.3.5 Additional Restrictions

{{#if additional_restrictions}}
- {{restriction_1}}
- {{restriction_2}}
- {{restriction_3}}
{{else}}
No additional restrictions beyond those specified above.
{{endif}}

{{endif}}

## 19.4 MRI Safety Labeling

The following MRI safety information is included in the device Instructions for Use (IFU Section 7.2):

---

**MRI SAFETY INFORMATION**

{{#if mri_classification == "MR Conditional"}}

**MR Conditional**

The {{device_name}} is MR Conditional. Patients with this device can be safely scanned in an MRI system meeting the following conditions:

- **Static Magnetic Field:** ≤{{max_field_strength}} Tesla
- **Maximum Spatial Gradient:** ≤{{max_gradient}} T/m
- **Maximum SAR:** ≤{{max_sar}} W/kg (whole-body-averaged)
- **Scan Duration:** ≤{{max_scan_duration}} minutes continuous scanning
- **MR Scanning Mode:** Normal Operating Mode only

**Patient Instructions:**
1. Inform the MRI technologist that you have a {{device_name}} implant
2. Provide your implant identification card showing the device model and serial number
3. Ensure the MRI scanner is set to Normal Operating Mode (SAR ≤{{max_sar}} W/kg)
4. Scan duration should not exceed {{max_scan_duration}} minutes

**Warnings:**
- Do NOT undergo MRI at field strengths >{{max_field_strength}}T
- Do NOT undergo MRI in First Level Controlled Operating Mode or higher SAR modes
- Wait at least {{wait_time}} minutes between consecutive scans

**Image Artifact:**
The device may produce an image artifact extending up to {{max_artifact}} mm from the implant. This may affect the diagnostic quality of MR images of structures immediately adjacent to the implant.

{{else if mri_classification == "MR Safe"}}

**MR Safe**

The {{device_name}} is MR Safe. Patients with this device can be safely scanned at any field strength without restrictions. The device contains no metallic components and poses no known hazards in all MR environments.

{{else if mri_classification == "MR Unsafe"}}

**⚠️ MR UNSAFE - DO NOT SCAN ⚠️**

The {{device_name}} is MR UNSAFE. Patients with this device must NOT undergo MRI scanning under any circumstances. The device contains ferromagnetic materials that pose serious risk of injury or death in the MR environment.

**WARNING TO PATIENTS:**
- NEVER enter an MRI room or MRI suite with this device
- Inform all healthcare providers that you have an MR UNSAFE implant
- Carry your implant identification card at all times
- Alternative imaging modalities (CT, ultrasound, X-ray) should be used

{{endif}}

---

## 19.5 Supporting Documentation

The following MRI safety test reports are provided as supporting documentation:

1. **RF-Induced Heating Test Report** (ASTM F2182-19e2)
   - Test lab: {{test_lab_name}}
   - Report number: {{report_number_rf}}
   - Test date: {{test_date_rf}}
   - Report pages: {{page_count_rf}}

2. **Displacement Force Test Report** (ASTM F2052-21)
   - Test lab: {{test_lab_name}}
   - Report number: {{report_number_displacement}}
   - Test date: {{test_date_displacement}}
   - Report pages: {{page_count_displacement}}

3. **Image Artifact Test Report** (ASTM F2119-07)
   - Test lab: {{test_lab_name}}
   - Report number: {{report_number_artifact}}
   - Test date: {{test_date_artifact}}
   - Report pages: {{page_count_artifact}}

{{#if torque_tested}}
4. **Torque Test Report** (ASTM F2213-17)
   - Test lab: {{test_lab_name}}
   - Report number: {{report_number_torque}}
   - Test date: {{test_date_torque}}
   - Report pages: {{page_count_torque}}
{{endif}}

**Test Lab Accreditation:**
{{test_lab_name}} is {{#if lab_accredited}}accredited to ISO/IEC 17025:2017 for MRI safety testing (accreditation number: {{accreditation_number}}){{else}}[SPECIFY ACCREDITATION STATUS]{{endif}}.

**Test Article Traceability:**
- Device model tested: {{device_model_tested}}
- Serial number: {{serial_number_tested}}
- Manufacturing lot: {{lot_number_tested}}
- Test article representativeness: {{representativeness_statement}}

## 19.6 Comparison to Predicate Devices

{{#if predicates_available}}

The following table compares the MRI safety characteristics of the subject device to accepted predicate devices:

| Characteristic | Subject Device | Predicate 1 ({{predicate_1_knumber}}) | Predicate 2 ({{predicate_2_knumber}}) |
|----------------|----------------|---------------------------------------|---------------------------------------|
| **MRI Classification** | {{subject_mri_class}} | {{pred1_mri_class}} | {{pred2_mri_class}} |
| **Maximum Field Strength** | {{subject_field}} | {{pred1_field}} | {{pred2_field}} |
| **Maximum SAR** | {{subject_sar}} | {{pred1_sar}} | {{pred2_sar}} |
| **RF Heating (ΔT)** | {{subject_heating}} | {{pred1_heating}} | {{pred2_heating}} |
| **Displacement Force** | {{subject_force}} | {{pred1_force}} | {{pred2_force}} |
| **Image Artifact (mm)** | {{subject_artifact}} | {{pred1_artifact}} | {{pred2_artifact}} |
| **Primary Material** | {{subject_material}} | {{pred1_material}} | {{pred2_material}} |

**Comparison Summary:**

The subject device demonstrates {{#if mri_equivalent}}equivalent{{else}}comparable{{endif}} MRI safety performance to the predicate devices. {{comparison_narrative}}

{{else}}

[No predicate MRI safety data available for comparison. Subject device MRI safety established through ASTM F2182/F2052/F2119 testing as documented above.]

{{endif}}

## 19.7 Risk Analysis

MRI-related hazards were evaluated in the device risk analysis (ISO 14971) with the following risk controls:

| Hazard | Risk Before Controls | Risk Controls | Residual Risk |
|--------|----------------------|---------------|---------------|
| RF-induced heating causing tissue damage | {{risk_heating_before}} | ASTM F2182 testing; SAR limits; scan duration limits; MR Conditional labeling | {{risk_heating_after}} |
| Displacement force causing device migration | {{risk_displacement_before}} | ASTM F2052 testing; fixation design; MR Conditional labeling | {{risk_displacement_after}} |
| Torque causing device rotation | {{risk_torque_before}} | ASTM F2213 testing; retention features; MR Conditional labeling | {{risk_torque_after}} |
| Image artifact impairing diagnosis | {{risk_artifact_before}} | ASTM F2119 testing; radiologist training; artifact extent labeling | {{risk_artifact_after}} |

All residual MRI-related risks are {{#if risks_acceptable}}acceptable{{else}}[SPECIFY ADDITIONAL RISK CONTROLS REQUIRED]{{endif}} per ISO 14971 criteria.

---

**End of Section 19: MRI Safety**

---

## Template Variable Glossary

**Device Information:**
- `{{device_name}}` - Full device trade name
- `{{product_code}}` - FDA product code
- `{{mri_classification}}` - MR Safe, MR Conditional, or MR Unsafe
- `{{material_list}}` - Comma-separated list of device materials

**MR Conditional Parameters:**
- `{{max_field_strength}}` - Maximum safe field strength (e.g., "3.0")
- `{{max_gradient}}` - Maximum spatial gradient (e.g., "40")
- `{{max_sar}}` - Maximum SAR in W/kg (e.g., "2.0")
- `{{max_scan_duration}}` - Maximum continuous scan time in minutes (e.g., "15")
- `{{wait_time}}` - Minimum wait between scans in minutes (e.g., "10")

**RF Heating Test Results:**
- `{{scanner_manufacturer}}` - MRI scanner manufacturer (e.g., "Siemens")
- `{{scanner_model}}` - MRI scanner model (e.g., "MAGNETOM Prisma")
- `{{field_strength}}` - Test field strength (e.g., "3.0")
- `{{max_delta_t}}` - Maximum temperature rise in °C (e.g., "1.8")
- `{{sar_level}}` - Test SAR level in W/kg (e.g., "2.0")
- `{{test_duration}}` - Test duration in minutes (e.g., "15")

**Displacement Force Test Results:**
- `{{max_force}}` - Maximum displacement force in Newtons (e.g., "0.15")
- `{{max_ratio}}` - Maximum force/weight ratio (e.g., "0.75")
- `{{max_angle}}` - Maximum deflection angle in degrees (e.g., "35")

**Image Artifact Results:**
- `{{max_artifact}}` - Maximum artifact extent in mm (e.g., "45")
- `{{diagnostic_distance}}` - Minimum distance for unimpaired imaging in mm (e.g., "50")

**Test Lab Information:**
- `{{test_lab_name}}` - Name of testing laboratory
- `{{report_number_rf}}` - RF heating test report number
- `{{test_date_rf}}` - RF heating test date

**Predicate Comparison:**
- `{{predicate_1_knumber}}` - First predicate K-number (e.g., "K123456")
- `{{pred1_mri_class}}` - First predicate MRI classification

---

**INSTRUCTIONS FOR USE:**

1. **Replace all `{{placeholders}}`** with actual test data from ASTM F2182/F2052/F2119 test reports
2. **Delete conditional blocks** (`{{#if ...}}...{{endif}}`) that don't apply to your device
3. **Remove template variable glossary** section before finalizing document
4. **Verify all numerical values** against original test reports (temperature, force, artifact extent)
5. **Ensure consistency** between Section 19 and IFU Section 7.2 (MRI safety labeling)
6. **Cross-reference** with predicate device 510(k) summaries for comparison table

**CRITICAL PLACEHOLDERS REQUIRING EXTERNAL TEST DATA:**
- All temperature rise values ({{max_delta_t}}, {{delta_t_1}}, etc.) - from ASTM F2182 test report
- All displacement force values ({{max_force}}, {{force_1}}, etc.) - from ASTM F2052 test report
- All artifact extent values ({{max_artifact}}, {{t1_artifact}}, etc.) - from ASTM F2119 test report
- Test lab information ({{test_lab_name}}, {{report_number_rf}}, etc.) - from test reports
