# FDA eSTAR XSD Schemas

This directory is for storing official FDA eSTAR XSD schema files.

## About XSD Schemas

FDA eSTAR XSD schemas define the official structure and validation rules for eSTAR XML submissions. These schemas are **NOT publicly distributed** and must be obtained separately from FDA.

## Obtaining Official Schemas

1. **eSTAR Application:** Download schemas through the official FDA eSTAR application
2. **FDA Contact:** Request schemas through FDA's Device Submissions office
3. **eCopy Program:** Schemas may be available through FDA's eCopy submission program

## Required Schema Files

Place the following XSD files in this directory to enable full validation:

### nIVD eSTAR (FDA 4062)
```
estar_nivd_v6.1.xsd
```
For non-IVD 510(k) submissions

### IVD eSTAR (FDA 4078)
```
estar_ivd_v6.1.xsd
```
For in vitro diagnostic (IVD) 510(k) submissions

### PreSTAR (FDA 5064)
```
estar_prestar_v2.1.xsd
```
For Pre-Submission meeting requests

## Version Compatibility

Current `estar_xml.py` implementation expects:
- nIVD eSTAR version 6.1
- IVD eSTAR version 6.1
- PreSTAR version 2.1

If you have different versions, you may need to:
1. Update the schema filenames in `estar_xml.py` (see `_validate_xml_against_xsd()`)
2. Test compatibility with your schema version
3. Report any issues

## Using Schemas

Once schemas are placed in this directory, the validation framework will automatically detect and use them:

```bash
python3 estar_xml.py validate --project PROJECT_NAME
```

You will see in the validation report:
```
XSD Schema Valid: YES
```

## Schema Not Available?

If you don't have access to official FDA schemas, the tool will still work with reduced validation:
- ✅ XML well-formedness validation
- ✅ Required field validation
- ✅ Structure validation
- ❌ Full XSD schema validation (skipped)

You will see in the validation report:
```
XSD Schema Valid: N/A (schema not available)
```

This is acceptable for development and testing, but we recommend obtaining official schemas for final submission validation.

## Security Note

**Do not distribute FDA's proprietary XSD schemas** without authorization. These schemas are:
- Intellectual property of FDA
- Subject to FDA's distribution policies
- Not licensed for redistribution

If you obtain schemas from FDA, keep them private and do not commit them to public repositories.

## Compliance

Per 21 CFR 11.10(a), software validation should include testing against official schemas when available. While not strictly required for open-source tools, using official schemas provides:
- Higher confidence in submission quality
- Earlier detection of compatibility issues
- Alignment with FDA's validation process

## Support

For questions about obtaining FDA eSTAR schemas:
- **FDA eSTAR Help:** Available through the eSTAR application
- **CDRH Submit:** https://www.fda.gov/medical-devices/premarket-submissions-selecting-and-preparing-correct-submission/cdrh-esubmitter
- **eCopy Program:** https://www.fda.gov/medical-devices/premarket-submissions/ecopy-program-medical-device-submissions

## Alternative: Manual Validation

If schemas are not available, you can manually validate XML files:
1. Generate XML: `python3 estar_xml.py generate --project PROJECT`
2. Import into official eSTAR PDF template in Adobe Acrobat
3. Review for import errors and field population
4. FDA's eSTAR application will perform final validation on submission

This manual validation approach is acceptable but more time-consuming than automated XSD validation.
