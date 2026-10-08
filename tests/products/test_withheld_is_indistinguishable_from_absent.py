"""SEC-020 — a PROJECTION-level withheld subject is indistinguishable from a nonexistent one.

Ruling of record: ``D-IMPL-370`` (and ``D-IMPL-368``/``D-IMPL-369``), question
Q12 (a) — *constant-fill*: a Π-withheld subject renders exactly as a
nonexistent one; debt, emptiness and the TTL anchor are not computed for it,
and non-withheld subjects are untouched. The row is
``docs/superpowers/specs/2026-10-05-remaining-rows-exploit-tests.md`` § SEC-020.

What was measured before this module existed
--------------------------------------------
A Policy-OPERATOR withhold is already indistinguishable
(``tests/products/test_policy_emptied_view_disclosure.py``): the operator
empties the view, and debt, the empty finding and the anchor are computed from
the view. The leak is one level up. A projection conditioned on who asks can
return the payload a missing subject gets while the operator view still holds
the subject, and the served vessel then differs from a nonexistent subject's
at ``computed_empty``, ``debt.debt``, ``debt.factors.freshness``,
``debt.scorers`` and ``debt.signal`` — every one of them computed from a view
the consumer was told nothing about. For a ``from_entity_freshness`` class the
anchor reads the withheld subject's observation instant as well, so the
withheld subject is SERVED while the nonexistent one is REFUSED.

The standard
------------
Equality, path for path, of ``ServedProduct.product.model_dump(mode="json")``
(the sibling's ``_diff_paths``), with nothing removed: the vessel carries no
subject echo (the sibling module measures that), so no path is legitimately
subject-caused.

The rule, as finally ruled (``D-IMPL-371``): the withheld vessel is EXACTLY the
vessel the same plan yields re-executed WITHOUT THE REQUEST SEED — the walk an
identifier that names nothing gets by construction (walk starts are the union
of the plan's seed classes and the request seed, `GQ-11`, and a nonexistent
identifier's seed matches nothing). The withheld subject's own records stay in
that view if and only if a class seed reaches them. Measured history: an EMPTY
view (round 1) created a serve-versus-refuse oracle on a class-seeded fabric;
MASKING the subject's records (round 2) left a residual whenever the subject's
evidence was fresher or staler than its siblings'. The five controls Dave set
as preconditions of integration are named in the test docstrings, (1)–(5).

The control the mechanism must not over-reach into
--------------------------------------------------
A projection whose answer is legitimately empty for an ADMITTED subject, and
that raises no signal, keeps its real debt and finding (``D-IMPL-242``
amendment 1: the finding is a positive statement about the view). A withhold
is never inferred from an empty payload; only the typed signal on
:class:`ccf.projection.plan.ProjectionOutput` enters the constant-fill branch.

Every domain value here is fixture vocabulary (CINV-01, CLAUDE.md §11).
"""

from __future__ import annotations

import pathlib
from collections.abc import Iterator, Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

import pytest

from ccf.contracts.canonical import content_hash
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.deployment import load_and_boot
from ccf.graph.protocols import GraphView
from ccf.halflife.assessment import NO_SOURCE_REFRESH_RECENCY
from ccf.controlplane.artifacts import HalfLifeEntry, HalfLifeTable
from ccf.products.constraints import ReferencePolicyConstraintResolver
from ccf.products.debt_scorer import AssemblyDebtScorer, DeclaredFactor
from ccf.products.entitlement import product_entitlement_key
from ccf.products.refusal import RefusalEnvelope
from ccf.products.request import ProductRequest
from ccf.products.resolver import GovernedResolver, ReplayRefusalRecorder
from ccf.projection.plan import Perspective, ProjectionOutput
from ccf.replay.serve import ServedProduct
from ccf.signal.envelope import SignalEnvelope
from ccf.products.composite import ADMITTED_CHILD_CONTRACT_CLASS
from tests.composition import (
    composition_replay_mint,
    declare_wide_temporal_boundary,
    declaring_store,
)
from tests.deployment.conftest import (
    ARTIFACT_SET,
    HALF_LIFE_KEY,
    RESOLUTION_SPEC_KEY,
    POLICY_BUNDLE_KEY,
    POLICY_PARAMS_KEY,
    PRODUCT_CLASS_KEY,
    TENANT,
    TRAVERSAL_KEY,
    manifest_document,
    write_artifact,
)
from tests.products.test_evidence_derived_debt import DECLARED, profile
from tests.products.test_policy_emptied_view_disclosure import _diff_paths
from tests.products.test_resolver_seam import (
    ASKED_AT,
    MAX_TTL_SECONDS,
    PERSPECTIVE,
    PRODUCT_CLASS,
    PRODUCT_VERSION,
    QUERY_PIN_CLASS,
    REPLAY_RECORD_CLASS,
    REQUEST_CONTRACT_CLASS_ID,
    REQUEST_CONTRACT_DOCUMENT,
    REQUEST_CONTRACT_KEY,
    THRESHOLD_PARAMETER,
)

# --- fixture vocabulary --------------------------------------------------------

#: The two anchors a product class may declare (``ccf.products.expiry``).
FROM_DECISION = "from_decision"
FROM_ENTITY_FRESHNESS = "from_entity_freshness"

#: The account the projection WITHHOLDS from this principal: admitted by the
#: Policy operator, present in the view, and not answered by Π.
WITHHELD_REF = "acct-withheld"

#: An admitted account Π answers EMPTY for, with no signal — the control the
#: constant-fill branch must not reach.
BLANK_REF = "acct-blank"

#: A second admitted account, so the shared-fabric shape holds more than the
#: withheld subject.
OTHER_REF = "acct-other"

#: Accounts nothing was ever ingested for.
MISSING_REF = "acct-missing"

#: Fixture instants. Every claim is ingested before the question; the source
#: observed it half an hour before the decision instant, so an evidence-anchored
#: expiry is inside the window the resolver below declares.
INGESTED_AT = datetime(2026, 3, 2, 11, 0, tzinfo=UTC)
OBSERVED_AT = datetime(2026, 3, 2, 11, 30, tzinfo=UTC)
SERVED_AT = datetime(2026, 3, 2, 12, 7, tzinfo=UTC)

#: The fixture's TTL window. Equal to the sibling's ceiling so an
#: evidence-anchored product (observed 11:30) is still alive at 12:07.
WINDOW_SECONDS = MAX_TTL_SECONDS

#: The entity class the fixture's resolution spec mints — the observation type
#: the debt scorer decays and the anchor reads. A fixture calibration.
OBSERVATION_TYPE = "account"
HALF_LIFE_SECONDS = 3600

#: The plan: the Policy operator and the typed neighborhood walk.
REQUIRED_OPERATORS = ["policy.principal-subgraph", "traversal.typed-neighborhood"]


def _uri(account_ref: str) -> str:
    """The entity URI the fixture's resolution spec mints for ``account_ref``."""
    return f"account://{content_hash({'account_ref': account_ref})}"


WITHHELD = _uri(WITHHELD_REF)
BLANK = _uri(BLANK_REF)
OTHER = _uri(OTHER_REF)
MISSING = _uri(MISSING_REF)


def _table_document() -> dict[str, Any]:
    """One ``valid-from`` row for the class this fabric holds, so both anchors resolve."""
    return {
        "semver": "1.0.0",
        "entries": {
            OBSERVATION_TYPE: {
                "half_life_seconds": HALF_LIFE_SECONDS,
                "decay_driver": "fixture-driver",
                "supersession_event": "fixture-supersession",
                "decay_basis": "valid-from",
            }
        },
    }


def _table() -> HalfLifeTable:
    document = _table_document()
    return HalfLifeTable(
        semver=document["semver"],
        entries={
            key: HalfLifeEntry(**row) for key, row in document["entries"].items()
        },
    )


def _envelope(account_ref: str) -> SignalEnvelope:
    """One admitted claim about ``account_ref``, dated by its source."""
    return SignalEnvelope.model_validate(
        {
            "tenant_id": TENANT,
            "envelope_id": f"envelope-{account_ref}",
            "source": {"system_id": "fixture-system"},
            "ingestion_timestamp": INGESTED_AT.isoformat().replace("+00:00", "Z"),
            "observed_time": OBSERVED_AT.isoformat().replace("+00:00", "Z"),
            "raw_payload": {
                "account_ref": account_ref,
                "classification": "fixture-open",
                "label": f"label-{account_ref}",
            },
        }
    )


# --- the projection under test -------------------------------------------------


def _withhold(*, plan_id: str) -> ProjectionOutput:
    """What Π returns for a subject it withholds from this principal.

    The payload is exactly the one it returns for a subject it cannot see —
    the empty mapping — and the output carries the typed withheld signal.
    """
    return ProjectionOutput(plan_id=plan_id, payload={}, withheld=True)


class _SubjectScopedProjection:
    """A Π that answers for the request's subject only, and withholds some.

    ``withhold`` are subjects this principal may not be told about: Π raises the
    typed signal for them. ``blank`` are admitted subjects Π answers EMPTY for
    WITHOUT the signal — a legitimately empty answer, the control.
    """

    def __init__(
        self,
        *,
        required: tuple[str, ...],
        request: ProductRequest,
        withhold: frozenset[str],
        blank: frozenset[str],
    ) -> None:
        self._required = required
        self._request = request
        self._withhold = withhold
        self._blank = blank

    @property
    def plan_id(self) -> str:
        return PRODUCT_CLASS

    def required_operators(self) -> tuple[str, ...]:
        return self._required

    def invoke(
        self,
        *,
        view: GraphView,
        operator_outputs: Mapping[str, Any],
        perspective: Perspective,
        temporal_boundary: datetime,
    ) -> ProjectionOutput:
        subject = self._request.subject
        if subject in self._withhold:
            return _withhold(plan_id=self.plan_id)
        if subject in self._blank:
            return ProjectionOutput(plan_id=self.plan_id, payload={})
        answered = sorted(
            record.claim.entity_uri
            for record in view.entities
            if record.claim.entity_uri == subject
        )
        return ProjectionOutput(
            plan_id=self.plan_id,
            payload={"accounts": answered} if answered else {},
        )


# --- the booted fixture ----------------------------------------------------------

#: How the plan's walk starts. ``class``: the fixture's own traversal, seeded on
#: the account class, so every account in the fabric is a walk start whatever
#: the question names (a CLASS-SEEDED plan). ``subject``: the traversal is
#: seeded on a class this fabric never holds, so the only walk start is the
#: request seed (a SUBJECT-SEEDED plan). The second class is declared in the
#: resolution spec so the boot-time producibility check (R-10) accepts it.
CLASS_SEEDED = "class"
SUBJECT_SEEDED = "subject"
UNHELD_CLASS = "fixture-branch"
_UNHELD_RULE = {
    "match_key": "branch_ref",
    "entity_class": UNHELD_CLASS,
    "identity_keys": ["branch_ref"],
    "attribute_keys": ["label"],
}


def _boot(
    tmp_path: pathlib.Path,
    *,
    name: str,
    ttl_anchor: str,
    envelopes: Sequence[SignalEnvelope],
    seeding: str = CLASS_SEEDED,
) -> Any:
    """The sibling's boot, with the class's anchor, the λ_c table and the seeding stated.

    Single-writer ingestion (``fabric.handle.worker.ingest``) is the only way
    anything reaches the graph. Test-side document variants only (CINV-01).
    """
    root = tmp_path / name
    root.mkdir()
    for key, filename, _class_id, _role, _registration, document in ARTIFACT_SET:
        if key == PRODUCT_CLASS_KEY:
            document = {
                **document,
                "required_operator_keys": REQUIRED_OPERATORS,
                "ttl_anchor": ttl_anchor,
            }
        if key == HALF_LIFE_KEY:
            document = _table_document()
        if seeding == SUBJECT_SEEDED and key == RESOLUTION_SPEC_KEY:
            document = {**document, "entity_rules": [*document["entity_rules"], _UNHELD_RULE]}
        if seeding == SUBJECT_SEEDED and key == TRAVERSAL_KEY:
            document = {**document, "seed_entity_classes": [UNHELD_CLASS]}
        write_artifact(root, filename, document)
    write_artifact(root, "request-contract.yaml", REQUEST_CONTRACT_DOCUMENT)
    body = manifest_document()
    body["artifacts"] = [
        *body["artifacts"],
        {
            "path": "request-contract.yaml",
            "key": REQUEST_CONTRACT_KEY,
            "class_id": REQUEST_CONTRACT_CLASS_ID,
            "role": "load",
            "registration": "typed",
        },
    ]
    manifest = write_artifact(root, "manifest.yaml", body)
    control_plane = ControlPlaneRegistry()
    fabric = load_and_boot(
        manifest,
        registry=control_plane,
        connection={"database_path": str(root / "graph.sqlite3")},
    )
    declare_wide_temporal_boundary(control_plane, tenant_id=fabric.tenant_id)
    for envelope in envelopes:
        fabric.handle.worker.ingest(envelope)
    return (
        fabric,
        control_plane,
        declaring_store(
            root / "artifacts",
            REPLAY_RECORD_CLASS,
            QUERY_PIN_CLASS,
            ADMITTED_CHILD_CONTRACT_CLASS,
        ),
    )


def _serve(
    booted: Any,
    subject: str,
    *,
    withhold: frozenset[str] = frozenset(),
    blank: frozenset[str] = frozenset(),
) -> Any:
    """One governed serve through the shipped resolver, as the fixture principal."""
    fabric, control_plane, store = booted
    resolver = GovernedResolver(
        composite_children=None,
        acquisition=None,
        population_acquisition=None,
        packaging_trace=None,
        half_life_key=HALF_LIFE_KEY,
        admission_clock=lambda: SERVED_AT,
        decision_instant_parameter=None,
        source_refresh_recency=NO_SOURCE_REFRESH_RECENCY,
        fabric=fabric,
        control_plane=control_plane,
        product_class_key=PRODUCT_CLASS_KEY,
        request_contract_key=REQUEST_CONTRACT_KEY,
        operator_parameter_keys=(POLICY_PARAMS_KEY, TRAVERSAL_KEY),
        policy_bundle_key=POLICY_BUNDLE_KEY,
        debt_profile_key=None,
        plan_factory=lambda *, required, request: _SubjectScopedProjection(
            required=required, request=request, withhold=withhold, blank=blank
        ),
        debt_scorer=AssemblyDebtScorer(
            table=_table(),
            profile=profile(),
            completeness=DeclaredFactor(value=DECLARED),
            semantic_consistency=DeclaredFactor(value=DECLARED),
        ),
        product_gate=None,
        constraint_resolver=ReferencePolicyConstraintResolver(
            control_plane=control_plane,
            entitlement_key=product_entitlement_key(tenant_id=TENANT),
        ),
        capabilities=(),
        refusal_recorder=ReplayRefusalRecorder(
            authorized=composition_replay_mint(
                control_plane, tenant=TENANT, artifact_class=REPLAY_RECORD_CLASS
            ),
            artifact_store=store,
            assembly_mode="algorithmic",
        ),
        artifact_store=store,
        replay_record_class=REPLAY_RECORD_CLASS,
        query_pin_class=QUERY_PIN_CLASS,
        max_ttl_seconds=MAX_TTL_SECONDS,
        product_ttl_seconds=WINDOW_SECONDS,
    )
    return resolver(
        tenant=TENANT,
        product_class=PRODUCT_CLASS,
        version=PRODUCT_VERSION,
        perspective=PERSPECTIVE,
        request=ProductRequest(
            schema_name=PRODUCT_CLASS,
            schema_version=PRODUCT_VERSION,
            subject=subject,
            intent="fixture-intent",
            freshness="fixture-freshness",
            asked_at=ASKED_AT,
            parameters={THRESHOLD_PARAMETER: 1000},
        ),
    )




#: The withheld subject's source observed it LATER than its siblings — round
#: 2's residual case, now control (1).
FRESHER_AT = datetime(2026, 3, 2, 11, 55, tzinfo=UTC)


def _observed_at(account_ref: str, at: datetime) -> SignalEnvelope:
    document = _envelope(account_ref).model_dump(mode="json")
    document["observed_time"] = at.isoformat().replace("+00:00", "Z")
    return SignalEnvelope.model_validate(document)


class _World:
    """Every fabric shape the controls ask on, under one anchor; closed together."""

    def __init__(self, tmp_path: pathlib.Path, anchor: str) -> None:
        self.anchor = anchor
        self._booted: list[Any] = []
        siblings = (_envelope(BLANK_REF), _envelope(OTHER_REF))
        self.shared_equal = self._boot(tmp_path, "shared-equal", (_envelope(WITHHELD_REF), *siblings))
        self.shared_fresher = self._boot(
            tmp_path, "shared-fresher", (_observed_at(WITHHELD_REF, FRESHER_AT), *siblings)
        )
        self.class_alone = self._boot(tmp_path, "class-alone", (_envelope(WITHHELD_REF),))
        self.class_empty = self._boot(tmp_path, "class-empty", ())
        self.subject_alone = self._boot(
            tmp_path, "subject-alone", (_envelope(WITHHELD_REF),), seeding=SUBJECT_SEEDED
        )
        self.subject_empty = self._boot(tmp_path, "subject-empty", (), seeding=SUBJECT_SEEDED)

    def _boot(self, tmp_path: pathlib.Path, name: str, envelopes: Sequence[SignalEnvelope], *, seeding: str = CLASS_SEEDED) -> Any:
        booted = _boot(
            tmp_path, name=f"{name}-{self.anchor}", ttl_anchor=self.anchor,
            envelopes=envelopes, seeding=seeding,
        )
        self._booted.append(booted)
        return booted

    def close(self) -> None:
        for booted in self._booted:
            booted[0].handle.close()


@pytest.fixture(params=[FROM_DECISION, FROM_ENTITY_FRESHNESS])
def world(request: pytest.FixtureRequest, tmp_path: pathlib.Path) -> Iterator[_World]:
    built = _World(tmp_path, request.param)
    try:
        yield built
    finally:
        built.close()


@pytest.fixture()
def decision_world(tmp_path: pathlib.Path) -> Iterator[_World]:
    built = _World(tmp_path, FROM_DECISION)
    try:
        yield built
    finally:
        built.close()


def _vessel(outcome: Any) -> dict[str, Any]:
    assert isinstance(outcome, ServedProduct), (
        f"not served — {outcome!r}; a refusal on one side and a served vessel on"
        " the other is itself the loudest possible difference"
    )
    return outcome.product.model_dump(mode="json")


def _refusal(outcome: Any) -> dict[str, Any]:
    """The refusal as a consumer reads it, minus the one per-decision member.

    ``replay_reference`` names WHERE this decision's own record landed — two
    decisions always land at two addresses (the sibling SEC rows hold the
    reference opaque); every other member is compared.
    """
    assert isinstance(outcome, RefusalEnvelope), (
        f"not refused — {type(outcome).__name__}: an evidence-anchored class over"
        " an empty view refuses (`D-IMPL-341` R-3), so a withheld subject must too"
    )
    dumped = outcome.model_dump(mode="json")
    dumped.pop("replay_reference", None)
    return dumped


# --- the exploit -------------------------------------------------------------------


def _observed(outcome: Any) -> tuple[str, dict[str, Any]]:
    """What a consumer observes: served-or-refused, and the body it reads."""
    if isinstance(outcome, ServedProduct):
        return "served", _vessel(outcome)
    return "refused", _refusal(outcome)


def _assert_indistinguishable(withheld: Any, nonexistent: Any, *, case: str) -> None:
    kind_w, body_w = _observed(withheld)
    kind_n, body_n = _observed(nonexistent)
    assert kind_w == kind_n, (
        f"[{case}] the withheld subject was {kind_w} and the nonexistent one was"
        f" {kind_n}: serve-versus-refuse is itself an existence oracle"
    )
    leaked = _diff_paths(body_w, body_n)
    assert not leaked, (
        f"[{case}] a Π-withheld subject is distinguishable from a nonexistent"
        f" one at {sorted(leaked)}"
    )




# --- the five controls (`D-IMPL-371`: all green, or the row PARKS) -------------


@pytest.mark.parametrize("fabric", ["shared_fresher", "shared_equal"])
def test_control_1_same_class_seeded_fabric_unequal_freshness(world: _World, fabric: str) -> None:
    """(1) ONE class-seeded fabric; the withheld subject and a never-ingested one asked on it.

    ``shared_fresher`` is round 2's residual: the withheld subject was observed
    at 11:55 and its siblings at 11:30. The nonexistent identifier's walk
    starts at the class seeds and so READS the withheld subject's claims; the
    withheld subject, re-executed without its request seed, reads exactly the
    same. Required, both anchors (promoted from round 2's strict xfail).
    """
    booted = getattr(world, fabric)
    withheld = _serve(booted, WITHHELD, withhold=frozenset({WITHHELD}))
    nonexistent = _serve(booted, MISSING)
    assert isinstance(nonexistent, ServedProduct), (
        f"[{world.anchor}] the class-seeded fabric's accounts should serve a"
        f" nonexistent subject; the case was not constructed: {nonexistent!r}"
    )
    _assert_indistinguishable(withheld, nonexistent, case=f"{world.anchor}, {fabric}")


def test_control_2_subject_seeded_per_request_shape(world: _World) -> None:
    """(2) A SUBJECT-SEEDED plan over the per-request fabric holding only the subject.

    The request seed is the only walk start, so a nonexistent identifier reads
    nothing — on this same fabric, and on the empty fabric its own question
    would get — and the withheld subject, unseeded, reads nothing too.
    ``from_decision`` serves all three identically; ``from_entity_freshness``
    refuses all three ``ttl-anchor-refusal`` (an empty view has no evidence
    instant, `D-IMPL-341` R-3).
    """
    withheld = _serve(world.subject_alone, WITHHELD, withhold=frozenset({WITHHELD}))
    for name, booted in (("same fabric", world.subject_alone), ("empty fabric", world.subject_empty)):
        nonexistent = _serve(booted, MISSING)
        if world.anchor == FROM_ENTITY_FRESHNESS:
            for outcome in (withheld, nonexistent):
                assert isinstance(outcome, RefusalEnvelope) and outcome.kind == "ttl-anchor-refusal", (
                    f"[{world.anchor}, {name}] expected the empty view's own refusal, got {outcome!r}"
                )
        _assert_indistinguishable(withheld, nonexistent, case=f"{world.anchor}, subject-seeded, {name}")
    if world.anchor == FROM_DECISION:
        assert isinstance(withheld, ServedProduct)
        finding = withheld.product.computed_empty
        assert finding is not None and set(finding.operators_returned_empty) == set(REQUIRED_OPERATORS), (
            f"the unseeded walk found nothing, so the finding names every operator: {finding}"
        )


@pytest.mark.parametrize("seeding", [CLASS_SEEDED, SUBJECT_SEEDED])
def test_control_3_empty_fabric_shape(world: _World, seeding: str) -> None:
    """(3) The fabric that holds nothing: a withheld and a nonexistent subject asked on it.

    Nothing exists, so nothing may differ — on either seeding, both anchors.
    """
    booted = world.class_empty if seeding == CLASS_SEEDED else world.subject_empty
    withheld = _serve(booted, WITHHELD, withhold=frozenset({WITHHELD}))
    nonexistent = _serve(booted, MISSING)
    _assert_indistinguishable(withheld, nonexistent, case=f"{world.anchor}, {seeding}-seeded empty fabric")


#: The two operators, by key, as a finding names them.
POLICY_OPERATOR = "policy.principal-subgraph"
TRAVERSAL_OPERATOR = "traversal.typed-neighborhood"


def test_control_5_a_legitimately_empty_answer_keeps_its_real_debt_and_finding(
    decision_world: _World,
) -> None:
    """(5) An admitted subject Π answers EMPTY for, with NO signal, keeps what its view earned.

    Two shapes. On the class-seeded fabric holding only this subject, its debt
    and finding are those the same fabric yields for the same subject answered
    in full. On the SUBJECT-SEEDED fabric holding only this subject, its own
    request seed is what admits it past the Policy operator, so its REAL
    finding names the traversal alone — a positive statement about its real
    view that the unseeded re-execution (where Policy returns nothing too)
    would contradict. A mechanism that inferred a withhold from an empty
    payload fails the second shape.
    """
    alone = decision_world.class_alone
    blank = _serve(alone, WITHHELD, blank=frozenset({WITHHELD}))
    answered = _serve(alone, WITHHELD)
    assert isinstance(blank, ServedProduct) and isinstance(answered, ServedProduct)
    assert blank.product.payload == {}, "the control did not construct an empty answer"
    assert answered.product.payload == {"accounts": [WITHHELD]}
    assert blank.product.computed_empty is None, (
        "an admitted subject's legitimately empty answer was given the empty"
        f" finding: {blank.product.computed_empty}"
    )
    assert blank.product.debt == answered.product.debt, (
        "an admitted subject's legitimately empty answer lost its real debt:"
        f" {blank.product.debt} vs {answered.product.debt}"
    )

    seeded = _serve(decision_world.subject_alone, WITHHELD, blank=frozenset({WITHHELD}))
    assert isinstance(seeded, ServedProduct) and seeded.product.payload == {}
    finding = seeded.product.computed_empty
    assert finding is not None and set(finding.operators_returned_empty) == {TRAVERSAL_OPERATOR}, (
        "a legitimately empty answer on the subject-seeded fabric lost its real"
        " finding — its request seed admits it past Policy, so only the"
        f" traversal returned empty: {finding}"
    )


def test_the_instrument_can_see_a_difference(decision_world: _World) -> None:
    """Positive control: an answered subject differs from a nonexistent one."""
    answered = _vessel(_serve(decision_world.class_alone, WITHHELD))
    nonexistent = _vessel(_serve(decision_world.class_empty, MISSING))
    differing = _diff_paths(answered, nonexistent)
    assert any(path.startswith("payload") for path in differing), sorted(differing)
    assert any(path.startswith("debt") for path in differing), sorted(differing)
    assert any(path.startswith("computed_empty") for path in differing), sorted(differing)


# --- replay of a withheld decision (corrective round, Finding 2) ------------------
#
# Dimension 5 did not carry the served product's empty finding, and
# `src/ccf/replay/environment.py::RecordedEnvironment.rehydrate_product` never
# set it, so any product served WITH a finding — every withheld subject, and
# every nonexistent subject on an empty per-request fabric — rebuilt without it
# and failed replay with `ReplayDivergence` on its content address. These run
# through the paved road and the SHIPPED `RecordedEnvironment`, never a
# hand-written environment, because the shipped one is what had the defect.

#: The paved fixture's subjects. The withheld one is the entity URI its
#: resolution spec mints for the account it acquires, so the request seed names
#: the entity the mask removes; the absent one names an account never acquired.
PAVED_WITHHELD_REF = "acct-1"
PAVED_WITHHELD = _uri(PAVED_WITHHELD_REF)
PAVED_ABSENT = _uri("acct-paved-absent")


class _PavedWithholding:
    """The paved fixture's own Π, withholding :data:`PAVED_WITHHELD`.

    For the withheld subject it returns what the fixture's Π returns over an
    EMPTY view — exactly its answer for a subject it cannot see — with the
    typed signal; for every other subject it is the fixture's Π unchanged.
    """

    def __init__(self, inner: Any, *, request: ProductRequest) -> None:
        self._inner = inner
        self._request = request

    @property
    def plan_id(self) -> str:
        return str(self._inner.plan_id)

    def required_operators(self) -> tuple[str, ...]:
        return tuple(self._inner.required_operators())

    def invoke(
        self,
        *,
        view: GraphView,
        operator_outputs: Mapping[str, Any],
        perspective: Perspective,
        temporal_boundary: datetime,
    ) -> ProjectionOutput:
        if self._request.subject != PAVED_WITHHELD:
            return self._inner.invoke(
                view=view, operator_outputs=operator_outputs,
                perspective=perspective, temporal_boundary=temporal_boundary,
            )
        unseen = self._inner.invoke(
            view=GraphView(tenant_id=view.tenant_id, as_of=view.as_of),
            operator_outputs={}, perspective=perspective,
            temporal_boundary=temporal_boundary,
        )
        return ProjectionOutput(plan_id=unseen.plan_id, payload=unseen.payload, withheld=True)


def _paved_withholding_project(*, required: tuple[str, ...], request: ProductRequest) -> _PavedWithholding:
    """A NAMED factory over the fixture's own (`D-IMPL-137`)."""
    from tests.deployment.test_replay_binding import _plan_factory  # noqa: PLC0415

    return _PavedWithholding(_plan_factory(required=required, request=request), request=request)


class _AcquireForSubject:
    """Acquisition that, like a real source, returns claims only for the subject asked."""

    def __call__(self, context: Any) -> tuple[SignalEnvelope, ...]:
        from tests.deployment.test_replay_binding import OBSERVED_AT as PAVED_OBSERVED  # noqa: PLC0415

        if context.request.subject != PAVED_WITHHELD:
            return ()
        return (
            SignalEnvelope.model_validate(
                {
                    "tenant_id": context.tenant_id,
                    "envelope_id": "envelope-paved-withheld",
                    "source": {"system_id": "fixture-system"},
                    "ingestion_timestamp": context.instant,
                    "observed_time": PAVED_OBSERVED,
                    "raw_payload": {
                        "account_ref": PAVED_WITHHELD_REF,
                        "classification": "fixture-open",
                        "label": "fixture account",
                    },
                }
            ),
        )


def _subject_seeded_paved_config() -> dict[str, Any]:
    """The paved fixture's config with its walk seeded on a class it never holds.

    So the only walk start is the request seed, and a withheld subject's
    unseeded re-execution reads nothing — its vessel carries the finding that
    replay must rehydrate. Test-side variant only (CINV-01).
    """
    import copy  # noqa: PLC0415

    from tests.products.test_paved_road import _config  # noqa: PLC0415

    document = copy.deepcopy(_config())
    for operator in document["operators"].values():
        operator["seed_entity_classes"] = [UNHELD_CLASS]
    document["resolution"]["entity_rules"].append(dict(_UNHELD_RULE))
    return document


def _replay_once(
    tmp_path: pathlib.Path, subject: str, *, config: dict[str, Any] | None = None
) -> tuple[Any, Any, str]:
    """Serve ``subject`` on the paved road, reopen its fabric, replay through ``RecordedEnvironment``.

    ``config`` is the subject-seeded paved config unless a control names another.
    """
    from ccf.deployment import load_config_and_boot  # noqa: PLC0415
    from ccf.replay.engine import replay  # noqa: PLC0415
    from ccf.replay.environment import RecordedEnvironment  # noqa: PLC0415
    from tests.products.test_paved_road import ASKED_AT as PAVED_ASKED_AT  # noqa: PLC0415
    from tests.products.test_paved_road import _open, _write_tree  # noqa: PLC0415
    from tests.deployment.test_replay_binding import THRESHOLD_PARAMETER as PAVED_THRESHOLD  # noqa: PLC0415

    root = _write_tree(
        tmp_path, config=config if config is not None else _subject_seeded_paved_config()
    )
    scratch = tmp_path / "scratch"
    with _open(root, scratch, acquire=_AcquireForSubject(), project=_paved_withholding_project) as opened:
        served = opened.answer(
            opened.question(
                subject=subject, asked_at=PAVED_ASKED_AT, intent="fixture-intent",
                freshness="fixture-freshness", parameters={PAVED_THRESHOLD: 1000},
            )
        )
        assert isinstance(served, ServedProduct), served
        record = opened.record_of(served)
        minted = sorted(scratch.glob("paved_fixture*.sqlite3"))[-1]
        fabric = load_config_and_boot(
            opened.config_path, registry=opened.control_plane,
            connection={"database_path": str(minted)},
        )
        try:
            outcome = replay(
                record_address=served.replay_ref.content_address,
                store=opened.artifact_store,
                reader=fabric.handle.reader,
                control_plane=opened.control_plane,
                environment=RecordedEnvironment(record=record, opened=opened, fabric=fabric),
            )
        finally:
            fabric.handle.close()
    return served, outcome, record.content_generation_path.product_content_address




def test_control_4_a_withheld_decision_replays_to_its_own_address(tmp_path: pathlib.Path) -> None:
    """(4) A withheld decision with a finding replays through the shipped RecordedEnvironment."""
    served, outcome, recorded = _replay_once(tmp_path, PAVED_WITHHELD)
    assert served.product.computed_empty is not None, (
        "under the subject-seeded paved plan the unseeded walk reads nothing, so"
        " the withheld vessel carries the finding — the case was not constructed"
    )
    assert content_hash(outcome.product) == recorded == content_hash(served.product)
    assert outcome.product.computed_empty == served.product.computed_empty


def test_control_4_a_nonexistent_subject_on_an_empty_fabric_replays_to_its_own_address(
    tmp_path: pathlib.Path,
) -> None:
    """(4) The control: the same defect on a product nobody withheld, closed by the same change."""
    served, outcome, recorded = _replay_once(tmp_path, PAVED_ABSENT)
    assert served.product.computed_empty is not None
    assert content_hash(outcome.product) == recorded == content_hash(served.product)


# --- the paved road WITH the acquisition seam (`D-IMPL-376` (3), route A) ---------
#
# The final close review of `D-IMPL-371` MEASURED the leak these controls could
# not see, because every control above either boots its fabric by hand or, on
# the paved road, seeds the walk on the subject alone: on the shipped paved road
# (`open_product`, the deployment's own `acquire`, a class-seeded plan)
# `GovernedResolver.__call__`'s declared acquisition seam ingests the ASKED
# subject's evidence BEFORE the plan runs. A subject that names nothing has
# nothing acquired, so its walk reads the fabric as it stood before
# acquisition; a withheld subject's unseeded re-execution read the fabric AFTER
# its own acquisition, so the class seeds reached the evidence acquisition had
# just put there. Measured on the reapplied final round: `from_decision`
# differs at `computed_empty`; `from_entity_freshness` refuses the withheld
# subject `ttl-refusal` and the never-acquired one `ttl-anchor-refusal`.


class _RecordingAcquireForSubject(_AcquireForSubject):
    """The same subject-keyed source, counting the envelopes it returned per subject.

    The count is what proves the case was constructed: the withheld subject's
    evidence really was acquired, and nothing was for the never-acquired one.
    """

    def __init__(self) -> None:
        self.returned: dict[str, int] = {}

    def __call__(self, context: Any) -> tuple[SignalEnvelope, ...]:
        envelopes = super().__call__(context)
        subject = context.request.subject
        self.returned[subject] = self.returned.get(subject, 0) + len(envelopes)
        return envelopes


def _paved_config(*, anchor: str, seeding: str) -> dict[str, Any]:
    """The paved fixture's config under ``anchor``; ``seeding`` as the controls name it.

    ``class`` is the paved fixture's own config, whose walk is seeded on the
    account class — the shape the close review measured. ``subject`` is the
    controls' subject-seeded variant. An evidence-anchored class declares its
    λ_c row ``valid-from`` (the open-time refusal `D-IMPL-341` R-3 requires).
    Test-side variants only (CINV-01).
    """
    import copy  # noqa: PLC0415

    from tests.products.test_paved_road import _config  # noqa: PLC0415

    document = (
        copy.deepcopy(_config()) if seeding == CLASS_SEEDED else _subject_seeded_paved_config()
    )
    document["product_class"]["ttl_anchor"] = anchor
    if anchor == FROM_ENTITY_FRESHNESS:
        for row in document["half_life"].values():
            row["decay_basis"] = "valid-from"
    return document


@pytest.mark.parametrize("seeding", [CLASS_SEEDED, SUBJECT_SEEDED])
@pytest.mark.parametrize("anchor", [FROM_DECISION, FROM_ENTITY_FRESHNESS])
def test_the_paved_road_acquisition_seam_does_not_reveal_a_withheld_subject(
    tmp_path: pathlib.Path, anchor: str, seeding: str
) -> None:
    """The same question through ``GovernedResolver.__call__`` WITH the acquisition seam.

    ``D-IMPL-376`` (3), route A. (a) A subject the source holds, acquired and
    then withheld by Π from this principal; (b) a subject that names nothing,
    so its acquisition returns nothing. Both asked through the shipped paved
    road — ``open_product``, a fresh per-question fabric, the deployment's
    ``acquire`` at the declared seam — and compared in every member a caller
    observes: served-or-refused, then the vessel path for path (or the refusal
    shell, every member but its own per-decision ``replay_reference``),
    ``computed_empty`` included, on both anchors. The never-acquired subject's
    side is pinned by name first — its walk reads nothing, so it is served with
    the empty finding naming the plan's operator under ``from_decision`` and
    refused ``ttl-anchor-refusal`` under ``from_entity_freshness`` (an empty
    view carries no evidence instant) — so the equality cannot hold by both
    sides being wrong the same way.
    """
    from tests.products.test_paved_road import ASKED_AT as PAVED_ASKED_AT  # noqa: PLC0415
    from tests.products.test_paved_road import _open, _write_tree  # noqa: PLC0415
    from tests.deployment.test_replay_binding import (  # noqa: PLC0415
        THRESHOLD_PARAMETER as PAVED_THRESHOLD,
    )

    acquire = _RecordingAcquireForSubject()
    root = _write_tree(tmp_path, config=_paved_config(anchor=anchor, seeding=seeding))
    with _open(
        root, tmp_path / "scratch", acquire=acquire, project=_paved_withholding_project
    ) as opened:

        def ask(subject: str) -> Any:
            return opened.answer(
                opened.question(
                    subject=subject, asked_at=PAVED_ASKED_AT, intent="fixture-intent",
                    freshness="fixture-freshness", parameters={PAVED_THRESHOLD: 1000},
                )
            )

        withheld = ask(PAVED_WITHHELD)
        nonexistent = ask(PAVED_ABSENT)
        withheld_record = opened.record_of(withheld)

    case = f"{anchor}, {seeding}-seeded paved road"
    assert acquire.returned == {PAVED_WITHHELD: 1, PAVED_ABSENT: 0}, (
        f"[{case}] the case was not constructed: the source must return the"
        f" withheld subject's evidence and nothing for the absent one: {acquire.returned}"
    )
    if seeding == CLASS_SEEDED:
        # The class seeds reach the acquired account, so the REAL read saw it,
        # and replay dimension 1 keeps that read: the withheld rendering never
        # replaces it. On the subject-seeded plan the real read is empty as
        # well, because the request seed never reaches the final operator view
        # (`TraversalNeighborhood.apply` walks from the seed classes only; the
        # SDK finding recorded at `D-IMPL-371`, bearing on `D-IMPL-111` limb (a)).
        assert PAVED_WITHHELD in withheld_record.context_fabric_snapshot.touched_entities, (
            f"[{case}] replay dimension 1 must keep the REAL read, which saw the"
            " acquired subject; the withheld rendering never replaces it"
        )
    if anchor == FROM_DECISION:
        assert isinstance(nonexistent, ServedProduct), nonexistent
        finding = nonexistent.product.computed_empty
        assert finding is not None and set(finding.operators_returned_empty) == {
            TRAVERSAL_OPERATOR
        }, f"[{case}] the never-acquired subject's walk reads nothing: {finding}"
    else:
        assert isinstance(nonexistent, RefusalEnvelope), nonexistent
        assert nonexistent.kind == "ttl-anchor-refusal", (
            f"[{case}] an empty view has no evidence instant to anchor on"
            f" (`D-IMPL-341` R-3): {nonexistent!r}"
        )
    _assert_indistinguishable(withheld, nonexistent, case=case)


@pytest.mark.parametrize("subject", [PAVED_WITHHELD, PAVED_ABSENT], ids=["withheld", "never-acquired"])
def test_control_4_on_the_class_seeded_paved_road_each_decision_replays_to_its_own_address(
    tmp_path: pathlib.Path, subject: str
) -> None:
    """(4) on the shape route A changes: the class-seeded paved road, acquisition seam on.

    The withheld decision now carries the empty finding of the fabric before
    its acquisition, while its dimension 1 keeps the real read of the acquired
    account; dimension 5 carries the finding and the shipped
    ``RecordedEnvironment`` rehydrates it, so the decision replays to its own
    address, as the never-acquired control does.
    """
    served, outcome, recorded = _replay_once(
        tmp_path, subject, config=_paved_config(anchor=FROM_DECISION, seeding=CLASS_SEEDED)
    )
    assert served.product.computed_empty is not None, (
        "on the class-seeded paved road both decisions carry the empty finding"
        " of a fabric holding nothing; the case was not constructed"
    )
    assert content_hash(outcome.product) == recorded == content_hash(served.product)
    assert outcome.product.computed_empty == served.product.computed_empty


# --- channel C-1: the answer's replay reference (SEC-020 OPEN; Dave's Q11) --------------
#
# The strict expected failure that stood here asserted that a withheld answer's
# reference carries the record NAME a nonexistent subject's gets. Dave rejected
# that criterion on 2026-10-07 (Q11): *"Equal public references must not
# identify different immutable record contents."* Its replacement holds what a
# reference may identify, on the in-memory, HTTP and MCP outputs and on refusals:
# `tests/http_api/test_sec020_replay_reference_issuance.py`.
