"""F1-1: the MCP artifact server's ``names`` resource must not tell a present governed address from an absent one.

The ``D-IMPL-378`` final panel's seat F1, finding F1-1, reproduced by execution on
``a539c215``. An address the caller's tenant filed under a governed class — one
the substrate's ``WriteKinds`` declares under ``ReplayMint`` — that is not a
readable record answered the governed dereference's refusal shell on the
``names`` resource, while an address nobody filed answered ``[]``. An
executed-query pin is such an address: it is ``content_hash(GraphQuery)``, the
same whichever principal asked. The blob and presence resources route both
cases through the one governed read and answer them alike
(``runtime/ccf_runtime/mcp/artifact_server.py::build_artifact_server``, "THE
SPLIT"); the names resource ran the governed read only for an address its
tenant had filed.

In the ``similarity_refreshed`` shape the withheld and the nonexistent
deployments file different pins, because the second walk segment's query embeds
the set of entities the in-process operator left standing. Reading ``names`` at a
pin that exists in one deployment only therefore told an unentitled asker
whether the withheld subject exists.

Asserted by mechanism, as the asker, through the real MCP artifact server
(streamable HTTP, bearer token, client session): the two answers are the same up
to the address the caller presented and the refusal's own record reference, and
each is the governed dereference's ``nonexistent`` shell — kind
``subject-unavailable``, cause ``nonexistent``, error code ``evidence-absent``,
under the dereference's own request identity. A control holds the other side:
the caller's own client-lane filing still answers its names.

Fixture vocabulary only (CINV-01).
"""

from __future__ import annotations

import hashlib
import json
import pathlib
from typing import Any

import pytest
from mcp.types import TextResourceContents
from pydantic import AnyUrl

from ccf.artifacts.protocol import ArtifactName
from ccf.authz.capability import ArtifactWrite, ReplayMint
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.products.refusal import RefusalEnvelope
from ccf_runtime.authz.delivery_boundary import DEREFERENCE_PRODUCT_ID
from ccf_runtime.http_api.errors import ERROR_EVIDENCE_ABSENT
from ccf_runtime.mcp.artifact_server import artifact_names_uri
from tests.controlplane.capabilities import capability
from tests.products import sec020_worlds as w

#: An address nobody filed in any deployment here.
NOBODYS = hashlib.sha256(b"f1-1: an address nobody filed").hexdigest()

#: A class no deployment here declares: the caller's client lane.
CLIENT_CLASS = "fixture.client-notes"

#: The shell members a refusal renders as canonical JSON (``RefusalEnvelope.fields``).
NONEXISTENT = canonical_bytes("nonexistent").decode("utf-8")
EVIDENCE_ABSENT = canonical_bytes(ERROR_EVIDENCE_ABSENT).decode("utf-8")


def _names(deployment: w.Deployment, address: str) -> Any:
    """The names resource's answer at ``address``, read as the asker through the real MCP artifact server."""

    async def operation(session: Any) -> Any:
        result = await session.read_resource(AnyUrl(artifact_names_uri(content_address=address)))
        return [c.text if isinstance(c, TextResourceContents) else repr(c) for c in result.contents]

    read = w.mcp_drive(w.mcp_artifact_server(deployment), operation, token=w.ASKER_TOKEN)
    assert isinstance(read, list) and len(read) == 1, f"the names read did not answer one text part: {read!r}"
    return json.loads(read[0])


def _pins(deployment: w.Deployment) -> tuple[str, ...]:
    """Ask the subject in process; the executed-query pins its record names, read as an auditor."""
    observation = w.observe_in_process(deployment, w.SUBJECT)
    reference = w._reference_of(w.IN_PROCESS, observation)
    assert reference is not None, observation.channels
    record = w._record_at(deployment.store, reference)
    return tuple(record.content_generation_path.graph_query_sequence)


def _filed_governed(deployment: w.Deployment, address: str) -> bool:
    """Whether the deployment's store files ``address`` under its tenant in a ``ReplayMint`` class (an auditor's read)."""
    return any(
        named.tenant_id == deployment.tenant
        and ReplayMint in deployment.store.write_kinds.for_class(named.artifact_class)
        for named in deployment.store.names_at(content_address=address)
    )


def _without_presentation(answer: Any, address: str) -> Any:
    """``answer`` less what legitimately varies: the address the caller presented, and the refusal's own record."""
    if not isinstance(answer, dict):
        return answer
    reduced = json.loads(json.dumps(answer, sort_keys=True).replace(address, "<presented-address>"))
    reduced.pop("replay_reference", None)
    return reduced


def _assert_alike(first: Any, first_address: str, second: Any, second_address: str, *, what: str) -> None:
    """The property, then the mechanism: one answer, and it is the governed dereference's ``nonexistent`` shell."""
    assert _without_presentation(first, first_address) == _without_presentation(second, second_address), (
        f"{what}: the names resource told the two addresses apart —"
        f" {first_address[:12]}… answered {json.dumps(first, sort_keys=True)[:240]}"
        f" and {second_address[:12]}… answered {json.dumps(second, sort_keys=True)[:240]}"
    )
    for answer, address in ((first, first_address), (second, second_address)):
        assert isinstance(answer, dict), f"{what}: {address[:12]}… answered {answer!r}, not a refusal shell"
        shell = RefusalEnvelope.model_validate(answer)
        assert shell.kind == "subject-unavailable", shell.kind
        assert shell.request.product_id == DEREFERENCE_PRODUCT_ID, shell.request
        assert dict(shell.request.parameters) == {"reference": address}, shell.request
        assert shell.fields.get("cause") == NONEXISTENT, shell.fields
        assert shell.fields.get("error_code") == EVIDENCE_ABSENT, shell.fields


@pytest.mark.parametrize("shape", [w.SUBJECT_KEYED, w.SIMILARITY])
def test_a_present_governed_pin_and_an_address_nobody_filed_answer_alike(
    tmp_path: pathlib.Path, shape: str
) -> None:
    """One deployment, the asker to whom the subject is withheld: ``names`` at the pin its own question filed and
    ``names`` at an address nobody filed are one answer, the governed dereference's ``nonexistent`` shell."""
    deployment = w.BUILDERS[shape](tmp_path / shape, anchor=w.FROM_DECISION, holds=True, active=True)
    try:
        pin = _pins(deployment)[0]
        # Positive controls: the first address really is a present governed non-record filing of the
        # asker's tenant, and the second really is nobody's.
        assert _filed_governed(deployment, pin), deployment.store.names_at(content_address=pin)
        assert deployment.store.names_at(content_address=NOBODYS) == ()
        _assert_alike(
            _names(deployment, pin), pin, _names(deployment, NOBODYS), NOBODYS,
            what=f"[{shape}] a present query pin against an address nobody filed",
        )
    finally:
        deployment.close()


def test_names_does_not_tell_the_withheld_deployment_from_the_nonexistent_one(tmp_path: pathlib.Path) -> None:
    """F1's two-deployment cross-read, ``similarity_refreshed``: a pin filed in one deployment only, read at the same
    address in each deployment as the asker, answers alike — in both directions."""
    withheld = w.BUILDERS[w.SIMILARITY](tmp_path / "withheld", anchor=w.FROM_DECISION, holds=True, active=True)
    nonexistent = w.BUILDERS[w.SIMILARITY](tmp_path / "nonexistent", anchor=w.FROM_DECISION, holds=False, active=True)
    try:
        pins = {"withheld": _pins(withheld), "nonexistent": _pins(nonexistent)}
        only = {
            side: [pin for pin in pins[side] if pin not in pins[other]]
            for side, other in (("withheld", "nonexistent"), ("nonexistent", "withheld"))
        }
        # Positive control: the shape files a pin in one deployment only, in each direction. Without it the
        # cross-read below would compare nothing.
        assert only["withheld"] and only["nonexistent"], pins
        for side, present_in, absent_in in (
            ("withheld", withheld, nonexistent),
            ("nonexistent", nonexistent, withheld),
        ):
            address = only[side][0]
            assert _filed_governed(present_in, address), present_in.store.names_at(content_address=address)
            assert absent_in.store.names_at(content_address=address) == ()
            _assert_alike(
                _names(present_in, address), address, _names(absent_in, address), address,
                what=f"a pin filed only in the {side} deployment, read in each deployment",
            )
    finally:
        withheld.close()
        nonexistent.close()


def test_the_callers_own_client_lane_filing_still_answers_its_names(tmp_path: pathlib.Path) -> None:
    """The other side, held: an address the asker's tenant filed on its client lane answers its names — not the shell
    — so the answer above is the governed decision and not a names resource that answers nothing."""
    deployment = w.BUILDERS[w.SIMILARITY](tmp_path / "client-lane", anchor=w.FROM_DECISION, holds=True, active=True)
    try:
        document = {"note": "f1-1 control", "subject": "none"}
        filed = deployment.store.put(
            capability(ArtifactWrite, tenant=deployment.tenant, resource=f"{CLIENT_CLASS}/control"), document
        )
        assert filed.content_address == content_hash(document)
        answer = _names(deployment, filed.content_address)
        assert [ArtifactName.model_validate(item) for item in answer] == [
            ArtifactName(
                tenant_id=deployment.tenant,
                artifact_class=CLIENT_CLASS,
                name="control",
                artifact_version=filed.content_address,
            )
        ]
    finally:
        deployment.close()
