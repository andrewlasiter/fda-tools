"""
FDA-267  [ORCH-014] Orchestrator Structured Observability
==========================================================
Structured telemetry for the MDRP orchestrator.  Uses an optional-import
pattern: if the OpenTelemetry SDK is installed the ``span()`` context manager
emits real distributed traces; otherwise it is a transparent no-op.  All
metric recording is always available in-process via the ``MetricPoint`` list.

Design principles (mirrors local_llm.py's optional-import pattern)
------------------------------------------------------------------
1. Zero hard dependencies — no ``opentelemetry`` package required.
2. No-op fallback for every SDK call — the orchestrator always runs.
3. ``health_status()`` returns a plain dict suitable for a FastAPI endpoint.
4. ``metrics()`` returns a list of ``MetricPoint`` records for Prometheus
   export or in-process inspection in tests.

Usage
-----
    tel = OrchestratorTelemetry(service_name="mdrp-orchestrator")

    with tel.span("agent_selection", task_type="security_review"):
        team = selector.select_review_team(profile)
        tel.record_agent_selection("security-auditor", score=0.9, latency_ms=45.0)

    tel.record_phase_complete(phase=1, agent_count=3, duration_ms=8200.0, finding_count=5)
    tel.record_run_complete(success=True, total_findings=5)

    status = tel.health_status()   # → dict for GET /health/orchestrator
    pts    = tel.metrics()         # → List[MetricPoint]
"""

from __future__ import annotations

import contextlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, List, Optional

logger = logging.getLogger(__name__)

# Optional OpenTelemetry — no-op if SDK not installed
try:
    from opentelemetry import trace as _otel_trace  # type: ignore[import]
    _OTEL_AVAILABLE = True
except ImportError:
    _OTEL_AVAILABLE = False
    _otel_trace = None  # type: ignore[assignment]


# ── Value object ──────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class MetricPoint:
    """
    A single recorded metric observation.

    Attributes:
        name:      Prometheus-style metric name (e.g. "orchestrator_runs_total").
        value:     Numeric value of the observation.
        timestamp: UTC ISO 8601 timestamp of the observation.
        labels:    Dimension labels (e.g. {"phase": "1", "agent_id": "python-pro"}).
    """
    name:      str
    value:     float
    timestamp: str
    labels:    Dict[str, str]


# ── Telemetry class ───────────────────────────────────────────────────────────

@dataclass
class OrchestratorTelemetry:
    """
    Structured telemetry for the MDRP orchestrator.

    All recording methods are safe to call even when OpenTelemetry is absent.
    Metric points are stored in-process and can be exported via ``metrics()``.

    Attributes:
        service_name: OpenTelemetry service name (default "mdrp-orchestrator").
    """

    service_name: str = "mdrp-orchestrator"

    _metrics:               List[MetricPoint] = field(default_factory=list, init=False, repr=False)
    _run_count:             int               = field(default=0,    init=False)
    _last_run_timestamp:    Optional[str]     = field(default=None, init=False)
    _circuit_breaker_state: str               = field(default="CLOSED", init=False)
    _active_agents:         List[str]         = field(default_factory=list, init=False)

    # ── Span context manager ──────────────────────────────────────────────────

    @contextlib.contextmanager
    def span(self, name: str, **attributes: Any) -> Iterator[None]:
        """
        Context manager that creates an OpenTelemetry span when available.

        If the SDK is not installed this is a transparent no-op.  Attributes
        are set as span attributes when the SDK is available.
        """
        if _OTEL_AVAILABLE and _otel_trace is not None:
            tracer = _otel_trace.get_tracer(self.service_name)
            with tracer.start_as_current_span(name) as active_span:
                for k, v in attributes.items():
                    active_span.set_attribute(k, str(v))
                yield
        else:
            yield

    # ── Private record helper ─────────────────────────────────────────────────

    def _record(
        self,
        name:   str,
        value:  float,
        labels: Optional[Dict[str, str]] = None,
    ) -> MetricPoint:
        pt = MetricPoint(
            name      = name,
            value     = value,
            timestamp = datetime.now(timezone.utc).isoformat(),
            labels    = labels or {},
        )
        self._metrics.append(pt)
        return pt

    # ── Public recording methods ──────────────────────────────────────────────

    def record_agent_selection(
        self,
        agent_id:   str,
        score:      float,
        latency_ms: float,
    ) -> None:
        """Record that an agent was selected with a given relevance score and latency."""
        lbl = {"agent_id": agent_id}
        self._record("orchestrator_agents_selected", 1.0, lbl)
        self._record("orchestrator_agent_selection_score", score, lbl)
        self._record("orchestrator_agent_selection_latency_ms", latency_ms, lbl)

    def record_phase_complete(
        self,
        phase:         int,
        agent_count:   int,
        duration_ms:   float,
        finding_count: int,
    ) -> None:
        """Record completion of one orchestrator execution phase."""
        lbl = {"phase": str(phase)}
        self._record("orchestrator_phase_duration_seconds", duration_ms / 1000.0, lbl)
        self._record("orchestrator_phase_agents", float(agent_count), lbl)
        self._record("orchestrator_phase_findings", float(finding_count), lbl)

    def record_run_start(self) -> None:
        """Record that a new orchestrator workflow run has started."""
        self._record("orchestrator_runs_total", 1.0)

    def record_run_complete(self, success: bool, total_findings: int) -> None:
        """Record the outcome of a completed orchestrator run."""
        self._run_count += 1
        self._last_run_timestamp = datetime.now(timezone.utc).isoformat()
        self._record("orchestrator_run_success", 1.0 if success else 0.0)
        self._record("orchestrator_run_findings_total", float(total_findings))

    def set_circuit_breaker_state(self, state: str) -> None:
        """
        Record a circuit breaker state change.

        Args:
            state: One of "CLOSED", "OPEN", or "HALF_OPEN".
        """
        self._circuit_breaker_state = state
        self._record(
            "orchestrator_circuit_breaker_state",
            1.0 if state == "CLOSED" else 0.0,
            {"state": state},
        )

    def set_active_agents(self, agents: List[str]) -> None:
        """Update the list of currently active agents and record a metric."""
        self._active_agents = list(agents)
        self._record("orchestrator_active_agents", float(len(agents)))

    # ── Inspection ────────────────────────────────────────────────────────────

    def health_status(self) -> Dict[str, Any]:
        """
        Return a dict suitable for a GET /health/orchestrator FastAPI endpoint.

        Keys:
            service                — service name
            circuit_breaker_state  — CLOSED / OPEN / HALF_OPEN
            run_count              — total completed runs this session
            last_run_timestamp     — ISO 8601 UTC of last completed run
            active_agents          — list of currently active agent IDs
            metrics_recorded       — total MetricPoint observations stored
        """
        return {
            "service":               self.service_name,
            "circuit_breaker_state": self._circuit_breaker_state,
            "run_count":             self._run_count,
            "last_run_timestamp":    self._last_run_timestamp,
            "active_agents":         list(self._active_agents),
            "metrics_recorded":      len(self._metrics),
        }

    def metrics(self) -> List[MetricPoint]:
        """Return a copy of all recorded MetricPoints."""
        return list(self._metrics)

    def metrics_by_name(self, name: str) -> List[MetricPoint]:
        """Return all MetricPoints with the given name."""
        return [m for m in self._metrics if m.name == name]

    def reset(self) -> None:
        """Clear all stored metrics and reset counters (useful in tests)."""
        self._metrics.clear()
        self._run_count = 0
        self._last_run_timestamp = None
        self._circuit_breaker_state = "CLOSED"
        self._active_agents.clear()
