# ADR-008: defusedxml Required for All Untrusted XML Parsing

**Status:** Accepted
**Date:** 2025-03-01

## Context

The tool parses eSTAR XML files received from FDA systems and third-party
submission portals. XML parsing of untrusted input is vulnerable to several
well-documented attack classes:

- **XXE (XML External Entity):** A crafted XML file declares an external entity
  referencing a local file (e.g., `file:///etc/passwd` or `file:///C:/Windows/win.ini`).
  When the parser expands the entity, the file contents are embedded in the
  parsed document and may be returned to an attacker or written to an output file.
- **Billion Laughs (entity expansion):** Exponentially nested entities cause
  memory exhaustion and denial of service.
- **DTD retrieval:** External DTD references cause outbound network requests,
  creating a network covert channel.

Python's stdlib `xml.etree.ElementTree` is vulnerable to XXE and entity
expansion by default. `lxml` is also vulnerable unless DTD loading is explicitly
disabled via `resolve_entities=False` — a flag that is easily omitted.

eSTAR XML files originate from external parties and must be treated as untrusted
input regardless of their apparent source.

## Decision

All XML parsing in `lib/` and `scripts/` must use `defusedxml`. Direct use of
`xml.etree.ElementTree` or `lxml` on untrusted input is a CI-enforced hard
failure (grep for `import xml.etree` and `from lxml` in non-test code triggers
a lint error). `defusedxml` disables DTD processing, external entity expansion,
and external DTD retrieval by default with no opt-in required.

## Alternatives Considered

- **stdlib xml.etree.ElementTree:** Convenient, no extra dependency. Rejected
  because it is vulnerable to XXE by default with no safe configuration option.
- **lxml with explicit hardening:** `lxml(resolve_entities=False, no_network=True)`
  is safe but requires every call site to pass both flags correctly. A single
  omission creates a vulnerability. Rejected in favor of a safe-by-default library.
- **Manual pre-sanitization:** Strip entity declarations with regex before
  parsing. Rejected as error-prone; regex-based XML sanitization has a long
  history of bypasses.

## Consequences

- `defusedxml` added to `requirements.txt` and included in the stdlib-exemption
  list for `lib/` (it is a security wrapper, not a feature library).
- Existing callers of `xml.etree` in scripts/ were migrated as part of this ADR.
- The CI lint rule catches regressions automatically.
- `defusedxml` is actively maintained and tracks Python stdlib changes.
