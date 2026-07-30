"""External model-trace correlation for replay dimension 3 (D-IMPL-45).

SDK-defined mechanism, marked as an **extension** of the whitepaper's replay
commitment (whitepaper §7.10.2, INV-CH7-86; CLAUDE.md §7.3 seam 4): a mature
deployment composes CCF environment replay with an external model-trace tool
(LangSmith/Weave), and the seam is a *stored correlation, never an ingestion*
— CCF owns environment replay; the external tool owns model-internals tracing.

This module discharges the I.3 handoff (``docs/PHASE_I3_GATE.md`` §5:
"``TraceCorrelationHook`` attaches to the ``harness_trace`` slot in I.4").
The attachment point is the *existing* dimension-3
:class:`~ccf.replay.record.HarnessTrace` slot, whose ``trace_provider`` and
``trace_id`` fields were shaped for exactly this hook (D-IMPL-55): the hook
mints no new record field, no new dimension, no new sentinel. INV-CH7-80
keeps the five dimensions inviolate, and the five-dimension structural
assertion in ``tests/replay`` fails if this module ever grows a slot.

Correlation is captured at **build time only** — the enriched trace is passed
to :func:`~ccf.replay.record.build_replay_record` as the pre-serialized
verbatim block the builder already accepts, and nothing here runs at
replay-read time. A correlation looked up at read time would describe the
provider's state at reading time, not at decision time — the same doctrine
that keeps every other block verbatim.

Byte-identity is claimed at the scope it earns (D-21): the no-op reference
provider correlates nothing, so the hook returns the reported trace unchanged
— byte for byte.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ccf.contracts.base import CCFContract
from ccf.replay.record import HarnessTrace

__ccf_mode__ = "algorithmic"

__all__ = [
    "ExternalTraceProviderProtocol",
    "NoOpTraceProvider",
    "TraceCorrelation",
    "TraceCorrelationHook",
]


class TraceCorrelation(CCFContract):
    """The correlation payload an external trace provider reports (D-IMPL-45).

    Exactly the two values the dimension-3 slot already carries: which
    provider holds the model-internals trace, and the provider-scoped
    identifier that resolves it there. A payload wider than the slot would be
    an ingestion, which the D-IMPL-45 ruling excludes by construction.
    """

    trace_provider: str
    trace_id: str


@runtime_checkable
class ExternalTraceProviderProtocol(Protocol):
    """What an external model-trace provider must offer (D-IMPL-45).

    One obligation: produce the correlation payload for a given execution
    reference at call time — or ``None`` when the provider holds no trace for
    it, in which case the trace's own (sentinel) values stay in force.
    Protocol-based per CLAUDE.md §11; implementations bind LangSmith, Weave,
    or any other tracer without this module naming a vendor.
    """

    def correlate(self, *, execution_ref: str) -> TraceCorrelation | None:
        """Return the correlation for ``execution_ref``, or ``None``."""
        ...


class NoOpTraceProvider:
    """Reference implementation that correlates nothing (D-IMPL-45).

    Ships alongside the Protocol per CLAUDE.md §11, and is honest about what
    it is: a deployment with no external tracer configured correlates to
    nothing, so the hook leaves every trace byte-identical. It is the
    no-tracer reference implementation, not a placeholder for one — a real
    tracer is an alternative implementation of the same Protocol, added
    without touching a consumer.
    """

    def correlate(self, *, execution_ref: str) -> TraceCorrelation | None:
        """No external tracer, no correlation — ``None``, always."""
        return None


class TraceCorrelationHook:
    """Composes a provider's correlation into the dimension-3 slot (D-IMPL-45).

    Runs at the Harness Adapter's replay-hooks seam (CLAUDE.md §7.3 seam 4),
    BEFORE the trace block is passed to
    :func:`~ccf.replay.record.build_replay_record`: the enriched
    :class:`~ccf.replay.record.HarnessTrace` is what the builder records
    verbatim, so the correlation is decision-time state by construction and
    nothing here ever runs at replay-read time.

    The hook writes only the two trace-reference fields the slot reserved for
    it — never ``harness_id``, ``model_version``, or the token counts, which
    stay what the harness reported (T-06-62's discipline, one seam over).
    """

    def __init__(self, *, provider: ExternalTraceProviderProtocol) -> None:
        self._provider = provider

    def enrich(self, trace: HarnessTrace, *, execution_ref: str) -> HarnessTrace:
        """Return ``trace`` with the provider's correlation composed in.

        When the provider reports no correlation, the trace passes through
        unchanged — byte-identical, so enrich-nothing means change-nothing.
        """
        correlation = self._provider.correlate(execution_ref=execution_ref)
        if correlation is None:
            return trace
        return HarnessTrace(
            harness_id=trace.harness_id,
            model_version=trace.model_version,
            trace_provider=correlation.trace_provider,
            trace_id=correlation.trace_id,
            input_tokens=trace.input_tokens,
            output_tokens=trace.output_tokens,
        )
