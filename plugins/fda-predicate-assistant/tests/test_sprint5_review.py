"""Sprint 5 Tests — 8-Agent Review Remediation (v5.18.0)

Tests for Sprint 5 items implemented from SPRINT5_8AGENT_REVIEW.md:
- Item 4 (DP-C3): Incremental extraction merge in predicate_extractor.py
- Item 7 (RS-C1/C2/C3): Reprocessing/Packaging/Materials reviewer templates
- Item 8 (SA-C1): Consistency check count alignment (11 checks)
- Item 9 (DP-H2): Merge column header guidance in data-pipeline-manager
- Item 14 (SW-C3, SA-H1): Section numbering cross-reference

Also validates that items already complete in v5.16.0 remain correct.
"""

import os
import re
import csv
import tempfile

import pytest

# Paths
PLUGIN_ROOT = os.path.join(os.path.dirname(__file__), '..')
SCRIPTS_DIR = os.path.join(PLUGIN_ROOT, 'scripts')
COMMANDS_DIR = os.path.join(PLUGIN_ROOT, 'commands')
AGENTS_DIR = os.path.join(PLUGIN_ROOT, 'agents')
REFERENCES_DIR = os.path.join(PLUGIN_ROOT, 'references')
SKILL_REFS_DIR = os.path.join(PLUGIN_ROOT, 'skills', 'fda-510k-knowledge', 'references')


# ===== Item 4: Incremental Extraction Merge =====

class TestIncrementalMerge:
    """predicate_extractor.py must support true incremental merge."""

    @pytest.fixture
    def extractor_content(self):
        with open(os.path.join(SCRIPTS_DIR, 'predicate_extractor.py')) as f:
            return f.read()

    def test_incremental_flag_exists(self, extractor_content):
        """--incremental CLI flag must exist."""
        assert '--incremental' in extractor_content

    def test_existing_rows_variable(self, extractor_content):
        """Must track existing rows for merge."""
        assert 'existing_rows' in extractor_content

    def test_merge_logic_present(self, extractor_content):
        """Must contain merge logic for incremental mode."""
        assert 'padded_existing' in extractor_content

    def test_incremental_overwrites_original(self, extractor_content):
        """In incremental mode, must write back to original output.csv (not output_1.csv)."""
        # The code should set filename to the original path, not get_available_filename
        assert "Incremental mode: merged" in extractor_content

    def test_column_repadding(self, extractor_content):
        """Must repad rows when column counts differ between old and new data."""
        assert 'max_predicates' in extractor_content
        assert 'old_pred_count' in extractor_content

    def test_supplement_merge(self, extractor_content):
        """Must deduplicate supplement data during incremental merge."""
        assert 'existing_supplements' in extractor_content

    def test_incremental_summary_stats(self, extractor_content):
        """Summary must show previously extracted and total row counts."""
        assert 'Previously extracted' in extractor_content
        assert 'Total rows in output' in extractor_content


# ===== Item 7: Reviewer Templates =====

class TestReviewerTemplates:
    """review-simulator.md and cdrh-review-structure.md must have all reviewer types."""

    @pytest.fixture
    def review_sim_content(self):
        with open(os.path.join(AGENTS_DIR, 'review-simulator.md')) as f:
            return f.read()

    @pytest.fixture
    def cdrh_content(self):
        with open(os.path.join(REFERENCES_DIR, 'cdrh-review-structure.md')) as f:
            return f.read()

    # Review Simulator: Reprocessing
    def test_reprocessing_template_in_simulator(self, review_sim_content):
        """Reprocessing reviewer evaluation template must exist."""
        assert '**Reprocessing**' in review_sim_content
        assert 'AAMI TIR30' in review_sim_content

    def test_reprocessing_cleaning_validation(self, review_sim_content):
        """Must check cleaning validation."""
        assert 'Cleaning validation' in review_sim_content

    def test_reprocessing_simulated_use(self, review_sim_content):
        """Must check simulated-use testing."""
        assert 'Simulated-use' in review_sim_content or 'simulated-use' in review_sim_content

    # Review Simulator: Packaging
    def test_packaging_template_in_simulator(self, review_sim_content):
        """Packaging reviewer evaluation template must exist."""
        assert '**Packaging**' in review_sim_content
        assert 'ISO 11607' in review_sim_content

    def test_packaging_accelerated_aging(self, review_sim_content):
        """Must reference ASTM F1980 for accelerated aging."""
        assert 'ASTM F1980' in review_sim_content

    def test_packaging_seal_strength(self, review_sim_content):
        """Must reference seal strength testing."""
        assert 'seal strength' in review_sim_content.lower()

    def test_packaging_distribution_simulation(self, review_sim_content):
        """Must reference ASTM D4169 for distribution simulation."""
        assert 'ASTM D4169' in review_sim_content

    # Review Simulator: Materials
    def test_materials_template_in_simulator(self, review_sim_content):
        """Materials reviewer evaluation template must exist."""
        assert '**Materials**' in review_sim_content
        assert 'ISO 10993-18' in review_sim_content

    def test_materials_3d_printing(self, review_sim_content):
        """Must address 3D-printed device requirements."""
        assert '3D-print' in review_sim_content or '3d-print' in review_sim_content

    def test_materials_extractables_leachables(self, review_sim_content):
        """Must reference E&L analysis."""
        assert 'extractable' in review_sim_content.lower()
        assert 'leachable' in review_sim_content.lower()

    # CDRH Review Structure: Reviewer entries
    def test_reprocessing_in_specialist_table(self, cdrh_content):
        """Reprocessing Reviewer must be in specialist table."""
        assert '| **Reprocessing Reviewer**' in cdrh_content

    def test_packaging_in_specialist_table(self, cdrh_content):
        """Packaging Reviewer must be in specialist table."""
        assert '| **Packaging Reviewer**' in cdrh_content

    def test_materials_in_specialist_table(self, cdrh_content):
        """Materials Reviewer must be in specialist table."""
        assert '| **Materials Reviewer**' in cdrh_content

    # CDRH: Auto-detection logic
    def test_materials_auto_detection(self, cdrh_content):
        """Auto-detection must include Materials reviewer keywords."""
        assert 'team.append("Materials")' in cdrh_content

    def test_packaging_auto_detection(self, cdrh_content):
        """Auto-detection must include Packaging reviewer trigger."""
        assert 'team.append("Packaging")' in cdrh_content

    # CDRH: Deficiency templates
    def test_reprocessing_deficiency_template(self, cdrh_content):
        """Reprocessing reviewer must have deficiency template."""
        assert 'Reprocessing Reviewer' in cdrh_content
        assert 'reprocessing validation data' in cdrh_content

    def test_packaging_deficiency_template(self, cdrh_content):
        """Packaging reviewer must have deficiency template."""
        assert 'Packaging Reviewer' in cdrh_content
        assert 'packaging validation data' in cdrh_content

    def test_materials_deficiency_template(self, cdrh_content):
        """Materials reviewer must have deficiency template."""
        assert 'Materials Reviewer' in cdrh_content
        assert 'chemical characterization' in cdrh_content


# ===== Item 8: Consistency Check Count Alignment =====

class TestConsistencyCheckAlignment:
    """consistency.md and submission-assembler.md must agree on check count."""

    @pytest.fixture
    def consistency_content(self):
        with open(os.path.join(COMMANDS_DIR, 'consistency.md')) as f:
            return f.read()

    @pytest.fixture
    def assembler_content(self):
        with open(os.path.join(AGENTS_DIR, 'submission-assembler.md')) as f:
            return f.read()

    def test_consistency_has_17_checks(self, consistency_content):
        """consistency.md must define 17 checks."""
        checks = re.findall(r'### Check (\d+):', consistency_content)
        assert len(checks) == 17, f"Expected 17 checks, found {len(checks)}: {checks}"

    def test_check_11_is_section_map(self, consistency_content):
        """Check 11 must be eSTAR Section Map Alignment."""
        assert 'Check 11: eSTAR Section Map Alignment' in consistency_content

    def test_assembler_says_17_checks(self, assembler_content):
        """Assembler must reference 17 consistency checks."""
        assert '17 checks' in assembler_content or '17 consistency checks' in assembler_content

    def test_assembler_progress_matches(self, assembler_content):
        """Assembler progress checkpoint must reference correct check count."""
        assert 'Passed {N}/17 checks' in assembler_content

    def test_consistency_report_has_17_rows(self, consistency_content):
        """Report template must show 17 check rows."""
        # Count rows in the results table that have numbered checks
        table_rows = re.findall(r'\|\s*\d+\s*\|', consistency_content)
        assert len(table_rows) >= 17, f"Expected 17+ table rows, found {len(table_rows)}"

    def test_check_11_has_section_map_entries(self, consistency_content):
        """Check 11 must list draft-to-section mappings."""
        assert 'draft_cover-letter.md' in consistency_content
        assert '01_CoverLetter/' in consistency_content
        assert 'draft_human-factors.md' in consistency_content
        assert '17_HumanFactors/' in consistency_content


# ===== Item 9: Merge Column Header Guidance =====

class TestMergeColumnHeaders:
    """data-pipeline-manager.md must document correct CSV column headers."""

    @pytest.fixture
    def pipeline_content(self):
        with open(os.path.join(AGENTS_DIR, 'data-pipeline-manager.md')) as f:
            return f.read()

    def test_column_header_reference(self, pipeline_content):
        """Must include column header reference for merge."""
        assert '510(k), Product Code, Predicate 1' in pipeline_content

    def test_warns_against_generic_col_names(self, pipeline_content):
        """Must warn against using generic column names like Col3."""
        assert 'Col3' in pipeline_content
        assert 'Never use generic column names' in pipeline_content

    def test_predicate_column_format(self, pipeline_content):
        """Must specify Predicate N format."""
        assert 'Predicate 1' in pipeline_content
        assert 'Predicate N' in pipeline_content

    def test_reference_device_column_format(self, pipeline_content):
        """Must specify Reference Device M format."""
        assert 'Reference Device 1' in pipeline_content
        assert 'Reference Device M' in pipeline_content

    def test_merge_instructions(self, pipeline_content):
        """Must include merge instructions for different column counts."""
        assert 'Pad shorter rows' in pipeline_content

    def test_incremental_reference(self, pipeline_content):
        """Must reference --incremental flag for automatic merge."""
        assert '--incremental' in pipeline_content


# ===== Item 14: Section Numbering Cross-Reference =====

class TestSectionNumberingCrossref:
    """section-numbering-crossref.md must exist and be comprehensive."""

    @pytest.fixture
    def crossref_content(self):
        path = os.path.join(REFERENCES_DIR, 'section-numbering-crossref.md')
        assert os.path.exists(path), "section-numbering-crossref.md must exist"
        with open(path) as f:
            return f.read()

    @pytest.fixture
    def assembler_content(self):
        with open(os.path.join(AGENTS_DIR, 'submission-assembler.md')) as f:
            return f.read()

    def test_file_exists(self):
        """section-numbering-crossref.md must exist."""
        assert os.path.exists(os.path.join(REFERENCES_DIR, 'section-numbering-crossref.md'))

    def test_three_numbering_systems(self, crossref_content):
        """Must document all three numbering systems."""
        assert 'Plugin' in crossref_content
        assert 'FDA Guidance' in crossref_content
        assert 'eSTAR' in crossref_content

    def test_plugin_sections_01_through_17(self, crossref_content):
        """Must map all 17 plugin sections."""
        for i in range(1, 18):
            assert f"| {i:02d}" in crossref_content or f"| {i:02d} " in crossref_content, \
                f"Plugin section {i:02d} not found in cross-reference"

    def test_fda_guidance_sections_1_through_20(self, crossref_content):
        """Must reference FDA guidance sections 1-20."""
        for i in [1, 2, 3, 4, 8, 9, 11, 17, 20]:
            assert f"| {i} |" in crossref_content or f"| {i}  |" in crossref_content, \
                f"FDA section {i} not found"

    def test_draft_file_mappings(self, crossref_content):
        """Must include draft file names."""
        expected_drafts = [
            'draft_cover-letter.md',
            'draft_device-description.md',
            'draft_se-discussion.md',
            'draft_labeling.md',
            'draft_performance-summary.md',
        ]
        for draft in expected_drafts:
            assert draft in crossref_content, f"{draft} not in cross-reference"

    def test_export_path_mappings(self, crossref_content):
        """Must include export directory paths."""
        expected_paths = [
            '01_CoverLetter/',
            '06_DeviceDescription/',
            '07_SEComparison/',
            '15_PerformanceTesting/',
        ]
        for path in expected_paths:
            assert path in crossref_content, f"{path} not in cross-reference"

    def test_assembler_references_crossref(self, assembler_content):
        """submission-assembler.md must reference section-numbering-crossref.md."""
        assert 'section-numbering-crossref.md' in assembler_content

    def test_key_differences_documented(self, crossref_content):
        """Must document key differences between systems."""
        assert 'Plugin vs. FDA Numbering' in crossref_content
        assert 'Plugin vs. eSTAR Pages' in crossref_content


# ===== Pre-existing items verification (already done in v5.16.0) =====

class TestPreExistingItemsStillCorrect:
    """Verify items already complete in v5.16.0 remain correct."""

    def test_batchfetch_delay_flag(self):
        """Item 3: batchfetch.py must have --delay CLI flag."""
        with open(os.path.join(SCRIPTS_DIR, 'batchfetch.py')) as f:
            content = f.read()
        assert '--delay' in content
        assert 'download_delay' in content

    def test_standards_dir_in_configure(self):
        """Item 5: configure.md must have standards_dir setting."""
        with open(os.path.join(COMMANDS_DIR, 'configure.md')) as f:
            content = f.read()
        assert 'standards_dir' in content

    def test_standards_index_in_standards_cmd(self):
        """Item 5: standards.md must have --index mode."""
        with open(os.path.join(COMMANDS_DIR, 'standards.md')) as f:
            content = f.read()
        assert '--index' in content
        assert 'standards_index.json' in content

    def test_presub_legal_status_check(self):
        """Item 6: presub-planner.md must check predicate legal status."""
        with open(os.path.join(AGENTS_DIR, 'presub-planner.md')) as f:
            content = f.read()
        assert 'WITHDRAWN' in content
        assert 'ENFORCEMENT_ACTION' in content
        assert 'legal_status' in content

    def test_review_simulator_legal_status_check(self):
        """Item 6: review-simulator.md must check predicate legal status."""
        with open(os.path.join(AGENTS_DIR, 'review-simulator.md')) as f:
            content = f.read()
        assert 'WITHDRAWN' in content
        assert 'ENFORCEMENT_ACTION' in content
        assert 'legal_status' in content

    def test_research_intelligence_progress_11_steps(self):
        """Item 8 (RI-C1): research-intelligence.md must show [1/11] to [11/11] (v5.18.0: AccessGUDID step added)."""
        with open(os.path.join(AGENTS_DIR, 'research-intelligence.md')) as f:
            content = f.read()
        assert '[1/11]' in content
        assert '[11/11]' in content

    def test_data_pipeline_progress_7_steps(self):
        """Item 8 (DP-H4): data-pipeline-manager.md must show [1/7] to [7/7]."""
        with open(os.path.join(AGENTS_DIR, 'data-pipeline-manager.md')) as f:
            content = f.read()
        assert '[1/7]' in content
        assert '[7/7]' in content

    def test_biocompat_matrix_15_endpoints(self):
        """Item 10: draft-templates.md must have 15 biocompat endpoints."""
        with open(os.path.join(REFERENCES_DIR, 'draft-templates.md')) as f:
            content = f.read()
        endpoints = [
            'Cytotoxicity', 'Sensitization', 'Irritation',
            'Pyrogenicity', 'Acute Systemic Toxicity',
            'Subacute/Subchronic', 'Chronic Systemic Toxicity',
            'Genotoxicity', 'Carcinogenicity',
            'Reproductive/Developmental', 'Implantation',
            'Hemocompatibility', 'Degradation',
            'Chemical Characterization', 'Toxicological Risk Assessment',
        ]
        for endpoint in endpoints:
            assert endpoint in content, f"Biocompat endpoint '{endpoint}' not found"

    def test_estar_section_02_in_mandatory_checks(self):
        """Item 11: review-simulator must have Section 02 (Form 3514) in mandatory checks."""
        with open(os.path.join(AGENTS_DIR, 'review-simulator.md')) as f:
            content = f.read()
        assert 'Cover Sheet (3514)' in content
        assert '| 02 |' in content

    def test_cybersecurity_critical_severity(self):
        """Item 12: Cybersecurity missing docs must be CRITICAL severity."""
        with open(os.path.join(AGENTS_DIR, 'review-simulator.md')) as f:
            content = f.read()
        assert 'CRITICAL severity' in content
        assert 'Section 524B' in content

    def test_export_includes_estar_index(self):
        """Item 13: export.md ZIP must include eSTAR_index.md."""
        with open(os.path.join(COMMANDS_DIR, 'export.md')) as f:
            content = f.read()
        assert 'eSTAR_index.md' in content

    def test_none_guard_in_predicate_classification(self):
        """Item 2: predicate_extractor.py must guard against None==None."""
        with open(os.path.join(SCRIPTS_DIR, 'predicate_extractor.py')) as f:
            content = f.read()
        assert 'is not None' in content


# ===== Version and Plugin Metadata =====

class TestPluginVersion:
    """Plugin must be at v5.18.0."""

    def test_plugin_json_version(self):
        """plugin.json must declare v5.18.0."""
        import json
        with open(os.path.join(PLUGIN_ROOT, '.claude-plugin', 'plugin.json')) as f:
            data = json.load(f)
        assert data['version'] == '5.22.0'

    @pytest.mark.skip(reason="SPRINT5_8AGENT_REVIEW.md removed during dev artifact cleanup")
    def test_sprint5_review_exists(self):
        """Sprint 5 review document must exist."""
        assert os.path.exists(os.path.join(PLUGIN_ROOT, 'SPRINT5_8AGENT_REVIEW.md'))
