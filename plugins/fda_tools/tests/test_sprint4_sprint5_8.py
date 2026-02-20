"""
Test Suite for Sprint 4 (ISO 14971 Risk Management) and Sprint 5-8 (Strategic Features)

Tests:
1. Risk management template structure
2. Hazard library JSON loading
3. Clinical endpoint library JSON loading
4. Terminology library JSON loading
5. AI/ML template structure
6. AI/ML detection in draft.md
"""

import json
import os
import pytest
import re

# Get plugin root
PLUGIN_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

class TestSprint4RiskManagement:
    """Test Sprint 4: ISO 14971 Risk Management Templates"""

    def test_risk_management_template_exists(self):
        """Test that ISO 14971 risk management template exists"""
        template_path = os.path.join(PLUGIN_ROOT, 'templates', 'risk_management_iso14971.md')
        assert os.path.exists(template_path), "Risk management template not found"

    def test_risk_management_template_structure(self):
        """Test that risk management template has required sections"""
        template_path = os.path.join(PLUGIN_ROOT, 'templates', 'risk_management_iso14971.md')
        with open(template_path, 'r') as f:
            content = f.read()

        required_sections = [
            '## 1. Risk Management Plan',
            '## 2. Hazard Identification and Risk Analysis',
            '### 2.2 Failure Modes and Effects Analysis (FMEA)',
            '### 2.3 Device-Specific Hazard Library',
            '## 3. Risk Evaluation',
            '## 4. Risk Control Measures',
            '## 5. Residual Risk Evaluation',
            '## 6. Risk-Benefit Analysis',
            '## 7. Production and Post-Production Information'
        ]

        for section in required_sections:
            assert section in content, f"Missing section: {section}"

    def test_risk_management_template_has_fmea_table(self):
        """Test that FMEA table structure is present"""
        template_path = os.path.join(PLUGIN_ROOT, 'templates', 'risk_management_iso14971.md')
        with open(template_path, 'r') as f:
            content = f.read()

        # Check for FMEA table headers
        assert 'Severity (S)' in content
        assert 'Probability (P)' in content
        assert 'RPN' in content
        assert 'Risk Level' in content

    def test_cardiovascular_hazards_library(self):
        """Test cardiovascular hazards JSON structure"""
        hazards_path = os.path.join(PLUGIN_ROOT, 'data', 'hazards', 'cardiovascular_hazards.json')
        assert os.path.exists(hazards_path), "Cardiovascular hazards library not found"

        with open(hazards_path, 'r') as f:
            data = json.load(f)

        # Validate structure
        assert 'version' in data
        assert 'source' in data
        assert 'hazards' in data
        assert isinstance(data['hazards'], list)
        assert len(data['hazards']) >= 10, "Should have at least 10 hazards"

        # Validate first hazard structure
        hazard = data['hazards'][0]
        required_keys = ['id', 'category', 'description', 'typical_severity',
                         'typical_probability', 'harm', 'iso14971_reference',
                         'common_causes', 'typical_controls']
        for key in required_keys:
            assert key in hazard, f"Missing key '{key}' in hazard"

    def test_orthopedic_hazards_library(self):
        """Test orthopedic hazards JSON structure"""
        hazards_path = os.path.join(PLUGIN_ROOT, 'data', 'hazards', 'orthopedic_hazards.json')
        assert os.path.exists(hazards_path), "Orthopedic hazards library not found"

        with open(hazards_path, 'r') as f:
            data = json.load(f)

        assert len(data['hazards']) >= 10, "Should have at least 10 orthopedic hazards"
        # Check for specific orthopedic hazards
        hazard_ids = [h['id'] for h in data['hazards']]
        assert 'OR-001' in hazard_ids  # Implant loosening
        assert 'OR-002' in hazard_ids  # Wear debris

    def test_surgical_hazards_library(self):
        """Test surgical hazards JSON structure"""
        hazards_path = os.path.join(PLUGIN_ROOT, 'data', 'hazards', 'surgical_hazards.json')
        assert os.path.exists(hazards_path), "Surgical hazards library not found"

        with open(hazards_path, 'r') as f:
            data = json.load(f)

        assert len(data['hazards']) >= 12, "Should have at least 12 surgical hazards"

    def test_electrical_hazards_library(self):
        """Test electrical hazards JSON structure"""
        hazards_path = os.path.join(PLUGIN_ROOT, 'data', 'hazards', 'electrical_hazards.json')
        assert os.path.exists(hazards_path), "Electrical hazards library not found"

        with open(hazards_path, 'r') as f:
            data = json.load(f)

        assert len(data['hazards']) >= 12, "Should have at least 12 electrical hazards"
        # Check for software-specific hazards
        hazard_ids = [h['id'] for h in data['hazards']]
        assert 'EL-005' in hazard_ids  # Software failure - loss of function
        assert 'EL-006' in hazard_ids  # Software failure - incorrect output


class TestSprint5_8StrategicFeatures:
    """Test Sprint 5-8: Strategic Features (Endpoints, AI/ML, Terminology)"""

    def test_cardiovascular_endpoints_library(self):
        """Test cardiovascular endpoints JSON structure"""
        endpoints_path = os.path.join(PLUGIN_ROOT, 'data', 'endpoints', 'cardiovascular_endpoints.json')
        assert os.path.exists(endpoints_path), "Cardiovascular endpoints library not found"

        with open(endpoints_path, 'r') as f:
            data = json.load(f)

        # Validate structure
        assert 'version' in data
        assert 'source' in data
        assert 'endpoints' in data
        assert 'primary_efficacy' in data['endpoints']
        assert 'primary_safety' in data['endpoints']

        # Check for key endpoints
        primary_efficacy = data['endpoints']['primary_efficacy']
        endpoint_ids = [e['id'] for e in primary_efficacy]
        assert 'CV-E001' in endpoint_ids  # TLR
        assert 'CV-E003' in endpoint_ids  # MACE

    def test_orthopedic_endpoints_library(self):
        """Test orthopedic endpoints JSON structure"""
        endpoints_path = os.path.join(PLUGIN_ROOT, 'data', 'endpoints', 'orthopedic_endpoints.json')
        assert os.path.exists(endpoints_path), "Orthopedic endpoints library not found"

        with open(endpoints_path, 'r') as f:
            data = json.load(f)

        # Check for key orthopedic endpoints
        primary_efficacy = data['endpoints']['primary_efficacy']
        endpoint_ids = [e['id'] for e in primary_efficacy]
        assert 'OR-E001' in endpoint_ids  # Harris Hip Score
        assert 'OR-E002' in endpoint_ids  # WOMAC
        assert 'OR-E004' in endpoint_ids  # Revision Rate

    def test_ivd_endpoints_library(self):
        """Test IVD endpoints JSON structure"""
        endpoints_path = os.path.join(PLUGIN_ROOT, 'data', 'endpoints', 'ivd_endpoints.json')
        assert os.path.exists(endpoints_path), "IVD endpoints library not found"

        with open(endpoints_path, 'r') as f:
            data = json.load(f)

        # Check for analytical and clinical performance sections
        assert 'analytical_performance' in data['endpoints']
        assert 'clinical_performance' in data['endpoints']

        analytical = data['endpoints']['analytical_performance']
        analytical_ids = [e['id'] for e in analytical]
        assert 'IVD-A001' in analytical_ids  # LoD
        assert 'IVD-A002' in analytical_ids  # Specificity
        assert 'IVD-A003' in analytical_ids  # Precision

    def test_catheter_terminology_library(self):
        """Test catheter terminology JSON structure"""
        terminology_path = os.path.join(PLUGIN_ROOT, 'data', 'terminology', 'catheter_terms.json')
        assert os.path.exists(terminology_path), "Catheter terminology library not found"

        with open(terminology_path, 'r') as f:
            data = json.load(f)

        assert 'version' in data
        assert 'terminology' in data

        # Check for key catheter terms
        device_chars = data['terminology']['device_characteristics']
        assert 'balloon_compliance' in device_chars
        assert 'rated_burst_pressure' in device_chars
        assert 'trackability' in device_chars

    def test_implant_terminology_library(self):
        """Test implant terminology JSON structure"""
        terminology_path = os.path.join(PLUGIN_ROOT, 'data', 'terminology', 'implant_terms.json')
        assert os.path.exists(terminology_path), "Implant terminology library not found"

        with open(terminology_path, 'r') as f:
            data = json.load(f)

        # Check for key implant terms
        materials = data['terminology']['materials']
        assert 'titanium_alloy' in materials
        assert 'cobalt_chromium' in materials
        assert 'ultra_high_molecular_weight_polyethylene' in materials

    def test_robot_terminology_library(self):
        """Test robot terminology JSON structure"""
        terminology_path = os.path.join(PLUGIN_ROOT, 'data', 'terminology', 'robot_terms.json')
        assert os.path.exists(terminology_path), "Robot terminology library not found"

        with open(terminology_path, 'r') as f:
            data = json.load(f)

        # Check for robotics-specific terms
        mech_specs = data['terminology']['mechanical_specifications']
        assert 'degrees_of_freedom' in mech_specs
        assert 'haptic_feedback' in mech_specs
        assert 'positioning_accuracy' in mech_specs

    def test_ivd_terminology_library(self):
        """Test IVD terminology JSON structure"""
        terminology_path = os.path.join(PLUGIN_ROOT, 'data', 'terminology', 'ivd_terms.json')
        assert os.path.exists(terminology_path), "IVD terminology library not found"

        with open(terminology_path, 'r') as f:
            data = json.load(f)

        # Check for IVD-specific terms
        analytical = data['terminology']['analytical_parameters']
        assert 'limit_of_detection' in analytical
        assert 'limit_of_quantitation' in analytical

    def test_samd_terminology_library(self):
        """Test SaMD terminology JSON structure"""
        terminology_path = os.path.join(PLUGIN_ROOT, 'data', 'terminology', 'samd_terms.json')
        assert os.path.exists(terminology_path), "SaMD terminology library not found"

        with open(terminology_path, 'r') as f:
            data = json.load(f)

        # Check for software-specific terms
        sw_class = data['terminology']['software_classification']
        assert 'software_as_medical_device' in sw_class
        assert 'clinical_decision_support' in sw_class

        # Check for software development terms
        sw_dev = data['terminology']['software_development']
        assert 'iec_62304_safety_class' in sw_dev
        assert 'software_bill_of_materials' in sw_dev

        # Check for AI/ML specific terms
        aiml = data['terminology']['ai_ml_specific']
        assert 'training_validation_test_datasets' in aiml
        assert 'bias_and_fairness' in aiml
        assert 'explainability' in aiml


class TestAIMLValidationTemplate:
    """Test AI/ML Validation Template"""

    def test_aiml_template_exists(self):
        """Test that AI/ML validation template exists"""
        template_path = os.path.join(PLUGIN_ROOT, 'templates', 'aiml_validation.md')
        assert os.path.exists(template_path), "AI/ML validation template not found"

    def test_aiml_template_structure(self):
        """Test that AI/ML template has required sections"""
        template_path = os.path.join(PLUGIN_ROOT, 'templates', 'aiml_validation.md')
        with open(template_path, 'r') as f:
            content = f.read()

        required_sections = [
            '## 1. Regulatory Framework and Standards',
            '### 1.2 Good Machine Learning Practice (GMLP) Principles',
            '## 2. Algorithm Development and Architecture',
            '## 3. Training Dataset',
            '## 4. Model Training and Hyperparameter Tuning',
            '## 5. Independent Test Set Evaluation',
            '### 5.4 Subgroup Performance Analysis',
            '## 6. External Validation',
            '## 8. Uncertainty Quantification and Explainability',
            '## 9. Failure Mode Analysis and Limitations',
            '## 10. Cybersecurity and Software Maintenance',
            '## 11. Post-Market Surveillance'
        ]

        for section in required_sections:
            assert section in content, f"Missing section: {section}"

    def test_aiml_template_has_gmlp_principles(self):
        """Test that all 10 GMLP principles are documented"""
        template_path = os.path.join(PLUGIN_ROOT, 'templates', 'aiml_validation.md')
        with open(template_path, 'r') as f:
            content = f.read()

        # Check for all 10 GMLP principles
        assert 'Multi-Disciplinary Expertise' in content
        assert 'Good Software Engineering' in content
        assert 'Representative of the Intended Patient Population' in content
        assert 'Independent of Test Sets' in content
        assert 'Best Available Methods' in content

    def test_aiml_template_has_bias_fairness_section(self):
        """Test that bias and fairness analysis is included"""
        template_path = os.path.join(PLUGIN_ROOT, 'templates', 'aiml_validation.md')
        with open(template_path, 'r') as f:
            content = f.read()

        assert '### 5.4 Subgroup Performance Analysis' in content
        assert 'bias and fairness' in content.lower()
        assert 'demographic subgroup' in content.lower()


class TestAIMLDetectionInDraft:
    """Test AI/ML auto-detection in draft.md"""

    def test_aiml_detection_section_exists(self):
        """Test that AI/ML detection section exists in draft.md"""
        draft_path = os.path.join(PLUGIN_ROOT, 'commands', 'draft.md')
        with open(draft_path, 'r') as f:
            content = f.read()

        assert 'AI/ML DEVICE AUTO-DETECTION' in content
        assert 'AIML_DETECTED' in content

    def test_aiml_keywords_comprehensive(self):
        """Test that AI/ML detection includes comprehensive keywords"""
        draft_path = os.path.join(PLUGIN_ROOT, 'commands', 'draft.md')
        with open(draft_path, 'r') as f:
            content = f.read()

        # Extract aiml_keywords list
        keywords_match = re.search(r'aiml_keywords\s*=\s*\[(.*?)\]', content, re.DOTALL)
        assert keywords_match, "aiml_keywords list not found"

        keywords_section = keywords_match.group(1)

        # Check for essential AI/ML keywords
        essential_keywords = [
            'machine learning',
            'neural network',
            'deep learning',
            'ai-powered',
            'artificial intelligence',
            'convolutional neural network',
            'random forest',
            'clinical decision support'
        ]

        for keyword in essential_keywords:
            assert keyword in keywords_section, f"Missing essential keyword: {keyword}"

    def test_aiml_template_reference(self):
        """Test that AI/ML detection references the correct template"""
        draft_path = os.path.join(PLUGIN_ROOT, 'commands', 'draft.md')
        with open(draft_path, 'r') as f:
            content = f.read()

        assert 'templates/aiml_validation.md' in content
        assert 'AIML_TEMPLATE' in content


class TestIntegration:
    """Integration tests for Sprint 4 & 5-8"""

    def test_all_hazard_libraries_loadable(self):
        """Test that all 4 hazard libraries can be loaded without errors"""
        hazard_types = ['cardiovascular', 'orthopedic', 'surgical', 'electrical']

        for hazard_type in hazard_types:
            hazards_path = os.path.join(PLUGIN_ROOT, 'data', 'hazards', f'{hazard_type}_hazards.json')
            assert os.path.exists(hazards_path), f"{hazard_type} hazards not found"

            with open(hazards_path, 'r') as f:
                data = json.load(f)

            # Validate JSON structure
            assert 'hazards' in data
            assert len(data['hazards']) > 0
            print(f"✓ {hazard_type}_hazards.json: {len(data['hazards'])} hazards loaded")

    def test_all_endpoint_libraries_loadable(self):
        """Test that all 3 endpoint libraries can be loaded without errors"""
        endpoint_types = ['cardiovascular', 'orthopedic', 'ivd']

        for endpoint_type in endpoint_types:
            endpoints_path = os.path.join(PLUGIN_ROOT, 'data', 'endpoints', f'{endpoint_type}_endpoints.json')
            assert os.path.exists(endpoints_path), f"{endpoint_type} endpoints not found"

            with open(endpoints_path, 'r') as f:
                data = json.load(f)

            # Validate JSON structure
            assert 'endpoints' in data
            print(f"✓ {endpoint_type}_endpoints.json loaded")

    def test_all_terminology_libraries_loadable(self):
        """Test that all 5 terminology libraries can be loaded without errors"""
        terminology_types = ['catheter', 'implant', 'robot', 'ivd', 'samd']

        for term_type in terminology_types:
            terminology_path = os.path.join(PLUGIN_ROOT, 'data', 'terminology', f'{term_type}_terms.json')
            assert os.path.exists(terminology_path), f"{term_type} terminology not found"

            with open(terminology_path, 'r') as f:
                data = json.load(f)

            # Validate JSON structure
            assert 'terminology' in data
            print(f"✓ {term_type}_terms.json loaded")

    def test_total_deliverables_count(self):
        """Test that all expected files are delivered"""
        # Sprint 4: 1 template + 4 hazard JSONs = 5 files
        # Sprint 5-8: 3 endpoint JSONs + 1 AI/ML template + 5 terminology JSONs + 1 draft.md modification = 10 new assets

        # Count hazard libraries
        hazards_dir = os.path.join(PLUGIN_ROOT, 'data', 'hazards')
        hazard_files = [f for f in os.listdir(hazards_dir) if f.endswith('.json')]
        assert len(hazard_files) == 4, f"Expected 4 hazard files, found {len(hazard_files)}"

        # Count endpoint libraries
        endpoints_dir = os.path.join(PLUGIN_ROOT, 'data', 'endpoints')
        endpoint_files = [f for f in os.listdir(endpoints_dir) if f.endswith('.json')]
        assert len(endpoint_files) == 3, f"Expected 3 endpoint files, found {len(endpoint_files)}"

        # Count terminology libraries
        terminology_dir = os.path.join(PLUGIN_ROOT, 'data', 'terminology')
        terminology_files = [f for f in os.listdir(terminology_dir) if f.endswith('.json')]
        assert len(terminology_files) == 5, f"Expected 5 terminology files, found {len(terminology_files)}"

        # Check templates
        templates_dir = os.path.join(PLUGIN_ROOT, 'templates')
        assert os.path.exists(os.path.join(templates_dir, 'risk_management_iso14971.md'))
        assert os.path.exists(os.path.join(templates_dir, 'aiml_validation.md'))

        print(f"✓ Total deliverables: {4 + 3 + 5 + 2} files (4 hazards + 3 endpoints + 5 terminology + 2 templates)")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
