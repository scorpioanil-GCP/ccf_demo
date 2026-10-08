"""C-2 over HTTP — a record decided under another tenant reads exactly as a missing address.

``D-IMPL-345`` R-2: *"a record crosses the HTTP boundary only when the caller is
held to the record's retained principal/tenant/product identity"*. The
independent review of the ``D-IMPL-376`` close-out (C-2) measured that
:func:`ccf_runtime.authz.delivery_boundary.govern_dereference` held the caller
to the record's PRINCIPAL and re-decided the grant under the record's TENANT,
but compared the capability's tenant with the record's nowhere:

* **collision** — a caller whose only tenant is this door's, whose principal id
  equals the principal of another tenant's record, and who is entitled in that
  tenant and at ``full`` here, received the other tenant's record;
* **oracle** — with no collision, at ``full``, another tenant's record answered
  ``unauthorized`` / ``evidence-principal-mismatch`` where a missing address
  answers ``nonexistent`` / ``evidence-absent``.

The ruling: the caller is held to the record's deciding tenant, and a record
decided under any other tenant answers exactly as a missing address does — the
one ``nonexistent`` envelope, at every disclosure level. Within the caller's own
tenant nothing changes: the owner still reads its record, and another
principal's genuine record still answers ``unauthorized`` at ``full`` (R-4).

Each case asks the SAME address twice — before the other tenant's record is
filed there, when it is missing, and after — and requires the two answers to be
the same bytes. The fixed determination clock makes a missing address's answer
reproducible, which the first assertion of
:func:`test_at_full_another_tenants_record_answers_as_a_missing_address_does`
measures rather than assumes. All three evidence routes that call
``govern_dereference`` are asked: ``/replay/decisions``, ``/replay/resolutions``
and ``/artifact``.

Tenant, principal, class and token names are test deployment vocabulary,
meaningful nowhere else (CINV-01 applied to test data).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from ccf.artifacts.protocol import artifact_uri
from ccf.contracts.canonical import content_hash
from ccf.products.entitlement import PRODUCT_ENTITLEMENT_POLICY, product_entitlement_key
from ccf.products.request import ProductRequest
from ccf.replay.record import DecisionReplayRecord
from ccf.replay.serve import ReplayWriter
from ccf_runtime.http_api.errors import ERROR_EVIDENCE_ABSENT, ERROR_EVIDENCE_PRINCIPAL_MISMATCH
from http_api.composition_authority import composition_replay_mint, register_typed_at_composition
from http_api.conftest import Fabric

from .test_evidence_dereference import (
    A,
    A_TOKEN,
    AUDIT_INSTANT,
    B_TOKEN,
    REPLAY_RECORD_CLASS,
    ROLE,
    Governed,
    _get_artifact,
    _get_record,
    _get_uri,
    _governed,
    _policy,
    _served_record,
)

#: The tenant whose records the caller must not be able to tell from nothing.
OTHER_TENANT = "c2-other-tenant"

#: A principal of the other tenant that collides with no principal here.
OTHERS_OWN_PRINCIPAL = "c2-other-tenants-principal"

ROUTES = ("decisions", "resolutions", "artifact")


@pytest.fixture
def governed(fabric: Fabric, tmp_path: Path) -> Governed:
    return _governed(fabric, tmp_path)


def _record(governed: Governed, *, tenant: str, principal: str, subject: str) -> DecisionReplayRecord:
    """A served record of ``tenant`` for ``principal`` — built, not yet filed."""
    from http_api.conftest import _replay_record

    base = _replay_record()
    served = base.content_generation_path.model_copy(
        update={
            "request": ProductRequest(
                schema_name=governed.product_class,
                schema_version="1.0.0",
                subject=subject,
                intent="intent-1",
                freshness="event-driven",
                asked_at=AUDIT_INSTANT,
                parameters={},
            )
        }
    )
    return base.model_copy(
        update={
            "tenant_id": tenant,
            "perspective_conditioning": base.perspective_conditioning.model_copy(
                update={"principal_id": principal, "role": ROLE}
            ),
            "content_generation_path": served,
        }
    )


def _file(governed: Governed, record: DecisionReplayRecord) -> str:
    """The record's own tenant files it, through its own replay writer."""
    return (
        ReplayWriter(
            authorized=composition_replay_mint(
                governed.registry, tenant=record.tenant_id, artifact_class=REPLAY_RECORD_CLASS
            ),
            store=governed.store,
        )
        .write_replay_record(record=record)
        .replay_ref.content_address
    )


def _uri(record: DecisionReplayRecord, address: str) -> str:
    # The record writer names a record by its own content address (Dave's Q11,
    # `D-IMPL-378`), so the URI it is registered under is `{address}@{address}`.
    return artifact_uri(
        tenant_id=record.tenant_id,
        artifact_class=REPLAY_RECORD_CLASS,
        name=address,
        artifact_version=address,
    )


def _ask(governed: Governed, route: str, record: DecisionReplayRecord, address: str, *, token: str) -> Any:
    if route == "decisions":
        return _get_record(governed, address, token=token)
    if route == "resolutions":
        return _get_uri(governed, _uri(record, address), token=token)
    assert route == "artifact", route
    return _get_artifact(governed, address, token=token)


def _answers(governed: Governed, record: DecisionReplayRecord, address: str, *, token: str) -> dict[str, Any]:
    return {route: _ask(governed, route, record, address, token=token) for route in ROUTES}


def _assert_identical(before: dict[str, Any], after: dict[str, Any]) -> None:
    """Every route's status, bytes and headers equal — all mismatches reported at once."""
    changed = [
        f"{route}: missing={before[route].status_code} {before[route].content[:120]!r}"
        f" / filed={after[route].status_code} {after[route].content[:120]!r}"
        for route in ROUTES
        if (after[route].status_code, after[route].content, dict(after[route].headers))
        != (before[route].status_code, before[route].content, dict(before[route].headers))
    ]
    assert not changed, "another tenant's record at the address changed the answer on: " + " | ".join(changed)


def _internal_cause(governed: Governed, response: Any) -> tuple[str, str]:
    """The recorded determination behind a disclosed shell: (cause, error code)."""
    internal = governed.internal(response.json()["refusal"]["replay_reference"])
    return json.loads(internal.fields["cause"]), json.loads(internal.fields["error_code"])


def test_another_tenants_record_with_a_colliding_principal_answers_as_a_missing_address_does(
    governed: Governed,
) -> None:
    """(a) The collision: ``A``'s grant names only this door's tenant, but ``A``
    is also the principal of the other tenant's record, entitled to its class
    there, and at ``full`` here. The record must not cross: every evidence
    route answers it with the bytes it answered while the address was empty —
    the recorded absence, ``nonexistent`` / ``evidence-absent``."""
    register_typed_at_composition(
        governed.registry,
        product_entitlement_key(tenant_id=OTHER_TENANT),
        _policy(OTHER_TENANT, governed.product_class),
        PRODUCT_ENTITLEMENT_POLICY,
    )
    record = _record(governed, tenant=OTHER_TENANT, principal=A, subject="c2-collision")
    address = content_hash(record)
    before = _answers(governed, record, address, token=A_TOKEN)

    assert _file(governed, record) == address
    after = _answers(governed, record, address, token=A_TOKEN)

    _assert_identical(before, after)
    for route in ROUTES:
        assert _internal_cause(governed, after[route]) == ("nonexistent", ERROR_EVIDENCE_ABSENT), route
    # Control: within its own tenant the owner still reads its own record.
    owned = _served_record(governed, principal=A)
    assert _get_record(governed, owned, token=A_TOKEN).status_code == 200


def test_at_full_another_tenants_record_answers_as_a_missing_address_does(
    governed: Governed,
) -> None:
    """(b) The oracle, with no collision: ``B`` is at ``full`` and is no
    principal of the other tenant. Another tenant's genuine record answers
    exactly what a missing address answers, so ``B`` cannot learn that some
    other tenant holds a record at an address it computed. Within the tenant,
    R-4 stands: another principal's genuine record still reads
    ``unauthorized`` at ``full``."""
    record = _record(governed, tenant=OTHER_TENANT, principal=OTHERS_OWN_PRINCIPAL, subject="c2-oracle")
    address = content_hash(record)
    # The instrument: a missing address answers the same bytes twice.
    first = _answers(governed, record, address, token=B_TOKEN)
    before = _answers(governed, record, address, token=B_TOKEN)
    _assert_identical(first, before)

    assert _file(governed, record) == address
    after = _answers(governed, record, address, token=B_TOKEN)

    _assert_identical(before, after)
    for route in ROUTES:
        assert _internal_cause(governed, after[route]) == ("nonexistent", ERROR_EVIDENCE_ABSENT), route
    # Control (R-4, unchanged): the same-tenant record of another principal.
    owned = _served_record(governed, principal=A)
    poached = _get_record(governed, owned, token=B_TOKEN)
    assert _internal_cause(governed, poached) == ("unauthorized", ERROR_EVIDENCE_PRINCIPAL_MISMATCH)
    assert json.loads(poached.json()["refusal"]["fields"]["cause"]) == "unauthorized"
