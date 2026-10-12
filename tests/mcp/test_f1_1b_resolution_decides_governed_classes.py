# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""Design 1.1 (F1-1b): the MCP versioned-URI resolution decides a governed class through the governed read.

``D-IMPL-378``. Dave, 2026-10-09 06:06 MST, confirmed 06:21: *"A; fix F1-1b and F1-1c now; X17(a)."* His choices on
the design, 2026-10-09 10:54 MST, design 1.1: *"Q1 (a), a refusal shell and a typed client error. Q2 (a), keep the
class/name permission. Q3, a two-parent error class is acceptable."*

The resolution resource (``ccf-artifact://{tenant}/{class}/{name}@{version}``) answered ``found: true`` where a name
was filed and ``found: false`` where it was not, from the naming index alone, for every class. For a class the
substrate declares under ``ReplayMint`` — a query pin above all, whose address is the hash of its own inputs — that
told a deployment that filed the pin from one that did not, and it resolved a record its tenant had sealed (Q12) and a
record of another principal. Now a governed class resolves through
:func:`~ccf_runtime.authz.delivery_boundary.govern_resolution`: a principal the governed read admits still gets its
address; everyone else gets the one recorded, disclosed shell, which the MCP store client raises as
:class:`~ccf.artifacts.protocol.ArtifactResolutionRefused`.

Asserted by mechanism, as the asker, through the real MCP artifact server. Controls hold the other side: an admitted
principal still resolves its own record, and a client-lane filing still resolves (and an unregistered client-lane
version still answers ``found: false``).

Fixture vocabulary only (CINV-01).
"""

from __future__ import annotations

import base64
import hashlib
import json
import pathlib
from typing import Any

import anyio
import pytest
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.types import TextResourceContents
from pydantic import AnyUrl

import ccf.artifacts.protocol as artifact_protocol
from ccf.artifacts.mcp_store import McpArtifactStore
from ccf.artifacts.protocol import ArtifactName, ArtifactNotFound, ArtifactUriUnresolvable, artifact_uri
from ccf.mcp.errors import McpServerUnreachable
from ccf.products.refusal import RefusalEnvelope
from ccf_runtime.authz.delivery_boundary import DEREFERENCE_PRODUCT_ID
from ccf_runtime.mcp.artifact_server import PUT_ARTIFACT_TOOL, artifact_meta_uri
from tests.mcp import test_f1_names_present_governed_and_absent_alike as names_alike
from tests.mcp import test_f1_names_refusal_typed_through_the_client as typed
from tests.products import sec020_worlds as w

#: An address nobody filed in any deployment here.
NOBODYS = hashlib.sha256(b"f1-1b: an address nobody filed").hexdigest()

#: A class no deployment here declares: the caller's client lane.
CLIENT_CLASS = "fixture.client-notes"


def _read(deployment: w.Deployment, uri: str, *, token: str = w.ASKER_TOKEN) -> Any:
    """The resource at ``uri``, read as ``token`` through the real MCP artifact server, parsed."""

    async def operation(session: Any) -> Any:
        result = await session.read_resource(AnyUrl(uri))
        return [c.text for c in result.contents if isinstance(c, TextResourceContents)]

    read = w.mcp_drive(w.mcp_artifact_server(deployment), operation, token=token)
    assert isinstance(read, list) and len(read) == 1, f"the read of {uri} did not answer one text part: {read!r}"
    return json.loads(read[0])


def _pin_uri(deployment: w.Deployment, pin: str) -> str:
    """The versioned URI the deployment's record writer filed ``pin`` under (an auditor's read of its naming)."""
    (named,) = [n for n in deployment.store.names_at(content_address=pin) if n.tenant_id == deployment.tenant]
    return artifact_uri(
        tenant_id=named.tenant_id, artifact_class=named.artifact_class, name=named.name, artifact_version=pin
    )


def _nobodys_uri(deployment: w.Deployment, pin: str) -> str:
    """A versioned URI in the pin's own (governed) class that nobody filed."""
    (named,) = [n for n in deployment.store.names_at(content_address=pin) if n.tenant_id == deployment.tenant]
    return artifact_uri(
        tenant_id=deployment.tenant, artifact_class=named.artifact_class, name=NOBODYS, artifact_version=NOBODYS
    )


def _reduced(answer: Any, uri: str) -> Any:
    """``answer`` less what legitimately varies: the URI the caller presented, and the refusal's own record."""
    if not isinstance(answer, dict):
        return answer
    reduced = json.loads(json.dumps(answer, sort_keys=True).replace(uri, "<presented-uri>"))
    reduced.pop("replay_reference", None)
    return reduced


def _assert_alike(first: Any, first_uri: str, second: Any, second_uri: str, *, what: str) -> None:
    """The property, then the mechanism: one answer, the governed dereference's ``nonexistent`` shell."""
    assert _reduced(first, first_uri) == _reduced(second, second_uri), (
        f"{what}: the resolution told the two URIs apart — {first_uri} answered"
        f" {json.dumps(first, sort_keys=True)[:240]} and {second_uri} answered {json.dumps(second, sort_keys=True)[:240]}"
    )
    for answer, uri in ((first, first_uri), (second, second_uri)):
        assert isinstance(answer, dict) and "found" not in answer, f"{what}: {uri} answered {answer!r}, not a shell"
        shell = RefusalEnvelope.model_validate(answer)
        assert shell.kind == "subject-unavailable", shell.kind
        assert shell.request.product_id == DEREFERENCE_PRODUCT_ID, shell.request
        assert dict(shell.request.parameters) == {"reference": uri}, shell.request
        assert shell.fields.get("cause") == names_alike.NONEXISTENT, shell.fields
        assert shell.fields.get("error_code") == names_alike.EVIDENCE_ABSENT, shell.fields


@pytest.mark.parametrize("shape", [w.SUBJECT_KEYED, w.SIMILARITY])
def test_a_present_governed_pin_and_a_governed_uri_nobody_filed_resolve_alike(tmp_path: pathlib.Path, shape: str) -> None:
    """One deployment, the asker to whom the subject is withheld: resolving the URI of the pin its own question filed
    and a URI of the same governed class that nobody filed are one answer, the governed dereference's ``nonexistent``
    shell. RED before design 1.1: the pin answered ``found: true`` with its address, the other ``found: false``."""
    deployment = w.BUILDERS[shape](tmp_path / shape, anchor=w.FROM_DECISION, holds=True, active=True)
    try:
        pin = names_alike._pins(deployment)[0]
        # Positive controls: the pin really is a present governed filing, and the other URI really names nothing.
        assert names_alike._filed_governed(deployment, pin), deployment.store.names_at(content_address=pin)
        assert deployment.store.names_at(content_address=NOBODYS) == ()
        pin_uri, nobodys_uri = _pin_uri(deployment, pin), _nobodys_uri(deployment, pin)
        _assert_alike(
            _read(deployment, pin_uri), pin_uri, _read(deployment, nobodys_uri), nobodys_uri,
            what=f"[{shape}] a present query pin's URI against a governed URI nobody filed",
        )
    finally:
        deployment.close()


def test_resolution_does_not_tell_the_withheld_deployment_from_the_nonexistent_one(tmp_path: pathlib.Path) -> None:
    """The two-deployment cross-read, ``similarity_refreshed``: a pin filed in one deployment only, resolved by the
    same URI in each deployment as the asker, answers alike — in both directions."""
    withheld = w.BUILDERS[w.SIMILARITY](tmp_path / "withheld", anchor=w.FROM_DECISION, holds=True, active=True)
    nonexistent = w.BUILDERS[w.SIMILARITY](tmp_path / "nonexistent", anchor=w.FROM_DECISION, holds=False, active=True)
    try:
        pins = {"withheld": names_alike._pins(withheld), "nonexistent": names_alike._pins(nonexistent)}
        only = {
            side: [pin for pin in pins[side] if pin not in pins[other]]
            for side, other in (("withheld", "nonexistent"), ("nonexistent", "withheld"))
        }
        # Positive control: the shape files a pin in one deployment only, in each direction.
        assert only["withheld"] and only["nonexistent"], pins
        for side, present_in, absent_in in (
            ("withheld", withheld, nonexistent),
            ("nonexistent", nonexistent, withheld),
        ):
            pin = only[side][0]
            uri = _pin_uri(present_in, pin)
            assert absent_in.store.names_at(content_address=pin) == ()
            _assert_alike(
                _read(present_in, uri), uri, _read(absent_in, uri), uri,
                what=f"a pin filed only in the {side} deployment, resolved in each deployment",
            )
    finally:
        withheld.close()
        nonexistent.close()


def test_an_admitted_principal_still_resolves_its_own_governed_record(tmp_path: pathlib.Path) -> None:
    """The asker's own read-refusal record — a governed record the governed read admits back to the principal it
    names — still resolves to its address for the asker (the control half, green before and after). Another principal
    of the tenant now gets the governed shell at the same URI: it answered ``found: true`` before design 1.1, the
    missing principal hold (the panel's K20), so this half is RED before."""
    deployment = w.BUILDERS[w.SIMILARITY](tmp_path / "admitted", anchor=w.FROM_DECISION, holds=True, active=True)
    try:
        refused = _read(deployment, artifact_meta_uri(content_address=NOBODYS))
        parts = w._reference_parts(RefusalEnvelope.model_validate(refused).replay_reference)
        uri = artifact_uri(
            tenant_id=parts["tenant"], artifact_class=parts["artifact_class"], name=parts["name"],
            artifact_version=parts["version"],
        )
        assert names_alike._filed_governed(deployment, parts["version"])
        assert _read(deployment, uri) == {"content_address": parts["version"], "found": True}
        other = _read(deployment, uri, token=w.OTHER_TOKEN)
        assert isinstance(other, dict) and "found" not in other, f"another principal resolved the asker's record: {other!r}"
        shell = RefusalEnvelope.model_validate(other)
        assert (shell.kind, shell.request.product_id) == ("subject-unavailable", DEREFERENCE_PRODUCT_ID), shell
    finally:
        deployment.close()


def test_the_callers_own_client_lane_filing_still_resolves(tmp_path: pathlib.Path) -> None:
    """Control, green before and after: a filing on the asker's client lane resolves ``found: true`` for the asker and
    for another principal of the tenant, and an unregistered client-lane version still answers ``found: false`` (FW-6's
    rendering), so the shell above is the governed decision and not a resource that refuses everything."""
    deployment = w.BUILDERS[w.SIMILARITY](tmp_path / "client-lane", anchor=w.FROM_DECISION, holds=True, active=True)
    try:

        async def put(session: Any) -> Any:
            result = await session.call_tool(
                PUT_ARTIFACT_TOOL,
                {
                    "artifact_class": CLIENT_CLASS,
                    "name": "n1",
                    "canonical_b64": base64.b64encode(b'{"f1-1b":"control"}').decode("ascii"),
                },
            )
            return result.structuredContent

        filed = w.mcp_drive(w.mcp_artifact_server(deployment), put, token=w.ASKER_TOKEN)
        address = hashlib.sha256(b'{"f1-1b":"control"}').hexdigest()
        assert filed["content_address"] == address, filed
        for token in (w.ASKER_TOKEN, w.OTHER_TOKEN):
            assert _read(deployment, filed["uri"], token=token) == {"content_address": address, "found": True}
        unregistered = filed["uri"].replace("/n1@", "/n2@")
        assert _read(deployment, unregistered) == {"content_address": None, "found": False}
    finally:
        deployment.close()


def test_the_mcp_store_raises_the_typed_refusal_for_a_governed_refusal(tmp_path: pathlib.Path) -> None:
    """The client (design 1.1, Q1 (a), Q3): ``McpArtifactStore.resolve_uri`` raises
    :class:`~ccf.artifacts.protocol.ArtifactResolutionRefused` — an ``ArtifactUriUnresolvable`` and an
    ``ArtifactNotFound``, carrying the server's shell, never ``McpServerUnreachable`` — for a governed URI the server
    refused; a client-lane URI nobody registered still raises the plain ``ArtifactUriUnresolvable``."""
    # Looked up at the call, not imported: the contract this test pins is what design 1.1 adds.
    refusal_type = artifact_protocol.ArtifactResolutionRefused
    deployment = w.BUILDERS[w.SIMILARITY](tmp_path / "client", anchor=w.FROM_DECISION, holds=True, active=True)
    try:
        pin = names_alike._pins(deployment)[0]
        governed = _nobodys_uri(deployment, pin)
        with typed._store_over_http(
            w.mcp_artifact_server(deployment), w.ASKER_TOKEN, deployment.store.write_kinds
        ) as store:
            assert isinstance(store, McpArtifactStore)
            with pytest.raises(refusal_type) as refused:
                store.resolve_uri(uri=governed)
            assert isinstance(refused.value, ArtifactUriUnresolvable)
            assert isinstance(refused.value, ArtifactNotFound)
            assert not isinstance(refused.value, McpServerUnreachable)
            assert refused.value.envelope.kind == "subject-unavailable", refused.value.envelope
            assert dict(refused.value.envelope.request.parameters) == {"reference": governed}
            unregistered = artifact_uri(
                tenant_id=deployment.tenant, artifact_class=CLIENT_CLASS, name="nobody", artifact_version=NOBODYS
            )
            with pytest.raises(ArtifactUriUnresolvable) as plain:
                store.resolve_uri(uri=unregistered)
            assert not isinstance(plain.value, refusal_type), type(plain.value).__mro__
    finally:
        deployment.close()


def test_q12_the_mcp_resolution_resource_holds_the_owner_read_back_rule(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Q12 (Dave, 2026-10-07; owner read-back is default-deny) on the resolution resource, as
    ``tests/http_api/test_sec020_q12_owner_read_back.py::test_q12_the_mcp_artifact_servers_other_governed_resources_hold_the_same_rule``
    holds it on presence and names: the owner at ``full``, its tenant listing no class for read-back, resolves its own
    record's URI to the refusal shell, recorded ``evidence-class-sealed``. RED before design 1.1: ``found: true``."""
    import tests.mcp.test_c2_tenant_hold_mcp as c2  # noqa: PLC0415
    from ccf_runtime.http_api.errors import ERROR_EVIDENCE_CLASS_SEALED  # noqa: PLC0415
    from tests.http_api import test_sec020_q12_owner_read_back as q12  # noqa: PLC0415
    from tests.mcp.guarded_servers import REPLAY_RECORD_CLASS  # noqa: PLC0415

    granted = c2._policy

    def unlisted(tenant: str) -> Any:
        policy = granted(tenant)
        return type(policy).model_validate({**policy.model_dump(), "evidence_readable_classes": frozenset()})

    monkeypatch.setattr(c2, "_policy", unlisted)
    world = q12._world(tmp_path)
    address = q12._file(world, q12._record(tenant=q12.MCP_TENANT, principal=q12.MCP_PRINCIPAL, subject="subject-q12-uri"))
    (named,) = [n for n in world.store.names_at(content_address=address) if n.artifact_class == REPLAY_RECORD_CLASS]
    assert isinstance(named, ArtifactName)
    uri = artifact_uri(
        tenant_id=named.tenant_id, artifact_class=named.artifact_class, name=named.name, artifact_version=address
    )
    reset = c2._as_grant(c2._grant())
    try:
        (answer,) = list(anyio.run(world.server.read_resource, uri))
    finally:
        auth_context_var.reset(reset)
    content = answer.content if isinstance(answer.content, bytes) else answer.content.encode("utf-8")
    try:
        shell = RefusalEnvelope.model_validate_json(content)
    except ValueError:
        pytest.fail(f"the owner's resolution crossed although no class is listed: {content[:200]!r}")
    assert q12._internal_error_code(world.recorded, shell.replay_reference) == ERROR_EVIDENCE_CLASS_SEALED
