"""FW-3 (whole-branch review I-2): an erasure crosses the MCP doors only as its disclosure level allows (SEC-009 x SEC-024; `D-IMPL-374`).

The whole-branch review measured it (probes X1 and X2, ported here): an
:class:`~ccf.erasure.ErasedContentRefused` reaching an MCP surface crossed as
raw exception prose naming the erased address, at every disclosure level —
``ToolError: Error executing tool get_replay_record: '<address>' was erased and
is not served (SEC-009)`` to a ``minimal`` principal. Its class is an
``ArtifactStoreError``, outside the egress tool's opaque ``ValueError /
TypeError / LookupError / OSError`` clause, and the Experience seams passed it
straight through. U11 (``ccf.products.refusal.ErasedContentRefusal``) says a
door renders the erasure only at ``reasoned`` and ``full``, and at ``minimal``
answers with its own not-found rendering — true at the HTTP doors and the MCP
artifact server only.

The ruled repair, held here surface by surface:

* the exception's text names no address (the address stays a structured
  attribute for in-process callers);
* a surface WITH a not-found rendering — the egress product tool and
  resource, the Experience product resource — records the ``erased-content``
  determination and discloses it: at ``minimal`` the same shell its typed
  absence answers, above it the ``erased-content`` shell;
* a surface WITHOUT one — the Experience ``get_context``, ``get_lineage`` and
  ``get_replay_record`` seams — answers ``minimal`` with the opaque
  ``ccf-runtime-failure:<id>`` and records nothing, and above it the recorded
  ``erased-content`` shell;
* a deployment directory's own failure on ``invoke_agent``, before
  authorization, is the existing opaque pre-authorization roster refusal.

In-process, offline: the shipped servers over scratch stores.
"""

from __future__ import annotations

import pathlib
import re
from datetime import UTC, datetime
from typing import Any

import anyio
import pytest
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
from mcp.server.auth.provider import AccessToken

from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.protocol import WriteKinds
from ccf.contracts.canonical import canonical_bytes
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.erasure import ErasedContentRefused, ErasureTrust, compose_erasure_consult
from ccf.erasure.index import ErasureIndexEntry, FileErasureIndex
from ccf.products.door import DoorOutcome, WireRequest
from ccf.products.refusal import RefusalEnvelope
from ccf_runtime.mcp.auth import TENANT_CLAIM
from tests.erasure.composed import _erase_capability
from tests.http_api.composition_authority import deployment_store, refusal_recorder
from tests.mcp.guarded_servers import (
    PRINCIPAL,
    PRODUCT_CLASS,
    REPLAY_RECORD_CLASS,
    SCOPE,
    TENANT,
    _auth,
    _entitlement_world,
    _perspective,
    _verifier,
    authorizer_granting,
)

#: The erased address, the record address and the child record address the
#: probes used — test data. Each must never reach a wire below ``full``.
ADDRESS = "ab" * 32
RECORD_ADDRESS = "cd" * 32
OPAQUE = re.compile(r"^(Error executing tool [^:\s]+: )?ccf-runtime-failure:[0-9a-f]{32}$")
VERSION = "1.0.0"


def _erased(**overrides: Any) -> ErasedContentRefused:
    fields: dict[str, Any] = dict(
        content_address=ADDRESS,
        erasure_record_address=RECORD_ADDRESS,
        reason="customer-request",
        erased_at=datetime(2026, 7, 30, tzinfo=UTC),
    )
    fields.update(overrides)
    return ErasedContentRefused(**fields)


def _raising(exc: BaseException) -> Any:
    def seam(**_: Any) -> Any:
        raise exc

    return seam


def _recorder(tmp_path: pathlib.Path, level: str | None) -> tuple[Any, Any]:
    """The entitlement world, with the disclosure level in force pinned when one is named."""
    source, recorder = _entitlement_world(tmp_path)
    if level is not None:
        recorder = refusal_recorder(
            ControlPlaneRegistry(),
            store=deployment_store(tmp_path / f"replay-{level}", REPLAY_RECORD_CLASS),
            tenant=TENANT,
            replay_record_class=REPLAY_RECORD_CLASS,
            disclosure_level_for=lambda *, tenant, principal_id: (level, None),
        )
    return source, recorder


def _as_caller(operation: Any) -> Any:
    reset = auth_context_var.set(
        AuthenticatedUser(
            AccessToken(token="in-process", client_id=PRINCIPAL, scopes=[SCOPE], claims={TENANT_CLAIM: [TENANT]})
        )
    )
    try:
        return operation()
    finally:
        auth_context_var.reset(reset)


def _no_disclosure(text: str) -> None:
    """Nothing of the erasure crosses: not the fact, not either address."""
    assert ADDRESS not in text and RECORD_ADDRESS not in text, text
    assert "erased" not in text.lower(), text
    assert "SEC-009" not in text, text


def _shell_without_reference(shell: RefusalEnvelope) -> bytes:
    """A shell up to the one member that must differ: the address of its own record."""
    return canonical_bytes(shell.model_copy(update={"replay_reference": ""}))


# --- the exception itself ------------------------------------------------------


def test_the_erasure_refusal_text_names_no_address_and_keeps_it_as_an_attribute() -> None:
    refused = _erased()
    assert ADDRESS not in str(refused) and RECORD_ADDRESS not in str(refused), str(refused)
    assert ADDRESS not in repr(refused) and RECORD_ADDRESS not in repr(refused), repr(refused)
    assert refused.content_address == ADDRESS
    assert refused.erasure_record_address == RECORD_ADDRESS


# --- X1: the Experience get_replay_record seam over an erasure-composed store ---


def _composed_store(tmp_path: pathlib.Path, registry: ControlPlaneRegistry) -> Any:
    """Probe X1's store: an index entry naming ADDRESS, composed through the SDK's own helper."""
    index = FileErasureIndex(tmp_path / "idx" / ".erasure-index.jsonl")
    index.append(
        _erase_capability(TENANT, "customer/r1"),
        ErasureIndexEntry(
            tenant_id=TENANT, content_address=ADDRESS, erasure_record_address=RECORD_ADDRESS,
            subject_class="customer", request_id="r1", subject_ref="ef" * 32, approval_ref="01" * 32,
            reason="customer-request", erased_at=datetime(2026, 7, 30, tzinfo=UTC),
            door_signature="x..y", door_key_id="door-1",
        ),
    )
    return compose_erasure_consult(
        FileArtifactStore(root=tmp_path / "store", write_kinds=WriteKinds.declare({})),
        index=index, audit_log=registry.audit_log, clock=lambda: datetime(2026, 8, 1, tzinfo=UTC),
        control_plane=registry, erasure_trust=ErasureTrust(authorities={}),
    )


def _experience(tmp_path: pathlib.Path, *, level: str | None, **seams: Any) -> Any:
    from ccf_runtime.mcp.experience import (
        ExperienceProductNotServable,
        GET_CONTEXT_TOOL,
        GET_LINEAGE_TOOL,
        GET_REPLAY_RECORD_TOOL,
        build_experience_server,
    )

    source, recorder = _recorder(tmp_path, level)
    arguments: dict[str, Any] = dict(
        server_name="fw3-experience",
        product_resolver=_raising(ExperienceProductNotServable("absent")),
        context_provider=_raising(_erased()),
        lineage_provider=_raising(_erased()),
        replay_record_reader=_raising(_erased()),
        get_context_description="fw3",
        get_lineage_description="fw3",
        get_replay_record_description="fw3",
        entitled_product_class=PRODUCT_CLASS,
        lineage_tenant=TENANT,
        replay_record_tenant=TENANT,
        replay_record_product_class=None,
        tool_allowlist=frozenset({GET_CONTEXT_TOOL, GET_LINEAGE_TOOL, GET_REPLAY_RECORD_TOOL}),
        token_verifier=_verifier(),
        auth_settings=_auth(),
        authorizer=authorizer_granting(),
        entitlement_source=source,
        perspective_resolver=_perspective,
        refusal_recorder=recorder,
    )
    arguments.update(seams)
    return build_experience_server(**arguments)


def _call(server: Any, tool: str, args: dict[str, Any]) -> tuple[str | None, BaseException | None]:
    try:
        result = _as_caller(lambda: anyio.run(server.call_tool, tool, args))
    except Exception as raised:  # noqa: BLE001 - the subject under test
        return None, raised
    if isinstance(result, tuple):
        result = result[0]
    return "".join(block.text for block in result if hasattr(block, "text")), None


def test_x1_get_replay_record_at_minimal_is_the_opaque_failure(tmp_path: pathlib.Path) -> None:
    """Probe X1, inverted: a deployment seam reading through the SDK-composed store."""
    from ccf_runtime.mcp.experience import GET_REPLAY_RECORD_TOOL

    registry = ControlPlaneRegistry()
    store = _composed_store(tmp_path, registry)

    def reader() -> str:  # the deployment's seam, reading the most recent record
        return store.scoped(TENANT).get(content_address=ADDRESS).decode("utf-8")

    server = _experience(tmp_path, level=None, replay_record_reader=reader)
    served, raised = _call(server, GET_REPLAY_RECORD_TOOL, {})
    assert served is None and raised is not None
    text = str(raised)
    _no_disclosure(text)
    assert OPAQUE.match(text), text


@pytest.mark.parametrize("tool", ["get_context", "get_lineage", "get_replay_record"])
def test_an_experience_seam_with_no_not_found_rendering_answers_minimal_opaquely(
    tool: str, tmp_path: pathlib.Path
) -> None:
    server = _experience(tmp_path, level=None)
    arguments = {"tenant": TENANT, "entity": "any"} if tool == "get_context" else {}
    served, raised = _call(server, tool, arguments)
    assert served is None and raised is not None, served
    _no_disclosure(str(raised))
    assert OPAQUE.match(str(raised)), str(raised)


@pytest.mark.parametrize("level", ["reasoned", "full"])
@pytest.mark.parametrize("tool", ["get_context", "get_lineage", "get_replay_record"])
def test_an_experience_seam_answers_the_erased_content_shell_above_minimal(
    tool: str, level: str, tmp_path: pathlib.Path
) -> None:
    server = _experience(tmp_path, level=level)
    arguments = {"tenant": TENANT, "entity": "any"} if tool == "get_context" else {}
    served, raised = _call(server, tool, arguments)
    assert raised is None, repr(raised)
    shell = RefusalEnvelope.model_validate_json(served or "")
    assert shell.kind == "erased-content" and shell.disclosure == level, shell
    assert ADDRESS not in (served or ""), "the erased address crossed in the shell"
    # The record address crosses at full only (INDISTINGUISHABLE_BELOW_FULL).
    assert (RECORD_ADDRESS in (served or "")) is (level == "full"), served


def _read(server: Any, uri: str) -> str:
    result = _as_caller(lambda: anyio.run(server.read_resource, uri))
    return "".join(contents.content for contents in result if isinstance(contents.content, str))


def test_the_experience_product_resource_answers_minimal_with_its_not_found_shell(
    tmp_path: pathlib.Path,
) -> None:
    from ccf_runtime.mcp.experience import experience_product_uri

    uri = experience_product_uri(tenant=TENANT, product_class=PRODUCT_CLASS, version=VERSION)
    # The absence leg: `_experience`'s default product resolver raises the typed absence.
    absent = _read(_experience(tmp_path / "absent", level=None), uri)
    erased = _read(_experience(tmp_path / "erased", level=None, product_resolver=_raising(_erased())), uri)
    _no_disclosure(erased)
    assert _shell_without_reference(RefusalEnvelope.model_validate_json(erased)) == _shell_without_reference(
        RefusalEnvelope.model_validate_json(absent)
    ), "the erasure is distinguishable from the surface's own not-found rendering"


def test_the_experience_product_resource_answers_erased_content_above_minimal(tmp_path: pathlib.Path) -> None:
    from ccf_runtime.mcp.experience import experience_product_uri

    uri = experience_product_uri(tenant=TENANT, product_class=PRODUCT_CLASS, version=VERSION)
    erased = _read(_experience(tmp_path, level="full", product_resolver=_raising(_erased())), uri)
    shell = RefusalEnvelope.model_validate_json(erased)
    assert shell.kind == "erased-content" and shell.disclosure == "full"


# --- X2: the egress product tool and resource ---------------------------------


def _egress(tmp_path: pathlib.Path, *, level: str | None, resolver: Any) -> Any:
    from ccf_runtime.mcp.egress import build_egress_server

    source, recorder = _recorder(tmp_path, level)
    return build_egress_server(
        server_name="fw3-egress", resolver=resolver, token_verifier=_verifier(), auth_settings=_auth(),
        authorizer=authorizer_granting(), entitlement_source=source,
        perspective_resolver=_perspective, refusal_recorder=recorder,
        expose_product_resource=True, expose_product_tool=True, product_tool_description="fw3",
    )


def _ask(server: Any) -> tuple[str | None, BaseException | None]:
    from ccf_runtime.mcp.egress import PRODUCT_REQUEST_TOOL

    return _call(
        server,
        PRODUCT_REQUEST_TOOL,
        {
            "tenant": TENANT, "product_class": PRODUCT_CLASS, "version": VERSION,
            "request": canonical_bytes(
                WireRequest(product_id=PRODUCT_CLASS, parameters={}, temporal_boundary=None)
            ).decode("utf-8"),
            "subject": "s", "intent": "i", "freshness": "f", "asked_at": "2026-05-12T00:00:00+00:00",
            "parameters": {},
        },
    )


def _refusal_of(text: str | None) -> RefusalEnvelope:
    outcome = DoorOutcome.model_validate_json(text or "")
    assert outcome.refusal is not None, outcome
    return outcome.refusal


def test_x2_the_egress_tool_answers_minimal_with_its_not_found_shell(tmp_path: pathlib.Path) -> None:
    """Probe X2, inverted: an erasure raised inside the resolver (the disclosed M4 propagation)."""
    from ccf_runtime.mcp.egress import ProductNotServable

    erased_text, raised = _ask(_egress(tmp_path / "erased", level=None, resolver=_raising(_erased())))
    assert raised is None, f"the erasure crossed as a tool error: {raised!r}"
    _no_disclosure(erased_text or "")
    absent_text, absent_raised = _ask(
        _egress(tmp_path / "absent", level=None, resolver=_raising(ProductNotServable("absent")))
    )
    assert absent_raised is None, repr(absent_raised)
    assert _shell_without_reference(_refusal_of(erased_text)) == _shell_without_reference(
        _refusal_of(absent_text)
    ), "the erasure is distinguishable from the tool's own not-found rendering"


@pytest.mark.parametrize("level", ["reasoned", "full"])
def test_the_egress_tool_answers_erased_content_above_minimal(level: str, tmp_path: pathlib.Path) -> None:
    text, raised = _ask(_egress(tmp_path, level=level, resolver=_raising(_erased())))
    assert raised is None, repr(raised)
    shell = _refusal_of(text)
    assert shell.kind == "erased-content" and shell.disclosure == level, shell
    assert (RECORD_ADDRESS in (text or "")) is (level == "full"), text


def test_the_egress_resource_answers_minimal_with_its_not_found_shell(tmp_path: pathlib.Path) -> None:
    from ccf_runtime.mcp.egress import ProductNotServable, product_uri

    uri = product_uri(tenant=TENANT, product_class=PRODUCT_CLASS, version=VERSION)
    erased = _read(_egress(tmp_path / "erased", level=None, resolver=_raising(_erased())), uri)
    _no_disclosure(erased)
    absent = _read(_egress(tmp_path / "absent", level=None, resolver=_raising(ProductNotServable("absent"))), uri)
    assert _shell_without_reference(RefusalEnvelope.model_validate_json(erased)) == _shell_without_reference(
        RefusalEnvelope.model_validate_json(absent)
    )


def test_the_egress_resource_answers_erased_content_above_minimal(tmp_path: pathlib.Path) -> None:
    from ccf_runtime.mcp.egress import product_uri

    uri = product_uri(tenant=TENANT, product_class=PRODUCT_CLASS, version=VERSION)
    shell = RefusalEnvelope.model_validate_json(
        _read(_egress(tmp_path, level="full", resolver=_raising(_erased())), uri)
    )
    assert shell.kind == "erased-content" and shell.disclosure == "full"


# --- invoke_agent: a deployment directory's failure before authorization -------


def test_a_directory_failure_on_invoke_agent_is_the_opaque_pre_authorization_refusal(
    tmp_path: pathlib.Path, caplog: Any
) -> None:
    from ccf_runtime.mcp.experience import INVOKE_AGENT_TOOL, build_experience_server
    from tests.mcp.test_product_roster import OPAQUE as ROSTER_OPAQUE
    from tests.mcp.test_product_roster import _as_caller as rostered, _underlying

    caplog.set_level("INFO", logger="ccf_runtime.mcp.tenancy")
    secret = "directory-prose-naming-agent-secret-and-class-secret"

    def directory(*, tenant: str) -> Any:
        raise RuntimeError(secret)

    invoked: list[str] = []
    source, recorder = _entitlement_world(tmp_path)
    server = build_experience_server(
        server_name="fw3-directory", product_resolver=lambda **kw: None,
        agent_directory=directory, agent_invoker=lambda **kw: invoked.append("x") or "{}",
        invoke_agent_description="fw3", tool_allowlist=frozenset({INVOKE_AGENT_TOOL}),
        token_verifier=_verifier(), auth_settings=_auth(), authorizer=authorizer_granting(),
        entitlement_source=source, perspective_resolver=_perspective, refusal_recorder=recorder,
    )
    reset = rostered(frozenset({PRODUCT_CLASS}))
    try:
        with pytest.raises(Exception) as raised:
            anyio.run(
                server.call_tool,
                INVOKE_AGENT_TOOL,
                {"tenant": TENANT, "definition_key": "agent-x", "definition_version": "1.0.0", "skill": "s", "arguments": {}},
            )
    finally:
        auth_context_var.reset(reset)
    assert secret not in str(raised.value), str(raised.value)
    refusal = _underlying(raised.value)
    assert type(refusal).__name__ == "ProductOutsideRosterRefused", repr(raised.value)
    assert ROSTER_OPAQUE in str(refusal)
    assert invoked == []
    # The log names the failure's type, never its text (SEC-024).
    assert "RuntimeError" in "\n".join(record.getMessage() for record in caplog.records)
    assert secret not in "\n".join(record.getMessage() for record in caplog.records)


def test_the_experience_door_states_the_egress_failure_token() -> None:
    """The role-separation invariant keeps the two doors from importing each other; this holds the token equal."""
    from ccf_runtime.mcp import egress, experience

    assert experience._RUNTIME_FAILURE_PREFIX == egress.CCF_FAILURE_PREFIX
