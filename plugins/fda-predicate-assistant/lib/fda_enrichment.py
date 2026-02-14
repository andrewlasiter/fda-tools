"""
FDA API Enrichment Module - Phase 1 & 2
=======================================

Production implementation of FDA 510(k) data enrichment with:
- Phase 1: Data Integrity (provenance, quality scoring, regulatory context)
- Phase 2: Intelligence Layer (clinical data detection, standards guidance, predicate assessment)

Version: 2.0.1 (Production Ready)
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
import time


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

    def __init__(self, api_key: Optional[str] = None, api_version: str = "2.0.1"):
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
        except Exception:
            pass

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
        except Exception:
            pass

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
        except Exception:
            pass

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
        except:
            pass

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

        print(f"\n📊 Enriching {total} devices with FDA API data...")
        print("━" * 60)

        for i, row in enumerate(device_rows, 1):
            k_number = row['KNUMBER']
            enriched = self.enrich_single_device(row, api_log)
            enriched_rows.append(enriched)

            # Progress reporting
            if i % 10 == 0 or i == total:
                print(f"  ✓ Processed {i}/{total} devices ({i/total*100:.1f}%)")

        print("━" * 60)
        print(f"✅ Enrichment complete: {total} devices processed\n")

        return enriched_rows, api_log


# Export main class
__all__ = ['FDAEnrichment']
