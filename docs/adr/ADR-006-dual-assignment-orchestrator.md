# ADR-006: Dual-Assignment Model in the Orchestrator

**Status:** Accepted
**Date:** 2025-09-01

## Context

Complex FDA regulatory tasks require two distinct knowledge domains:
- **Domain expertise:** RA-specific knowledge — CFR requirements, FDA guidance
  documents, predicate strategy, substantial equivalence argumentation.
- **Technical expertise:** Code and data knowledge — which files exist, how
  schemas are structured, what transformations are safe, how to avoid regressions.

A single agent prompted as a "regulatory AI assistant" tends to be authoritative
on domain knowledge but makes unsafe assumptions about code state. Conversely, a
code-focused agent may produce technically correct changes that violate regulatory
conventions it was not trained to prioritize.

Assigning both roles to one agent creates a context-overload problem: the agent
must simultaneously reason about regulatory correctness and code correctness,
leading to gaps in both.

## Decision

Each orchestrator task is assigned to two agents in parallel:
- **Primary agent:** Domain expert framing — answers "is this regulatorily correct?"
- **Delegate agent:** Technical expert framing — answers "is this code correct and
  safe to run?"

Both agents report to the orchestrator. Conflicts between their assessments trigger
an explicit resolution step before the task is marked complete.

## Alternatives Considered

- **Single agent per task:** Simpler orchestration. Rejected because empirical
  testing showed consistent blind spots at the domain/technical boundary —
  agents either produced correct code that violated regulatory logic or correct
  regulatory logic with broken code.
- **Pure specialist teams (3+ agents):** RA specialist, code specialist, QA
  specialist. Rejected because the integration step between three independent
  outputs adds latency and the marginal gain over dual-assignment is small.
- **Human-in-the-loop for every decision:** Maximum correctness but unacceptably
  slow for batch workflows. Reserved for final human review, not intermediate steps.

## Consequences

- Task latency is higher (parallel agents, then conflict resolution if needed).
- Orchestrator prompt complexity increases; must define clear handoff protocol.
- The model is well-suited to tasks with a clear domain/technical split; less
  useful for purely technical or purely regulatory tasks where single-agent suffices.
- Conflict resolution logic must be explicit; silent majority-vote is prohibited.
