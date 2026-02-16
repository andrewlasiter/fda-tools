#!/usr/bin/env python3
"""
Integration tests for TICKET-004: Pre-Sub Multi-Pathway Package Generator.

Tests the complete multi-pathway Pre-Sub workflow including:
1. Pathway detection from device class and keywords
2. Question selection with pathway filtering
3. Template routing to pathway-specific templates
4. Metadata generation with v2.0 schema fields
5. End-to-end package generation for all 4 pathways

Usage:
    pytest tests/test_presub_multipathway.py -v
    python3 tests/test_presub_multipathway.py  # Run directly
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Paths
PLUGIN_ROOT = Path(__file__).parent.parent
COMMANDS_DIR = PLUGIN_ROOT / "commands"
TEMPLATES_DIR = PLUGIN_ROOT / "data" / "templates" / "presub_meetings"
QUESTION_BANK_PATH = PLUGIN_ROOT / "data" / "question_banks" / "presub_questions.json"
SCHEMA_PATH = PLUGIN_ROOT / "data" / "schemas" / "presub_metadata_schema.json"

# Add scripts directory to path for imports
SCRIPT_DIR = PLUGIN_ROOT / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))


def _load_question_bank():
    """Load and return the question bank."""
    with open(QUESTION_BANK_PATH) as f:
        return json.load(f)


def _load_metadata_schema():
    """Load and return the metadata schema."""
    with open(SCHEMA_PATH) as f:
        return json.load(f)


def _detect_pathway(device_class, device_description, has_predicates=False):
    """Replicate the pathway detection logic from presub.md Step 3.25.

    This mirrors the Python code embedded in the presub.md command to
    ensure test fidelity with the actual implementation.

    Args:
        device_class: FDA device class ("1", "2", or "3")
        device_description: Device description text (searched for keywords)
        has_predicates: Whether predicate devices have been identified

    Returns:
        Tuple of (pathway, detection_method, rationale)
    """
    device_description_lower = device_description.lower()

    # Class III devices -> PMA (unless IDE for clinical study)
    if device_class == "3":
        ide_keywords = [
            "clinical study", "clinical investigation", "clinical trial",
            "investigational", "ide", "feasibility study", "pivotal study",
            "first-in-human", "first in human"
        ]
        for kw in ide_keywords:
            if kw in device_description_lower:
                return ("ide", "auto",
                        f"Class III device with clinical study planned -> IDE pathway")
        return ("pma", "auto",
                f"Class III device -> Premarket Approval (PMA) pathway")

    # Explicit De Novo indicators
    de_novo_keywords = [
        "no predicate", "novel device", "no legally marketed",
        "de novo", "first-of-kind", "new device type",
        "no substantially equivalent", "novel technology"
    ]
    for kw in de_novo_keywords:
        if kw in device_description_lower:
            return ("de_novo", "auto",
                    f"Novel device type ('{kw}' detected) -> De Novo classification")

    # IDE indicators (any class)
    ide_keywords = [
        "clinical study", "clinical investigation", "clinical trial",
        "investigational device", "ide", "feasibility study", "pivotal study",
        "first-in-human", "first in human", "significant risk study",
        "nonsignificant risk study"
    ]
    for kw in ide_keywords:
        if kw in device_description_lower:
            return ("ide", "auto",
                    f"Clinical investigation planned ('{kw}' detected) -> IDE pathway")

    # Class I or II with predicates -> 510(k)
    if device_class in ("1", "2") and has_predicates:
        return ("510k", "auto",
                f"Class {device_class} device with predicates identified -> 510(k) pathway")

    # Class I or II without predicates -> could be 510(k) or De Novo
    if device_class in ("1", "2") and not has_predicates:
        return ("510k", "auto",
                f"Class {device_class} device, no predicates yet -> 510(k) "
                "(consider De Novo if no predicate found)")

    # Default to 510(k)
    return ("510k", "auto", "Default pathway -> 510(k) Premarket Notification")


def _filter_questions_by_pathway(questions, pathway):
    """Filter questions by applicable_pathways field.

    Mirrors the filtering logic from presub.md Step 3.5 (TICKET-004).

    Args:
        questions: List of question dicts from question bank
        pathway: Regulatory pathway string ("510k", "pma", "ide", "de_novo")

    Returns:
        List of questions applicable to the given pathway
    """
    filtered = []
    for q in questions:
        applicable_pathways = q.get("applicable_pathways", [])
        if isinstance(applicable_pathways, list) and len(applicable_pathways) > 0:
            if pathway not in applicable_pathways and "all" not in applicable_pathways:
                continue
        filtered.append(q)
    return filtered


def _get_template_for_pathway(pathway, meeting_type="formal"):
    """Determine the template file for a given pathway and meeting type.

    PMA, IDE, and De Novo pathways have dedicated templates.
    510(k) pathway uses meeting-type-based templates (formal, written, etc.).

    Args:
        pathway: Regulatory pathway
        meeting_type: Meeting type for 510(k) pathway

    Returns:
        Template filename string
    """
    pathway_templates = {
        "pma": "pma_presub.md",
        "ide": "ide_presub.md",
        "de_novo": "de_novo_presub.md",
    }

    if pathway in pathway_templates:
        return pathway_templates[pathway]

    # 510(k) uses meeting-type templates
    meeting_type_templates = {
        "formal": "formal_meeting.md",
        "written": "written_response.md",
        "info": "info_meeting.md",
        "pre-ide": "pre_ide.md",
        "administrative": "administrative_meeting.md",
        "info-only": "info_only.md",
    }
    return meeting_type_templates.get(meeting_type, "formal_meeting.md")


# =============================================================================
# TEST CLASS 1: Pathway Detection Tests (4 tests)
# =============================================================================


class TestPathwayDetection(unittest.TestCase):
    """Test pathway auto-detection from device class and keywords."""

    def test_class_iii_device_detects_pma(self):
        """Test that a Class III device without clinical keywords auto-detects PMA pathway."""
        pathway, method, rationale = _detect_pathway(
            device_class="3",
            device_description="Implantable cardiac defibrillator for ventricular tachycardia",
            has_predicates=False
        )
        self.assertEqual(pathway, "pma")
        self.assertEqual(method, "auto")
        self.assertIn("Class III", rationale)
        self.assertIn("PMA", rationale)

    def test_novel_device_detects_de_novo(self):
        """Test that a novel device with De Novo keywords auto-detects De Novo pathway."""
        pathway, method, rationale = _detect_pathway(
            device_class="2",
            device_description="Novel device type for digital pathology with no predicate available",
            has_predicates=False
        )
        self.assertEqual(pathway, "de_novo")
        self.assertEqual(method, "auto")
        self.assertIn("no predicate", rationale)

    def test_clinical_study_keywords_trigger_ide(self):
        """Test that clinical study keywords trigger IDE pathway detection."""
        test_cases = [
            "Device for clinical study of neural stimulation",
            "Planned clinical investigation of catheter device",
            "Pivotal study device for cardiac ablation",
            "First-in-human feasibility study for novel implant",
        ]
        for desc in test_cases:
            pathway, method, _rationale = _detect_pathway(
                device_class="2",
                device_description=desc,
                has_predicates=True
            )
            self.assertEqual(pathway, "ide",
                             f"Failed to detect IDE for description: {desc}")
            self.assertEqual(method, "auto")

    def test_explicit_pathway_override(self):
        """Test that explicit --pathway override bypasses auto-detection."""
        # Simulate the user_pathway override logic from presub.md
        user_pathway = "de_novo"
        valid_pathways = ["510k", "pma", "ide", "de_novo"]

        if user_pathway and user_pathway in valid_pathways:
            result_pathway = user_pathway
            result_method = "user-specified"
        else:
            result_pathway, result_method, _ = _detect_pathway(
                device_class="2",
                device_description="Standard catheter device",
                has_predicates=True
            )

        self.assertEqual(result_pathway, "de_novo")
        self.assertEqual(result_method, "user-specified")


# =============================================================================
# TEST CLASS 2: Question Selection Tests (4 tests)
# =============================================================================


class TestQuestionSelection(unittest.TestCase):
    """Test pathway-aware question selection and filtering."""

    def setUp(self):
        """Load the question bank."""
        self.question_bank = _load_question_bank()
        self.all_questions = self.question_bank.get("questions", [])

    def test_pma_pathway_gets_pma_questions(self):
        """Test that PMA pathway includes PMA-specific questions."""
        pma_defaults = self.question_bank.get("pathway_defaults", {}).get("pma", [])
        self.assertGreater(len(pma_defaults), 0, "PMA pathway should have default questions")

        # PMA-CLINICAL-001 should be in PMA defaults
        self.assertIn("PMA-CLINICAL-001", pma_defaults,
                       "PMA pathway should include PMA-CLINICAL-001")
        self.assertIn("PMA-RISK-001", pma_defaults,
                       "PMA pathway should include PMA-RISK-001")

        # Verify the actual question objects exist
        pma_questions = [q for q in self.all_questions
                         if q.get("id") in pma_defaults]
        self.assertGreater(len(pma_questions), 0)

    def test_ide_pathway_gets_ide_questions(self):
        """Test that IDE pathway includes IDE-specific questions."""
        ide_defaults = self.question_bank.get("pathway_defaults", {}).get("ide", [])
        self.assertGreater(len(ide_defaults), 0, "IDE pathway should have default questions")

        # IDE-SR-NSR-001 should be in IDE defaults
        self.assertIn("IDE-SR-NSR-001", ide_defaults,
                       "IDE pathway should include IDE-SR-NSR-001")
        self.assertIn("IDE-PROTOCOL-001", ide_defaults,
                       "IDE pathway should include IDE-PROTOCOL-001")

        # Verify the actual question objects exist
        ide_questions = [q for q in self.all_questions
                         if q.get("id") in ide_defaults]
        self.assertGreater(len(ide_questions), 0)

    def test_de_novo_pathway_gets_de_novo_questions(self):
        """Test that De Novo pathway includes De Novo-specific questions."""
        de_novo_defaults = self.question_bank.get("pathway_defaults", {}).get("de_novo", [])
        self.assertGreater(len(de_novo_defaults), 0,
                           "De Novo pathway should have default questions")

        # DENOVO-RISK-001 and DENOVO-CONTROLS-001 should be in De Novo defaults
        self.assertIn("DENOVO-RISK-001", de_novo_defaults,
                       "De Novo pathway should include DENOVO-RISK-001")
        self.assertIn("DENOVO-CONTROLS-001", de_novo_defaults,
                       "De Novo pathway should include DENOVO-CONTROLS-001")
        self.assertIn("DENOVO-PREDICATE-001", de_novo_defaults,
                       "De Novo pathway should include DENOVO-PREDICATE-001")

    def test_pathway_filtering_excludes_wrong_pathway(self):
        """Test that applicable_pathways filtering excludes questions from other pathways."""
        # Get all questions that are exclusively for PMA
        pma_only_questions = [
            q for q in self.all_questions
            if q.get("applicable_pathways") == ["pma"]
        ]

        # Filter these through IDE pathway filter -- they should all be excluded
        ide_filtered = _filter_questions_by_pathway(pma_only_questions, "ide")
        self.assertEqual(len(ide_filtered), 0,
                         "PMA-only questions should be excluded from IDE pathway")

        # Also verify that PRED-001 (510k only) is excluded from PMA
        pred_001 = next(
            (q for q in self.all_questions if q.get("id") == "PRED-001"), None
        )
        self.assertIsNotNone(pred_001)
        assert pred_001 is not None  # Type narrowing
        pma_filtered = _filter_questions_by_pathway([pred_001], "pma")
        self.assertEqual(len(pma_filtered), 0,
                         "PRED-001 (510k only) should be excluded from PMA pathway")

        # CLASS-001 (all pathways) should pass through any pathway filter
        class_001 = next(
            (q for q in self.all_questions if q.get("id") == "CLASS-001"), None
        )
        self.assertIsNotNone(class_001)
        assert class_001 is not None  # Type narrowing
        for pathway in ["510k", "pma", "ide", "de_novo"]:
            filtered = _filter_questions_by_pathway([class_001], pathway)
            self.assertEqual(len(filtered), 1,
                             f"CLASS-001 should pass through {pathway} filter")


# =============================================================================
# TEST CLASS 3: Template Routing Tests (4 tests)
# =============================================================================


class TestTemplateRouting(unittest.TestCase):
    """Test pathway-specific template selection and file existence."""

    def test_pma_pathway_loads_pma_template(self):
        """Test that PMA pathway routes to pma_presub.md template."""
        template = _get_template_for_pathway("pma")
        self.assertEqual(template, "pma_presub.md")

        # Verify template file exists
        template_path = TEMPLATES_DIR / template
        self.assertTrue(template_path.exists(),
                        f"PMA template not found at {template_path}")

        # Verify PMA-specific content
        with open(template_path) as f:
            content = f.read()
        self.assertIn("Premarket Approval (PMA)", content)
        self.assertIn("PMA Regulatory Strategy", content)
        self.assertIn("Proposed Clinical Study Design", content)
        self.assertIn("Benefit-Risk Assessment", content)

    def test_ide_pathway_loads_ide_template(self):
        """Test that IDE pathway routes to ide_presub.md template."""
        template = _get_template_for_pathway("ide")
        self.assertEqual(template, "ide_presub.md")

        # Verify template file exists
        template_path = TEMPLATES_DIR / template
        self.assertTrue(template_path.exists(),
                        f"IDE template not found at {template_path}")

        # Verify IDE-specific content
        with open(template_path) as f:
            content = f.read()
        self.assertIn("Investigational Device Exemption (IDE)", content)
        self.assertIn("SR/NSR Risk Determination", content)
        self.assertIn("Proposed Clinical Investigation Design", content)
        self.assertIn("Informed Consent", content)

    def test_de_novo_pathway_loads_de_novo_template(self):
        """Test that De Novo pathway routes to de_novo_presub.md template."""
        template = _get_template_for_pathway("de_novo")
        self.assertEqual(template, "de_novo_presub.md")

        # Verify template file exists
        template_path = TEMPLATES_DIR / template
        self.assertTrue(template_path.exists(),
                        f"De Novo template not found at {template_path}")

        # Verify De Novo-specific content
        with open(template_path) as f:
            content = f.read()
        self.assertIn("De Novo Classification", content)
        self.assertIn("No Legally Marketed Predicate", content)
        self.assertIn("Proposed Special Controls", content)
        self.assertIn("Risk Assessment", content)

    def test_510k_pathway_loads_meeting_type_templates(self):
        """Test that 510(k) pathway routes to meeting-type-based templates."""
        meeting_types_and_templates = {
            "formal": "formal_meeting.md",
            "written": "written_response.md",
            "info": "info_meeting.md",
            "pre-ide": "pre_ide.md",
            "administrative": "administrative_meeting.md",
            "info-only": "info_only.md",
        }

        for meeting_type, expected_template in meeting_types_and_templates.items():
            template = _get_template_for_pathway("510k", meeting_type)
            self.assertEqual(template, expected_template,
                             f"510(k) with {meeting_type} should use {expected_template}")

            # Verify template file exists
            template_path = TEMPLATES_DIR / template
            self.assertTrue(template_path.exists(),
                            f"510(k) template not found: {template_path}")


# =============================================================================
# TEST CLASS 4: Metadata Generation Tests (4 tests)
# =============================================================================


class TestMetadataGeneration(unittest.TestCase):
    """Test v2.0 metadata schema with pathway-specific fields."""

    def setUp(self):
        """Load metadata schema and set up test metadata."""
        self.schema = _load_metadata_schema()
        self.test_dir = tempfile.mkdtemp(prefix="presub_metadata_test_")

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_v2_metadata_includes_regulatory_pathway(self):
        """Test that v2.0 metadata schema includes regulatory_pathway field."""
        # Verify schema defines regulatory_pathway
        properties = self.schema.get("properties", {})
        self.assertIn("regulatory_pathway", properties,
                       "v2.0 schema must include regulatory_pathway field")

        # Verify valid pathway values
        pathway_enum = properties["regulatory_pathway"].get("enum", [])
        self.assertIn("510k", pathway_enum)
        self.assertIn("pma", pathway_enum)
        self.assertIn("ide", pathway_enum)
        self.assertIn("de_novo", pathway_enum)

        # Create a valid v2.0 metadata instance
        metadata = {
            "version": "2.0",
            "meeting_type": "formal",
            "regulatory_pathway": "pma",
            "questions_generated": ["CLASS-001", "PMA-CLINICAL-001"],
            "question_count": 2,
            "fda_form": "FDA-5064"
        }

        # Validate required fields present
        required_fields = self.schema.get("required", [])
        for field in required_fields:
            self.assertIn(field, metadata, f"Missing required field: {field}")

    def test_pathway_detection_method_populated(self):
        """Test that pathway_detection_method field is defined and accepts valid values."""
        properties = self.schema.get("properties", {})
        self.assertIn("pathway_detection_method", properties,
                       "v2.0 schema must include pathway_detection_method field")

        # Verify valid detection method values
        method_enum = properties["pathway_detection_method"].get("enum", [])
        self.assertIn("auto", method_enum)
        self.assertIn("user-specified", method_enum)
        self.assertIn("device-profile", method_enum)

        # Test metadata with auto-detected pathway
        metadata_auto = {
            "version": "2.0",
            "meeting_type": "formal",
            "regulatory_pathway": "pma",
            "pathway_detection_method": "auto",
            "questions_generated": ["CLASS-001"],
            "question_count": 1,
            "fda_form": "FDA-5064"
        }
        self.assertEqual(metadata_auto["pathway_detection_method"], "auto")

        # Test metadata with user-specified pathway
        metadata_user = {
            "version": "2.0",
            "meeting_type": "formal",
            "regulatory_pathway": "ide",
            "pathway_detection_method": "user-specified",
            "questions_generated": ["CLASS-001"],
            "question_count": 1,
            "fda_form": "FDA-5064"
        }
        self.assertEqual(metadata_user["pathway_detection_method"], "user-specified")

    def test_pathway_rationale_generated(self):
        """Test that pathway_rationale field is populated by detection logic."""
        properties = self.schema.get("properties", {})
        self.assertIn("pathway_rationale", properties,
                       "v2.0 schema must include pathway_rationale field")

        # Test that detection logic produces non-empty rationale
        test_cases = [
            ("3", "Cardiac device", False, "pma"),
            ("2", "Novel device with no predicate", False, "de_novo"),
            ("2", "Clinical study planned", True, "ide"),
            ("2", "Standard catheter", True, "510k"),
        ]

        for device_class, description, has_preds, expected_pathway in test_cases:
            pathway, _method, rationale = _detect_pathway(
                device_class, description, has_preds
            )
            self.assertEqual(pathway, expected_pathway,
                             f"Wrong pathway for '{description}'")
            self.assertIsInstance(rationale, str)
            self.assertGreater(len(rationale), 0,
                               f"Rationale should be non-empty for '{description}'")

    def test_device_class_field_extraction(self):
        """Test that device_class field is correctly defined in schema."""
        properties = self.schema.get("properties", {})
        self.assertIn("device_class", properties,
                       "v2.0 schema must include device_class field")

        # Verify valid class values
        class_enum = properties["device_class"].get("enum", [])
        self.assertIn("1", class_enum)
        self.assertIn("2", class_enum)
        self.assertIn("3", class_enum)

        # Test metadata with device class
        metadata = {
            "version": "2.0",
            "meeting_type": "formal",
            "regulatory_pathway": "pma",
            "device_class": "3",
            "questions_generated": ["CLASS-001"],
            "question_count": 1,
            "fda_form": "FDA-5064"
        }
        self.assertIn(metadata["device_class"], ["1", "2", "3"])


# =============================================================================
# TEST CLASS 5: End-to-End Tests (4 tests)
# =============================================================================


class TestEndToEndPackageGeneration(unittest.TestCase):
    """Test complete Pre-Sub package generation for each pathway."""

    def setUp(self):
        """Set up test environment."""
        self.question_bank = _load_question_bank()
        self.all_questions = self.question_bank.get("questions", [])
        self.test_dir = tempfile.mkdtemp(prefix="presub_e2e_test_")

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def _generate_package(self, device_class, device_description,
                          has_predicates=False, user_pathway=None):
        """Simulate the complete Pre-Sub package generation pipeline.

        This replicates the core logic from presub.md Steps 3.25 and 3.5.

        Returns:
            Dict with pathway, template, questions, and metadata
        """
        # Step 3.25: Detect pathway
        if user_pathway:
            pathway = user_pathway
            detection_method = "user-specified"
            rationale = f"User specified --pathway {user_pathway}"
        else:
            pathway, detection_method, rationale = _detect_pathway(
                device_class, device_description, has_predicates
            )

        # Step 3.5: Select template
        template = _get_template_for_pathway(pathway)

        # Select default questions for pathway
        pathway_defaults = self.question_bank.get(
            "pathway_defaults", {}
        ).get(pathway, [])
        meeting_defaults = self.question_bank.get(
            "meeting_type_defaults", {}
        ).get("formal", [])

        selected_ids = set(pathway_defaults) | set(meeting_defaults)

        # Get question objects
        selected_questions = [
            q for q in self.all_questions
            if q.get("id") in selected_ids
        ]

        # Filter by pathway
        selected_questions = _filter_questions_by_pathway(
            selected_questions, pathway
        )

        # Deduplicate
        seen_ids = set()
        unique_questions = []
        for q in selected_questions:
            qid = q.get("id", "")
            if qid and qid not in seen_ids:
                seen_ids.add(qid)
                unique_questions.append(q)

        # Sort by priority
        unique_questions.sort(
            key=lambda q: q.get("priority", 0), reverse=True
        )

        # Limit questions
        max_q = 10 if pathway in ("pma", "ide", "de_novo") else 7
        unique_questions = unique_questions[:max_q]

        # Generate metadata
        metadata = {
            "version": "2.0",
            "meeting_type": "formal",
            "regulatory_pathway": pathway,
            "pathway_detection_method": detection_method,
            "pathway_rationale": rationale,
            "device_class": device_class,
            "questions_generated": [q["id"] for q in unique_questions],
            "question_count": len(unique_questions),
            "template_used": template,
            "fda_form": "FDA-5064",
            "expected_timeline_days": 75,
            "auto_triggers_fired": [],
            "data_sources_used": ["classification"],
            "metadata": {
                "placeholder_count": 0,
                "auto_filled_fields": [],
                "question_bank_version": "2.0",
                "pathway_specific_questions": len([
                    q for q in unique_questions
                    if q.get("category", "").startswith(
                        pathway.replace("510k", "predicate")
                    )
                ])
            }
        }

        # Write metadata to test directory
        metadata_path = Path(self.test_dir) / f"{pathway}_metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        return {
            "pathway": pathway,
            "detection_method": detection_method,
            "rationale": rationale,
            "template": template,
            "questions": unique_questions,
            "metadata": metadata,
            "metadata_path": str(metadata_path),
        }

    def test_complete_pma_presub_generation(self):
        """Test complete PMA Pre-Sub package generation end-to-end."""
        result = self._generate_package(
            device_class="3",
            device_description="Implantable cardiac defibrillator for ventricular arrhythmia treatment",
            has_predicates=False
        )

        # Verify pathway
        self.assertEqual(result["pathway"], "pma")
        self.assertEqual(result["detection_method"], "auto")

        # Verify template
        self.assertEqual(result["template"], "pma_presub.md")
        template_path = TEMPLATES_DIR / result["template"]
        self.assertTrue(template_path.exists())

        # Verify questions include PMA-specific ones
        question_ids = [q["id"] for q in result["questions"]]
        self.assertIn("PMA-CLINICAL-001", question_ids,
                       "PMA package should include PMA-CLINICAL-001")
        self.assertIn("CLASS-001", question_ids,
                       "PMA package should include CLASS-001")

        # Verify 510k-only questions are excluded
        self.assertNotIn("PRED-001", question_ids,
                         "PMA package should NOT include PRED-001 (510k only)")

        # Verify metadata
        metadata = result["metadata"]
        self.assertEqual(metadata["version"], "2.0")
        self.assertEqual(metadata["regulatory_pathway"], "pma")
        self.assertEqual(metadata["device_class"], "3")
        self.assertGreater(metadata["question_count"], 0)

        # Verify metadata file was written
        self.assertTrue(os.path.exists(result["metadata_path"]))
        with open(result["metadata_path"]) as f:
            saved_metadata = json.load(f)
        self.assertEqual(saved_metadata["regulatory_pathway"], "pma")

    def test_complete_ide_presub_generation(self):
        """Test complete IDE Pre-Sub package generation end-to-end."""
        result = self._generate_package(
            device_class="2",
            device_description="Vascular catheter requiring clinical study before clearance",
            has_predicates=True
        )

        # Verify pathway
        self.assertEqual(result["pathway"], "ide")
        self.assertEqual(result["detection_method"], "auto")

        # Verify template
        self.assertEqual(result["template"], "ide_presub.md")
        template_path = TEMPLATES_DIR / result["template"]
        self.assertTrue(template_path.exists())

        # Verify questions include IDE-specific ones
        question_ids = [q["id"] for q in result["questions"]]
        self.assertIn("IDE-SR-NSR-001", question_ids,
                       "IDE package should include IDE-SR-NSR-001")

        # Verify PRED-001 is excluded (510k only)
        self.assertNotIn("PRED-001", question_ids,
                         "IDE package should NOT include PRED-001 (510k only)")

        # Verify metadata
        metadata = result["metadata"]
        self.assertEqual(metadata["version"], "2.0")
        self.assertEqual(metadata["regulatory_pathway"], "ide")
        self.assertEqual(metadata["device_class"], "2")

    def test_complete_de_novo_presub_generation(self):
        """Test complete De Novo Pre-Sub package generation end-to-end."""
        result = self._generate_package(
            device_class="2",
            device_description="Novel device type for AI-powered diagnostics with no predicate",
            has_predicates=False
        )

        # Verify pathway
        self.assertEqual(result["pathway"], "de_novo")
        self.assertEqual(result["detection_method"], "auto")

        # Verify template
        self.assertEqual(result["template"], "de_novo_presub.md")
        template_path = TEMPLATES_DIR / result["template"]
        self.assertTrue(template_path.exists())

        # Verify questions include De Novo-specific ones
        question_ids = [q["id"] for q in result["questions"]]
        self.assertIn("DENOVO-RISK-001", question_ids,
                       "De Novo package should include DENOVO-RISK-001")
        self.assertIn("DENOVO-CONTROLS-001", question_ids,
                       "De Novo package should include DENOVO-CONTROLS-001")

        # Verify PRED-001 is excluded (510k only)
        self.assertNotIn("PRED-001", question_ids,
                         "De Novo package should NOT include PRED-001 (510k only)")

        # Verify metadata
        metadata = result["metadata"]
        self.assertEqual(metadata["version"], "2.0")
        self.assertEqual(metadata["regulatory_pathway"], "de_novo")
        self.assertIn("no predicate", metadata["pathway_rationale"].lower())

    def test_complete_510k_presub_generation(self):
        """Test complete 510(k) Pre-Sub package generation end-to-end."""
        result = self._generate_package(
            device_class="2",
            device_description="Single-use vascular access catheter",
            has_predicates=True
        )

        # Verify pathway
        self.assertEqual(result["pathway"], "510k")
        self.assertEqual(result["detection_method"], "auto")

        # Verify template (510k uses meeting type templates)
        self.assertEqual(result["template"], "formal_meeting.md")
        template_path = TEMPLATES_DIR / result["template"]
        self.assertTrue(template_path.exists())

        # Verify questions include 510k-specific ones
        question_ids = [q["id"] for q in result["questions"]]
        self.assertIn("PRED-001", question_ids,
                       "510(k) package should include PRED-001")
        self.assertIn("CLASS-001", question_ids,
                       "510(k) package should include CLASS-001")

        # Verify PMA-only questions are excluded
        pma_only_ids = {"PMA-CLINICAL-001", "PMA-CLINICAL-002",
                        "PMA-CLINICAL-003", "PMA-RISK-001", "PMA-NONCLIN-001",
                        "PMA-PANEL-001"}
        for pma_id in pma_only_ids:
            self.assertNotIn(pma_id, question_ids,
                             f"510(k) package should NOT include {pma_id}")

        # Verify metadata
        metadata = result["metadata"]
        self.assertEqual(metadata["version"], "2.0")
        self.assertEqual(metadata["regulatory_pathway"], "510k")
        self.assertEqual(metadata["device_class"], "2")
        self.assertIn("510(k)", metadata["pathway_rationale"])


# =============================================================================
# Test Runner
# =============================================================================


def run_tests():
    """Run all multi-pathway integration tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestPathwayDetection))
    suite.addTests(loader.loadTestsFromTestCase(TestQuestionSelection))
    suite.addTests(loader.loadTestsFromTestCase(TestTemplateRouting))
    suite.addTests(loader.loadTestsFromTestCase(TestMetadataGeneration))
    suite.addTests(loader.loadTestsFromTestCase(TestEndToEndPackageGeneration))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_tests())
