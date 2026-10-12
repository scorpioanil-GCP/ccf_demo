"""The paved road honors a declared demonstration serve instant when the caller composed no clock (G1-SDK-01).

**SDK-defined** (CLAUDE.md §11). `D-IMPL-378` C1 gave a deployment a way to
declare a fixed, explicitly labeled DEVELOPMENT serve instant
(``demonstration_serve_instant:``). Until this round the paved road could never
use it: :func:`~ccf.products.product.open_product` defaulted its clock to its own
``_utc_now``, the resolver compared that clock BY IDENTITY with its own
``_utc_now``, and the two were different function objects, so every paved
deployment that declared an instant and composed no clock was refused with
:class:`~ccf.products.demonstration_clock.DemonstrationServeInstantConflict`
("this composition supplies its own clock"), which was not true (Dave,
2026-10-11 16:23 MST, ruling 4 and the clock fix ruling 1 depends on).

What these tests hold, in one module, permitted beside refused:

* a paved deployment that DECLARES an instant in its ``ccf_config.yaml`` and
  composes NO clock serves its dated question at that instant, and the record
  pins the declaration;
* the same declaration beside a caller-composed clock is still refused by name
  (one serve instant, one authority);
* a store that is not the SDK's own development store is still refused, even
  wrapped in the SDK's erasure consult;
* a question older than the declared instant's temporal window is still refused
  as an ordinary governed refusal (the expiry check is not disabled);
* without the declaration the same dated question is refused against the real
  clock;
* a second declaration beside the document's is refused, never a silent winner.
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest

from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.protocol import WriteKinds
from ccf.authz.capability import ReplayMint
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.products.contract import SUBJECT_WITHHOLDING_NEVER
from ccf.products.demonstration_clock import (
    DeclaredServeClock,
    DemonstrationServeInstantConflict,
    DemonstrationServeInstantRefused,
)
from ccf.products.product import open_product
from ccf.products.refusal import RefusalEnvelope
from ccf.replay.serve import ServedProduct

from tests.composition import declared_erasure_trust
from tests.products import paved_fixture as fixture

#: The declared demonstration serve instant: seven minutes after the fixture's
#: dated question, inside its declared product lifetime (600 s).
DECLARED = fixture.ADMITTED_AT

DEMONSTRATION_KEY_SUFFIX = "ccf.demonstration-serve-instant"


class _NotTheSdkStore(FileArtifactStore):
    """A subclass of the SDK's file store that overrides nothing (decision 4 (a) refuses it)."""


def _tree(tmp_path: Path, *, declare: bool) -> Path:
    # A narrow window, so the real clock (months after the fixture's question)
    # refuses the dated question and only the declared instant can serve it.
    overrides: dict[str, Any] = {
        "temporal_boundary": {"max_past_seconds": 3600, "permitted_clock_skew_seconds": 0}
    }
    if declare:
        overrides["demonstration_serve_instant"] = {"serve_instant": DECLARED.isoformat()}
    return fixture.write_tree(
        tmp_path / "deployment",
        config=fixture.producer_config(subject_withholding=SUBJECT_WITHHOLDING_NEVER, **overrides),
        environment=fixture.producer_environment_text(),
    )


def _open(tmp_path: Path, *, declare: bool, **extra: Any) -> Any:
    return open_product(
        erasure_trust=declared_erasure_trust(fixture.PRODUCER_TENANT),
        config_root=_tree(tmp_path, declare=declare),
        scratch=tmp_path / "scratch",
        acquire=fixture.Acquire(),
        project=fixture.plan_factory,
        assess=fixture.assess,
        environ={fixture.CHILD_DSN_VAR: "postgresql://fixture"},
        control_plane=ControlPlaneRegistry(),
        **extra,
    )


def _ask(opened: Any, *, asked_at: Any = fixture.ASKED_AT) -> Any:
    return opened.answer(
        opened.question(
            subject="acct-1",
            asked_at=asked_at,
            intent="fixture-intent",
            freshness="fixture-freshness",
            parameters={fixture.THRESHOLD_PARAMETER: 1000},
        )
    )


def _demonstration_pins(opened: Any, outcome: Any) -> list[Any]:
    record = opened.record_of(outcome)
    return [
        binding
        for binding in record.policy_bindings.bindings
        if binding.key == f"{opened.tenant_id}/{DEMONSTRATION_KEY_SUFFIX}"
    ]


# --- permitted -------------------------------------------------------------------------


def test_a_paved_deployment_with_no_composed_clock_serves_at_its_declared_instant(
    tmp_path: Path,
) -> None:
    """The dated question serves, ``served_at`` is the declared instant, the record pins it."""
    with _open(tmp_path, declare=True) as opened:
        outcome = _ask(opened)
        assert isinstance(outcome, ServedProduct), outcome
        record = opened.record_of(outcome)
        assert record.content_generation_path.served_at == DECLARED
        pins = _demonstration_pins(opened, outcome)
        assert len(pins) == 1, "the served record does not pin the declaration that set served_at"


# --- refused, beside it ---------------------------------------------------------------


def test_without_the_declaration_the_dated_question_is_refused_on_the_real_clock(
    tmp_path: Path,
) -> None:
    with _open(tmp_path, declare=False) as opened:
        outcome = _ask(opened)
        assert isinstance(outcome, RefusalEnvelope), outcome
        assert outcome.reason == "asked-at-outside-temporal-bound", outcome.reason


def test_a_caller_composed_clock_beside_the_declaration_is_still_refused(tmp_path: Path) -> None:
    with _open(tmp_path, declare=True, clock=lambda: DECLARED) as opened:
        with pytest.raises(DemonstrationServeInstantConflict):
            _ask(opened)


def test_a_question_outside_the_declared_instants_window_is_refused(tmp_path: Path) -> None:
    """The expiry/temporal check is not disabled: the declared instant is judged like any other."""
    with _open(tmp_path, declare=True) as opened:
        outcome = _ask(opened, asked_at=fixture.ASKED_AT - timedelta(days=2))
        assert isinstance(outcome, RefusalEnvelope), outcome
        assert outcome.reason == "asked-at-outside-temporal-bound", outcome.reason


def test_a_store_that_is_not_the_sdks_own_is_still_refused(tmp_path: Path) -> None:
    """Decision 4 (a) holds on the paved road: the SDK's erasure wrapper does not launder a subclass."""
    from ccf.erasure.index import erasure_index_at
    from ccf.erasure.store import compose_erasure_consult

    control_plane = ControlPlaneRegistry()
    root = tmp_path / "foreign-store"
    inner = _NotTheSdkStore(
        root=root,
        write_kinds=WriteKinds.declare(
            {fixture.RECORD_CLASS: (ReplayMint,), fixture.QUERY_PIN_CLASS: (ReplayMint,)}
        ),
    )
    index = erasure_index_at(root)
    trust = declared_erasure_trust(fixture.PRODUCER_TENANT)
    store = compose_erasure_consult(
        inner,
        index=index,
        audit_log=control_plane.audit_log,
        clock=lambda: DECLARED,
        control_plane=control_plane,
        erasure_trust=trust,
        tenant_id=fixture.PRODUCER_TENANT,
    )
    with open_product(
        erasure_trust=trust,
        config_root=_tree(tmp_path, declare=True),
        scratch=tmp_path / "scratch",
        acquire=fixture.Acquire(),
        project=fixture.plan_factory,
        assess=fixture.assess,
        environ={fixture.CHILD_DSN_VAR: "postgresql://fixture"},
        control_plane=control_plane,
        artifact_store=store,
    ) as opened:
        with pytest.raises(DemonstrationServeInstantRefused) as refused:
            _ask(opened)
        assert refused.value.reason == "artifact-store-not-development"


def test_the_declared_clock_type_is_what_the_paved_road_serves_on(tmp_path: Path) -> None:
    """The resolver the paved road builds runs on the SDK's DeclaredServeClock, not a caller's clock."""
    with _open(tmp_path, declare=True) as opened:
        _ask(opened)  # boots once so the declaration is registered
        from ccf.products.resolver import build_governed_resolver

        fabric = opened._boot()  # noqa: SLF001 - the low road's own fabric, for the clock's type
        try:
            resolver = build_governed_resolver(**opened.build_arguments(fabric))
            assert isinstance(resolver.admission_clock, DeclaredServeClock)
        finally:
            fabric.handle.close()


def test_several_declarations_are_still_refused(tmp_path: Path) -> None:
    """A second version registered beside the document's declaration is refused, never a silent winner."""
    from ccf.controlplane.demonstration_serve_instant import (
        DEMONSTRATION_SERVE_INSTANT,
        DemonstrationServeInstant,
        DemonstrationServeInstantMisplaced,
        demonstration_serve_instant_key,
    )
    from tests.composition import register_typed_at_composition

    with _open(tmp_path, declare=True) as opened:
        assert isinstance(_ask(opened), ServedProduct)
        register_typed_at_composition(
            opened.control_plane,
            demonstration_serve_instant_key(tenant_id=opened.tenant_id),
            DemonstrationServeInstant(serve_instant=DECLARED + timedelta(minutes=1)),
            DEMONSTRATION_SERVE_INSTANT,
        )
        with pytest.raises(DemonstrationServeInstantMisplaced):
            _ask(opened)
