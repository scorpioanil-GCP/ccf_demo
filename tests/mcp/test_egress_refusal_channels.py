"""Every governed answer leaves the MCP door as a governed answer.

``D-IMPL-253`` D-19 and D-20 as amended by ``D-IMPL-256`` (Dave, 2026-09-04);
ledger row ``24.6-L-03``. Three rulings meet in this module and they are one
change, because they need the same one:

* **The standing resource gets the refusal channel it never had** (D-19). Its
  body was ``canonical_bytes(servable.product)`` over whatever the resolver
  returned, so a returned :class:`~ccf.products.refusal.RefusalEnvelope` was an
  ``AttributeError`` reaching a client as a resource error indistinguishable
  from *not found*. Dave: **not-found would destroy the distinction and
  replayability**.
* **No governed determination reaches a client as a tool error** (D-20). An
  entitlement denial is a governed determination — one the fabric genuinely
  made — and it leaves as the suppression-safe ``subject-unavailable`` shell at
  the principal's disclosure level. ``ToolError`` is reserved for CCF's own
  failure and carries an opaque id.
* **A door that cannot record is not built** (``D-IMPL-256`` (2)):
  *"a door configured to make governed determinations without the ability to
  record them is not a valid governed door."*

**What this module measures, and at what strength.** The unit under test is
what a **real, authenticated door** puts on a real MCP wire, read the way a
client reads it: the resource through ``read_resource``, the tool through
``call_tool``. Three legs are source-level and say so — the two sabotages and
the transport-neutrality walk — because their subject is the *shape of the
module* rather than an answer, and each carries a planted control so it cannot
pass against a walk that sees nothing.

**The MCP door of D-20 at this plan is the EGRESS door.**
``runtime/ccf_runtime/mcp/experience.py``'s three entitling paths are plan
``24.6-16``'s, in this same wave, and nothing here touches them.

Tenant, principal, role, class, scope and token names are test deployment
vocabulary. The SDK holds none of them (CINV-01).
"""

from __future__ import annotations

import ast
import asyncio
import importlib.util
import json
import re
import sys
import types
from collections.abc import Awaitable, Callable, Mapping
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
import pytest
from mcp.client.session import ClientSession
from mcp.server.auth.settings import AuthSettings
from mcp.types import TextContent, TextResourceContents
from pydantic import AnyHttpUrl, AnyUrl

from ccf.artifacts.file_store import FileArtifactStore
from ccf.contracts.canonical import canonical_bytes
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.mcp.client import run_with_session
from ccf.mcp.errors import McpServerUnreachable
from ccf.products.constraints import ConstraintRefusal
from ccf.products.disclosure import WITHHELD
from ccf.products.door import DoorOutcome, WireRequest
from ccf.products.entitlement import (
    PRODUCT_ENTITLEMENT_POLICY,
    ProductEntitlementGrant,
    ProductEntitlementPolicy,
    product_entitlement_key,
)
from ccf.products.gates import ToleranceExceededRefusal
from ccf.products.provenance import ParameterBound, ProvenanceSource
from ccf.products.refusal import (
    NO_REPLAY_REFERENCE,
    REFUSAL_KINDS,
    RefusalEnvelope,
    RequestIdentity,
    SubjectUnavailableRefusal,
    envelope_for,
)
from ccf.products.request import ProductRequest
from ccf.products.resolver import ReplayRefusalRecorder
from ccf.projection.plan import Perspective
from ccf.replay.record import (
    NO_ROLE_RESOLVED,
    DecisionReplayRecord,
    ResolutionNotApplicable,
)
from ccf_runtime.authz.delivery_boundary import UnrecordableDeliveryBoundaryError
from ccf_runtime.authz.product_entitlement import (
    ControlPlaneProductEntitlementSource,
)
from ccf_runtime.http_api.errors import ERROR_PRODUCT_CLASS_UNENTITLED
from ccf_runtime.mcp.auth import FileTokenSource, SourceBackedTokenVerifier
from ccf_runtime.mcp.egress import (
    product_address,
    CCF_FAILURE_PREFIX,
    PRODUCT_REQUEST_TOOL,
    build_egress_server,
    product_uri,
)
from tests.mcp.guarded_servers import wide_authorizer

from ccf_runtime.mcp.egress import ProductNotServable
from crossproc.servers.mcp_egress_child import ProductAddress, build_servable_product
from ccf.controlplane.registry import ControlPlaneRegistry
from http_api.composition_authority import (
    deployment_store,
    refusal_recorder,
    register_typed_at_composition,
)

#: Test deployment vocabulary; the SDK ships none of it.
TOKEN = "egress-channels-token"
PRINCIPAL = "egress-channels-caller"
SCOPE = "ccf:egress-channels"
ROLE = "egress-channels-role"
SERVER_NAME = "ccf-egress-channels"
POLICY_VERSION = "1.0.0"
TOOL_DESCRIPTION = "Ask this test deployment's product class a question."
REPLAY_ARTIFACT_CLASS = "egress-channels-replay-record"

#: The class this caller is granted nothing for, so an entitlement denial is
#: reachable by ASKING rather than by hand-building a verdict.
UNENTITLED = "a-class-this-caller-was-never-granted"

#: The four §6.3 axes the tool carries, held constant.
SUBJECT = "egress-channels-subject"
INTENT = "egress-channels-intent"
FRESHNESS = "egress-channels-freshness"
ASKED_AT = datetime(2026, 9, 5, 9, 30, tzinfo=UTC)

#: The ONE instant every determination below is reached at. Pinned on the
#: entitlement source, because the whole subject of the record assertions is
#: that the shell and its record read the same clock — a wall-clock read would
#: make `recorded_at == determined_at` true by luck rather than by mechanism.
DETERMINED_AT = datetime(2026, 9, 5, 11, 15, tzinfo=UTC)

#: Loopback with an explicit port: FastMCP's DNS-rebinding protection allows
#: ``127.0.0.1:*`` even over ASGI, where no socket exists. Nothing binds it.
IN_PROCESS_BASE_URL = "http://127.0.0.1:8129"

EGRESS_PATH = Path(
    __file__
).resolve().parents[2] / "runtime" / "ccf_runtime" / "mcp" / "egress.py"
EGRESS_SOURCE = EGRESS_PATH.read_bytes()


# ---------------------------------------------------------------------------
# The world: one real door, one real store, one pinned clock.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def assembled(tmp_path_factory: pytest.TempPathFactory) -> Any:
    """One assembled, gate-admitted product, reused by every door below."""
    return build_servable_product(
        database_path=tmp_path_factory.mktemp("egress-channels") / "door.sqlite3"
    )


def _token_file(root: Path, *, tenant: str) -> Path:
    """The door's token file, whose one credential is scoped to ``tenant``.

    ``tenant`` is required rather than defaulted (``SEC-018``): a credential
    that names no tenant reaches nothing, so a fixture that forgot it would
    fail loudly instead of quietly minting the unscoped bearer this finding is
    about.
    """
    path = root / "egress-channels-tokens.json"
    path.write_text(
        json.dumps(
            {
                TOKEN: {
                    "client_id": PRINCIPAL,
                    "scopes": [SCOPE],
                    "tenants": [tenant],
                }
            }
        ),
        encoding="utf-8",
    )
    return path


class _World:
    """A booted egress door with its entitlement source, store and recorder.

    The recorder is built with the keyword list
    :func:`~ccf.products.resolver.build_governed_resolver` uses for its own and
    reads its disclosure posture off the **same** entitlement source the door
    entitles through, so the door's denial and a resolver's refusal disclose
    under one reading of one policy.
    """

    def __init__(
        self,
        root: Path,
        *,
        address: ProductAddress,
        resolver: Callable[..., object],
        expose_product_resource: bool = True,
    ) -> None:
        self.address = address
        self.registry = ControlPlaneRegistry()
        register_typed_at_composition(self.registry, 
            product_entitlement_key(tenant_id=address.tenant),
            ProductEntitlementPolicy(
                tenant_id=address.tenant,
                policy_version=POLICY_VERSION,
                principals={
                    PRINCIPAL: ProductEntitlementGrant(
                        permitted_schema_names=frozenset({address.product_class}),
                        permitted_roles=frozenset({ROLE}),
                    )
                },
            ),
            PRODUCT_ENTITLEMENT_POLICY,
        )
        self.source = ControlPlaneProductEntitlementSource(
            control_plane=self.registry, clock=lambda: DETERMINED_AT
        )
        self.store = deployment_store(root / "artifacts", REPLAY_ARTIFACT_CLASS)
        self.recorder = refusal_recorder(
            self.registry,
            store=self.store,
            tenant=address.tenant,
            replay_record_class=REPLAY_ARTIFACT_CLASS,
            assembly_mode="algorithmic",
            disclosure_level_for=self.source.disclosure_level_for,
        )
        self.server = build_egress_server(
            server_name=SERVER_NAME,
            resolver=resolver,  # type: ignore[arg-type]
            token_verifier=SourceBackedTokenVerifier(
                source=FileTokenSource(path=_token_file(root, tenant=address.tenant))
            ),
            auth_settings=AuthSettings(
                issuer_url=AnyHttpUrl("https://issuer.invalid"),
                resource_server_url=AnyHttpUrl(f"{IN_PROCESS_BASE_URL}/mcp"),
                required_scopes=[SCOPE],
            ),
            authorizer=wide_authorizer(scopes=(SCOPE,)),
            entitlement_source=self.source,
            perspective_resolver=(
                lambda *, grant, tenant, requested_role: Perspective(
                    principal_id=grant.client_id, role=ROLE
                )
            ),
            refusal_recorder=self.recorder,
            expose_product_resource=expose_product_resource,
            expose_product_tool=True,
            product_tool_description=TOOL_DESCRIPTION,
        )

    def record_at(self, uri: str) -> DecisionReplayRecord:
        """Resolve one replay record out of the store the door wrote to."""
        return DecisionReplayRecord.model_validate_json(
            self.store.get(content_address=self.store.resolve_uri(uri=uri))
        )

    def internal(self, record: DecisionReplayRecord) -> RefusalEnvelope:
        """Dimension 5's determination as the fabric reached it, un-disclosed."""
        return RefusalEnvelope.model_validate_json(
            record.content_generation_path.assembly_refusal
        )

    def stored(self) -> set[str]:
        """Every content address in the store, so growth is measured."""
        root = self.store.root
        return (
            {path.name for path in root.iterdir() if len(path.name) == 64}
            if root.exists()
            else set()
        )


def _answering(outcome: object) -> Callable[..., object]:
    """A deployment resolver that answers every call with ``outcome``."""

    def resolve(
        *,
        tenant: str,
        product_class: str,
        version: str,
        perspective: Perspective,
        request: ProductRequest | None,
    ) -> object:
        return outcome

    return resolve


def _raising(exc: BaseException) -> Callable[..., object]:
    """A deployment resolver whose assembly path FAILS rather than refuses."""

    def resolve(
        *,
        tenant: str,
        product_class: str,
        version: str,
        perspective: Perspective,
        request: ProductRequest | None,
    ) -> object:
        raise exc

    return resolve


# ---------------------------------------------------------------------------
# The drivers: a real client session over the door's own ASGI app.
# ---------------------------------------------------------------------------


def _drive(
    server: Any,
    operation: Callable[[ClientSession], Awaitable[tuple[bool, str]]],
    *,
    token: str | None = TOKEN,
) -> tuple[bool, str]:
    app = server.streamable_http_app()

    async def go() -> tuple[bool, str]:
        async with app.router.lifespan_context(app):

            def factory() -> httpx.AsyncClient:
                headers = (
                    {"Authorization": f"Bearer {token}"} if token is not None else {}
                )
                return httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app),
                    base_url=IN_PROCESS_BASE_URL,
                    headers=headers,
                )

            try:
                return await run_with_session(
                    url=f"{IN_PROCESS_BASE_URL}/mcp",
                    operation=operation,
                    http_client_factory=factory,
                )
            except McpServerUnreachable as refused:
                return True, str(refused)

    return asyncio.run(go())


def _resource_operation(
    uri: str,
) -> Callable[[ClientSession], Awaitable[tuple[bool, str]]]:
    """Read the standing resource; return ``(refused, text)``.

    The shape is copied from ``tests/examples/test_cp_04_two_callers.py``'s
    ``resource_read`` rather than imported: a test package importing another
    test package's driver would couple two suites that answer different
    questions.
    """

    async def operation(session: ClientSession) -> tuple[bool, str]:
        result = await session.read_resource(AnyUrl(uri))
        return False, "".join(
            contents.text
            for contents in result.contents
            if isinstance(contents, TextResourceContents)
        )

    return operation


def _tool_operation(
    arguments: Mapping[str, Any],
) -> Callable[[ClientSession], Awaitable[tuple[bool, str]]]:
    async def operation(session: ClientSession) -> tuple[bool, str]:
        result = await session.call_tool(PRODUCT_REQUEST_TOOL, dict(arguments))
        return bool(result.isError), " | ".join(
            content.text
            for content in result.content
            if isinstance(content, TextContent)
        )

    return operation


def _tool_arguments(address: ProductAddress) -> dict[str, Any]:
    return {
        "tenant": address.tenant,
        "product_class": address.product_class,
        "version": address.version,
        "request": canonical_bytes(
            WireRequest(
                product_id=address.product_class,
                parameters={},
                temporal_boundary=None,
            )
        ).decode("utf-8"),
        "subject": SUBJECT,
        "intent": INTENT,
        "freshness": FRESHNESS,
        "asked_at": ASKED_AT.isoformat(),
    }


def _read_resource(world: _World, *, address: ProductAddress | None = None) -> str:
    """The standing resource's body, as text."""
    at = world.address if address is None else address
    _refused, text = _drive(world.server, _resource_operation(at.uri))
    return text


def _call_tool(world: _World, *, address: ProductAddress | None = None) -> tuple[bool, str]:
    at = world.address if address is None else address
    return _drive(world.server, _tool_operation(_tool_arguments(at)))


def _decode(text: str) -> DoorOutcome:
    """What a client does with the tool's text — validate it, never sniff it."""
    return DoorOutcome.model_validate_json(text)


def _identity(address: ProductAddress) -> RequestIdentity:
    """The identity a QUESTION-LESS surface states for itself."""
    return RequestIdentity(
        product_id=address.product_class,
        product_version=address.version,
        parameters={},
        temporal_boundary=None,
    )


# ---------------------------------------------------------------------------
# (1) The standing resource's body is the shell (D-19, C-24).
# ---------------------------------------------------------------------------


def _refusal_of(kind: str, address: ProductAddress) -> RefusalEnvelope:
    """One real refusal value of ``kind``, enveloped with this surface's identity.

    Real values rather than a hand-built envelope: the kind token comes off
    :data:`~ccf.products.refusal.REFUSAL_KINDS` by lookup, so a renamed kind
    fails here rather than silently testing a string nothing produces.
    """
    if kind == REFUSAL_KINDS[ConstraintRefusal]:
        value: Any = ConstraintRefusal(
            reason="bound-exceeded",
            key="max_depth",
            detail="the requested bound is above what this deployment declares",
            bound=ParameterBound(
                operator="<=",
                value=6,
                authority="policy",
                source=ProvenanceSource(
                    kind="artifact", identity="test/bounds", version="1.0.0"
                ),
            ),
            requested=9,
        )
    elif kind == REFUSAL_KINDS[SubjectUnavailableRefusal]:
        value = SubjectUnavailableRefusal(
            cause="nonexistent", detail="no such subject in this fabric"
        )
    elif kind == REFUSAL_KINDS[ToleranceExceededRefusal]:
        value = ToleranceExceededRefusal(
            authority="policy",
            source=ProvenanceSource(
                kind="artifact", identity="test/tolerance", version="1.0.0"
            ),
            tolerance=Decimal("0.20"),
            observed=Decimal("0.55"),
            breakdown=None,
            detail="measured debt exceeded the declared tolerance",
        )
    else:  # pragma: no cover - the parametrization below is closed
        raise AssertionError(f"no real value declared for kind {kind!r}")
    return envelope_for(value, request=_identity(address))


@pytest.mark.parametrize(
    "kind",
    [
        REFUSAL_KINDS[ConstraintRefusal],
        REFUSAL_KINDS[SubjectUnavailableRefusal],
        REFUSAL_KINDS[ToleranceExceededRefusal],
    ],
)
def test_the_standing_resource_body_is_the_shell_per_kind_class(
    kind: str, assembled: Any, tmp_path: Path
) -> None:
    """D-19: the resource answers a governed "no" WITH the governed "no".

    Three kind classes, because the resource's channel must not be special to
    one: a constraint verdict, the shared subject outcome, and a gate's
    tolerance refusal. Each is a real value of its own type, enveloped, and the
    body decodes as that envelope — never as a resource error, never as the
    ``AttributeError`` on ``.product`` this handler raised before this row.

    What would fail here: a resource that answered *not found*, which would
    make **you may not**, **there is no such thing** and **this refusal has a
    record** one indistinguishable non-answer.

    **The refusal source here is a deployment-resolver STUB, by construction,
    and that is named rather than hidden.** No shipped resolver answers the
    standing resource with a refusal ENVELOPE:
    :class:`~ccf.products.resolver.GovernedResolver` raises
    ``ProductNotResolvable`` on ``request=None`` and cp-04's ``compose.py``
    raises ``ProductNotServable``. The door's OWN denial on this same path is
    real and recorded, and is asserted below.
    """
    # Minted through the door's OWN recorder, lazily — `D-IMPL-260` P-A: a
    # door releases only what `ReplayRefusalRecorder.record` returned, and the
    # recorder exists once the world does.
    held: dict[str, _World] = {}

    def resolve(**_: Any) -> object:
        return held["world"].recorder.record(
            _refusal_of(kind, assembled.address),
            perspective=Perspective(principal_id=PRINCIPAL, role=ROLE),
            recorded_at=DETERMINED_AT,
            served_at=DETERMINED_AT,
            resolution=ResolutionNotApplicable(reason="no-resolution-step"),
        )

    world = _World(tmp_path, address=assembled.address, resolver=resolve)
    held["world"] = world

    body = _read_resource(world)

    shell = RefusalEnvelope.model_validate_json(body)
    assert shell.kind == kind
    assert shell.request.parameters == {}
    assert shell.request.temporal_boundary is None
    assert shell.replay_reference != NO_REPLAY_REFERENCE


def test_an_absent_class_reaches_the_caller_as_the_common_shell_on_both_surfaces(
    assembled: Any, tmp_path: Path
) -> None:
    """``D-IMPL-260`` P-C at the egress door, tool and resource alike.

    The resolver's ``ProductNotServable`` — the typed absence of a servable
    product at an address the caller was entitled to — was an opaque runtime
    failure on the tool and a transport error on the resource. It is a
    governed determination now: the common ``subject-unavailable`` shell,
    recorded and disclosed at the boundary, with the resolver's statement on
    the record and off the wire.
    """
    absent = _raising(ProductNotServable("no gate-admitted product there"))
    # One world per surface: a session manager runs once per instance.
    world = _World(tmp_path / "tool", address=assembled.address, resolver=absent)

    is_error, text = _call_tool(world)
    assert not is_error, text
    outcome = _decode(text)
    assert outcome.refusal is not None
    assert outcome.refusal.kind == "subject-unavailable"
    assert outcome.refusal.disclosure == "minimal"
    assert outcome.replay_ref == outcome.refusal.replay_reference != NO_REPLAY_REFERENCE
    assert "no gate-admitted product" not in text
    assert "ProductNotServable" not in text
    record = world.record_at(outcome.refusal.replay_reference)
    internal = world.internal(record)
    assert json.loads(internal.fields["cause"]) == "nonexistent"
    assert "no gate-admitted product there" in internal.detail
    assert internal.resource is not None and internal.resource.surface == "mcp-tool"
    assert record.perspective_conditioning.role == ROLE
    assert record.policy_bindings.bindings == ()

    world = _World(tmp_path / "resource", address=assembled.address, resolver=absent)
    body = _read_resource(world)
    shell = RefusalEnvelope.model_validate_json(body)
    assert shell.kind == "subject-unavailable"
    assert shell.replay_reference != NO_REPLAY_REFERENCE
    assert "no gate-admitted product" not in body
    resource_internal = world.internal(world.record_at(shell.replay_reference))
    assert resource_internal.resource is not None
    assert resource_internal.resource.surface == "mcp-resource"


def test_the_standing_resource_serves_the_vessel_when_the_resolver_serves(
    assembled: Any, tmp_path: Path
) -> None:
    """The vacuity guard for the three legs above.

    Without it, a resource that returned the shell for *every* read — served or
    refused — would pass all three. The two shapes share a ``mime_type`` and
    are told apart by the top-level ``kind`` key, so this asserts the served
    body is byte-identical to the vessel's canonical bytes and carries no
    ``kind`` at all.
    """
    world = _World(
        tmp_path, address=assembled.address, resolver=_answering(assembled.served)
    )

    body = _read_resource(world)

    assert body == canonical_bytes(assembled.servable.product).decode("utf-8")
    assert "kind" not in json.loads(body)


def test_a_bare_refusal_value_does_not_cross_the_resource(
    assembled: Any, tmp_path: Path
) -> None:
    """``D-IMPL-260`` P-A, on the standing resource: a bare value is a wiring defect.

    ``24.6-10`` taught the door to state this surface's own identity for a
    bare refusal value, so the resource had a refusal channel at all. That
    translation released an envelope nothing had recorded or disclosed, and
    the ruling ends it: a resolver holding a bare value records it through
    the SDK's recorder — whose request identity is what a question-less
    surface states for itself — and returns the shell. The bare value is
    refused at the door and the read fails as a transport error, never as a
    shell the fabric minted.
    """
    world = _World(
        tmp_path,
        address=assembled.address,
        resolver=_answering(
            SubjectUnavailableRefusal(
                cause="nonexistent", detail="no such subject in this fabric"
            )
        ),
    )

    refused, text = _drive(world.server, _resource_operation(world.address.uri))

    assert refused is True, text
    assert "no such subject in this fabric" not in text
    # And nothing was minted on the way out: the door records nothing itself.
    root = world.store.root
    assert not root.exists() or not any(len(p.name) == 64 for p in root.iterdir())


# ---------------------------------------------------------------------------
# (2) Entitlement on the TOOL path: shelled, recorded, resolvable (D-20, C-25).
# ---------------------------------------------------------------------------


def _unentitled(address: ProductAddress) -> ProductAddress:
    """The same door, addressed at a class this caller was granted nothing for."""
    return ProductAddress(
        tenant=address.tenant, product_class=UNENTITLED, version=address.version
    )


def test_an_entitlement_denial_on_the_tool_path_is_a_recorded_shell(
    assembled: Any, tmp_path: Path
) -> None:
    """D-20 and ``D-IMPL-256`` (1) at the tool: a governed answer with a record.

    Six things are asserted and each fails differently: the call is not an
    error; the outcome carries a refusal and no vessel; the kind is the SHARED
    outcome; the internal cause did not cross at ``minimal``; the reference is
    non-sentinel and is the one the outcome reports; and the record it resolves
    to says *what resource, by whom, at what instant, and why*.

    What would fail here: a denial that reached the client as ``ToolError``
    prose (the ``24.5`` shape), and — separately — a denial that produced a
    perfectly well-formed shell with nothing behind it, which is Q13's *silent
    second class* and is what a sentinel reference looks like.
    """
    world = _World(
        tmp_path, address=assembled.address, resolver=_answering(assembled.served)
    )
    at = _unentitled(assembled.address)

    is_error, text = _call_tool(world, address=at)

    assert is_error is False, text
    outcome = _decode(text)
    assert outcome.product_json is None
    assert outcome.content_address is None
    assert outcome.refusal is not None
    shell = outcome.refusal
    assert shell.kind == REFUSAL_KINDS[SubjectUnavailableRefusal]
    assert json.loads(shell.fields["cause"]) == WITHHELD
    assert shell.replay_reference != NO_REPLAY_REFERENCE
    assert outcome.replay_ref == shell.replay_reference

    record = world.record_at(shell.replay_reference)
    internal = world.internal(record)
    assert json.loads(internal.fields["cause"]) == "unauthorized"
    assert record.perspective_conditioning.principal_id == PRINCIPAL
    # Dimension 4 is the role the source DECIDED under — this door's resolver
    # conditions every caller under `ROLE` — not the positive-absence claim
    # (`D-IMPL-260` P-D).
    assert record.perspective_conditioning.role == ROLE
    # `D-IMPL-358` step 5 section F. MIGRATED, not deleted: this asserted
    # `DETERMINED_AT` and was pinning the defect — a refusal to a question asked
    # at 09:30 recorded its dimension-1 boundary at the door's 11:15 clock. The
    # two instants are now two statements and both are asserted, which is what a
    # one-sided version of this could never have caught.
    assert record.recorded_at == ASKED_AT
    assert record.content_generation_path.served_at == DETERMINED_AT
    assert internal.resource is not None
    assert internal.resource.surface == "mcp-tool"
    assert internal.resource.address == product_uri(
        tenant=at.tenant, product_class=at.product_class, version=at.version
    )
    assert internal.resource.determined_at == DETERMINED_AT


# ---------------------------------------------------------------------------
# (3) Entitlement on the RESOURCE path — the D-34 case, real and recorded.
# ---------------------------------------------------------------------------


def test_an_entitlement_denial_on_the_resource_path_is_a_recorded_shell(
    assembled: Any, tmp_path: Path
) -> None:
    """``D-IMPL-256`` (1), D-34: *no fulfilled product does not mean no replay*.

    Dave, on what a standing resource's denial must still answer: *"what
    resource was requested, by whom/perspective, at what instant, under which
    policy, and why fulfillment was refused."* All five, off the record this
    read produced — and the store is measured as having **grown by one**, so
    the record is this call's rather than one that happened to be lying there.

    What would fail here: *"a replay hole based on transport shape"* — a
    resource denial recorded thinner than a tool denial, or not at all.
    """
    world = _World(
        tmp_path, address=assembled.address, resolver=_answering(assembled.served)
    )
    at = _unentitled(assembled.address)
    before = world.stored()

    shell = RefusalEnvelope.model_validate_json(_read_resource(world, address=at))

    assert shell.kind == REFUSAL_KINDS[SubjectUnavailableRefusal]
    assert json.loads(shell.fields["cause"]) == WITHHELD
    assert shell.replay_reference != NO_REPLAY_REFERENCE
    assert len(world.stored() - before) == 1

    record = world.record_at(shell.replay_reference)
    internal = world.internal(record)
    # (1) what resource, (2) at what instant.
    assert internal.resource is not None
    assert internal.resource.surface == "mcp-resource"
    assert internal.resource.address == product_uri(
        tenant=at.tenant, product_class=at.product_class, version=at.version
    )
    assert internal.resource.determined_at == DETERMINED_AT == record.recorded_at
    # The resource poses no question, and its identity says exactly that.
    assert internal.request.temporal_boundary is None
    assert internal.request.parameters == {}
    # (3) by whom — dimension 4, under the role the source decided against
    # (`D-IMPL-260` P-D).
    assert record.perspective_conditioning.principal_id == PRINCIPAL
    assert record.perspective_conditioning.role == ROLE
    # (4) under which policy — dimension 2.
    assert record.policy_bindings.bindings != ()
    # (5) why — dimension 5's internal determination.
    assert json.loads(internal.fields["cause"]) == "unauthorized"


def test_an_entitlement_denial_on_the_address_surface_records_that_address(
    assembled: Any, tmp_path: Path
) -> None:
    """The ``/q/`` address is a resource of its own, and its denial says so.

    ``24.5-L-08`` gave the tool's question an address, and the address answers
    through the tool's own body. **Phase 24.6 close panel:** that one body
    stamped every denial ``mcp-tool`` at the standing product URI, so a caller
    who read ``…/q/<question>`` and was refused had the refusal recorded
    against a surface they never used and an address they never read —
    criterion 24's *what resource* answered falsely. The tool's own denial
    keeps its identity (asserted beside this, above); this one records the
    address surface and the address itself.
    """
    world = _World(
        tmp_path, address=assembled.address, resolver=_answering(assembled.served)
    )
    at = _unentitled(assembled.address)
    uri = product_address(
        tenant=at.tenant,
        product_class=at.product_class,
        version=at.version,
        question=WireRequest(
            product_id=at.product_class, parameters={}, temporal_boundary=None
        ),
        subject=SUBJECT,
        intent=INTENT,
        freshness=FRESHNESS,
        asked_at=ASKED_AT,
    )
    assert "/q/" in uri
    before = world.stored()

    _refused, text = _drive(world.server, _resource_operation(uri))

    outcome = _decode(text)
    assert outcome.product_json is None
    assert outcome.refusal is not None
    shell = outcome.refusal
    assert shell.kind == REFUSAL_KINDS[SubjectUnavailableRefusal]
    assert shell.replay_reference != NO_REPLAY_REFERENCE
    assert len(world.stored() - before) == 1

    record = world.record_at(shell.replay_reference)
    internal = world.internal(record)
    assert internal.resource is not None
    assert internal.resource.surface == "mcp-resource", internal.resource
    assert internal.resource.address == uri, internal.resource
    assert internal.resource.address != product_uri(
        tenant=at.tenant, product_class=at.product_class, version=at.version
    )
    # `D-IMPL-358` step 5 section F. The chain is SPLIT because the two halves
    # stopped being the same fact: the resource still carries the instant the
    # determination was reached, while the record's boundary is the question's.
    # Chaining them read as one claim and was really two, which is why the
    # migration is a split rather than a re-pin.
    assert internal.resource.determined_at == DETERMINED_AT
    assert record.recorded_at == ASKED_AT
    assert record.content_generation_path.served_at == DETERMINED_AT


def test_the_two_resource_shells_are_both_minted_through_the_one_recorder(
    assembled: Any, tmp_path: Path
) -> None:
    """The door's denial and a nonexistent subject, side by side on one path.

    The unauthorized shell is the door's own, minted by the governed step at
    the determination instant. The nonexistent shell comes from a deployment
    resolver that returns ``refusal_recorder.record(...)`` over the **same**
    recorder — the real minting path, because no shipped resolver refuses on
    this surface with an envelope at all (see the parametrized legs above).
    Both references resolve; their internal causes differ; and that difference
    lives only in the record.
    """
    world = _World(
        tmp_path, address=assembled.address, resolver=_answering(assembled.served)
    )
    unauthorized = RefusalEnvelope.model_validate_json(
        _read_resource(world, address=_unentitled(assembled.address))
    )

    nonexistent_world = _World(
        tmp_path / "nonexistent",
        address=assembled.address,
        resolver=_answering(None),
    )
    minted = nonexistent_world.recorder.record(
        envelope_for(
            SubjectUnavailableRefusal(
                cause="nonexistent", detail="no such subject in this fabric"
            ),
            request=_identity(assembled.address),
        ),
        perspective=Perspective(principal_id=PRINCIPAL, role=NO_ROLE_RESOLVED),
        recorded_at=DETERMINED_AT,
        served_at=DETERMINED_AT,
        resolution=ResolutionNotApplicable(reason="no-resolution-step"),
    )
    nonexistent_world = _World(
        tmp_path / "nonexistent",
        address=assembled.address,
        resolver=_answering(minted),
    )
    nonexistent = RefusalEnvelope.model_validate_json(_read_resource(nonexistent_world))

    assert unauthorized.replay_reference != NO_REPLAY_REFERENCE
    assert nonexistent.replay_reference != NO_REPLAY_REFERENCE
    assert (
        json.loads(world.internal(world.record_at(unauthorized.replay_reference)).fields["cause"])
        == "unauthorized"
    )
    assert (
        json.loads(
            nonexistent_world.internal(
                nonexistent_world.record_at(nonexistent.replay_reference)
            ).fields["cause"]
        )
        == "nonexistent"
    )


# ---------------------------------------------------------------------------
# The construction-time refusal, and its sabotage (C-36, `D-IMPL-256` (2)).
# ---------------------------------------------------------------------------


def _builder_kwargs(address: ProductAddress, root: Path) -> dict[str, Any]:
    return {
        "server_name": SERVER_NAME,
        "resolver": _answering(None),
        "token_verifier": SourceBackedTokenVerifier(
            source=FileTokenSource(path=_token_file(root, tenant=address.tenant))
        ),
        "auth_settings": AuthSettings(
            issuer_url=AnyHttpUrl("https://issuer.invalid"),
            resource_server_url=AnyHttpUrl(f"{IN_PROCESS_BASE_URL}/mcp"),
            required_scopes=[SCOPE],
        ),
        "authorizer": wide_authorizer(scopes=(SCOPE,)),
        "entitlement_source": ControlPlaneProductEntitlementSource(
            control_plane=ControlPlaneRegistry(), clock=lambda: DETERMINED_AT
        ),
        "perspective_resolver": (
            lambda *, grant, tenant, requested_role: Perspective(
                principal_id=grant.client_id, role=ROLE
            )
        ),
        "expose_product_tool": True,
        "product_tool_description": TOOL_DESCRIPTION,
    }


@pytest.mark.parametrize("recorder", [None, object()])
def test_a_door_that_could_deny_unrecorded_is_not_built(
    recorder: object, assembled: Any, tmp_path: Path
) -> None:
    """``D-IMPL-256`` (2): the refusal is at construction, and it names where.

    Both failures are covered because they arrive differently: a deployment
    that bound an entitlement source and forgot the recorder, and one that
    bound something that is not a recorder at all. Neither builds, so there is
    no recorder-less door to measure a residual channel at — no warn-and-serve
    posture, no denial-branch failure, and nothing that would make
    auditability contingent on outcome.
    """
    with pytest.raises(UnrecordableDeliveryBoundaryError) as refused:
        build_egress_server(
            **_builder_kwargs(assembled.address, tmp_path),
            refusal_recorder=recorder,  # type: ignore[arg-type]
        )

    assert "build_egress_server" in str(refused.value)
    assert "refusal_recorder=" in str(refused.value)


def test_a_conforming_recorder_builds_the_door(
    assembled: Any, tmp_path: Path
) -> None:
    """The vacuity guard: without it, the two raises pass against a dead builder."""
    server = build_egress_server(
        **_builder_kwargs(assembled.address, tmp_path),
        refusal_recorder=refusal_recorder(
            ControlPlaneRegistry(),
            store=deployment_store(tmp_path / "artifacts", REPLAY_ARTIFACT_CLASS),
            tenant=assembled.address.tenant,
            replay_record_class=REPLAY_ARTIFACT_CLASS,
            assembly_mode="algorithmic",
        ),
    )

    assert server.name == SERVER_NAME


#: The construction-time check the sabotage removes. Asserted present, exactly
#: once, before mutating — a reflow makes this control fail loudly rather than
#: silently mutate nothing.
RECORDER_CHECK = (
    "    recorder = recorded_boundary(\n"
    '        refusal_recorder=refusal_recorder, builder="build_egress_server"\n'
    "    )\n"
)
SKIPPED_CHECK = "    recorder = refusal_recorder  # SABOTAGE\n"

#: The governed step both handlers call. The second sabotage replaces every
#: occurrence with the pre-`D-IMPL-256` direct call.
GOVERNED_CALL = "govern_entitlement("

#: What the pre-`D-IMPL-256` door did instead: reach `entitled_perspective`
#: directly, so a denial left as a raise. Appended to the scratch module, which
#: is legal because a handler resolves its globals when it RUNS.
PRE_256_SHIM = '''

from ccf_runtime.authz.product_entitlement import (
    entitled_perspective as _pre_256_entitled,
)


def _pre_256(
    *,
    grant,
    tenant,
    product_class,
    product_version,
    requested_role,
    parameters,
    asked_at,
    surface,
    address,
    entitlement_source,
    perspective_resolver,
    refusal_recorder,
):
    """The 24.5 shape: entitle directly, and let the refusal RAISE."""
    return _pre_256_entitled(
        grant=grant,
        tenant=tenant,
        product_class=product_class,
        requested_role=requested_role,
        entitlement_source=entitlement_source,
        perspective_resolver=perspective_resolver,
    )
'''


def _scratch_egress(tmp_path: Path, *, mutate: Callable[[str], str], name: str) -> types.ModuleType:
    """Import a MUTATED copy of ``egress.py`` under its own module name.

    A scratch copy, never an edit-and-revert: a control implemented as an edit
    leaves nothing in the tree, and one implemented as a test runs on every CI
    run forever.
    """
    source = EGRESS_SOURCE.decode("utf-8")
    mutated = mutate(source)
    assert mutated != source, "the sabotage did not take"
    path = tmp_path / f"egress_{name}.py"
    path.write_text(mutated, encoding="utf-8")
    spec = importlib.util.spec_from_file_location(f"egress_{name}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[f"egress_{name}"] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:  # pragma: no cover - a broken scratch is a red test
        sys.modules.pop(f"egress_{name}", None)
        raise
    return module


def test_a_builder_that_skips_the_recorder_check_is_red_sabotage(
    assembled: Any, tmp_path: Path
) -> None:
    """Remove the check on a scratch copy and the recorder-less door BUILDS.

    That is what makes the two raises above a property of this module rather
    than of the arguments the tests happen to pass. The sabotaged builder
    returns a real ``FastMCP`` whose handlers hold ``recorder = None``, which is
    exactly the door ``D-IMPL-256`` (2) refuses to let exist.
    """

    def mutate(source: str) -> str:
        assert source.count(RECORDER_CHECK) == 1, (
            "the construction-time check is not where the sabotage looks"
        )
        return source.replace(RECORDER_CHECK, SKIPPED_CHECK)

    scratch = _scratch_egress(tmp_path, mutate=mutate, name="skipping_the_check")

    built = scratch.build_egress_server(
        **_builder_kwargs(assembled.address, tmp_path), refusal_recorder=None
    )
    assert built.name == SERVER_NAME, (
        "the sabotage did not build a recorder-less door, so it is not a control"
    )

    # And the REAL builder refuses the identical call.
    with pytest.raises(UnrecordableDeliveryBoundaryError):
        build_egress_server(
            **_builder_kwargs(assembled.address, tmp_path), refusal_recorder=None
        )


def test_a_door_that_entitles_directly_leaks_prose_red_sabotage(
    assembled: Any, tmp_path: Path
) -> None:
    """The pre-``D-IMPL-256`` shape, restored on a scratch copy, and it leaks.

    This is the control for D-20 itself: with the governed step replaced by a
    direct :func:`~ccf_runtime.authz.product_entitlement.entitled_perspective`
    call, the denial RAISES, FastMCP wraps it as ``isError`` prose, and the
    typed ``error_code`` reaches a client as a string it would have to parse.
    The shipped door answers the identical call ``isError`` false.
    """

    def mutate(source: str) -> str:
        assert source.count(GOVERNED_CALL) == 2, (
            f"expected two {GOVERNED_CALL!r} calls, found"
            f" {source.count(GOVERNED_CALL)}"
        )
        return source.replace(GOVERNED_CALL, "_pre_256(") + PRE_256_SHIM

    scratch = _scratch_egress(tmp_path, mutate=mutate, name="entitling_directly")

    world = _World(
        tmp_path, address=assembled.address, resolver=_answering(assembled.served)
    )
    sabotaged = scratch.build_egress_server(
        **{
            **_builder_kwargs(assembled.address, tmp_path),
            "entitlement_source": world.source,
            "resolver": _answering(assembled.served),
        },
        refusal_recorder=world.recorder,
    )
    at = _unentitled(assembled.address)

    is_error, text = _drive(sabotaged, _tool_operation(_tool_arguments(at)))

    assert is_error is True, (
        "the sabotage did not restore the raise, so it is not a control"
    )
    # Both halves of the leak: the typed code a client would have to
    # string-parse, and the CLASS NAME beside it — which is the suppression
    # channel `D-27` amendment 2 (4) names, since a caller learns from the
    # prose that the subject exists and is merely closed to them.
    assert ERROR_PRODUCT_CLASS_UNENTITLED in text, text
    assert UNENTITLED in text, text

    shipped_error, shipped_text = _call_tool(world, address=at)
    assert shipped_error is False, shipped_text


def test_no_sabotage_edits_the_real_source_tree() -> None:
    """Both controls above mutate a copy under ``tmp_path``."""
    assert EGRESS_PATH.read_bytes() == EGRESS_SOURCE
    source = EGRESS_SOURCE.decode("utf-8")
    assert RECORDER_CHECK in source
    assert SKIPPED_CHECK not in source
    assert "_pre_256" not in source


# ---------------------------------------------------------------------------
# The transport-neutrality gate for THIS door (criterion 36).
# ---------------------------------------------------------------------------

#: The seams a transport must never reach. `record` and `record_refusal` are the
#: minting seams; `disclose`/`disclose_only` are the Disclosure layer's;
#: `write_replay_record` is the writer's. Read by ATTRIBUTE name, so a call
#: written through any object trips it.
MINTING_ATTRIBUTES = frozenset(
    {"record", "disclose_only", "disclose", "write_replay_record", "record_refusal"}
)


def _transport_violations(source: str) -> list[str]:
    """Every mint, disclosure or governance catch an AST walk finds.

    A walk rather than a grep, because a grep over prose is satisfied by a
    docstring that merely *says* the door mints nothing — and this module's
    docstrings say exactly that, at length.
    """
    tree = ast.parse(source)
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in MINTING_ATTRIBUTES:
                found.append(f"line {node.lineno}: {ast.unparse(node.func)}(")
        if isinstance(node, ast.ExceptHandler) and node.type is not None:
            if "ProductEntitlementRefused" in ast.unparse(node.type):
                found.append(f"line {node.lineno}: except ProductEntitlementRefused")
    return found


def test_the_egress_transport_never_mints() -> None:
    """Criterion 36: *replay belongs to the determination, not to HTTP or MCP*.

    The egress half. Plan ``24.6-11`` Task 3 covers both transport trees in
    wave 9, once all three doors exist; this asserts it for the door this plan
    built, at the commit that built it.

    What would fail here: a door that "helpfully" recorded the denial it
    noticed — which is the inverted sequence Dave's ruling names and rejects,
    and which reappears as the standing-resource/tool asymmetry somewhere else.
    """
    assert _transport_violations(EGRESS_SOURCE.decode("utf-8")) == []


def test_the_transport_walk_sees_a_planted_call(tmp_path: Path) -> None:
    """The planted-call control: a walk that sees nothing passes vacuously.

    Two plants, because the walk makes two different claims: an attribute call
    into a minting seam, and an ``except`` for the governance refusal.
    """
    source = EGRESS_SOURCE.decode("utf-8")
    anchor = "    recorder = recorded_boundary(\n"
    assert source.count(anchor) == 1

    minting = source.replace(
        anchor, "    _leaked = refusal_recorder.record(None)  # PLANT\n" + anchor
    )
    assert any("record(" in entry for entry in _transport_violations(minting)), (
        "the walk did not see a planted minting call"
    )

    catching = source.replace(
        "    if not expose_product_resource and not expose_product_tool:\n",
        "    try:\n        pass\n    except ProductEntitlementRefused:  # PLANT\n"
        "        pass\n"
        "    if not expose_product_resource and not expose_product_tool:\n",
    )
    assert any(
        "ProductEntitlementRefused" in entry for entry in _transport_violations(catching)
    ), "the walk did not see a planted governance catch"


# ---------------------------------------------------------------------------
# (4) A raised non-refusal is a TRANSPORT error carrying an opaque id.
# ---------------------------------------------------------------------------


def test_a_raised_failure_is_a_tool_error_with_an_opaque_id(
    assembled: Any, tmp_path: Path
) -> None:
    """``T-24.6-34``: the fabric's own failure, and nothing about it.

    ``LookupError("boom")`` stands for any runtime failure inside the
    deployment's assembly path. The client learns that CCF failed and an id it
    can quote to an operator; it does not learn the exception's text, and the
    prose ``boom`` — which in a real deployment would be a store path, a query
    or a subject — is asserted absent by name.

    ``Error executing tool …`` is FastMCP's own prefix on the wrapped error and
    is the transport's; the id after it is ours.
    """
    world = _World(
        tmp_path,
        address=assembled.address,
        resolver=_raising(LookupError("boom")),
    )

    is_error, text = _call_tool(world)

    assert is_error is True
    assert re.match(
        rf"^Error executing tool .*{CCF_FAILURE_PREFIX}:[0-9a-f]{{32}}$", text
    ), text
    assert "boom" not in text
    assert "LookupError" not in text


# ---------------------------------------------------------------------------
# (5) No governed determination is a tool error — over the WHOLE vocabulary.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("kind", sorted(REFUSAL_KINDS.values()))
def test_no_kind_in_the_vocabulary_is_ever_a_tool_error(
    kind: str, assembled: Any, tmp_path: Path
) -> None:
    """Enumerated over the vocabulary itself, so coverage is proven not claimed.

    Parametrizing over ``REFUSAL_KINDS.values()`` rather than over a hand-listed
    subset is what makes *"no governed determination is a tool error"* a
    statement about the closed set: a kind added next year is covered here
    without an edit, and a kind the door special-cased would fail alone.

    The envelope is built at the ``RefusalEnvelope`` level rather than from each
    of the twenty-three underlying types, because the claim under test is about
    the DOOR's branch — a refusal is a return value, so the failure wrapper
    cannot reach it (``T-24.6-37``) — and not about any type's own fields.
    """
    # Recorded through the door's own recorder, lazily (`D-IMPL-260` P-A).
    held: dict[str, _World] = {}

    def resolve(**_: Any) -> object:
        return held["world"].recorder.record(
            RefusalEnvelope(
                kind=kind,
                reason=kind,
                key=None,
                detail="a governed determination this deployment reached",
                fields={},
                request=_identity(assembled.address),
                pre_assembly_lineage=None,
            ),
            perspective=Perspective(principal_id=PRINCIPAL, role=ROLE),
            recorded_at=DETERMINED_AT,
            served_at=DETERMINED_AT,
            resolution=ResolutionNotApplicable(reason="no-resolution-step"),
        )

    world = _World(tmp_path, address=assembled.address, resolver=resolve)
    held["world"] = world

    is_error, text = _call_tool(world)

    assert is_error is False, text
    outcome = _decode(text)
    assert outcome.refusal is not None
    assert outcome.refusal.kind == kind
