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

    def test_main_workflow_has_step_zero(self):
        # Find the main workflow block (contains "1. /fda:research PRODUCT_CODE")
        marker = "1. /fda:research PRODUCT_CODE"
        idx_research = self.content.index(marker)
        # Step 0 should appear before step 1 in the same block
        block_start = self.content.rfind("```", 0, idx_research)
        block = self.content[block_start:idx_research]
        assert "--setup-key" in block

    def test_import_workflow_has_step_zero(self):
        # Find the import workflow block (contains /fda:import)
        idx_import = self.content.index("/fda:import")
        block_start = self.content.rfind("```", 0, idx_import)
        block = self.content[block_start:idx_import]
        assert "--setup-key" in block


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
