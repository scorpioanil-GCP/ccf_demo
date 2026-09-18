"""`D-IMPL-304` at the HTTP door: the typed handoff is recorded and rendered through the ONE refusal path; a fault stays a fault."""

from __future__ import annotations

import pathlib
from typing import Any

from ccf.products.refusal import GovernedRefusalRaised, SubjectUnavailableRefusal
from ccf.products.request import ProductRequest
from ccf.projection.plan import Perspective
from ccf.replay.record import ResolutionNotApplicable
from ccf_runtime.http_api.refusal_status import STATUS_BY_KIND
from http_api.conftest import Fabric
from tests.http_api.test_product_declared_obligation_409 import SUBJECT_UNAVAILABLE, _ask, _governed, _question


def _raising(exception: Any) -> Any:
    def resolve(*, tenant: str, product_class: str, version: str, perspective: Perspective, request: ProductRequest | None) -> object:
        raise exception

    return resolve


def test_a_refusal_raised_to_the_route_is_recorded_and_rendered_as_the_common_shell(fabric: Fabric, tmp_path: pathlib.Path) -> None:
    """The route catches only the typed handoff, records it through the recorded
    boundary and renders it by kind — the same path the typed absence takes."""
    raised = GovernedRefusalRaised(
        SubjectUnavailableRefusal(cause="nonexistent", detail="held, not returnable", error_code=None),
        resolution=ResolutionNotApplicable(reason="refused-before-resolution"),
    )
    governed = _governed(fabric, tmp_path, resolver=_raising(raised))
    answer = _ask(governed.app, fabric, query=_question(), product_class=fabric.product_address.product_class)
    assert answer.status == STATUS_BY_KIND[SUBJECT_UNAVAILABLE]
    assert answer.body["kind"] == SUBJECT_UNAVAILABLE
    assert answer.body["refusal"]["replay_reference"] not in (None, "", "no-replay-reference"), answer.body


def test_a_fault_raised_to_the_route_stays_a_door_fault(fabric: Fabric, tmp_path: pathlib.Path) -> None:
    """A `ValueError` from the resolver is not a determination; it keeps its
    existing treatment and is never rendered as a governed refusal."""
    governed = _governed(fabric, tmp_path, resolver=_raising(ValueError("a programming fault")))
    answer = _ask(governed.app, fabric, query=_question(), product_class=fabric.product_address.product_class)
    # The route's existing treatment of a fault: no response at all — the
    # exception escapes the app (httpx's ASGI transport re-raises rather than
    # rendering a 500), which `_ask` reports as `escaped`. Unchanged by the
    # typed catch, and never a governed shell.
    assert answer.status is None and answer.body is None
    assert isinstance(answer.escaped, ValueError)
