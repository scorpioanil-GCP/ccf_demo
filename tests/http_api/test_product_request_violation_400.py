"""The HTTP product door answers ``400`` for a request-conformity verdict.

Phase 24.5 close panel, finding R3, ruled by Dave 2026-09-03: *"Request
violation is 400-family. A 500 is a door lie. Map that kind (and any other
request-violation reasons the door already has) to 400. Sabotage: drop the
map → 500 → restore. This is not a new gate type."*

Before this map a :class:`~ccf.products.request.ProductRequestViolation`
envelope — the resolver's verdict that the QUESTION does not conform to the
class's declared contract, including ``24.5-FIX-02``'s ``not-a-proportion``
— reached :func:`~ccf.products.door.served_answer`, which raised
``TypeError`` naming the shape: no response, an opaque 500. The door already
answered ``400`` for its own two request-shape refusals (malformed
``parameters``, an unrepresentable ``asked_at``); the resolver's verdict on
the same request is the same family and now carries the same status, with
the envelope as the body in the ``409``'s shape.

The mapping is by KIND, read from :data:`~ccf.products.refusal.REFUSAL_KINDS`
and never spelled as a second literal, so every reason the vocabulary
carries — all six — arrives as ``400`` through one branch. The ``409`` is
asserted unchanged in ``test_product_declared_obligation_409.py``, which this
module shares its door with rather than restating it.

**Superseded in scope at ``24.6-09``, not in substance.** DIV-4's remainder is
gone: D-18 (``D-IMPL-253`` Q18) gives every member of the vocabulary a status
by class, so ``ttl-refusal`` no longer escapes and this ``400`` is one row of
:data:`~ccf_runtime.http_api.refusal_status.STATUS_BY_KIND` rather than one of
two hand-written branches. The status is read from that table here, so this
module asserts *the row this kind has* rather than a number that happened to
agree with it.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import pytest

from ccf.products.refusal import REFUSAL_KINDS, RefusalEnvelope, envelope_for
from ccf.products.request import ProductRequestViolation
from ccf_runtime.http_api.refusal_status import STATUS_BY_KIND
from tests.http_api.test_product_declared_obligation_409 import (
    KIND as OBLIGATION_KIND,
    _answering,
    _ask,
    _governed_app,
    _identity,
    _question,
)
from http_api.conftest import Fabric

#: The kind this map answers, read from the mapping.
KIND = REFUSAL_KINDS[ProductRequestViolation]


def _violation(reason: str, key: str) -> ProductRequestViolation:
    return ProductRequestViolation(
        reason=reason,  # type: ignore[arg-type]
        key=key,
        declared_type="number" if reason == "not-a-proportion" else None,
        presented_type="int",
        declared_keys=frozenset({"minimum_score", key}),
        presented_keys=frozenset({"minimum_score", key}),
        detail=f"{key}: the request boundary's {reason} verdict, as this test authors it",
    )


def _envelope(fabric: Fabric, reason: str, key: str) -> RefusalEnvelope:
    """The envelope the resolver returns BEFORE the graph is touched — no lineage."""
    return envelope_for(_violation(reason, key), request=_identity(fabric))


@pytest.mark.parametrize(
    ("reason", "key"),
    [
        ("not-a-proportion", "debt_tolerance"),
        ("not-supported-at-tier", "as_of"),
        ("undeclared-parameter", "colour"),
        ("missing-required-parameter", "debt_tolerance"),
    ],
)
def test_a_request_violation_answers_400_with_the_envelope(
    fabric: Fabric, tmp_path: Path, reason: str, key: str
) -> None:
    """One kind, one status, every reason: ``400`` carrying the whole envelope.

    What would fail here: the door as shipped before this map — no response,
    a ``TypeError`` escaping from ``served_answer`` (the sabotage below
    restores exactly that and watches this go RED).
    """
    answer = _ask(
        _governed_app(
            fabric, tmp_path, resolver=_answering(_envelope(fabric, reason, key))
        ),
        fabric,
        query=_question(),
    )

    assert answer.escaped is None, (
        f"a {KIND!r} reached the product door and {type(answer.escaped).__name__}"
        f" escaped instead of a response ({answer.escaped}); a request-conformity"
        " verdict is 400-family, never a door fault"
    )
    assert answer.status == STATUS_BY_KIND[KIND] == 400, answer.body
    body = answer.body
    assert isinstance(body, Mapping) and body.get("kind") == KIND, body
    assert body.get("refusal_type") == ProductRequestViolation.__name__
    refusal = body.get("refusal")
    assert isinstance(refusal, Mapping) and refusal.get("kind") == KIND
    assert refusal.get("reason") == reason
    assert refusal.get("key") == key
    # Pre-assembly: the verdict precedes the graph, so it carries no lineage.
    assert refusal.get("pre_assembly_lineage") is None
    # The question survives the refusal (D-09).
    assert refusal["request"]["product_id"] == fabric.product_address.product_class


def test_the_two_mapped_kinds_are_distinct_statuses(fabric: Fabric) -> None:
    """``400`` and ``409`` are decided by two different kinds, never one.

    Re-derived at ``24.6-09``: the second assertion pinned this kind's token as
    a literal, which said nothing about the mapping and drifted the moment
    D-18 made the mapping a table. It now reads the table — the two kinds are
    distinct **and** their statuses are, which is the claim the name makes.
    """
    assert KIND != OBLIGATION_KIND
    assert STATUS_BY_KIND[KIND] == 400
    assert STATUS_BY_KIND[OBLIGATION_KIND] == 409
    assert STATUS_BY_KIND[KIND] != STATUS_BY_KIND[OBLIGATION_KIND]
