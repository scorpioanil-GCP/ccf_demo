# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""Decision 10 (b), as ruled: a 401 on a WRITE is typed too, under one renamed type that covers reads and writes.

Decision 10 (b), 2026-10-09 16:38 MST (``D-IMPL-378``; the text is Grok's recommendation, which Dave adopted), verbatim:
*"(b) Type a 401 on a write, and rename the type so it covers both."* It extends repair 2.5 (a) (10:54 MST),
verbatim: *"Return a typed authentication refusal for 401, preserving its distinction from authorization denial and
transport outage."* Repair 2.5 (a) was built for reads only: ``McpArtifactStore.put`` kept reporting the server
guard's 401 as ``ccf.mcp.errors.McpServerUnreachable``, an outage, and
``tests/conformance/test_artifactstore.py`` pinned that. SEC-020 stays open: this module measures, it closes nothing.

What is asserted, each by mechanism (type, cause, status code), never by message text:

* **one name.** ``ccf.artifacts.protocol.ArtifactStoreUnauthenticated`` is the typed authentication refusal, an
  ``ArtifactStoreError`` in the module's ``__all__``; the read-only name it replaces is gone, with no alias left in
  ``src/`` or ``runtime/`` (nothing has shipped);
* **the write.** ``put`` raises it when the guard answers 401, for each credential shape the guard answers 401 (no
  credential, one that is not a bearer token, a bearer token the verifier does not know), chained from the guard's
  own 401 response, with no ``McpServerUnreachable`` anywhere in its chain; and the substrate holds nothing new;
* **the distinction.** at the same write, a credential without the required scope (the guard's 403) and a refused
  connection still reach the writer as ``McpServerUnreachable`` (decision 11 (a) keeps the 403 an outage, disclosed),
  so only the 401 is typed;
* **no reclassification.** the five reference-mismatch refusals (decision 5 (a)), which are ``ArtifactStoreError``
  subclasses raised after a write returns, are neither the typed refusal nor its parent.

Positive control first in each write test: the same server, transport and store, presenting the token the verifier
knows, file the artifact, so the refusal is the credential's and not the server's or the transport's. The world,
the transport and the credential shapes are ``tests/mcp/test_auth_401_typed_through_the_client.py``'s. Fixture
vocabulary only (CINV-01).
"""

from __future__ import annotations

import hashlib
import importlib
import pathlib
from http import HTTPStatus
from typing import Any

import httpx
import pytest

import ccf.artifacts.protocol as artifact_protocol
from ccf.artifacts.protocol import ArtifactRef, ArtifactStoreError
from ccf.authz.capability import ArtifactWrite
from ccf.contracts.canonical import canonical_bytes
from ccf.mcp.errors import McpServerUnreachable
from tests.controlplane.capabilities import capability
from tests.mcp.guarded_servers import TENANT
from tests.mcp.test_auth_401_typed_through_the_client import (
    CLIENT_CLASS,
    GUARD_401,
    KNOWN_TOKEN,
    SCOPELESS_TOKEN,
    UNKNOWN,
    World,
    assert_the_authentication_refusal,
    raised_by,
    single_cause,
    store_at_nothing,
    store_over_http,
)

#: The one name the ruling asks for: the typed authentication refusal, for reads and writes.
RENAMED = "ArtifactStoreUnauthenticated"

#: The read-only name repair 2.5 (a) shipped in this batch, which the rename replaces with no alias.
RETIRED = "ArtifactReadUnauthenticated"

#: The reference-mismatch refusals decision 5 (a) adds, by ``module:QualName``: raised after a write RETURNS.
REFERENCE_MISMATCHES = (
    "ccf.replay.serve:ReplayReferenceMismatch",
    "ccf.replay.serve:QueryPinReferenceMismatch",
    "ccf.peering.admission:AdmissionRecordReferenceMismatch",
    "ccf.products.child_resolver:ChildQuestionReferenceMismatch",
    "ccf_runtime.workflow.engine:WorkflowTraceReferenceMismatch",
)

_REPO = pathlib.Path(__file__).resolve().parents[2]


def renamed_refusal() -> type[BaseException]:
    """The ruled one-name refusal, or a MISSING CONTRACT failure that names it."""
    found = getattr(artifact_protocol, RENAMED, None)
    if not (isinstance(found, type) and issubclass(found, BaseException)):
        pytest.fail(
            f"MISSING CONTRACT: ccf.artifacts.protocol.{RENAMED}, the one typed authentication refusal for reads and"
            " writes that decision 10 (b) requires (D-IMPL-378, 2026-10-09 16:38 MST; the text is Grok's recommendation, which Dave adopted), does not exist on this"
            " tree"
        )
    return found


def chain_of(error: BaseException) -> list[BaseException]:
    """Every exception reachable from ``error`` by cause, by context and by exception-group membership."""
    seen: set[int] = set()
    stack: list[BaseException] = [error]
    found: list[BaseException] = []
    while stack:
        current = stack.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        found.append(current)
        stack.extend(link for link in (current.__cause__, current.__context__) if link is not None)
        if isinstance(current, BaseExceptionGroup):
            stack.extend(current.exceptions)
    return found


def a_write(label: str) -> tuple[Any, dict[str, str], str]:
    """A client-lane write of the guarded servers' tenant: its capability, its payload, and the payload's address."""
    payload = {"note": label}
    return (
        capability(ArtifactWrite, tenant=TENANT, resource=f"{CLIENT_CLASS}/{label}"),
        payload,
        hashlib.sha256(canonical_bytes(payload)).hexdigest(),
    )


# --- one name ----------------------------------------------------------------------------------------------------


def test_one_type_names_the_authentication_refusal_for_reads_and_writes_and_the_read_only_name_is_gone() -> None:
    """The rename, as ruled: one honest name, an ``ArtifactStoreError`` the module exports, and no alias anywhere.

    The alias check reads the source of every module under ``src/`` and ``runtime/``: an import, an assignment or a
    docstring naming the retired type would let a caller keep writing the read-only name for a refusal that is no
    longer read-only."""
    renamed = renamed_refusal()
    assert issubclass(renamed, ArtifactStoreError), renamed.__mro__
    assert RENAMED in artifact_protocol.__all__, "the renamed refusal is not exported from ccf.artifacts.protocol"
    assert not hasattr(artifact_protocol, RETIRED), f"ccf.artifacts.protocol still binds the retired name {RETIRED}"
    assert RETIRED not in artifact_protocol.__all__, f"ccf.artifacts.protocol still exports the retired name {RETIRED}"
    naming = sorted(
        str(path.relative_to(_REPO))
        for tree in ("src", "runtime")
        for path in (_REPO / tree).rglob("*.py")
        if RETIRED in path.read_text(encoding="utf-8")
    )
    assert naming == [], f"modules under src/ and runtime/ still name the retired type {RETIRED}: {naming}"


# --- the write ---------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("credential", list(GUARD_401))
def test_put_raises_the_typed_authentication_refusal_when_the_guard_answers_401(
    tmp_path: pathlib.Path, credential: str
) -> None:
    """``McpArtifactStore.put`` given a credential the guard answers 401, for each credential shape.

    Measured on the base (``59f6aaaf``): ``McpServerUnreachable``, the outage, as the pinned conformance test said.
    Here: the typed authentication refusal, chained from the guard's 401 response (the helper asserts the type, that
    it is no outage, no access decision, no absence and no MCP-client error, and the cause's status code), with no
    ``McpServerUnreachable`` anywhere in its chain, and nothing new on the substrate."""
    world = World(tmp_path)
    authorized, payload, address = a_write("written-with-the-known-token")
    with store_over_http(world.server(), {"Authorization": f"Bearer {KNOWN_TOKEN}"}) as known:
        filed = known.put(authorized, payload)
    assert isinstance(filed, ArtifactRef) and filed.content_address == address, filed
    assert world.store.exists(content_address=address), "the positive control filed nothing"

    authorized, payload, address = a_write("refused")
    with store_over_http(world.server(), GUARD_401[credential]) as refused:
        raised = raised_by(lambda: refused.put(authorized, payload), what=f"put, presenting {credential}")
    assert_the_authentication_refusal(raised, what=f"put, presenting {credential}")
    assert isinstance(raised, renamed_refusal()), type(raised).__mro__
    outages = [type(link).__name__ for link in chain_of(raised) if isinstance(link, McpServerUnreachable)]
    assert outages == [], f"put, presenting {credential}: the typed refusal carries an outage in its chain: {outages}"
    assert not world.store.exists(content_address=address), f"put, presenting {credential}: the write was filed"


def test_at_one_write_a_401_a_403_and_a_refused_connection_reach_the_writer_as_two_types(
    tmp_path: pathlib.Path,
) -> None:
    """Only the 401 is typed: the same ``put``, three ways it does not complete.

    * the guard's 401 (a token its verifier does not know): the typed authentication refusal;
    * the guard's 403 (a token it knows, whose grant lacks the required scope): ``McpServerUnreachable``, chained from
      the 403 response — decision 11 (a) keeps it so, disclosed in SP §4.10;
    * a refused connection (nothing listening): ``McpServerUnreachable``, chained from the connection error."""
    world = World(tmp_path)
    authorized, payload, _ = a_write("three-ways")
    with store_over_http(world.server(), UNKNOWN) as store:
        guard_401 = raised_by(lambda: store.put(authorized, payload), what="the guard's 401")
    with store_over_http(world.server(), {"Authorization": f"Bearer {SCOPELESS_TOKEN}"}) as store:
        guard_403 = raised_by(lambda: store.put(authorized, payload), what="the guard's 403")
    with store_at_nothing() as store:
        outage = raised_by(lambda: store.put(authorized, payload), what="a refused connection")

    assert_the_authentication_refusal(guard_401, what="put, the guard's 401")

    unauthenticated = renamed_refusal()
    assert type(guard_403) is McpServerUnreachable, (type(guard_403).__mro__, str(guard_403)[:300])
    cause = single_cause(guard_403)
    assert isinstance(cause, httpx.HTTPStatusError), repr(cause)
    assert cause.response.status_code == HTTPStatus.FORBIDDEN, cause.response.status_code
    assert not isinstance(guard_403, unauthenticated), type(guard_403).__mro__

    assert type(outage) is McpServerUnreachable, (type(outage).__mro__, str(outage)[:300])
    assert isinstance(single_cause(outage), httpx.ConnectError), repr(single_cause(outage))
    assert not isinstance(outage, unauthenticated), type(outage).__mro__


# --- no reclassification -----------------------------------------------------------------------------------------


@pytest.mark.parametrize("mismatch", REFERENCE_MISMATCHES)
def test_a_reference_mismatch_refusal_is_not_the_authentication_refusal(mismatch: str) -> None:
    """The writers' own refusals (decision 5 (a)) keep their own names: a store that answered a write with the wrong
    reference is not a credential the server refused, so neither class is the other or derives from it."""
    module, _, name = mismatch.partition(":")
    refusal = getattr(importlib.import_module(module), name)
    unauthenticated = renamed_refusal()
    assert issubclass(refusal, ArtifactStoreError), refusal.__mro__
    assert not issubclass(refusal, unauthenticated), refusal.__mro__
    assert not issubclass(unauthenticated, refusal), unauthenticated.__mro__
