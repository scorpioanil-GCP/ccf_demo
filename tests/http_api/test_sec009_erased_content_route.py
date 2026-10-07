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

from pathlib import Path

from ccf.products.disclosure import DISCLOSURE_FULL
from ccf.products.entitlement import PRODUCT_ENTITLEMENT_POLICY, product_entitlement_key
from http_api import test_evidence_dereference as ed
from http_api.composition_authority import register_typed_at_composition
from http_api.conftest import Fabric
from ccf.contracts.canonical import content_hash
from tests.erasure import composed
from tests.erasure import harness as h

def _erase(governed: ed.Governed, address: str) -> str:
    """Plant a GENUINE erasure of ``address`` in the deployment's index; return the record address."""
    record = composed.erase(governed.store, governed.erasure_index, address, control_plane=governed.registry, tenant=governed.tenant)
    return str(content_hash(record))


def test_an_erased_record_is_gone_at_full_and_not_found_at_minimal(fabric: Fabric, tmp_path: Path) -> None:
    governed = ed._governed(fabric, tmp_path)
    address = ed._served_record(governed, principal=ed.A)
    before = ed._get_artifact(governed, address, token=ed.A_TOKEN)
    assert before.status_code == 200, before.text
    stored = before.content

    record_address = _erase(governed, address)

    full = ed._get_artifact(governed, address, token=ed.A_TOKEN)
    assert full.status_code == 410, (full.status_code, full.text[:400])
    assert stored not in full.content
    refusal = full.json()["refusal"]
    assert refusal["kind"] == "erased-content"
    assert refusal["disclosure"] == DISCLOSURE_FULL
    assert record_address in full.text

    # minimal: the route's own not-found rendering, identical to an address
    # nothing is stored at — the erasure is not disclosed.
    minimal = ed._get_artifact(governed, address, token=ed.C_TOKEN)
    nowhere = ed._get_artifact(governed, ed.NOWHERE, token=ed.C_TOKEN)
    assert minimal.status_code == 404
    assert ed.same_shell(minimal, address, nowhere, ed.NOWHERE)


def test_an_erased_record_at_reasoned_is_gone_with_its_reason_and_without_its_record(fabric: Fabric, tmp_path: Path) -> None:
    governed = ed._governed(fabric, tmp_path)
    address = ed._served_record(governed, principal=ed.C)
    record_address = _erase(governed, address)
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
    assert record_address not in response.text


def test_an_unentitled_caller_cannot_learn_that_an_address_was_erased(fabric: Fabric, tmp_path: Path) -> None:
    """Ruling 1 (authorization first): the holds run BEFORE the erasure consult.

    ``B`` discloses at ``full`` and holds the same grant, but the record is
    ``A``'s; the stranger holds no grant at all. Each must receive, after the
    erasure, exactly the rendering the door gave it before — no ``erased-content``
    kind, no 410, no reason, no instant, no record address.
    """
    governed = ed._governed(fabric, tmp_path)
    address = ed._served_record(governed, principal=ed.A)
    before = {
        token: ed._get_artifact(governed, address, token=token)
        for token in (ed.B_TOKEN, ed.STRANGER_TOKEN, ed.C_TOKEN)
    }
    record_address = _erase(governed, address)
    for token, earlier in before.items():
        after = ed._get_artifact(governed, address, token=token)
        assert after.status_code == earlier.status_code != 410, (token, after.status_code)
        assert "erased" not in after.text and record_address not in after.text, token
        assert "customer-request" not in after.text, token
        assert ed.same_shell(earlier, address, after, address), token


def test_at_minimal_the_wire_is_not_found_and_the_recorded_refusal_is_erased_content(fabric: Fabric, tmp_path: Path) -> None:
    """Fix round 1, I5: the audit trail is honest at ``minimal``.

    The entitled owner ``C`` discloses at ``minimal``. The wire shell is the
    route's not-found rendering, identical to an address nothing is stored at;
    the refusal RECORDED behind it (dimension 5) is the ``erased-content``
    determination, never a false "nonexistent".
    """
    governed = ed._governed(fabric, tmp_path)
    address = ed._served_record(governed, principal=ed.C)
    _erase(governed, address)
    minimal = ed._get_artifact(governed, address, token=ed.C_TOKEN)
    nowhere = ed._get_artifact(governed, ed.NOWHERE, token=ed.C_TOKEN)
    assert minimal.status_code == 404
    assert ed.same_shell(minimal, address, nowhere, ed.NOWHERE)
    internal = governed.internal(minimal.json()["refusal"]["replay_reference"])
    assert internal.kind == "erased-content", internal.kind
