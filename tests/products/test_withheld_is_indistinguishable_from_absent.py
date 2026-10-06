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
the same plan yields over an EMPTY view — the same finding naming every
operator, the same debt, scorers and signal — never ``None`` or zero.

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
    return ProjectionOutput(plan_id=plan_id, payload={})


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


def test_a_withheld_subject_reads_exactly_as_a_nonexistent_one(
    fabrics: tuple[str, dict[str, Any]],
) -> None:
    """Q12 (a), on both anchors and both fabric shapes.

    ``from_decision``: the two SERVED vessels are equal, path for path.
    ``from_entity_freshness``: an empty view has no evidence instant, so the
    nonexistent subject refuses ``ttl-anchor-refusal``; the withheld subject
    must refuse identically rather than be served on an anchor read off the
    claims the consumer was not told about.
    """
    anchor, booted = fabrics
    nonexistent = _serve(booted["empty"], MISSING)
    for shape in ("withheld", "shared"):
        withheld = _serve(booted[shape], WITHHELD, withhold=frozenset({WITHHELD}))
        if anchor == FROM_DECISION:
            leaked = _diff_paths(_vessel(withheld), _vessel(nonexistent))
        else:
            leaked = _diff_paths(_refusal(withheld), _refusal(nonexistent))
        assert not leaked, (
            f"[{anchor}, {shape} fabric] a Π-withheld subject is distinguishable"
            f" from a nonexistent one at {sorted(leaked)}"
        )


def test_the_withheld_vessel_is_the_empty_view_vessel_not_a_blank_one(
    decision_fabrics: dict[str, Any],
) -> None:
    """Constant-fill is the plan over an EMPTY view — a finding and a real debt, never ``None``."""
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
    """
    blank = _serve(decision_fabrics["shared"], BLANK, blank=frozenset({BLANK}))
    answered = _serve(decision_fabrics["shared"], OTHER)
    assert isinstance(blank, ServedProduct) and isinstance(answered, ServedProduct)
    assert blank.product.payload == {}, "the control did not construct an empty answer"
    assert answered.product.payload == {"accounts": [OTHER]}
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
