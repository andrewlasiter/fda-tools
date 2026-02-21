# ADR-004: Local-Only Analytics, No External Telemetry

**Status:** Accepted
**Date:** 2025-06-01

## Context

Usage analytics would help prioritize feature development. However, users are
regulatory affairs professionals working on FDA submissions. Their usage
patterns reveal which devices they are submitting, which predicates they
consider, and which regulatory strategies they pursue — all competitively and
legally sensitive information. Submission documents may reference clinical data
that constitutes PHI.

RA professionals in regulated industries are risk-averse about data leaving
their workstations. Any cloud telemetry, even opt-in, would be a barrier to
adoption and could violate company data governance policies.

The tool runs fully offline by design (see ADR-002). Adding an outbound
telemetry channel contradicts that design principle.

## Decision

All usage analytics and error reporting are written to local log files only:
`~/.fda-tools/logs/usage.jsonl` and `~/.fda-tools/logs/errors.jsonl`.
No data is transmitted to external services. No third-party analytics SDK
is included in the dependency tree.

## Alternatives Considered

- **Mixpanel / Amplitude:** Rich product analytics. Rejected because event
  payloads could contain file paths, device names, or error tracebacks that
  include PHI.
- **Sentry for error reporting:** Automatic stack traces would be valuable for
  debugging. Rejected because tracebacks frequently include variable values
  from device profile parsing, which may contain PHI.
- **Custom analytics server (self-hosted):** Removes third-party risk but
  still requires infrastructure, user consent, and network access — all
  contrary to the offline-first model.
- **Opt-in anonymous telemetry:** Considered but rejected; RA professionals
  will default to off and the consent friction reduces adoption.

## Consequences

- Feature prioritization relies on direct user feedback and support requests
  rather than automated usage data.
- Local log files rotate at 10MB; retention is 90 days by default.
- Error reports can be shared voluntarily by users when filing bug reports
  (they paste from the local log).
- No dependency on any external analytics service simplifies the dependency
  graph and eliminates a category of supply-chain risk.
