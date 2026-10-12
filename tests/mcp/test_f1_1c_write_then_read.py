# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""Design 1.2 (F1-1c): write-then-read — a tenant's own client-lane filing decides its client-lane reads.

``D-IMPL-378``. Dave, 2026-10-09 06:06 MST, confirmed 06:21: *"A; fix F1-1b and F1-1c now; X17(a)."* His choices on
the design, 2026-10-09 10:54 MST, design 1.2: *"Q1 (A), a tenant’s own filing decides its own reads. Q2, the A6 names
rule. Q3 (a), build it with 1.3. Q4 (a), disclose the write-timing difference. Do not change the storage layer."*

The asker files a query pin's canonical bytes on its own client lane (``put_artifact``) and reads them back. Under the
same-tenant rule N4 (C8's fragment ``377-02``), a governed filing of the address by the asker's tenant sent every read
of it to the governed dereference, so the read answered the governed shell where the record writer had filed the pin
and the asker's own bytes where it had not: the two deployments told apart. Now the client lane serves an address its
tenant filed on the client lane, whatever else that tenant filed there (``runtime/ccf_runtime/mcp/artifact_server.py``,
nested ``dereference`` and ``artifact_names``, rule A6). Only bytes a principal of the tenant presented itself cross;
record-shaped bytes and bytes not at their address still go to the governed read.

Fixture vocabulary only (CINV-01).
"""

from __future__ import annotations

import base64
import hashlib
import json
import pathlib
from typing import Any

from mcp.types import BlobResourceContents, TextResourceContents
from pydantic import AnyUrl

from ccf.artifacts.protocol import ArtifactName
from ccf.authz.capability import ReplayMint
from ccf.products.refusal import RefusalEnvelope
from ccf_runtime.mcp.artifact_server import artifact_blob_uri, artifact_meta_uri, artifact_names_uri
from tests.mcp import test_f1_names_present_governed_and_absent_alike as names_alike
from tests.products import sec020_worlds as w

#: An address nobody filed in any deployment here.
NOBODYS = hashlib.sha256(b"f1-1c: an address nobody filed").hexdigest()


def _read(deployment: w.Deployment, uri: str, *, token: str) -> Any:
    """The resource at ``uri`` as ``token``: raw bytes for a blob part, parsed JSON for a text part."""

    async def operation(session: Any) -> Any:
        result = await session.read_resource(AnyUrl(uri))
        parts: list[Any] = []
        for contents in result.contents:
            if isinstance(contents, BlobResourceContents):
                parts.append(base64.b64decode(contents.blob))
            elif isinstance(contents, TextResourceContents):
                parts.append(json.loads(contents.text))
        return parts

    (part,) = w.mcp_drive(w.mcp_artifact_server(deployment), operation, token=token)
    return part


def _write_then_read(deployment: w.Deployment, address: str, canonical: bytes, *, reader: str) -> dict[str, Any]:
    """The asker's put of ``canonical`` on its client lane, then ``reader``'s blob, presence and names at ``address``."""
    put = w._mcp_put(deployment, canonical)
    assert not w._put_failed(put), put
    return {
        "put": put["structured"],
        "blob": _read(deployment, artifact_blob_uri(content_address=address), token=reader),
        "presence": _read(deployment, artifact_meta_uri(content_address=address), token=reader),
        "names": _read(deployment, artifact_names_uri(content_address=address), token=reader),
    }


def _one_sided_pin(withheld: w.Deployment, nonexistent: w.Deployment) -> tuple[str, bytes]:
    """A pin the withholding deployment's record writer filed and the other did not, with its canonical bytes."""
    pins = {"withheld": names_alike._pins(withheld), "nonexistent": names_alike._pins(nonexistent)}
    only = [pin for pin in pins["withheld"] if pin not in pins["nonexistent"]]
    # Positive control: the shape files a pin in one deployment only. Without it nothing below is compared.
    assert only, pins
    pin = only[0]
    assert names_alike._filed_governed(withheld, pin), withheld.store.names_at(content_address=pin)
    assert nonexistent.store.names_at(content_address=pin) == ()
    canonical = withheld.store.get(content_address=pin)
    assert hashlib.sha256(canonical).hexdigest() == pin
    return pin, canonical


def _assert_the_client_lane_answered(read: dict[str, Any], deployment: w.Deployment, pin: str, canonical: bytes) -> None:
    """The mechanism by name: the bytes the asker filed, ``found: true``, and exactly the client-lane name."""
    assert read["blob"] == canonical, f"blob did not serve the filed bytes: {read['blob']!r}"[:300]
    assert hashlib.sha256(read["blob"]).hexdigest() == pin
    assert read["presence"] == {"found": True}, read["presence"]
    names = [ArtifactName.model_validate(item) for item in read["names"]]
    assert names == [
        ArtifactName(
            tenant_id=deployment.tenant, artifact_class=w.PIN_CLIENT_CLASS, name=w.PIN_CLIENT_NAME, artifact_version=pin
        )
    ], names
    assert not any(ReplayMint in deployment.store.write_kinds.for_class(n.artifact_class) for n in names), names


def _alike(reader: str, tmp_path: pathlib.Path) -> None:
    withheld = w.BUILDERS[w.SIMILARITY](tmp_path / "withheld", anchor=w.FROM_DECISION, holds=True, active=True)
    nonexistent = w.BUILDERS[w.SIMILARITY](tmp_path / "nonexistent", anchor=w.FROM_DECISION, holds=False, active=True)
    try:
        pin, canonical = _one_sided_pin(withheld, nonexistent)
        reads = {
            "withheld": _write_then_read(withheld, pin, canonical, reader=reader),
            "nonexistent": _write_then_read(nonexistent, pin, canonical, reader=reader),
        }
        # The property: put, blob, presence and names are one answer in the two worlds.
        assert reads["withheld"] == reads["nonexistent"], {
            side: {key: (value if not isinstance(value, bytes) else hashlib.sha256(value).hexdigest()) for key, value in read.items()}
            for side, read in reads.items()
        }
        for side, deployment in (("withheld", withheld), ("nonexistent", nonexistent)):
            _assert_the_client_lane_answered(reads[side], deployment, pin, canonical)
    finally:
        withheld.close()
        nonexistent.close()


def test_the_askers_filing_of_a_governed_pins_bytes_reads_back_alike_in_both_worlds(tmp_path: pathlib.Path) -> None:
    """The asker files a pin's canonical bytes on its client lane in the deployment whose record writer filed the pin
    and in the one whose did not, and reads them back: the same ``put``, blob, presence and names in both — its own
    bytes, ``found: true`` and its own client-lane name only. RED before design 1.2: the governed shell where the pin
    was filed, the asker's bytes where it was not."""
    _alike(w.ASKER_TOKEN, tmp_path)


def test_another_principal_reads_the_tenants_client_filing_alike_in_both_worlds(tmp_path: pathlib.Path) -> None:
    """After the asker's write, another principal of the tenant reads the address: alike in both worlds, and it is
    the tenant's client-lane filing it reads (C8's tenant-shared client lane, kept). RED before design 1.2."""
    _alike(w.OTHER_TOKEN, tmp_path)


def test_a_records_owner_keeps_its_provenance_when_its_bytes_are_also_on_a_client_lane(tmp_path: pathlib.Path) -> None:
    """Guard for names rule A6 (design 1.2, Q2; Dave, 2026-10-09 10:54 MST, "the A6 names rule"): when a principal files
    a genuine record's exact bytes on its client lane, the record's owner still reads the record writer's name at the
    address — so provenance read through the MCP store (``filed_by_record_writer``) stays true for it — while another
    principal, whom the governed read does not admit, reads the client-lane name only, never the shell. A names rule
    that answered client-lane names alone (the measured A2) loses the owner's provenance here."""
    deployment = w.BUILDERS[w.SIMILARITY](tmp_path / "record-twin", anchor=w.FROM_DECISION, holds=True, active=True)
    try:
        refused = _read(deployment, artifact_meta_uri(content_address=NOBODYS), token=w.ASKER_TOKEN)
        record = w._reference_parts(RefusalEnvelope.model_validate(refused).replay_reference)["version"]
        assert names_alike._filed_governed(deployment, record)

        def provenance(answer: Any) -> bool:
            assert isinstance(answer, list), f"the names read answered {answer!r}, not names"
            return any(
                ArtifactName.model_validate(n).tenant_id == deployment.tenant
                and ReplayMint in deployment.store.write_kinds.for_class(ArtifactName.model_validate(n).artifact_class)
                for n in answer
            )

        names = artifact_names_uri(content_address=record)
        assert provenance(_read(deployment, names, token=w.ASKER_TOKEN)), "control: provenance before the twin"
        put = w._mcp_put(deployment, deployment.store.get(content_address=record), name="my-copy")
        assert not w._put_failed(put), put
        assert provenance(_read(deployment, names, token=w.ASKER_TOKEN)), "the owner lost its record's provenance"
        assert _read(deployment, artifact_blob_uri(content_address=record), token=w.ASKER_TOKEN) == deployment.store.get(
            content_address=record
        )
        other = [ArtifactName.model_validate(n) for n in _read(deployment, names, token=w.OTHER_TOKEN)]
        assert other == [
            ArtifactName(
                tenant_id=deployment.tenant, artifact_class=w.PIN_CLIENT_CLASS, name="my-copy", artifact_version=record
            )
        ], other
    finally:
        deployment.close()
