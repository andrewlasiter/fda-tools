# 510(k) Section Detection — 3-Tier System

Centralized patterns for detecting and extracting sections from FDA 510(k) PDF documents. Section names vary significantly across years, sponsors, device types, and OCR quality. This file is the single canonical source — all commands reference it.

## Escalation Protocol

Apply tiers in order. Stop at the first tier that produces a confident match.

```
Tier 1: Regex Patterns (deterministic, fast)
  ↓ no match
Tier 2: OCR-Tolerant Matching (apply substitution table, retry regex)
  ↓ no match
Tier 3: LLM Semantic Classification (content signals + non-standard headings)
```

**Decision rules:**
- Tier 1 match → use it (highest confidence)
- Tier 2 match after ≤2 character substitutions → use it (high confidence, note OCR correction)
- Tier 3 match with 2+ classification signals → use it (moderate confidence, note semantic detection)
- No match at any tier → mark section as "Not detected" and note in output

---

## Tier 1: Regex Patterns (Deterministic)

Case-insensitive regex patterns. Apply to each line or heading candidate.

### Predicate / SE Sections (high value — weight 3x)

```regex
(?i)(?:substantial\s+equivalen|predicate\s+(?:device|comparison|analysis|identification)|comparison\s+(?:of|to|with)\s+predicate|SE\s+(?:comparison|discussion|summary)|technological\s+characteristics|comparison\s+(?:table|chart|matrix)|similarities\s+and\s+differences|comparison\s+of\s+(?:the\s+)?(?:features|technological|device))
```

**Note:** This section often appears as a TABLE. If header found but minimal prose, search for table structures (`|` delimiters or aligned columns) within the next 100 lines.

### Indications for Use

```regex
(?i)(?:indications?\s+for\s+use|intended\s+use|ifu\b|indication\s+statement|device\s+indications?|clinical\s+indications?|approved\s+use)
```

**Semantic fallback (Tier 3):** patient population + anatomical site + clinical condition within 3 sentences

### Device Description

```regex
(?i)(?:device\s+description|product\s+description|description\s+of\s+(?:the\s+)?device|device\s+characteristics|physical\s+description|device\s+composition|device\s+components|system\s+(?:description|overview)|principle\s+of\s+operation)
```

### Non-Clinical / Performance Testing

```regex
(?i)(?:non[- ]?clinical\s+(?:testing|studies|data|performance)|performance\s+(?:testing|data|evaluation|characteristics|bench)|bench\s+(?:testing|top\s+testing)|in\s+vitro\s+(?:testing|studies)|mechanical\s+(?:testing|characterization)|laboratory\s+testing|verification\s+(?:testing|studies)|validation\s+testing|analytical\s+performance|test(?:ing)?\s+(?:summary|results|data))
```

**Semantic fallback (Tier 3):** 3+ test standard citations (ASTM, ISO, IEC, AAMI, ANSI) within 200 words

### Biocompatibility

```regex
(?i)(?:biocompatib(?:ility|le)?|biological?\s+(?:evaluation|testing|safety|assessment)|iso\s*10993|cytotoxicity|sensitization\s+test|irritation\s+test|systemic\s+toxicity|genotoxicity|implantation\s+(?:testing|studies|study)|hemocompatibility|material\s+characterization|extractables?\s+and\s+leachables?)
```

**Note:** Any mention of ISO 10993-X (where X is a part number) indicates biocompatibility. Key parts:
- ISO 10993-1: Evaluation framework
- ISO 10993-5: Cytotoxicity (in vitro)
- ISO 10993-10: Sensitization
- ISO 10993-11: Systemic toxicity
- ISO 10993-18: Chemical characterization
- ISO 10993-23: Irritation tests

### Sterilization

```regex
(?i)(?:steriliz(?:ation|ed|ing)|sterility\s+(?:assurance|testing|validation)|ethylene\s+oxide|eto\b|e\.?o\.?\s+(?:steriliz|residual)|gamma\s+(?:radiation|irradiation|steriliz)|electron\s+beam|e[- ]?beam|steam\s+steriliz|autoclave|iso\s*11135|iso\s*11137|sal\s+10|sterility\s+assurance\s+level)
```

### Clinical Testing / Clinical Data

```regex
(?i)(?:clinical\s+(?:testing|trial|study|studies|data|evidence|information|evaluation|investigation|performance)|human\s+(?:subjects?|study|clinical)|patient\s+study|pivotal\s+(?:study|trial)|feasibility\s+study|post[- ]?market\s+(?:clinical\s+)?follow[- ]?up|pmcf|literature\s+(?:review|search|summary|based)|clinical\s+experience)
```

**Distinguish types:**
- Prospective clinical study (strongest): "prospective", "enrolled", "IDE", "multi-center"
- Retrospective: "retrospective", "chart review"
- Literature review: "literature", "published", "peer-reviewed"
- Clinical experience: "post-market", "complaint", "adverse event"

### Shelf Life / Stability

```regex
(?i)(?:shelf[- ]?life|stability\s+(?:testing|studies|data)|accelerated\s+aging|real[- ]?time\s+aging|package\s+(?:integrity|testing|validation|aging)|astm\s*f1980|expiration\s+dat(?:e|ing)|storage\s+condition)
```

### Software / Cybersecurity

```regex
(?i)(?:software\s+(?:description|validation|verification|documentation|testing|v&v|lifecycle|architecture|design|level\s+of\s+concern)|firmware|algorithm\s+(?:description|validation)|cybersecurity|iec\s*62304|sloc|soup\s+analysis|off[- ]?the[- ]?shelf\s+software|ots\s+software|mobile\s+(?:medical\s+)?app(?:lication)?|SBOM|threat\s+model)
```

### Electrical Safety & EMC

```regex
(?i)(?:electrical\s+safety|iec\s*60601|electromagnetic\s+(?:compatibility|interference|disturbance)|emc\b|emi\b|wireless\s+(?:coexistence|testing)|rf\s+(?:safety|testing|emissions?)|radiation\s+safety|battery\s+safety|iec\s*62133|ul\s*1642)
```

### Human Factors / Usability

```regex
(?i)(?:human\s+factors|usability\s+(?:testing|engineering|study|evaluation)|use[- ]?related\s+risk|iec\s*62366|formative\s+(?:evaluation|study)|summative\s+(?:evaluation|study|test)|simulated\s+use|use\s+error)
```

### Risk Management

```regex
(?i)(?:risk\s+(?:management|analysis|assessment|evaluation)|iso\s*14971|fmea|failure\s+mode|hazard\s+analysis|fault\s+tree|risk[- ]?benefit)
```

### Labeling

```regex
(?i)(?:label(?:ing)?\s+(?:requirements?|review)|instructions?\s+for\s+use|package\s+(?:insert|label)|iso\s*15223|udi|unique\s+device\s+identif|user\s+manual)
```

### Regulatory / Submission History

```regex
(?i)(?:regulatory\s+(?:history|status|classification|pathway)|510\s*\(\s*k\s*\)\s+(?:submission|clearance|number)|special\s+510\s*\(\s*k\s*\)|abbreviated\s+510\s*\(\s*k\s*\)|third[- ]?party\s+review|de\s+novo\s+(?:classification|pathway)|pre[- ]?market\s+(?:notification|approval)|pma\s+(?:submission|approval)|classification\s+name|product\s+code|regulation\s+number|advisory\s+committee|review\s+panel|clearance\s+date|decision\s+(?:date|summary)|predicate\s+history)
```

**Variations:**
- "Regulatory Pathway and Classification"
- "510(k) Submission Type"
- "Third-Party Review Status"
- "Historical 510(k) Submissions"
- "Regulatory Status"

### Reprocessing (for reusable devices)

```regex
(?i)(?:reprocessing\s+(?:instructions?|validation|procedures?)|cleaning\s+(?:validation|instructions?|procedures?)|disinfection\s+(?:validation|protocol)|validated\s+cleaning\s+cycle|reusable\s+device|multi[- ]?use\s+device|sterilization\s+cycle|cleaning\s+efficacy|residual\s+(?:contamination|soil)|worst[- ]?case\s+soil|protein\s+residue|microbial\s+burden|cleaning\s+agent|automated\s+(?:washer|disinfector)|manual\s+cleaning|ultrasonic\s+cleaning)
```

**Variations:**
- "Cleaning and Disinfection"
- "Validated Reprocessing Procedures"
- "Device Reuse Instructions"
- "Sterilization and Reprocessing"
- "Cleaning Validation Summary"

### Packaging (for sterile devices)

```regex
(?i)(?:packaging\s+(?:design|validation|materials|testing)|primary\s+packaging|secondary\s+packaging|protective\s+packaging|package\s+(?:seal\s+)?integrity|astm\s*(?:f88|f1929|f2096)|peel\s+(?:strength|testing|test)|transit\s+(?:simulation|testing)|ista\s+(?:1a|2a|3a)|distribution\s+simulation|package\s+seal|barrier\s+(?:properties|material)|sterile\s+barrier\s+system|tyvek|foil\s+pouch)
```

**Variations:**
- "Primary and Secondary Packaging"
- "Package Integrity Testing"
- "Sterile Barrier System"
- "Packaging Validation"
- "Transit and Distribution Testing"

### Materials (detailed characterization)

```regex
(?i)(?:materials?\s+(?:of\s+construction|characterization|composition|specification)|raw\s+materials?|material\s+(?:safety|biocompatibility)|chemical\s+composition|material\s+(?:properties|testing)|polymer\s+characterization|metal\s+alloys?|surface\s+(?:finish|treatment|coating)|material\s+identification|certificate\s+of\s+analysis|material\s+supplier|peek|titanium|cobalt[- ]?chrome|stainless\s+steel|nitinol|silicone|polyurethane|pvc|pet\s+(?:polymer)?|polycarbonate|collagen|gelatin)
```

**Variations:**
- "Materials of Construction and Composition"
- "Raw Material Specifications"
- "Material Characterization Report"
- "Chemical and Physical Properties"
- "Material Safety Assessment"

### Environmental / Transportation Testing

```regex
(?i)(?:environmental\s+(?:testing|conditioning|simulation)|temperature\s+(?:cycling|shock|range)|humidity\s+(?:testing|conditioning)|altitude\s+(?:testing|simulation)|vibration\s+(?:testing|test)|shock\s+(?:testing|test)|drop\s+(?:testing|test)|transit\s+simulation|ista\s+(?:testing|standard)|mil[- ]?std|shipping\s+(?:validation|testing)|storage\s+conditions?|temperature\s+range|operating\s+conditions?|environmental\s+limits)
```

**Variations:**
- "Environmental and Transportation Testing"
- "Storage and Shipping Validation"
- "Temperature and Humidity Limits"
- "Distribution Simulation Testing"
- "Environmental Conditioning"

### Mechanical Testing (device-type specific)

```regex
(?i)(?:mechanical\s+(?:testing|properties|characterization|performance)|tensile\s+(?:strength|testing|test)|compression\s+(?:strength|testing|test)|flexural\s+(?:strength|testing|modulus)|torsion(?:al)?\s+(?:strength|testing|test)|fatigue\s+(?:testing|life|cycles)|wear\s+(?:testing|resistance)|burst\s+(?:pressure|test)|leak\s+(?:testing|test)|pressure\s+(?:testing|test)|flow\s+(?:rate|testing)|force\s+(?:measurement|testing)|dimensional\s+(?:verification|tolerances)|structural\s+integrity|mechanical\s+durability)
```

**Variations:**
- "Mechanical and Structural Testing"
- "Strength and Durability Testing"
- "Mechanical Performance Characterization"
- "Physical Testing Summary"
- "Mechanical Properties"

### Functional Testing (device operation)

```regex
(?i)(?:functional\s+(?:testing|validation|performance|verification)|operational\s+(?:testing|qualification)|performance\s+verification|functional\s+performance|device\s+function(?:ality)?|operation(?:al)?\s+testing|user\s+function|clinical\s+function|functional\s+requirements?|performance\s+specification|acceptance\s+testing|product\s+performance\s+testing)
```

**Variations:**
- "Functional Performance Testing"
- "Operational Qualification"
- "Device Functionality Verification"
- "Performance Specifications"
- "Functional Requirements Testing"

### Accelerated Aging / Real-Time Aging

```regex
(?i)(?:accelerated\s+ag(?:e|ing)|real[- ]?time\s+ag(?:e|ing)|aging\s+(?:protocol|study|validation)|astm\s*f1980|shelf[- ]?life\s+(?:validation|study|testing)|expiration\s+dat(?:e|ing)|aging\s+factor|q10\s+(?:factor|value)|aging\s+(?:temperature|time)|aged\s+(?:samples?|units?)|end[- ]?of[- ]?life\s+testing|package\s+aging)
```

**Variations:**
- "Accelerated Aging Study"
- "Real-Time Aging Protocol"
- "Shelf Life Validation Summary"
- "Aging Study Results"
- "Package Integrity After Aging"

### Antimicrobial / Drug Efficacy (for drug-device combinations)

```regex
(?i)(?:antimicrobial\s+(?:efficacy|testing|effectiveness|activity)|zone\s+of\s+inhibition|mic|mbc|minimum\s+inhibitory\s+concentration|minimum\s+bactericidal\s+concentration|aatcc\s+100|iso\s*20743|jis\s*z\s*2801|log\s+reduction|bacteriostatic|bactericidal|drug\s+(?:release|elution|content|dosing|stability)|pharmaceutical\s+testing|active\s+(?:ingredient|pharmaceutical)|drug\s+product\s+(?:testing|characterization)|antimicrobial\s+agent)
```

**Variations:**
- "Antimicrobial Effectiveness Testing"
- "Drug Release Characterization"
- "Antimicrobial Activity Assessment"
- "Drug Content and Stability"
- "Pharmaceutical Testing Summary"

### Electromagnetic Compatibility (detailed EMC/EMI)

```regex
(?i)(?:electromagnetic\s+(?:compatibility|interference|emissions?|immunity|disturbance)|emc\s+(?:testing|test)|emi\s+(?:testing|test)|iec\s*60601[- ]?1[- ]?2|wireless\s+(?:coexistence|performance|connectivity)|rf\s+(?:emissions?|immunity|testing|test|performance)|radiated\s+(?:emissions?|immunity)|conducted\s+(?:emissions?|immunity)|harmonic\s+(?:emissions?|current)|flicker|electrostatic\s+discharge|esd\s+(?:testing|test)|surge\s+(?:immunity|test)|burst\s+(?:immunity|test))
```

**Variations:**
- "Electromagnetic Compatibility Testing"
- "EMC/EMI Test Results"
- "Wireless Coexistence Validation"
- "RF Emissions and Immunity"
- "IEC 60601-1-2 Compliance"

### MRI Safety / Compatibility

```regex
(?i)(?:mri\s+(?:safety|compatibility|conditional|conditional\s+safe|safe|unsafe)|magnetic\s+resonance\s+(?:imaging|environment)|astm\s*f2503|astm\s*f2119|astm\s*f2182|magnetically\s+induced\s+(?:displacement|torque|force)|rf[- ]?induced\s+heating|image\s+artifact|gradient\s+field|static\s+(?:magnetic\s+)?field|3\s*[tT]|1\.5\s*[tT]|whole[- ]?body\s+sar|specific\s+absorption\s+rate)
```

**Variations:**
- "MRI Conditional Safety"
- "Magnetic Resonance Compatibility"
- "MRI Safety Assessment"
- "MRI Artifact Testing"
- "RF-Induced Heating"

### Animal Testing (pre-clinical)

```regex
(?i)(?:animal\s+(?:testing|study|studies|model|trial)|pre[- ]?clinical\s+(?:testing|study|studies|trial|evaluation)|in\s+vivo\s+(?:testing|study|studies|evaluation|performance)|ovine\s+(?:model|study)|porcine\s+(?:model|study)|canine\s+(?:model|study)|rodent\s+(?:model|study)|rabbit\s+(?:study|model)|cadaver\s+(?:study|testing)|animal\s+care\s+and\s+use\s+committee|iacuc|survival\s+study|acute\s+study|chronic\s+(?:implant|study)|histopathology|necropsy)
```

**Variations:**
- "Pre-Clinical Animal Studies"
- "In Vivo Testing Results"
- "Animal Model Evaluation"
- "Animal Study Summary"
- "Histopathology and Necropsy"

### Literature Review / Clinical Literature

```regex
(?i)(?:literature\s+(?:review|search|summary|analysis|evaluation|evidence)|published\s+(?:data|studies|literature|evidence)|peer[- ]?reviewed\s+(?:publications?|articles?|studies)|scientific\s+literature|clinical\s+literature|pubmed\s+search|systematic\s+review|meta[- ]?analysis|evidence[- ]?based|post[- ]?market\s+(?:data|literature|surveillance)|real[- ]?world\s+evidence|safety\s+and\s+effectiveness\s+literature)
```

**Variations:**
- "Literature-Based Evidence"
- "Published Clinical Data"
- "Systematic Literature Review"
- "Post-Market Literature Search"
- "Scientific Literature Analysis"

### Manufacturing / Quality System

```regex
(?i)(?:manufacturing\s+(?:process|site|description|location)|quality\s+(?:system|management\s+system)|iso\s*13485|fda\s+establishment|device\s+master\s+record|dmr|design\s+history\s+file|dhf|process\s+validation|process\s+controls?|manufacturing\s+controls?|facility\s+(?:description|location)|quality\s+assurance|good\s+manufacturing\s+practice|gmp\s+compliance)
```

**Variations:**
- "Manufacturing Process Description"
- "Quality System Compliance"
- "ISO 13485 Certification"
- "Manufacturing Site Location"
- "Process Validation Summary"

### Special 510(k) Requirements (for special pathway)

```regex
(?i)(?:special\s+510\s*\(\s*k\s*\)|design\s+controls?|risk\s+analysis\s+summary|declaration\s+of\s+conformity|doc\b|compliance\s+with\s+(?:recognized\s+)?standards?|consensus\s+standards?|guidance\s+document\s+compliance|special\s+controls?\s+compliance|design\s+changes?|device\s+modifications?|change\s+(?:description|rationale)|comparison\s+to\s+legally\s+marketed\s+device)
```

**Variations:**
- "Special 510(k) Declaration"
- "Design Control Summary"
- "Consensus Standards Compliance"
- "Device Modification Description"
- "Declaration of Conformity"

---

## Tier 2: OCR-Tolerant Matching

Apply when Tier 1 fails. Many 510(k) PDFs are scanned images with OCR artifacts.

### OCR Substitution Table

| OCR Error | Intended | Context |
|-----------|----------|---------|
| `1` | `I` or `l` | "1ndications" → "Indications"; "She1f" → "Shelf" |
| `0` | `O` | "Bi0compatibility" → "Biocompatibility" |
| `O` | `0` | In numbers: "1O993" → "10993" |
| `5` | `S` | "5terilization" → "Sterilization"; "5ubstantial" → "Substantial" |
| `$` | `S` | "$terilization" → "Sterilization" |
| `7` | `T` | "7esting" → "Testing" |
| `3` | `E` | "P3rformance" → "Performance" |
| `8` | `B` | "8iocompatibility" → "Biocompatibility" |
| `|` (pipe) | `l` or `I` | "|ndications" → "Indications" |
| `rn` | `m` | "Perforrnance" → "Performance" |
| ` ` (spurious space) | (remove) | "Ste rilization" → "Sterilization" |

### Canonical Headings to Match Against

After applying substitutions, attempt to match against these canonical headings:

1. Indications for Use
2. Device Description
3. Substantial Equivalence
4. Performance Testing
5. Biocompatibility
6. Sterilization
7. Clinical Data
8. Shelf Life
9. Software
10. Electrical Safety
11. Human Factors
12. Risk Management
13. Labeling

### Instructions

1. For short header-like lines (<80 characters), apply the substitution table
2. Allow at most 2 character substitutions per heading candidate
3. Handle split words: rejoin tokens where removing a space produces a dictionary word or a Tier 1 match (e.g., "Ste rilization" → "Sterilization")
4. Handle fused words: if two heading words are joined without a space, try inserting a space at plausible boundaries (e.g., "DeviceDescription" → "Device Description")
5. After corrections, retry the Tier 1 regex for that section
6. If the corrected text matches, report: `"Section detected via Tier 2 (OCR correction: '{original}' → '{corrected}')"`

### Calibration Examples

| OCR Text | Corrections Applied | Expected Match |
|----------|---------------------|----------------|
| `1ndications for Use` | `1→I` | Indications for Use |
| `Bi0compatibility Testing` | `0→O` | Biocompatibility |
| `5terilization Validation` | `5→S` | Sterilization |
| `She1f Life 7esting` | `1→l`, `7→T` | Shelf Life |
| `Perforrnance Data` | `rn→m` | Performance Testing |
| `SUBSTANTIAL EQU1VALENCE` | `1→I` | Predicate / SE |
| `$oftware Description` | `$→S` | Software |
| `Ste rilization` | remove space | Sterilization |
| `8iocompatibility` | `8→B` | Biocompatibility |
| `P3rformance 7esting` | `3→E`, `7→T` | Performance Testing |
| `C1inical Data` | `1→l` | Clinical |
| `E1ectrical Safety` | `1→l` | Electrical Safety |

---

## Tier 3: LLM Semantic Classification

Apply when Tiers 1 and 2 both fail. Uses content analysis and non-standard heading recognition.

### When to Apply

- Freeform narrative PDFs with no clear section headers
- EU-formatted documents using different terminology
- Novel or company-specific section naming
- Documents where headings are embedded in running text

### Classification Signal Table

For each section, require 2+ signals within a 200-word window to classify:

| Section | Classification Signals (2+ required) |
|---------|--------------------------------------|
| Indications for Use | "patient population", "anatomical site", "clinical condition", "prescription", "over-the-counter", "intended for" |
| Device Description | "principle of operation", "components", "materials of construction", "dimensions", "mechanism of action" |
| Substantial Equivalence | "predicate", "K-number" (K\d{6}), "substantially equivalent", "comparison", "subject device", "technological characteristics" |
| Performance Testing | standard citation (ISO/ASTM/IEC/AAMI), "sample size", "pass/fail", "test method", "acceptance criteria", "bench testing" |
| Biocompatibility | "ISO 10993", "cytotoxicity", "sensitization", "irritation", "systemic toxicity", "biocompatible", "biological evaluation" |
| Sterilization | "sterility assurance level", "SAL", "ethylene oxide", "gamma", "validation", "ISO 11135", "ISO 11137" |
| Clinical | "clinical study", "patients enrolled", "adverse events", "endpoints", "follow-up", "IDE", "literature review" |
| Shelf Life | "accelerated aging", "real-time aging", "ASTM F1980", "expiration", "storage conditions", "package integrity" |
| Software | "IEC 62304", "software lifecycle", "level of concern", "SOUP", "cybersecurity", "SBOM", "software architecture" |
| Electrical Safety | "IEC 60601", "EMC", "electromagnetic", "leakage current", "dielectric strength", "wireless coexistence" |
| Human Factors | "IEC 62366", "usability", "use error", "formative", "summative", "simulated use", "user interface" |
| Labeling | "instructions for use", "package insert", "symbols", "ISO 15223", "warnings and precautions" |

### Non-Standard Heading Map

Map non-standard or EU/international headings to canonical section names:

| Non-Standard Heading | Canonical Section |
|----------------------|-------------------|
| Intended Purpose | Indications for Use |
| Purpose and Clinical Application | Indications for Use |
| Therapeutic Indications | Indications for Use |
| Product Overview | Device Description |
| Technical Specifications | Device Description |
| Design Description | Device Description |
| Predicate Comparison | Substantial Equivalence |
| Equivalence Assessment | Substantial Equivalence |
| Comparative Analysis | Substantial Equivalence |
| Bench Testing | Performance Testing |
| Verification and Validation | Performance Testing |
| Analytical Performance | Performance Testing |
| Biological Safety | Biocompatibility |
| Material Biocompatibility | Biocompatibility |
| Biological Evaluation Report | Biocompatibility |
| Sterility | Sterilization |
| Microbial Control | Sterilization |
| Reprocessing | Sterilization |
| Stability | Shelf Life |
| Package Testing | Shelf Life |
| Durability | Shelf Life |
| Clinical Evidence | Clinical |
| Literature Evidence | Clinical |
| Post-Market Evidence | Clinical |
| Firmware | Software |
| Algorithm Description | Software |
| Digital Health | Software |
| Electromagnetic Compatibility | Electrical Safety |
| Wireless Testing | Electrical Safety |
| Usability Engineering | Human Factors |
| Ergonomic Assessment | Human Factors |
| Hazard Analysis | Risk Management |
| FMEA Results | Risk Management |

### Instructions

1. Scan the document for heading-like text (short lines, bold/caps formatting cues, lines followed by paragraph breaks)
2. Check each heading candidate against the Non-Standard Heading Map (case-insensitive exact or substring match)
3. If no heading match, scan the surrounding 200-word window for classification signals
4. Require 2+ signals from the same section's row to classify
5. Confidence threshold: if exactly 2 signals, confidence = moderate; 3+ signals, confidence = high
6. Output format: `"Section detected via Tier 3 (semantic: signals=[signal1, signal2, ...], confidence=high)"`

---

## Device-Type Specific Patterns

Apply these in addition to universal patterns when the product code is known.

### CGM / Glucose Monitors (Product Codes: SBA, QBJ, QLG, QDK, NBW, CGA, LFR, SAF)

```regex
(?i)(accuracy|mard|mean\s+absolute\s+relative\s+difference|clarke\s+error\s+grid|consensus\s+error\s+grid|parkes\s+error\s+grid|calibration|sensor\s+performance|sensor\s+duration|sensor\s+life|sensor\s+survival|warm[- ]?up\s+time|glucose\s+range|reportable\s+range|interference\s+testing|clsi\s+ep0?7|ysi|comparator\s+method|icgm|special\s+controls|alert\s+detection|hypo(?:glycemia|glycemic)|hyper(?:glycemia|glycemic))
```

**Key metrics to extract:** MARD (%), within 15/15%, within 20/20%, within 40/40%, reportable range, sensor duration, study size (N), number of matched pairs

### Wound Dressings (Product Codes: KGN, FRO, MGP)

```regex
(?i)(fluid\s+(?:handling|absorption|management)|moisture\s+vapor\s+transmission\s+rate|mvtr|wvtr|barrier\s+properties|adhesion\s+testing|conformability|antimicrobial\s+(?:efficacy|testing|effectiveness)|zone\s+of\s+inhibition|mic|mbc|minimum\s+inhibitory|minimum\s+bactericidal|silver\s+(?:content|release|ion)|collagen\s+(?:content|source|type)|wound\s+contact|aatcc\s+100|astm\s+d1777|dressing\s+integrity|peel\s+strength|absorbency)
```

### Orthopedic / Implantable Devices

```regex
(?i)(fatigue\s+(?:testing|life|strength)|biomechanical\s+(?:testing|characterization|performance)|wear\s+(?:testing|rate|characterization)|osseointegration|fixation\s+(?:strength|testing)|corrosion\s+(?:testing|resistance)|compression\s+(?:testing|strength)|tensile\s+(?:testing|strength)|torsion|astm\s+f(?:136|1295|1472|1537|1717|2129)|subsidence|migration|push[- ]?out|pull[- ]?out)
```

### Cardiovascular Devices (Product Codes: DXY, DTB, etc.)

```regex
(?i)(hemodynamic|thrombogenicity|blood\s+contact|platelet\s+adhesion|hemolysis|catheter\s+tracking|burst\s+pressure|kink\s+resistance|tensile\s+strength|flow\s+rate|pressure\s+drop|radiopacity|mri\s+(?:safety|conditional|compatibility))
```

### In Vitro Diagnostics

```regex
(?i)(analytical\s+(?:sensitivity|specificity)|clinical\s+(?:sensitivity|specificity)|limit\s+of\s+(?:detection|quantitation)|lod|loq|precision|reproducibility|linearity|accuracy|interference|cross[- ]?reactivity|matrix\s+effect|clsi\s+ep0?\d+|reference\s+range|cut[- ]?off|roc\s+curve|positive\s+predictive|negative\s+predictive)
```

---

## K/P/DEN/N Number Patterns

### K-Number Patterns

```regex
# Standard K-number (6 digits after K)
K\d{6}

# K-number with supplement suffix
K\d{6}/S\d{3}

# K-number with OCR errors (O→0, I→1, S→5)
[Kkℜ][O0I1]\d{5}
```

### P-Number Patterns

```regex
# Standard PMA number
P\d{6}

# PMA supplement
P\d{6}/S\d{3}
```

### DEN Number Patterns

```regex
# De Novo number
DEN\d{6,7}
```

### N-Number Patterns

```regex
# Pre-amendments device
N\d{4,5}
```

### Combined Device Number Pattern

```regex
(?:K\d{6}(?:/S\d{3})?|P\d{6}(?:/S\d{3})?|DEN\d{6,7}|N\d{4,5})
```

---

## eSTAR Section Number to XML Element Mapping

Used for routing imported eSTAR XML data to the correct parser:

| Section Regex | eSTAR Section | XML Root |
|---------------|---------------|----------|
| `section\s*0?1\b\|cover\s*letter` | 01 Cover Letter | `form1.CoverLetter` |
| `section\s*0?2\b\|cover\s*sheet\|3514` | 02 Cover Sheet | `form1.FDA3514` |
| `section\s*0?3\b\|510.*summary` | 03 510(k) Summary | `form1.Summary` |
| `section\s*0?4\b\|truthful` | 04 Truthful & Accuracy | `form1.TruthfulAccuracy` |
| `section\s*0?6\b\|device\s*desc` | 06 Device Description | `form1.DeviceDescription` |
| `section\s*0?7\b\|substantial\|SE\s` | 07 SE Comparison | `form1.SE` |
| `section\s*0?8\b\|standard` | 08 Standards | `form1.Standards` |
| `section\s*0?9\b\|label` | 09 Labeling | `form1.Labeling` |
| `section\s*10\b\|steriliz` | 10 Sterilization | `form1.Sterilization` |
| `section\s*11\b\|shelf` | 11 Shelf Life | `form1.ShelfLife` |
| `section\s*12\b\|biocompat` | 12 Biocompatibility | `form1.Biocompat` |
| `section\s*13\b\|software\|cyber` | 13 Software | `form1.Software` |
| `section\s*14\b\|EMC\|electric` | 14 EMC/Electrical | `form1.EMC` |
| `section\s*15\b\|performance` | 15 Performance Testing | `form1.Performance` |
| `section\s*16\b\|clinical` | 16 Clinical | `form1.Clinical` |

---

## Product Code Device Type Groups

Product codes grouped by device category for test plan generation and device-specific pattern selection:

| Category | Product Codes |
|----------|---------------|
| Continuous Glucose Monitors | MDS, QKQ, SBA, QBJ, QLG, QDK, NBW, CGA, LFR, SAF |
| Wound Dressings | FRO, KGN, KGO, MGP, NAO |
| Orthopedic Implants | OVE, MAX, NKB, MQP, MQV |
| Cardiovascular | DQY, DTB, DXY, MGB, NIQ |
| Software / SaMD | QAS, QMT, QDQ, QPG |
| IVD / Diagnostics | JJX, QKQ, MQB, OEW |
| Dental | HQF, EHJ, EIG |
| Ophthalmic | HQF, MRC, NQB |
| Respiratory | BTK, BYF, CAK |
| General Surgery | GEI, LYA, GAX |

---

## Section Extraction Strategy

1. **Apply the 3-tier escalation protocol** — try Tier 1 regex first, then Tier 2 OCR correction, then Tier 3 semantic classification
2. **Handle numbered sections** — `1.`, `I.`, `A.`, `Section 1:` etc. may precede section names; strip numbering before matching
3. **Handle ALL CAPS** — all patterns are case-insensitive; normalize before Tier 2/3 if needed
4. **Handle table-formatted SE sections** — look for `|` or tab-delimited structures after SE headers
5. **Handle very short sections** — if extracted text is <50 words, check the next 30 lines for continuation on the next page
6. **Multi-page sections** — section may span multiple pages; skip page break indicators (e.g., "Page X of Y", footer text)
7. **Record which tier detected each section** — this aids debugging and confidence assessment
