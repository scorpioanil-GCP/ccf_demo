# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""A request-scoped OPTIONAL child over the SDK-derived, composition-registered chain (G4-F-08, cp-20).

**SDK-defined** (CLAUDE.md §11). Dave, 2026-10-11 16:23 MST, ruling 4: *"Preserve ...
cp-20's optional-versus-required child behavior ... show the permitted case serving
and the corresponding ... required-but-missing case refusing."*

Before: the only way a request parameter (cp-20's ``include_federated``) reached the
child seam was ``build_children=``, which ``open_product`` refused beside a declared
``agent:``/``skills:`` chain — so cp-20 registered its agent and skill and requested
its grant BY HAND inside the factory, which ``D-IMPL-353`` now refuses
(``CapabilityBypassError``). Now: the deployment declares the chain (``producers:``,
``skills:``, ``agent:``, ``grants:``) and passes ``questions=`` AND
``build_children=``; the SDK derives the chain — registered and granted by
composition — and hands it to the factory as ``ConsumerContext.derived_children``.
The factory only decides whether THIS request asks the optional child; it writes
nothing. Whether a missing child refuses stays the requirement's declaration.

Held here, against a real producer door:

* default request (switch off): served WITHOUT the child — the optional slot reads
  ``optional-absent`` and nothing was dispatched;
* switch on: served WITH the governed, admitted child;
* the same switch over a REQUIRED child: the request that leaves it missing is
  REFUSED;
* the factory registers nothing on the Control Plane, and a half-declared chain
  beside ``build_children=`` is still refused by name.
"""

from __future__ import annotations

import pathlib
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

import pytest

from ccf.products.contract import SUBJECT_WITHHOLDING_NEVER, ChildRequirement
from ccf.products.product import ConsumerContext
from ccf.products.refusal import RefusalEnvelope
from ccf.products.request import ProductRequest
from ccf.replay.serve import ServedProduct

from tests.composition import declare_wide_temporal_boundary
from tests.products import paved_fixture as fixture
from tests.products.paved_fixture import SKILL
from tests.products.test_paved_consumer import (  # noqa: F401 - `producer_url` is a fixture
    _open,
    _the_row,
    _tree,
    producer_url,
)
from ccf.controlplane.registry import ControlPlaneRegistry

SWITCH = "include_child"


class _Switch:
    """The deployment's whole factory: ask the optional child only when the request says so."""

    def __init__(self, context: ConsumerContext) -> None:
        assert context.derived_children is not None, "the SDK handed no derived chain"
        self.inner = context.derived_children
        self.dispatches = 0

    def resolve_for(
        self,
        *,
        requirements: Sequence[ChildRequirement],
        request: ProductRequest,
        asked_at: datetime,
        admitted_at: datetime,
        composition_invocation: str,
        consumer_lineage: Any,
    ) -> Mapping[str, object]:
        if not request.parameters.get(SWITCH, False):
            return {}  # nothing invoked: the requirement's own declaration prices it
        self.dispatches += 1
        return self.inner.resolve_for(
            requirements=requirements,
            request=request,
            asked_at=asked_at,
            admitted_at=admitted_at,
            composition_invocation=composition_invocation,
            consumer_lineage=consumer_lineage,
        )


def _config(*, required: bool) -> dict[str, Any]:
    config = fixture.consumer_config(subject_withholding=SUBJECT_WITHHOLDING_NEVER, grants=[SKILL])
    requirement: dict[str, Any] = {
        "product_class": fixture.CHILD_CLASS,
        "required": required,
        "compatible_from": fixture.CHILD_VERSION,
    }
    if not required:
        requirement["absence_treatment"] = {
            "completeness_when_absent": "0.50",
            "omissible_outcomes": ["optional-absent"],
        }
    config["product_class"]["requires"] = [requirement]
    config["request_contract"]["arguments"]["properties"][SWITCH] = {
        "type": "boolean",
        "description": "whether this request asks the optional child at all",
    }
    return config


def _plane() -> ControlPlaneRegistry:
    registry = ControlPlaneRegistry()
    declare_wide_temporal_boundary(registry, tenant_id=fixture.CONSUMER_TENANT)
    return registry


def _ask(opened: Any, *, switch: bool | None) -> Any:
    parameters: dict[str, Any] = {fixture.THRESHOLD_PARAMETER: 1000}
    if switch is not None:
        parameters[SWITCH] = switch
    return opened.answer(
        opened.question(
            subject="acct-1",
            asked_at=fixture.ASKED_AT,
            intent="fixture-intent",
            freshness="fixture-freshness",
            parameters=parameters,
        )
    )


def _open_switched(tmp_path: pathlib.Path, url: str, *, required: bool) -> tuple[Any, list[_Switch]]:
    built: list[_Switch] = []

    def factory(context: ConsumerContext) -> _Switch:
        switch = _Switch(context)
        built.append(switch)
        return switch

    root = _tree(tmp_path, config=_config(required=required))
    opened = _open(
        root,
        tmp_path / "scratch",
        url,
        control_plane=_plane(),
        questions=fixture.questions,
        build_children=factory,
    )
    return opened, built


# --- permitted -------------------------------------------------------------------------


def test_the_default_request_serves_without_the_optional_child(
    tmp_path: pathlib.Path, producer_url: str  # noqa: F811
) -> None:
    opened, built = _open_switched(tmp_path, producer_url, required=False)
    with opened:
        served = _ask(opened, switch=None)
        assert isinstance(served, ServedProduct), getattr(served, "detail", served)
        assert built[0].dispatches == 0
        assert _the_row(opened, served).outcome_status == "optional-absent"


def test_switched_on_it_serves_with_the_governed_child(
    tmp_path: pathlib.Path, producer_url: str  # noqa: F811
) -> None:
    opened, built = _open_switched(tmp_path, producer_url, required=False)
    with opened:
        served = _ask(opened, switch=True)
        assert isinstance(served, ServedProduct), getattr(served, "detail", served)
        assert built[0].dispatches == 1
        assert _the_row(opened, served).outcome_status == "admitted"


# --- refused, beside it -----------------------------------------------------------------


def test_a_required_child_left_missing_by_the_request_is_refused(
    tmp_path: pathlib.Path, producer_url: str  # noqa: F811
) -> None:
    opened, built = _open_switched(tmp_path, producer_url, required=True)
    with opened:
        refused = _ask(opened, switch=False)
        assert isinstance(refused, RefusalEnvelope), refused
        assert (refused.kind, refused.reason) == ("composite-child-refusal", "child_admission"), refused
        assert built[0].dispatches == 0
        # And the same required child, asked for, serves — the refusal is the absence.
        assert isinstance(_ask(opened, switch=True), ServedProduct)


def test_the_factory_registers_nothing_and_the_chain_is_registered_by_composition(
    tmp_path: pathlib.Path, producer_url: str  # noqa: F811
) -> None:
    registry = _plane()
    seen: dict[str, int] = {}

    def factory(context: ConsumerContext) -> _Switch:
        seen["events_at_factory"] = len(context.control_plane.audit_log.events())
        switch = _Switch(context)
        seen["events_after_factory"] = len(context.control_plane.audit_log.events())
        return switch

    root = _tree(tmp_path, config=_config(required=False))
    with _open(
        root, tmp_path / "scratch", producer_url,
        control_plane=registry, questions=fixture.questions, build_children=factory,
    ) as opened:
        assert seen["events_at_factory"] == seen["events_after_factory"]
        actors = {e.actor for e in opened.control_plane.audit_log.events() if e.action == "grant_effective"}
        assert actors == {"ccf.composition-root"}, actors


def test_a_half_declared_chain_beside_build_children_is_still_refused(
    tmp_path: pathlib.Path, producer_url: str  # noqa: F811
) -> None:
    config = _config(required=False)
    del config["agent"]
    root = _tree(tmp_path, config=config)
    with pytest.raises(ValueError, match=r"declares no \['agent'\] section"):
        _open(
            root, tmp_path / "scratch", producer_url,
            control_plane=_plane(), questions=fixture.questions, build_children=_Switch,
        )
