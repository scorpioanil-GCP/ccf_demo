"""At the MCP door, "you may not" and "there is no such thing" are one statement.

``D-IMPL-253`` D-27 as strengthened by **amendment 2 (4)** (Dave, verbatim):

    *"Unauthorized and nonexistent subjects must be consumer-observationally
    equivalent at the same disclosure level: same transport status, kind,
    external reason, body schema/field presence and permitted disclosure
    behavior. Internal truth/replay may differ according to policy."*

    *"I would not require byte identity, because request identity, timestamps,
    replay IDs, etc. may legitimately differ. The criterion should test
    semantic/observable equivalence, not accidental byte equality."*

He named six ways the two could still diverge after *same kind, same reason,
same shape* — **HTTP status, presence/absence of evidence fields, lineage,
replay reference behavior, message text, serialization differences** — and this
module measures all six at this door, plus the kind/reason/disclosure triple
the base ruling already required. Ledger row ``24.6-L-21``, MCP half; plan
``24.6-09`` holds the HTTP half.

**Both subjects are produced, never hand-built.** The unauthorized answer comes
from a real unentitled read at a real authenticated door, denied by
``govern_entitlement`` and minted at the entitlement source's determination
instant. The nonexistent answer comes from a deployment resolver that envelopes
``SubjectUnavailableRefusal(cause="nonexistent")`` and returns
``refusal_recorder.record(...)`` over the **same** recorder the server was built
with — the real minting path, not a hand-built ``disclose``. Two hand-built
shells would agree with each other and prove nothing about the mechanism.

**Both surfaces, because the door has two.** The tool pair and the resource pair
are compared over the same channels. Since ``D-IMPL-256`` (1) the resource-path
denial is minted the same way the tool's is, so the resource pair is a second
real pair rather than a weaker echo of the first.

Tenant, principal, role, class, scope and token names are test deployment
vocabulary. The SDK holds none of them (CINV-01).
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
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
from ccf.products.disclosure import (
    DISCLOSURE_LEVELS,
    INDISTINGUISHABLE_BELOW_FULL,
)
from ccf.products.door import DoorOutcome, WireRequest
from ccf.products.entitlement import (
    PRODUCT_ENTITLEMENT_POLICY,
    ProductEntitlementGrant,
    ProductEntitlementPolicy,
    product_entitlement_key,
)
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
from ccf_runtime.authz.product_entitlement import (
    ControlPlaneProductEntitlementSource,
)
from ccf_runtime.mcp.auth import FileTokenSource, SourceBackedTokenVerifier
from ccf_runtime.mcp.egress import (
    PRODUCT_REQUEST_TOOL,
    build_egress_server,
)
from tests.mcp.guarded_servers import wide_authorizer

from crossproc.servers.mcp_egress_child import ProductAddress, build_servable_product
from ccf.controlplane.registry import ControlPlaneRegistry
from http_api.composition_authority import (
    deployment_store,
    refusal_recorder,
    register_typed_at_composition,
)

#: Test deployment vocabulary; the SDK ships none of it.
TOKEN = "egress-disclosure-token"
PRINCIPAL = "egress-disclosure-caller"
SCOPE = "ccf:egress-disclosure"
ROLE = "egress-disclosure-role"
SERVER_NAME = "ccf-egress-disclosure"
POLICY_VERSION = "1.0.0"
TOOL_DESCRIPTION = "Ask this test deployment's product class a question."
REPLAY_RECORD_CLASS = "egress-disclosure.replay-record"

#: The class this caller holds no grant for — the UNAUTHORIZED subject.
UNENTITLED = "a-class-this-caller-was-never-granted"

SUBJECT = "egress-disclosure-subject"
INTENT = "egress-disclosure-intent"
FRESHNESS = "egress-disclosure-freshness"
ASKED_AT = datetime(2026, 9, 5, 9, 30, tzinfo=UTC)

#: One pinned determination instant, so a timestamp cannot become an accidental
#: channel and the two records are comparable on everything but their causes.
DETERMINED_AT = datetime(2026, 9, 5, 11, 15, tzinfo=UTC)

IN_PROCESS_BASE_URL = "http://127.0.0.1:8131"

#: The internal statement the nonexistent subject carries. Deliberately a
#: DIFFERENT sentence from the one the entitlement denial carries: if the two
#: internal details were made identical, the message-text channel Dave named
#: would be equal by construction and this module would prove nothing about
#: disclosure.
NONEXISTENT_DETAIL = "no subject resolves at that anchor in this fabric"


# ---------------------------------------------------------------------------
# The world, per disclosure level.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def assembled(tmp_path_factory: pytest.TempPathFactory) -> Any:
    """One assembled, gate-admitted product, reused by every door below."""
    return build_servable_product(
        database_path=tmp_path_factory.mktemp("egress-disclosure") / "door.sqlite3"
    )


def _token_file(root: Path, *, tenant: str) -> Path:
    """The door's token file, whose one credential is scoped to ``tenant``.

    ``tenant`` is required rather than defaulted (``SEC-018``): a credential
    that names no tenant reaches nothing, so a fixture that forgot it would
    fail loudly instead of quietly minting the unscoped bearer this finding is
    about.
    """
    path = root / "egress-disclosure-tokens.json"
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
    """One booted door at ONE declared disclosure level.

    The level is set on the tenant's registered
    :class:`~ccf.products.entitlement.ProductEntitlementPolicy`, which is where
    ``24.6-08`` put it — so what this module varies is a **Control Plane
    value**, not a test switch. Dave, Q17: *"Suppression silence should be
    policy-controlled, with minimal disclosure as the safe default."*
    """

    def __init__(self, root: Path, *, address: ProductAddress, level: str) -> None:
        self.address = address
        self.level = level
        self.registry = ControlPlaneRegistry()
        register_typed_at_composition(self.registry, 
            product_entitlement_key(tenant_id=address.tenant),
            ProductEntitlementPolicy(
                tenant_id=address.tenant,
                policy_version=POLICY_VERSION,
                disclosure_level=level,  # type: ignore[arg-type]
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
        self.store = deployment_store(root / "artifacts", REPLAY_RECORD_CLASS)
        self.recorder = refusal_recorder(
            self.registry,
            store=self.store,
            tenant=address.tenant,
            replay_record_class=REPLAY_RECORD_CLASS,
            assembly_mode="algorithmic",
            disclosure_level_for=self.source.disclosure_level_for,
        )
        self._tokens = _token_file(root, tenant=address.tenant)

    def server(self) -> Any:
        """A FRESH door over this world's one registry, source, store and recorder.

        A new ``FastMCP`` per ask, deliberately: the installed
        ``mcp==1.28.1``'s ``StreamableHTTPSessionManager`` refuses a second
        ``run()`` on one instance, and this module asks two questions of every
        world. What must NOT be fresh is everything behind the door — one
        policy read at one level, one store, one recorder — because two worlds
        would be comparing two deployments rather than two answers.
        """
        return build_egress_server(
            server_name=SERVER_NAME,
            resolver=self._resolve,  # type: ignore[arg-type]
            token_verifier=SourceBackedTokenVerifier(
                source=FileTokenSource(path=self._tokens)
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
            expose_product_tool=True,
            product_tool_description=TOOL_DESCRIPTION,
        )

    def _resolve(
        self,
        *,
        tenant: str,
        product_class: str,
        version: str,
        perspective: Perspective,
        request: ProductRequest | None,
    ) -> object:
        """The NONEXISTENT subject, minted through the door's own recorder.

        Never a hand-built ``disclose``: this returns what
        :meth:`~ccf.products.resolver.ReplayRefusalRecorder.record` returns, so
        the shell a consumer sees on this leg was produced by the identical
        seam that produced the unauthorized one, under the identical policy
        read. A fixture that hand-built the shell would compare two of this
        module's own opinions rather than two of the fabric's answers.
        """
        return self.recorder.record(
            envelope_for(
                SubjectUnavailableRefusal(
                    cause="nonexistent", detail=NONEXISTENT_DETAIL
                ),
                request=RequestIdentity(
                    product_id=product_class,
                    product_version=version,
                    parameters=dict(request.parameters) if request else {},
                    temporal_boundary=request.asked_at if request else None,
                ),
            ),
            perspective=Perspective(
                principal_id=perspective.principal_id, role=NO_ROLE_RESOLVED
            ),
            recorded_at=DETERMINED_AT,
            resolution=ResolutionNotApplicable(reason="no-resolution-step"),
        )

    def record_at(self, uri: str) -> DecisionReplayRecord:
        return DecisionReplayRecord.model_validate_json(
            self.store.get(content_address=self.store.resolve_uri(uri=uri))
        )

    def internal_envelope(self, uri: str) -> RefusalEnvelope:
        """The determination as the fabric recorded it, before disclosure."""
        record = self.record_at(uri)
        return RefusalEnvelope.model_validate_json(
            record.content_generation_path.assembly_refusal
        )

    def internal_cause(self, uri: str) -> str:
        return json.loads(self.internal_envelope(uri).fields["cause"])

    def resolves(self, uri: str) -> bool:
        try:
            self.store.resolve_uri(uri=uri)
        except Exception:
            return False
        return True


def _unentitled(address: ProductAddress) -> ProductAddress:
    return ProductAddress(
        tenant=address.tenant, product_class=UNENTITLED, version=address.version
    )


# ---------------------------------------------------------------------------
# The drivers.
# ---------------------------------------------------------------------------


def _drive(
    server: Any, operation: Callable[[ClientSession], Awaitable[tuple[bool, str]]]
) -> tuple[bool, str]:
    app = server.streamable_http_app()

    async def go() -> tuple[bool, str]:
        async with app.router.lifespan_context(app):

            def factory() -> httpx.AsyncClient:
                return httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app),
                    base_url=IN_PROCESS_BASE_URL,
                    headers={"Authorization": f"Bearer {TOKEN}"},
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


def _resource_operation(
    uri: str,
) -> Callable[[ClientSession], Awaitable[tuple[bool, str]]]:
    async def operation(session: ClientSession) -> tuple[bool, str]:
        result = await session.read_resource(AnyUrl(uri))
        return False, "".join(
            contents.text
            for contents in result.contents
            if isinstance(contents, TextResourceContents)
        )

    return operation


# ---------------------------------------------------------------------------
# What a consumer can observe, as one value.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Answer:
    """Everything about one refusal a CONSUMER can see, and nothing else.

    Deliberately not the door's internals: the record, the internal cause and
    the store are read separately, by the caller, and are never members here.
    An equivalence check that could reach internal truth would pass or fail for
    reasons a consumer cannot observe, which is the opposite of what amendment
    2 (4) asks for.

    Attributes:
        is_error: The transport's own flag — Dave's *"transport status"* on a
            protocol with no status code.
        outcome: The decoded :class:`~ccf.products.door.DoorOutcome` on the tool
            path, or ``None`` on the resource path, whose body **is** the
            envelope. Carried rather than flattened so the envelope-schema
            channel is checkable on the surface that has one.
        refusal: The shell itself.
        resolves: Whether the shell's ``replay_reference`` resolves in the
            store the door wrote to — the *"replay reference behavior"* channel,
            which is about behavior rather than value: the two references
            legitimately differ and that difference is excluded.
        text: The bytes the door actually put on the wire, kept as text.
            Carried because *key presence* is a channel amendment 2 (4) names
            explicitly, and a parsed :class:`RefusalEnvelope` cannot report it:
            ``model_dump`` re-materializes every member at its default whether
            the rendering carried the key or not, so a presence divergence is
            invisible to a comparison made over the parsed model
            (``D-IMPL-258`` (2)).
    """

    is_error: bool
    outcome: DoorOutcome | None
    refusal: RefusalEnvelope
    resolves: bool
    text: str


def wire_shell(answer: Answer) -> dict[str, Any]:
    """The refusal shell exactly as it was rendered, keys and all.

    The tool path nests the shell inside a
    :class:`~ccf.products.door.DoorOutcome`; the resource path's body **is**
    the shell. Both are read from :attr:`Answer.text` rather than from the
    parsed model, for the reason that attribute records.
    """
    document = json.loads(answer.text)
    shell = document.get("refusal", document)
    assert isinstance(shell, dict), answer.text
    return shell


def _tool_answer(world: _World, address: ProductAddress) -> Answer:
    is_error, text = _drive(world.server(), _tool_operation(_tool_arguments(address)))
    outcome = DoorOutcome.model_validate_json(text)
    assert outcome.refusal is not None, text
    return Answer(
        is_error=is_error,
        outcome=outcome,
        refusal=outcome.refusal,
        resolves=world.resolves(outcome.refusal.replay_reference),
        text=text,
    )


def _resource_answer(world: _World, address: ProductAddress) -> Answer:
    is_error, text = _drive(world.server(), _resource_operation(address.uri))
    shell = RefusalEnvelope.model_validate_json(text)
    return Answer(
        is_error=is_error,
        outcome=None,
        refusal=shell,
        resolves=world.resolves(shell.replay_reference),
        text=text,
    )


#: What legitimately differs and is therefore never compared. Dave: *"request
#: identity, timestamps, replay IDs, etc. may legitimately differ."*
#:
#: `refusal.resource` was on this tuple until `D-IMPL-260` P-J: the phase's own
#: instrument excluded the member on that sentence, and the close review
#: measured that its KEY PRESENCE — carried by a boundary denial, absent from
#: an assembler's determination — told the two subjects apart at every level.
#: It is now a compared channel, (9) below, and the disclosure step normalizes
#: it below `full`.
EXCLUDED = ("refusal.request", "the replay reference's value")


def observational_equivalence_violations(*, a: Answer, b: Answer) -> list[str]:
    """Every channel on which two governed denials are distinguishable.

    Seven channels, each named after what a consumer would read. The function
    returns the violated names rather than asserting, so the controls below can
    plant a divergence and see the *specific* channel it lands on — a boolean
    would let a control pass by breaking something else.

    Args:
        a: One consumer-observable answer.
        b: The other, for the same question at the same level.

    Returns:
        The violated channel names, sorted. Empty means indistinguishable.
    """
    violations: list[str] = []

    # (1) Transport status. MCP has no status code; `isError` is the flag a
    # client branches on, and it is the whole of the status channel here.
    if a.is_error != b.is_error:
        violations.append("is_error")

    # (2) The outcome envelope's schema, on the surface that has one.
    if (a.outcome is None) != (b.outcome is None):
        violations.append("outcome.presence")
    elif a.outcome is not None and b.outcome is not None:
        if set(a.outcome.model_dump()) != set(b.outcome.model_dump()):
            violations.append("outcome.schema")
        if (a.outcome.product_json is None) != (b.outcome.product_json is None):
            violations.append("outcome.product_json")

    # (3) Body schema and field PRESENCE — amendment 2 (4) names presence
    # explicitly, and a shape channel is harder to notice than a prose one.
    if set(a.refusal.model_dump()) != set(b.refusal.model_dump()):
        violations.append("refusal.schema")
    if set(a.refusal.fields) != set(b.refusal.fields):
        violations.append("refusal.fields.keys")

    # (4) Message text.
    if a.refusal.detail != b.refusal.detail:
        violations.append("refusal.detail")

    # (5) Evidence and lineage presence — two of the six Dave named.
    if (a.refusal.evidence is None) != (b.refusal.evidence is None):
        violations.append("refusal.evidence.presence")
    if (a.refusal.pre_assembly_lineage is None) != (
        b.refusal.pre_assembly_lineage is None
    ):
        violations.append("refusal.pre_assembly_lineage.presence")

    # (6) Replay-reference BEHAVIOR, never its value. Both must be real
    # references and both must resolve; that they name different records is the
    # internal truth policy is allowed to differ on.
    for name, answer in (("a", a), ("b", b)):
        if answer.refusal.replay_reference == NO_REPLAY_REFERENCE:
            violations.append(f"refusal.replay_reference.sentinel[{name}]")
        if not answer.resolves:
            violations.append(f"refusal.replay_reference.unresolvable[{name}]")

    # (7) The base ruling's triple, plus the declared level the shell states.
    for member in ("kind", "reason", "disclosure"):
        if getattr(a.refusal, member) != getattr(b.refusal, member):
            violations.append(f"refusal.{member}")

    # The remaining field values at whatever level is in force. `fields` is
    # where the internal cause lives, so this is the channel that legitimately
    # opens at `full` and must be shut below it.
    for key in sorted(set(a.refusal.fields) & set(b.refusal.fields)):
        if a.refusal.fields[key] != b.refusal.fields[key]:
            violations.append(f"fields.{key}")

    # (8) `policy_bindings` — ruled in `D-IMPL-258` (2), where `24.6-10`'s F-1
    # left it open. BOTH halves, because Dave named both: *"If unauthorized and
    # nonexistent subjects differ in `policy_bindings` by either key presence
    # or value, then they are not consumer-observationally equivalent."* The
    # presence half is read off the rendered bytes rather than the parsed
    # model, which reports every member whether the wire carried it or not.
    if a.refusal.policy_bindings != b.refusal.policy_bindings:
        violations.append("refusal.policy_bindings")
    if ("policy_bindings" in wire_shell(a)) != ("policy_bindings" in wire_shell(b)):
        violations.append("refusal.policy_bindings.presence")

    # (9) `resource` — ruled in `D-IMPL-260` P-J. The same two halves as (8):
    # the boundary denial carried the identity it was decided against and the
    # nonexistent determination carried none, so the key's presence alone was
    # a channel. Read the same way, for the same reason.
    if a.refusal.resource != b.refusal.resource:
        violations.append("refusal.resource")
    if ("resource" in wire_shell(a)) != ("resource" in wire_shell(b)):
        violations.append("refusal.resource.presence")

    return sorted(violations)


# ---------------------------------------------------------------------------
# The measurement, per level, on both surfaces.
# ---------------------------------------------------------------------------

def _allowed_to_differ(level: str) -> list[str]:
    """What the two denials may differ on at ``level``, DERIVED from the tree.

    At `minimal` and `reasoned`: **nothing**. ``subject-unavailable`` is in
    :data:`~ccf.products.disclosure.INDISTINGUISHABLE_BELOW_FULL`, so every
    member that could tell the two causes apart is withheld — the key kept, the
    value replaced — at both levels.

    At `full` the internal truth crosses by policy, and what crosses is
    **exactly the members that table names**: five since ``D-IMPL-260`` P-J
    added ``resource`` beside ``D-IMPL-258`` (2)'s ``policy_bindings``.
    `cause` is the discriminator itself; `error_code` is present on the
    entitlement denial and absent on the nonexistent one; `detail` is the two
    determinations' own sentences; and `policy_bindings` and `resource` are
    the members the rulings normalize **below** `full` and leave alone at it.
    Derived by reading the shipped table and mapping each
    member to the channel it lands on, rather than transcribed — so a member
    leaving that table, or a new kind joining it, changes this expectation
    without an edit here, and a member the table names that does NOT actually
    differ at `full` fails the equality below.
    """
    if level != "full":
        return []
    members = INDISTINGUISHABLE_BELOW_FULL[
        REFUSAL_KINDS[SubjectUnavailableRefusal]
    ]
    # Three shapes of channel name, and the split is read off the shipped
    # types rather than spelled: a WHOLE member of the envelope lands on
    # `refusal.<member>` and — when one side renders the key and the other
    # does not — on `refusal.<member>.presence` too; `detail` is a whole
    # member with no presence half, because it is required and always
    # rendered; everything else is a `fields` key.
    names: list[str] = []
    for member in members:
        if member == "detail":
            names.append(f"refusal.{member}")
        elif member in RefusalEnvelope.model_fields:
            names.extend((f"refusal.{member}", f"refusal.{member}.presence"))
        else:
            names.append(f"fields.{member}")
    return sorted(names)


@pytest.mark.parametrize("level", sorted(DISCLOSURE_LEVELS))
def test_unauthorized_and_nonexistent_are_observationally_equivalent(
    level: str, assembled: Any, tmp_path: Path
) -> None:
    """D-27 amendment 2 (4), at this door, on both surfaces, per level.

    The tool pair first, then the resource pair asserted as a **second** pair
    over the same seven channels. Both are real: since ``D-IMPL-256`` (1) the
    resource-path denial is minted by the governed step at the determination
    instant, exactly as the tool's is.

    What would fail here: any of the six channels Dave named — the transport
    flag, evidence presence, lineage presence, replay-reference behavior,
    message text, or the body's shape — carrying the difference between *you
    may not* and *there is no such thing*.
    """
    world = _World(tmp_path, address=assembled.address, level=level)
    unentitled = _unentitled(assembled.address)

    tool = observational_equivalence_violations(
        a=_tool_answer(world, unentitled),
        b=_tool_answer(world, assembled.address),
    )
    resource = observational_equivalence_violations(
        a=_resource_answer(world, unentitled),
        b=_resource_answer(world, assembled.address),
    )

    expected = _allowed_to_differ(level)
    assert tool == expected, f"tool path at {level!r}: {tool}"
    assert resource == expected, f"resource path at {level!r}: {resource}"


@pytest.mark.parametrize("level", sorted(DISCLOSURE_LEVELS))
def test_the_two_denials_differ_in_the_record_at_every_level(
    level: str, assembled: Any, tmp_path: Path
) -> None:
    """The other half of the ruling: *"Internal truth/replay may differ."*

    Without this, the equivalence above would pass against a door that had
    destroyed the distinction rather than suppressed it — Dave, Q27: *"Don't
    destroy audit truth merely to achieve external suppression silence."* Both
    references resolve, and the two records say different things.
    """
    world = _World(tmp_path, address=assembled.address, level=level)

    unauthorized = _tool_answer(world, _unentitled(assembled.address))
    nonexistent = _tool_answer(world, assembled.address)

    assert world.internal_cause(unauthorized.refusal.replay_reference) == "unauthorized"
    assert world.internal_cause(nonexistent.refusal.replay_reference) == "nonexistent"


def test_the_policy_binding_channel_is_closed_below_full(
    assembled: Any, tmp_path: Path
) -> None:
    """`policy_bindings` cannot tell the two subjects apart below `full`.

    The inversion of ``24.6-10``'s measurement, under ``D-IMPL-258`` (2), Dave:
    *"the externally disclosed* ``RefusalEnvelope`` *must normalize/suppress
    that field so unauthorized and nonexistent cases have the same observable
    policy-binding shape at the same disclosure level; the control should prove
    equivalence at HTTP and MCP."* This is the MCP half; the HTTP half is
    ``tests/http_api/test_product_disclosure.py``.

    Two measurements per level, on both surfaces the door has:

    * the **count** of bindings each shell carries, which is the value half;
    * whether the rendered bytes carry the ``policy_bindings`` key at all,
      which is the presence half — the one a consumer can read without reading
      a value.

    Below `full` both are identical for the two subjects. At `full` internal
    truth crosses by policy and the entitlement denial's pin is visible, which
    is also this test's vacuity guard: a fixture where neither side ever
    carried a binding would make the two closed levels pass for free.

    What would fail here: the ``policy_bindings`` row leaving
    :data:`~ccf.products.disclosure.INDISTINGUISHABLE_BELOW_FULL` (the sabotage
    of record), or a normalization applied on one surface and not the other.
    """
    counts: dict[str, tuple[int, int]] = {}
    keys: dict[str, tuple[bool, bool]] = {}
    resource_keys: dict[str, tuple[bool, bool]] = {}
    for level in sorted(DISCLOSURE_LEVELS):
        world = _World(tmp_path / level, address=assembled.address, level=level)
        unentitled = _unentitled(assembled.address)
        unauthorized = _tool_answer(world, unentitled)
        nonexistent = _tool_answer(world, assembled.address)
        counts[level] = (
            len(unauthorized.refusal.policy_bindings),
            len(nonexistent.refusal.policy_bindings),
        )
        keys[level] = (
            "policy_bindings" in wire_shell(unauthorized),
            "policy_bindings" in wire_shell(nonexistent),
        )
        resource_keys[level] = (
            "policy_bindings" in wire_shell(_resource_answer(world, unentitled)),
            "policy_bindings"
            in wire_shell(_resource_answer(world, assembled.address)),
        )

    assert counts == {
        "full": (1, 0),
        "minimal": (0, 0),
        "reasoned": (0, 0),
    }, counts
    assert keys == {
        "full": (True, False),
        "minimal": (False, False),
        "reasoned": (False, False),
    }, keys
    assert resource_keys == keys, resource_keys


def test_the_resource_channel_is_closed_below_full(
    assembled: Any, tmp_path: Path
) -> None:
    """`resource` cannot tell the two subjects apart below `full` (`D-IMPL-260` P-J).

    The member the phase's own instrument excluded, measured the way
    `policy_bindings` is: the key's presence on the rendered bytes, per level,
    on both surfaces. Below `full` it is absent from BOTH shells; at `full`
    the boundary denial carries it and the nonexistent determination does not
    — which is also this test's vacuity guard.

    What would fail here: the `resource` row leaving
    :data:`~ccf.products.disclosure.INDISTINGUISHABLE_BELOW_FULL` (the
    sabotage of record), or a normalization applied on one surface only.
    """
    keys: dict[str, tuple[bool, bool]] = {}
    resource_keys: dict[str, tuple[bool, bool]] = {}
    for level in sorted(DISCLOSURE_LEVELS):
        world = _World(tmp_path / level, address=assembled.address, level=level)
        unentitled = _unentitled(assembled.address)
        keys[level] = (
            "resource" in wire_shell(_tool_answer(world, unentitled)),
            "resource" in wire_shell(_tool_answer(world, assembled.address)),
        )
        resource_keys[level] = (
            "resource" in wire_shell(_resource_answer(world, unentitled)),
            "resource" in wire_shell(_resource_answer(world, assembled.address)),
        )

    assert keys == {
        "full": (True, False),
        "minimal": (False, False),
        "reasoned": (False, False),
    }, keys
    assert resource_keys == keys, resource_keys


def test_the_record_keeps_the_resource_identity_the_shell_no_longer_shows(
    assembled: Any, tmp_path: Path
) -> None:
    """`D-IMPL-260` P-J's other half: *"retain internally/replay."*

    The boundary denial's record still names what resource was addressed, on
    which surface, at what instant (`D-IMPL-256` (1)) — the closure above is a
    disclosure act, not an erasure.
    """
    world = _World(tmp_path, address=assembled.address, level="minimal")
    unauthorized = _tool_answer(world, _unentitled(assembled.address))

    assert unauthorized.refusal.resource is None
    internal = world.internal_envelope(unauthorized.refusal.replay_reference)
    assert internal.resource is not None, internal
    assert internal.resource.surface == "mcp-tool"
    assert internal.resource.address, internal.resource


def test_the_record_keeps_the_bindings_the_shell_no_longer_shows(
    assembled: Any, tmp_path: Path
) -> None:
    """``D-IMPL-258`` (2)'s other half: the audit plane keeps what governed it.

    Dave: *"replay/internal determination may retain the actual policy bindings
    that produced the decision."* So the closure above must be a disclosure act
    and not an erasure. Without this, a door that simply stopped pinning the
    entitlement policy would pass every consumer-side assertion in this module
    — and would be the *"destroy audit truth merely to achieve external
    suppression silence"* Q27 forbids.
    """
    world = _World(tmp_path, address=assembled.address, level="minimal")
    unauthorized = _tool_answer(world, _unentitled(assembled.address))

    assert unauthorized.refusal.policy_bindings == ()
    internal = world.internal_envelope(unauthorized.refusal.replay_reference)
    assert internal.policy_bindings, internal
    assert all(source.version for source in internal.policy_bindings), internal


# ---------------------------------------------------------------------------
# The watched controls (D-22): each plants ONE divergence.
# ---------------------------------------------------------------------------


def _pair(world: _World, assembled: Any) -> tuple[Answer, Answer]:
    return (
        _tool_answer(world, _unentitled(assembled.address)),
        _tool_answer(world, assembled.address),
    )


@pytest.fixture()
def indistinguishable(assembled: Any, tmp_path: Path) -> tuple[Answer, Answer]:
    """A real, passing pair at ``minimal`` — the subject every control mutates."""
    world = _World(tmp_path, address=assembled.address, level="minimal")
    pair = _pair(world, assembled)
    assert observational_equivalence_violations(a=pair[0], b=pair[1]) == [], (
        "the control subject is not indistinguishable to begin with, so nothing"
        " a control plants below can be attributed to the control"
    )
    return pair


def test_the_status_control_fires(
    indistinguishable: tuple[Answer, Answer],
) -> None:
    """A door that made one of them a transport error is caught.

    The pre-``D-IMPL-256`` shape, exactly: the unauthorized read was `isError`
    and the nonexistent one was not, so a consumer could tell them apart
    without reading a single field.
    """
    honest, other = indistinguishable
    diverged = Answer(
        is_error=True,
        outcome=honest.outcome,
        refusal=honest.refusal,
        resolves=honest.resolves,
        # The wire text is the honest one: every control here plants its
        # divergence on the PARSED model, and the only channel read off
        # the bytes is `policy_bindings.presence`, which no control here
        # touches (`D-IMPL-258` (2)).
        text=honest.text,
    )

    assert "is_error" in observational_equivalence_violations(a=diverged, b=other)


def test_the_evidence_presence_control_fires(
    indistinguishable: tuple[Answer, Answer],
) -> None:
    """Evidence attached to one and not the other — Dave's second channel.

    Presence, not content: the mere fact that one refusal carried evidence and
    the other did not tells a consumer which one the fabric actually looked for.
    """
    from ccf.graph.protocols import NO_STORE_SNAPSHOT_PIN
    from ccf.products.refusal import RefusalEvidence

    honest, other = indistinguishable
    diverged = Answer(
        is_error=honest.is_error,
        outcome=honest.outcome,
        refusal=honest.refusal.model_copy(
            update={
                "evidence": RefusalEvidence(
                    operators_invoked=frozenset(),
                    plan_id="a-plan-only-one-of-them-ran",
                )
            }
        ),
        resolves=honest.resolves,
        # The wire text is the honest one: every control here plants its
        # divergence on the PARSED model, and the only channel read off
        # the bytes is `policy_bindings.presence`, which no control here
        # touches (`D-IMPL-258` (2)).
        text=honest.text,
    )

    assert "refusal.evidence.presence" in observational_equivalence_violations(
        a=diverged, b=other
    )


def test_the_field_set_control_fires(
    indistinguishable: tuple[Answer, Answer],
) -> None:
    """A field dropped rather than withheld — the SHAPE channel.

    ``24.6-08``'s discipline is that a withheld value is replaced and its key is
    kept, so the shell's shape is identical for every internal cause at one
    level. A door that *removed* the key instead would leak the difference
    through the body's shape, which is harder to notice than prose.
    """
    honest, other = indistinguishable
    thinner = dict(honest.refusal.fields)
    thinner.pop("cause")
    diverged = Answer(
        is_error=honest.is_error,
        outcome=honest.outcome,
        refusal=honest.refusal.model_copy(update={"fields": thinner}),
        resolves=honest.resolves,
        # The wire text is the honest one: every control here plants its
        # divergence on the PARSED model, and the only channel read off
        # the bytes is `policy_bindings.presence`, which no control here
        # touches (`D-IMPL-258` (2)).
        text=honest.text,
    )

    assert "refusal.fields.keys" in observational_equivalence_violations(
        a=diverged, b=other
    )


def test_the_sentinel_versus_reference_control_fires(
    indistinguishable: tuple[Answer, Answer],
) -> None:
    """One recorded and one not — the *replay reference behavior* channel.

    The silent second class (``D-IMPL-253`` Q13) read from the consumer's seat:
    a denial that minted no record carries the sentinel, and a consumer holding
    both answers can tell which decision the fabric bothered to record.
    """
    honest, other = indistinguishable
    diverged = Answer(
        is_error=honest.is_error,
        outcome=honest.outcome,
        refusal=honest.refusal.model_copy(
            update={"replay_reference": NO_REPLAY_REFERENCE}
        ),
        resolves=False,
        # The wire text is the honest one: every control here plants its
        # divergence on the PARSED model, and the only channel read off
        # the bytes is `policy_bindings.presence`, which no control here
        # touches (`D-IMPL-258` (2)).
        text=honest.text,
    )

    violations = observational_equivalence_violations(a=diverged, b=other)
    assert "refusal.replay_reference.sentinel[a]" in violations
    assert "refusal.replay_reference.unresolvable[a]" in violations


def test_the_comparison_refuses_a_single_answer(
    indistinguishable: tuple[Answer, Answer],
) -> None:
    """One answer compared with itself is not evidence of anything.

    The vacuity guard for the whole module: every control above plants a
    divergence into a **pair**, and a comparison that could be handed one
    answer twice would report perfect equivalence forever. Asserted as a
    property of the subjects rather than of the function — the two answers must
    be different objects describing different determinations, which is what the
    differing internal causes in the record test establishes.
    """
    honest, other = indistinguishable

    assert honest is not other
    assert honest.refusal.replay_reference != other.refusal.replay_reference, (
        "the two legs named one record, so they are one determination compared"
        " with itself rather than two compared with each other"
    )
    assert observational_equivalence_violations(a=honest, b=honest) == []


def test_equivalence_is_not_byte_identity(
    indistinguishable: tuple[Answer, Answer],
) -> None:
    """Two answers that differ on the EXCLUDED members still pass.

    Dave: *"I would not require byte identity, because request identity,
    timestamps, replay IDs, etc. may legitimately differ."* This is that
    sentence executed: the two shells below carry different request identities
    and different replay references, are not byte-identical, and are still
    indistinguishable on every channel a consumer can read them through.
    """
    honest, other = indistinguishable

    assert canonical_bytes(honest.refusal) != canonical_bytes(other.refusal), (
        "the two shells are byte-identical, so this test would pass without the"
        " exclusions it exists to justify"
    )
    for member in EXCLUDED[:1]:
        name = member.split(".", 1)[1]
        assert getattr(honest.refusal, name) != getattr(other.refusal, name), (
            f"{member} is equal across the pair, so excluding it is untested"
        )
    # And `resource` is NOT among the exclusions any more: both sides are
    # normalized below `full`, so equality here is the closure and not an
    # accident of the fixture (`D-IMPL-260` P-J).
    assert honest.refusal.resource is None and other.refusal.resource is None
    assert observational_equivalence_violations(a=honest, b=other) == []
