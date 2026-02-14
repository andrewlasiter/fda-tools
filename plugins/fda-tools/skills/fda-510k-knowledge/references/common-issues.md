# Common Extraction Issues and Troubleshooting

## OCR-Related Issues

### Character Confusion

The most common OCR errors in K-numbers:

| Misread | Correct | Example |
|---------|---------|---------|
| O (letter) | 0 (zero) | K24O717 → K240717 |
| I (letter) | 1 (one) | KI23456 → K123456 |
| l (lowercase L) | 1 (one) | Kl23456 → K123456 |
| S | 5 | K24S717 → K245717 |
| B | 8 | K24B717 → K248717 |
| Z | 2 | K2Z4717 → K224717 |
| G | 6 | K24G717 → K246717 |

### Resolving OCR Errors

1. **Validate against FDA database**: Check if number exists
2. **Try common substitutions**: Apply the table above
3. **Check context**: Does the document mention the company?
4. **Cross-reference**: Look for the number elsewhere in document

### When OCR Fails Completely

Symptoms:
- Very few or no K-numbers found
- Gibberish characters in output
- All numbers fail validation

Solutions:
- Use `--ocr always` mode
- Check PDF quality/resolution
- Verify PDF isn't image-only
- Try different PDF extraction library

## Document Format Issues

### 510(k) Statement vs Summary

| Document Type | Content Level | Extraction Success |
|---------------|---------------|-------------------|
| Summary | Detailed | High |
| Statement | Minimal | Low |

**Statements** often contain:
- Only the submitter's name
- Device name and intended use
- Brief equivalence statement
- NO predicate details

**Summaries** contain:
- Detailed device description
- Predicate device information
- Comparison tables
- Performance data

### Scanned vs Native PDFs

| PDF Type | Text Quality | OCR Needed |
|----------|--------------|------------|
| Native | Excellent | No |
| Scanned (high res) | Good | Yes |
| Scanned (low res) | Poor | Yes, may fail |

### Multi-Column Layouts

Problems:
- Text extraction may be jumbled
- K-numbers split across columns
- Tables not recognized

Solutions:
- Use table-aware extraction
- Process by visual regions
- Manual review for complex layouts

## Validation Issues

### Number Not in Database

Possible causes:
1. **Too recent**: FDA database not updated
2. **OCR error**: Number is incorrect
3. **Not a 510(k)**: Could be PMA, De Novo, etc.
4. **Typo in original**: Document has error

Resolution steps:
1. Try OCR corrections
2. Check FDA website directly
3. Verify document source
4. Flag for manual review

### Multiple Numbers, One Validation

When extracted text contains:
- Both K-number and related numbers
- Reference numbers mixed with predicates
- Supplement numbers (K123456/S001)

Solution:
- Parse supplement suffixes separately
- Distinguish predicate from reference context
- Use contextual clues

## Extraction Pattern Issues

### Missing Predicates

When predicates aren't found:

**Check document characteristics:**
- Is it a Statement (not Summary)?
- Are predicates in tables/images?
- Is the document redacted?
- Is the document complete?

**Check extraction settings:**
- Is OCR enabled if needed?
- Are all pages being processed?
- Are regex patterns comprehensive?

### False Positives

When non-predicates are extracted:

**Common false positives:**
- K-numbers in headers/footers
- Reference device numbers
- FDA submission tracking numbers
- Examples/comparisons

**Filtering strategies:**
- Check context around number
- Validate against FDA database
- Filter known non-predicates
- Use classification context

### Duplicate Entries

Causes:
- Number appears multiple times in document
- Multiple document versions processed
- Text extraction overlap

Solutions:
- Deduplicate after extraction
- Track source page/location
- Merge duplicate submissions

## Performance Issues

### Slow Processing

Factors:
- Large PDF files
- Many PDFs to process
- OCR processing time
- Network delays (database download)

Optimizations:
- Process in smaller batches
- Use cached database files
- Adjust worker count
- Skip OCR when not needed

### Memory Issues

Symptoms:
- Process killed
- Out of memory errors
- System slowdown

Solutions:
- Reduce batch size
- Reduce worker count
- Process PDFs sequentially
- Clear cache between batches

## Output Issues

### CSV Encoding Problems

Symptoms:
- Special characters corrupted
- Excel shows wrong characters
- Import errors

Solutions:
- Ensure UTF-8 encoding
- Use CSV reader that handles encoding
- Convert problematic characters

### Missing Columns

When output has fewer columns than expected:
- Some submissions have fewer predicates
- This is normal - not all cite many predicates
- Average is typically 1-3 predicates

## Debugging Checklist

When extraction results are unexpected:

1. **Check input**
   - [ ] PDFs are readable
   - [ ] Correct directory selected
   - [ ] Filters applied correctly

2. **Check processing**
   - [ ] No errors in console
   - [ ] All PDFs processed
   - [ ] OCR mode appropriate

3. **Check output**
   - [ ] Output files created
   - [ ] Data format correct
   - [ ] Validation passed

4. **Check database**
   - [ ] Database files current
   - [ ] Database files complete
   - [ ] Network access available

5. **Manual verification**
   - [ ] Sample PDF manually
   - [ ] Compare to extracted results
   - [ ] Identify discrepancies
