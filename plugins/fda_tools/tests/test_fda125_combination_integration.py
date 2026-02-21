"""
Integration Tests for Combination Product Detection CLI (FDA-125)
=================================================================

Validates the ``fda_tools.scripts.detect_combination`` module and its
integration with ``CombinationProductDetector``:

  - detect_from_profile: drug-device, device-biologic, drug-device-biologic,
    standard device, Class U device
  - detect_from_text: basic call, Class U via device_class field
  - CLI --project-dir: loads device_profile.json and exits 0
  - CLI --device-description: text-only mode exits 0
  - CLI missing profile: exits 1 with JSON error on stderr
  - Output fields: all documented keys present in every result

Test count: 15
Target: pytest plugins/fda_tools/tests/test_fda125_combination_integration.py -v
"""

import json
import subprocess
import sys

from fda_tools.scripts.detect_combination import (
    detect_from_profile,
    detect_from_text,
)


# ---------------------------------------------------------------------------
# Expected output keys
# ---------------------------------------------------------------------------

REQUIRED_KEYS = {
    "is_combination",
    "combination_type",
    "confidence",
    "detected_components",
    "rho_assignment",
    "rho_rationale",
    "consultation_required",
    "regulatory_pathway",
    "recommendations",
    "class_u",
    "class_u_rationale",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _profile(description: str = "", trade_name: str = "",
             intended_use: str = "", device_class: str = "") -> dict:
    return {
        "device_description": description,
        "trade_name": trade_name,
        "intended_use": intended_use,
        "device_class": device_class,
    }


# ---------------------------------------------------------------------------
# TestDetectFromProfile
# ---------------------------------------------------------------------------


class TestDetectFromProfile:
    """Tests for detect_from_profile()."""

    def test_drug_device_detected(self):
        """Paclitaxel-eluting stent should be identified as drug-device."""
        profile = _profile(
            description="Drug-eluting coronary stent releasing paclitaxel "
                        "via controlled release polymer coating.",
            intended_use="Treatment of coronary artery disease.",
        )
        result = detect_from_profile(profile)
        assert result["is_combination"] is True
        assert "drug" in (result["combination_type"] or "").lower()

    def test_device_biologic_detected(self):
        """Collagen scaffold with growth factor should be device-biologic."""
        profile = _profile(
            description="Resorbable collagen scaffold impregnated with "
                        "recombinant human bone morphogenetic protein-2 (rhBMP-2).",
            intended_use="Bone regeneration and spinal fusion.",
        )
        result = detect_from_profile(profile)
        assert result["is_combination"] is True
        assert result["detected_components"]

    def test_drug_device_biologic_detected(self):
        """Triple combination product returns is_combination True."""
        profile = _profile(
            description="Absorbable scaffold containing antibiotic drug "
                        "and autologous platelet-rich plasma biologic component.",
            intended_use="Wound closure with infection prophylaxis.",
        )
        result = detect_from_profile(profile)
        assert result["is_combination"] is True

    def test_standard_device_not_combination(self):
        """Plain orthopedic screw has no drug/biologic components."""
        profile = _profile(
            description="Titanium cortical bone screw for fixation of long-bone "
                        "fractures. No drug or biologic component.",
            intended_use="Internal fixation of orthopedic fractures.",
        )
        result = detect_from_profile(profile)
        assert result["is_combination"] is False
        assert result["combination_type"] is None

    def test_class_u_from_device_class_field(self):
        """device_class='U' must set class_u=True."""
        profile = _profile(
            description="Novel monitoring device for continuous glucose tracking.",
            device_class="U",
        )
        result = detect_from_profile(profile)
        assert result["class_u"] is True

    def test_class_u_from_description_keyword(self):
        """'unclassified' keyword in description must set class_u=True."""
        profile = _profile(
            description="Unclassified transcranial magnetic stimulation device.",
        )
        result = detect_from_profile(profile)
        assert result["class_u"] is True

    def test_standard_device_class_u_false(self):
        """Standard Class II device must return class_u=False."""
        profile = _profile(
            description="Class II cardiac rhythm monitor.",
            device_class="II",
        )
        result = detect_from_profile(profile)
        assert result["class_u"] is False


# ---------------------------------------------------------------------------
# TestDetectFromText
# ---------------------------------------------------------------------------


class TestDetectFromText:
    """Tests for detect_from_text()."""

    def test_drug_device_from_text(self):
        result = detect_from_text(
            device_description="Antibiotic-eluting orthopedic cement releasing "
                               "gentamicin for infection prophylaxis.",
        )
        assert result["is_combination"] is True
        assert isinstance(result["detected_components"], list)

    def test_class_u_from_device_class_arg(self):
        result = detect_from_text(
            device_description="Novel neuromodulation implant.",
            device_class="U",
        )
        assert result["class_u"] is True

    def test_all_required_keys_present(self):
        result = detect_from_text(device_description="Standard diagnostic catheter.")
        missing = REQUIRED_KEYS - set(result.keys())
        assert not missing, f"Missing keys: {missing}"


# ---------------------------------------------------------------------------
# TestCLI
# ---------------------------------------------------------------------------


class TestCLI:
    """Tests for the CLI entry point."""

    def _run(self, *args) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-m", "fda_tools.scripts.detect_combination", *args],
            capture_output=True,
            text=True,
        )

    def test_project_dir_exits_zero(self, tmp_path):
        profile = {
            "device_description": "Standard pacemaker lead.",
            "trade_name": "LeadPro",
            "intended_use": "Cardiac rhythm management.",
        }
        (tmp_path / "device_profile.json").write_text(json.dumps(profile))
        proc = self._run("--project-dir", str(tmp_path))
        assert proc.returncode == 0

    def test_project_dir_output_is_json(self, tmp_path):
        profile = {"device_description": "Standard catheter."}
        (tmp_path / "device_profile.json").write_text(json.dumps(profile))
        proc = self._run("--project-dir", str(tmp_path))
        data = json.loads(proc.stdout)
        assert isinstance(data, dict)
        assert "is_combination" in data

    def test_device_description_flag_exits_zero(self):
        proc = self._run(
            "--device-description", "Drug-eluting stent releasing sirolimus."
        )
        assert proc.returncode == 0
        data = json.loads(proc.stdout)
        assert data["is_combination"] is True

    def test_missing_profile_exits_one(self, tmp_path):
        empty_dir = tmp_path / "no_profile"
        empty_dir.mkdir()
        proc = self._run("--project-dir", str(empty_dir))
        assert proc.returncode == 1
        err = json.loads(proc.stderr)
        assert "error" in err
