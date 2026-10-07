"""M-4 — a tenant id containing the naming separator is refused at the store's write boundary.

The store files a name under the key ``"<tenant>/<class>/<name>"``, and
:meth:`ccf.artifacts.file_store.FileArtifactStore.names_at` reads that key back
by splitting it at its first two separators. A tenant id that itself contains
the separator is therefore read back as ANOTHER tenant: a filing by
``"<t>/x"`` of class ``c`` comes back as tenant ``"<t>"``, class ``"x"``. The
independent review of the ``D-IMPL-376`` close-out (M-4) measured the
consequence through the shipped artifact server: tenant ``"<t>"`` was served
tenant ``"<t>/x"``'s client-lane bytes, because the C8 split decides both
"own" and "governed" from that attribution.

The ruling: refuse such a tenant at the write boundary, by name — the rule
``WriteKinds`` already applies to a declared class (SEC-004) — so no filing a
reverse read would misattribute can be made. Both write shapes are held: the
addressed write a door's capability makes, and the derived write the fabric's
own mechanism makes. A refused write files nothing: no bytes, no name.

Tenant, class and name values are test deployment vocabulary, meaningful
nowhere else (CINV-01 applied to test data).
"""

from __future__ import annotations

import json
import pathlib

import anyio
import pytest
from mcp.server.auth.middleware.auth_context import auth_context_var

from ccf.artifacts.protocol import ArtifactWriteRefused, DerivedWrite
from ccf.authz.capability import ArtifactWrite
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.controlplane.registry import ControlPlaneRegistry
from tests.controlplane.capabilities import capability
from tests.http_api.composition_authority import composition_replay_mint, deployment_store
from tests.mcp import test_c8_governed_judged_per_tenant as c8
from tests.mcp.guarded_servers import REPLAY_RECORD_CLASS, TENANT
from tests.mcp.test_artifact_server_authorized import _as_grant

#: A different tenant whose id has the caller's id as a prefix, plus the separator.
SLASHED = f"{TENANT}/x"
SECRET = {"secret": "of the other tenant"}


def test_an_addressed_write_under_a_tenant_containing_the_separator_is_refused_and_files_nothing(
    tmp_path: pathlib.Path,
) -> None:
    store = deployment_store(tmp_path / "artifacts", REPLAY_RECORD_CLASS)
    with pytest.raises(ArtifactWriteRefused) as refused:
        store.put(capability(ArtifactWrite, tenant=SLASHED, resource="c/theirs"), SECRET)
    assert SLASHED in str(refused.value), "the refusal names the tenant it refused"
    address = content_hash(SECRET)
    assert store.names_at(content_address=address) == ()
    assert store.exists(content_address=address) is False


def test_a_derived_write_under_a_tenant_containing_the_separator_is_refused_and_files_nothing(
    tmp_path: pathlib.Path,
) -> None:
    store = deployment_store(tmp_path / "artifacts", REPLAY_RECORD_CLASS)
    with pytest.raises(ArtifactWriteRefused) as refused:
        store.put(
            composition_replay_mint(ControlPlaneRegistry(), tenant=SLASHED, artifact_class=REPLAY_RECORD_CLASS),
            DerivedWrite(artifact_class=REPLAY_RECORD_CLASS, name="theirs", artifact=SECRET),
        )
    assert SLASHED in str(refused.value), "the refusal names the tenant it refused"
    address = content_hash(SECRET)
    assert store.names_at(content_address=address) == ()
    assert store.exists(content_address=address) is False


def test_the_prefix_tenant_is_never_served_the_slashed_tenants_bytes_over_the_artifact_server(
    tmp_path: pathlib.Path,
) -> None:
    """The reviewer's scenario end to end: the slashed tenant's filing is
    refused at the store, so the caller's tenant — the slashed id's prefix —
    reads the address as the nonexistent shell a missing address answers, never
    as the other tenant's bytes."""
    world = c8._world(tmp_path)
    with pytest.raises(ArtifactWriteRefused):
        world.store.put(capability(ArtifactWrite, tenant=SLASHED, resource="c/theirs"), SECRET)
    reset = _as_grant(c8._grant())
    try:
        (blob,) = list(anyio.run(world.server.read_resource, c8._uri("blob", content_hash(SECRET))))
    finally:
        auth_context_var.reset(reset)
    body = blob.content if isinstance(blob.content, bytes) else blob.content.encode("utf-8")
    assert body != canonical_bytes(SECRET)
    assert json.loads(body)["kind"] == "subject-unavailable"
