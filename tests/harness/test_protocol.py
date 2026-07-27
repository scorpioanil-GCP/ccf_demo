"""Structural properties of `HarnessAdapterProtocol` (CLAUDE.md §7.3; D-IMPL-25).

These are the tests the three reference adapters in 06-12 through 06-14 are
written against, so they pin the *shape* of the seam rather than any behavior:
what the Protocol declares, what it deliberately does not, and what an adapter
must state about itself before the conformance suite will drive it.

Per the I.2 D-03 boundary, the minimal adapter below is a **test** double and
lives here — never in `/src` or `/runtime`. It exists to prove the Protocol is
satisfiable and `runtime_checkable`; the real conformance suite (D-09) runs
against the real SDKs with no LLM calls and no doubles, because a double
written to the Protocol we designed can pass while the real surface disagrees.
"""

from __future__ import annotations

import inspect
from collections.abc import Mapping
from typing import Any

import pytest
from pydantic import ValidationError

import ccf.harness.protocol as protocol_module
from ccf.agents.agent import Agent, EmittedEffect
from ccf.harness.protocol import (
    EFFECT_CAPABILITIES,
    EffectRefusal,
    HarnessAdapterProtocol,
    HarnessCapabilities,
)
from ccf.products.contract import ContextProductContract
from ccf.replay.record import NO_HARNESS, HarnessTrace

#: Names of fabric surfaces that must never appear on the adapter seam. A
#: source scan rather than a signature scan on purpose: a type mentioned in a
#: docstring, a comment, or an unused import is a type someone was thinking
#: about handing to an adapter, and the seam's whole claim is that `Agent` is
#: the only fabric-side input (T-06-61, extending T-02-26).
FORBIDDEN_FABRIC_SURFACES = (
    "FabricHandle",
    "GraphWriter",
    "GraphReader",
    "GraphStore",
    "ControlPlaneRegistry",
    "AssemblyWorker",
)


class _MinimalAdapter:
    """The smallest thing that satisfies the Protocol — a read-only consumer.

    Declares ``effects: unsupported``, so every output is refused. D-10 makes
    that declaration only half the requirement; the *inert* half is proven by
    the real conformance suite in 06-14, not here.
    """

    def capabilities(self) -> HarnessCapabilities:
        return HarnessCapabilities(harness_id="minimal", effects="unsupported")

    def inject_context(
        self,
        *,
        agent: Agent,
        products: tuple[ContextProductContract, ...],
        instructions: tuple[str, ...],
    ) -> object:
        return {"instructions": instructions, "products": products}

    def expose_skills(self, *, agent: Agent) -> tuple[str, ...]:
        return agent.bound_skill_names

    def capture_effect(
        self, *, agent: Agent, output: Mapping[str, Any]
    ) -> EmittedEffect | EffectRefusal:
        return EffectRefusal(
            harness_id="minimal",
            agent_definition_hash=agent.identity.definition_hash,
            reason="this adapter declares effects: unsupported",
        )

    def replay_trace(self, *, execution: object) -> HarnessTrace:
        return HarnessTrace(harness_id="minimal")


# --------------------------------------------------------------------------
# The Protocol's declared shape
# --------------------------------------------------------------------------


def test_the_protocol_is_runtime_checkable_and_satisfiable() -> None:
    """An implementation that binds the four seams conforms structurally."""
    assert isinstance(_MinimalAdapter(), HarnessAdapterProtocol)


def test_an_incomplete_adapter_does_not_conform() -> None:
    """`runtime_checkable` verifies method presence — a missing seam is caught."""

    class _MissingReplayHooks:
        def capabilities(self) -> HarnessCapabilities:  # pragma: no cover
            raise NotImplementedError

        def inject_context(self, **kwargs: Any) -> object:  # pragma: no cover
            raise NotImplementedError

        def expose_skills(self, **kwargs: Any) -> tuple[str, ...]:  # pragma: no cover
            raise NotImplementedError

        def capture_effect(self, **kwargs: Any) -> object:  # pragma: no cover
            raise NotImplementedError

    assert not isinstance(_MissingReplayHooks(), HarnessAdapterProtocol)


def test_the_four_seams_are_declared() -> None:
    """CLAUDE.md §7.3: context injection, skill exposure, effect capture, replay."""
    declared = set(HarnessAdapterProtocol.__protocol_attrs__)
    assert declared == {
        "capabilities",
        "inject_context",
        "expose_skills",
        "capture_effect",
        "replay_trace",
    }


def test_every_seam_is_keyword_only_with_an_ellipsis_body() -> None:
    """Protocol conventions: no positional-by-accident, no fake implementation."""
    source = inspect.getsource(protocol_module)
    assert "raise NotImplementedError" not in source

    for name in ("inject_context", "expose_skills", "capture_effect", "replay_trace"):
        signature = inspect.signature(getattr(HarnessAdapterProtocol, name))
        for parameter_name, parameter in signature.parameters.items():
            if parameter_name == "self":
                continue
            assert parameter.kind is inspect.Parameter.KEYWORD_ONLY, (
                f"{name}.{parameter_name} is not keyword-only"
            )


# --------------------------------------------------------------------------
# What the seam deliberately omits (T-06-61)
# --------------------------------------------------------------------------


def test_the_only_fabric_side_input_is_agent() -> None:
    """No fabric boot handle, registry, or graph handle reaches an adapter.

    The claim is scoped to what this test enforces (D-21): the *declared
    surface* names no such type. It is not a claim that no path exists — that
    would need a transitive-closure argument this surface has not made.
    """
    source = inspect.getsource(protocol_module)
    for forbidden in FORBIDDEN_FABRIC_SURFACES:
        assert forbidden not in source, (
            f"{forbidden!r} appears in the harness seam; the adapter's"
            " fabric-side input is Agent and nothing more (T-06-61)"
        )


def test_the_seam_imports_no_harness_package() -> None:
    """CLAUDE.md §7.3: zero harness imports in core, and this is core."""
    source = inspect.getsource(protocol_module)
    for token in ("import langgraph", "import claude_agent_sdk", "google.adk"):
        assert token not in source
    assert protocol_module.__ccf_mode__ == "algorithmic"


def test_agents_does_not_import_the_harness_package() -> None:
    """The dependency runs seam → agent, never the reverse.

    This is why the plan widens no ``ALLOWED_CCF_PREFIXES`` entry: ``ccf.harness``
    never enters ``ccf.agents``' import closure, so ``test_consumption_discipline``
    is unaffected and owes no new transitive-closure argument (D-22).
    """
    import ccf.agents

    assert "ccf.harness" not in inspect.getsource(ccf.agents)
    for module in (ccf.agents.agent, ccf.agents.factory):  # type: ignore[attr-defined]
        assert "ccf.harness" not in inspect.getsource(module)


# --------------------------------------------------------------------------
# The capability declaration (D-IMPL-25, D-10)
# --------------------------------------------------------------------------


def test_the_effects_capability_must_be_stated_explicitly() -> None:
    """Omitting it raises rather than defaulting.

    A defaulted capability would let an adapter that never considered effect
    capture inherit a claim about it — exactly the difference D-IMPL-25 draws
    between a conformance-verified absence and an unimplemented seam.
    """
    with pytest.raises(ValidationError):
        HarnessCapabilities(harness_id="minimal")  # type: ignore[call-arg]


def test_unsupported_is_a_declared_value_not_a_missing_field() -> None:
    """D-10: the absence is something the adapter *says*, positively."""
    declared = _MinimalAdapter().capabilities()
    assert declared.effects == "unsupported"
    assert "effects" in declared.model_dump()
    assert declared.model_dump()["effects"] == "unsupported"
    assert set(EFFECT_CAPABILITIES) == {"governed", "unsupported"}


def test_the_capability_contract_rejects_an_unknown_field() -> None:
    """``extra=forbid``: adapter and fabric disagreeing is not an extension point."""
    with pytest.raises(ValidationError):
        HarnessCapabilities(
            harness_id="minimal",
            effects="unsupported",
            supports_streaming=True,  # type: ignore[call-arg]
        )


def test_an_unknown_effects_value_is_refused() -> None:
    """The capability vocabulary is closed."""
    with pytest.raises(ValidationError):
        HarnessCapabilities(harness_id="minimal", effects="best-effort")  # type: ignore[arg-type]


# --------------------------------------------------------------------------
# Effect capture and replay hooks return typed CCF values
# --------------------------------------------------------------------------


def test_a_refusal_is_a_returned_value_not_an_exception() -> None:
    """The SDK's established refusal discipline, held at this seam too."""
    assert not issubclass(EffectRefusal, BaseException)
    refusal = EffectRefusal(
        harness_id="minimal", agent_definition_hash="abc", reason="unsupported"
    )
    assert refusal.harness_id == "minimal"
    assert refusal.agent_definition_hash == "abc"
    # Frozen and closed-world like every other CCF contract: a refusal is a
    # value the caller inspects and audits, not mutable state.
    with pytest.raises(ValidationError):
        EffectRefusal(  # type: ignore[call-arg]
            harness_id="minimal",
            agent_definition_hash="abc",
            reason="unsupported",
            retryable=True,
        )


def test_the_replay_seam_returns_the_dimension_three_block() -> None:
    """Seam 4 writes into ``harness_trace`` and nowhere else (D-25, T-06-62)."""
    trace = _MinimalAdapter().replay_trace(execution=object())
    assert isinstance(trace, HarnessTrace)
    assert trace.harness_id == "minimal"
    # Fields the adapter could not determine stay at the positive sentinel
    # rather than being guessed (T-06-63).
    assert trace.trace_id == NO_HARNESS
    assert trace.trace_provider == NO_HARNESS
