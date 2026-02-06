# 510(k) Section Detection Patterns

Centralized fuzzy regex patterns for detecting sections in FDA 510(k) summary PDFs. Section names vary significantly across years, sponsors, and device types. Use these patterns for case-insensitive matching.

## How to Use

For each section you need to extract:
1. Apply the regex pattern (case-insensitive) to find the section header
2. The section ends at the next header match or end of document
3. If no header found, try the **semantic fallback** keywords — if 3+ appear within 200 words, treat that block as the section
4. Apply device-type-specific patterns (bottom of this file) for additional sections

## Universal Sections (All Device Types)

### Indications for Use
```regex
(?i)(indications?\s+for\s+use|intended\s+use|ifu|indication\s+statement|device\s+indications?|clinical\s+indications?|approved\s+use)
```
**Semantic fallback:** patient population + anatomical site + clinical condition within 3 sentences

### Device Description
```regex
(?i)(device\s+description|product\s+description|description\s+of\s+(the\s+)?device|device\s+characteristics|physical\s+description|device\s+composition|device\s+components|system\s+description|system\s+overview)
```

### Substantial Equivalence / Predicate Comparison
```regex
(?i)(substantial\s+equivalence|se\s+comparison|predicate\s+(comparison|device|analysis|identification)|comparison\s+to\s+predicate|technological\s+characteristics|comparison\s+(table|chart|matrix)|similarities\s+and\s+differences|comparison\s+of\s+(the\s+)?(features|technological|device))
```
**Note:** This section often appears as a TABLE. If header found but minimal prose, search for table structures (rows with `|` delimiters or aligned columns) within the next 100 lines.

### Non-Clinical / Performance Testing
```regex
(?i)(non[- ]?clinical\s+(testing|studies|data|performance)|performance\s+(testing|data|evaluation|characteristics|bench)|bench\s+(testing|top\s+testing)|in\s+vitro\s+(testing|studies)|mechanical\s+(testing|characterization)|laboratory\s+testing|verification\s+(testing|studies)|validation\s+testing|analytical\s+performance)
```
**Semantic fallback:** 3+ test standard citations (ASTM, ISO, IEC, AAMI, ANSI) within 200 words

### Biocompatibility
```regex
(?i)(biocompatib(ility|le)?|biological\s+(evaluation|testing|safety|assessment)|iso\s*10993|cytotoxicity|sensitization\s+test|irritation\s+test|systemic\s+toxicity|genotoxicity|implantation\s+(testing|studies|study)|hemocompatibility|material\s+characterization|extractables?\s+and\s+leachables?)
```
**Note:** Any mention of ISO 10993-X (where X is a part number) indicates biocompatibility. Map parts:
- ISO 10993-1: Evaluation and testing framework
- ISO 10993-3: Genotoxicity, carcinogenicity, reproductive toxicity
- ISO 10993-4: Hemocompatibility
- ISO 10993-5: Cytotoxicity (in vitro)
- ISO 10993-6: Implantation effects
- ISO 10993-7: EO sterilization residuals
- ISO 10993-10: Sensitization
- ISO 10993-11: Systemic toxicity
- ISO 10993-12: Sample preparation
- ISO 10993-17: Toxicological risk assessment of device constituents
- ISO 10993-18: Chemical characterization
- ISO 10993-23: Irritation tests

### Clinical Testing / Clinical Data
```regex
(?i)(clinical\s+(testing|trial|study|studies|data|evidence|information|evaluation|investigation|performance)|human\s+(subjects?|study|clinical)|patient\s+study|pivotal\s+(study|trial)|feasibility\s+study|post[- ]?market\s+(clinical\s+)?follow[- ]?up|pmcf|literature\s+(review|search|summary|based)|clinical\s+experience)
```
**Distinguish types:**
- Prospective clinical study (strongest): "prospective", "enrolled", "IDE", "multi-center"
- Retrospective: "retrospective", "chart review"
- Literature review: "literature", "published", "peer-reviewed"
- Clinical experience: "post-market", "complaint", "adverse event"

### Sterilization
```regex
(?i)(steriliz(ation|ed|ing)|sterility\s+(assurance|testing|validation)|ethylene\s+oxide|eto|e\.?o\.?\s+(steriliz|residual)|gamma\s+(radiation|irradiation|steriliz)|electron\s+beam|e[- ]?beam|steam\s+steriliz|autoclave|iso\s*11135|iso\s*11137|sal\s+10|sterility\s+assurance\s+level)
```

### Shelf Life / Stability
```regex
(?i)(shelf[- ]?life|stability\s+(testing|studies|data)|accelerated\s+aging|real[- ]?time\s+aging|package\s+(integrity|testing|validation|aging)|astm\s*f1980|expiration\s+dat(e|ing)|storage\s+condition)
```

### Software
```regex
(?i)(software\s+(description|validation|verification|documentation|testing|v&v|lifecycle|architecture|design)|firmware|algorithm\s+(description|validation)|cybersecurity|iec\s*62304|software\s+level\s+of\s+concern|sloc|soup\s+analysis|off[- ]?the[- ]?shelf\s+software|ots\s+software|mobile\s+(medical\s+)?app(lication)?)
```

### Electrical Safety & EMC
```regex
(?i)(electrical\s+safety|iec\s*60601|electromagnetic\s+(compatibility|interference|disturbance)|emc|emi|wireless\s+(coexistence|testing)|rf\s+(safety|testing|emissions?)|radiation\s+safety|battery\s+safety|iec\s*62133|ul\s*1642)
```

### Human Factors / Usability
```regex
(?i)(human\s+factors|usability\s+(testing|engineering|study|evaluation)|use[- ]?related\s+risk|iec\s*62366|formative\s+(evaluation|study)|summative\s+(evaluation|study|test)|simulated\s+use|use\s+error)
```

### Risk Management
```regex
(?i)(risk\s+(management|analysis|assessment|evaluation)|iso\s*14971|fmea|failure\s+mode|hazard\s+analysis|fault\s+tree|risk[- ]?benefit)
```

### Labeling
```regex
(?i)(label(ing|s)?|instructions\s+for\s+use|package\s+insert|user\s+manual|iso\s*15223|udi|unique\s+device\s+identif)
```

## Device-Type Specific Patterns

### CGM / Glucose Monitors (Product Codes: SBA, QBJ, QLG, QDK, NBW, CGA, LFR, SAF)
```regex
(?i)(accuracy|mard|mean\s+absolute\s+relative\s+difference|clarke\s+error\s+grid|consensus\s+error\s+grid|parkes\s+error\s+grid|calibration|sensor\s+performance|sensor\s+duration|sensor\s+life|sensor\s+survival|warm[- ]?up\s+time|glucose\s+range|reportable\s+range|interference\s+testing|clsi\s+ep0?7|ysi|comparator\s+method|icgm|special\s+controls|alert\s+detection|hypo(glycemia|glycemic)|hyper(glycemia|glycemic))
```
**Key metrics to extract:** MARD (%), within 15/15%, within 20/20%, within 40/40%, reportable range, sensor duration, study size (N), number of matched pairs

### Wound Dressings (Product Codes: KGN, FRO, MGP)
```regex
(?i)(fluid\s+(handling|absorption|management)|moisture\s+vapor\s+transmission\s+rate|mvtr|wvtr|barrier\s+properties|adhesion\s+testing|conformability|antimicrobial\s+(efficacy|testing|effectiveness)|zone\s+of\s+inhibition|mic|mbc|minimum\s+inhibitory|minimum\s+bactericidal|silver\s+(content|release|ion)|collagen\s+(content|source|type)|wound\s+contact|aatcc\s+100|astm\s+d1777|dressing\s+integrity|peel\s+strength|absorbency)
```
**Key metrics to extract:** Absorption capacity, MVTR, adhesion strength, antimicrobial organisms tested, zone of inhibition sizes

### Orthopedic / Implantable Devices (Product Codes: various)
```regex
(?i)(fatigue\s+(testing|life|strength)|biomechanical\s+(testing|characterization|performance)|wear\s+(testing|rate|characterization)|osseointegration|fixation\s+(strength|testing)|corrosion\s+(testing|resistance)|compression\s+(testing|strength)|tensile\s+(testing|strength)|torsion|astm\s+f(136|1295|1472|1537|1717|2129)|subsidence|migration|push[- ]?out|pull[- ]?out)
```

### Cardiovascular Devices (Product Codes: DXY, DTB, etc.)
```regex
(?i)(hemodynamic|thrombogenicity|blood\s+contact|platelet\s+adhesion|hemolysis|catheter\s+tracking|burst\s+pressure|kink\s+resistance|tensile\s+strength|flow\s+rate|pressure\s+drop|radiopacity|mri\s+(safety|conditional|compatibility))
```

### In Vitro Diagnostics (Product Codes: various)
```regex
(?i)(analytical\s+(sensitivity|specificity)|clinical\s+(sensitivity|specificity)|limit\s+of\s+(detection|quantitation)|lod|loq|precision|reproducibility|linearity|accuracy|interference|cross[- ]?reactivity|matrix\s+effect|clsi\s+ep0?\d+|reference\s+range|cut[- ]?off|roc\s+curve|positive\s+predictive|negative\s+predictive)
```

## Section Extraction Strategy

1. **Try header matching first** — scan for section header patterns at the start of lines or after page breaks
2. **Handle numbered sections** — `1.`, `I.`, `A.`, `Section 1:` etc. may precede section names
3. **Handle ALL CAPS** — some sponsors use `DEVICE DESCRIPTION` instead of `Device Description`
4. **Handle table-formatted SE sections** — look for `|` or tab-delimited structures after SE headers
5. **Fallback to semantic detection** — if no header match, scan for keyword density (3+ domain keywords within 200 words)
6. **Handle very short sections** — if extracted text is <50 words, it may be a heading with content on the next page; check the next 30 lines
7. **Multi-page sections** — section may span multiple pages; look for page break indicators (e.g., "Page X of Y", footer text) and skip them
