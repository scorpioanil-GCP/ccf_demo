"""`D-IMPL-389` (gap 3) — a composite decision replays from its record alone through ``OpenedProduct.replay_decision``.

Dave, 2026-10-17 01:46 MST, verbatim: *"The one-step replay command must be able
to replay a composite decision from the record alone. Supply the missing
`resolve_composite_plan` step in the setup that `serve.py replay` builds, so the
engine's existing composite path is reachable. No change to the record format
or to the engine's composite logic."* The setup is
:class:`~ccf.replay.environment.RecordedEnvironment`, which
``OpenedProduct.replay_decision`` builds.

Held over the paved consumer fixture (``tests/products/test_paved_consumer.py``):
a composite parent asking the paved child producer in ANOTHER process over
loopback MCP; SQLite substrates under ``tmp_path``; no estate. Every test
TERMINATES the producer before it replays, so a replay that asked a provider
could not pass. Every replay is read through :func:`_replayed`, which returns
what was raised instead of raising it: today's ``ReplayUnresolvable`` (and any
partial fix's ``ReplayDivergence``) fails an ASSERTION naming it, never an error.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import pathlib
import uuid
from collections.abc import Iterator
from datetime import timedelta
from typing import Any

import pytest

from ccf.contracts.canonical import content_hash
from ccf.products.composite import ChildContractView
from ccf.products.contract import SUBJECT_WITHHOLDING_NEVER
from ccf.products.product import OpenedProduct
from ccf.products.refusal import RefusalEnvelope
from ccf.products.request import ProductRequest
from ccf.replay.engine import CompositeReplayEnvironment, RefusalReplayOutcome, ReplayOutcome
from ccf.replay.environment import RecordedEnvironment
from ccf.replay.record import NO_FABRIC_READ
from ccf.replay.serve import ServedProduct
from ccf_runtime.cli import evidence as inspection
from tests.products import paved_fixture as fixture
from tests.products.test_paved_consumer import DEV_TOKEN, _open, _producer, _question, _tree
from tests.products.test_paved_optional_child_switch import _ask, _config, _plane, _Switch

pytestmark = [pytest.mark.crossproc]

#: Where the child-aware plan surfaces the CHILD's own value, read off the retained contract.
CHILD_VALUE_KEY = "child_threshold"
#: What that key reads when no child reached the plan — a value, never a raise, so a
#: severing that withholds the children diverges rather than errors.
NO_CHILD = "no-child-reached-the-plan"


# --- a child-aware factory: implements BOTH seams, reads the child's payload ---------------


class _ReadsTheChild:
    def __init__(self, inner: Any, children: ChildContractView) -> None:
        self._inner, self._children = inner, children

    @property
    def plan_id(self) -> str:
        return str(self._inner.plan_id)

    def required_operators(self) -> tuple[str, ...]:
        return tuple(self._inner.required_operators())

    def invoke(self, **kw: Any) -> Any:
        out = self._inner.invoke(**kw)
        child = self._children.get(fixture.CHILD_CLASS)
        payload = dict(out.payload)
        payload[CHILD_VALUE_KEY] = child.payload["threshold"] if child is not None else NO_CHILD
        return out.model_copy(update={"payload": payload})


class _ChildAwareFactory:
    """`CompositePlanFactoryProtocol` structurally, plus the plain seam; records which ran."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def __call__(self, *, required: tuple[str, ...], request: ProductRequest) -> Any:
        self.calls.append("plain")
        return fixture.plan_factory(required=required, request=request)

    def build_with_children(
        self, *, required: tuple[str, ...], request: ProductRequest, children: ChildContractView
    ) -> Any:
        self.calls.append("children")
        return _ReadsTheChild(fixture.plan_factory(required=required, request=request), children)

    def withholds_no_subject(self) -> bool:
        """Dave's E2 (ii) (d): neither seam's projection sets the withheld signal."""
        return True


# --- helpers -------------------------------------------------------------------------------


def _replayed(opened: OpenedProduct, address: str) -> Any:
    """What ``replay_decision`` returned — or what it raised, for the assertion to name."""
    try:
        return opened.replay_decision(address)
    except Exception as raised:  # noqa: BLE001 — reported by the caller's assertion, never swallowed
        return raised


def _address(opened: OpenedProduct, outcome: Any) -> str:
    if isinstance(outcome, ServedProduct):
        return outcome.replay_ref.content_address
    assert isinstance(outcome, RefusalEnvelope), outcome
    return opened.artifact_store.resolve_uri(uri=outcome.replay_reference)


@contextlib.contextmanager
def _decided(
    tmp_path: pathlib.Path, *, config: dict[str, Any] | None = None, **overrides: Any
) -> Iterator[tuple[OpenedProduct, Any, str]]:
    """One composite decision, taken with the producer UP; yielded with the producer TERMINATED."""
    root = _tree(tmp_path, config=config)
    with contextlib.ExitStack() as stack:
        producer = stack.enter_context(contextlib.ExitStack())
        url = producer.enter_context(_producer())
        opened = stack.enter_context(
            _open(root, tmp_path / "scratch", url, evidence_root=tmp_path / "evidence", **overrides)
        )
        outcome = opened.answer(_question(opened))
        address = _address(opened, outcome)
        producer.close()  # the producer process exits HERE; nothing below can reach it
        yield opened, outcome, address


def _admitted_row(opened: OpenedProduct, outcome: Any) -> Any:
    rows = opened.record_of(outcome).content_generation_path.child_resolutions
    assert [row.outcome_status for row in rows] == ["admitted"], "premise: the composite admitted its one child"
    return rows[0]


# --- 0. the seam, structurally ----------------------------------------------------------------


def test_the_recorded_environment_implements_the_engines_composite_seam() -> None:
    assert issubclass(RecordedEnvironment, CompositeReplayEnvironment), (
        "RecordedEnvironment does not implement `resolve_composite_plan`, so the engine refuses"
        " every composite record it is handed (engine `_re_execute`, D-IMPL-339)"
    )


# --- 1. served composites reproduce ------------------------------------------------------------


def test_a_served_composite_replays_from_its_record_alone(tmp_path: pathlib.Path) -> None:
    with _decided(tmp_path) as (opened, served, address):
        assert isinstance(served, ServedProduct), getattr(served, "detail", served)
        _admitted_row(opened, served)
        record = opened.record_of(served)
        outcome = _replayed(opened, address)
    assert isinstance(outcome, ReplayOutcome), f"the composite decision did not replay: {outcome!r}"
    assert outcome.record_content_address == address
    assert outcome.product_content_address == record.content_generation_path.product_content_address
    assert outcome.product_content_address == content_hash(served.product)
    assert outcome.graph_snapshot_id == record.context_fabric_snapshot.graph_snapshot_id


def test_a_child_aware_plan_is_rebuilt_over_the_retained_children_as_the_serve_built_it(
    tmp_path: pathlib.Path,
) -> None:
    factory = _ChildAwareFactory()
    with _decided(tmp_path, project=factory) as (opened, served, address):
        assert isinstance(served, ServedProduct), getattr(served, "detail", served)
        assert served.product.payload[CHILD_VALUE_KEY] == "1000", "premise: the parent's payload read its child"
        assert factory.calls == ["children"], "premise: the serve called build_with_children"
        outcome = _replayed(opened, address)
    assert isinstance(outcome, ReplayOutcome), f"the composite decision did not replay: {outcome!r}"
    assert outcome.product_content_address == content_hash(served.product)
    assert outcome.product.payload[CHILD_VALUE_KEY] == "1000"
    assert factory.calls == ["children", "children"], (
        f"replay did not rebuild the plan through the seam the serve used: {factory.calls}"
    )


def test_a_composite_whose_child_expiry_binds_reproduces_its_floored_expiry(tmp_path: pathlib.Path) -> None:
    config = fixture.consumer_config(subject_withholding=SUBJECT_WITHHOLDING_NEVER)
    # The parent's own window (1200 s) outlives the child's (the producer's 600 s), so the
    # served expiry is the CHILD's: `D-IMPL-336` F14's floor, not the parent's own term.
    config["ttl"] = {"max_ttl_seconds": 3600, "product_ttl_seconds": 1200}
    with _decided(tmp_path, config=config) as (opened, served, address):
        assert isinstance(served, ServedProduct), getattr(served, "detail", served)
        row = _admitted_row(opened, served)
        anchor = opened.record_of(served).content_generation_path.ttl_anchor_at
        outcome = _replayed(opened, address)
    assert anchor is not None and row.child_expires_at is not None
    assert served.product.expires_at == row.child_expires_at < anchor + timedelta(seconds=1200), (
        "premise: the child's expiry binds the composite, not the parent's own window"
    )
    assert isinstance(outcome, ReplayOutcome), f"the composite decision did not replay: {outcome!r}"
    assert outcome.product.expires_at == row.child_expires_at
    assert outcome.product_content_address == content_hash(served.product)


# --- 2. refused composites reproduce ------------------------------------------------------------


def test_a_composite_refused_after_projection_replays_its_refusal(tmp_path: pathlib.Path) -> None:
    config = fixture.consumer_config(subject_withholding=SUBJECT_WITHHOLDING_NEVER)
    config["product_class"]["declared_product_gate"] = {"gate_id": "fixture.gate", "gate_version": "1.0.0"}

    def _refuses(*, candidate: Any, evidence: Any = None) -> str:
        return "this fixture's declared gate refuses every candidate"

    with _decided(tmp_path, config=config, gate=_refuses) as (opened, refused, address):
        assert isinstance(refused, RefusalEnvelope) and refused.kind == "product-invariant-refusal", refused
        row = _admitted_row(opened, refused)
        record = opened.record_of(refused)
        assert record.content_generation_path.plan_id != NO_FABRIC_READ, "premise: refused AFTER projection"
        outcome = _replayed(opened, address)
    assert isinstance(outcome, RefusalReplayOutcome), f"the refused composite did not replay: {outcome!r}"
    assert outcome.graph_snapshot_id == record.context_fabric_snapshot.graph_snapshot_id
    assert outcome.child_contract_addresses == (row.child_content_address,)


def test_control_a_composite_refused_before_projection_replays_without_a_plan(tmp_path: pathlib.Path) -> None:
    """A CONTROL, green before the fix: the engine's no-read refusal path consults no environment."""
    config = fixture.consumer_config(
        compatible_from="1.5.0",
        producers={"child": fixture.producer_section(versions_from="1.5.0")},
        subject_withholding=SUBJECT_WITHHOLDING_NEVER,
    )
    with _decided(tmp_path, config=config) as (opened, refused, address):
        assert isinstance(refused, RefusalEnvelope), refused
        outcome = _replayed(opened, address)
    assert isinstance(outcome, RefusalReplayOutcome), f"the no-read refusal did not replay: {outcome!r}"
    assert outcome.graph_snapshot_id == NO_FABRIC_READ


# --- 3. the one-step command, after a restart --------------------------------------------------


def test_the_replay_verb_reproduces_a_composite_after_a_restart(tmp_path: pathlib.Path) -> None:
    root = _tree(tmp_path)
    evidence = tmp_path / "evidence"
    with _producer() as url, _open(root, tmp_path / "first", url, evidence_root=evidence) as opened:
        served = opened.answer(_question(opened))
        assert isinstance(served, ServedProduct), getattr(served, "detail", served)
        address = served.replay_ref.content_address
    # A restarted auditor: a fresh scratch, no source settings, and a producer address
    # nothing listens on (the opening reads the producer's NAMES; replay asks no producer).
    dead = {fixture.ENDPOINT_VAR: "http://127.0.0.1:9/mcp", fixture.CREDENTIAL_VAR: DEV_TOKEN}
    out = io.StringIO()
    with _open(
        root, tmp_path / f"restart-{uuid.uuid4().hex}", "unused", evidence_root=evidence,
        read_sources=False, environ=dead,
    ) as reopened:
        try:
            status: Any = inspection.run(argparse.Namespace(command="replay", decision=address), reopened, out=out)
        except Exception as raised:  # noqa: BLE001 — reported by the assertion below
            status = raised
    assert status == inspection.ANSWERED, f"the replay verb did not answer: {status!r} {out.getvalue()!r}"
    assert out.getvalue().startswith("REPRODUCED:"), out.getvalue()
    assert content_hash(served.product) in out.getvalue()


# --- 4. a composite whose optional child was absent, under a child-aware factory (option (c)) ---


def test_a_composite_that_admitted_no_child_replays_through_the_seam_the_serve_used(
    tmp_path: pathlib.Path,
) -> None:
    """The serve handed the child-aware factory an EMPTY view; replay must make the same call."""
    factory = _ChildAwareFactory()
    root = _tree(tmp_path, config=_config(required=False))
    with contextlib.ExitStack() as stack:
        producer = stack.enter_context(contextlib.ExitStack())
        url = producer.enter_context(_producer())
        opened = stack.enter_context(
            _open(
                root, tmp_path / "scratch", url, evidence_root=tmp_path / "evidence",
                control_plane=_plane(), questions=fixture.questions, build_children=_Switch, project=factory,
            )
        )
        served = _ask(opened, switch=None)
        assert isinstance(served, ServedProduct), getattr(served, "detail", served)
        rows = opened.record_of(served).content_generation_path.child_resolutions
        assert [row.outcome_status for row in rows] == ["optional-absent"], "premise: the walk admitted no child"
        assert factory.calls == ["children"], "premise: the serve called build_with_children over an empty view"
        assert served.product.payload[CHILD_VALUE_KEY] == NO_CHILD
        producer.close()
        outcome = _replayed(opened, served.replay_ref.content_address)
    assert isinstance(outcome, ReplayOutcome), f"the composite decision did not replay: {outcome!r}"
    assert outcome.product_content_address == content_hash(served.product)
    assert factory.calls == ["children", "children"], (
        f"replay did not rebuild the plan through the seam the serve used: {factory.calls}"
    )
