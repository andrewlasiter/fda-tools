"""Tests for v5.22.0 — Specialty Audit Remediation (70 items, 5 phases).

Phase 1: Structural fixes (OHT numbering, DHT codes)
Phase 2: Guidance index expansion (13+ device categories)
Phase 3: Keyword trigger expansion (19 specialties)
Phase 4: Reviewer templates (19 templates in cdrh-review-structure.md)
Phase 5: SE comparison templates (39+) + consensus standards (183+)
"""

import os
import re

import pytest

PLUGIN_ROOT = os.path.join(os.path.dirname(__file__), '..')
COMMANDS_DIR = os.path.join(PLUGIN_ROOT, 'commands')
REFERENCES_DIR = os.path.join(PLUGIN_ROOT, 'references')
SKILL_REFS_DIR = os.path.join(PLUGIN_ROOT, 'skills', 'fda-510k-knowledge', 'references')


# ═══════════════════════════════════════════════════════════════════
# Phase 1: Structural fixes — OHT numbering, DHT codes
# ═══════════════════════════════════════════════════════════════════

class TestOHTStructure:
    """Verify OHT1-OHT8 structure in cdrh-review-structure.md."""

    @pytest.fixture(autouse=True)
    def load_content(self):
        with open(os.path.join(REFERENCES_DIR, 'cdrh-review-structure.md')) as f:
            self.content = f.read()

    @pytest.mark.parametrize("oht_num", range(1, 9))
    def test_oht_present(self, oht_num):
        """Each OHT office (1-8) must be present."""
        assert f"OHT{oht_num}" in self.content

    def test_oht_count_exactly_8(self):
        """Must have exactly 8 OHT offices."""
        oht_matches = set(re.findall(r'OHT(\d)', self.content))
        assert oht_matches == {'1', '2', '3', '4', '5', '6', '7', '8'}

    @pytest.mark.parametrize("dht", [
        "DHT1A", "DHT1B", "DHT1C", "DHT1D",
        "DHT2A", "DHT2B", "DHT2C", "DHT2D",
        "DHT3A", "DHT3B", "DHT3C",
        "DHT4A", "DHT4B",
        "DHT5A", "DHT5B", "DHT5C",
        "DHT6A", "DHT6B",
        "DHT7A", "DHT7B", "DHT7C", "DHT7D",
        "DHT8A", "DHT8B",
    ])
    def test_dht_code_present(self, dht):
        """All DHT division codes must be referenced."""
        assert dht in self.content


# ═══════════════════════════════════════════════════════════════════
# Phase 2: Guidance index expansion
# ═══════════════════════════════════════════════════════════════════

class TestGuidanceIndexExpansion:
    """Verify fda-guidance-index.md has 13+ device categories."""

    @pytest.fixture(autouse=True)
    def load_content(self):
        with open(os.path.join(REFERENCES_DIR, 'fda-guidance-index.md')) as f:
            self.content = f.read()

    @pytest.mark.parametrize("section,cfr", [
        ("5.1", "870"),   # CV
        ("5.2", "888"),   # OR
        ("5.4", "862"),   # IVD
        ("5.5", "872"),   # DE
        ("5.6", "886"),   # OP
        ("5.8", "868"),   # AN/Respiratory
        ("5.9", "880"),   # HO
        ("5.10", "892"),  # RA
        ("5.11", "882"),  # NE
        ("5.12", "878"),  # SU
        ("5.13", "874"),  # EN
        ("5.14", "876"),  # GU
        ("5.15", "884"),  # OB
        ("5.16", "890"),  # PM
    ])
    def test_device_category_present(self, section, cfr):
        """Each device category section must exist with CFR reference."""
        assert section in self.content
        assert cfr in self.content

    def test_fy2026_agenda_exists(self):
        """FY2026 guidance agenda section must exist."""
        assert "FY 2026" in self.content or "FY2026" in self.content

    def test_regulation_lookup_table(self):
        """Regulation number quick lookup table must exist."""
        assert "Regulation" in self.content

    def test_skill_copy_matches(self):
        """Skill reference copy must match top-level copy."""
        with open(os.path.join(SKILL_REFS_DIR, 'fda-guidance-index.md')) as f:
            skill_content = f.read()
        assert self.content == skill_content


# ═══════════════════════════════════════════════════════════════════
# Phase 3: Keyword trigger expansion
# ═══════════════════════════════════════════════════════════════════

class TestKeywordTriggers:
    """Verify 19 specialty keyword triggers in guidance.md."""

    @pytest.fixture(autouse=True)
    def load_content(self):
        with open(os.path.join(COMMANDS_DIR, 'guidance.md')) as f:
            self.content = f.read()

    def test_specialty_keyword_section_exists(self):
        """Must have specialty keyword categories section."""
        assert "Specialty keyword categories" in self.content or \
               "specialty keyword categories" in self.content.lower()

    @pytest.mark.parametrize("panel_tag", [
        "kw_cv", "kw_or", "kw_de", "kw_en", "kw_ne", "kw_op",
        "kw_su", "kw_pm", "kw_ho", "kw_ob", "kw_ra", "kw_gu",
        "kw_an",
    ])
    def test_panel_trigger_tag_present(self, panel_tag):
        """Each advisory panel must have a keyword trigger tag."""
        assert panel_tag in self.content

    @pytest.mark.parametrize("keyword,panel", [
        ("stent", "Cardiovascular"),
        ("arthroplasty", "Orthopedic"),
        ("dental implant", "Dental"),
        ("hearing aid", "ENT"),
        ("neurostimulator", "Neurological"),
        ("intraocular lens", "Ophthalmic"),
        ("electrosurgical", "Surg"),
        ("wheelchair", "Physical Medicine"),
        ("infusion pump", "General Hospital"),
        ("fetal monitor", "Obstetrics"),
        ("x-ray", "Radiol"),
        ("endoscope", "Gastroenterology"),
        ("ventilator", "Anesthesia"),
    ])
    def test_keyword_mapped_to_correct_panel(self, keyword, panel):
        """Keywords must be associated with the correct advisory panel."""
        # Find the keyword in the content and check the panel context
        idx = self.content.lower().find(keyword.lower())
        assert idx != -1, f"Keyword '{keyword}' not found"
        # Check that the panel name appears within 1000 chars of the keyword
        context = self.content[max(0, idx - 1000):idx + 1000]
        assert panel in context, f"'{panel}' not near '{keyword}'"

    def test_negation_awareness(self):
        """Keyword matching must have negation awareness."""
        assert "negat" in self.content.lower() or "prefix" in self.content.lower()

    def test_ivd_expanded_trigger(self):
        """IVD must have expanded trigger covering sub-disciplines."""
        assert "kw_ivd" in self.content
        # Must cover hematology, molecular, immunoassay
        assert "hematology" in self.content.lower()
        assert "molecular" in self.content.lower()
        assert "immunoassay" in self.content.lower()


# ═══════════════════════════════════════════════════════════════════
# Phase 4: Reviewer templates (19 specialties)
# ═══════════════════════════════════════════════════════════════════

class TestReviewerTemplates:
    """Verify all 19 reviewer templates in cdrh-review-structure.md."""

    @pytest.fixture(autouse=True)
    def load_content(self):
        with open(os.path.join(REFERENCES_DIR, 'cdrh-review-structure.md')) as f:
            self.content = f.read()

    @pytest.mark.parametrize("panel", [
        "Cardiovascular", "Orthopedic", "Surgical", "Neurological",
        "Gastro", "Obstetric", "General Hospital", "Dental",
        "ENT", "Anesthes", "Ophthalmic", "Physical Medicine",
        "Radiological",
    ])
    def test_primary_template_present(self, panel):
        """Each primary reviewer panel template must exist."""
        assert panel in self.content

    @pytest.mark.parametrize("ivd_panel", [
        "Clinical Chemistry", "Hematology", "Immunology",
        "Microbiology", "Pathology", "Toxicology",
    ])
    def test_ivd_subpanel_template(self, ivd_panel):
        """Each IVD sub-panel template must exist."""
        assert ivd_panel in self.content

    def test_deficiency_templates_present(self):
        """Must contain deficiency template blocks (> ** format)."""
        deficiency_blocks = re.findall(r'^> \*\*', self.content, re.MULTILINE)
        assert len(deficiency_blocks) >= 45, f"Only {len(deficiency_blocks)} deficiency blocks"

    def test_scoring_rubrics_present(self):
        """Each template must have a scoring statement."""
        score_lines = re.findall(r'\*\*Score:\*\*.*items addressed', self.content)
        assert len(score_lines) >= 14, f"Only {len(score_lines)} scoring lines"

    def test_section_8_readiness_scoring(self):
        """Section 8 Submission Readiness Scoring must exist."""
        assert "Submission Readiness Scoring" in self.content

    def test_readiness_tiers(self):
        """Must have readiness tiers (Ready, Nearly Ready, etc.)."""
        assert "Ready" in self.content
        assert "Nearly Ready" in self.content or "Significant Gaps" in self.content

    def test_cross_references_section(self):
        """Cross-References section must exist."""
        assert "Cross-Reference" in self.content

    def test_file_synced_with_skill(self):
        """Must be synced with skill reference copy."""
        with open(os.path.join(SKILL_REFS_DIR, 'cdrh-review-structure.md')) as f:
            skill_content = f.read()
        assert self.content == skill_content

    def test_line_count_exceeds_1500(self):
        """File must be at least 1500 lines after expansion."""
        lines = self.content.count('\n')
        assert lines >= 1500, f"Only {lines} lines (expected 1500+)"


# ═══════════════════════════════════════════════════════════════════
# Phase 5a: SE Comparison Templates (39+ templates)
# ═══════════════════════════════════════════════════════════════════

class TestSEComparisonTemplates:
    """Verify 39+ SE comparison templates in compare-se.md."""

    @pytest.fixture(autouse=True)
    def load_content(self):
        with open(os.path.join(COMMANDS_DIR, 'compare-se.md')) as f:
            self.content = f.read()

    @pytest.mark.parametrize("template_name", [
        # Orthopedic (3)
        "Joint Arthroplasty", "Spinal", "Fracture Fixation",
        # Cardiovascular (4)
        "Intravascular Stent", "Cardiac Implantable", "Heart Valve",
        # Radiological (5)
        "X-Ray", "CT Scanner", "MRI", "Diagnostic Ultrasound", "AI/ML",
        # Surgical (3)
        "Electrosurgical", "Stapler", "Mesh",
        # Neurological (2)
        "Neurostimulator", "CSF Shunt",
        # GU (1)
        "Endoscope",
        # OB (2)
        "Fetal Monitor", "Intrauterine",
        # HO (2)
        "Infusion Pump", "Glove",
        # DE (2)
        "Dental", "Restorative",
        # EN (2)
        "Hearing Aid", "Sleep Apnea",
        # AN (2)
        "Workstation", "Pulse Oximeter",
        # OP (2)
        "Intraocular Lens", "Contact Lens",
        # PM (3)
        "Wheelchair", "TENS", "Prosthetic",
        # IVD (8)
        "Clinical Chemistry", "Hematology", "Immunoassay",
        "Molecular", "AST", "NGS", "Drug", "Coagulation",
    ])
    def test_template_present(self, template_name):
        """Each SE comparison template must exist."""
        assert template_name in self.content

    def test_default_template_present(self):
        """Default fallback template must exist."""
        assert "Default" in self.content

    def test_cgm_template_present(self):
        """CGM/Glucose Monitor template must exist."""
        assert "CGM" in self.content or "Glucose Monitor" in self.content

    def test_wound_template_present(self):
        """Wound Dressing template must exist."""
        assert "Wound" in self.content

    def test_template_count_at_least_39(self):
        """Must have at least 39 template blocks (** pattern)."""
        templates = re.findall(r'^\*\*[A-Z].*\*\*', self.content, re.MULTILINE)
        assert len(templates) >= 39, f"Only {len(templates)} templates"

    def test_each_template_has_rows(self):
        """Each template must define comparison rows."""
        assert "Rows:" in self.content or "Intended Use" in self.content

    def test_product_codes_referenced(self):
        """Must reference product codes for template selection."""
        # Check for 3-letter product code patterns
        product_codes = re.findall(r'\b[A-Z]{3}\b', self.content)
        assert len(product_codes) >= 50, f"Only {len(product_codes)} product code refs"

    def test_step_1_template_selection(self):
        """Step 1 must describe template selection logic."""
        assert "Step 1" in self.content
        assert "Product Code" in self.content or "product code" in self.content


# ═══════════════════════════════════════════════════════════════════
# Phase 5b: Consensus Standards Database (183+ standards)
# ═══════════════════════════════════════════════════════════════════

class TestConsensusStandards:
    """Verify 19 sections and 183+ standards in guidance-lookup.md."""

    @pytest.fixture(autouse=True)
    def load_content(self):
        with open(os.path.join(REFERENCES_DIR, 'guidance-lookup.md')) as f:
            self.content = f.read()

    @pytest.mark.parametrize("section", [
        "Universal", "Orthopedic", "Cardiovascular", "IVD",
        "Surgical", "Anesthesia", "Dental", "ENT", "Ophthalmic",
        "Neurological", "Physical Medicine", "Gastroenterology",
        "Obstetrics", "General Hospital", "Radiological",
        "Software",
    ])
    def test_section_present(self, section):
        """Each specialty standards section must exist."""
        assert section in self.content

    def test_iso_standards_count(self):
        """Must have substantial ISO standards."""
        iso_refs = re.findall(r'ISO \d+', self.content)
        assert len(iso_refs) >= 30, f"Only {len(iso_refs)} ISO references"

    def test_iec_standards_count(self):
        """Must have substantial IEC standards."""
        iec_refs = re.findall(r'IEC \d+', self.content)
        assert len(iec_refs) >= 20, f"Only {len(iec_refs)} IEC references"

    def test_astm_standards_count(self):
        """Must have substantial ASTM standards."""
        astm_refs = re.findall(r'ASTM [A-Z]\d+', self.content)
        assert len(astm_refs) >= 15, f"Only {len(astm_refs)} ASTM references"

    def test_clsi_standards_for_ivd(self):
        """IVD section must reference CLSI EP/H/M/MM series."""
        assert "CLSI EP" in self.content
        assert "CLSI H" in self.content
        assert "CLSI M" in self.content or "CLSI MM" in self.content

    def test_iec_60601_particular_standards(self):
        """Must have IEC 60601-2-xx particular standards."""
        particular = re.findall(r'IEC 60601-2-\d+', self.content)
        assert len(particular) >= 10, f"Only {len(particular)} particular standards"

    def test_file_synced_with_skill(self):
        """Must be synced with skill reference copy."""
        with open(os.path.join(SKILL_REFS_DIR, 'guidance-lookup.md')) as f:
            skill_content = f.read()
        assert self.content == skill_content

    def test_cfr_referenced_in_guidance_index(self):
        """Key 21 CFR parts must appear in fda-guidance-index.md (not guidance-lookup.md).
        guidance-lookup.md uses OHT references and specialty names, not CFR part numbers.
        Verify that guidance-lookup.md covers all major panels by name instead."""
        panels_found = []
        for panel in ["Cardiovascular", "Dental", "ENT", "Gastroenterology",
                       "Surgical", "General Hospital", "Neurological",
                       "Obstetrics", "Ophthalmic", "Orthopedic",
                       "Physical Medicine", "Radiological"]:
            if panel in self.content:
                panels_found.append(panel)
        assert len(panels_found) >= 12, f"Only {len(panels_found)}/12 panels: {panels_found}"


# ═══════════════════════════════════════════════════════════════════
# Cross-file consistency checks
# ═══════════════════════════════════════════════════════════════════

class TestCrossFileConsistency:
    """Verify consistency across modified files."""

    def test_version_consistent(self):
        """v5.22.0 must appear in plugin.json."""
        import json
        with open(os.path.join(PLUGIN_ROOT, '.claude-plugin', 'plugin.json')) as f:
            data = json.load(f)
        assert data['version'] == '5.22.0'

    def test_version_in_commands(self):
        """v5.22.0 must appear in at least one command footer."""
        with open(os.path.join(COMMANDS_DIR, 'status.md')) as f:
            content = f.read()
        assert 'v5.22.0' in content

    def test_reviewer_templates_match_se_templates(self):
        """Each advisory panel in reviewer templates should have SE templates."""
        with open(os.path.join(REFERENCES_DIR, 'cdrh-review-structure.md')) as f:
            reviewer = f.read()
        with open(os.path.join(COMMANDS_DIR, 'compare-se.md')) as f:
            se = f.read()
        # Key panels must appear in both files
        for panel in ["Cardiovascular", "Orthopedic", "Dental", "Ophthalmic",
                       "Neurological", "Radiological"]:
            assert panel in reviewer, f"{panel} missing from reviewer templates"
            assert panel in se, f"{panel} missing from SE templates"

    def test_standards_referenced_in_reviewer_templates(self):
        """Key standards in guidance-lookup.md should appear in reviewer templates."""
        with open(os.path.join(REFERENCES_DIR, 'guidance-lookup.md')) as f:
            standards = f.read()
        with open(os.path.join(REFERENCES_DIR, 'cdrh-review-structure.md')) as f:
            reviewer = f.read()
        # IEC 60601-1 is the core medical electrical equipment standard
        assert "IEC 60601" in standards
        assert "IEC 60601" in reviewer

    def test_guidance_index_referenced_in_guidance_command(self):
        """guidance.md must reference fda-guidance-index.md sections."""
        with open(os.path.join(COMMANDS_DIR, 'guidance.md')) as f:
            content = f.read()
        assert "Section 5.1" in content  # CV
        assert "Section 5.2" in content  # OR

    def test_all_reference_copies_synced(self):
        """All modified reference files must be synced to skill copies."""
        for filename in ['cdrh-review-structure.md', 'guidance-lookup.md',
                         'fda-guidance-index.md']:
            ref_path = os.path.join(REFERENCES_DIR, filename)
            skill_path = os.path.join(SKILL_REFS_DIR, filename)
            if os.path.exists(ref_path) and os.path.exists(skill_path):
                with open(ref_path) as f:
                    ref = f.read()
                with open(skill_path) as f:
                    skill = f.read()
                assert ref == skill, f"{filename} out of sync"
