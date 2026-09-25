"""The experience door's three entitlement paths answer with a governed shell.

``24.6-16``. The ruling of record is ``D-IMPL-256`` (3), Dave, verbatim:

    *"That is a delivery-boundary rule, not an egress-door-specific feature.
    … leaving them untouched means 24.6 would knowingly ship another delivery
    seam violating the very architecture the phase exists to establish."*

and its scope, in the same ruling: *"only the three measured entitlement paths
and whatever shared mechanism they require"* — *"not a general experience-server
rewrite."*

Every assertion below is drafted from *what would fail here*:

=========================================  ===================================
Invariant / ruling                         What would fail here
=========================================  ===================================
C-25 (``D-IMPL-256`` (3))                  a governed "you may not" could reach
                                           an external MCP client as a tool
                                           error carrying entitlement prose
C-36 (``D-IMPL-256`` (1), criterion 36)    a denial at this door could be
                                           released with no replay record
                                           behind it, or with a reference that
                                           resolves to nothing
``D-IMPL-256`` (2)                         a door could be built with no
                                           recorder and serve authorized
                                           requests normally, making
                                           auditability contingent on outcome
the sequence principle                     this transport could mint, disclose
                                           or catch — putting MCP back in
                                           charge of replay, which is how the
                                           standing-resource/tool asymmetry
                                           *"simply reappears somewhere else"*
``D-IMPL-253`` am.2 (4)                    the internal error code, or prose
                                           that distinguishes an unauthorized
                                           principal from a nonexistent
                                           subject, could cross the wire
=========================================  ===================================

**In-process rather than over the wire, and the reason is what can be
measured.** The store a denial's ``replay_reference`` resolves in lives in the
serving process; the parent of ``tests/crossproc/test_experience_edge.py``
cannot read the child's, so that file asserts the shell and this one asserts
the record behind it. The audit-plane half of the leak assertion — *the error
code is still there, internally* — is the same story: it is a positive control
for the absence assertions on the wire, and it is only readable here.

**The clock is pinned.** A test whose instants come from the wall cannot tell
*"the audit event and the record read one clock"* from *"they read two clocks a
millisecond apart"*.

**The whole-surface no-transport-mint walk is not here.** This module walks
``runtime/ccf_runtime/mcp/experience.py`` alone. The walk over both transport
trees, with the exactly-one-catch-site assertion and the move-the-mint,
planted-handler and planted-``disclose(`` sabotages, is plan ``24.6-11`` Task 3
in wave 9 — it can only be green once all three doors have landed.

Tenant, principal, role, class and token names are test deployment vocabulary,
meaningful nowhere else (CINV-01 applied to test data).
"""

from __future__ import annotations

import ast
import importlib.util
import json
import pathlib
import sys
import types
from datetime import UTC, datetime
from typing import Any

import anyio
import pytest

from ccf.artifacts.file_store import FileArtifactStore
from ccf.contracts.canonical import canonical_bytes
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.products.entitlement import (
    PRODUCT_ENTITLEMENT_POLICY,
    ProductEntitlementGrant,
    ProductEntitlementPolicy,
    product_entitlement_key,
)
from ccf.products.refusal import (
    NO_REPLAY_REFERENCE,
    RefusalEnvelope,
)
from ccf.products.resolver import ReplayRefusalRecorder
from ccf.projection.plan import Perspective
from ccf.replay.record import (
    NO_ROLE_RESOLVED,
    DecisionReplayRecord,
    ResolutionNotApplicable,
)
from ccf_runtime.authz.delivery_boundary import (
    UnrecordableDeliveryBoundaryError,
)
from ccf_runtime.authz.product_entitlement import (
    ControlPlaneProductEntitlementSource,
)
from ccf_runtime.http_api.errors import (
    ERROR_PRINCIPAL_NOT_ENTITLED,
    ERROR_PRODUCT_CLASS_UNENTITLED,
)
from crossproc.servers.mcp_egress_child import build_servable_product
from ccf_runtime.mcp.experience import ExperienceProductNotServable
from ccf.products.refusal import (
    RequestIdentity,
    SubjectUnavailableRefusal,
    envelope_for,
)
from ccf_runtime.mcp.experience import (
    GET_CONTEXT_TOOL,
    GET_LINEAGE_TOOL,
    _tool_address,
    build_experience_server,
    experience_product_uri,
)
from tests.mcp.guarded_servers import wide_authorizer
from ccf.controlplane.registry import ControlPlaneRegistry
from http_api.composition_authority import (
    deployment_store,
    refusal_recorder,
    register_typed_at_composition,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXPERIENCE_PATH = REPO_ROOT / "runtime/ccf_runtime/mcp/experience.py"
EXPERIENCE_SOURCE = EXPERIENCE_PATH.read_bytes()
TESTS_ROOT = REPO_ROOT / "tests"

#: Test deployment vocabulary.
TENANT = "tenant-experience-channels"
PRINCIPAL = "principal-experience-entitled"
STRANGER = "principal-experience-undeclared"
ROLE = "role-experience-granted"
PRODUCT_CLASS = "class-experience-served"
PRODUCT_VERSION = "1.0.0"
POLICY_VERSION = "1.0.0"
REPLAY_RECORD_CLASS = "ccf.decision-replay-record"
SCOPE = "ccf:experience-channels"
SERVED_LINEAGE = '{"served":"the lineage"}'

#: The one instant every determination below is reached at. Pinned, so the
#: audit event and the replay record of ONE decision cannot merely happen to
#: agree.
DETERMINED_AT = datetime(2026, 5, 12, 9, 30, tzinfo=UTC)

#: The three paths ``D-IMPL-256`` (3) names, enumerated by their surface token
#: so a parametrization drives each on the operand it really has.
RESOURCE_PATH = "the-context-product-resource"
CONTEXT_PATH = "the-get-context-tool"
LINEAGE_PATH = "the-get-lineage-tool"
ENTITLEMENT_PATHS = (RESOURCE_PATH, CONTEXT_PATH, LINEAGE_PATH)


class _Door:
    """One built experience server, with the store its denials land in.

    Composed the way ``tests/crossproc/test_experience_edge.py::_in_process_door``
    composes its own — the shape is copied rather than imported because this
    door registers all three entitlement paths, where that one registers the
    single tool its subject needs.
    """

    def __init__(self, tmp_path: pathlib.Path, *, entitled_class: str = PRODUCT_CLASS) -> None:
        registry = ControlPlaneRegistry()
        register_typed_at_composition(registry, 
            product_entitlement_key(tenant_id=TENANT),
            ProductEntitlementPolicy(
                tenant_id=TENANT,
                policy_version=POLICY_VERSION,
                principals={
                    PRINCIPAL: ProductEntitlementGrant(
                        permitted_schema_names=frozenset({PRODUCT_CLASS}),
                        permitted_roles=frozenset({ROLE}),
                    )
                },
            ),
            PRODUCT_ENTITLEMENT_POLICY,
        )
        self.registry = registry
        self.source = ControlPlaneProductEntitlementSource(
            control_plane=registry, clock=lambda: DETERMINED_AT
        )
        self.store = deployment_store(tmp_path / "replay", REPLAY_RECORD_CLASS)
        self.recorder = refusal_recorder(
            registry,
            store=self.store,
            tenant=TENANT,
            replay_record_class=REPLAY_RECORD_CLASS,
            assembly_mode="algorithmic",
            policy_bundle_pin=None,
            disclosure_level_for=self.source.disclosure_level_for,
        )
        # A REAL gate-admitted vessel, from the shipped fixture assembly, so
        # the served leg crosses `served_answer` the way a deployment's does
        # (`D-IMPL-260` P-B: the resource reads its resolver through the
        # common translation, which admits no stand-in for the vessel).
        self.assembled = build_servable_product(
            database_path=tmp_path / "experience-fabric.sqlite3"
        )
        self.served_product = self.assembled.servable.product
        self.entitled_class = entitled_class
        self.server = build_experience_server(**self.kwargs(tmp_path))

    def kwargs(self, tmp_path: pathlib.Path) -> dict[str, Any]:
        """Every argument the builder takes, so a test can vary exactly one."""

        def resolve_product(
            *,
            tenant: str,
            product_class: str,
            version: str,
            perspective: Perspective,
            request: Any,
        ) -> Any:
            return self.assembled.served

        def provide_context(
            *, tenant: str, entity: str, perspective: Perspective
        ) -> str:
            return json.dumps({"served": entity, "role": perspective.role})

        def provide_lineage() -> str:
            return SERVED_LINEAGE

        def resolve_perspective(
            *, grant: Any, tenant: str, requested_role: str | None
        ) -> Perspective:
            return Perspective(
                principal_id=grant.client_id,
                role=requested_role if requested_role is not None else ROLE,
            )

        return {
            "server_name": "experience-refusal-channels",
            "product_resolver": resolve_product,
            "context_provider": provide_context,
            "lineage_provider": provide_lineage,
            "get_context_description": "served for this test only",
            "get_lineage_description": "served for this test only",
            "entitled_product_class": self.entitled_class,
            "lineage_tenant": TENANT,
            "tool_allowlist": frozenset({GET_CONTEXT_TOOL, GET_LINEAGE_TOOL}),
            "token_verifier": _token_verifier(tmp_path),
            "auth_settings": _auth_settings(),
            "authorizer": wide_authorizer(scopes=(SCOPE,)),
            "entitlement_source": self.source,
            "perspective_resolver": resolve_perspective,
            "refusal_recorder": self.recorder,
        }

    # --- driving the three paths -------------------------------------------

    def ask(self, path: str, *, principal: str, tenant: str = TENANT) -> str:
        """Drive one entitlement path as ``principal`` and return its text."""
        if path == RESOURCE_PATH:
            return _as_principal(
                principal,
                lambda: anyio.run(
                    self.server.read_resource,
                    experience_product_uri(
                        tenant=tenant,
                        product_class=PRODUCT_CLASS,
                        version=PRODUCT_VERSION,
                    ),
                ),
                render=_render_resource,
            )
        if path == CONTEXT_PATH:
            return self.call(GET_CONTEXT_TOOL, {"tenant": tenant, "entity": "any"}, principal)
        return self.call(GET_LINEAGE_TOOL, {}, principal)

    def call(self, tool: str, arguments: dict[str, Any], principal: str) -> str:
        return _as_principal(
            principal,
            lambda: anyio.run(self.server.call_tool, tool, arguments),
            render=_render_tool,
        )

    # --- reading what the door recorded ------------------------------------

    def addresses(self) -> set[str]:
        root = self.store.root
        return (
            {path.name for path in root.iterdir() if len(path.name) == 64}
            if root.exists()
            else set()
        )

    def record_at(self, uri: str) -> DecisionReplayRecord:
        return DecisionReplayRecord.model_validate_json(
            self.store.get(content_address=self.store.resolve_uri(uri=uri))
        )

    def internal(self, record: DecisionReplayRecord) -> RefusalEnvelope:
        return RefusalEnvelope.model_validate_json(
            record.content_generation_path.assembly_refusal
        )

    def audit_text(self) -> str:
        return " | ".join(
            repr(event) for event in self.registry.audit_log.events()
        )


def _token_verifier(tmp_path: pathlib.Path) -> Any:
    from ccf_runtime.mcp.auth import FileTokenSource, SourceBackedTokenVerifier

    tokens = tmp_path / "tokens.json"
    tokens.write_text(
        json.dumps(
            {
                # Both credentials are scoped to this door's one tenant
                # (`SEC-018`), because what these tests vary is ENTITLEMENT —
                # the stranger is a verified caller of the same tenant whom the
                # policy does not grant. A stranger refused for tenancy instead
                # would still go red and would stop testing the subject.
                "entitled": {
                    "client_id": PRINCIPAL,
                    "scopes": [SCOPE],
                    "tenants": [TENANT],
                },
                "stranger": {
                    "client_id": STRANGER,
                    "scopes": [SCOPE],
                    "tenants": [TENANT],
                },
            }
        ),
        encoding="utf-8",
    )
    return SourceBackedTokenVerifier(source=FileTokenSource(path=tokens))


def _auth_settings() -> Any:
    from mcp.server.auth.settings import AuthSettings
    from pydantic import AnyHttpUrl

    return AuthSettings(
        issuer_url=AnyHttpUrl("https://issuer.invalid"),
        resource_server_url=AnyHttpUrl("https://experience.invalid/mcp"),
        required_scopes=[SCOPE],
    )


def _as_principal(principal: str, operation: Any, *, render: Any) -> str:
    """Run ``operation`` with the auth contextvar the middleware would set.

    The bearer middleware is what normally populates it, and an in-process call
    has no request to carry a header. Setting the same contextvar stands in for
    it exactly — nothing is bypassed, because what is under test is the
    *entitlement* decision, which runs on the verified identity however it
    arrived (the ``_call_in_process`` precedent in
    ``tests/crossproc/test_experience_edge.py``).
    """
    from mcp.server.auth.middleware.auth_context import auth_context_var
    from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
    from mcp.server.auth.provider import AccessToken

    from ccf_runtime.mcp.auth import TokenGrant, tenant_claims

    reset = auth_context_var.set(
        AuthenticatedUser(
            AccessToken(
                token="in-process",
                client_id=principal,
                scopes=[SCOPE],
                # The claim the bearer middleware would carry, composed through
                # the shipped renderer rather than spelled here, so this stand-in
                # cannot drift from what a real verification produces
                # (`SEC-018`).
                claims=dict(
                    tenant_claims(
                        TokenGrant(
                            client_id=principal,
                            scopes=(SCOPE,),
                            tenants=frozenset({TENANT}),
                        )
                    )
                ),
            )
        )
    )
    try:
        return render(operation())
    finally:
        auth_context_var.reset(reset)


def _render_resource(result: Any) -> str:
    return "".join(
        contents.content
        for contents in result
        if isinstance(contents.content, str)
    )


def _render_tool(result: Any) -> str:
    if isinstance(result, tuple):
        result = result[0]
    if isinstance(result, dict):
        return json.dumps(result)
    return "".join(block.text for block in result if hasattr(block, "text"))


@pytest.fixture()
def door(tmp_path: pathlib.Path) -> _Door:
    return _Door(tmp_path)


# --- (1) each of the three paths answers with a recorded, disclosed shell ----


@pytest.mark.parametrize("path", ENTITLEMENT_PATHS)
def test_each_entitlement_path_answers_a_denial_with_a_recorded_shell(
    path: str, door: _Door
) -> None:
    """``D-IMPL-256`` (1)/(3) and criterion 36, on each path in turn.

    What would fail here: a path that raised instead of answering; a shell with
    a sentinel reference; a reference that resolves to nothing; a record at an
    instant other than the determination's; a record with no way to say what
    was requested or by whom.

    Driven per path rather than once, because ``D-IMPL-128`` was ruled on
    exactly this failure — one surface on one server behaving unlike its
    neighbour — and a single-path test cannot see it.
    """
    body = door.ask(path, principal=STRANGER)

    shell = RefusalEnvelope.model_validate_json(body)
    assert shell.kind == "subject-unavailable", shell.kind
    # `D-IMPL-253` Q27: the shared outcome, with the internal cause withheld.
    assert shell.fields["cause"] == '"undisclosed"', shell.fields
    assert shell.disclosure == "minimal"

    assert shell.replay_reference != NO_REPLAY_REFERENCE
    record = door.record_at(shell.replay_reference)
    assert record.recorded_at == DETERMINED_AT

    # Dimension 4: who asked, and the role the source DECIDED under — this
    # door's resolver established `ROLE` for a caller that asked for none, and
    # the record carries that rather than a positive-absence claim for a role
    # that did participate (`D-IMPL-260` P-D; never a `None` to interpret).
    assert record.perspective_conditioning.principal_id == STRANGER
    assert record.perspective_conditioning.role == ROLE

    # Dimension 5's internal determination — the truth the shell withheld.
    internal = door.internal(record)
    assert internal.fields["cause"] == '"unauthorized"'
    assert internal.resource is not None
    assert internal.resource.determined_at == DETERMINED_AT
    assert internal.resource.tenant_id == TENANT


@pytest.mark.parametrize(
    ("path", "surface", "version_bearing"),
    [
        (RESOURCE_PATH, "mcp-resource", True),
        (CONTEXT_PATH, "mcp-tool", False),
        (LINEAGE_PATH, "mcp-tool", False),
    ],
)
def test_each_path_records_the_identity_its_own_surface_carries(
    path: str, surface: str, version_bearing: bool, door: _Door
) -> None:
    """The resource-request identity ``D-IMPL-256`` (1) requires, per path.

    Dave: *"the request identity for a standing resource may be a different
    request form, but it still needs enough identity to answer: what resource
    was requested … at what instant"*.

    What would fail here: three doors spelling one surface three ways; a tool
    address invented with a version lane the deployment never named; a
    ``product_version`` of ``None`` recorded on the resource, which DOES carry
    one on the wire. The version claim is asserted in **both** directions in
    one test, because *"the tools carry none"* is only a positive claim if the
    surface that does carry one is shown to record it.
    """
    body = door.ask(path, principal=STRANGER)
    shell = RefusalEnvelope.model_validate_json(body)

    # The identity is RECORDED, and read off the record: below `full` the
    # shell carries none (`D-IMPL-260` P-J — its presence alone told a boundary
    # denial from an assembler's determination).
    assert shell.resource is None
    assert "resource" not in body
    recorded = door.internal(door.record_at(shell.replay_reference))
    assert recorded.resource is not None
    assert recorded.resource.surface == surface

    if path == RESOURCE_PATH:
        assert recorded.resource.address == experience_product_uri(
            tenant=TENANT,
            product_class=PRODUCT_CLASS,
            version=PRODUCT_VERSION,
        )
        assert shell.request.product_version == PRODUCT_VERSION
    else:
        tool = GET_CONTEXT_TOOL if path == CONTEXT_PATH else GET_LINEAGE_TOOL
        assert recorded.resource.address == _tool_address(
            tool=tool, tenant=TENANT, product_class=PRODUCT_CLASS
        )
        # A positive claim, not a gap: these tools address a class, not a lane.
        assert shell.request.product_version is None

    assert version_bearing is (shell.request.product_version is not None)


def test_an_absent_class_reaches_the_caller_as_the_common_shell(
    tmp_path: pathlib.Path,
) -> None:
    """``D-IMPL-260`` P-C at the experience resource.

    An entitled caller addresses a class the deployment's resolver has nothing
    for. Before this pass the resolver's ``ExperienceProductNotServable``
    escaped the handler as a transport error; now it is a governed
    determination — the same ``subject-unavailable`` an assembler reaches for
    a subject nothing resolves — recorded, disclosed and returned as the
    common shell, with the resolver's own statement kept on the record and
    withheld from the wire at this tenant's level.
    """
    door = _Door(tmp_path)

    def absent(**_: Any) -> Any:
        raise ExperienceProductNotServable("nothing is servable at that address")

    door.server = build_experience_server(
        **{**door.kwargs(tmp_path), "product_resolver": absent}
    )

    body = door.ask(RESOURCE_PATH, principal=PRINCIPAL)

    shell = RefusalEnvelope.model_validate_json(body)
    assert shell.kind == "subject-unavailable"
    assert shell.disclosure == "minimal"
    assert shell.fields["cause"] == '"undisclosed"'
    assert "nothing is servable" not in body
    assert "ExperienceProductNotServable" not in body
    assert shell.replay_reference != NO_REPLAY_REFERENCE
    record = door.record_at(shell.replay_reference)
    internal = door.internal(record)
    assert internal.fields["cause"] == '"nonexistent"'
    assert "nothing is servable at that address" in internal.detail
    assert internal.resource is not None
    assert internal.resource.surface == "mcp-resource"
    # Dimension 4: the perspective the caller was entitled under participated.
    assert record.perspective_conditioning.principal_id == PRINCIPAL
    assert record.perspective_conditioning.role == ROLE
    # Dimension 2: no policy decided the absence.
    assert record.policy_bindings.bindings == ()


def test_the_resource_returns_a_resolvers_refusal_as_its_shell(
    tmp_path: pathlib.Path,
) -> None:
    """``D-IMPL-260`` P-B: the resource reads its resolver through the door.

    A resolver that answers with a recorded, disclosed refusal envelope —
    what the SDK's own governed resolver returns — crosses as that shell.
    Before this pass the handler reached for ``.product`` on whatever it was
    handed, so a returned refusal was an ``AttributeError`` here.
    """
    door = _Door(tmp_path)
    minted = door.recorder.record(
        envelope_for(
            SubjectUnavailableRefusal(
                cause="nonexistent",
                detail="no entity resolved for the anchor",
                error_code=None,
            ),
            request=RequestIdentity(
                product_id=PRODUCT_CLASS,
                product_version=PRODUCT_VERSION,
                parameters={},
                temporal_boundary=None,
            ),
        ),
        perspective=Perspective(principal_id=PRINCIPAL, role=ROLE),
        recorded_at=DETERMINED_AT,
        resolution=ResolutionNotApplicable(reason="no-resolution-step"),
        policy_bindings=(),
    )

    def refusing(**_: Any) -> Any:
        return minted

    door.server = build_experience_server(
        **{**door.kwargs(tmp_path), "product_resolver": refusing}
    )

    body = door.ask(RESOURCE_PATH, principal=PRINCIPAL)

    shell = RefusalEnvelope.model_validate_json(body)
    assert shell.kind == "subject-unavailable"
    assert shell.replay_reference == minted.replay_reference


@pytest.mark.parametrize("path", ENTITLEMENT_PATHS)
def test_an_entitled_caller_is_served_and_the_store_does_not_grow(
    path: str, door: _Door
) -> None:
    """The companion serve leg, without which the denial legs prove nothing.

    Two halves. A door that refused everyone would satisfy every assertion
    above, so the served text is asserted **by value**. And a fulfilled
    decision is the resolver's to record, not this door's — a second record
    here would make one decision two — so the store is asserted not to grow,
    with the denial in the same test as its positive control.
    """
    before = door.addresses()

    served = door.ask(path, principal=PRINCIPAL)

    if path == RESOURCE_PATH:
        assert served == canonical_bytes(door.served_product).decode("utf-8")
    elif path == CONTEXT_PATH:
        assert json.loads(served) == {"served": "any", "role": ROLE}
    else:
        assert served == SERVED_LINEAGE
    assert "kind" not in json.loads(served)
    assert door.addresses() == before

    # The counter's positive control: a DENIAL on the same path does add one,
    # so "nothing was written" is a measurement rather than a lister that
    # finds nothing whatever happens.
    door.ask(path, principal=STRANGER)
    assert len(door.addresses() - before) == 1


@pytest.mark.parametrize("path", ENTITLEMENT_PATHS)
def test_the_internal_error_code_stays_in_the_audit_plane(
    path: str, door: _Door
) -> None:
    """``D-IMPL-253`` am.2 (4): the message-text channel, closed and controlled.

    The absence assertion alone is satisfied by a door that decided nothing, so
    the same truth is asserted **present** where it belongs, in two places that
    keep two different halves of it. The internal determination the replay
    record carries keeps the typed ``error_code``; the Control Plane's own
    ``authz_decision`` event keeps *that a deny happened, to whom, at which
    instant*. *"Don't destroy audit truth merely to achieve external
    suppression silence."*

    Measured rather than assumed: the audit event records the **decision**,
    not the code — nothing appends an error code to it — so asserting the code
    there would be asserting against a shape the audit log does not have.
    """
    from ccf_runtime.authz.refusals import ACTION_PRODUCT_RETRIEVE

    body = door.ask(path, principal=STRANGER)

    assert ERROR_PRINCIPAL_NOT_ENTITLED not in body
    assert STRANGER not in body

    shell = RefusalEnvelope.model_validate_json(body)
    internal = door.internal(door.record_at(shell.replay_reference))
    assert internal.fields["error_code"] == f'"{ERROR_PRINCIPAL_NOT_ENTITLED}"'

    denials = [
        event
        for event in door.registry.audit_log.events()
        if getattr(event, "authz_action_id", None) == ACTION_PRODUCT_RETRIEVE
        and event.actor == STRANGER
        and event.resolved is False
    ]
    assert len(denials) == 1, door.audit_text()
    # One clock: the audit event and the replay record of ONE determination.
    assert denials[0].occurred_at == DETERMINED_AT
    assert door.record_at(shell.replay_reference).recorded_at == DETERMINED_AT


def test_two_denials_that_differ_only_in_cause_are_indistinguishable(
    tmp_path: pathlib.Path,
) -> None:
    """D-27 at this door: the shell's SHAPE is not a channel either.

    An undeclared principal and an entitled principal asking for a class
    outside the grant are two different internal determinations. At the safe
    default a consumer must not be able to tell them apart — not by the cause,
    not by the fields present, not by the prose.

    What would fail here: a disclosure step that withheld a *value* but left a
    key behind, or that let one internal ``detail`` through.
    """
    door = _Door(tmp_path / "a")
    other = _Door(tmp_path / "b", entitled_class=f"{PRODUCT_CLASS}-not-this-one")

    undeclared = RefusalEnvelope.model_validate_json(
        door.ask(CONTEXT_PATH, principal=STRANGER)
    )
    unentitled_class = RefusalEnvelope.model_validate_json(
        other.ask(CONTEXT_PATH, principal=PRINCIPAL)
    )

    # The two internal determinations really do differ — the vacuity guard.
    assert (
        other.internal(
            other.record_at(unentitled_class.replay_reference)
        ).fields["error_code"]
        == f'"{ERROR_PRODUCT_CLASS_UNENTITLED}"'
    )
    assert (
        door.internal(door.record_at(undeclared.replay_reference)).fields[
            "error_code"
        ]
        == f'"{ERROR_PRINCIPAL_NOT_ENTITLED}"'
    )

    assert undeclared.kind == unentitled_class.kind
    assert undeclared.reason == unentitled_class.reason
    assert undeclared.detail == unentitled_class.detail
    assert set(undeclared.fields) == set(unentitled_class.fields)
    assert undeclared.fields == unentitled_class.fields

    # `D-IMPL-258` (2): the third door, on the one leg its fixture can reach.
    # These are two ENTITLEMENT determinations under two different registered
    # policies, so before the ruling each shell pinned its own policy at its
    # own version and the pair was distinguishable by the pin alone. Both are
    # normalized below `full` now, so neither shell says which policy decided.
    #
    # **The nonexistent leg is not reachable at this fixture and is not
    # faked.** This door's three paths all produce `cause="unauthorized"`
    # (``24.6-16``); the unauthorized-versus-nonexistent pair is measured where
    # both causes exist — at the HTTP door and at the MCP egress door, which is
    # the pair Dave's *"prove equivalence at HTTP and MCP"* names.
    assert undeclared.policy_bindings == ()
    assert unentitled_class.policy_bindings == ()

    # And the audit plane keeps what the shells no longer show — the vacuity
    # guard for the two assertions above, which a door that had simply stopped
    # pinning anything would also satisfy. Both determinations DID pin an
    # entitlement policy; only the disclosed shells are empty.
    #
    # Measured, not assumed: the two pins are the same artifact at the same
    # version here, because the two doors register policies whose content is
    # identical — the class each grant permits is a request-side fact at this
    # fixture. So this pair proves the suppression is a disclosure act rather
    # than an erasure; it cannot prove the *pin* was a channel, and the
    # unauthorized-versus-nonexistent pairs at the two product doors are where
    # that is proved.
    internal_undeclared = door.internal(door.record_at(undeclared.replay_reference))
    internal_unentitled = other.internal(
        other.record_at(unentitled_class.replay_reference)
    )
    assert internal_undeclared.policy_bindings, internal_undeclared
    assert internal_unentitled.policy_bindings, internal_unentitled


# --- (2) the construction-time check -----------------------------------------


def test_the_door_refuses_to_build_without_a_recorder(
    tmp_path: pathlib.Path,
) -> None:
    """``D-IMPL-256`` (2): this builder always entitles, so it always records.

    Dave: *"a door configured to make governed determinations without the
    ability to record them is not a valid governed door."* What would fail
    here: a builder that accepted ``None`` and failed only on a denial, which
    would *"make auditability contingent on outcome"*.
    """
    door = _Door(tmp_path)
    kwargs = door.kwargs(tmp_path)

    for supplied in (None, object()):
        broken = dict(kwargs)
        broken["refusal_recorder"] = supplied
        with pytest.raises(UnrecordableDeliveryBoundaryError) as refused:
            build_experience_server(**broken)
        assert "build_experience_server" in str(refused.value)
        assert "refusal_recorder=" in str(refused.value)

    # The vacuity guard: the same kwargs WITH a conforming recorder build, so
    # the two raises above are about the recorder rather than about anything
    # else this argument set happens to be missing.
    assert build_experience_server(**kwargs) is not None


def test_the_recorder_check_runs_before_the_allowlist_check(
    tmp_path: pathlib.Path,
) -> None:
    """The order, asserted with a kwargs set that would trip BOTH.

    The recorder's requiredness is the only unconditional check on this
    builder — every other one is conditional on what the allowlist admits — so
    it runs first, and a door misconfigured two ways reports the structural
    defect rather than the typo. Asserted rather than assumed, on the D-03
    ordering precedent in ``tests/crossproc/test_experience_edge.py``.

    ``UnrecordableDeliveryBoundaryError`` subclasses ``ValueError``, so the
    type alone is not the assertion: the allowlist entry is also asserted
    absent from the message, which is what a D-01 refusal would name.
    """
    door = _Door(tmp_path)
    broken = door.kwargs(tmp_path)
    broken["refusal_recorder"] = None
    broken["tool_allowlist"] = frozenset({"not_a_tool"})

    with pytest.raises(UnrecordableDeliveryBoundaryError) as refused:
        build_experience_server(**broken)
    assert "not_a_tool" not in str(refused.value)

    # The other order is reachable and does fire — so the assertion above is
    # about precedence rather than about the D-01 check having been deleted.
    supplied = door.kwargs(tmp_path)
    supplied["tool_allowlist"] = frozenset({"not_a_tool"})
    with pytest.raises(ValueError) as unknown:
        build_experience_server(**supplied)
    assert "not_a_tool" in str(unknown.value)


#: The check the sabotage below removes. Asserted present, exactly once, before
#: mutating — so a reflow makes this control fail loudly rather than silently
#: mutate nothing.
RECORDER_CHECK = """    recorder = recorded_boundary(
        refusal_recorder=refusal_recorder, builder="build_experience_server"
    )
"""

#: What the scratch copy runs instead: the keyword accepted and never checked.
SKIPPED_CHECK = "    recorder = refusal_recorder  # SABOTAGE\n"

#: The whole governed block the direct-entitlement sabotage replaces on ONE
#: path — ``get_context``. The full block rather than its head, because
#: ``govern_entitlement`` takes four arguments ``entitled_perspective`` does
#: not: swapping only the callee raises ``TypeError``, and a control that fires
#: on a signature mismatch measures nothing about the ruling.
GOVERNED_CALL = """            decided = govern_entitlement(
                grant=verified_grant(),
                tenant=tenant,
                product_class=context_class,
                # No version on the wire, and saying so is the positive claim:
                # this tool addresses a class, not a lane.
                product_version=None,
                requested_role=None,
                # What the caller supplied — the request identity's
                # parameters, never a value this module chose.
                parameters={"entity": entity},
                asked_at=None,
                surface=SURFACE_MCP_TOOL,
                address=_tool_address(
                    tool=GET_CONTEXT_TOOL,
                    tenant=tenant,
                    product_class=context_class,
                ),
                entitlement_source=entitlement_source,
                perspective_resolver=perspective_resolver,
                refusal_recorder=recorder,
            )
            if isinstance(decided, RefusalEnvelope):
                return canonical_bytes(decided).decode("utf-8")
"""

#: The pre-``D-IMPL-256`` body, in the shape ``1022ad59`` shipped: the
#: resolution order run at the transport, so the refusal raises through it with
#: no determination, no record and no shell.
DIRECT_CALL = """            decided = entitled_perspective(  # SABOTAGE
                grant=verified_grant(),
                tenant=tenant,
                product_class=context_class,
                requested_role=None,
                entitlement_source=entitlement_source,
                perspective_resolver=perspective_resolver,
            )
"""

#: The sabotage needs a SECOND mutation, and that is itself a measurement: the
#: shipped module no longer imports `entitled_perspective` at all, so the
#: pre-ruling body cannot be reinstated by editing one line. Without this the
#: scratch raises `NameError` and the control would be asserting that a typo
#: fails rather than that the old shape leaks.
SHIPPED_IMPORT = "    verified_grant,\n)"
SABOTAGED_IMPORT = "    entitled_perspective,  # SABOTAGE\n    verified_grant,\n)"


def _scratch_experience(
    tmp_path: pathlib.Path, *, name: str, mutations: tuple[tuple[str, str], ...]
) -> types.ModuleType:
    """A copy of ``experience.py`` with the named mutations, importable alone."""
    source = EXPERIENCE_SOURCE.decode("utf-8")
    mutated = source
    for old, new in mutations:
        assert mutated.count(old) == 1, (
            f"the sabotage for {name} is not where it looks: {old!r}"
        )
        mutated = mutated.replace(old, new, 1)
    assert mutated != source

    path = tmp_path / f"{name}.py"
    path.write_text(mutated, encoding="utf-8")
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:  # pragma: no cover - a broken scratch is a red test
        sys.modules.pop(name, None)
        raise
    return module


def test_a_builder_that_skips_the_recorder_check_is_red_sabotage(
    tmp_path: pathlib.Path,
) -> None:
    """Remove the check and a recorder-less door builds — the control.

    Without this, ``test_the_door_refuses_to_build_without_a_recorder`` would
    pass against a builder whose typed error came from somewhere else entirely.
    """
    scratch = _scratch_experience(
        tmp_path,
        name="experience_skipping_the_recorder_check",
        mutations=((RECORDER_CHECK, SKIPPED_CHECK),),
    )
    door = _Door(tmp_path)
    broken = door.kwargs(tmp_path)
    broken["refusal_recorder"] = None

    built = scratch.build_experience_server(**broken)
    assert built is not None, (
        "the sabotage did not remove the check, so it is not a control"
    )

    # And the REAL builder refuses the same arguments.
    with pytest.raises(UnrecordableDeliveryBoundaryError):
        build_experience_server(**broken)


# --- (3) the direct-entitlement sabotage -------------------------------------


def test_a_path_that_entitles_directly_raises_with_prose_red_sabotage(
    tmp_path: pathlib.Path,
) -> None:
    """The pre-ruling body, on one path, and it is exactly the defect.

    ``D-IMPL-256`` (3) names the failure it closes: a governed determination
    reaching an MCP client as a tool error. A handler that calls
    ``entitled_perspective`` directly instead of the governed step raises
    ``ProductEntitlementRefused`` through the transport — ``isError`` True with
    the entitlement's prose and its typed code — and mints nothing.

    Both halves are asserted, because either alone is weak: the sabotage's
    denial leaks and does not record, and the real door's does neither.
    """
    scratch = _scratch_experience(
        tmp_path,
        name="experience_entitling_directly",
        mutations=(
            (SHIPPED_IMPORT, SABOTAGED_IMPORT),
            (GOVERNED_CALL, DIRECT_CALL),
        ),
    )
    door = _Door(tmp_path)
    sabotaged = scratch.build_experience_server(**door.kwargs(tmp_path))

    before = door.addresses()
    with pytest.raises(Exception) as leaked:
        _as_principal(
            STRANGER,
            lambda: anyio.run(
                sabotaged.call_tool,
                GET_CONTEXT_TOOL,
                {"tenant": TENANT, "entity": "any"},
            ),
            render=_render_tool,
        )
    # The raise itself is half the defect: a governed determination arriving as
    # a transport failure. The prose it carries is the other half.
    assert ERROR_PRINCIPAL_NOT_ENTITLED in _causes(leaked.value)
    assert door.addresses() == before, "the sabotaged path minted a record"

    # The real door, same inputs: a governed shell, and one record.
    body = door.ask(CONTEXT_PATH, principal=STRANGER)
    shell = RefusalEnvelope.model_validate_json(body)
    assert ERROR_PRINCIPAL_NOT_ENTITLED not in body
    assert shell.replay_reference != NO_REPLAY_REFERENCE
    assert len(door.addresses() - before) == 1


def _causes(error: BaseException, _seen: frozenset[int] = frozenset()) -> str:
    """Every message in an exception's cause chain and group tree, joined.

    The ``tests/crossproc/test_experience_edge.py`` idiom: anyio renders a task
    group's failure with the real cause nested below, so asserting on the
    top-level string would assert on anyio's wording rather than on the
    refusal — the difference between *"it failed"* and *"it refused for the
    stated reason"*.
    """
    if id(error) in _seen:
        return ""
    seen = _seen | {id(error)}
    parts = [f"{type(error).__name__}: {error}"]
    if isinstance(error, BaseExceptionGroup):
        parts.extend(_causes(inner, seen) for inner in error.exceptions)
    for chained in (error.__cause__, error.__context__):
        if chained is not None:
            parts.append(_causes(chained, seen))
    return " | ".join(part for part in parts if part)


def test_no_sabotage_edits_the_real_source_tree() -> None:
    """Every control above mutates a copy under ``tmp_path``."""
    assert EXPERIENCE_PATH.read_bytes() == EXPERIENCE_SOURCE
    source = EXPERIENCE_SOURCE.decode("utf-8")
    assert RECORDER_CHECK in source
    assert GOVERNED_CALL in source
    assert SHIPPED_IMPORT in source
    assert SKIPPED_CHECK not in source
    assert DIRECT_CALL not in source
    assert SABOTAGED_IMPORT not in source
    # The shipped module does not reach the pre-ruling seam at all — the
    # positive claim behind the second mutation above.
    assert "entitled_perspective" not in source


# --- (4) this transport mints, discloses and catches nothing -----------------

#: What a transport must never call. ``record`` and ``record_refusal`` are the
#: minting seams; ``disclose``/``disclose_only`` are the Disclosure layer's;
#: ``write_replay_record`` is the writer's.
FORBIDDEN_CALLS = frozenset(
    {"record", "disclose_only", "disclose", "write_replay_record", "record_refusal"}
)

#: What a transport must never catch: catching it puts the transport back in
#: charge of building the shell and minting the record.
FORBIDDEN_HANDLER = "ProductEntitlementRefused"


def transport_mint_violations(path: pathlib.Path) -> list[str]:
    """Every forbidden call or handler in ONE module, by AST.

    A guard on the walked module's **direct** calls and handlers, not on what
    its imports do: ``ccf_runtime.authz`` legitimately records, discloses and
    catches, which is the whole point of the sequence. An AST walk rather than
    a grep, because a grep would be satisfied by a docstring that merely says
    the module mints nothing — and would be tripped by one that names a seam.

    The walk over BOTH transport trees, with the exactly-one-catch-site
    assertion and its three sabotages, is plan ``24.6-11`` Task 3 (wave 9): it
    can only be green once all three doors have landed, and this one is green
    on its own door's evidence in the meantime.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in FORBIDDEN_CALLS:
                violations.append(f"{path.name}:{node.lineno} {ast.unparse(node.func)}")
        elif isinstance(node, ast.ExceptHandler) and node.type is not None:
            if FORBIDDEN_HANDLER in ast.unparse(node.type):
                violations.append(
                    f"{path.name}:{node.lineno} except {ast.unparse(node.type)}"
                )
    return violations


def test_the_experience_transport_never_mints(tmp_path: pathlib.Path) -> None:
    """Criterion 36 at this door: the transport encodes and decides nothing.

    Dave, on why: *"Replay belongs to the governed determination, not to HTTP
    or MCP. That matters because otherwise the standing-resource/tool asymmetry
    simply reappears somewhere else."*

    The planted-call control is what makes the empty list a measurement rather
    than a walker that finds nothing whatever it is pointed at.
    """
    assert transport_mint_violations(EXPERIENCE_PATH) == []

    source = EXPERIENCE_SOURCE.decode("utf-8")
    # Anchored on the preceding newline: an eight-space needle is a SUBSTRING
    # of the twelve-space one inside the tool handlers, so an unanchored
    # `count` reports two and the assertion below would trip on its own
    # indentation rather than on a reflow.
    needle = "\n        decided = govern_entitlement(\n"
    assert source.count(needle) == 1, "the plant is not where it looks"
    planted = tmp_path / "experience_that_mints.py"
    planted.write_text(
        source.replace(
            needle,
            "\n        refusal_recorder.record()  # PLANTED" + needle,
            1,
        ),
        encoding="utf-8",
    )

    reported = transport_mint_violations(planted)
    assert reported, "the walker reports nothing it is shown, so it is not a gate"
    assert any("record" in finding for finding in reported), reported
    # And the real tree is untouched.
    assert EXPERIENCE_PATH.read_bytes() == EXPERIENCE_SOURCE


def test_every_experience_door_in_the_tree_binds_a_recorder() -> None:
    """``D-IMPL-256`` (2) as a tree fact, not a per-call-site habit.

    Every ``build_experience_server(`` call under ``tests/`` that actually
    builds a door passes ``refusal_recorder=``. By AST over the call's keywords
    rather than ``grep -c``, because a grep counts a mention in a comment and
    cannot tell one call site from three.

    Two modules name the symbol without calling it —
    ``tests/test_surface_shape_capture.py`` (a captured shape) and
    ``tests/invariants/test_mcp_role_separation.py`` (an identity comparison) —
    and are excluded by name. The roster is printed and asserted non-empty, so
    a walk that stopped finding call sites fails here instead of passing.
    """
    excluded = {"test_surface_shape_capture.py", "test_mcp_role_separation.py"}
    bound: list[str] = []
    unbound: list[str] = []

    for path in sorted(TESTS_ROOT.rglob("*.py")):
        if path.name in excluded:
            continue
        text = path.read_text(encoding="utf-8")
        if "build_experience_server(" not in text:
            continue
        for node in ast.walk(ast.parse(text)):
            if not isinstance(node, ast.Call):
                continue
            name = node.func
            if not (
                isinstance(name, ast.Name)
                and name.id == "build_experience_server"
            ):
                continue
            site = f"{path.relative_to(TESTS_ROOT)}:{node.lineno}"
            keywords = {keyword.arg for keyword in node.keywords}
            # `**kwargs` carries the recorder from `_builder_kwargs`, which is
            # itself asserted below.
            if "refusal_recorder" in keywords or None in keywords:
                bound.append(site)
            else:
                unbound.append(site)

    assert not unbound, f"experience doors built with no recorder: {unbound}"
    assert bound, "no build_experience_server( call site was found at all"
    # The `**kwargs` sites are only sound because the two kwargs builders bind
    # the seam themselves — asserted here so the `None in keywords` branch
    # above cannot become a hole. `_builder_kwargs` supplies it as a dict KEY
    # rather than a keyword, which is why the needle is the name and not
    # `refusal_recorder=`.
    for builder in (
        TESTS_ROOT / "crossproc" / "test_experience_edge.py",
        TESTS_ROOT / "crossproc" / "servers" / "mcp_experience_child.py",
    ):
        assert "refusal_recorder" in builder.read_text(encoding="utf-8"), builder
