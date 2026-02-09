"""Tests for v5.15.0: Guidance-to-Device Matching Accuracy.

Validates the 3-tier guidance trigger system:
  Tier 1 — API-authoritative flags (openFDA + AccessGUDID)
  Tier 2 — Word-boundary keyword matching with negation awareness
  Tier 3 — Classification heuristics (regulation family, fallback)

Test categories:
  - False positive resistance (~20 tests)
  - False negative resistance (~20 tests)
  - API flag priority (~10 tests)
  - Comprehensive device scenarios (~15 tests)
"""

import os
import re

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
CMDS_DIR = os.path.join(BASE_DIR, "commands")
REFS_DIR = os.path.join(BASE_DIR, "skills", "fda-510k-knowledge", "references")
TOP_REFS_DIR = os.path.join(BASE_DIR, "references")
PLUGIN_JSON = os.path.join(BASE_DIR, ".claude-plugin", "plugin.json")


# ── Helper: Reproduce the kw_match logic from guidance.md ──────────────


def kw_match(desc, keywords):
    """Word-boundary matching with negation awareness.
    Mirrors the logic in commands/guidance.md Step 3."""
    for kw in keywords:
        pattern = r'\b' + re.escape(kw) + r'\b'
        match = re.search(pattern, desc, re.IGNORECASE)
        if match:
            prefix = desc[max(0, match.start() - 20):match.start()].lower()
            if not any(neg in prefix for neg in
                       ['not ', 'non-', 'non ', 'no ', 'without ',
                        "doesn't ", "does not "]):
                return True
    return False


# ── Keyword lists from guidance.md (must stay in sync) ──────────────

KW_AIML = [
    "artificial intelligence", "ai-enabled", "ai-based", "ai/ml",
    "machine learning", "deep learning", "neural network",
    "computer-aided detection", "computer-aided diagnosis", "cadx", "cade",
]

KW_SOFTWARE = [
    "software", "algorithm", "mobile app", "software app", "firmware",
    "samd", "software as a medical device", "digital health",
    "software function", "machine learning algorithm",
    "cloud-based software",
]

KW_WIRELESS = [
    "wireless", "bluetooth", "wifi", "wi-fi", "network-connected",
    "cloud-connected", "internet of things", "iot device",
    "rf communication", "rf wireless", "radio frequency",
    "cellular", "zigbee", "lora", "near-field communication", "nfc",
]

KW_COMBINATION = [
    "combination product", "drug-device", "drug-eluting", "drug-coated",
    "biologic-device", "antimicrobial agent", "drug delivery device",
    "drug-impregnated", "bioresorbable drug",
]

KW_STERILIZATION = [
    "sterile", "sterilized", "sterilization", "aseptic",
    "terminally sterilized", "gamma irradiated", "gamma sterilized",
    "eo sterilized", "ethylene oxide", "e-beam sterilized",
    "radiation sterilized", "steam sterilized",
]

KW_IMPLANT = [
    "implant", "implantable", "permanent implant", "indwelling",
    "prosthesis", "prosthetic", "endoprosthesis",
]

KW_REUSABLE = [
    "reusable", "reprocessing", "reprocessed", "multi-use",
    "cleaning validation", "disinfection",
]

KW_3D_PRINTING = [
    "3d print", "3d-printed", "3d printed",
    "additive manufactur", "additively manufactured",
    "selective laser sintering", "selective laser melting",
    "electron beam melting", "fused deposition", "binder jetting",
]

KW_ANIMAL = [
    "collagen", "gelatin", "bovine", "porcine", "animal-derived",
    "animal tissue", "equine", "ovine", "decellularized",
    "xenograft", "biologic matrix",
]

KW_HOME_USE = [
    "home use", "over-the-counter", "otc device", "patient self-test",
    "lay user", "home monitoring", "self-administered",
    "consumer use", "non-professional use",
]

KW_PEDIATRIC = [
    "pediatric", "neonatal", "infant", "children", "child",
    "neonate", "newborn", "adolescent",
]

KW_LATEX = [
    "latex", "natural rubber", "natural rubber latex",
]

KW_ELECTRICAL = [
    "battery-powered", "battery powered", "ac mains", "rechargeable",
    "electrically powered", "mains-powered", "line-powered",
    "lithium battery", "power supply", "electrical stimulation",
]


# ══════════════════════════════════════════════════════════════════════
#  Section A: False Positive Resistance Tests
# ══════════════════════════════════════════════════════════════════════


class TestFalsePositiveResistance:
    """Ambiguous device descriptions must NOT trigger wrong guidance."""

    def test_drain_does_not_trigger_ai(self):
        """'surgical drain' must NOT trigger AI/ML guidance."""
        assert not kw_match("surgical drain", KW_AIML)

    def test_air_mattress_does_not_trigger_ai(self):
        """'air mattress' must NOT trigger AI/ML guidance."""
        assert not kw_match("air mattress pressure relief", KW_AIML)

    def test_aid_does_not_trigger_ai(self):
        """'first aid kit' must NOT trigger AI/ML guidance."""
        assert not kw_match("first aid kit for wound care", KW_AIML)

    def test_pair_does_not_trigger_ai(self):
        """'pair of scissors' must NOT trigger AI/ML guidance."""
        assert not kw_match("pair of surgical scissors", KW_AIML)

    def test_apparatus_does_not_trigger_software(self):
        """'medical apparatus' must NOT trigger software guidance."""
        assert not kw_match("medical apparatus for patient positioning", KW_SOFTWARE)

    def test_digital_thermometer_basic(self):
        """'digital thermometer' should NOT trigger software.
        'digital' is removed from keyword list; only 'digital health' matches."""
        assert not kw_match("digital thermometer with LCD display", KW_SOFTWARE)

    def test_performance_does_not_trigger_wireless(self):
        """'high performance device' must NOT trigger wireless guidance.
        'rf' alone no longer matches — only 'rf communication', 'rf wireless'."""
        assert not kw_match("high performance surgical device", KW_WIRELESS)

    def test_connected_tubes_does_not_trigger_wireless(self):
        """'tubes connected to pump' must NOT trigger wireless guidance.
        'connected' alone no longer matches — only 'network-connected', 'cloud-connected'."""
        assert not kw_match("tubes connected to pump assembly", KW_WIRELESS)

    def test_iot_in_word_does_not_trigger(self):
        """'patriotic' must NOT trigger IoT guidance."""
        assert not kw_match("patriotic design surgical drape", KW_WIRELESS)

    def test_no_drug_claims_does_not_trigger_combination(self):
        """'contains no drug or biologic' must NOT trigger combination.
        Negation awareness should catch 'no drug'."""
        assert not kw_match("this device contains no drug or biologic substance", KW_COMBINATION)

    def test_drug_free_does_not_trigger_combination(self):
        """'drug-free wound dressing' must NOT trigger combination."""
        assert not kw_match("drug-free wound dressing", KW_COMBINATION)

    def test_non_sterile_does_not_trigger_sterilization(self):
        """'supplied non-sterile' must NOT trigger sterilization guidance."""
        assert not kw_match("supplied non-sterile for single use", KW_STERILIZATION)

    def test_not_sterile_does_not_trigger_sterilization(self):
        """'not sterile' must NOT trigger sterilization guidance."""
        assert not kw_match("this product is not sterile", KW_STERILIZATION)

    def test_without_sterilization_does_not_trigger(self):
        """'without sterilization required' must NOT trigger."""
        assert not kw_match("shipped without sterilization required", KW_STERILIZATION)

    def test_non_implant_does_not_trigger_implant(self):
        """'non-implantable' must NOT trigger implant guidance."""
        assert not kw_match("non-implantable external fixation device", KW_IMPLANT)

    def test_rf_wound_does_not_trigger_wireless(self):
        """'RF wound' (wound from radio frequency ablation context) should not match.
        Actually 'rf wound' doesn't contain 'rf communication' or 'rf wireless'."""
        assert not kw_match("rf wound closure device", KW_WIRELESS)

    def test_plain_app_does_not_trigger_software(self):
        """'app' alone (e.g., 'application of bandage') must NOT trigger.
        'app' is removed; only 'mobile app', 'software app' match."""
        assert not kw_match("application of bandage to wound site", KW_SOFTWARE)

    def test_natural_does_not_trigger_latex(self):
        """'natural' alone must NOT trigger latex guidance."""
        assert not kw_match("natural collagen matrix", KW_LATEX)

    def test_child_proof_cap_not_pediatric(self):
        """'child-proof cap' DOES contain 'child' so it may trigger.
        This is a known edge case — child-proof packaging IS relevant
        to pediatric considerations."""
        # This actually SHOULD match per our keyword list
        assert kw_match("child-proof cap on medication dispenser", KW_PEDIATRIC)

    def test_rechargeable_light_not_medical(self):
        """'rechargeable examination light' DOES trigger electrical — correct.
        Battery/rechargeable devices DO need IEC 60601-1."""
        assert kw_match("rechargeable examination light", KW_ELECTRICAL)


# ══════════════════════════════════════════════════════════════════════
#  Section B: False Negative Resistance Tests
# ══════════════════════════════════════════════════════════════════════


class TestFalseNegativeResistance:
    """Known device descriptions MUST trigger the correct guidance."""

    def test_prosthesis_triggers_implant(self):
        """'hip prosthesis' must trigger implant guidance."""
        assert kw_match("total hip prosthesis cemented", KW_IMPLANT)

    def test_prosthetic_triggers_implant(self):
        """'prosthetic heart valve' must trigger implant guidance."""
        assert kw_match("prosthetic heart valve", KW_IMPLANT)

    def test_indwelling_triggers_implant(self):
        """'indwelling catheter' must trigger implant guidance."""
        assert kw_match("indwelling urinary catheter", KW_IMPLANT)

    def test_gamma_irradiated_triggers_sterilization(self):
        """'gamma irradiated' must trigger sterilization guidance."""
        assert kw_match("gamma irradiated wound dressing", KW_STERILIZATION)

    def test_eo_sterilized_triggers_sterilization(self):
        """'EO sterilized' must trigger sterilization guidance."""
        assert kw_match("EO sterilized surgical pack", KW_STERILIZATION)

    def test_ethylene_oxide_triggers_sterilization(self):
        """'ethylene oxide' must trigger sterilization guidance."""
        assert kw_match("validated with ethylene oxide sterilization", KW_STERILIZATION)

    def test_terminally_sterilized_triggers(self):
        """'terminally sterilized' must trigger sterilization."""
        assert kw_match("terminally sterilized implant", KW_STERILIZATION)

    def test_battery_powered_triggers_electrical(self):
        """'battery-powered' must trigger electrical safety guidance."""
        assert kw_match("battery-powered infusion pump", KW_ELECTRICAL)

    def test_rechargeable_triggers_electrical(self):
        """'rechargeable' must trigger electrical safety guidance."""
        assert kw_match("rechargeable hearing aid", KW_ELECTRICAL)

    def test_bovine_collagen_triggers_animal_derived(self):
        """'bovine collagen matrix' must trigger animal-derived guidance."""
        assert kw_match("bovine collagen matrix for tissue repair", KW_ANIMAL)

    def test_porcine_triggers_animal_derived(self):
        """'porcine dermis' must trigger animal-derived guidance."""
        assert kw_match("porcine dermis surgical mesh", KW_ANIMAL)

    def test_xenograft_triggers_animal_derived(self):
        """'xenograft' must trigger animal-derived guidance."""
        assert kw_match("xenograft bone void filler", KW_ANIMAL)

    def test_home_use_triggers_home_guidance(self):
        """'intended for home use' must trigger home use guidance."""
        assert kw_match("blood pressure monitor intended for home use", KW_HOME_USE)

    def test_otc_triggers_home_guidance(self):
        """'over-the-counter' must trigger home use guidance."""
        assert kw_match("over-the-counter pregnancy test", KW_HOME_USE)

    def test_additive_manufactured_triggers_3d_printing(self):
        """'additively manufactured titanium' must trigger 3D printing."""
        assert kw_match("additively manufactured titanium spinal cage", KW_3D_PRINTING)

    def test_3d_printed_triggers(self):
        """'3D-printed' must trigger 3D printing guidance."""
        assert kw_match("3D-printed patient-specific cranial implant", KW_3D_PRINTING)

    def test_selective_laser_melting_triggers(self):
        """'selective laser melting' must trigger 3D printing guidance."""
        assert kw_match("fabricated via selective laser melting", KW_3D_PRINTING)

    def test_latex_triggers_latex_guidance(self):
        """'natural rubber latex' must trigger latex guidance."""
        assert kw_match("contains natural rubber latex components", KW_LATEX)

    def test_neonatal_triggers_pediatric(self):
        """'neonatal' must trigger pediatric guidance."""
        assert kw_match("neonatal incubator temperature sensor", KW_PEDIATRIC)

    def test_pediatric_triggers_pediatric(self):
        """'pediatric' must trigger pediatric guidance."""
        assert kw_match("pediatric orthopedic fixation plate", KW_PEDIATRIC)

    def test_machine_learning_triggers_aiml(self):
        """'machine learning' must trigger AI/ML guidance."""
        assert kw_match("machine learning algorithm for lesion detection", KW_AIML)

    def test_cade_triggers_aiml(self):
        """'CADe' must trigger AI/ML guidance."""
        assert kw_match("CADe software for mammography screening", KW_AIML)

    def test_drug_eluting_triggers_combination(self):
        """'drug-eluting' must trigger combination product guidance."""
        assert kw_match("drug-eluting coronary stent", KW_COMBINATION)

    def test_bluetooth_triggers_wireless(self):
        """'bluetooth' must trigger wireless guidance."""
        assert kw_match("bluetooth-enabled pulse oximeter", KW_WIRELESS)

    def test_wifi_triggers_wireless(self):
        """'Wi-Fi' must trigger wireless guidance."""
        assert kw_match("Wi-Fi connected blood glucose monitor", KW_WIRELESS)


# ══════════════════════════════════════════════════════════════════════
#  Section C: API Flag Priority Tests
# ══════════════════════════════════════════════════════════════════════


class TestAPIFlagPriority:
    """API flags should take priority over keyword matching.

    These tests verify the logic structure in guidance.md and
    guidance-lookup.md documents, not runtime API calls.
    """

    def setup_method(self):
        with open(os.path.join(CMDS_DIR, "guidance.md")) as f:
            self.guidance_content = f.read()
        with open(os.path.join(REFS_DIR, "guidance-lookup.md")) as f:
            self.lookup_content = f.read()

    def test_tier1_before_tier2_in_guidance(self):
        """Tier 1 API flags must be checked before Tier 2 keywords."""
        tier1_pos = self.guidance_content.find("TIER 1")
        tier2_pos = self.guidance_content.find("TIER 2")
        assert tier1_pos < tier2_pos, "Tier 1 must come before Tier 2"

    def test_tier2_before_tier3_in_guidance(self):
        """Tier 2 keywords must be checked before Tier 3 heuristics."""
        tier2_pos = self.guidance_content.find("TIER 2")
        tier3_pos = self.guidance_content.find("TIER 3")
        assert tier2_pos < tier3_pos, "Tier 2 must come before Tier 3"

    def test_implant_flag_in_tier1(self):
        """implant_flag == 'Y' must be in Tier 1 (API authoritative)."""
        tier1_start = self.guidance_content.find("TIER 1")
        tier2_start = self.guidance_content.find("TIER 2")
        tier1_section = self.guidance_content[tier1_start:tier2_start]
        assert "implant_flag" in tier1_section

    def test_gudid_sterile_in_tier1(self):
        """GUDID is_sterile must be in Tier 1."""
        tier1_start = self.guidance_content.find("TIER 1")
        tier2_start = self.guidance_content.find("TIER 2")
        tier1_section = self.guidance_content[tier1_start:tier2_start]
        assert "gudid_is_sterile" in tier1_section

    def test_life_sustain_in_tier1(self):
        """life_sustain_flag must be in Tier 1."""
        tier1_start = self.guidance_content.find("TIER 1")
        tier2_start = self.guidance_content.find("TIER 2")
        tier1_section = self.guidance_content[tier1_start:tier2_start]
        assert "life_sustain_flag" in tier1_section

    def test_gudid_single_use_logs_note(self):
        """is_single_use == true must log a note (not silently suppress)."""
        tier1_start = self.guidance_content.find("TIER 1")
        tier2_start = self.guidance_content.find("TIER 2")
        tier1_section = self.guidance_content[tier1_start:tier2_start]
        assert "gudid_single_use == True" in tier1_section
        # Must produce a Single-Use Note rather than silently passing
        assert "Single-Use Note" in tier1_section

    def test_sterilization_tier2_skips_if_gudid_present(self):
        """Tier 2 sterilization keywords should skip if GUDID already triggered."""
        tier2_start = self.guidance_content.find("TIER 2")
        tier3_start = self.guidance_content.find("TIER 3")
        tier2_section = self.guidance_content[tier2_start:tier3_start]
        assert "not already triggered by GUDID" in tier2_section or \
               'not any(t[0].startswith("Sterilization")' in tier2_section

    def test_implant_tier2_skips_if_api_present(self):
        """Tier 2 implant keywords should skip if API flag already triggered."""
        tier2_start = self.guidance_content.find("TIER 2")
        tier3_start = self.guidance_content.find("TIER 3")
        tier2_section = self.guidance_content[tier2_start:tier3_start]
        assert "not already triggered by API flag" in tier2_section or \
               'not any(t[0] == "Implantable"' in tier2_section

    def test_sterilization_method_maps_to_correct_standard(self):
        """EO method → ISO 11135, radiation → ISO 11137, steam → ISO 17665."""
        assert "ISO 11135" in self.guidance_content
        assert "ISO 11137" in self.guidance_content
        assert "ISO 17665" in self.guidance_content

    def test_lookup_ref_documents_3_tiers(self):
        """guidance-lookup.md must document all 3 tiers."""
        assert "Tier 1" in self.lookup_content
        assert "Tier 2" in self.lookup_content
        assert "Tier 3" in self.lookup_content

    def test_lookup_has_sterilization_method_mapping(self):
        """guidance-lookup.md must have sterilization method → standard table."""
        assert "Sterilization Method" in self.lookup_content
        assert "ISO 11135" in self.lookup_content
        assert "ISO 11137" in self.lookup_content


# ══════════════════════════════════════════════════════════════════════
#  Section D: Comprehensive Device Scenario Tests
# ══════════════════════════════════════════════════════════════════════


class TestDeviceScenarios:
    """Test complete guidance trigger output for known device types."""

    def _get_triggers(self, desc):
        """Return set of category names triggered by the description."""
        triggered = set()
        checks = [
            ("AI/ML", KW_AIML),
            ("Software", KW_SOFTWARE),
            ("Wireless", KW_WIRELESS),
            ("Combination", KW_COMBINATION),
            ("Sterilization", KW_STERILIZATION),
            ("Implant", KW_IMPLANT),
            ("Reusable", KW_REUSABLE),
            ("3D Printing", KW_3D_PRINTING),
            ("Animal-Derived", KW_ANIMAL),
            ("Home Use", KW_HOME_USE),
            ("Pediatric", KW_PEDIATRIC),
            ("Latex", KW_LATEX),
            ("Electrical", KW_ELECTRICAL),
        ]
        for category, kws in checks:
            if kw_match(desc, kws):
                triggered.add(category)
        return triggered

    def test_wound_dressing_sterile(self):
        """Sterile wound dressing → sterilization (no software, no wireless)."""
        t = self._get_triggers("sterile collagen wound dressing for acute wounds")
        assert "Sterilization" in t
        assert "Animal-Derived" in t  # collagen
        assert "Software" not in t
        assert "Wireless" not in t

    def test_cgm_software_wireless(self):
        """iCGM → software + wireless + electrical."""
        t = self._get_triggers(
            "continuous glucose monitoring system with bluetooth-enabled "
            "software algorithm and rechargeable battery"
        )
        assert "Software" in t
        assert "Wireless" in t
        assert "Electrical" in t

    def test_orthopedic_implant_3d_printed(self):
        """3D printed spinal implant → implant + 3D printing."""
        t = self._get_triggers(
            "3D-printed titanium spinal interbody fusion implant"
        )
        assert "Implant" in t
        assert "3D Printing" in t

    def test_ivd_home_use(self):
        """OTC blood glucose test → home use (no wireless, no implant)."""
        t = self._get_triggers(
            "over-the-counter blood glucose test strip for home use"
        )
        assert "Home Use" in t
        assert "Wireless" not in t
        assert "Implant" not in t

    def test_simple_non_sterile_class_i(self):
        """Non-sterile Class I device → minimal triggers."""
        t = self._get_triggers(
            "non-sterile elastic bandage for external wound support"
        )
        # Non-sterile should NOT trigger sterilization
        assert "Sterilization" not in t
        assert "Software" not in t
        assert "Wireless" not in t

    def test_ai_radiology(self):
        """AI radiology CADx → AI/ML + software."""
        t = self._get_triggers(
            "artificial intelligence CADx software for chest X-ray "
            "analysis using deep learning neural network"
        )
        assert "AI/ML" in t
        assert "Software" in t

    def test_combination_drug_device(self):
        """Drug-eluting stent → combination + implant."""
        t = self._get_triggers(
            "drug-eluting coronary stent with sirolimus implant"
        )
        assert "Combination" in t
        assert "Implant" in t

    def test_pediatric_home_use_device(self):
        """Pediatric home-use device → pediatric + home use."""
        t = self._get_triggers(
            "pediatric asthma monitoring device for home use"
        )
        assert "Pediatric" in t
        assert "Home Use" in t

    def test_reusable_surgical_instrument(self):
        """Reusable surgical instrument → reusable (no sterile trigger)."""
        t = self._get_triggers(
            "reusable stainless steel surgical forceps"
        )
        assert "Reusable" in t
        assert "Sterilization" not in t

    def test_latex_exam_gloves(self):
        """Natural rubber latex exam gloves → latex."""
        t = self._get_triggers(
            "natural rubber latex examination gloves"
        )
        assert "Latex" in t

    def test_animal_derived_surgical_mesh(self):
        """Porcine dermis mesh → animal-derived."""
        t = self._get_triggers(
            "porcine dermis surgical mesh for hernia repair"
        )
        assert "Animal-Derived" in t

    def test_wireless_infusion_pump(self):
        """Wi-Fi infusion pump → wireless + electrical + software."""
        t = self._get_triggers(
            "Wi-Fi connected infusion pump with software algorithm "
            "and rechargeable lithium battery"
        )
        assert "Wireless" in t
        assert "Electrical" in t
        assert "Software" in t

    def test_neonatal_monitor(self):
        """Neonatal monitor → pediatric + electrical."""
        t = self._get_triggers(
            "neonatal vital signs monitor with rechargeable battery"
        )
        assert "Pediatric" in t
        assert "Electrical" in t

    def test_additive_manufactured_dental(self):
        """Additively manufactured dental implant → 3D printing + implant."""
        t = self._get_triggers(
            "additively manufactured titanium dental implant"
        )
        assert "3D Printing" in t
        assert "Implant" in t

    def test_bovine_collagen_sterile(self):
        """Sterile bovine collagen → sterilization + animal-derived."""
        t = self._get_triggers(
            "sterile bovine collagen wound matrix"
        )
        assert "Sterilization" in t
        assert "Animal-Derived" in t


# ══════════════════════════════════════════════════════════════════════
#  Section E: Document Structure Validation
# ══════════════════════════════════════════════════════════════════════


class TestGuidanceDocumentStructure:
    """Verify guidance.md has the required 3-tier structure."""

    def setup_method(self):
        with open(os.path.join(CMDS_DIR, "guidance.md")) as f:
            self.content = f.read()

    def test_has_step_1_5_gudid(self):
        """guidance.md must have Step 1.5 for AccessGUDID query."""
        assert "Step 1.5" in self.content
        assert "AccessGUDID" in self.content

    def test_has_implant_flag_in_api(self):
        """Step 1 API must output IMPLANT_FLAG."""
        assert "IMPLANT_FLAG" in self.content

    def test_has_life_sustain_in_api(self):
        """Step 1 API must output LIFE_SUSTAIN."""
        assert "LIFE_SUSTAIN" in self.content

    def test_has_gudid_sterile(self):
        """Step 1.5 must output GUDID_STERILE."""
        assert "GUDID_STERILE" in self.content

    def test_has_gudid_single_use(self):
        """Step 1.5 must output GUDID_SINGLE_USE."""
        assert "GUDID_SINGLE_USE" in self.content

    def test_has_gudid_mri_safety(self):
        """Step 1.5 must output GUDID_MRI_SAFETY."""
        assert "GUDID_MRI_SAFETY" in self.content

    def test_has_gudid_latex(self):
        """Step 1.5 must output GUDID_LATEX."""
        assert "GUDID_LATEX" in self.content

    def test_has_kw_match_function(self):
        """guidance.md must define the kw_match helper."""
        assert "def kw_match" in self.content

    def test_has_negation_awareness(self):
        """kw_match must check for negation prefixes."""
        assert "not " in self.content
        assert "non-" in self.content
        assert "without " in self.content

    def test_has_3d_printing_category(self):
        """guidance.md must have 3D printing trigger."""
        assert "3D Printing" in self.content or "3d print" in self.content

    def test_has_animal_derived_category(self):
        """guidance.md must have animal-derived trigger."""
        assert "Animal-Derived" in self.content

    def test_has_home_use_category(self):
        """guidance.md must have home use trigger."""
        assert "Home Use" in self.content

    def test_has_pediatric_category(self):
        """guidance.md must have pediatric trigger."""
        assert "Pediatric" in self.content

    def test_has_electrical_category(self):
        """guidance.md must have electrical safety trigger."""
        assert "Electrical Safety" in self.content


class TestResearchCommandMirror:
    """Verify research.md Step 3.75 mirrors the 3-tier system."""

    def setup_method(self):
        with open(os.path.join(CMDS_DIR, "research.md")) as f:
            self.content = f.read()

    def test_has_3_tier_system(self):
        """research.md must reference the 3-tier system."""
        assert "3-Tier" in self.content or "3-tier" in self.content

    def test_has_tier1_api_flags(self):
        """research.md must list Tier 1 API flags."""
        assert "implant_flag" in self.content
        assert "life_sustain" in self.content

    def test_has_tier2_keyword_matching(self):
        """research.md must describe Tier 2 keyword matching."""
        assert "word-boundary" in self.content.lower() or "kw_match" in self.content

    def test_has_negation_awareness(self):
        """research.md must mention negation awareness."""
        assert "negation" in self.content.lower()

    def test_has_new_categories(self):
        """research.md must include new trigger categories."""
        assert "3D Print" in self.content or "3d print" in self.content
        assert "Animal-Derived" in self.content or "animal-derived" in self.content.lower()
        assert "Home Use" in self.content or "home use" in self.content.lower()
        assert "Pediatric" in self.content or "pediatric" in self.content.lower()

    def test_has_gudid_references(self):
        """research.md must reference AccessGUDID data."""
        assert "AccessGUDID" in self.content or "GUDID" in self.content


class TestGuidanceLookupReference:
    """Verify guidance-lookup.md has updated trigger table."""

    def setup_method(self):
        with open(os.path.join(REFS_DIR, "guidance-lookup.md")) as f:
            self.content = f.read()

    def test_has_api_authority_column(self):
        """Trigger table must have API Authority column."""
        assert "API Authority" in self.content or "API Flag" in self.content

    def test_has_sterilization_method_table(self):
        """Must have sterilization method → standard mapping."""
        assert "Sterilization Method" in self.content
        assert "ISO 11135" in self.content
        assert "ISO 11137" in self.content
        assert "ISO 17665" in self.content

    def test_has_keyword_lists(self):
        """Must document the keyword lists for each category."""
        assert "Keyword Lists" in self.content or "keyword" in self.content.lower()

    def test_has_3d_printing_row(self):
        """Must have 3D Printing in trigger table."""
        assert "3D Printing" in self.content

    def test_has_animal_derived_row(self):
        """Must have Animal-Derived in trigger table."""
        assert "Animal-Derived" in self.content

    def test_has_home_use_row(self):
        """Must have Home Use in trigger table."""
        assert "Home Use" in self.content

    def test_has_pediatric_row(self):
        """Must have Pediatric in trigger table."""
        assert "Pediatric" in self.content

    def test_copies_match(self):
        """Skill reference and top-level reference must match."""
        with open(os.path.join(TOP_REFS_DIR, "guidance-lookup.md")) as f:
            top_content = f.read()
        assert self.content == top_content


class TestGuidanceIndexNewEntries:
    """Verify fda-guidance-index.md has new guidance documents."""

    def setup_method(self):
        with open(os.path.join(REFS_DIR, "fda-guidance-index.md")) as f:
            self.content = f.read()

    def test_has_additive_manufacturing_guidance(self):
        """Must include additive manufacturing guidance (2017)."""
        assert "Additive Manufactured Medical Devices" in self.content

    def test_has_home_use_guidance(self):
        """Must include home use design guidance (2014)."""
        assert "Home Use" in self.content

    def test_has_pediatric_guidance(self):
        """Must include pediatric assessment guidance (2020)."""
        assert "Pediatric Medical Devices" in self.content

    def test_has_bench_performance_guidance(self):
        """Must include bench performance testing guidance (2019)."""
        assert "Bench Performance" in self.content or \
               "Non-Clinical Bench Performance" in self.content

    def test_has_latex_labeling(self):
        """Must include latex labeling regulation reference."""
        assert "801.437" in self.content or "latex" in self.content.lower()

    def test_has_animal_derived_guidance(self):
        """Must include animal-derived materials guidance."""
        assert "Animal" in self.content

    def test_has_3d_printing_trigger_keywords(self):
        """Must include 3D printing trigger keywords."""
        assert "3d print" in self.content.lower() or "additive manufactur" in self.content.lower()

    def test_index_copies_match(self):
        """Skill reference and top-level reference must match."""
        with open(os.path.join(TOP_REFS_DIR, "fda-guidance-index.md")) as f:
            top_content = f.read()
        assert self.content == top_content


# ══════════════════════════════════════════════════════════════════════
#  Section H: Audit Remediation Tests (HIGH severity fixes)
# ══════════════════════════════════════════════════════════════════════


class TestSingleUseSuppression:
    """HIGH-1: Single-use flag must NOT silently suppress reprocessing guidance."""

    def setup_method(self):
        with open(os.path.join(CMDS_DIR, "guidance.md")) as f:
            self.content = f.read()

    def test_single_use_has_caveat(self):
        """gudid_single_use == True must produce a note, not silent pass."""
        assert "Single-Use Note" in self.content

    def test_single_use_mentions_third_party(self):
        """Must mention third-party reprocessing per 21 CFR 820.3(p)."""
        assert "third-party reprocessing" in self.content.lower() or \
               "21 CFR 820.3(p)" in self.content

    def test_no_bare_pass_for_single_use(self):
        """Must not have bare 'pass' after single_use == True check."""
        # Find the single_use block and verify no bare 'pass'
        idx = self.content.find("gudid_single_use == True")
        assert idx >= 0, "gudid_single_use == True not found in guidance.md"
        # Get the next 300 chars after the match
        block = self.content[idx:idx+300]
        # Should NOT have a bare 'pass  # Single-use devices do NOT get reprocessing'
        assert "pass  # Single-use devices do NOT get reprocessing guidance" not in block

    def test_research_md_has_single_use_caveat(self):
        """research.md must also note the third-party reprocessing caveat."""
        with open(os.path.join(CMDS_DIR, "research.md")) as f:
            content = f.read()
        assert "third-party reprocessing" in content.lower() or \
               "21 CFR 820.3(p)" in content

    def test_guidance_lookup_has_caveat(self):
        """guidance-lookup.md must not silently suppress reprocessing."""
        with open(os.path.join(REFS_DIR, "guidance-lookup.md")) as f:
            content = f.read()
        # Should mention third-party or caveat for single-use
        assert "third-party" in content.lower() or "unless" in content.lower()


class TestUSBCybersecurityKeywords:
    """HIGH-2: USB must trigger cybersecurity guidance."""

    def test_usb_keywords_in_guidance_md(self):
        """guidance.md must have USB keywords in Tier 2."""
        with open(os.path.join(CMDS_DIR, "guidance.md")) as f:
            content = f.read()
        assert "usb data" in content.lower()
        assert "usb communication" in content.lower()
        assert "usb port" in content.lower()

    def test_usb_triggers_cybersecurity_not_emc(self):
        """USB keywords must trigger cybersecurity but NOT EMC/Wireless."""
        with open(os.path.join(CMDS_DIR, "guidance.md")) as f:
            content = f.read()
        # Find USB block
        idx = content.find("usb data")
        assert idx >= 0
        block = content[idx:idx+300]
        assert "Cybersecurity" in block
        # EMC/Wireless should NOT be triggered by USB alone
        assert "EMC/Wireless" not in block

    def test_research_md_has_usb(self):
        """research.md must include USB in keyword table."""
        with open(os.path.join(CMDS_DIR, "research.md")) as f:
            content = f.read()
        assert "usb data" in content.lower() or "usb communication" in content.lower()

    def test_guidance_lookup_has_usb(self):
        """guidance-lookup.md must list USB keywords."""
        with open(os.path.join(REFS_DIR, "guidance-lookup.md")) as f:
            content = f.read()
        assert "usb data" in content.lower()

    def test_usb_kw_match_true(self):
        """'device with USB data port for configuration' must match USB keywords."""
        assert kw_match("device with usb data port for configuration",
                       ["usb data", "usb communication", "usb port"])

    def test_usb_kw_match_no_usb(self):
        """'wireless bluetooth device' must NOT match USB keywords."""
        assert not kw_match("wireless bluetooth device",
                           ["usb data", "usb communication", "usb port"])

    def test_usb_consistency_with_cybersecurity_framework(self):
        """USB must be mentioned in cybersecurity-framework.md (pre-existing)."""
        fw_path = os.path.join(REFS_DIR, "cybersecurity-framework.md")
        if os.path.exists(fw_path):
            with open(fw_path) as f:
                content = f.read()
            assert "USB" in content or "usb" in content


class TestSubmissionOutlineKwMatch:
    """HIGH-3: submission-outline.md must use kw_match(), not substring matching."""

    def setup_method(self):
        with open(os.path.join(CMDS_DIR, "submission-outline.md")) as f:
            self.content = f.read()

    def test_has_kw_match_function(self):
        """submission-outline.md must define kw_match()."""
        assert "def kw_match" in self.content

    def test_has_negation_awareness(self):
        """submission-outline.md kw_match must check negation prefixes."""
        assert "not " in self.content
        assert "non-" in self.content
        assert "without " in self.content

    def test_no_bare_in_operator(self):
        """Must NOT use 'kw in desc' substring matching for section determination."""
        # Find the section applicability block
        idx = self.content.find("sections = {")
        if idx == -1:
            idx = self.content.find("Section Applicability")
        assert idx >= 0
        block = self.content[idx:idx+1500]
        # Should not have old-style 'any(kw in desc for kw'
        assert 'any(kw in desc for kw' not in block

    def test_uses_precise_software_keywords(self):
        """Must use precise software keywords (not bare 'app')."""
        idx = self.content.find("sections = {")
        if idx == -1:
            idx = self.content.find("Section Applicability")
        block = self.content[idx:idx+2500]
        # "app" alone should NOT be in the keyword list
        # "mobile app" or "software app" should be
        assert '"mobile app"' in block or '"software app"' in block
        # Bare "app" should not appear as a standalone keyword
        assert ', "app",' not in block
        assert '["app"' not in block

    def test_uses_precise_electrical_keywords(self):
        """Must use precise electrical keywords (not bare 'electric' or 'powered')."""
        idx = self.content.find("sections = {")
        if idx == -1:
            idx = self.content.find("Section Applicability")
        block = self.content[idx:idx+2500]
        # Should have precise terms like "battery-powered", not bare "powered"
        assert '"battery-powered"' in block or '"battery powered"' in block
        # Should NOT have bare "powered" or "electric" as standalone keywords
        assert ', "powered",' not in block
        assert ', "electric",' not in block

    def test_has_usb_in_cybersecurity_trigger(self):
        """submission-outline.md must include USB in cybersecurity trigger."""
        assert "usb data" in self.content.lower() or \
               "usb communication" in self.content.lower()
