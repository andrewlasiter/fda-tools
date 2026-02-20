# eSTAR XML Validation - Quick Start Guide

**Feature:** FDA-23 eSTAR XML Schema Validation and Security Hardening
**Status:** Production Ready
**Compliance:** 21 CFR Part 11

---

## 5-Minute Quick Start

### 1. Validate Your Project Before Submission

```bash
python3 scripts/estar_xml.py validate --project YOUR_PROJECT_NAME
```

**What it checks:**
- ✅ Required FDA fields (applicant, device name, product code, etc.)
- ✅ Field formats (product code, regulation number)
- ✅ XML security (injection prevention)
- ✅ XML structure (well-formedness, namespaces)
- ✅ XSD schema (if available)

**Example output:**
```
Validating eSTAR XML for project: DQY_CATHETER
Template type: nIVD

=== VALIDATION REPORT ===
Project: DQY_CATHETER
Template: nIVD
Overall Status: PASS

XML Well-Formed: YES
XSD Schema Valid: N/A (schema not available)

VALIDATION PASSED - Ready for FDA submission review.
```

### 2. Generate XML (with Automatic Validation)

```bash
python3 scripts/estar_xml.py generate --project YOUR_PROJECT_NAME --template nIVD
```

**Automatic validation:**
- Checks required fields before generation
- Validates XML structure after generation
- Reports warnings and errors

### 3. Save Detailed Validation Report

```bash
python3 scripts/estar_xml.py validate --project YOUR_PROJECT_NAME --output validation_report.json
```

**Report includes:**
- Missing/invalid fields
- XML structure errors
- Security issues
- Warnings
- Overall status (PASS/WARNING/FAIL)

---

## Common Validation Issues and Fixes

### Issue 1: Missing Required Fields

**Error:**
```
Missing or empty required field: Applicant company name (applicant_name)
```

**Fix:**
Add to `device_profile.json` or `import_data.json`:
```json
{
  "applicant": {
    "applicant_name": "Your Company Name Inc"
  }
}
```

### Issue 2: Invalid Product Code Format

**Error:**
```
Invalid product code format: 'dqy'. Expected 3 uppercase letters.
```

**Fix:**
Product codes must be exactly 3 uppercase letters:
```json
{
  "product_code": "DQY"  // Correct
}
```

### Issue 3: Invalid Regulation Number Format

**Error:**
```
Invalid regulation number format: '870-1210'. Expected format: xxx.xxxx
```

**Fix:**
Use period separator, not hyphen:
```json
{
  "regulation_number": "870.1210"  // Correct
}
```

### Issue 4: Placeholder Text Detected

**Warning:**
```
WARNING: Indications for use contains placeholder text (TODO placeholder).
```

**Fix:**
Replace placeholder text in `device_profile.json`:
```json
{
  "indications_for_use": "The device is indicated for [TODO: text here]"  // Wrong
}

// Should be:
{
  "indications_for_use": "The device is indicated for temporary vascular access in adult patients requiring intravenous therapy."  // Correct
}
```

### Issue 5: Brief Indications for Use

**Warning:**
```
WARNING: Indications for use appears too brief (<50 characters).
```

**Fix:**
FDA expects detailed IFU statements (minimum 50 characters). Expand your indication:
```json
{
  "indications_for_use": "For diagnostic use."  // Too brief (17 chars)
}

// Should be:
{
  "indications_for_use": "The device is indicated for in vitro diagnostic use in clinical laboratories to measure glucose levels in whole blood samples from adult patients."  // Better (155 chars)
}
```

### Issue 6: No Predicate Device

**Warning:**
```
WARNING: No predicate device specified. Required for traditional SE 510(k) pathway.
```

**Fix:**
Add predicate device to `review.json` or `import_data.json`:
```json
{
  "predicates": [
    {
      "k_number": "K241335",
      "device_name": "Predicate Device Name",
      "manufacturer": "Predicate Medical Corp"
    }
  ]
}
```

---

## Template Types

### nIVD (Default)
For non-IVD 510(k) submissions:
```bash
python3 scripts/estar_xml.py validate --project PROJECT --template nIVD
```

**Required fields:**
- Applicant name
- Device trade name
- Product code (3 uppercase letters)
- Regulation number (xxx.xxxx format)
- Indications for use (≥50 chars)
- Predicate K-number

### IVD
For in vitro diagnostic (IVD) 510(k) submissions:
```bash
python3 scripts/estar_xml.py validate --project PROJECT --template IVD
```

**Same requirements as nIVD** plus IVD-specific sections

### PreSTAR
For Pre-Submission meeting requests:
```bash
python3 scripts/estar_xml.py validate --project PROJECT --template PreSTAR
```

**Required fields (relaxed):**
- Applicant name
- Device trade name
- Product code
- Indications for use
- No predicate required (meeting may precede pathway selection)
- No regulation number required (device may not be classified yet)

---

## Security Features

### Automatic Protection Against:

1. **XML Injection Attacks**
   - Script tags: `<script>alert('xss')</script>`
   - Entity declarations: `<!ENTITY xxe ...>`
   - JavaScript protocols: `javascript:alert()`

2. **Data Corruption**
   - Control characters removed
   - Invalid XML characters filtered
   - Special characters properly escaped

3. **DoS Attacks**
   - Field length limits enforced
   - Excessively long fields truncated with warning

**You don't need to do anything - protection is automatic!**

---

## XSD Schema Validation (Optional)

For complete validation, obtain official FDA eSTAR XSD schemas:

### 1. Obtain Schemas from FDA
- Download from eSTAR application
- Request from FDA Device Submissions office

### 2. Install Schemas
```bash
mkdir -p scripts/schemas/
cp estar_nivd_v6.1.xsd scripts/schemas/
cp estar_ivd_v6.1.xsd scripts/schemas/
cp estar_prestar_v2.1.xsd scripts/schemas/
```

### 3. Validate with Schemas
```bash
python3 scripts/estar_xml.py validate --project PROJECT
```

**With schemas:**
```
XSD Schema Valid: YES
```

**Without schemas (default):**
```
XSD Schema Valid: N/A (schema not available)
```

**Note:** Schemas are NOT required for basic validation. Structural and field validation works without them.

---

## Validation Status Meanings

### ✅ PASS
All validations passed, no issues found.

**Action:** Ready for FDA submission review

### ⚠️ WARNING
Passed with non-critical warnings.

**Action:** Review warnings, fix if possible, then proceed

**Example warnings:**
- No predicate device (may be acceptable for De Novo)
- Brief indications for use
- Placeholder text detected
- XSD schema not available

### ❌ FAIL
Critical errors found, must be resolved.

**Action:** Fix all errors before submission

**Example errors:**
- Missing required fields
- Invalid field formats
- Malformed XML
- XSD schema validation failed

---

## Command Reference

### Validate Command
```bash
python3 scripts/estar_xml.py validate [OPTIONS]
```

**Options:**
- `--project, -p` - Project name (required)
- `--template, -t` - Template type: nIVD, IVD, PreSTAR (default: nIVD)
- `--output, -o` - Output JSON report file path (optional)

**Examples:**
```bash
# Basic validation
python3 scripts/estar_xml.py validate --project DQY_CATHETER

# IVD template
python3 scripts/estar_xml.py validate --project IVD_TEST --template IVD

# Save report
python3 scripts/estar_xml.py validate --project PROJECT --output report.json
```

### Generate Command (with Validation)
```bash
python3 scripts/estar_xml.py generate [OPTIONS]
```

**Options:**
- `--project, -p` - Project name (required)
- `--template, -t` - Template type: nIVD, IVD, PreSTAR (default: nIVD)
- `--format, -f` - XML format: real, legacy (default: real)
- `--output, -o` - Output XML file path (optional)

**Examples:**
```bash
# Generate with automatic validation
python3 scripts/estar_xml.py generate --project DQY_CATHETER

# Generate IVD template
python3 scripts/estar_xml.py generate --project IVD_TEST --template IVD

# Custom output path
python3 scripts/estar_xml.py generate --project PROJECT --output custom_path.xml
```

---

## Troubleshooting

### "Project directory not found"

**Error:**
```
ERROR: Project directory not found: /path/to/project
```

**Fix:**
Check project name and location:
```bash
# Check settings
cat ~/.claude/fda-tools.local.md | grep projects_dir

# List projects
ls ~/fda-510k-data/projects/

# Use correct project name
python3 scripts/estar_xml.py validate --project CORRECT_NAME
```

### "No data files found"

**Warning:**
```
WARNING: Project directory has no data files
```

**Fix:**
Run import or create data files:
```bash
# Import from FDA data
/fda-tools:import --product-code DQY

# Or create minimal device_profile.json
cat > device_profile.json << EOF
{
  "applicant_name": "Your Company",
  "trade_name": "Device Name",
  "product_code": "DQY",
  "regulation_number": "870.1210",
  "intended_use": "Your detailed indications for use..."
}
EOF
```

### "Validation failed with exception"

**Error:**
```
CRITICAL: Validation exception: [error details]
```

**Fix:**
1. Check Python version (requires Python 3.7+)
2. Check dependencies: `pip install lxml beautifulsoup4`
3. Check project data files are valid JSON
4. Report issue with error details

---

## Best Practices

### Before FDA Submission

1. **Run validation:**
   ```bash
   python3 scripts/estar_xml.py validate --project PROJECT --output validation_report.json
   ```

2. **Review report:**
   - Check `overall_status`
   - Fix all FAIL errors
   - Review and address WARNING items

3. **Generate final XML:**
   ```bash
   python3 scripts/estar_xml.py generate --project PROJECT --template nIVD
   ```

4. **Test import:**
   - Open official FDA eSTAR template PDF in Adobe Acrobat
   - Import generated XML
   - Verify all fields populated correctly

5. **Save validation artifacts:**
   - Keep `validation_report.json` with submission package
   - Documents validation performed per 21 CFR 11

### During Development

1. **Validate frequently:**
   ```bash
   # After each major change
   python3 scripts/estar_xml.py validate --project PROJECT
   ```

2. **Fix issues incrementally:**
   - Don't wait until submission deadline
   - Fix validation errors as they appear

3. **Use version control:**
   ```bash
   git add validation_report.json
   git commit -m "Validation passed for v1.2"
   ```

---

## Getting Help

### Documentation
- Full documentation: `docs/ESTAR_VALIDATION.md`
- Implementation details: `FDA-23_IMPLEMENTATION_SUMMARY.md`
- Schema setup: `scripts/schemas/README.md`

### Common Questions

**Q: Do I need XSD schemas?**
A: No, basic validation works without them. Schemas provide additional validation but are optional.

**Q: What if validation shows warnings?**
A: Review warnings and fix if possible. Some warnings are acceptable (e.g., no predicate for De Novo).

**Q: Can I skip validation?**
A: No, validation is automatic in `generate` command. Always review validation results before FDA submission.

**Q: Is my data secure?**
A: Yes, all user data is automatically sanitized to prevent XML injection and other security issues.

---

## Next Steps

1. **Validate your project:**
   ```bash
   python3 scripts/estar_xml.py validate --project YOUR_PROJECT
   ```

2. **Fix any issues** following the examples above

3. **Generate XML:**
   ```bash
   python3 scripts/estar_xml.py generate --project YOUR_PROJECT
   ```

4. **Import into eSTAR template** and review

5. **Submit to FDA** via eSTAR portal

---

## Support

For technical issues or questions:
- Check documentation in `docs/` directory
- Review test cases in `tests/test_estar_xml_validation.py`
- Consult FDA eSTAR guidance documents

**Remember:** This tool provides validation assistance, but final submission review is your responsibility. Always verify generated XML before FDA submission.
