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
subject-caused. Constant-fill means the withheld vessel is EXACTLY the vessel
the same plan yields over the SAME fabric with the subject masked out — its
entity, its claims, and anything reachable only through it — which is what a
never-ingested subject reads there, siblings included (walk starts are the
union of seed classes and the request seed, `GQ-11`). On a per-request fabric
that holds only the subject, the masked fabric is empty and the vessel carries
the finding naming every operator. The first version of the repair rendered an
empty view on every fabric, and the close panel measured the existence oracle
that created on one shared fabric (corrective round, ``D-IMPL-370``); both
shapes are asked here, for both anchors.

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


def _boot(
    tmp_path: pathlib.Path,
    *,
    name: str,
    ttl_anchor: str,
    envelopes: Sequence[SignalEnvelope],
) -> Any:
    """The sibling's boot, with the class's anchor and the λ_c table stated.

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


def _fabrics(tmp_path: pathlib.Path, ttl_anchor: str) -> dict[str, Any]:
    """The three fabric shapes, booted under one anchor.

    ``withheld`` — the per-request fabric for a question about the withheld
    subject: it holds that subject's admitted claim. ``shared`` — a long-lived
    fabric holding it beside two other admitted subjects. ``empty`` — the
    per-request fabric for a subject that does not exist.
    """
    return {
        "withheld": _boot(
            tmp_path, name=f"withheld-{ttl_anchor}", ttl_anchor=ttl_anchor,
            envelopes=(_envelope(WITHHELD_REF),),
        ),
        "shared": _boot(
            tmp_path, name=f"shared-{ttl_anchor}", ttl_anchor=ttl_anchor,
            envelopes=(_envelope(WITHHELD_REF), _envelope(BLANK_REF), _envelope(OTHER_REF)),
        ),
        "empty": _boot(
            tmp_path, name=f"empty-{ttl_anchor}", ttl_anchor=ttl_anchor, envelopes=(),
        ),
    }


@pytest.fixture(params=[FROM_DECISION, FROM_ENTITY_FRESHNESS])
def fabrics(request: pytest.FixtureRequest, tmp_path: pathlib.Path) -> Iterator[tuple[str, dict[str, Any]]]:
    booted = _fabrics(tmp_path, request.param)
    try:
        yield request.param, booted
    finally:
        for value in booted.values():
            value[0].handle.close()


@pytest.fixture()
def decision_fabrics(tmp_path: pathlib.Path) -> Iterator[dict[str, Any]]:
    booted = _fabrics(tmp_path, FROM_DECISION)
    try:
        yield booted
    finally:
        for value in booted.values():
            value[0].handle.close()


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


def test_on_one_shared_fabric_a_withheld_subject_reads_as_a_nonexistent_one(
    fabrics: tuple[str, dict[str, Any]],
) -> None:
    """The row's shape: ONE fabric, the withheld subject admitted, the other never ingested.

    Walk starts are the union of the plan's seed classes and the request seed
    (`GQ-11`), so the nonexistent subject reads every in-scope sibling and
    earns their debt, anchor and finding. The withheld subject must read
    exactly that: the fabric with itself masked out — not an empty view, which
    the close panel measured as debt 0 against the nonexistent subject's real
    debt, and as a REFUSAL against its serve on an evidence-anchored class.
    """
    anchor, booted = fabrics
    shared = booted["shared"]
    withheld = _serve(shared, WITHHELD, withhold=frozenset({WITHHELD}))
    nonexistent = _serve(shared, MISSING)
    assert isinstance(nonexistent, ServedProduct), (
        f"[{anchor}] the shared fabric's siblings should serve a nonexistent"
        f" subject; the case under measurement was not constructed: {nonexistent!r}"
    )
    _assert_indistinguishable(withheld, nonexistent, case=f"{anchor}, one shared fabric")


def test_on_a_per_request_fabric_a_withheld_subject_reads_as_a_nonexistent_one(
    fabrics: tuple[str, dict[str, Any]],
) -> None:
    """The paved road's shape: each question's fabric holds what acquisition put in it.

    The fabric for a question about the withheld subject holds its claim and
    nothing else; masked out, that fabric is empty — exactly the fabric a
    question about a nonexistent subject gets. ``from_decision`` serves both
    identically; ``from_entity_freshness`` refuses both ``ttl-anchor-refusal``
    (an empty view has no evidence instant, `D-IMPL-341` R-3).
    """
    anchor, booted = fabrics
    withheld = _serve(booted["withheld"], WITHHELD, withhold=frozenset({WITHHELD}))
    nonexistent = _serve(booted["empty"], MISSING)
    if anchor == FROM_ENTITY_FRESHNESS:
        for outcome in (withheld, nonexistent):
            assert isinstance(outcome, RefusalEnvelope) and outcome.kind == "ttl-anchor-refusal", (
                f"[{anchor}] expected the empty view's own refusal (`D-IMPL-341`"
                f" R-3), got {outcome!r}"
            )
    _assert_indistinguishable(withheld, nonexistent, case=f"{anchor}, per-request fabrics")


def test_the_masked_vessel_carries_the_finding_its_masked_fabric_earns(
    decision_fabrics: dict[str, Any],
) -> None:
    """On a per-request fabric the masked fabric is empty: a finding naming every operator, never ``None``."""
    withheld = _serve(decision_fabrics["withheld"], WITHHELD, withhold=frozenset({WITHHELD}))
    assert isinstance(withheld, ServedProduct)
    finding = withheld.product.computed_empty
    assert finding is not None, "the withheld vessel carries no empty finding"
    assert set(finding.operators_returned_empty) == set(REQUIRED_OPERATORS)
    assert withheld.product.payload == {}


def test_a_legitimately_empty_answer_keeps_its_real_debt_and_finding(
    decision_fabrics: dict[str, Any],
) -> None:
    """The control: an admitted subject Π answers EMPTY for, with no signal.

    Its view holds what it holds, so its debt and its finding are the ones the
    same fabric yields for a subject Π answers in full — never the constant.
    A mechanism that inferred a withhold from an empty payload fails here.

    Asked on the fabric that holds ONLY this subject, so that masking it out
    would change everything the vessel states (its fabric would be empty):
    on the shared fabric a mis-keyed mask is invisible whenever the siblings
    are as fresh as the subject, and the first version of this control was
    measured to stay green under exactly that severing.
    """
    alone = decision_fabrics["withheld"]
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


def test_the_instrument_can_see_a_difference(decision_fabrics: dict[str, Any]) -> None:
    """Positive control: an answered subject differs from a nonexistent one."""
    answered = _vessel(_serve(decision_fabrics["withheld"], WITHHELD))
    nonexistent = _vessel(_serve(decision_fabrics["empty"], MISSING))
    differing = _diff_paths(answered, nonexistent)
    assert any(path.startswith("payload") for path in differing), sorted(differing)
    assert any(path.startswith("debt") for path in differing), sorted(differing)
    assert any(path.startswith("computed_empty") for path in differing), sorted(differing)


#: The withheld subject's source observed it LATER than its siblings — the
#: one ingredient the shared-fabric case above holds equal.
FRESHER_AT = datetime(2026, 3, 2, 11, 55, tzinfo=UTC)


@pytest.mark.xfail(
    strict=True,
    reason=(
        "SEC-020 residual, measured in the corrective round and NOT closed: on one"
        " shared fabric a nonexistent subject's walk (seed classes ∪ request seed,"
        " GQ-11) reads the withheld subject's own claims, so the masked rendering"
        " differs whenever those claims are fresher or staler than the siblings'."
        " No rendering keyed on the fabric alone satisfies both this shape and the"
        " per-request shape; escalated for a ruling."
    ),
)
@pytest.mark.parametrize("anchor", [FROM_DECISION, FROM_ENTITY_FRESHNESS])
def test_residual_on_one_shared_fabric_a_fresher_withheld_subject_is_distinguishable(
    tmp_path: pathlib.Path, anchor: str
) -> None:
    """Strict expected failure: the evidence the residual is real, kept executable."""
    fresher = _envelope(WITHHELD_REF).model_dump(mode="json")
    fresher["observed_time"] = FRESHER_AT.isoformat().replace("+00:00", "Z")
    booted = _boot(
        tmp_path, name=f"residual-{anchor}", ttl_anchor=anchor,
        envelopes=(SignalEnvelope.model_validate(fresher), _envelope(BLANK_REF), _envelope(OTHER_REF)),
    )
    try:
        withheld = _serve(booted, WITHHELD, withhold=frozenset({WITHHELD}))
        nonexistent = _serve(booted, MISSING)
        _assert_indistinguishable(withheld, nonexistent, case=f"{anchor}, residual")
    finally:
        booted[0].handle.close()


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


def _replay_once(tmp_path: pathlib.Path, subject: str) -> tuple[Any, Any, str]:
    """Serve ``subject`` on the paved road, reopen its fabric, replay through ``RecordedEnvironment``."""
    from ccf.deployment import load_config_and_boot  # noqa: PLC0415
    from ccf.replay.engine import replay  # noqa: PLC0415
    from ccf.replay.environment import RecordedEnvironment  # noqa: PLC0415
    from tests.products.test_paved_road import ASKED_AT as PAVED_ASKED_AT  # noqa: PLC0415
    from tests.products.test_paved_road import _open, _write_tree  # noqa: PLC0415
    from tests.deployment.test_replay_binding import THRESHOLD_PARAMETER as PAVED_THRESHOLD  # noqa: PLC0415

    root = _write_tree(tmp_path)
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


def test_a_withheld_decision_replays_to_its_own_address(tmp_path: pathlib.Path) -> None:
    """The withheld vessel carries a finding; replay rehydrates it from dimension 5."""
    served, outcome, recorded = _replay_once(tmp_path, PAVED_WITHHELD)
    assert served.product.computed_empty is not None, (
        "the withheld subject's masked fabric is empty, so its vessel carries the"
        " finding — the case under measurement was not constructed"
    )
    assert content_hash(outcome.product) == recorded == content_hash(served.product)
    assert outcome.product.computed_empty == served.product.computed_empty


def test_a_nonexistent_subject_on_an_empty_fabric_replays_to_its_own_address(
    tmp_path: pathlib.Path,
) -> None:
    """The control: the same defect on a product nobody withheld, closed by the same change."""
    served, outcome, recorded = _replay_once(tmp_path, PAVED_ABSENT)
    assert served.product.computed_empty is not None
    assert content_hash(outcome.product) == recorded == content_hash(served.product)
