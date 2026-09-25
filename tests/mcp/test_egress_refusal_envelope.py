"""The MCP door says "no" in the one shape, and both doors name the record.

``D-IMPL-148`` (Dave, 2026-08-17) **as amended by Addendum A the same day**.
Two rulings are executed here and they arrived as one change because they need
the same one:

* **The refusal is the tool's return value, never a raise.** Measured against
  ``mcp==1.28.1``, a FastMCP tool that raises reaches the client as
  ``isError=True`` carrying ``ToolError: Error executing tool <name>:
  <message>`` — so a client wanting the governed answer would have to strip a
  server's wording. String-parsing prose for an audited verdict is not a
  channel, and that is why the shape moved.
* **Both doors carry the replay reference.** ``Result.replay_ref`` is in
  ``GUARDED_FIELDS`` and ``assert_served_parity`` compares every declared field,
  so an adapter bound against a door that emits none would fail parity on it.
  The base entry scoped the fix to the MCP door; Dave superseded that with
  *both, not one* — the principle ``D-IMPL-133`` applied to ``parameters``.

Because the tool's return had to become a structure for the refusal, the
reference rides that same change rather than forcing a second one. The HTTP door
has a header channel, so it publishes the identical string there and its body
stays the vessel.

What this module measures, and at what strength
------------------------------------------------
The unit under test is **what a door emits**, decoded the way a client decodes
it — :meth:`~ccf.products.door.DoorOutcome.model_validate_json` over the tool's
text, and the response header over HTTP. It is deliberately not a source
reading: a door that imported the envelope and never emitted one would pass a
grep and fail every assertion below.

**Served and refused are discriminated structurally.** Every leg validates the
tool's text as a :class:`~ccf.products.door.DoorOutcome` and reads the member;
nothing here sniffs for a key or matches a string. The two halves are exclusive
by a model validator, and underneath that
:class:`~ccf.products.refusal.RefusalEnvelope` and the vessel are both
``extra=forbid`` with disjoint required fields, so neither can validate as the
other.

The controls (``D-22``)
------------------------
Every assertion is a function taking its subject as a parameter, and each
control calls *that same function* with a divergent subject — never a copy of
it, and never by editing ``runtime/`` and reverting. A control implemented as an
edit leaves nothing in the tree; a control implemented as a test runs on every
CI run forever. This is the discipline plan ``17-10`` Task 1 already shipped in
``tests/mcp/test_egress_parameters.py``.

Tenant, principal, role, class, parameter, artifact and token names are test
deployment vocabulary. The SDK holds none of them (CINV-01).
"""

from __future__ import annotations

import asyncio
import json
import re
import tempfile
from collections.abc import Awaitable, Callable, Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import pytest
from mcp.client.session import ClientSession
from mcp.server.auth.settings import AuthSettings
from mcp.types import TextContent
from pydantic import AnyHttpUrl, ValidationError

from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.protocol import ArtifactRef
from ccf.contracts.canonical import canonical_bytes
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.mcp.client import run_with_session
from ccf.mcp.errors import McpServerUnreachable
from ccf.products.door import DoorOutcome, UngovernedResolverResult, door_refusal
from ccf.products.entitlement import (
    PRODUCT_ENTITLEMENT_POLICY,
    ProductEntitlementGrant,
    ProductEntitlementPolicy,
    product_entitlement_key,
)
from ccf.products.disclosure import WITHHELD
from ccf.products.gates import TTLRefusal
from ccf.graph.protocols import NO_STORE_SNAPSHOT_PIN
from ccf.products.provenance import EffectiveRequest, ProvenanceSource
from ccf.products.refusal import (
    NO_REPLAY_REFERENCE,
    REFUSAL_KINDS,
    RefusalEnvelope,
    RefusalEvidence,
    RequestIdentity,
    ResourceRequestIdentity,
    SubjectUnavailableRefusal,
    envelope_for,
)
from ccf.products.resolver import ReplayRefusalRecorder
from ccf.products.request import (
    ProductRequest,
    ProductRequestContract,
    refuse_request,
)
from ccf.projection.plan import Perspective
from ccf.replay.record import DecisionReplayRecord, ResolutionNotApplicable
from ccf.replay.serve import ServedProduct
from ccf.skills.catalog import SkillArgumentProperty, SkillArgumentSchema
from ccf_runtime.authz.delivery_boundary import (
    SURFACE_MCP_RESOURCE,
    govern_entitlement,
)
from ccf_runtime.authz.product_entitlement import (
    ControlPlaneProductEntitlementSource,
    ProductEntitlementRefused,
)
from ccf_runtime.mcp.auth import TokenGrant
from ccf_runtime.http_api.app import create_app
from ccf_runtime.http_api.dependencies import ApiDependencies
from ccf_runtime.http_api.routes import REPLAY_REF_HEADER

from http_api.gate_fixtures import SCOPE_EVERYTHING, authority
from ccf_runtime.mcp.auth import FileTokenSource, SourceBackedTokenVerifier
from ccf.contracts.canonical import canonical_bytes
from ccf.products.door import WireRequest
from ccf_runtime.mcp.egress import (
    CCF_FAILURE_PREFIX,
    PRODUCT_REQUEST_TOOL,
    build_egress_server,
    product_uri,
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
TOKEN = "egress-refusal-token"
PRINCIPAL = "egress-refusal-caller"
SCOPE = "ccf:egress-refusal"
ROLE = "egress-refusal-role"
#: This suite's own scope-mapping key. The authorizer pins one version at
#: one key, so a key of its own is what keeps another suite's mapping from
#: deciding about this suite's vocabulary.
MAPPING_KEY = "egress-refusal/scope-mapping"
SERVER_NAME = "ccf-egress-refusal"
POLICY_VERSION = "1.0.0"
AUDIT_INSTANT = datetime(2026, 8, 17, tzinfo=UTC)
TOOL_DESCRIPTION = "Ask this test deployment's product class a question."
REPLAY_ARTIFACT_CLASS = "egress-refusal-replay-record"
REPLAY_ARTIFACT_NAME = "egress-refusal-snapshot"

#: The four §6.3 axes, held constant so the only thing moving between legs is
#: what the deployment's resolver answered with.
SUBJECT = "egress-refusal-subject"
INTENT = "egress-refusal-intent"
FRESHNESS = "egress-refusal-freshness"
ASKED_AT = datetime(2026, 8, 17, 9, 30, tzinfo=UTC)

#: The declared surface this module's class carries, and the mapping a caller
#: sends against it. One required parameter, so a request violation is
#: reachable by *omitting* it rather than by hand-building a verdict.
REQUIRED_PARAMETER = "minimum_score"
UNDECLARED_PARAMETER = "not_declared_by_this_class"
CALLER_PARAMETERS: Mapping[str, Any] = {REQUIRED_PARAMETER: 11}

#: Loopback with an explicit port: FastMCP's DNS-rebinding protection allows
#: ``127.0.0.1:*`` even over ASGI, where no socket exists. Nothing binds it.
IN_PROCESS_BASE_URL = "http://127.0.0.1:8127"

#: What a door answers with, as a callable — the unit the replay-reference
#: assertion compares two doors as, and the unit a control substitutes.
AskRef = Callable[[], str | None]

#: What a door does with a refusal it was handed. The subject of the
#: governance-boundary assertion; a control passes a divergent one.
Renderer = Callable[[ProductEntitlementRefused], RefusalEnvelope | None]


# ---------------------------------------------------------------------------
# The shipped assertions — functions over their subjects (D-22).
# ---------------------------------------------------------------------------


def assert_refusals_identical(
    first: RefusalEnvelope, second: RefusalEnvelope
) -> None:
    """Two decoded refusals agree on **every declared field**.

    The D-15(b) leg in miniature, and written the way
    ``tests/client/conformance/suite.py`` writes its own: the field list is
    **derived from the type**, never transcribed. A member added to
    :class:`~ccf.products.refusal.RefusalEnvelope` next year is compared here
    without an edit, which is what stops this assertion from quietly narrowing
    as the contract widens.

    Comparing whole objects with ``==`` would be shorter and strictly worse: it
    reports *"they differ"* and names nothing, so the first real failure would
    send a reader diffing two multi-page envelopes by eye.

    Args:
        first: One decoded refusal.
        second: The other, for the same question.

    Raises:
        AssertionError: any declared field disagreed.
    """
    differences = [
        f"{name}: {getattr(first, name)!r} != {getattr(second, name)!r}"
        for name in RefusalEnvelope.model_fields
        if getattr(first, name) != getattr(second, name)
    ]
    if differences:
        raise AssertionError(
            "two refusals for the same question disagreed — "
            + "; ".join(differences)
            + ". A refusal that changes shape at a transport is a refusal a"
            " cross-adapter parity suite cannot compare, which is what"
            " `D-IMPL-148` refused to work around by exempting the field"
        )


def assert_governance_is_shelled(render: Renderer) -> None:
    """A governance refusal becomes the suppression-safe shell, never a raise.

    **This assertion is the inversion of the one that stood here through
    ``24.5``** (``D-IMPL-253`` Q20, ``D-IMPL-256``; ``24.6-L-03``). It was
    ``assert_governance_stays_a_raise``, and it asserted that a renderer handed
    a ``ProductEntitlementRefused`` produced **no** envelope, on the reading
    that an envelope *"would report 'the fabric answered no' about a caller the
    fabric never answered at all."* Dave's ruling denies the premise: an
    entitlement denial **is** a governed determination the fabric made, and it
    shares the one canonical external outcome a nonexistent subject also
    carries — ``subject-unavailable`` — so that *you may not* and *there is no
    such thing* are one statement at the principal's disclosure level (Q27,
    ``D-27`` amendment 2 (4)).

    Three channels are checked and each would fail differently: a renderer that
    still returns ``None`` is the pre-ruling door (the control below); one that
    returns a *different* kind has made the denial distinguishable from a
    nonexistent subject by kind alone; and one whose ``cause`` is not withheld
    has leaked the internal truth into the shell at ``minimal``, which is the
    suppression leak the disclosure layer exists to close.

    The subject is the **renderer**, not the door, so the control below can pass
    a divergent one into this same function.

    Args:
        render: What a door does with a governance refusal. The shipped subject
            runs the real
            :func:`~ccf_runtime.authz.delivery_boundary.govern_entitlement`
            over a source that raises exactly the refusal handed in, and returns
            the shell it hands back.

    Raises:
        AssertionError: the renderer produced no envelope, the wrong kind, or a
            shell whose internal cause crossed at ``minimal``.
    """
    rendered = render(
        ProductEntitlementRefused(
            error_code="ERROR_TEST_PRINCIPAL_NOT_ENTITLED",
            message="this principal is not entitled to this class",
        )
    )
    if rendered is None:
        raise AssertionError(
            "a governance refusal was rendered as nothing at all, which is the"
            " pre-`D-IMPL-256` door: the denial then reaches a client as"
            " transport prose it would have to string-parse, and the decision"
            " reaches no replay record. A denial is a governed determination"
            " and leaves as one"
        )
    if rendered.kind != REFUSAL_KINDS[SubjectUnavailableRefusal]:
        raise AssertionError(
            f"a governance refusal was shelled as kind {rendered.kind!r}, not"
            f" {REFUSAL_KINDS[SubjectUnavailableRefusal]!r}; the whole point of"
            " the shared outcome is that an unauthorized principal and a"
            " nonexistent subject are one external statement, and a kind of its"
            " own would make 'you may not' readable from the outside"
        )
    crossed = json.loads(rendered.fields["cause"])
    if crossed != WITHHELD:
        raise AssertionError(
            f"the shell's `cause` crossed as {crossed!r} rather than the"
            f" withheld sentinel {WITHHELD!r}; the internal cause is what"
            " distinguishes an unauthorized principal from a nonexistent"
            " subject, so a shell that carries it at `minimal` has suppressed"
            " nothing"
        )


def assert_both_doors_carry_the_replay_ref(
    ask_mcp: AskRef, ask_http: AskRef
) -> None:
    """Both doors name the same replay record for the same served product.

    ``D-IMPL-148`` **Addendum A**'s *"both, not one"*, executable — the shape
    ``assert_same_verdicts`` already has in
    ``tests/mcp/test_egress_parameters.py``, for the same reason: one shared
    subject asked of both real doors is what keeps them from drifting apart one
    edit at a time.

    **Absence is checked before equality, and that ordering is the point.** Two
    doors that both emitted ``None`` would agree perfectly while carrying
    nothing — the vacuous pass this repository ships repeatedly — so a ``None``
    from either side is refused by name rather than compared.

    Args:
        ask_mcp: The MCP tool, as a callable returning the reference it emitted.
        ask_http: The HTTP route, in the same shape.

    Raises:
        AssertionError: either door emitted no reference, or the two disagreed.
    """
    mcp_ref = ask_mcp()
    http_ref = ask_http()
    absent = [
        name
        for name, ref in (("the MCP tool", mcp_ref), ("the HTTP route", http_ref))
        if ref is None
    ]
    if absent:
        raise AssertionError(
            f"{' and '.join(absent)} emitted no replay reference for a product"
            " whose resolver produced one. Two doors that both emit nothing"
            " agree perfectly while carrying nothing, which is why absence is"
            " refused here rather than compared — and it is the exact state"
            " `D-IMPL-148` was raised about"
        )
    if mcp_ref != http_ref:
        raise AssertionError(
            f"the MCP tool named {mcp_ref!r} and the HTTP route named"
            f" {http_ref!r} for the same served product; the reference is a"
            " property of the decision, not of the transport that reported it"
        )


# ---------------------------------------------------------------------------
# The declared world both doors are measured against.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def assembled(tmp_path_factory: pytest.TempPathFactory) -> Any:
    """One assembled, gate-admitted product, reused by every door below."""
    return build_servable_product(
        database_path=tmp_path_factory.mktemp("egress-refusal") / "door.sqlite3"
    )


#: The parameter this module's class declares and always refuses, and the
#: reason its declaration authors (``24.5-L-13``). Test deployment vocabulary.
INERT_PARAMETER = "as_of"
INERT_REASON = "declared, always refused at this tier"


def _contract(
    address: ProductAddress, *, inert: Mapping[str, str] | None = None
) -> ProductRequestContract:
    """The request surface this module's class declares — one required integer.

    ``inert`` widens it with the declared-and-always-refused mapping; omitted,
    the contract is exactly what it was before ``24.5-L-13``.
    """
    return ProductRequestContract(
        semver="1.0.0",
        schema_name=address.product_class,
        schema_version=address.version,
        arguments=SkillArgumentSchema(
            properties={
                REQUIRED_PARAMETER: SkillArgumentProperty(
                    type="integer",
                    description="The declared threshold this class answers at.",
                )
            },
            required=(REQUIRED_PARAMETER,),
        ),
        unsupported_arguments=dict(inert or {}),
    )


def _replay_ref(address: ProductAddress) -> ArtifactRef:
    """The reference a deployment's replay append would have produced."""
    return ArtifactRef(
        content_address="a" * 64,
        uri=f"ccf-artifact://{address.tenant}/{REPLAY_ARTIFACT_CLASS}/1",
        tenant_id=address.tenant,
        artifact_class=REPLAY_ARTIFACT_CLASS,
        name=REPLAY_ARTIFACT_NAME,
    )


def _identity(address: ProductAddress) -> RequestIdentity:
    """The question, as the door carried it."""
    return RequestIdentity(
        product_id=address.product_class,
        product_version=address.version,
        parameters=dict(CALLER_PARAMETERS),
        temporal_boundary=ASKED_AT,
    )


def _ttl_refusal() -> TTLRefusal:
    """One gate refusal with fields of its own beyond ``gate`` and ``detail``."""
    return TTLRefusal(
        gate="ttl",
        detail="expires_at fell outside (now, now + MAX_TTL]",
        expires_at=ASKED_AT + timedelta(days=400),
        now=ASKED_AT,
        max_ttl_seconds=3600,
    )


def _answering(outcome: object) -> Callable[..., object]:
    """A resolver that answers every call with ``outcome``, whatever it is.

    The seam is typed to ``ServableProduct`` and this returns a wider set on
    purpose: the whole subject of this module is what a door does with the
    shapes a deployment's resolver actually returns (``D-IMPL-148``
    Addendum A), and a fixture narrowed to the declared type could not present
    any of them.
    """

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


def _refusing(
    declared: ProductRequestContract, *, root: Path | None = None
) -> Callable[..., object]:
    """A resolver that runs the one shared comparison and RECORDS its verdict.

    It calls :func:`~ccf.products.request.refuse_request` — the obligation
    ``ProductResolverProtocol`` puts on every resolver — so the violation these
    legs carry is one the fabric genuinely produced rather than one this module
    hand-built to the shape it wanted to see. Since ``D-IMPL-260`` P-A it then
    hands the verdict through the one minting seam, because a door releases
    only a refusal that proves its record and its disclosure; the bare value
    this returned before is refused at the door as a wiring defect. The store
    is per resolver, under ``root`` when given and under a fresh temporary
    directory otherwise — a fixture that needs to read the record back passes
    its own root.
    """
    store = deployment_store(
        (root or Path(tempfile.mkdtemp(prefix="egress-refusing-"))) / "artifacts",
        REPLAY_ARTIFACT_CLASS,
    )
    # Where this stub deployment's composition decisions are recorded.
    composition = ControlPlaneRegistry()

    def resolve(
        *,
        tenant: str,
        product_class: str,
        version: str,
        perspective: Perspective,
        request: ProductRequest | None,
    ) -> object:
        assert request is not None
        violation = refuse_request(request=request, declared=declared)
        assert violation is not None, (
            "this leg's caller was built to violate the declared surface and"
            " did not; the fixture, not the door, is what failed"
        )
        recorder = refusal_recorder(
            composition,
            store=store,
            tenant=tenant,
            replay_record_class=REPLAY_ARTIFACT_CLASS,
            assembly_mode="algorithmic",
        )
        return recorder.record(
            envelope_for(
                violation,
                request=RequestIdentity(
                    product_id=product_class,
                    product_version=version,
                    parameters=request.parameters,
                    temporal_boundary=request.asked_at,
                ),
            ),
            perspective=perspective,
            recorded_at=request.asked_at,
            resolution=ResolutionNotApplicable(reason="no-resolution-step"),
            request=request,
        )

    return resolve


def _minted(
    root: Path, address: ProductAddress, value: object, *, level: str = "minimal"
) -> RefusalEnvelope:
    """One refusal, RECORDED and DISCLOSED at ``level``, as a resolver must return it.

    ``D-IMPL-260`` P-A: the door releases only what
    :class:`~ccf.products.resolver.ReplayRefusalRecorder` hands back. A bare
    value is enveloped with this surface's identity first; an envelope is
    recorded as it is. The disclosure reader is a stub answering ``level``, so
    a test that needs the whole internal envelope on the wire asks for
    ``"full"`` and gets exactly what the recorder would return under a policy
    declaring it.
    """
    recorder = refusal_recorder(
        ControlPlaneRegistry(),
        store=deployment_store(root / "artifacts", REPLAY_ARTIFACT_CLASS),
        tenant=address.tenant,
        replay_record_class=REPLAY_ARTIFACT_CLASS,
        assembly_mode="algorithmic",
        disclosure_level_for=lambda *, tenant, principal_id: (level, None),
    )
    envelope = (
        value
        if isinstance(value, RefusalEnvelope)
        else envelope_for(value, request=_identity(address))
    )
    return recorder.record(
        envelope,
        perspective=Perspective(principal_id=PRINCIPAL, role=ROLE),
        recorded_at=ASKED_AT,
        resolution=ResolutionNotApplicable(reason="no-resolution-step"),
    )


def _refusing_and_recording(
    declared: ProductRequestContract, *, store: Any, tenant: str
) -> Callable[..., object]:
    """:func:`_refusing`, minting the refusal's decision record (``24.6-07``).

    ``D-IMPL-253`` Q13 made a refusal a recorded decision, so a resolver that
    returned a bare value and appended nothing is no longer what a governed
    seam does. This one runs the same shared comparison and then hands the
    verdict through the ONE minting seam
    (:class:`~ccf.products.resolver.ReplayRefusalRecorder`), which is what a
    real deployment's :class:`~ccf.products.resolver.GovernedResolver` does on
    every refusal branch.

    It returns the **envelope** rather than the bare value, because that is
    what a shell carrying its own replay reference has to be — and
    ``door_refusal`` passes an envelope through untouched, so the two doors
    below compare exactly what the resolver produced.
    """
    recorder = refusal_recorder(
        ControlPlaneRegistry(),
        store=store,
        tenant=tenant,
        replay_record_class=REPLAY_ARTIFACT_CLASS,
        assembly_mode="algorithmic",
    )

    def resolve(
        *,
        tenant: str,
        product_class: str,
        version: str,
        perspective: Perspective,
        request: ProductRequest | None,
    ) -> object:
        assert request is not None
        violation = refuse_request(request=request, declared=declared)
        assert violation is not None, (
            "this leg's caller was built to violate the declared surface and"
            " did not; the fixture, not the door, is what failed"
        )
        return recorder.record(
            envelope_for(
                violation,
                request=RequestIdentity(
                    product_id=product_class,
                    product_version=version,
                    parameters=request.parameters,
                    temporal_boundary=request.asked_at,
                ),
            ),
            perspective=perspective,
            recorded_at=request.asked_at,
            resolution=ResolutionNotApplicable(reason="no-resolution-step"),
            request=request,
        )

    return resolve


# ---------------------------------------------------------------------------
# The MCP door.
# ---------------------------------------------------------------------------


def _recorder(root: Path, *, tenant: str) -> ReplayRefusalRecorder:
    """The seam every entitling door in this module binds (``D-IMPL-256`` (2)).

    Built with the keyword list ``build_governed_resolver`` uses for its own,
    so a door's recorder and a resolver's are the same shape over the same
    store — *one writer, one record form*. The disclosure reader is left at
    its default, which reads nothing and answers ``minimal``: these fixtures
    register an entitlement policy that declares no level, and ``minimal`` is
    what that policy is in force at.
    """
    return refusal_recorder(
        ControlPlaneRegistry(),
        store=deployment_store(root / "artifacts", REPLAY_ARTIFACT_CLASS),
        tenant=tenant,
        replay_record_class=REPLAY_ARTIFACT_CLASS,
        assembly_mode="algorithmic",
    )


def _token_file(root: Path, *, tenant: str) -> Path:
    """The door's token file, whose one credential is scoped to ``tenant``.

    ``tenant`` is required rather than defaulted (``SEC-018``): a credential
    that names no tenant reaches nothing, so a fixture that forgot it would
    fail loudly instead of quietly minting the unscoped bearer this finding is
    about.
    """
    path = root / "egress-refusal-tokens.json"
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


def _entitlement(
    address: ProductAddress, *, classes: frozenset[str] | None = None
) -> ControlPlaneProductEntitlementSource:
    registry = ControlPlaneRegistry()
    register_typed_at_composition(registry, 
        product_entitlement_key(tenant_id=address.tenant),
        ProductEntitlementPolicy(
            tenant_id=address.tenant,
            policy_version=POLICY_VERSION,
            principals={
                PRINCIPAL: ProductEntitlementGrant(
                    permitted_schema_names=(
                        frozenset({address.product_class})
                        if classes is None
                        else classes
                    ),
                    permitted_roles=frozenset({ROLE}),
                )
            },
        ),
        PRODUCT_ENTITLEMENT_POLICY,
    )
    return ControlPlaneProductEntitlementSource(
        control_plane=registry, clock=lambda: AUDIT_INSTANT
    )


def _mcp_server(
    root: Path,
    *,
    address: ProductAddress,
    resolver: Callable[..., object],
    classes: frozenset[str] | None = None,
) -> Any:
    """The real egress door, tool exposed, over the supplied resolver."""
    return build_egress_server(
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
        entitlement_source=_entitlement(address, classes=classes),
        perspective_resolver=(
            lambda *, grant, tenant, requested_role: Perspective(
                principal_id=grant.client_id, role=ROLE
            )
        ),
        # `D-IMPL-256` (2): a door that entitles without a recorder is not
        # built, so every fixture door in this module binds the seam.
        refusal_recorder=_recorder(root, tenant=address.tenant),
        expose_product_tool=True,
        product_tool_description=TOOL_DESCRIPTION,
    )


def _tool_arguments(
    address: ProductAddress, parameters: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        "tenant": address.tenant,
        "product_class": address.product_class,
        "version": address.version,
        # The caller's own question, encoded (`C-16`). Built from the same
        # values the address arguments beside it carry, because the door
        # refuses a call that encodes one question and addresses another.
        "request": canonical_bytes(
            WireRequest(
                product_id=address.product_class,
                parameters=dict(parameters),
                temporal_boundary=None,
            )
        ).decode("utf-8"),
        "subject": SUBJECT,
        "intent": INTENT,
        "freshness": FRESHNESS,
        "asked_at": ASKED_AT.isoformat(),
        "parameters": dict(parameters),
    }


def _tool_operation(
    arguments: dict[str, Any],
) -> Callable[[ClientSession], Awaitable[tuple[bool, str]]]:
    async def operation(session: ClientSession) -> tuple[bool, str]:
        result = await session.call_tool(PRODUCT_REQUEST_TOOL, arguments)
        return bool(result.isError), " | ".join(
            content.text
            for content in result.content
            if isinstance(content, TextContent)
        )

    return operation


def _drive_mcp(
    server: Any,
    operation: Callable[[ClientSession], Awaitable[tuple[bool, str]]],
) -> tuple[bool, str]:
    """Run one operation against the server's own ASGI app, in one lifespan."""
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


def _ask_mcp_door(
    root: Path,
    *,
    address: ProductAddress,
    resolver: Callable[..., object],
    parameters: Mapping[str, Any] = CALLER_PARAMETERS,
    classes: frozenset[str] | None = None,
) -> tuple[bool, str]:
    """Ask the real MCP tool one question; return ``(is_error, text)``."""
    return _drive_mcp(
        _mcp_server(root, address=address, resolver=resolver, classes=classes),
        _tool_operation(_tool_arguments(address, parameters)),
    )


def _decode(text: str) -> DoorOutcome:
    """What a client does with the tool's text — validate it, never sniff it.

    :class:`~ccf.products.door.DoorOutcome` is ``extra=forbid``, so a door that
    emitted the bare vessel or an ad-hoc dict fails here rather than being
    read as an outcome with missing halves.
    """
    return DoorOutcome.model_validate_json(text)


# ---------------------------------------------------------------------------
# The HTTP door.
# ---------------------------------------------------------------------------


def _http_app(
    root: Path, *, address: ProductAddress, resolver: Callable[..., object]
) -> Any:
    """The real HTTP product door, authenticated, authorized and entitled.

    The five authority seams come from
    :func:`~http_api.gate_fixtures.authority` as one bundle. None of them is
    this module's subject — it compares what the two doors put on the wire —
    and building five seams by hand in a module that is about something else
    is five chances to build a permissive one.

    The credential is the tenanted one that helper mints, not the dev
    ``FileTokenSource`` beside it: that source mints a grant with no scalar
    ``tenant``, and the HTTP door refuses it (``SEC-002``). The MCP leg keeps
    the token file, because the MCP tenancy floor reads the plural ``tenants``
    claim instead — the two doors read different shapes of the same fact, and
    that asymmetry is the SDK's, not this fixture's.
    """
    return create_app(
        ApiDependencies(
            control_plane=ControlPlaneRegistry(),
            artifact_store=deployment_store(root / "artifacts", REPLAY_ARTIFACT_CLASS),
            product_resolver=resolver,  # type: ignore[arg-type]
        ),
        **authority(
            tenant=address.tenant,
            key=MAPPING_KEY,
            grants={TOKEN: (PRINCIPAL, (SCOPE_EVERYTHING,), address.tenant)},
            product_entitlement=_entitlement(address),
            perspective_resolver=(
                lambda *, grant, tenant, requested_role: Perspective(
                    principal_id=grant.client_id, role=ROLE
                )
            ),
            # The HTTP twin binds the same seam on the same rule
            # (`D-IMPL-256` (2)). `create_app`'s own keyword and its
            # construction-time check are plan `24.6-09`'s, in this same wave;
            # this call site is this plan's.
            refusal_recorder=_recorder(root, tenant=address.tenant),
        ),
    )


def _ask_http_door(
    root: Path, *, address: ProductAddress, resolver: Callable[..., object]
) -> httpx.Response:
    """Ask the real HTTP route the same question, with the same parameters."""
    app = _http_app(root, address=address, resolver=resolver)

    async def go() -> httpx.Response:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://fabric.invalid",
        ) as client:
            return await client.get(
                f"/product/{address.tenant}/{address.product_class}"
                f"/{address.version}",
                params={
                    "subject": SUBJECT,
                    "intent": INTENT,
                    "freshness": FRESHNESS,
                    "asked_at": ASKED_AT.isoformat(),
                    "parameters": json.dumps(dict(CALLER_PARAMETERS)),
                },
                headers={"Authorization": f"Bearer {TOKEN}"},
            )

    return asyncio.run(go())


# ---------------------------------------------------------------------------
# The behaviours.
# ---------------------------------------------------------------------------


def test_a_request_the_class_does_not_answer_returns_an_envelope(
    assembled: Any, tmp_path: Path
) -> None:
    """Behaviour 1: a refusal is a **return value**, and its kind names it.

    What would fail here: the door letting the refusal reach the client as a
    raised ``ToolError``. That is not a hypothetical shape — it is what
    ``mcp==1.28.1`` does with any exception a tool body lets escape, prose
    prefix and all, and it is the measurement that decided this design.
    """
    address = assembled.address
    is_error, text = _ask_mcp_door(
        tmp_path,
        address=address,
        resolver=_refusing(_contract(address)),
        parameters={},
    )

    assert is_error is False, (
        f"the tool refused at the protocol level rather than returning the"
        f" governed refusal: {text}"
    )
    outcome = _decode(text)
    assert outcome.product_json is None
    assert outcome.refusal is not None
    assert outcome.refusal.kind == "product-request-violation"
    assert outcome.refusal.reason == "missing-required-parameter"
    assert outcome.refusal.key == REQUIRED_PARAMETER


def test_a_tier_refusal_arrives_as_a_typed_verdict_not_tool_error_prose(
    assembled: Any, tmp_path: Path
) -> None:
    """``24.5-L-12``/``L-13`` at a real client: the tier refusal is a typed verdict.

    What would fail here: the state the ladder shipped in, where every
    example's assembler raised ``AssemblyRefused("400 not_supported_at_tier
    …")`` because the reason vocabulary had no member for it — and the raise
    reached an MCP client as ``ToolError`` prose with ``isError=True``
    (``24.4`` deferred item 9). Now the declaration names the parameter inert,
    ``refuse_request`` returns the fifth reason, and the door envelopes it:
    ``is_error`` is **false** and the consumer reads ``kind``, ``reason`` and
    ``key`` as fields, not by parsing a sentence.
    """
    address = assembled.address
    is_error, text = _ask_mcp_door(
        tmp_path,
        address=address,
        resolver=_refusing(
            _contract(address, inert={INERT_PARAMETER: INERT_REASON}), root=tmp_path
        ),
        parameters={**CALLER_PARAMETERS, INERT_PARAMETER: "2026-08-17"},
    )

    assert is_error is False, (
        f"the tier refusal reached the client as protocol-level error prose"
        f" rather than as the governed verdict: {text}"
    )
    outcome = _decode(text)
    assert outcome.product_json is None
    assert outcome.refusal is not None
    assert outcome.refusal.kind == "product-request-violation"
    assert outcome.refusal.reason == "not-supported-at-tier"
    assert outcome.refusal.key == INERT_PARAMETER
    # The verdict's own sentence — the Standard's status token and the
    # declared reason prose — is on the RECORD; the wire carries the external
    # statement at this tenant's level (`D-IMPL-260` P-A: what crosses is the
    # recorded, disclosed shell, never the resolver's bare value).
    store = deployment_store(tmp_path / "artifacts", REPLAY_ARTIFACT_CLASS)
    record = DecisionReplayRecord.model_validate_json(
        store.get(
            content_address=store.resolve_uri(uri=outcome.refusal.replay_reference)
        )
    )
    internal = RefusalEnvelope.model_validate_json(
        record.content_generation_path.assembly_refusal
    )
    assert "400 not_supported_at_tier" in internal.detail
    assert INERT_REASON in internal.detail
    assert INERT_REASON not in outcome.refusal.detail


def test_a_gate_refusal_carries_its_own_typed_fields(
    assembled: Any, tmp_path: Path
) -> None:
    """Behaviour 2: nothing the refusal type declared is flattened out.

    What would fail here: a door that promoted ``gate`` and ``detail`` and
    dropped the rest. The three fields a ``TTLRefusal`` declares of its own are
    exactly what a consumer needs to tell *how far* outside the window the
    product fell, and a refusal reduced to a token cannot be audited.
    """
    address = assembled.address
    is_error, text = _ask_mcp_door(
        tmp_path,
        address=address,
        resolver=_answering(_minted(tmp_path, address, _ttl_refusal())),
    )

    assert is_error is False, text
    refusal = _decode(text).refusal
    assert refusal is not None
    assert refusal.kind == "ttl-refusal"
    # The gate token wins the `reason` promotion for the whole gate family.
    assert refusal.reason == "ttl"
    assert set(refusal.fields) == {"expires_at", "now", "max_ttl_seconds"}
    assert refusal.fields["max_ttl_seconds"] == "3600"


def test_the_envelope_carries_the_pre_assembly_request_identity(
    assembled: Any, tmp_path: Path
) -> None:
    """Behaviour 3: the question travels with the refusal — and no door emitted it.

    Constraint (b) of the envelope's own ruling. ``parameters`` is the member
    worth asserting by value: it is the half plan ``17-10`` Task 1 taught the
    door to carry, and a refusal that named the class but not the arguments
    would be an audit record of *which* question was refused with the question
    left out.
    """
    address = assembled.address
    is_error, text = _ask_mcp_door(
        tmp_path,
        address=address,
        resolver=_answering(_minted(tmp_path, address, _ttl_refusal())),
    )

    assert is_error is False, text
    refusal = _decode(text).refusal
    assert refusal is not None
    assert refusal.request == _identity(address)
    assert dict(refusal.request.parameters) == dict(CALLER_PARAMETERS)
    assert refusal.request.temporal_boundary == ASKED_AT


class _RefusingEntitlement:
    """An entitlement source that raises exactly the refusal it was handed.

    Conforms to
    :class:`~ccf_runtime.authz.product_entitlement.ProductEntitlementSourceProtocol`
    — including the ``clock`` member ``24.6-08`` added, pinned here — so the
    governed step below runs its real path over a real denial. Handing the
    exception in rather than provoking one is what keeps
    :func:`assert_governance_is_shelled` a function **over its subject**: the
    control passes a divergent renderer into the same assertion.
    """

    def __init__(self, refused: ProductEntitlementRefused) -> None:
        self._refused = refused
        self.clock: Callable[[], datetime] = lambda: AUDIT_INSTANT

    def authorize(
        self, *, grant: Any, tenant: str, product_class: str, role: str
    ) -> Any:
        raise self._refused


def test_a_governance_refusal_is_shelled_and_is_never_a_tool_error(
    assembled: Any, tmp_path: Path
) -> None:
    """Behaviour 4, INVERTED: the boundary moved, and this is where it now is.

    ``D-IMPL-253`` Q20 and ``D-IMPL-256``, ``24.6-L-03``. Through ``24.5`` this
    test was ``test_a_governance_refusal_still_raises_and_is_not_enveloped`` and
    asserted the opposite of every line below: ``is_error is True`` on the wire
    and a ``ValidationError`` on the decode, because the denial arrived as
    FastMCP prose rather than as an answer. Both halves invert together, and
    they still assert different things — the wire half is what a client
    observes, the renderer half is what the shipped mechanism produces — so a
    door could still get one right and the other wrong.

    A raised :class:`~ccf.agents.errors.AssemblyRefused` is a **failure** at
    this door and is unchanged in kind, but not in shape: since this row it
    reaches a client as the opaque ``ccf-runtime-failure:<id>``, asserted in
    ``tests/mcp/test_egress_refusal_channels.py``.
    """
    address = assembled.address
    is_error, text = _ask_mcp_door(
        tmp_path,
        address=address,
        resolver=_answering(assembled.served),
        classes=frozenset({"a-class-this-caller-was-never-granted"}),
    )

    assert is_error is False, text
    outcome = _decode(text)
    assert outcome.product_json is None
    assert outcome.refusal is not None
    assert outcome.refusal.kind == REFUSAL_KINDS[SubjectUnavailableRefusal]

    def render(refused: ProductEntitlementRefused) -> RefusalEnvelope | None:
        decided = govern_entitlement(
            grant=TokenGrant(client_id=PRINCIPAL, scopes=()),
            tenant=address.tenant,
            product_class=address.product_class,
            product_version=address.version,
            requested_role=None,
            parameters={},
            asked_at=None,
            surface=SURFACE_MCP_RESOURCE,
            address=product_uri(
                tenant=address.tenant,
                product_class=address.product_class,
                version=address.version,
            ),
            entitlement_source=_RefusingEntitlement(refused),  # type: ignore[arg-type]
            perspective_resolver=(
                lambda *, grant, tenant, requested_role: Perspective(
                    principal_id=grant.client_id, role=ROLE
                )
            ),
            refusal_recorder=_recorder(tmp_path / "rendered", tenant=address.tenant),
        )
        return decided if isinstance(decided, RefusalEnvelope) else None

    assert_governance_is_shelled(render)


def test_the_mcp_refusal_is_field_identical_to_the_in_process_one(
    assembled: Any, tmp_path: Path
) -> None:
    """Behaviour 5: the crossing loses nothing — the leg D-15(b) will consume.

    One resolver, driven two ways. In process a caller holds the envelope the
    resolver returned; over MCP the *same* envelope is canonically serialized,
    carried, and re-validated. Field-identity is therefore a statement about
    the **crossing** rather than about two implementations happening to agree,
    which is the only form of it a parity suite can lean on.

    **The resolver MINTS as of ``24.6-07``**, and that is what puts
    ``replay_reference`` inside this comparison rather than beside it.
    :func:`assert_refusals_identical` derives its field list from
    :class:`~ccf.products.refusal.RefusalEnvelope` itself, so the six members
    this row added are compared with no edit — but a fixture resolver that
    minted nothing would compare six sentinels and prove nothing about them.
    Both references are asserted **non-sentinel** below for that reason.

    They are also the **same** address, and that is a property rather than a
    coincidence: one resolver, two calls at one ``asked_at``, no clock read
    anywhere on the path, and a content-addressed store. Two identical
    determinations converge on one record — which is what makes *"which record
    authorized this?"* have one answer whichever door a caller came through.
    """
    address = assembled.address
    declared = _contract(address)
    resolver = _refusing_and_recording(
        declared,
        store=deployment_store(tmp_path / "refusal-records", REPLAY_ARTIFACT_CLASS),
        tenant=address.tenant,
    )

    in_process = resolver(
        tenant=address.tenant,
        product_class=address.product_class,
        version=address.version,
        perspective=Perspective(principal_id=PRINCIPAL, role=ROLE),
        request=ProductRequest(
            schema_name=address.product_class,
            schema_version=address.version,
            subject=SUBJECT,
            intent=INTENT,
            freshness=FRESHNESS,
            asked_at=ASKED_AT,
            parameters={},
        ),
    )
    is_error, text = _ask_mcp_door(
        tmp_path, address=address, resolver=resolver, parameters={}
    )

    assert is_error is False, text
    decoded = _decode(text)
    over_the_wire = decoded.refusal
    assert over_the_wire is not None
    in_process_envelope = door_refusal(in_process) or pytest.fail(
        "the in-process leg produced no refusal"
    )
    assert_refusals_identical(in_process_envelope, over_the_wire)

    # 24.6-07: the replay reference is INSIDE that identity, and non-sentinel
    # on both sides. Asserted explicitly because a comparison of two sentinels
    # would pass and prove nothing about the field.
    for side, envelope in (
        ("in process", in_process_envelope),
        ("over MCP", over_the_wire),
    ):
        assert envelope.replay_reference != NO_REPLAY_REFERENCE, side
    assert in_process_envelope.replay_reference == over_the_wire.replay_reference
    # And the door reports it, translated to the outcome's own vocabulary.
    assert decoded.replay_ref == over_the_wire.replay_reference


def test_the_mcp_door_carries_the_replay_reference(
    assembled: Any, tmp_path: Path
) -> None:
    """Behaviour 6: ``D-IMPL-148``'s own subject, on the door it was raised about.

    What would fail here: the door serving the vessel and discarding the
    reference beside it, which is what all three shipped doors did and what
    ``WireOutcome.replay_ref`` had already called *"a defect the client seam
    exists to fix"*.

    The vessel is asserted too, and byte-for-byte: the envelope is a frame
    around the producer's bytes, never a re-rendering of them.
    """
    address = assembled.address
    ref = _replay_ref(address)
    is_error, text = _ask_mcp_door(
        tmp_path,
        address=address,
        resolver=_answering(
            ServedProduct(product=assembled.servable.product, replay_ref=ref)
        ),
    )

    assert is_error is False, text
    outcome = _decode(text)
    assert outcome.refusal is None
    assert outcome.replay_ref == ref.uri
    assert outcome.product_json == canonical_bytes(
        assembled.servable.product
    ).decode("utf-8")


def test_both_doors_carry_the_same_replay_reference(
    assembled: Any, tmp_path: Path
) -> None:
    """Behaviour 7: Addendum A's *"both, not one"*, through the real assertion.

    The two doors are passed as callables so the control below substitutes a
    divergent one into **this same** function rather than into a copy of it.
    """
    address = assembled.address
    ref = _replay_ref(address)
    served = ServedProduct(product=assembled.servable.product, replay_ref=ref)
    http_root = tmp_path / "http"
    http_root.mkdir()

    def ask_mcp() -> str | None:
        is_error, text = _ask_mcp_door(
            tmp_path, address=address, resolver=_answering(served)
        )
        assert is_error is False, text
        return _decode(text).replay_ref

    def ask_http() -> str | None:
        response = _ask_http_door(
            http_root, address=address, resolver=_answering(served)
        )
        assert response.status_code == 200, response.text
        return response.headers.get(REPLAY_REF_HEADER)

    assert_both_doors_carry_the_replay_ref(ask_mcp, ask_http)


def test_a_bare_vessel_does_not_cross_either_door(
    assembled: Any, tmp_path: Path
) -> None:
    """Behaviour 8, INVERTED by ``D-IMPL-260`` P-A: a bare vessel does not cross.

    The narrower ``ServableProduct`` carries no reference because nothing
    recorded it, and a door that served it would release a fulfillment with no
    replay behind it. Until this ruling both doors said so by omission and
    served anyway; now both refuse it as the wiring defect it is — the MCP tool
    as its opaque runtime failure, the HTTP route as the typed
    :class:`~ccf.products.door.UngovernedResolverResult` escaping — and the
    same vessel SERVED (``assembled.served``) crosses with its reference on
    both, which the two behaviours above already measure.
    """
    address = assembled.address
    http_root = tmp_path / "http-absent"
    http_root.mkdir()

    is_error, text = _ask_mcp_door(
        tmp_path, address=address, resolver=_answering(assembled.servable)
    )
    assert is_error is True, text
    assert re.fullmatch(
        rf"(Error executing tool [^:\s]+: )?{CCF_FAILURE_PREFIX}:[0-9a-f]{{32}}",
        text.strip(),
    ), text
    assert "ServableProduct" not in text

    with pytest.raises(UngovernedResolverResult, match="bare `ServableProduct`"):
        _ask_http_door(
            http_root, address=address, resolver=_answering(assembled.servable)
        )
def test_the_served_and_refused_shapes_cannot_validate_as_each_other(
    assembled: Any,
) -> None:
    """Behaviour 9: discrimination is **structural**, and never a sniff.

    The ruling's own words. Three checks, and the conjunction is the claim:
    the bare vessel is not a ``DoorOutcome``, so a door that emitted one would
    be caught rather than read as an outcome with missing halves; and the
    vessel and the envelope cannot validate as each other, because both are
    ``extra=forbid`` with disjoint required fields.

    Without this a consumer would have to branch on the presence of a key —
    which is a sniff, and which silently starts answering differently the day
    either contract gains a member.
    """
    vessel = canonical_bytes(assembled.servable.product).decode("utf-8")
    envelope = RefusalEnvelope(
        kind="ttl-refusal",
        reason="ttl",
        key=None,
        detail="expires_at fell outside the window",
        fields={},
        request=_identity(assembled.address),
        pre_assembly_lineage=None,
    )

    with pytest.raises(ValidationError):
        DoorOutcome.model_validate_json(vessel)
    with pytest.raises(ValidationError):
        RefusalEnvelope.model_validate_json(vessel)
    with pytest.raises(ValidationError):
        type(assembled.servable.product).model_validate_json(
            canonical_bytes(envelope).decode("utf-8")
        )


# ---------------------------------------------------------------------------
# The sabotage controls (D-22) — divergent subjects into the real assertions.
# ---------------------------------------------------------------------------


def test_the_identity_assertion_fires_on_a_dropped_kind(
    assembled: Any, tmp_path: Path
) -> None:
    """A refusal that lost its ``kind`` is caught by the **real** assertion.

    ``kind`` is the single most consequential field to lose: constraint (a) of
    the envelope's ruling exists because a consumer that cannot name the kind
    cannot audit the refusal, and a flattened refusal is otherwise a perfectly
    well-formed object.
    """
    address = assembled.address
    honest = RefusalEnvelope(
        kind="ttl-refusal",
        reason="ttl",
        key=None,
        detail="expires_at fell outside the window",
        fields={"max_ttl_seconds": "3600"},
        request=_identity(address),
        pre_assembly_lineage=None,
    )
    flattened = honest.model_copy(update={"kind": "gate-refusal"})

    with pytest.raises(AssertionError, match="kind"):
        assert_refusals_identical(honest, flattened)


@pytest.mark.parametrize(
    "member",
    [
        "replay_reference",
        "policy_bindings",
        "evidence",
        "provenance",
        "disclosure",
        "resource",
    ],
)
def test_the_identity_assertion_fires_on_each_member_24_6_07_added(
    assembled: Any, member: str
) -> None:
    """Each of the six is genuinely compared, one at a time (``24.6-07``).

    :func:`assert_refusals_identical` derives its field list from the type, so
    the six joined the comparison with no edit — and *"joined with no edit"* is
    the kind of claim that is easy to assert and easy to be wrong about. Six
    planted differences, one per member, are what turn it into a measurement.

    Parametrized rather than folded into one test because a single assertion
    over six planted differences passes when **one** of them is caught.
    """
    honest = RefusalEnvelope(
        kind="ttl-refusal",
        reason="ttl",
        key=None,
        detail="expires_at fell outside the window",
        fields={"max_ttl_seconds": "3600"},
        request=_identity(assembled.address),
        pre_assembly_lineage=None,
    )
    planted: dict[str, Any] = {
        "replay_reference": "ccf-artifact://a/replay/1",
        "policy_bindings": (
            ProvenanceSource(kind="artifact", identity="policy.bundle", version="v1"),
        ),
        "evidence": RefusalEvidence(
            operators_invoked=frozenset({"traversal.neighbors"}),
            plan_id="plan-1",
        ),
        "provenance": EffectiveRequest(
            parameters=(),
            guidance=(),
            overrides=(),
            applied=(),
            asked_at=ASKED_AT,
        ),
        "disclosure": "minimal",
        "resource": ResourceRequestIdentity(
            surface="fixture-surface",
            address="ccf-product://fixture/1.0.0",
            tenant_id=assembled.address.tenant,
            determined_at=ASKED_AT,
        ),
    }
    assert set(planted) == set(
        RefusalEnvelope.model_fields
    ) - {
        "kind",
        "reason",
        "key",
        "detail",
        "fields",
        "request",
        "pre_assembly_lineage",
    }, "the planted set must be exactly the six this row added"
    divergent = honest.model_copy(update={member: planted[member]})
    with pytest.raises(AssertionError, match=member):
        assert_refusals_identical(honest, divergent)


def test_the_boundary_assertion_fires_on_each_way_a_door_can_get_it_wrong(
    assembled: Any,
) -> None:
    """Three divergent renderers, three different failures of the real assertion.

    The controls invert with the assertion (``24.6-10``). The first is the
    **pre-ruling door itself**: :func:`~ccf.products.door.door_refusal` returns
    ``None`` for a ``ProductEntitlementRefused`` because that type is outside
    the envelope's vocabulary, which is exactly the shape ``24.5`` shipped and
    ``D-IMPL-256`` replaced — so the old behavior is now a watched failure
    rather than the subject.

    The second and third are the two ways a door could envelope the denial and
    still leak: a kind of its own, which makes *you may not* readable from the
    outside, and an un-withheld ``cause``, which is the internal truth crossing
    at ``minimal``. Each would pass the other two checks.
    """
    address = assembled.address
    identity = _identity(address)

    with pytest.raises(AssertionError, match="nothing at all"):
        assert_governance_is_shelled(lambda refused: door_refusal(refused))

    def own_kind(refused: ProductEntitlementRefused) -> RefusalEnvelope:
        return RefusalEnvelope(
            kind="gate-refusal",
            reason="entitlement",
            key=None,
            detail=refused.message,
            fields={"cause": json.dumps(WITHHELD)},
            request=identity,
            pre_assembly_lineage=None,
        )

    with pytest.raises(AssertionError, match="shared outcome"):
        assert_governance_is_shelled(own_kind)

    def leaking_cause(refused: ProductEntitlementRefused) -> RefusalEnvelope:
        return RefusalEnvelope(
            kind=REFUSAL_KINDS[SubjectUnavailableRefusal],
            reason="subject-unavailable",
            key=None,
            detail=refused.message,
            fields={"cause": json.dumps("unauthorized")},
            request=identity,
            pre_assembly_lineage=None,
        )

    with pytest.raises(AssertionError, match="withheld sentinel"):
        assert_governance_is_shelled(leaking_cause)


def test_the_replay_ref_assertion_fires_on_a_door_that_drops_it() -> None:
    """A door that discards the reference fails the **real** assertion.

    Two halves, because the two failures are different and the second is the
    one that ships silently: a door that emits nothing is caught by the absence
    leg, and two doors that emit *different* references — which is a door
    naming a record that is not the one that authorized the delivery — is
    caught by the equality leg.
    """
    honest = "ccf-artifact://tenant/replay/1"

    with pytest.raises(AssertionError, match="no replay reference"):
        assert_both_doors_carry_the_replay_ref(lambda: honest, lambda: None)

    with pytest.raises(AssertionError, match="property of the decision"):
        assert_both_doors_carry_the_replay_ref(
            lambda: honest, lambda: "ccf-artifact://tenant/replay/2"
        )
