"""A forged record over HTTP — bytes the fabric's record writer did not file are never read as a record.

The re-review of the ``D-IMPL-376`` close-out (confirmed by the coordinator):
:func:`ccf_runtime.authz.delivery_boundary.govern_dereference` takes the
record's tenant (hold 0) and principal (hold 1) from the BYTES stored at the
address, and never checks that the address was filed by the fabric's own
record writer. Anyone who can file an artifact — another tenant on its own
client lane, or a principal of this tenant on this tenant's client lane, both
with an ordinary ``ArtifactWrite`` — can file the canonical bytes of a
``DecisionReplayRecord`` claiming this tenant and principal ``A``, and ``A``'s
governed reads served them as ``A``'s own evidence.

Dave's ruling: the governed read serves a record only if the store shows it was
filed by the fabric's own record writer under the tenant the record claims;
anything else answers EXACTLY like a missing address; a store that cannot
answer that question refuses rather than serves.

Each case asks the SAME address before the forged bytes are filed and after,
on all three evidence routes — ``/replay/decisions``, ``/artifact``, and
``/replay/resolutions`` with the URI naming the forger's own filing, which is
the URI a forger would hand over — and requires the same bytes. The controls
hold what must keep working: the owner reads a genuine record, and reads its
own read-refusal record through its reference (``D-IMPL-345`` C20).

Tenant, principal, class and token names are test deployment vocabulary,
meaningful nowhere else (CINV-01 applied to test data).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from ccf.artifacts.protocol import artifact_uri
from ccf.authz.capability import ArtifactWrite
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf_runtime.http_api.errors import ERROR_EVIDENCE_ABSENT
from http_api.conftest import Fabric
from tests.controlplane.capabilities import capability

from .test_c2_tenant_hold_http import ROUTES, _assert_identical, _internal_cause, _record
from .test_evidence_dereference import (
    A,
    A_TOKEN,
    B,
    Governed,
    _get_artifact,
    _get_record,
    _get_uri,
    _governed,
    _served_record,
)

#: A tenant that files forged bytes on its own client lane.
FORGER_TENANT = "forged-record-forger-tenant"
#: A client-lane class: one the store does not declare under ``ReplayMint``.
CLIENT_CLASS = "c"


@pytest.fixture
def governed(fabric: Fabric, tmp_path: Path) -> Governed:
    return _governed(fabric, tmp_path)


def _answers(governed: Governed, address: str, forged_uri: str, *, token: str) -> dict[str, Any]:
    return {
        "decisions": _get_record(governed, address, token=token),
        "resolutions": _get_uri(governed, forged_uri, token=token),
        "artifact": _get_artifact(governed, address, token=token),
    }


def _forge_and_ask(governed: Governed, *, forger_tenant: str, subject: str) -> None:
    """File a record claiming this tenant and ``A`` on ``forger_tenant``'s client
    lane; ``A``'s three answers must equal the ones a missing address got."""
    forged = _record(governed, tenant=governed.tenant, principal=A, subject=subject)
    address = content_hash(forged)
    name = f"forged-{subject}"
    forged_uri = artifact_uri(
        tenant_id=forger_tenant, artifact_class=CLIENT_CLASS, name=name, artifact_version=address
    )
    before = _answers(governed, address, forged_uri, token=A_TOKEN)

    filed = governed.store.put(
        capability(ArtifactWrite, tenant=forger_tenant, resource=f"{CLIENT_CLASS}/{name}"),
        json.loads(canonical_bytes(forged)),
    )
    assert filed.content_address == address
    after = _answers(governed, address, forged_uri, token=A_TOKEN)

    _assert_identical(before, after)
    for route in ROUTES:
        assert _internal_cause(governed, after[route]) == ("nonexistent", ERROR_EVIDENCE_ABSENT), route


def test_a_record_forged_on_another_tenants_client_lane_answers_as_a_missing_address_does(
    governed: Governed,
) -> None:
    """Another tenant files the forged bytes on ITS OWN client lane."""
    _forge_and_ask(governed, forger_tenant=FORGER_TENANT, subject="cross-tenant-forgery")


def test_a_record_forged_on_the_tenants_own_client_lane_answers_as_a_missing_address_does(
    governed: Governed,
) -> None:
    """A principal of THIS tenant files the forged bytes on this tenant's client lane."""
    _forge_and_ask(governed, forger_tenant=governed.tenant, subject="same-tenant-forgery")


def test_a_genuine_record_and_the_owners_own_refusal_chain_still_read(governed: Governed) -> None:
    """The controls: a record the fabric's writer filed reads for its owner, and
    the read-refusal record the door itself wrote reads for the principal it was
    written for, through the reference its shell handed back (``D-IMPL-345`` C20)."""
    owned = _served_record(governed, principal=A)
    assert _get_record(governed, owned, token=A_TOKEN).status_code == 200

    someone_elses = _served_record(governed, principal=B)
    refused = _get_record(governed, someone_elses, token=A_TOKEN)
    reference = refused.json()["refusal"]["replay_reference"]
    read_back = _get_uri(governed, reference, token=A_TOKEN)
    assert read_back.status_code == 200
    assert read_back.json()["perspective_conditioning"]["principal_id"] == A
