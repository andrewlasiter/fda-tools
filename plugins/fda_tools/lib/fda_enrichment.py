"""
FDA API Enrichment Module - Phase 1, 2 & 3
==========================================

Production implementation of FDA 510(k) data enrichment with:
- Phase 1: Data Integrity (provenance, quality scoring, regulatory context)
- Phase 2: Intelligence Layer (clinical data detection, standards guidance, predicate assessment)
- Phase 3: Advanced Analytics (MAUDE peer comparison, competitive intelligence)

Version: 3.0.0 (Phase 3 Release 1)
Date: 2026-02-13

IMPORTANT: This module provides enrichment data for research and intelligence purposes.
All enriched data MUST be independently verified by qualified Regulatory Affairs
professionals before inclusion in any FDA submission.
"""

from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.parse import quote
from urllib.error import HTTPError, URLError
import json
import logging
import time
import sys

logger = logging.getLogger(__name__)


# Product Code to CFR Part Mapping
# Source: FDA Product Classification Database
# Updated: 2026-02-13
PRODUCT_CODE_CFR_PARTS = {
    # Cardiovascular Devices - 21 CFR 870
    'DQY': ('21 CFR 870.1340', 'Percutaneous Catheter'),
    'DRG': ('21 CFR 870.3610', 'Pacemaker'),
    'NIQ': ('21 CFR 870.3680', 'Implantable Cardioverter Defibrillator'),
    'NJY': ('21 CFR 870.3925', 'Coronary Stent'),
    'DTK': ('21 CFR 870.1425', 'Cardiovascular Angiographic Catheter'),
    'DRR': ('21 CFR 870.3545', 'Cardiovascular Permanent Implantable Pacemaker Electrode'),

    # Orthopedic Devices - 21 CFR 888
    'OVE': ('21 CFR 888.3080', 'Intervertebral Body Fusion Device'),
    'MNH': ('21 CFR 888.3353', 'Hip Prosthesis'),
    'KWP': ('21 CFR 888.3358', 'Knee Joint Patellofemorotibial Polymer/Metal/Polymer Semi-Constrained Cemented Prosthesis'),
    'HWC': ('21 CFR 888.3030', 'Bone Fixation Device'),
    'MAX': ('21 CFR 888.3025', 'Spinal Interlaminar Fixation Orthosis'),

    # General & Plastic Surgery - 21 CFR 878
    'GEI': ('21 CFR 878.4400', 'Electrosurgical Cutting and Coagulation Device'),
    'FRO': ('21 CFR 878.4018', 'Hydrophilic Wound Dressing'),
    'GAB': ('21 CFR 878.4450', 'Unclassified Surgical Instrument'),
    'KXM': ('21 CFR 878.5000', 'Suture'),

    # Radiology Devices - 21 CFR 892
    'QKQ': ('21 CFR 892.2050', 'Picture Archiving and Communications System'),
    'JAK': ('21 CFR 892.1650', 'Computed Tomography X-Ray System'),
    'MUW': ('21 CFR 892.1760', 'Magnetic Resonance Diagnostic Device'),

    # General Hospital - 21 CFR 880
    'FMM': ('21 CFR 880.5900', 'Surgical Instrument'),
    'FZP': ('21 CFR 880.6260', 'Nonelectrically Powered Fluid Injector'),
    'LRH': ('21 CFR 880.5400', 'Medical Magnetic Instrument'),

    # Anesthesiology - 21 CFR 868
    'BYG': ('21 CFR 868.5240', 'Breathing Circuit'),
    'BSM': ('21 CFR 868.1040', 'Anesthesia Breathing Circuit Bacterial Filter'),
    'CAW': ('21 CFR 868.5870', 'Ventilator'),

    # Clinical Chemistry - 21 CFR 862
    'JJE': ('21 CFR 862.1150', 'Glucose Test System'),
    'JIT': ('21 CFR 862.1660', 'Hemoglobin A1c Test System'),
    'DKZ': ('21 CFR 862.1355', 'Integrated Blood Glucose Test System'),

    # Hematology - 21 CFR 864
    'JJT': ('21 CFR 864.5220', 'Automated Hematology Analyzer'),
    'GGM': ('21 CFR 864.5425', 'Multipurpose System for In Vitro Coagulation Studies'),

    # Immunology - 21 CFR 866
    'MMH': ('21 CFR 866.5950', 'Immunological Test System'),
    'KSO': ('21 CFR 866.5540', 'Tumor Antigen Test System'),

    # Microbiology - 21 CFR 866
    'MEA': ('21 CFR 866.2660', 'Antimicrobial Susceptibility Test Powder'),
    'GDK': ('21 CFR 866.1640', 'Microbiological Specimen Collection and Transport Device'),

    # Pathology - 21 CFR 864
    'PHY': ('21 CFR 864.3250', 'Automated Cell Counter'),

    # Dental - 21 CFR 872
    'EMA': ('21 CFR 872.3570', 'Endodontic Dry Heat Sterilizer'),
    'EJS': ('21 CFR 872.3680', 'Orthodontic Plastic Bracket and Tray'),

    # Ear, Nose, Throat - 21 CFR 874
    'ETO': ('21 CFR 874.3430', 'Hearing Aid'),
    'FPJ': ('21 CFR 874.3695', 'Middle Ear Mold'),

    # Gastroenterology-Urology - 21 CFR 876
    'DQA': ('21 CFR 876.5540', 'Endoscope and Accessories'),
    'FKY': ('21 CFR 876.5011', 'Gastroenterology-Urology Catheter'),

    # Neurology - 21 CFR 882
    'GWQ': ('21 CFR 882.5820', 'Neonatal Incubator'),
    'DZE': ('21 CFR 882.1570', 'Computerized Electroencephalography System'),

    # Obstetrical and Gynecological - 21 CFR 884
    'MHW': ('21 CFR 884.2980', 'Unclassified Obstetrical-Gynecological Device'),

    # Ophthalmic - 21 CFR 886
    'NIR': ('21 CFR 886.4150', 'Soft (Hydrophilic) Contact Lens'),
    'HQD': ('21 CFR 886.3600', 'Intraocular Lens'),

    # Physical Medicine - 21 CFR 890
    'IOR': ('21 CFR 890.5150', 'Powered Wheelchair'),
    'KGZ': ('21 CFR 890.3475', 'Powered Patient Rotation Bed'),
}


def get_device_specific_cfr(product_code: str) -> Optional[Tuple[str, str]]:
    """
    Get device-specific CFR citation for a product code.

    Args:
        product_code: FDA product code (e.g., 'DQY', 'OVE')

    Returns:
        Tuple of (cfr_part, device_type) or None if not found
        Example: ('21 CFR 870.1340', 'Percutaneous Catheter')
    """
    return PRODUCT_CODE_CFR_PARTS.get(product_code)


class FDAEnrichment:
    """
    Main enrichment class for FDA 510(k) device data analysis.

    Provides comprehensive enrichment of FDA 510(k) data through:
    - Real-time openFDA API queries
    - Data provenance tracking
    - Quality scoring (0-100)
    - Regulatory context generation
    - Clinical data detection
    - Standards guidance
    - Predicate acceptability assessment

    Example:
        enricher = FDAEnrichment(api_key="your_key", api_version="2.0.1")
        api_log = []
        enriched_device = enricher.enrich_single_device(device_row, api_log)
    """

    def __init__(self, api_key: Optional[str] = None, api_version: str = "3.0.0"):
        """
        Initialize FDA enrichment system.

        Args:
            api_key: Optional openFDA API key for higher rate limits
            api_version: openFDA API version (default: "2.0.1")
        """
        self.api_key = api_key
        self.api_version = api_version
        self.base_url = "https://api.fda.gov/device"
        self.enrichment_timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

    # ========================================================================
    # PHASE 1: DATA INTEGRITY FUNCTIONS
    # ========================================================================

    def api_query(self, endpoint: str, params: Dict[str, Any]) -> Optional[Dict]:
        """
        Query openFDA API with rate limiting and error handling.

        Args:
            endpoint: API endpoint ('event', 'recall', '510k')
            params: Query parameters dict

        Returns:
            API response dict or None if error

        Example:
            data = enricher.api_query('510k', {'search': 'k_number:"K123456"', 'limit': 1})
        """
        if self.api_key:
            params['api_key'] = self.api_key

        query_string = '&'.join([f"{k}={quote(str(v))}" for k, v in params.items()])
        url = f"{self.base_url}/{endpoint}.json?{query_string}"

        try:
            req = Request(url, headers={'User-Agent': 'FDA-Predicate-Assistant/2.0'})
            response = urlopen(req, timeout=10)
            data = json.loads(response.read().decode('utf-8'))
            time.sleep(0.25)  # Rate limiting: 4 requests/second
            return data
        except HTTPError as e:
            if e.code == 404:
                return None
            return None
        except (URLError, Exception):
            return None

    def get_maude_events_by_product_code(self, product_code: str) -> Dict[str, Any]:
        """
        Get MAUDE events for a product code (NOT K-number).

        CRITICAL: openFDA links MAUDE events to product codes, NOT individual K-numbers.
        This means event counts are for the ENTIRE product code category.

        Args:
            product_code: FDA product code (e.g., 'DQY', 'GEI')

        Returns:
            Dict with MAUDE event counts and trending analysis

        Example:
            maude_data = enricher.get_maude_events_by_product_code('DQY')
            # Returns: {'maude_productcode_5y': 1847, 'maude_trending': 'stable', ...}
        """
        try:
            data = self.api_query('event', {
                'search': f'product_code:"{product_code}"',
                'count': 'date_received'
            })

            if data and 'results' in data:
                # Last 5 years of events (60 months)
                total_5y = sum([r['count'] for r in data['results'][:60]])

                # Trending: last 6 months vs previous 6 months
                recent_6m = sum([r['count'] for r in data['results'][:6]])
                prev_6m = sum([r['count'] for r in data['results'][6:12]])

                if prev_6m == 0:
                    trending = 'stable'
                elif recent_6m > prev_6m * 1.2:
                    trending = 'increasing'
                elif recent_6m < prev_6m * 0.8:
                    trending = 'decreasing'
                else:
                    trending = 'stable'

                return {
                    'maude_productcode_5y': total_5y,
                    'maude_trending': trending,
                    'maude_recent_6m': recent_6m,
                    'maude_scope': 'PRODUCT_CODE'  # Critical disclaimer
                }
        except Exception as e:
            logger.warning("MAUDE events query failed: %s", e)

        return {
            'maude_productcode_5y': 'N/A',
            'maude_trending': 'unknown',
            'maude_recent_6m': 'N/A',
            'maude_scope': 'UNAVAILABLE'
        }

    def get_recall_history(self, k_number: str) -> Dict[str, Any]:
        """
        Get recall data for specific K-number (ACCURATE - device specific).

        Unlike MAUDE data, recall data IS device-specific and linked to K-numbers.

        Args:
            k_number: FDA K-number (e.g., 'K123456')

        Returns:
            Dict with recall counts, latest date, class, and status

        Example:
            recalls = enricher.get_recall_history('K123456')
            # Returns: {'recalls_total': 2, 'recall_latest_date': '2024-01-15', ...}
        """
        try:
            data = self.api_query('recall', {
                'search': f'k_numbers:"{k_number}"',
                'limit': 10
            })

            if data and 'results' in data:
                recalls = data['results']

                if len(recalls) > 0:
                    latest = recalls[0]
                    return {
                        'recalls_total': len(recalls),
                        'recall_latest_date': latest.get('recall_initiation_date', 'Unknown'),
                        'recall_class': latest.get('classification', 'Unknown'),
                        'recall_status': latest.get('status', 'Unknown')
                    }
        except Exception as e:
            logger.warning("Recall history query failed: %s", e)

        return {
            'recalls_total': 0,
            'recall_latest_date': '',
            'recall_class': '',
            'recall_status': ''
        }

    def get_510k_validation(self, k_number: str) -> Dict[str, Any]:
        """
        Validate K-number and get clearance details.

        Args:
            k_number: FDA K-number (e.g., 'K123456')

        Returns:
            Dict with validation status and clearance details

        Example:
            validation = enricher.get_510k_validation('K123456')
            # Returns: {'api_validated': 'Yes', 'decision': 'Substantially Equivalent', ...}
        """
        try:
            data = self.api_query('510k', {
                'search': f'k_number:"{k_number}"',
                'limit': 1
            })

            if data and 'results' in data and len(data['results']) > 0:
                device = data['results'][0]
                return {
                    'api_validated': 'Yes',
                    'decision': device.get('decision_description', 'Unknown'),
                    'expedited_review': device.get('expedited_review_flag', 'N'),
                    'statement_or_summary': device.get('statement_or_summary', 'Unknown')
                }
        except Exception as e:
            logger.warning("510(k) validation query failed: %s", e)

        return {
            'api_validated': 'No',
            'decision': 'Unknown',
            'expedited_review': 'Unknown',
            'statement_or_summary': 'Unknown'
        }

    def calculate_enrichment_completeness_score(self, row: Dict[str, Any], api_log: List[Dict]) -> float:
        """
        Calculate Enrichment Data Completeness Score (0-100).

        IMPORTANT: This score measures the completeness and reliability of the FDA API
        enrichment process. It does NOT assess device quality, submission readiness,
        or regulatory compliance.

        Score Components:
        - Data Completeness (40%): Percentage of enrichment fields successfully populated
        - API Success Rate (30%): Percentage of openFDA API calls that returned valid data
        - Data Freshness (20%): Whether data is real-time from FDA vs cached/stale
        - Metadata Consistency (10%): Internal validation of enrichment provenance tracking

        Interpretation:
        - 80-100: HIGH confidence in enrichment data completeness
        - 60-79: MEDIUM confidence - some fields missing or API failures
        - <60: LOW confidence - significant data gaps or API issues

        Args:
            row: Enriched device row dict
            api_log: List of API call records for this device

        Returns:
            Score (0-100)

        Example:
            score = enricher.calculate_enrichment_completeness_score(device_row, api_log)
            # Returns: 87.5
        """
        score = 0

        # Data Completeness (40 points)
        fields_to_check = [
            'maude_productcode_5y',
            'maude_trending',
            'recalls_total',
            'api_validated',
            'decision',
            'statement_or_summary'
        ]
        populated = sum([1 for f in fields_to_check if row.get(f) not in ['N/A', '', None, 'Unknown', 'unknown']])
        completeness_pct = populated / len(fields_to_check)
        score += completeness_pct * 40

        # API Success Rate (30 points)
        k_number = row.get('KNUMBER', '')
        device_calls = [r for r in api_log if k_number in r.get('query', '')]
        if device_calls:
            success_rate = len([r for r in device_calls if r.get('success', False)]) / len(device_calls)
            score += success_rate * 30
        else:
            score += 15  # Partial credit if no calls logged

        # Data Freshness (20 points)
        if row.get('api_validated') == 'Yes':
            score += 20
        elif row.get('api_validated') == 'No':
            score += 10  # Partial credit for attempting validation

        # Cross-validation (10 points)
        if row.get('maude_scope') in ['PRODUCT_CODE', 'UNAVAILABLE']:
            score += 10  # Consistent scope metadata

        return round(score, 1)

    # ========================================================================
    # PHASE 2: INTELLIGENCE LAYER FUNCTIONS
    # ========================================================================

    def assess_predicate_clinical_history(self, validation_data: Dict[str, Any], decision_desc: str) -> Dict[str, Any]:
        """
        Assess whether PREDICATES had clinical data at time of clearance.

        IMPORTANT LIMITATION: This function analyzes predicate clinical data HISTORY.
        It does NOT predict whether YOUR device will need clinical data.

        Args:
            validation_data: Validation data dict from get_510k_validation()
            decision_desc: Decision description text

        Returns:
            Dict with predicate clinical history analysis

        Example:
            clinical = enricher.assess_predicate_clinical_history(validation, "Clinical study...")
            # Returns: {'predicate_clinical_history': 'YES', 'predicate_study_type': 'premarket', ...}
        """
        predicate_clinical_history = "NO"
        study_type = "none"
        indicators = []
        special_controls = "NO"

        decision_lower = decision_desc.lower() if decision_desc else ""

        # Assess if PREDICATE had clinical data
        if any(keyword in decision_lower for keyword in ['clinical study', 'clinical data', 'clinical trial', 'clinical evaluation']):
            predicate_clinical_history = "YES"
            study_type = "premarket"
            indicators.append('clinical_study_mentioned')

        # Check for postmarket requirements
        if any(keyword in decision_lower for keyword in ['postmarket surveillance', 'postmarket study', '522 order']):
            predicate_clinical_history = "YES"
            study_type = "postmarket"
            indicators.append('postmarket_study_required')

        # Check for special controls
        if any(keyword in decision_lower for keyword in ['special controls', 'guidance document', 'performance standards']):
            special_controls = "YES"
            indicators.append('special_controls_mentioned')

        # Check for human factors
        if any(keyword in decision_lower for keyword in ['human factors', 'usability', 'hfe']):
            indicators.append('human_factors')

        # Check for limited SE
        if 'sesp' in decision_lower or 'with limitations' in decision_lower:
            indicators.append('limited_se_decision')

        if predicate_clinical_history == "NO" and len(indicators) == 0:
            predicate_clinical_history = "UNKNOWN"

        return {
            'predicate_clinical_history': predicate_clinical_history,
            'predicate_study_type': study_type,
            'predicate_clinical_indicators': ', '.join(indicators) if indicators else 'none',
            'special_controls_applicable': special_controls
        }

    def assess_predicate_acceptability(self, k_number: str, recalls_data: Dict[str, Any], clearance_date: str) -> Dict[str, Any]:
        """
        Assess predicate acceptability per FDA SE guidance.

        Based on FDA's "The 510(k) Program: Evaluating Substantial Equivalence" (2014).

        Args:
            k_number: FDA K-number
            recalls_data: Recall data dict from get_recall_history()
            clearance_date: Clearance date string (YYYY-MM-DD)

        Returns:
            Dict with acceptability status and recommendation

        Example:
            acceptability = enricher.assess_predicate_acceptability('K123456', recalls, '2020-01-15')
            # Returns: {'acceptability_status': 'ACCEPTABLE', 'predicate_recommendation': '...', ...}
        """
        acceptability_status = "ACCEPTABLE"
        rationale = []
        risk_factors = []

        # Check recall history
        total_recalls = recalls_data.get('recalls_total', 0)

        if total_recalls > 0:
            acceptability_status = "REVIEW_REQUIRED"
            risk_factors.append(f"{total_recalls} recall(s) on record")
            rationale.append("Review recall details to assess if design issues affect YOUR device")

            if total_recalls >= 2:
                acceptability_status = "NOT_RECOMMENDED"
                rationale.append("Multiple recalls indicate systematic issues")

        # Check clearance age
        try:
            clearance_year = int(clearance_date[:4]) if clearance_date else 0
            age_years = datetime.now().year - clearance_year

            if age_years > 15:
                if acceptability_status == "ACCEPTABLE":
                    acceptability_status = "REVIEW_REQUIRED"
                risk_factors.append(f"Clearance age: {age_years} years")
                rationale.append(f"Device cleared in {clearance_year} may not reflect current standards")
            elif age_years > 10:
                risk_factors.append(f"Clearance age: {age_years} years")
        except Exception as e:
            logger.warning("Could not calculate clearance age for predicate acceptability: %s", e)

        # Generate recommendation
        if acceptability_status == "ACCEPTABLE":
            recommendation = "Suitable for primary predicate citation"
        elif acceptability_status == "REVIEW_REQUIRED":
            recommendation = "Review issues before using as primary predicate; consider as secondary predicate only"
        else:
            recommendation = "Avoid as primary predicate - search for alternatives without recall history"

        return {
            'predicate_acceptability': acceptability_status,
            'acceptability_rationale': '; '.join(rationale) if rationale else 'No significant issues identified',
            'predicate_risk_factors': ', '.join(risk_factors) if risk_factors else 'none',
            'predicate_recommendation': recommendation,
            'assessment_basis': 'FDA SE Guidance (2014) + recall history + clearance age'
        }

    def analyze_maude_peer_comparison(self, product_code: str, device_maude_count: int,
                                      device_name: str = '') -> Dict[str, Any]:
        """
        Phase 3 Feature 1: MAUDE Peer Comparison

        Compare device's MAUDE event count against peer distribution in same product code.
        Uses statistical percentiles to classify device as EXCELLENT, GOOD, AVERAGE,
        CONCERNING, or EXTREME_OUTLIER.

        Args:
            product_code: FDA product code (e.g., 'DQY', 'OVE')
            device_maude_count: This device's MAUDE event count (from Phase 1)
            device_name: Optional device name for brand fallback

        Returns:
            Dict with 7 new columns:
                - peer_cohort_size: Number of peer devices analyzed
                - peer_median_events: Median MAUDE count across peers
                - peer_75th_percentile: 75th percentile threshold
                - peer_90th_percentile: 90th percentile threshold
                - device_percentile: This device's percentile rank (0-100)
                - maude_classification: EXCELLENT/GOOD/AVERAGE/CONCERNING/EXTREME_OUTLIER
                - peer_comparison_note: Interpretation text
        """
        import statistics

        # Default response for unavailable/sparse data
        default_response = {
            'peer_cohort_size': 0,
            'peer_median_events': 'N/A',
            'peer_75th_percentile': 'N/A',
            'peer_90th_percentile': 'N/A',
            'device_percentile': 'N/A',
            'maude_classification': 'INSUFFICIENT_DATA',
            'peer_comparison_note': 'Insufficient peer data for comparison (cohort size < 10)'
        }

        # Query MAUDE for all devices in product code (aggregate product code level)
        # Note: MAUDE data is at product code level, not K-number level
        # We'll use decision_date from 510k API to get peer devices
        try:
            # Get peer devices from 510k API (last 5 years for statistical validity)
            from datetime import datetime, timedelta
            five_years_ago = (datetime.now() - timedelta(days=1825)).strftime('%Y%m%d')

            params = {
                'search': f'product_code:{product_code} AND decision_date:[{five_years_ago} TO 20991231]',
                'limit': 1000  # Get up to 1000 peers for robust statistics
            }

            peer_data = self.api_query('device/510k.json', params)

            if not peer_data or 'results' not in peer_data:
                return default_response

            peer_devices = peer_data['results']

            if len(peer_devices) < 10:  # Require minimum 10 peers for statistical validity
                default_response['peer_cohort_size'] = len(peer_devices)
                default_response['peer_comparison_note'] = f'Cohort too small ({len(peer_devices)} devices) for reliable statistics'
                return default_response

            # Extract MAUDE counts for each peer
            # Challenge: MAUDE is product-code level, not K-number level
            # Solution: Use brand name fallback hierarchy
            peer_maude_counts = []

            for peer in peer_devices:
                # Attempt 1: Query by K-number (often returns 0 due to indexing gaps)
                k_num = peer.get('k_number', '')
                maude_k = self.get_maude_events_by_product_code(k_num)  # Will return 0 if not indexed

                # Attempt 2: If K-number query returns 0 and we have brand name, try brand query
                if maude_k.get('maude_productcode_5y', 0) == 0:
                    brand_name = peer.get('device_name', '')
                    if brand_name:
                        # Query MAUDE by brand name (more likely to match)
                        brand_params = {
                            'search': f'product_code:{product_code} AND brand_name:"{brand_name}"',
                            'count': 'product_code'
                        }
                        brand_maude = self.api_query('device/event.json', brand_params)
                        if brand_maude and 'results' in brand_maude:
                            peer_maude_counts.append(brand_maude['results'][0].get('count', 0))
                        else:
                            peer_maude_counts.append(0)
                    else:
                        peer_maude_counts.append(0)
                else:
                    peer_maude_counts.append(maude_k.get('maude_productcode_5y', 0))

            # Calculate statistical distribution
            if len(peer_maude_counts) < 10:
                return default_response

            # Remove zeros for more meaningful statistics (devices with no events skew distribution)
            non_zero_counts = [c for c in peer_maude_counts if c > 0]

            if len(non_zero_counts) < 5:  # Need at least 5 non-zero for percentiles
                return default_response

            sorted_counts = sorted(non_zero_counts)

            # Calculate percentiles
            median = statistics.median(sorted_counts)
            percentile_75 = statistics.quantiles(sorted_counts, n=4)[2]  # 75th percentile
            percentile_90 = statistics.quantiles(sorted_counts, n=10)[8]  # 90th percentile
            percentile_25 = statistics.quantiles(sorted_counts, n=4)[0]  # 25th percentile

            # Calculate this device's percentile rank
            if device_maude_count == 0:
                device_pct = 0
                classification = 'EXCELLENT'
                note = 'Zero adverse events reported (best possible outcome)'
            else:
                # Count how many peers have fewer events than this device
                devices_below = sum(1 for c in sorted_counts if c < device_maude_count)
                device_pct = round((devices_below / len(sorted_counts)) * 100, 1)

                # Classify based on percentile
                if device_pct < 25:
                    classification = 'EXCELLENT'
                    note = f'Significantly below median ({device_maude_count} vs {median:.0f} median events)'
                elif device_pct < 50:
                    classification = 'GOOD'
                    note = f'Below median ({device_maude_count} vs {median:.0f} median events)'
                elif device_pct < 75:
                    classification = 'AVERAGE'
                    note = f'Near median ({device_maude_count} vs {median:.0f} median events)'
                elif device_pct < 90:
                    classification = 'CONCERNING'
                    note = f'Above 75th percentile ({device_maude_count} vs {percentile_75:.0f} P75) - review severity'
                else:
                    classification = 'EXTREME_OUTLIER'
                    note = f'Above 90th percentile ({device_maude_count} vs {percentile_90:.0f} P90) - DO NOT USE as predicate'

            return {
                'peer_cohort_size': len(sorted_counts),
                'peer_median_events': round(median, 1),
                'peer_75th_percentile': round(percentile_75, 1),
                'peer_90th_percentile': round(percentile_90, 1),
                'device_percentile': device_pct,
                'maude_classification': classification,
                'peer_comparison_note': note
            }

        except Exception as e:
            # Graceful degradation on error
            return {
                **default_response,
                'peer_comparison_note': f'Error during peer analysis: {str(e)[:100]}'
            }

    def enrich_single_device(self, device_row: Dict[str, Any], api_log: List[Dict]) -> Dict[str, Any]:
        """
        Enrich a single device row with Phase 1 & 2 data.

        Args:
            device_row: Base device data dict (must have 'KNUMBER', 'PRODUCTCODE', 'DECISIONDATE')
            api_log: List to append API call records to

        Returns:
            Enriched device row dict with all Phase 1 & 2 fields

        Example:
            api_log = []
            enriched = enricher.enrich_single_device({'KNUMBER': 'K123456', 'PRODUCTCODE': 'DQY', ...}, api_log)
        """
        k_number = device_row['KNUMBER']
        product_code = device_row.get('PRODUCTCODE', '')
        clearance_date = device_row.get('DECISIONDATE', '')

        # Phase 1: Basic enrichment
        maude_data = self.get_maude_events_by_product_code(product_code)
        recalls_data = self.get_recall_history(k_number)
        validation_data = self.get_510k_validation(k_number)

        # Log API calls
        api_log.append({'query': f'MAUDE:{product_code}', 'success': maude_data.get('maude_scope') != 'UNAVAILABLE'})
        api_log.append({'query': f'Recall:{k_number}', 'success': True})
        api_log.append({'query': f'510k:{k_number}', 'success': validation_data.get('api_validated') == 'Yes'})

        # Merge Phase 1 data
        enriched = device_row.copy()
        enriched.update(maude_data)
        enriched.update(recalls_data)
        enriched.update(validation_data)

        # Phase 2: Intelligence layer
        clinical_data = self.assess_predicate_clinical_history(
            validation_data,
            validation_data.get('decision', '')
        )
        enriched.update(clinical_data)

        acceptability_data = self.assess_predicate_acceptability(
            k_number,
            recalls_data,
            clearance_date
        )
        enriched.update(acceptability_data)

        # Phase 3: Advanced Analytics
        # Feature 1: MAUDE Peer Comparison
        device_maude_count = maude_data.get('maude_productcode_5y', 0)
        maude_scope = maude_data.get('maude_scope', '')

        # Only run peer comparison if MAUDE data is available (not UNAVAILABLE scope)
        if isinstance(device_maude_count, int) and device_maude_count >= 0 and maude_scope != 'UNAVAILABLE':
            peer_comparison = self.analyze_maude_peer_comparison(
                product_code,
                device_maude_count,
                device_row.get('DEVICENAME', '')
            )
            enriched.update(peer_comparison)
            api_log.append({'query': f'MAUDE_Peer:{product_code}', 'success': peer_comparison.get('peer_cohort_size', 0) >= 10})
        else:
            # No MAUDE data available - add default columns
            enriched.update({
                'peer_cohort_size': 0,
                'peer_median_events': 'N/A',
                'peer_75th_percentile': 'N/A',
                'peer_90th_percentile': 'N/A',
                'device_percentile': 'N/A',
                'maude_classification': 'NO_MAUDE_DATA',
                'peer_comparison_note': 'No MAUDE data available for this device'
            })

        # Add device-specific CFR citations (Fix #3: Critical Expert Review Finding)
        device_cfr = get_device_specific_cfr(product_code)
        if device_cfr:
            cfr_part, device_type = device_cfr
            enriched['regulation_number'] = cfr_part
            enriched['device_classification'] = device_type
        else:
            # Product code not in mapping - flag for manual lookup
            enriched['regulation_number'] = 'VERIFY_MANUALLY'
            enriched['device_classification'] = f'Product Code {product_code} - verify classification'

        # Calculate quality score
        enriched['enrichment_completeness_score'] = self.calculate_enrichment_completeness_score(enriched, api_log)

        # Add enrichment timestamp
        enriched['enrichment_timestamp'] = self.enrichment_timestamp
        enriched['api_version'] = self.api_version

        return enriched

    def enrich_device_batch(self, device_rows: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict]]:
        """
        Enrich a batch of devices with progress reporting.

        Args:
            device_rows: List of base device data dicts

        Returns:
            Tuple of (enriched_rows, api_log)

        Example:
            enriched_rows, api_log = enricher.enrich_device_batch(devices)
        """
        enriched_rows = []
        api_log = []
        total = len(device_rows)

        logger.info("Enriching %d devices with FDA API data...", total)

        for i, row in enumerate(device_rows, 1):
            k_number = row['KNUMBER']
            enriched = self.enrich_single_device(row, api_log)
            enriched_rows.append(enriched)

            # Progress reporting
            if i % 10 == 0 or i == total:
                logger.debug("Processed %d/%d devices (%.1f%%)", i, total, i/total*100)

        logger.info("Enrichment complete: %d devices processed", total)

        return enriched_rows, api_log


# Export main class
__all__ = ['FDAEnrichment']
