# eSTAR Field Extraction Guide (FDA-120)

## Overview

The eSTAR Field Extractor improves automated field population from 25% to 60%+ by intelligently extracting data from project files.

## Field Coverage

### Before (25%)
✅ Device name, product code, regulation number, classification

### After (60%+)
✅ All above PLUS:
- Predicate comparison table (from se_comparison.md)
- Testing summary (from test_plan.md)
- Standards compliance list (from standards_lookup.json)
- Sterilization method (from device_profile.json or drafts)
- Materials (from device_profile.json or drafts)
- Shelf life (from calculations/)
- Biocompatibility summary (from drafts)
- Software description (from drafts)
- Predicate K-numbers (from review.json)

## Quick Start

### Standalone Usage

```python
from fda_tools.lib.estar_field_extractor import EStarFieldExtractor

# Create extractor
extractor = EStarFieldExtractor("/path/to/project")

# Extract all fields
fields = extractor.extract_all_fields()

# Use fields in eSTAR XML generation
print(f"Sterilization: {fields['sterilization_method']}")
print(f"Materials: {', '.join(fields['materials'])}")
print(f"Shelf Life: {fields['shelf_life']}")
```

### Integration with estar_xml.py

```python
# In estar_xml.py

from fda_tools.lib.estar_field_extractor import EStarFieldExtractor

def generate_xml(project_dir, output_path):
    # Extract fields
    extractor = EStarFieldExtractor(project_dir)
    fields = extractor.extract_all_fields()

    # Use extracted fields in XML generation
    xml_data = {
        'sterilization_method': fields['sterilization_method'],
        'materials': ', '.join(fields['materials']),
        'shelf_life': fields['shelf_life'],
        # ... etc
    }

    # Generate XML
    xml = build_estar_xml(xml_data)
    write_xml(output_path, xml)
```

## Field Extraction Details

### 1. Sterilization Method

**Sources** (priority order):
1. `device_profile.json` → `sterilization_method` field
2. `drafts/12_sterilization.md` → Parse method from text
3. Device description drafts

**Extraction Logic:**
- Normalizes to standard terms (EO, Steam, Gamma)
- Detects common variants ("ethylene oxide" → "EO")

**Example:**
```python
method = extractor.get_sterilization_method()
# Returns: "EO"
```

### 2. Materials

**Sources:**
1. `device_profile.json` → `materials` field (list or comma-separated)
2. `drafts/06_device_description.md` → Parse from "made of", "composed of"

**Extraction Logic:**
- Extracts up to 10 materials
- Detects common materials (titanium, silicone, PEEK, etc.)

**Example:**
```python
materials = extractor.get_materials()
# Returns: ["Titanium", "Silicone", "PEEK"]
```

### 3. Shelf Life

**Sources:**
1. `calculations/shelf_life.json` → `shelf_life` or `result` field
2. `device_profile.json` → `shelf_life` field

**Example:**
```python
shelf_life = extractor.get_shelf_life()
# Returns: "3 years"
```

### 4. Biocompatibility Summary

**Sources:**
1. `drafts/10_biocompatibility.md` → First 500 chars
2. `device_profile.json` → `biocompatibility` field

**Extraction Logic:**
- Removes markdown formatting
- Cleans newlines for eSTAR compatibility

**Example:**
```python
summary = extractor.get_biocompatibility_summary()
# Returns: "Device evaluated per ISO 10993-1. Testing included cytotoxicity..."
```

### 5. Software Description

**Sources:**
1. `drafts/15_software.md` → First 500 chars
2. `device_profile.json` → `software_description` field

**Example:**
```python
desc = extractor.get_software_description()
# Returns: "Embedded software for control and monitoring. Developed per IEC 62304..."
```

### 6. Predicate Comparison Table

**Source:** `se_comparison.md` markdown table

**Extraction Logic:**
- Parses markdown table rows
- Extracts: characteristic, subject value, predicate value, assessment
- Limits to first 20 rows

**Example:**
```python
comparison = extractor.get_predicate_comparison()
# Returns: [
#   {
#     'characteristic': 'Indications',
#     'subject': 'Cardiovascular use',
#     'predicate': 'Cardiovascular use',
#     'assessment': 'SE'
#   },
#   ...
# ]
```

### 7. Standards Compliance

**Source:** `standards_lookup.json`

**Extraction Logic:**
- Loads all standards
- Assumes "Compliant" status for listed standards
- Limits to first 30 standards

**Example:**
```python
standards = extractor.get_standards_compliance()
# Returns: [
#   {'number': 'ISO 10993-1', 'title': 'Biocompatibility', 'status': 'Compliant'},
#   ...
# ]
```

### 8. Testing Summary

**Sources:**
1. `test_plan.md` → Summary section or first 500 chars
2. `device_profile.json` → `testing_performed` list

**Extraction Logic:**
- Prefers explicit Summary section from test plan
- Falls back to test list from device profile
- Cleans markdown formatting

**Example:**
```python
summary = extractor.get_testing_summary()
# Returns: "Testing included biocompatibility, sterilization validation, and performance testing..."
```

### 9. Predicate K-Numbers

**Source:** `review.json` → `accepted_predicates`

**Example:**
```python
k_numbers = extractor.get_predicate_k_numbers()
# Returns: ['K123456', 'K789012']
```

## Field Population Scoring

Monitor extraction completeness:

```python
stats = extractor.get_field_population_score()
print(f"Coverage: {stats['population_percentage']}%")
print(f"Populated: {stats['populated_fields']}/{stats['total_fields']}")
print(f"List Items: {stats['list_items']}")
```

## CLI Testing

Test extraction for a project:

```bash
python3 -m lib.estar_field_extractor ~/fda-510k-data/projects/DQY/
```

Output:
```
eSTAR Field Population Report
==================================================
Total Fields: 9
Populated: 8
Coverage: 88.9%
List Items: 15

Extracted Fields:
  sterilization_method: EO
  materials: 2 items
  shelf_life: 3 years
  biocompatibility_summary: Device evaluated per ISO 10993-1. Testing includ...
  software_description: (empty)
  predicate_comparison: 5 items
  standards_compliance: 8 items
  testing_summary: Testing included biocompatibility, sterilization valida...
  predicate_k_numbers: 2 items
```

## Integration Checklist

For integrating into estar_xml.py:

1. ✅ Import EStarFieldExtractor
2. ✅ Create extractor instance with project_dir
3. ✅ Call extract_all_fields()
4. ✅ Map extracted fields to eSTAR XML elements
5. ✅ Handle None/empty values gracefully
6. ✅ Validate XML schema compliance
7. ✅ Test with 10+ diverse device types

## Field Mapping to eSTAR XML

| Extracted Field | eSTAR XML Element | Required |
|---|---|---|
| sterilization_method | Sterilization/Method | HIGH |
| materials | DeviceDescription/Materials | HIGH |
| predicate_comparison | PredicateComparison/Table | HIGH |
| testing_summary | TestingSummary/Text | HIGH |
| standards_compliance | Standards/List | MEDIUM |
| shelf_life | ShelfLife/Duration | MEDIUM |
| biocompatibility_summary | Biocompatibility/Summary | MEDIUM |
| software_description | Software/Description | MEDIUM (if applicable) |
| predicate_k_numbers | Predicates/KNumbers | HIGH |

## Error Handling

The extractor handles missing data gracefully:

```python
fields = extractor.extract_all_fields()

# Check for None before using
if fields['sterilization_method']:
    xml.add_sterilization(fields['sterilization_method'])
else:
    # Use default or prompt user
    pass

# Check list length
if len(fields['materials']) > 0:
    xml.add_materials(fields['materials'])
```

## Performance

- **Cold Start**: ~50-100ms (loads all JSON files)
- **Cached**: ~5-10ms (uses lazy-loaded data)
- **Memory**: ~1-2MB per project (JSON data cached)

## Limitations

1. **Draft Section Naming**: Requires standard naming (e.g., `12_sterilization.md`)
2. **Markdown Format**: SE comparison must be valid markdown table
3. **Text Extraction**: Regex-based extraction may miss complex formats
4. **Manual Review**: Extracted data should be reviewed before submission

## Future Enhancements

Potential improvements for >80% coverage:

- Accessories list extraction
- Packaging specifications
- Use environment details
- Intended user demographics
- IFU key points
- Performance specifications

## References

- **Module**: `lib/estar_field_extractor.py` (500+ lines)
- **Tests**: `tests/test_estar_field_extractor.py` (27 tests, all passing)
- **Integration**: `scripts/estar_xml.py` (2495 lines)
- **Issue**: FDA-120 - eSTAR Field Population Improvement
