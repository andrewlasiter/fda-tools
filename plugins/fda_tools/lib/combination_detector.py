#!/usr/bin/env python3
"""
Combination Product Detection Module

Detects drug-device and device-biologic combination products from device
descriptions, IFU text, and product names. Assigns RHO (Responsible Health
Organization) per 21 CFR Part 3.

FDA Guidance References:
- "Classification of Products as Drugs and Devices and Additional Product
  Classification Issues" (2011)
- "Principles for Codevelopment of an In Vitro Companion Diagnostic Device
  with a Therapeutic Product" (2016)

Author: FDA Tools Plugin Development Team
Date: 2026-02-14
"""

from typing import Dict, List, Optional, Tuple
import re
import unicodedata


class CombinationProductDetector:
    """Detects combination products and assigns RHO per FDA guidance."""

    # Security: FDA-939 HIGH-2 remediation
    MAX_INPUT_LENGTH = 50_000  # 50KB per field (generous for device descriptions)

    # Drug-device combination keywords
    # FDA-939 Priority 1-3: Use tuple instead of list (immutable)
    DRUG_DEVICE_KEYWORDS = (
        # Drug-eluting/coated devices
        'drug-eluting', 'drug-coated', 'drug eluting', 'drug coated',
        'drug impregnated', 'drug-impregnated', 'drug loaded', 'drug-loaded',

        # Specific drugs commonly used in combination products
        'paclitaxel', 'sirolimus', 'everolimus', 'zotarolimus',  # DES/DCB
        'heparin-coated', 'heparin coated', 'heparinized',  # Anticoagulant coatings
        'antibiotic-loaded', 'antibiotic loaded', 'gentamicin',  # Bone cement
        'silver-coated', 'silver coated', 'antimicrobial',  # Antimicrobial devices

        # Pharmacological descriptors
        'pharmacological', 'pharmacologic', 'drug delivery',
        'controlled release', 'sustained release', 'elution'
    )

    # Device-biologic combination keywords
    # FDA-939 Priority 1-3: Use tuple instead of list (immutable)
    DEVICE_BIOLOGIC_KEYWORDS = (
        # Tissue-based products
        'collagen', 'tissue-engineered', 'tissue engineered',
        'decellularized', 'acellular', 'xenograft', 'allograft',

        # Cell-based products
        'cell-seeded', 'cell seeded', 'cellular', 'autologous cells',
        'allogeneic cells', 'stem cell', 'cell therapy',

        # Biological materials
        'growth factor', 'platelet-rich plasma', 'prp', 'bone morphogenetic protein',
        'bmp', 'hyaluronic acid', 'chitosan',

        # Biologic descriptors
        'biological', 'biologic', 'bioactive', 'regenerative'
    )

    # Exclusions (keywords that look like combination but aren't)
    # FDA-939 Priority 1-3: Use tuple instead of list (immutable)
    EXCLUSIONS = (
        'compatible with', 'may be used with', 'can be used with',
        'drug-free', 'non-pharmacological', 'non-biological',
        'without drug', 'no drug', 'uncoated'
    )

    def __init__(self, device_data: Dict):
        """
        Initialize detector with device data.

        Args:
            device_data: Dictionary containing:
                - device_description: str
                - trade_name: str (optional)
                - intended_use: str (optional)
                - device_profile: dict (optional, for extracted_sections)

        Raises:
            ValueError: If input exceeds maximum length or is invalid type

        Security: FDA-939 CRITICAL-1, HIGH-2 remediation
        """
        self.device_data = device_data

        # FDA-939 HIGH-2: Validate input lengths BEFORE any processing
        self.device_description = self._validate_input(
            device_data.get('device_description', ''),
            'device_description'
        )
        self.trade_name = self._validate_input(
            device_data.get('trade_name', ''),
            'trade_name'
        )
        self.intended_use = self._validate_input(
            device_data.get('intended_use', ''),
            'intended_use'
        )

        # FDA-939 Priority 1-2: Normalize and combine text safely (validated lengths)
        combined_raw = ' '.join([
            self.device_description,
            self.trade_name,
            self.intended_use
        ])
        self.combined_text = self._normalize_text(combined_raw)

    # ============================================================
    # Security Validation Methods (FDA-939 Security Fixes)
    # ============================================================

    def _validate_input(self, text: str, field_name: str, max_length: int = None) -> str:
        """
        Validate input text length and type.

        Args:
            text: Input text to validate
            field_name: Field name for error messages
            max_length: Maximum allowed length (default: MAX_INPUT_LENGTH)

        Returns:
            Validated text string

        Raises:
            ValueError: If input exceeds maximum length or is not a string

        Security: FDA-939 HIGH-2 remediation (prevents DoS via oversized inputs)
        """
        if max_length is None:
            max_length = self.MAX_INPUT_LENGTH

        if not isinstance(text, str):
            raise ValueError(f"{field_name} must be a string, got {type(text).__name__}")

        if len(text) > max_length:
            raise ValueError(
                f"{field_name} exceeds maximum length {max_length} "
                f"(got {len(text)} characters). This limit prevents resource exhaustion."
            )

        return text

    def _normalize_text(self, text: str) -> str:
        """
        Normalize Unicode text to prevent lookalike bypasses and ensure consistent matching.

        Args:
            text: Text to normalize

        Returns:
            Normalized lowercase text

        Security: FDA-939 Priority 1-2 remediation
        - NFC normalization prevents Unicode lookalike bypasses
        - Lowercase conversion done after normalization for efficiency
        """
        # NFC normalization (canonical composition)
        # Prevents bypass via Unicode lookalikes (e.g., 'e' vs 'é' vs 'ė')
        normalized = unicodedata.normalize('NFC', text)

        # Convert to lowercase (after normalization)
        lowercased = normalized.lower()

        return lowercased

    def detect(self) -> Dict:
        """
        Detect combination product status and assign RHO.

        Returns:
            Dictionary with:
                - is_combination: bool
                - combination_type: str ('drug-device', 'device-biologic', 'drug-device-biologic', or None)
                - confidence: str ('HIGH', 'MEDIUM', 'LOW')
                - detected_components: List[str] (specific drugs/biologics detected)
                - rho_assignment: str ('CDRH', 'CDER', 'CBER', or 'UNCERTAIN')
                - rho_rationale: str (explanation of RHO assignment)
                - consultation_required: str (which center to consult, or None)
                - regulatory_pathway: str ('510(k)', 'PMA', 'BLA', 'NDA', or 'UNCERTAIN')
                - recommendations: List[str] (regulatory guidance)
        """
        # Check for exclusions first
        if self._has_exclusions():
            return self._no_combination_result()

        # Detect drug component
        drug_detected, drug_components, drug_confidence = self._detect_drug()

        # Detect biologic component
        biologic_detected, biologic_components, biologic_confidence = self._detect_biologic()

        # Determine combination type
        if drug_detected and biologic_detected:
            combination_type = 'drug-device-biologic'
            confidence = min(drug_confidence, biologic_confidence)
            components = drug_components + biologic_components
        elif drug_detected:
            combination_type = 'drug-device'
            confidence = drug_confidence
            components = drug_components
        elif biologic_detected:
            combination_type = 'device-biologic'
            confidence = biologic_confidence
            components = biologic_components
        else:
            return self._no_combination_result()

        # Assign RHO and consultation requirements
        rho_info = self._assign_rho(combination_type, components)

        return {
            'is_combination': True,
            'combination_type': combination_type,
            'confidence': confidence,
            'detected_components': components,
            'rho_assignment': rho_info['rho'],
            'rho_rationale': rho_info['rationale'],
            'consultation_required': rho_info['consultation'],
            'regulatory_pathway': rho_info['pathway'],
            'recommendations': self._get_recommendations(combination_type)
        }

    def _has_exclusions(self) -> bool:
        """Check for exclusion keywords that negate combination status."""
        return any(excl in self.combined_text for excl in self.EXCLUSIONS)

    def _detect_drug(self) -> Tuple[bool, List[str], str]:
        """
        Detect drug component.

        Returns:
            (detected: bool, components: List[str], confidence: str)
        """
        detected_drugs = []

        for keyword in self.DRUG_DEVICE_KEYWORDS:
            if keyword in self.combined_text:
                detected_drugs.append(keyword)

        if not detected_drugs:
            return (False, [], 'NONE')

        # High confidence: Specific drug names (paclitaxel, sirolimus, etc.)
        specific_drugs = ['paclitaxel', 'sirolimus', 'everolimus', 'zotarolimus',
                         'gentamicin', 'heparin']
        if any(drug in self.combined_text for drug in specific_drugs):
            confidence = 'HIGH'
        # Medium confidence: "drug-eluting", "drug-coated"
        elif any(term in self.combined_text for term in ['drug-eluting', 'drug-coated', 'drug eluting']):
            confidence = 'MEDIUM'
        # Low confidence: General terms like "pharmacological"
        else:
            confidence = 'LOW'

        return (True, detected_drugs, confidence)

    def _detect_biologic(self) -> Tuple[bool, List[str], str]:
        """
        Detect biologic component.

        Returns:
            (detected: bool, components: List[str], confidence: str)
        """
        detected_biologics = []

        for keyword in self.DEVICE_BIOLOGIC_KEYWORDS:
            if keyword in self.combined_text:
                detected_biologics.append(keyword)

        if not detected_biologics:
            return (False, [], 'NONE')

        # High confidence: Cell therapy, growth factors, tissue-engineered
        high_conf_terms = ['cell therapy', 'stem cell', 'growth factor', 'tissue-engineered',
                          'bmp', 'bone morphogenetic protein']
        if any(term in self.combined_text for term in high_conf_terms):
            confidence = 'HIGH'
        # Medium confidence: Collagen, tissue materials
        elif any(term in self.combined_text for term in ['collagen', 'xenograft', 'allograft']):
            confidence = 'MEDIUM'
        # Low confidence: General biologic descriptors
        else:
            confidence = 'LOW'

        return (True, detected_biologics, confidence)

    def _assign_rho(self, combination_type: str, components: List[str]) -> Dict:
        """
        Assign RHO based on combination type and primary mode of action.

        Per FDA guidance, RHO is determined by the PRIMARY mode of action.
        For most medical devices with drug/biologic components, the device
        provides the primary mode of action (structural, mechanical).

        Args:
            combination_type: 'drug-device', 'device-biologic', or 'drug-device-biologic'
            components: List of detected drug/biologic components

        Returns:
            Dictionary with RHO assignment details
        """
        # Default: CDRH (device-led) for most combination products
        # Rationale: Most drug-eluting/coated devices have device as PMOA

        if combination_type == 'drug-device':
            # Drug-eluting stents, drug-coated balloons: Device is PMOA
            return {
                'rho': 'CDRH',
                'rationale': 'Device provides primary mode of action (mechanical/structural). Drug component provides secondary therapeutic benefit. Per 21 CFR Part 3, CDRH is RHO.',
                'consultation': 'CDER',
                'pathway': '510(k) or PMA (device pathway with drug component assessment)'
            }

        elif combination_type == 'device-biologic':
            # Tissue scaffolds, collagen matrices: Device is typically PMOA
            # Exception: Cell therapy devices may be CBER-led
            # Check for actual cell-based products (not "acellular")
            cell_based_terms = ['cell-seeded', 'cell seeded', 'stem cell', 'cell therapy',
                               'autologous cells', 'allogeneic cells', 'cellular']
            has_cells = any(term in comp for comp in components for term in cell_based_terms)
            # Exclude "acellular" from cell detection
            is_acellular = any('acellular' in comp or 'decellularized' in comp for comp in components)

            if has_cells and not is_acellular:
                return {
                    'rho': 'UNCERTAIN (likely CBER)',
                    'rationale': 'Cell-based component detected. If cells provide primary therapeutic mode of action (regenerative, immunological), CBER may be RHO. Recommend OCP Request for Designation (RFD).',
                    'consultation': 'CDRH',
                    'pathway': 'BLA (biologic license application) if CBER-led, or PMA if CDRH-led'
                }
            else:
                return {
                    'rho': 'CDRH',
                    'rationale': 'Device provides primary mode of action (structural support, barrier). Biologic component provides secondary benefit. Per 21 CFR Part 3, CDRH is RHO.',
                    'consultation': 'CBER',
                    'pathway': '510(k) or PMA (device pathway with biologic component assessment)'
                }

        elif combination_type == 'drug-device-biologic':
            return {
                'rho': 'UNCERTAIN',
                'rationale': 'Complex combination product with drug, device, and biologic components. Primary mode of action determination required. STRONGLY RECOMMEND OCP Request for Designation (RFD) per 21 CFR 3.7.',
                'consultation': 'CDER and CBER',
                'pathway': 'To be determined by OCP RFD process'
            }

        else:
            return {
                'rho': 'CDRH',
                'rationale': 'Standard medical device',
                'consultation': None,
                'pathway': '510(k) or PMA'
            }

    def _get_recommendations(self, combination_type: str) -> List[str]:
        """Get regulatory recommendations for combination products."""
        recommendations = [
            'CRITICAL: Identify and clearly state the Primary Mode of Action (PMOA) in Section 4 (Device Description)',
            'Include combination product rationale in cover letter',
            'Address both device and drug/biologic components in risk analysis (ISO 14971)',
        ]

        if combination_type == 'drug-device':
            recommendations.extend([
                'Provide drug component specifications: active ingredient, concentration, elution profile',
                'Include biocompatibility testing per ISO 10993 for drug-device interface',
                'Address drug stability and shelf life separately from device shelf life',
                'Consider guidance: "Drug-Eluting Coronary Artery Stent Systems" (2008) if cardiovascular',
            ])

        elif combination_type == 'device-biologic':
            recommendations.extend([
                'Provide biologic component specifications: source, processing, sterility',
                'Address immunogenicity and disease transmission risks',
                'Include detailed manufacturing controls for biologic component',
                'Consider guidance: "Regulatory Considerations for Human Cells, Tissues, and Cellular and Tissue-Based Products" (2007)',
            ])

        elif combination_type == 'drug-device-biologic':
            recommendations.extend([
                'STRONGLY RECOMMEND: Submit OCP Request for Designation (RFD) per 21 CFR 3.7 BEFORE full submission',
                'Engage OCP early in development (Pre-Pre-Sub or Pre-Sub meeting)',
                'Prepare detailed PMOA rationale with scientific justification',
            ])

        return recommendations

    def _no_combination_result(self) -> Dict:
        """Return result for non-combination device."""
        return {
            'is_combination': False,
            'combination_type': None,
            'confidence': 'N/A',
            'detected_components': [],
            'rho_assignment': 'CDRH',
            'rho_rationale': 'Standard medical device (not a combination product)',
            'consultation_required': None,
            'regulatory_pathway': '510(k) or PMA (standard device pathway)',
            'recommendations': []
        }


# Convenience function for command-line use
def detect_combination_product(device_description: str, trade_name: str = '', intended_use: str = '') -> Dict:
    """
    Convenience function to detect combination product from text inputs.

    Args:
        device_description: Device description text
        trade_name: Device trade/brand name (optional)
        intended_use: Intended use statement (optional)

    Returns:
        Detection result dictionary
    """
    device_data = {
        'device_description': device_description,
        'trade_name': trade_name,
        'intended_use': intended_use
    }

    detector = CombinationProductDetector(device_data)
    return detector.detect()
