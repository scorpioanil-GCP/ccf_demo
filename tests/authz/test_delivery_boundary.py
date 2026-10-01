"""The governed delivery-boundary step — one call, and nothing left to decide.

``24.6-08``. The rulings of record are ``D-IMPL-256`` and ``D-IMPL-254``, and
the invariant this module exists to make measurable is criterion 36:

    *"Every governed determination that crosses a CCF delivery boundary —
    fulfilled or refused, tool or resource, authorized or denied — must reach
    the replay writer before the response is released. A delivery boundary
    unable to satisfy that invariant is unavailable, not partially governed."*

Every assertion below is drafted from *what would fail here*:

=========================================  ===================================
Invariant / ruling                         What would fail here
=========================================  ===================================
criterion 36 (``D-IMPL-256``)              a denial could be released with no
                                           replay record behind it
``D-IMPL-256`` (1) — the resource identity a standing-resource denial could be
                                           recorded with no way to say WHAT was
                                           requested, or WHEN
``D-IMPL-256`` (2) — fail at construction  a boundary with no recorder could
                                           serve normally and fail only on a
                                           denial, making auditability
                                           contingent on outcome
``D-IMPL-98`` — one injected clock         the audit event and the replay
                                           record of ONE decision could carry
                                           two different instants
D-34 — *"under which policy"*              dimension 2 could pin the deploying
                                           tenant's policy on a denial another
                                           tenant's policy decided
``D-IMPL-253`` Q27 — one shared outcome    a denial could cross as a kind a
                                           nonexistent subject cannot share
=========================================  ===================================

The clock is **pinned** throughout: a test whose instants come from the wall
cannot tell "the two halves read one clock" from "the two halves read two
clocks a millisecond apart".

Tenant, principal, role, class and address names are test deployment
vocabulary, meaningful nowhere else (CINV-01 applied to test data).
"""

from __future__ import annotations

import importlib.util
import ast
import pathlib
import sys
import types
from datetime import UTC, datetime
from typing import Any

import pytest

from ccf.artifacts.file_store import FileArtifactStore
from ccf.controlplane.audit import AuthzDecisionAuditEvent
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.products.disclosure import DisclosureDecision
from ccf.products.entitlement import (
    PRODUCT_ENTITLEMENT_POLICY,
    ProductEntitlementGrant,
    ProductEntitlementPolicy,
    product_entitlement_key,
)
from ccf.products.refusal import (
    NO_REPLAY_REFERENCE,
    RefusalEnvelope,
    SubjectUnavailableRefusal,
)
from ccf.products.resolver import ReplayRefusalRecorder
from ccf.projection.plan import Perspective
from ccf.replay.record import (
    NO_FABRIC_READ,
    NO_PRODUCT_ADDRESS,
    NO_REQUEST_RESOLUTION,
    NO_ROLE_RESOLVED,
    DecisionReplayRecord,
    ResolutionNotApplicable,
)
from ccf_runtime.authz.delivery_boundary import (
    SURFACE_HTTP_ROUTE,
    SURFACE_MCP_RESOURCE,
    UnrecordableDeliveryBoundaryError,
    govern_absence,
    govern_entitlement,
    recorded_boundary,
)
from ccf_runtime.authz.product_entitlement import (
    ControlPlaneProductEntitlementSource,
    TokenGrant,
)
from ccf_runtime.authz.refusals import ACTION_PRODUCT_RETRIEVE
from ccf_runtime.http_api.errors import ERROR_PRODUCT_POLICY_ABSENT
from http_api.composition_authority import (
    deployment_store,
    refusal_recorder,
    register_typed_at_composition,
)

BOUNDARY_PATH = (
    pathlib.Path(__file__).parent.parent.parent
    / "runtime/ccf_runtime/authz/delivery_boundary.py"
)
BOUNDARY_SOURCE = BOUNDARY_PATH.read_bytes()

#: Test deployment vocabulary.
TENANT = "tenant-delivery-boundary"
FOREIGN_TENANT = "tenant-delivery-boundary-foreign"
UNREGISTERED_TENANT = "tenant-delivery-boundary-unregistered"
PRINCIPAL = "caller-at-the-boundary"
ROLE = "role-granted"
PRODUCT_CLASS = "class-permitted"
OTHER_PRODUCT_CLASS = "class-not-permitted"
PRODUCT_VERSION = "1.0.0"
POLICY_VERSION = "1.0.0"
FOREIGN_POLICY_VERSION = "2.0.0"
ADDRESS = f"ccf-product://{PRODUCT_CLASS}/{PRODUCT_VERSION}/subject-a"
REPLAY_RECORD_CLASS = "ccf.decision-replay-record"

#: The one instant every determination below is reached at. Pinned, because the
#: whole subject is that the audit event and the replay record read ONE clock.
DETERMINED_AT = datetime(2026, 4, 7, 11, 15, tzinfo=UTC)
LATER = datetime(2026, 4, 7, 11, 16, tzinfo=UTC)


def _grant(client_id: str = PRINCIPAL) -> TokenGrant:
    return TokenGrant(client_id=client_id, scopes=())


def _policy(
    *,
    tenant: str = TENANT,
    version: str = POLICY_VERSION,
    principals: str = PRINCIPAL,
) -> ProductEntitlementPolicy:
    return ProductEntitlementPolicy(
        tenant_id=tenant,
        policy_version=version,
        principals={
            principals: ProductEntitlementGrant(
                permitted_schema_names=frozenset({PRODUCT_CLASS}),
                permitted_roles=frozenset({ROLE}),
            )
        },
    )


def _registry() -> ControlPlaneRegistry:
    """One registry holding the deployment's policy and a foreign tenant's.

    The foreign tenant's policy names a DIFFERENT principal, so a request under
    it is refused by a policy that genuinely decided — which is what makes the
    D-34 pin assertion measure something.
    """
    registry = ControlPlaneRegistry()
    register_typed_at_composition(registry, 
        product_entitlement_key(tenant_id=TENANT),
        _policy(),
        PRODUCT_ENTITLEMENT_POLICY,
    )
    register_typed_at_composition(registry, 
        product_entitlement_key(tenant_id=FOREIGN_TENANT),
        _policy(
            tenant=FOREIGN_TENANT,
            version=FOREIGN_POLICY_VERSION,
            principals="somebody-else",
        ),
        PRODUCT_ENTITLEMENT_POLICY,
    )
    return registry


class _Resolver:
    """The deployment's role-derivation seam: derives the role from the grant."""

    def __call__(
        self, *, grant: TokenGrant, tenant: str, requested_role: str | None
    ) -> Perspective:
        return Perspective(
            principal_id=grant.client_id, role=requested_role or ROLE
        )


class _FixedRoleResolver:
    """A resolver that conditions every caller under one deployment role."""

    def __call__(
        self, *, grant: TokenGrant, tenant: str, requested_role: str | None
    ) -> Perspective:
        return Perspective(principal_id=grant.client_id, role=ROLE)


class _SubstitutingResolver:
    """A resolver that proposes a principal the caller is not.

    The subject-conflict path: `entitled_perspective` refuses this BEFORE any
    entitlement source is consulted, so no policy decided it.
    """

    def __call__(
        self, *, grant: TokenGrant, tenant: str, requested_role: str | None
    ) -> Perspective:
        return Perspective(principal_id="somebody-else", role=ROLE)


class _Fixture:
    """One booted delivery boundary: a registry, a source, a store, a recorder."""

    def __init__(self, tmp_path: pathlib.Path, *, clock: Any) -> None:
        self.registry = _registry()
        self.source = ControlPlaneProductEntitlementSource(
            control_plane=self.registry, clock=clock
        )
        self.store = deployment_store(tmp_path / "artifacts", REPLAY_RECORD_CLASS)
        # Built with the keyword list `build_governed_resolver` uses for its
        # own, so the door's recorder and the resolver's are the same shape —
        # one writer, one store, one record form ("do not create second-class
        # replay").
        self.recorder = refusal_recorder(
            self.registry,
            store=self.store,
            tenant=TENANT,
            replay_record_class=REPLAY_RECORD_CLASS,
            assembly_mode="algorithmic",
            policy_bundle_pin=None,
            disclosure_level_for=self.source.disclosure_level_for,
        )
        self.resolver: Any = _Resolver()

    def govern(self, **overrides: Any) -> Any:
        arguments: dict[str, Any] = {
            "grant": _grant(),
            "tenant": TENANT,
            "product_class": PRODUCT_CLASS,
            "product_version": PRODUCT_VERSION,
            "requested_role": ROLE,
            "parameters": {"threshold": 1},
            "asked_at": DETERMINED_AT,
            "surface": SURFACE_HTTP_ROUTE,
            "address": ADDRESS,
            "entitlement_source": self.source,
            "perspective_resolver": self.resolver,
            "refusal_recorder": self.recorder,
        }
        arguments.update(overrides)
        return govern_entitlement(**arguments)

    def record_at(self, uri: str) -> DecisionReplayRecord:
        return DecisionReplayRecord.model_validate_json(
            self.store.get(content_address=self.store.resolve_uri(uri=uri))
        )

    def internal(self, record: DecisionReplayRecord) -> RefusalEnvelope:
        return RefusalEnvelope.model_validate_json(
            record.content_generation_path.assembly_refusal
        )

    def addresses(self) -> set[str]:
        root = self.store.root
        return (
            {path.name for path in root.iterdir() if len(path.name) == 64}
            if root.exists()
            else set()
        )

    def authz_events(self) -> list[AuthzDecisionAuditEvent]:
        return [
            event
            for event in self.registry.audit_log.events()
            if isinstance(event, AuthzDecisionAuditEvent)
            and event.authz_action_id == ACTION_PRODUCT_RETRIEVE
        ]


@pytest.fixture()
def fixture(tmp_path: pathlib.Path) -> _Fixture:
    return _Fixture(tmp_path, clock=lambda: DETERMINED_AT)


# --- (1) the entitled path writes nothing -----------------------------------


def test_an_entitled_request_returns_a_perspective_and_records_nothing(
    fixture: _Fixture,
) -> None:
    """A fulfilled decision is the resolver's to record, not the door's.

    What would fail here: a step that minted at every determination, which
    would make one decision two records and put a refusal-shaped artifact in
    front of a decision that was never refused.
    """
    before = fixture.addresses()

    outcome = fixture.govern()

    assert isinstance(outcome, Perspective), type(outcome)
    assert outcome.principal_id == PRINCIPAL
    assert outcome.role == ROLE
    assert fixture.addresses() == before
    # The counter's positive control: a DENIAL through the same fixture does
    # add one, so "nothing was written" is a measurement rather than a lister
    # that finds nothing whatever happens.
    fixture.govern(product_class=OTHER_PRODUCT_CLASS)
    assert len(fixture.addresses() - before) == 1


# --- (2) a denial is minted, disclosed, and resolvable -----------------------


def test_a_denial_is_recorded_at_the_determination_instant_and_resolves(
    fixture: _Fixture,
) -> None:
    """Criterion 36 at the boundary, whole.

    What would fail here: a denial released with a sentinel reference, or with
    a reference that resolves to nothing, or recorded at an instant other than
    the one the determination was reached at.
    """
    shell = fixture.govern(product_class=OTHER_PRODUCT_CLASS)

    assert isinstance(shell, RefusalEnvelope), type(shell)
    assert shell.kind == "subject-unavailable"
    # `D-IMPL-253` Q27: the consumer sees the shared outcome, and the internal
    # cause is withheld at the safe default.
    assert shell.fields["cause"] == '"undisclosed"'
    assert shell.disclosure == "minimal"

    assert shell.replay_reference != NO_REPLAY_REFERENCE
    record = fixture.record_at(shell.replay_reference)

    # The determination's own instant, on its record. The resource identity
    # does not cross below `full` (`D-IMPL-260` P-J: its presence alone told a
    # boundary denial from an assembler's determination); the record keeps it.
    assert record.recorded_at == DETERMINED_AT
    assert shell.resource is None

    # Dimension 4: the principal that asked, and the role it asked under.
    assert record.perspective_conditioning.principal_id == PRINCIPAL
    assert record.perspective_conditioning.role == ROLE
    # Dimension 1: a denial at the boundary read nothing.
    assert record.context_fabric_snapshot.store_watermark == NO_FABRIC_READ
    # Dimension 5: no product, and the INTERNAL determination.
    assert record.content_generation_path.product_content_address == (
        NO_PRODUCT_ADDRESS
    )
    internal = fixture.internal(record)
    assert internal.fields["cause"] == '"unauthorized"'
    assert internal.resource is not None
    assert internal.resource.determined_at == DETERMINED_AT
    assert internal.resource.surface == SURFACE_HTTP_ROUTE
    assert internal.resource.address == ADDRESS
    assert internal.resource.tenant_id == TENANT

    # Dimension 2: the policy that DECIDED, at the version the audit names.
    events = fixture.authz_events()
    assert events, "the source appended no authz decision"
    audited = events[-1]
    assert audited.occurred_at == DETERMINED_AT, (
        "the audit event and the replay record must be stamped from ONE clock"
    )
    pins = {
        binding.key: binding.version for binding in record.policy_bindings.bindings
    }
    assert pins == {product_entitlement_key(tenant_id=TENANT): audited.version}


def test_the_role_recorded_is_the_one_the_source_decided_under(
    fixture: _Fixture,
) -> None:
    """``D-IMPL-260`` P-D: the role that PARTICIPATED, never the one asked for.

    The caller asked for no role; the deployment's resolver established one
    (its default) and the source decided against it. Dimension 4 carries that
    role — the determination's own — rather than the positive-absence claim
    that was recorded here before, which said no role was established when one
    had been. A `None` never reaches the recorder either way.

    What would fail here: a record that reads the CALLER's request for the
    role (absent here, so `NO_ROLE_RESOLVED` substituted for a role that did
    participate), or one that records a role the source never saw.
    """
    fixture.resolver = _Resolver()
    shell = fixture.govern(
        product_class=OTHER_PRODUCT_CLASS, requested_role=None
    )

    assert isinstance(shell, RefusalEnvelope)
    record = fixture.record_at(shell.replay_reference)
    assert record.perspective_conditioning.role == ROLE
    assert record.perspective_conditioning.role != NO_ROLE_RESOLVED


def test_a_requested_role_the_resolver_replaced_is_not_the_one_recorded(
    fixture: _Fixture,
) -> None:
    """The other half of P-D: the request is not the determination.

    A resolver that maps every caller onto one role — a deployment whose roles
    are derived from the grant, not asked for — decides under that role
    whatever was requested; the record must say what was decided under.
    """
    fixture.resolver = _FixedRoleResolver()
    shell = fixture.govern(
        product_class=OTHER_PRODUCT_CLASS, requested_role="role-the-caller-asked-for"
    )

    assert isinstance(shell, RefusalEnvelope)
    record = fixture.record_at(shell.replay_reference)
    assert record.perspective_conditioning.role == ROLE


# --- (2b) the foreign-tenant cases: dimension 2 names who DECIDED ------------


def test_a_foreign_tenants_denial_pins_that_tenants_policy(
    fixture: _Fixture,
) -> None:
    """D-34, *"under which policy"*, on the case that would go wrong silently.

    What would fail here: dimension 2 pinning the DEPLOYMENT's tenant policy on
    a denial another tenant's policy decided. That record would name a policy
    that never ran, and an examiner reconstructing the decision would resolve
    the wrong artifact and get a different answer.
    """
    shell = fixture.govern(tenant=FOREIGN_TENANT)

    assert isinstance(shell, RefusalEnvelope), type(shell)
    record = fixture.record_at(shell.replay_reference)
    pins = {
        binding.key: binding.version for binding in record.policy_bindings.bindings
    }
    foreign_key = product_entitlement_key(tenant_id=FOREIGN_TENANT)
    own_key = product_entitlement_key(tenant_id=TENANT)
    # The registry is the denominator: the pin must be the version the registry
    # actually holds for THAT key, read here rather than assumed from the
    # artifact's own `policy_version` (registration is content-addressed, so
    # the two are different strings and only one is what replay resolves by).
    foreign_version, _ = fixture.registry.resolve_latest(foreign_key)
    own_version, _ = fixture.registry.resolve_latest(own_key)
    assert pins == {foreign_key: foreign_version}
    # NOT the deployment's own tenant key, and the two are genuinely different
    # — so "the right key" is a measurement rather than a coincidence.
    assert own_key not in pins
    assert foreign_version != own_version
    # The RECORDED resource identity names the tenant the pin belongs to; the
    # shell carries none below `full` (`D-IMPL-260` P-J).
    assert shell.resource is None
    assert fixture.internal(record).resource is not None
    assert fixture.internal(record).resource.tenant_id == FOREIGN_TENANT


def test_an_unregistered_tenants_denial_names_the_absence_and_pins_nothing(
    fixture: _Fixture,
) -> None:
    """A measured absence is recorded as an absence, never as a policy.

    ``D-IMPL-253`` amendment 2 (1) and ``D-IMPL-26``:
    :class:`~ccf.products.provenance.ProvenanceSource` refuses an ``artifact``
    source with no version by construction, so *"the key resolved nothing"* is
    unrepresentable as a pin. It is recorded where it IS representable — the
    internal determination's own typed code and message, and the resource
    identity's tenant, from which the key is a pure derivation.

    What would fail here: an empty dimension 2 with nothing else saying why,
    which would read exactly like a decision no policy governed.
    """
    shell = fixture.govern(tenant=UNREGISTERED_TENANT)

    assert isinstance(shell, RefusalEnvelope), type(shell)
    record = fixture.record_at(shell.replay_reference)
    assert record.policy_bindings.bindings == ()

    internal = fixture.internal(record)
    assert internal.fields["error_code"] == f'"{ERROR_PRODUCT_POLICY_ABSENT}"'
    consulted = product_entitlement_key(tenant_id=UNREGISTERED_TENANT)
    assert consulted in internal.detail
    assert internal.resource is not None
    assert internal.resource.tenant_id == UNREGISTERED_TENANT
    assert consulted == product_entitlement_key(
        tenant_id=internal.resource.tenant_id
    )
    # And the consumer learns none of it: the code is withheld at the safe
    # default, so an unregistered tenant and a refused role look identical.
    assert shell.fields["error_code"] == '"undisclosed"'


# --- 24.7-04: a boundary denial states that resolution never began ----------


REFUSED_BEFORE_RESOLUTION = ResolutionNotApplicable(
    reason="refused-before-resolution"
)


def _resolution_state_of(record: DecisionReplayRecord) -> ResolutionNotApplicable:
    rendered = record.policy_bindings.request_resolution
    assert rendered != NO_REQUEST_RESOLUTION, rendered
    return ResolutionNotApplicable.model_validate_json(rendered)


def test_an_entitlement_denial_states_it_was_refused_before_resolution_began(
    fixture: _Fixture,
) -> None:
    """``D-IMPL-264`` D-09 and D-10 at the door: an entitlement denial is
    decided before any resolver runs, and its record SAYS so — the typed
    marker with the reason ``refused-before-resolution`` on dimension 2,
    never the legacy sentinel and never an inferred absence.

    What would fail here: a denial whose dimension 2 read exactly like a
    record whose caller dropped the resolution (the sentinel), or a
    marker with the wrong reason (``no-resolution-step`` is the direct
    validator's claim, not the door's).
    """
    shell = fixture.govern(product_class=OTHER_PRODUCT_CLASS)
    assert isinstance(shell, RefusalEnvelope), type(shell)

    record = fixture.record_at(shell.replay_reference)
    assert _resolution_state_of(record) == REFUSED_BEFORE_RESOLUTION
    assert _resolution_state_of(record).reason == "refused-before-resolution"


def test_an_absence_denial_states_it_was_refused_before_resolution_began(
    fixture: _Fixture,
) -> None:
    """The same claim on the other boundary denial (``D-IMPL-260`` P-C):
    the class the deployment does not serve is refused before resolution
    could begin, and the record states that with its reason.
    """
    shell = govern_absence(
        grant=_grant(),
        tenant=TENANT,
        product_class=PRODUCT_CLASS,
        product_version=PRODUCT_VERSION,
        parameters={"threshold": 1},
        asked_at=DETERMINED_AT,
        surface=SURFACE_HTTP_ROUTE,
        address=ADDRESS,
        perspective=Perspective(principal_id=PRINCIPAL, role=ROLE),
        absent=LookupError("nothing servable at that address (fixture)"),
        entitlement_source=fixture.source,
        refusal_recorder=fixture.recorder,
    )
    assert isinstance(shell, RefusalEnvelope), type(shell)
    assert shell.kind == "subject-unavailable"
    assert shell.replay_reference != NO_REPLAY_REFERENCE

    record = fixture.record_at(shell.replay_reference)
    assert record.policy_bindings.bindings == ()
    assert _resolution_state_of(record) == REFUSED_BEFORE_RESOLUTION


# --- (3) the subject-conflict path is a recorded decision now ----------------


def test_the_subject_conflict_path_is_recorded_with_no_entitlement_pin(
    fixture: _Fixture,
) -> None:
    """The path no audit covered before.

    `entitled_perspective` refuses a substituted principal BEFORE any source is
    consulted, so the reference source appends no ``authz_decision`` event for
    it — this was a governed determination with no trace at all. It is a
    recorded decision now, and dimension 2 correctly names NO policy, because
    none was asked.

    What would fail here: either half — a conflict released without a record,
    or a record pinning a policy that was never consulted.
    """
    fixture.resolver = _SubstitutingResolver()
    before = len(fixture.authz_events())

    shell = fixture.govern()

    assert isinstance(shell, RefusalEnvelope), type(shell)
    assert shell.kind == "subject-unavailable"
    record = fixture.record_at(shell.replay_reference)
    assert record.recorded_at == DETERMINED_AT
    assert record.policy_bindings.bindings == ()
    # Dimension 4: no role of the CALLER's was established — the resolved
    # perspective belongs to somebody else — and the record says so
    # positively rather than carrying the substituted identity's role
    # (`D-IMPL-260` P-D).
    assert record.perspective_conditioning.role == NO_ROLE_RESOLVED
    assert record.perspective_conditioning.principal_id == PRINCIPAL
    # Still no authz audit event, because no source was consulted — which is
    # exactly why the replay record is the only trace and has to exist.
    assert len(fixture.authz_events()) == before


# --- (4) the standing-resource shape -----------------------------------------


def test_a_standing_resource_denial_carries_the_identity_the_ruling_requires(
    fixture: _Fixture,
) -> None:
    """``D-IMPL-256`` (1): the resource form, with no ProductRequest at all.

    Dave: *"the request identity for a standing resource may be a different
    request form, but it still needs enough identity to answer: what resource
    was requested, by whom/perspective, at what instant, under which policy,
    and why fulfillment was refused."* All five, measured here.

    What would fail here: *"a replay hole based on transport shape"* — a
    resource denial recorded thinner than a tool denial, or not at all.
    """
    shell = fixture.govern(
        product_class=OTHER_PRODUCT_CLASS,
        asked_at=None,
        parameters={},
        surface=SURFACE_MCP_RESOURCE,
    )

    assert isinstance(shell, RefusalEnvelope), type(shell)
    assert shell.request.temporal_boundary is None
    assert shell.request.parameters == {}
    # Below `full` the shell carries no resource identity (`D-IMPL-260` P-J).
    assert shell.resource is None

    record = fixture.record_at(shell.replay_reference)
    # (1) what resource, (2) at what instant — on the RECORDED resource identity.
    internal = fixture.internal(record)
    assert internal.resource is not None
    assert internal.resource.surface == SURFACE_MCP_RESOURCE
    assert internal.resource.surface == "mcp-resource"
    assert internal.resource.address == ADDRESS
    assert internal.resource.determined_at == DETERMINED_AT
    # (3) by whom — dimension 4. (4) under which policy — dimension 2.
    assert record.perspective_conditioning.principal_id == PRINCIPAL
    assert record.policy_bindings.bindings != ()
    # (5) why fulfillment was refused — dimension 5's internal determination.
    assert internal.fields["cause"] == '"unauthorized"'


# --- (5) determinism ---------------------------------------------------------


def test_two_identical_denials_at_one_instant_are_one_address(
    tmp_path: pathlib.Path,
) -> None:
    """Same inputs, same instant, same content address; move the clock and it moves.

    What would fail here: a record carrying anything the determination did not
    determine — a wall-clock read, an ordering counter — which would make two
    replays of one decision two different artifacts.
    """
    pinned = _Fixture(tmp_path / "a", clock=lambda: DETERMINED_AT)
    first = pinned.govern(product_class=OTHER_PRODUCT_CLASS)
    second = pinned.govern(product_class=OTHER_PRODUCT_CLASS)
    assert isinstance(first, RefusalEnvelope)
    assert isinstance(second, RefusalEnvelope)
    assert first.replay_reference == second.replay_reference

    moved = _Fixture(tmp_path / "b", clock=lambda: LATER)
    third = moved.govern(product_class=OTHER_PRODUCT_CLASS)
    assert isinstance(third, RefusalEnvelope)
    assert third.replay_reference != first.replay_reference


# --- (6) the construction-time check -----------------------------------------


def test_a_boundary_with_no_recorder_is_refused_at_construction(
    fixture: _Fixture,
) -> None:
    """``D-IMPL-256`` (2). The typed error, named once, and it names the builder.

    What would fail here: a boundary that built cleanly with no recorder,
    served authorized requests normally and failed only on a denial — which
    would *"make auditability contingent on outcome"* and would let
    unauthorized and nonexistent requests diverge merely because a door was
    misconfigured.
    """
    with pytest.raises(UnrecordableDeliveryBoundaryError) as absent:
        recorded_boundary(refusal_recorder=None, builder="build_egress_server")
    assert "build_egress_server" in str(absent.value)
    assert "refusal_recorder=" in str(absent.value)

    with pytest.raises(UnrecordableDeliveryBoundaryError) as wrong:
        recorded_boundary(refusal_recorder=object(), builder="create_app")
    assert "create_app" in str(wrong.value)
    assert "refusal_recorder=" in str(wrong.value)

    # A conforming recorder comes back unchanged — the vacuity guard. Without
    # it the two raises above would pass against a function that refused
    # everything.
    assert (
        recorded_boundary(
            refusal_recorder=fixture.recorder, builder="create_app"
        )
        is fixture.recorder
    )


# --- (7) the recorder-skipping sabotage --------------------------------------


#: The return the sabotage replaces — ``govern_entitlement``'s, named by the
#: comment that precedes only it. Asserted present, exactly once, before
#: mutating, so a reflow makes this control fail loudly rather than silently
#: mutate nothing. The preceding lines are part of the anchor because
#: ``D-IMPL-345`` added a second minting call to this module
#: (``govern_dereference``'s), and a control that sabotaged whichever one it
#: happened to find first would measure a different function on a later edit.
MINTING_RETURN = (
    "        # The mint AND the disclosure, both inside the seam and in that order.\n"
    "        # Nothing is disclosed before it is recorded, and a failed append\n"
    "        # propagates rather than releasing an unrecorded response.\n"
    "        return refusal_recorder.record(\n"
)
SKIPPING_RETURN = "        return envelope  # SABOTAGE\n"


def _scratch_boundary(tmp_path: pathlib.Path) -> types.ModuleType:
    """A copy of ``delivery_boundary.py`` whose denial branch skips the recorder."""
    source = BOUNDARY_SOURCE.decode("utf-8")
    assert source.count(MINTING_RETURN) == 1, (
        "the minting call is not where the sabotage looks"
    )
    # An UNREACHABLE mint left in place, rather than a deletion: the mutation
    # is one inserted line, so a reader of the scratch can see exactly what was
    # skipped and the parenthesised call below stays syntactically whole.
    mutated = source.replace(MINTING_RETURN, SKIPPING_RETURN + MINTING_RETURN)
    assert mutated != source

    path = tmp_path / "boundary_skipping_the_recorder.py"
    path.write_text(mutated, encoding="utf-8")
    spec = importlib.util.spec_from_file_location(
        "boundary_skipping_the_recorder", path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["boundary_skipping_the_recorder"] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:  # pragma: no cover - a broken scratch is a red test
        sys.modules.pop("boundary_skipping_the_recorder", None)
        raise
    return module


def test_a_denial_that_skips_the_recorder_is_red_sabotage(
    tmp_path: pathlib.Path, fixture: _Fixture
) -> None:
    """Return the envelope without minting and the resolve predicate fails.

    T-24.6-57, and it is the defect the checker found three times: a governed
    determination that occurs without reaching the replay writer. The shell it
    hands back looks entirely well-formed — same kind, same reason, same fields
    — and carries the sentinel reference, which resolves to nothing.
    """
    scratch = _scratch_boundary(tmp_path)

    leaked = scratch.govern_entitlement(
        grant=_grant(),
        tenant=TENANT,
        product_class=OTHER_PRODUCT_CLASS,
        product_version=PRODUCT_VERSION,
        requested_role=ROLE,
        parameters={},
        asked_at=DETERMINED_AT,
        surface=SURFACE_HTTP_ROUTE,
        address=ADDRESS,
        entitlement_source=fixture.source,
        perspective_resolver=fixture.resolver,
        refusal_recorder=fixture.recorder,
    )
    assert isinstance(leaked, RefusalEnvelope)
    assert leaked.kind == "subject-unavailable"
    assert leaked.replay_reference == NO_REPLAY_REFERENCE, (
        "the sabotage did not skip the mint, so it is not a control"
    )
    with pytest.raises(Exception):
        fixture.store.resolve_uri(uri=leaked.replay_reference)

    # And the REAL module mints for the same inputs.
    real = fixture.govern(product_class=OTHER_PRODUCT_CLASS, parameters={})
    assert isinstance(real, RefusalEnvelope)
    assert real.replay_reference != NO_REPLAY_REFERENCE
    assert fixture.record_at(real.replay_reference).recorded_at == DETERMINED_AT


def test_no_sabotage_edits_the_real_source_tree() -> None:
    """The control above mutates a copy under ``tmp_path``."""
    assert BOUNDARY_PATH.read_bytes() == BOUNDARY_SOURCE
    source = BOUNDARY_SOURCE.decode("utf-8")
    assert MINTING_RETURN in source
    assert SKIPPING_RETURN not in source


# --- (8) the module reads exactly one clock, and it is the source's ---------


def test_the_module_reads_one_clock_and_it_is_the_entitlement_sources() -> None:
    """``D-IMPL-98``: injected, never read.

    An AST walk rather than a grep, because a grep over prose would be
    satisfied by a docstring that merely *says* no clock is read. What would
    fail here: a `datetime.now` or a `time.time` anywhere in the module, or a
    second `.clock()` call — which would let the audit event and the replay
    record of one decision carry two instants.
    """
    tree = ast.parse(BOUNDARY_SOURCE.decode("utf-8"))
    wall_clock: list[str] = []
    clock_calls = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        function = node.func
        if isinstance(function, ast.Attribute):
            if function.attr in {"now", "utcnow", "time", "monotonic"}:
                wall_clock.append(ast.unparse(function))
            if function.attr == "clock":
                clock_calls += 1
    assert not wall_clock, wall_clock
    assert clock_calls == 1, (
        f"expected exactly one `.clock()` call, found {clock_calls}"
    )
    # The positive control: the one call is on the entitlement source.
    assert "entitlement_source.clock()" in BOUNDARY_SOURCE.decode("utf-8")


def test_a_naive_determination_instant_is_refused(
    tmp_path: pathlib.Path,
) -> None:
    """A clock with no offset replays differently on every host (``D-IMPL-38``).

    What would fail here: a determination recorded at an instant whose offset
    is the deciding host's local configuration.
    """
    naive = _Fixture(
        tmp_path, clock=lambda: datetime(2026, 4, 7, 11, 15)  # noqa: DTZ001
    )
    with pytest.raises(ValueError) as caught:
        naive.govern(product_class=OTHER_PRODUCT_CLASS)
    assert "UTC offset" in str(caught.value)


def test_the_shared_outcome_is_the_kind_a_nonexistent_subject_also_carries(
    fixture: _Fixture,
) -> None:
    """``D-IMPL-253`` Q27, at the boundary.

    What would fail here: a denial crossing as an entitlement-shaped kind, at
    which point a nonexistent subject and an unauthorized principal would be
    distinguishable on the wire by the kind alone — before disclosure was even
    consulted.
    """
    shell = fixture.govern(product_class=OTHER_PRODUCT_CLASS)
    assert isinstance(shell, RefusalEnvelope)

    from ccf.products.refusal import REFUSAL_KINDS

    assert shell.kind == REFUSAL_KINDS[SubjectUnavailableRefusal]
    assert shell.reason == "subject-unavailable"

    record = fixture.record_at(shell.replay_reference)
    decision = DisclosureDecision.model_validate_json(
        record.content_generation_path.disclosure_decision
    )
    assert decision.internal_kind == decision.external_kind == "subject-unavailable"


# --- `D-IMPL-358` step 5 section F: the question's instant bounds the record ---

#: Distinct from :data:`DETERMINED_AT` ON PURPOSE. Every pre-existing control in
#: this module passes ``asked_at=DETERMINED_AT``, so `recorded_at=determined_at`
#: and `recorded_at=asked_at` are the same assertion there and neither could ever
#: fail. A control that agrees by coincidence is not a control.
QUESTION_ASKED_AT = datetime(2026, 4, 7, 9, 0, tzinfo=UTC)


def test_F_govern_entitlement_bounds_the_record_at_the_QUESTION(
    fixture: Any,
) -> None:
    """F. `recorded_at` is the question's instant; `served_at` is the live one.

    `D-IMPL-358` step 5 section F. These are two different statements about one
    determination and the record carries both: dimension 1's boundary is *the
    moment the question was asked as-of*, and the live instant travels beside it.
    Collapsing them moves a refusal's graph boundary onto whenever the door
    happened to run, which is a different question than the one that was asked.
    """
    assert QUESTION_ASKED_AT != DETERMINED_AT, "the premise of this control moved"
    # The same way this module's own controls reach the refusal path: a resolver
    # that substitutes the principal is refused before any source is consulted.
    fixture.resolver = _SubstitutingResolver()

    shell = fixture.govern(asked_at=QUESTION_ASKED_AT)
    assert isinstance(shell, RefusalEnvelope), type(shell)

    record = fixture.record_at(shell.replay_reference)
    assert record.recorded_at == QUESTION_ASKED_AT, (
        "the record's boundary moved onto the door's clock — this refusal now "
        "claims to have been asked at an instant nobody asked at"
    )
    assert record.content_generation_path.served_at == DETERMINED_AT


def test_F_govern_absence_bounds_the_record_at_the_QUESTION(
    fixture: Any,
) -> None:
    """F, the absence path. Same two statements, same separation."""
    shell = govern_absence(
        grant=_grant(),
        tenant=TENANT,
        product_class=PRODUCT_CLASS,
        product_version=PRODUCT_VERSION,
        parameters={"threshold": 1},
        asked_at=QUESTION_ASKED_AT,
        surface=SURFACE_HTTP_ROUTE,
        address=ADDRESS,
        perspective=Perspective(principal_id=PRINCIPAL, role=ROLE),
        absent=LookupError("nothing servable at that address (fixture)"),
        entitlement_source=fixture.source,
        refusal_recorder=fixture.recorder,
    )
    record = fixture.record_at(shell.replay_reference)
    assert record.recorded_at == QUESTION_ASKED_AT
    assert record.content_generation_path.served_at == DETERMINED_AT


def test_F_a_surface_with_no_question_instant_falls_back_to_the_determination(
    fixture: Any,
) -> None:
    """The other half, and the reason the fallback is not a synonym.

    A governed surface that genuinely has no ``asked_at`` keeps the ruled
    resource-form boundary (`D-IMPL-256` (1)). Without this half the repair above
    could be read as *"always use asked_at"*, which would refuse to record a
    surface that legitimately has none.
    """
    fixture.resolver = _SubstitutingResolver()

    shell = fixture.govern(asked_at=None)
    assert isinstance(shell, RefusalEnvelope), type(shell)
    record = fixture.record_at(shell.replay_reference)
    assert record.recorded_at == DETERMINED_AT
    assert record.content_generation_path.served_at == DETERMINED_AT
