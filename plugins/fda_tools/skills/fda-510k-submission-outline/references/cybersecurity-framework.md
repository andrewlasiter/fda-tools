# Cybersecurity Documentation Framework

## Statutory Basis — Section 524B of FD&C Act

Section 524B of the Federal Food, Drug, and Cosmetic Act (21 U.S.C. 360n-2), enacted as part of the Consolidated Appropriations Act, 2023 (signed December 29, 2022), established **mandatory cybersecurity requirements** for medical devices. Effective **March 29, 2023** (90 days after enactment).

### The 3 Core Statutory Requirements

Section 524B requires that premarket submissions for "cyber devices" include:
1. **A plan to monitor, identify, and address** postmarket cybersecurity vulnerabilities and exploits
2. **A plan for coordinated vulnerability disclosure** — processes for receiving and addressing cybersecurity vulnerability information
3. **A Software Bill of Materials (SBOM)** — including commercial, open-source, and off-the-shelf components

Additionally, Section 524B includes an enabling provision allowing FDA to establish further requirements through regulation.

### What Is a "Cyber Device"?

Under Section 524B, a "cyber device" is a device that:
- Includes software validated, installed, or authorized by the sponsor
- Has the ability to connect to the internet
- Contains any technological characteristics that could be vulnerable to cybersecurity threats

### RTA Impact

FDA **will Refuse to Accept (RTA)** premarket submissions for cyber devices that lack cybersecurity documentation. This is a statutory requirement, not merely a guidance recommendation.

## When Cybersecurity Documentation is Required

### Statutory Requirement (Section 524B) vs. Guidance Recommendation

| Condition | Basis | Consequence if Missing |
|-----------|-------|----------------------|
| Device connects to internet AND includes software | Section 524B (statutory) | RTA — submission will be refused |
| Device has any connectivity (Bluetooth, WiFi, USB, network) | FDA guidance (recommended) | May receive AI letter; strong expectation |
| Device exchanges data with other systems | FDA guidance (recommended) | Expected for thorough review |
| SaMD / software-only device | Both statutory and guidance | RTA for internet-connected SaMD |

### Trigger Conditions
A cybersecurity section is required (per statute and/or guidance) if the device:
- Contains software or firmware
- Has wireless connectivity (Bluetooth, WiFi, cellular, RF)
- Connects to a network (hospital, cloud, internet)
- Exchanges data with other devices or systems
- Has USB or other data ports
- Is a Software as a Medical Device (SaMD)

### Auto-Detection from Product Code
Product code families likely requiring cybersecurity:
- Software/SaMD codes: QAS, QBJ, QDK, QEH, QFP, QMT, QPC, QPZ
- Connected/wireless device codes: Any with "wireless", "connected", "software" in classification
- Implantable with telemetry: Pacemakers, neurostimulators, pumps

## eSTAR Cybersecurity Section Content

### Required Elements

1. **Threat Model**
   - System architecture diagram
   - Data flow diagram (DFD)
   - Attack surface analysis
   - Threat identification (STRIDE or equivalent)
   - Risk scoring (CVSS or equivalent)

2. **Software Bill of Materials (SBOM)**
   - Format: SPDX or CycloneDX
   - All third-party components listed
   - Version numbers for each component
   - Known vulnerability status (CVE check)

3. **Security Controls**
   - Authentication and authorization
   - Encryption (data at rest and in transit)
   - Software integrity verification
   - Audit logging
   - Secure update mechanism

4. **Vulnerability Management**
   - Coordinated vulnerability disclosure policy
   - Patch/update plan and timeline
   - End-of-support / end-of-life plan
   - Customer notification procedures

5. **Security Testing**
   - Penetration testing scope and results
   - Fuzz testing results
   - Static and dynamic code analysis
   - Third-party component vulnerability scan

## Template Structure

### Threat Model Template
```markdown
## Threat Model

### System Architecture
[TODO: Company-specific — insert system architecture diagram]

### Data Flow
| Data | Source | Destination | Transport | Encryption | Sensitivity |
|------|--------|------------|-----------|-----------|-------------|
| Patient data | Sensor | Mobile app | BLE | AES-128 | PHI |
| Device config | Cloud | Device | HTTPS/TLS 1.3 | Yes | Moderate |

### Attack Surfaces
| Surface | Description | Mitigations |
|---------|-----------|-------------|
| Wireless (BLE) | Bluetooth Low Energy data channel | Pairing, encryption |
| Cloud API | REST API for data sync | OAuth 2.0, TLS, rate limiting |
| USB | Configuration port | Physical access control |

### Threats (STRIDE Analysis)
| Threat | Category | Risk | Mitigation | Residual Risk |
|--------|----------|------|-----------|---------------|
| Data interception | Information Disclosure | High | BLE encryption | Low |
| Firmware tampering | Tampering | High | Code signing | Low |
| DoS via BLE | Denial of Service | Medium | Connection throttling | Low |
```

### SBOM Template
```markdown
## Software Bill of Materials

**Format:** CycloneDX 1.5
**Generated:** {date}
**Tool:** [TODO: Company-specific — SBOM generation tool]

### Components
| Component | Version | License | Supplier | CVE Status |
|-----------|---------|---------|----------|-----------|
| [TODO: List all third-party components] | | | | |

### Known Vulnerabilities
| CVE | Component | Severity | Status | Mitigation |
|-----|-----------|---------|--------|-----------|
| [TODO: Run vulnerability scan] | | | | |
```

### Patch Plan Template
```markdown
## Vulnerability Management Plan

### Coordinated Disclosure
- Contact: [TODO: Company-specific — security contact email]
- Response timeline: Acknowledge within 48 hours
- Fix timeline: Critical within 30 days, High within 90 days

### Update Mechanism
- Method: [TODO: OTA / manual / service visit]
- Validation: [TODO: Code signing, integrity check]
- Rollback: [TODO: Ability to revert to previous version]

### End of Support
- Planned support duration: [TODO: years]
- End-of-life notification: [TODO: advance notice period]
- Post-EOL risk mitigation: [TODO: plan]
```

## Tier 1 vs. Tier 2 Devices

The FDA cybersecurity guidance distinguishes two tiers based on cybersecurity risk:

| Tier | Criteria | Documentation Level |
|------|----------|-------------------|
| **Tier 1 (Higher)** | Device can connect to internet/network, AND could cause patient harm if compromised | Full cybersecurity documentation required |
| **Tier 2 (Standard)** | Device not in Tier 1 but still a cyber device | Documentation required but may be scaled to risk |

**Tier 1 examples:** Infusion pumps with network connectivity, implantable devices with wireless telemetry, cloud-connected SaMD with diagnostic claims

**Tier 2 examples:** Non-connected software tools, devices with only local USB connectivity for configuration

## Premarket vs. Postmarket Obligations Under 524B

### Premarket
- Threat model and cybersecurity risk assessment
- SBOM (all components, versions, vulnerabilities)
- Security architecture and controls documentation
- Vulnerability management/patch plan
- Evidence of security testing

### Postmarket
- Monitor and address known vulnerabilities in a timely manner
- Maintain coordinated vulnerability disclosure process
- Provide security patches/updates throughout device lifecycle
- Report cybersecurity vulnerabilities per MDR requirements (if they constitute a safety issue)
- Maintain SBOM accuracy as components are updated

## Applicable Standards

| Standard | Title | When Required | FDA Recognition Status |
|----------|-------|--------------|----------------------|
| AAMI TIR57:2016/(R)2023 | Cybersecurity risk management for medical devices | All software devices | Recognized |
| IEC 81001-5-1:2021 | Health software — security | All health software | Recognized |
| IEC 62443-4-1:2018 | Security for industrial automation — secure product development lifecycle | Network-connected devices | Recognized |
| NIST Cybersecurity Framework 2.0 | Cybersecurity risk management framework | Reference framework | Referenced in guidance |
| NIST SP 800-171 | Protecting CUI | Government use devices | Not formally recognized; referenced |
| UL 2900-1 | Software cybersecurity for network-connectable products | Voluntary | Recognized |
| UL 2900-2-1 | Cybersecurity for network-connectable healthcare devices | Healthcare-specific | Recognized |
| OWASP Top 10 | Web application security risks | Devices with web interfaces | Referenced in guidance |
| OWASP Medical Device Security | Medical device specific security guidance | All cyber devices | Referenced |

Note: Check FDA's [recognized consensus standards database](https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfStandards/search.cfm) for current recognition status and versions.
