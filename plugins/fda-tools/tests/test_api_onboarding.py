"""Tests for first-run API key onboarding UX.

Validates that the WELCOME banner, Step 0 workflow hints, and API_KEY_NUDGE
tip lines are present in the correct files so new users discover the free
openFDA API key signup path naturally.
"""

import os


BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
CMDS_DIR = os.path.join(BASE_DIR, "commands")
SKILL_MD = os.path.join(
    BASE_DIR, "skills", "fda-510k-knowledge", "SKILL.md"
)


def _read(path):
    with open(path) as f:
        return f.read()


class TestStatusFirstRunBanner:
    """Test that status.md has first-run detection and WELCOME banner."""

    def setup_method(self):
        self.content = _read(os.path.join(CMDS_DIR, "status.md"))

    def test_has_first_run_detection(self):
        assert "FIRST_RUN" in self.content

    def test_has_welcome_banner(self):
        assert "WELCOME" in self.content

    def test_has_signup_url(self):
        assert "open.fda.gov/apis/authentication" in self.content

    def test_has_configure_setup_key_in_banner(self):
        assert "/fda:configure --setup-key" in self.content

    def test_has_rate_limit_comparison(self):
        assert "1,000 requests/day" in self.content
        assert "120,000 requests/day" in self.content


class TestSkillWorkflowStepZero:
    """Test that SKILL.md has Step 0 in both workflows."""

    def setup_method(self):
        self.content = _read(SKILL_MD)

    def test_main_workflow_has_setup_key_in_stage_1(self):
        """Workflow Guide Stage 1 should include --setup-key before data collection."""
        # In the new 5-stage layout, --setup-key appears in the Workflow Guide section
        assert "## Workflow Guide" in self.content
        idx_wf = self.content.index("## Workflow Guide")
        idx_stage1 = self.content.index("Stage 1: Setup", idx_wf)
        idx_stage2 = self.content.index("Stage 2", idx_stage1)
        stage1_block = self.content[idx_stage1:idx_stage2]
        assert "--setup-key" in stage1_block

    def test_import_workflow_references_configure(self):
        """Import workflow should be documented in the Workflow Guide."""
        # The import path is in the "Alternative: Import Existing eSTAR" section
        assert "/fda:import" in self.content


class TestValidateNudge:
    """Test that validate.md has API_KEY_NUDGE and tip line."""

    def setup_method(self):
        self.content = _read(os.path.join(CMDS_DIR, "validate.md"))

    def test_has_api_key_nudge(self):
        assert "API_KEY_NUDGE" in self.content

    def test_has_tip_line(self):
        assert "120x more API requests/day" in self.content

    def test_has_setup_key_reference(self):
        assert "--setup-key" in self.content


class TestResearchNudge:
    """Test that research.md has API_KEY_NUDGE and tip line."""

    def setup_method(self):
        self.content = _read(os.path.join(CMDS_DIR, "research.md"))

    def test_has_api_key_nudge(self):
        assert "API_KEY_NUDGE" in self.content

    def test_has_tip_line(self):
        assert "120x more API requests/day" in self.content

    def test_has_setup_key_reference(self):
        assert "--setup-key" in self.content


class TestSafetyNudge:
    """Test that safety.md has API_KEY_NUDGE and tip line."""

    def setup_method(self):
        self.content = _read(os.path.join(CMDS_DIR, "safety.md"))

    def test_has_api_key_nudge(self):
        assert "API_KEY_NUDGE" in self.content

    def test_has_tip_line(self):
        assert "120x more API requests/day" in self.content

    def test_has_setup_key_reference(self):
        assert "--setup-key" in self.content


class TestExtractNudge:
    """Test that extract.md has API_KEY_NUDGE and tip line."""

    def setup_method(self):
        self.content = _read(os.path.join(CMDS_DIR, "extract.md"))

    def test_has_api_key_nudge(self):
        assert "API_KEY_NUDGE" in self.content

    def test_has_tip_line(self):
        assert "120x more API requests/day" in self.content

    def test_has_setup_key_reference(self):
        assert "--setup-key" in self.content
