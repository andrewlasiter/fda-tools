"""
FDA Enrichment Disclaimers Module
==================================

Standardized disclaimer text for all FDA enrichment output files.
Ensures consistent, prominent warnings about data scope limitations
and verification requirements.

Version: 2.0.1 (Production Ready)
Date: 2026-02-13

IMPORTANT: All disclaimers are designed to comply with regulatory
best practices and prevent misuse of enriched data in FDA submissions
without independent verification.
"""

# ========================================================================
# CORE DISCLAIMERS
# ========================================================================

MAUDE_SCOPE_WARNING = """⚠️ MAUDE DATA SCOPE LIMITATION:
MAUDE event counts are aggregated at the PRODUCT CODE level, NOT device-specific.
This count reflects ALL devices within product code {product_code}, not just
K-number {k_number}. DO NOT cite as device-specific safety data without manual review.

For device-specific safety data, consult:
- FDA MAUDE database: https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfmaude/search.cfm
- Device recall database: https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfres/res.cfm
"""

ENRICHMENT_VERIFICATION_DISCLAIMER = """⚠️ DATA VERIFICATION REQUIRED:
All enriched data MUST be independently verified against official FDA sources by
qualified Regulatory Affairs professionals before inclusion in any FDA submission.

This enrichment tool provides RESEARCH and INTELLIGENCE data, not regulatory advice.
"""

CFR_CITATION_DISCLAIMER = """⚠️ CFR CITATION DISCLAIMER:
While CFR citation structure has been verified (URLs resolve, sections exist), the
appropriateness and completeness for specific regulatory contexts must be confirmed
by qualified RA professionals.

CFR citations are provided for convenience. Always verify you are using the most
current version of regulatory requirements at https://www.ecfr.gov/
"""

QUALITY_SCORE_DISCLAIMER = """⚠️ QUALITY SCORE DISCLAIMER:
Enrichment Data Completeness Scores reflect data completeness and API success rates
but do NOT constitute regulatory validation or FDA compliance certification.

Quality scores measure enrichment process reliability, NOT device quality or
submission readiness.
"""

CLINICAL_DATA_DISCLAIMER = """⚠️ CLINICAL DATA DETERMINATION DISCLAIMER:
Clinical data indicators reflect predicate HISTORY only. Whether YOUR device requires
clinical data depends on YOUR device's intended use, technological characteristics,
and device-specific guidance.

Per FDA's "The 510(k) Program: Evaluating Substantial Equivalence" (2014), schedule
a Pre-Submission meeting with FDA to discuss clinical data needs if uncertain.
"""

STANDARDS_DISCLAIMER = """⚠️ STANDARDS DETERMINATION DISCLAIMER:
Standards guidance is informational only. Applicable standards for YOUR device must
be determined through:
1. FDA Recognized Standards database query by product code
2. Device-specific FDA guidance document review
3. Predicate 510(k) summary analysis
4. Consultation with ISO 17025 accredited testing laboratories

Typical medical devices require 10-50 applicable standards depending on complexity.
"""

# ========================================================================
# CSV FILE DISCLAIMERS
# ========================================================================

def get_csv_header_disclaimer(product_codes: str = "[PRODUCT_CODES]") -> str:
    """
    Get disclaimer text for CSV file header.

    Args:
        product_codes: Product code(s) being enriched (e.g., 'DQY', 'DQY, GEI')

    Returns:
        Multi-line CSV comment string with warnings

    Example:
        disclaimer = get_csv_header_disclaimer('DQY')
        # Use in CSV: csv_content = disclaimer + csv_data
    """
    return f"""# FDA 510(k) Enriched Data - RESEARCH USE ONLY
#
# ⚠️ MAUDE DATA SCOPE LIMITATION:
# MAUDE event counts are PRODUCT CODE level (not device-specific).
# Product codes in this file: {product_codes}
# DO NOT cite MAUDE counts as device-specific safety data.
#
# ⚠️ DATA VERIFICATION REQUIRED:
# All enriched data MUST be independently verified by qualified RA professionals
# before inclusion in any FDA submission.
#
# ⚠️ APPROVED USE CASE: Research and intelligence gathering ONLY
# ⚠️ PROHIBITED USE CASE: Direct inclusion in FDA submissions without verification
#
# Generated: {{timestamp}}
# API Version: openFDA v2.1
# Enrichment Tool: FDA Predicate Assistant v2.0.1
#
"""

# ========================================================================
# HTML REPORT DISCLAIMERS
# ========================================================================

def get_html_banner_disclaimer() -> str:
    """
    Get HTML banner disclaimer for enrichment reports.

    Returns:
        HTML div element with prominent warning banner

    Example:
        banner = get_html_banner_disclaimer()
        # Insert at top of HTML report
    """
    return """
<div class="disclaimer-banner" style="background-color: #fff3cd; border: 3px solid #ffc107; border-radius: 8px; padding: 20px; margin: 20px 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;">
    <h2 style="color: #856404; margin-top: 0; font-size: 20px;">
        ⚠️ IMPORTANT DATA SCOPE LIMITATIONS & VERIFICATION REQUIREMENTS
    </h2>
    <div style="color: #856404; font-size: 14px; line-height: 1.6;">
        <ul style="margin: 10px 0; padding-left: 20px;">
            <li><strong>MAUDE Events:</strong> Aggregated by <strong>PRODUCT CODE</strong>, NOT device-specific.
                DO NOT cite as device-specific safety data without manual verification.</li>
            <li><strong>Verification Required:</strong> All enriched data (MAUDE counts, recall information,
                CFR citations, guidance references, quality scores, intelligence analysis) MUST be independently
                verified against official FDA sources by qualified Regulatory Affairs professionals before
                inclusion in any FDA submission.</li>
            <li><strong>Quality Scores:</strong> Reflect enrichment data completeness, NOT regulatory compliance
                or device quality.</li>
            <li><strong>Clinical Data Indicators:</strong> Reflect predicate history only. YOUR device's clinical
                data needs must be determined through device-specific analysis and FDA Pre-Submission discussion.</li>
            <li><strong>Standards Guidance:</strong> Informational only. Consult FDA Recognized Standards database,
                device-specific guidance, and ISO 17025 labs for YOUR device's requirements.</li>
        </ul>
        <p style="margin: 15px 0 0 0; font-weight: bold;">
            ✅ APPROVED USE: Research and intelligence gathering<br>
            ❌ PROHIBITED USE: Direct inclusion in FDA submissions without independent RA professional verification
        </p>
    </div>
</div>
"""

def get_html_footer_disclaimer() -> str:
    """
    Get HTML footer disclaimer for enrichment reports.

    Returns:
        HTML footer element with additional warnings

    Example:
        footer = get_html_footer_disclaimer()
        # Insert at bottom of HTML report
    """
    return """
<div class="disclaimer-footer" style="background-color: #f8f9fa; border-top: 2px solid #dee2e6; padding: 20px; margin-top: 40px; font-size: 12px; color: #6c757d; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;">
    <p style="margin: 0 0 10px 0;"><strong>Regulatory Advice Disclaimer:</strong></p>
    <p style="margin: 0 0 10px 0;">
        This enrichment tool provides data intelligence, not regulatory advice. All submission decisions
        should be reviewed by qualified regulatory affairs professionals, clinical/safety experts as
        appropriate, and legal counsel for compliance matters.
    </p>
    <p style="margin: 0 0 10px 0;">
        FDA guidance documents and CFR citations are provided for convenience. Always verify you are
        using the most current version of regulatory requirements.
    </p>
    <p style="margin: 0;"><strong>Data Sources:</strong> openFDA API v2.1 |
        <strong>Tool Version:</strong> FDA Predicate Assistant v2.0.1 |
        <strong>Status:</strong> Production Ready - Research Use Only
    </p>
</div>
"""

# ========================================================================
# MARKDOWN REPORT DISCLAIMERS
# ========================================================================

def get_markdown_header_disclaimer(report_type: str = "Enrichment Report") -> str:
    """
    Get markdown header disclaimer for markdown reports.

    Args:
        report_type: Type of report (e.g., "Quality Report", "Intelligence Report")

    Returns:
        Markdown-formatted disclaimer section

    Example:
        disclaimer = get_markdown_header_disclaimer("Quality Report")
        # Insert at top of markdown report
    """
    return f"""# {report_type}

---

## ⚠️ CRITICAL DISCLAIMERS

**RESEARCH USE ONLY - NOT FOR DIRECT FDA SUBMISSION USE**

### MAUDE Data Scope Limitation
MAUDE event counts are aggregated at the **PRODUCT CODE level**, NOT device-specific.
- ❌ **INCORRECT:** "K123456 has 1,847 adverse events"
- ✅ **CORRECT:** "Product code DQY has 1,847 MAUDE events over 5 years (category-level)"

### Data Verification Requirement
**ALL enriched data MUST be independently verified** against official FDA sources by qualified
Regulatory Affairs professionals before inclusion in any FDA submission.

This includes:
- MAUDE event counts
- Recall information
- CFR citations
- Guidance document references
- Quality scores
- Clinical data indicators
- Standards recommendations
- Predicate acceptability assessments

### Quality Score Interpretation
Enrichment Data Completeness Scores (0-100) measure the **reliability of the enrichment process**,
NOT device quality, submission readiness, or regulatory compliance.

### Clinical Data Determination
Clinical data indicators reflect **predicate history only**. YOUR device's clinical data needs
must be determined through device-specific analysis, guidance review, and FDA Pre-Submission discussion.

### Standards Determination
Standards guidance is **informational only**. Consult:
1. FDA Recognized Standards database (by product code)
2. Device-specific FDA guidance documents
3. Predicate 510(k) summary analysis
4. ISO 17025 accredited testing laboratories

---
"""

# ========================================================================
# JSON METADATA DISCLAIMERS
# ========================================================================

def get_json_disclaimers_section() -> dict:
    """
    Get disclaimers section for JSON metadata file.

    Returns:
        Dict with structured disclaimer information

    Example:
        metadata = {
            "enrichment_run": {...},
            "disclaimers": get_json_disclaimers_section()
        }
    """
    return {
        "scope_limitations": {
            "maude_data": "PRODUCT_CODE level aggregation, NOT device-specific",
            "clinical_indicators": "Predicate history only, NOT predictions for YOUR device",
            "standards_guidance": "Informational only, actual standards must be independently determined"
        },
        "verification_requirements": {
            "all_enriched_data": "MUST be independently verified by qualified RA professionals",
            "cfr_citations": "Verify appropriateness and currency for your regulatory context",
            "guidance_documents": "Confirm using most current version before reliance"
        },
        "approved_use_cases": [
            "Research and intelligence gathering",
            "Preliminary competitive analysis",
            "Predicate identification and screening",
            "Regulatory strategy planning"
        ],
        "prohibited_use_cases": [
            "Direct inclusion in FDA submissions without verification",
            "Citing as sole source for safety/effectiveness claims",
            "Relying on quality scores for regulatory compliance",
            "Using MAUDE counts as device-specific safety data"
        ],
        "quality_assurance": {
            "data_provenance": "All enriched fields include source, timestamp, and confidence metadata",
            "api_logging": "Complete audit trail of all openFDA API calls",
            "cfr_verification": "CFR citations verified for URL resolution and section existence",
            "guidance_currency": "Guidance documents checked against FDA.gov (as of enrichment date)"
        },
        "regulatory_status": "CONDITIONAL APPROVAL - RESEARCH USE ONLY (2026-02-13)",
        "required_actions_pending": [
            "RA-2: Genuine manual audit with independent FDA source verification",
            "RA-4: Independent CFR/guidance verification by qualified RA professional"
        ]
    }

# ========================================================================
# CONTEXT-SPECIFIC DISCLAIMERS
# ========================================================================

def format_maude_disclaimer_for_device(product_code: str, k_number: str, maude_count: int) -> str:
    """
    Format device-specific MAUDE disclaimer with actual values.

    Args:
        product_code: FDA product code (e.g., 'DQY')
        k_number: FDA K-number (e.g., 'K123456')
        maude_count: MAUDE event count to display

    Returns:
        Formatted disclaimer string

    Example:
        disclaimer = format_maude_disclaimer_for_device('DQY', 'K123456', 1847)
    """
    return MAUDE_SCOPE_WARNING.format(product_code=product_code, k_number=k_number)

def format_quality_score_disclaimer(score: float) -> str:
    """
    Format quality score with interpretation disclaimer.

    Args:
        score: Enrichment completeness score (0-100)

    Returns:
        Formatted score with interpretation

    Example:
        display = format_quality_score_disclaimer(87.5)
        # Returns: "87.5/100 (HIGH confidence in enrichment process) ⚠️ ..."
    """
    if score >= 80:
        confidence = "HIGH"
    elif score >= 60:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    return f"{score}/100 ({confidence} confidence in enrichment process)\n\n{QUALITY_SCORE_DISCLAIMER}"


# Export all public functions
__all__ = [
    'MAUDE_SCOPE_WARNING',
    'ENRICHMENT_VERIFICATION_DISCLAIMER',
    'CFR_CITATION_DISCLAIMER',
    'QUALITY_SCORE_DISCLAIMER',
    'CLINICAL_DATA_DISCLAIMER',
    'STANDARDS_DISCLAIMER',
    'get_csv_header_disclaimer',
    'get_html_banner_disclaimer',
    'get_html_footer_disclaimer',
    'get_markdown_header_disclaimer',
    'get_json_disclaimers_section',
    'format_maude_disclaimer_for_device',
    'format_quality_score_disclaimer'
]
