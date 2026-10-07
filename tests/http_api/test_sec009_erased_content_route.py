"""SEC-009 step (2), over HTTP — an erased artifact is not served (`D-IMPL-374` (4)).

The hole as worded: an erased artifact is still served over HTTP. Ruled (U11,
U12): ``create_app`` composes the decorating store ALWAYS, around whatever
store it is given; ``GET /artifact/{address}`` of an erased address answers
``410`` with an ``erased-content`` shell at ``reasoned`` and ``full``, and the
route's existing not-found rendering — consumer-observationally identical to an
address nothing is stored at — at ``minimal``. Never the bytes.

RED on a tree without the mechanism: the app serves the bytes (200).
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from ccf.products.disclosure import DISCLOSURE_FULL
from ccf.products.entitlement import PRODUCT_ENTITLEMENT_POLICY, product_entitlement_key
from http_api import test_evidence_dereference as ed
from http_api.composition_authority import register_typed_at_composition
from http_api.conftest import Fabric
from tests.composition import composition_register
from tests.erasure import harness as h

ERASED_AT = datetime(2026, 7, 30, tzinfo=UTC)
RECORD_ADDRESS = "f" * 64


def _erase(governed: ed.Governed, address: str) -> None:
    h.erasure("append_to_erasure_index")(
        governed.registry,
        composition_register(governed.registry, h.erasure("erasure_index_key")(governed.tenant)),
        (
            h.erasure("ErasureIndexEntry")(
                content_address=address,
                erasure_record_address=RECORD_ADDRESS,
                reason="customer-request",
                erased_at=ERASED_AT,
            ),
        ),
    )


def test_an_erased_record_is_gone_at_full_and_not_found_at_minimal(fabric: Fabric, tmp_path: Path) -> None:
    governed = ed._governed(fabric, tmp_path)
    address = ed._served_record(governed, principal=ed.A)
    before = ed._get_artifact(governed, address, token=ed.A_TOKEN)
    assert before.status_code == 200, before.text
    stored = before.content

    _erase(governed, address)

    full = ed._get_artifact(governed, address, token=ed.A_TOKEN)
    assert full.status_code == 410, (full.status_code, full.text[:400])
    assert stored not in full.content
    refusal = full.json()["refusal"]
    assert refusal["kind"] == "erased-content"
    assert refusal["disclosure"] == DISCLOSURE_FULL
    assert RECORD_ADDRESS in full.text

    # minimal: the route's own not-found rendering, identical to an address
    # nothing is stored at — the erasure is not disclosed.
    minimal = ed._get_artifact(governed, address, token=ed.C_TOKEN)
    nowhere = ed._get_artifact(governed, ed.NOWHERE, token=ed.C_TOKEN)
    assert minimal.status_code == 404
    assert ed.same_shell(minimal, address, nowhere, ed.NOWHERE)


def test_an_erased_record_at_reasoned_is_gone_with_its_reason_and_without_its_record(fabric: Fabric, tmp_path: Path) -> None:
    governed = ed._governed(fabric, tmp_path)
    address = ed._served_record(governed, principal=ed.C)
    _erase(governed, address)
    policy = ed._policy(governed.tenant, governed.product_class)
    reasoned = policy.model_copy(
        update={
            "policy_version": "1.0.1",
            "principals": {
                **policy.principals,
                ed.C: policy.principals[ed.C].model_copy(update={"disclosure_level": "reasoned"}),
            },
        }
    )
    register_typed_at_composition(
        governed.registry, product_entitlement_key(tenant_id=governed.tenant), reasoned, PRODUCT_ENTITLEMENT_POLICY
    )
    response = ed._get_artifact(governed, address, token=ed.C_TOKEN)
    assert response.status_code == 410, (response.status_code, response.text[:400])
    refusal = response.json()["refusal"]
    assert refusal["kind"] == "erased-content" and refusal["disclosure"] == "reasoned"
    assert "customer-request" in response.text
    assert RECORD_ADDRESS not in response.text
