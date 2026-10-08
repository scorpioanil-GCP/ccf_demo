"""SEC-020, channels 1, 4 and 6 — a withheld subject beyond the rendering (PROPOSAL tests).

SEC-020 is OPEN. These tests belong to lane ``378-s020design``: each one
measures a channel through which a subject Π withholds was still told apart
from a subject that names nothing after route A (``D-IMPL-376`` (3)), and the
prototype that closes it on this branch. Every prototype here amends a public
Protocol or the acquisition seam's "exactly once" text, so the branch is a
PROPOSAL for Dave, not an integration candidate (lane
``378-s020design``, ``PROPOSAL.md``).

The channels, as the close-out names them (``docs/D-IMPL-377-CLOSE-OUT.md``
section 4a):

* **1 — population-shaped acquisition.** Route A renders a withheld subject
  over the fabric as it stood before its question's acquisition, which is
  what a subject that names nothing walks only when the acquisition is keyed
  on the subject. A source that returns the same accounts whatever is asked
  gives a nonexistent subject those accounts too.
* **4 — composite children (I-1).** A composite resolves its children for the
  asked subject BEFORE its plan runs, so before Π can withhold anything; the
  composed debt replaces the rendered one.
* **6 — a fabric that outlives the question (M-6).** A hand-composed
  long-lived fabric keeps what a withheld subject's question acquired, and a
  later question about an identifier that names nothing reads it.

Two prototypes are measured here.

* **Early disclosure** (channels 4, 1 and 6 for a subject withheld early): a
  plan factory may decide, before anything is acquired, that this principal
  is not told about the subject. Every step that can depend on the subject —
  the acquisition seam and the child questions — is then asked about the
  deployment's declared undisclosed subject, an identifier that names nothing,
  so it does exactly what it does for any nonexistent identifier. The seam is
  still invoked once.
* **Population-aware acquisition** (channel 1 for a subject Π withholds
  late): a seam may declare the subject-independent part of its acquisition,
  which the resolver invokes first and WITHOUT the subject; the withheld
  rendering walks the fabric after that part and before the subject-keyed
  part.
* **One question per acquired fabric** (channel 6): a fabric an acquisition
  seam has written into answers no second acquisition-bearing question.

Equality is the controls' standard
(``tests/products/test_withheld_is_indistinguishable_from_absent.py``):
served-or-refused first, then the vessel path for path, or the refusal shell
in every member but its own ``replay_reference``. Every domain value here is
fixture vocabulary (CINV-01, CLAUDE.md §11).
"""

from __future__ import annotations

import copy
import dataclasses
import pathlib
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime
from typing import Any

import pytest

from ccf.contracts.canonical import content_hash
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.deployment import load_and_boot
from ccf.halflife.assessment import NO_SOURCE_REFRESH_RECENCY
from ccf.products.composite import ADMITTED_CHILD_CONTRACT_CLASS, CHILD_QUESTION_CLASS
from ccf.products.constraints import ReferencePolicyConstraintResolver
from ccf.products.debt_scorer import AssemblyDebtScorer, DeclaredFactor
from ccf.products.door import WireRequest, door_answer
from ccf.products.entitlement import product_entitlement_key
from ccf.products.refusal import RefusalEnvelope
from ccf.products.request import ProductRequest
from ccf.products.resolver import GovernedResolver, ProductNotResolvable, ReplayRefusalRecorder
from ccf.projection.plan import Perspective
from ccf.replay.serve import ServedProduct
from ccf.signal.envelope import SignalEnvelope
from tests.composition import composition_replay_mint, declare_wide_temporal_boundary, declaring_store
from tests.deployment.conftest import (
    ARTIFACT_SET,
    HALF_LIFE_KEY,
    POLICY_BUNDLE_KEY,
    POLICY_PARAMS_KEY,
    PRODUCT_CLASS_KEY,
    RESOLUTION_SPEC_KEY,
    SIGNAL_BATCH_KEY,
    TENANT,
    TRAVERSAL_KEY,
    manifest_document,
    write_artifact,
)
from tests.products import composite_fixture as cf
from tests.products import test_withheld_is_indistinguishable_from_absent as sec020
from tests.products.provider_boot import (
    CHILD_CLASS,
    CHILD_CLASS_KEY,
    CHILD_REQUEST_CONTRACT_KEY,
    child_product_class,
    child_request_contract,
)
from tests.products.test_evidence_derived_debt import DECLARED, profile
from tests.products.test_resolver_seam import (
    ASKED_AT,
    DEBT_PROFILE_KEY,
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
    _arguments,
    _Booted,
)

FROM_DECISION = sec020.FROM_DECISION
FROM_ENTITY_FRESHNESS = sec020.FROM_ENTITY_FRESHNESS
CLASS_SEEDED = sec020.CLASS_SEEDED

#: An identifier the fixture deployments declare as their undisclosed subject:
#: one that names nothing in any of their sources, children or fabrics.
UNDISCLOSED = sec020._uri("acct-undisclosed-fixture")

_assert_indistinguishable = sec020._assert_indistinguishable


# --- shared: a hand-composed governed call over a booted fabric -------------------


def _governed(
    booted: Any,
    *,
    acquisition: Any,
    plan_factory: Any,
) -> GovernedResolver:
    """The controls' resolver (``sec020._serve``), with the seam and the factory stated."""
    fabric, control_plane, store = booted
    return GovernedResolver(
        composite_children=None,
        acquisition=acquisition,
        packaging_trace=None,
        half_life_key=HALF_LIFE_KEY,
        admission_clock=lambda: sec020.SERVED_AT,
        decision_instant_parameter=None,
        source_refresh_recency=NO_SOURCE_REFRESH_RECENCY,
        fabric=fabric,
        control_plane=control_plane,
        product_class_key=PRODUCT_CLASS_KEY,
        request_contract_key=REQUEST_CONTRACT_KEY,
        operator_parameter_keys=(POLICY_PARAMS_KEY, TRAVERSAL_KEY),
        policy_bundle_key=POLICY_BUNDLE_KEY,
        debt_profile_key=None,
        plan_factory=plan_factory,
        debt_scorer=AssemblyDebtScorer(
            table=sec020._table(),
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
        product_ttl_seconds=sec020.WINDOW_SECONDS,
    )


def _question(subject: str) -> ProductRequest:
    return ProductRequest(
        schema_name=PRODUCT_CLASS,
        schema_version=PRODUCT_VERSION,
        subject=subject,
        intent="fixture-intent",
        freshness="fixture-freshness",
        asked_at=ASKED_AT,
        parameters={THRESHOLD_PARAMETER: 1000},
    )


def _late_withholding(*, required: tuple[str, ...], request: ProductRequest) -> Any:
    """A NAMED factory whose Π withholds the withheld account LATE (`D-IMPL-137`)."""
    return sec020._SubjectScopedProjection(
        required=required,
        request=request,
        withhold=frozenset({sec020.WITHHELD}),
        blank=frozenset(),
    )


class _ConstantWithholding:
    """The reviewer's paved Π (`R/lanes/s20docs/probes/probe_acquisition_shapes.py`).

    Its payload is the same constant for every subject (the threshold asked),
    so only what the SDK renders — the debt, the empty finding, the TTL anchor,
    the refusal — can differ; it raises the typed withheld signal for the
    paved withheld account.
    """

    def __init__(self, *, required: tuple[str, ...], request: ProductRequest) -> None:
        self._required = required
        self._request = request

    @property
    def plan_id(self) -> str:
        from tests.deployment.test_replay_binding import PRODUCT_CLASS as PAVED_CLASS  # noqa: PLC0415

        return PAVED_CLASS

    def required_operators(self) -> tuple[str, ...]:
        return self._required

    def invoke(self, *, view: Any, operator_outputs: Any, perspective: Perspective, temporal_boundary: datetime) -> Any:
        from ccf.projection.plan import ProjectionOutput  # noqa: PLC0415
        from tests.deployment.test_replay_binding import THRESHOLD_PARAMETER as PAVED_THRESHOLD  # noqa: PLC0415

        payload = {"threshold": str(self._request.parameters[PAVED_THRESHOLD])}
        return ProjectionOutput(
            plan_id=self.plan_id,
            payload=payload,
            withheld=self._request.subject == sec020.PAVED_WITHHELD,
        )


def _constant_withholding(*, required: tuple[str, ...], request: ProductRequest) -> _ConstantWithholding:
    """A NAMED factory over the constant-payload Π (`D-IMPL-137`)."""
    return _ConstantWithholding(required=required, request=request)


class _EarlyDisclosing:
    """A plan factory that decides BEFORE acquisition what this principal is told.

    The early-disclosure capability is structural: ``discloses`` and
    ``undisclosed_subject``. Its Π withholds exactly the subjects it does not
    disclose, which the resolver requires of it.
    """

    def __init__(self, *, withhold: str, inner: Callable[..., Any] | None = None) -> None:
        self._withhold = withhold
        self._inner = inner
        self.decided: list[str] = []

    def __call__(self, *, required: tuple[str, ...], request: ProductRequest) -> Any:
        if self._inner is not None:
            return self._inner(required=required, request=request)
        return sec020._SubjectScopedProjection(
            required=required,
            request=request,
            withhold=frozenset({self._withhold}),
            blank=frozenset(),
        )

    def discloses(self, *, request: ProductRequest, perspective: Perspective) -> bool:
        self.decided.append(request.subject)
        return request.subject != self._withhold

    def undisclosed_subject(self) -> str:
        return UNDISCLOSED


# --- channel 6: a fabric that outlives the question ------------------------------


class _RefreshWhenAsked:
    """A subject-keyed source composed by hand over a fabric that outlives the question.

    Asked about the withheld account it ingests one FRESHER claim about it
    through the fabric's one writer (L2), as a hand-composed spine's seam does;
    asked about anything else it ingests nothing. ``asked`` is every subject
    the seam was invoked with, in order.
    """

    def __init__(self, fabric: Any, *, held: bool = True) -> None:
        self._fabric = fabric
        self._held = held
        self.asked: list[str] = []
        self.ingested = 0

    def __call__(self, *, request: ProductRequest, perspective: Perspective) -> None:
        self.asked.append(request.subject)
        if self._held and request.subject == sec020.WITHHELD:
            document = sec020._observed_at(sec020.WITHHELD_REF, sec020.FRESHER_AT).model_dump(
                mode="json"
            )
            document["envelope_id"] = "envelope-withheld-acquired-fresher"
            self._fabric.handle.worker.ingest(SignalEnvelope.model_validate(document))
            self.ingested += 1


def _long_lived(tmp_path: pathlib.Path, name: str, anchor: str) -> Any:
    """A class-seeded fabric already holding the withheld account and two siblings."""
    return sec020._boot(
        tmp_path,
        name=name,
        ttl_anchor=anchor,
        envelopes=(
            sec020._envelope(sec020.WITHHELD_REF),
            sec020._envelope(sec020.BLANK_REF),
            sec020._envelope(sec020.OTHER_REF),
        ),
    )


def _refused_as_reused(raised: BaseException) -> bool:
    """The one-question guard, named: the type the prototype raises for a reused fabric."""
    return type(raised).__name__ == "AcquiredFabricReused"


@pytest.mark.parametrize("anchor", [FROM_DECISION, FROM_ENTITY_FRESHNESS])
def test_channel_6_asking_about_a_withheld_subject_moves_no_later_answer(
    tmp_path: pathlib.Path, anchor: str
) -> None:
    """M-6, as the close-out words it: a later answer about a nonexistent identifier moved.

    Two fabrics holding the same accounts. On ``untouched`` a nonexistent
    identifier is asked first, which is the baseline. On ``planted`` the
    withheld account is asked first — its source returns a fresher claim,
    acquired into the fabric — and the same nonexistent identifier second.
    The later answer must be the baseline, or the second question must be
    refused by the one-question guard before anything subject-dependent runs
    (the seam is not invoked again).
    """
    untouched = _long_lived(tmp_path, "untouched", anchor)
    planted = _long_lived(tmp_path, "planted", anchor)
    try:
        baseline = _governed(
            untouched, acquisition=_RefreshWhenAsked(untouched[0]), plan_factory=_late_withholding
        )(
            tenant=TENANT, product_class=PRODUCT_CLASS, version=PRODUCT_VERSION,
            perspective=PERSPECTIVE, request=_question(sec020.MISSING),
        )
        source = _RefreshWhenAsked(planted[0])
        _governed(planted, acquisition=source, plan_factory=_late_withholding)(
            tenant=TENANT, product_class=PRODUCT_CLASS, version=PRODUCT_VERSION,
            perspective=PERSPECTIVE, request=_question(sec020.WITHHELD),
        )
        assert source.ingested == 1, (
            f"[{anchor}] the case was not constructed: the withheld account's"
            " source must have written its fresher claim into the fabric"
        )
        try:
            later = _governed(planted, acquisition=source, plan_factory=_late_withholding)(
                tenant=TENANT, product_class=PRODUCT_CLASS, version=PRODUCT_VERSION,
                perspective=PERSPECTIVE, request=_question(sec020.MISSING),
            )
        except ProductNotResolvable as raised:
            assert _refused_as_reused(raised), f"[{anchor}] refused for another reason: {raised!r}"
            assert source.asked == [sec020.WITHHELD], (
                f"[{anchor}] the guard must refuse before the seam runs again: {source.asked}"
            )
            return
        _assert_indistinguishable(later, baseline, case=f"{anchor}, long-lived fabric, M-6")
    finally:
        untouched[0].handle.close()
        planted[0].handle.close()


def test_channel_6_the_guard_refuses_any_second_question_whatever_its_subject(
    tmp_path: pathlib.Path,
) -> None:
    """The guard reads nothing about the subject: two questions about NONEXISTENT ids, same refusal.

    The control that the refusal is not itself an existence oracle — the
    second question is refused by the same named mechanism when nothing was
    ever acquired and nothing names anything.
    """
    booted = _long_lived(tmp_path, "nothing-acquired", FROM_DECISION)
    source = _RefreshWhenAsked(booted[0], held=False)
    try:
        first = _governed(booted, acquisition=source, plan_factory=_late_withholding)(
            tenant=TENANT, product_class=PRODUCT_CLASS, version=PRODUCT_VERSION,
            perspective=PERSPECTIVE, request=_question(sec020.MISSING),
        )
        assert isinstance(first, ServedProduct), first
        with pytest.raises(ProductNotResolvable) as raised:
            _governed(booted, acquisition=source, plan_factory=_late_withholding)(
                tenant=TENANT, product_class=PRODUCT_CLASS, version=PRODUCT_VERSION,
                perspective=PERSPECTIVE, request=_question(sec020._uri("acct-missing-2")),
            )
        assert _refused_as_reused(raised.value), repr(raised.value)
        assert source.asked == [sec020.MISSING]
    finally:
        booted[0].handle.close()


# --- channel 1: population-shaped acquisition ---------------------------------------


class _PopulationSource:
    """A paved-road source whose accounts do not depend on who is asked about.

    ``population`` is the population-aware capability: the resolver invokes it
    WITHOUT the subject. ``hybrid`` adds a subject-keyed part: the withheld
    account's own claim, only when it is the subject asked. ``population_contexts``
    and ``subject_contexts`` are what each half was handed, in order.
    """

    def __init__(self, *, hybrid: bool) -> None:
        self._hybrid = hybrid
        self.population_contexts: list[Any] = []
        self.subject_contexts: list[Any] = []

    @staticmethod
    def _envelope(ref: str, context: Any) -> SignalEnvelope:
        from tests.deployment.test_replay_binding import OBSERVED_AT as PAVED_OBSERVED  # noqa: PLC0415

        return SignalEnvelope.model_validate(
            {
                "tenant_id": context.tenant_id,
                "envelope_id": f"envelope-population-{ref}",
                "source": {"system_id": "fixture-system"},
                "ingestion_timestamp": context.instant,
                "observed_time": PAVED_OBSERVED,
                "raw_payload": {
                    "account_ref": ref,
                    "classification": "fixture-open",
                    "label": f"label {ref}",
                },
            }
        )

    def population(self, context: Any) -> tuple[SignalEnvelope, ...]:
        self.population_contexts.append(context)
        refs = ("acct-2",) if self._hybrid else (sec020.PAVED_WITHHELD_REF, "acct-2")
        return tuple(self._envelope(ref, context) for ref in refs)

    def __call__(self, context: Any) -> tuple[SignalEnvelope, ...]:
        self.subject_contexts.append(context)
        if self._hybrid and context.request.subject == sec020.PAVED_WITHHELD:
            return (self._envelope(sec020.PAVED_WITHHELD_REF, context),)
        return ()


def _paved_ask(opened: Any, subject: str) -> Any:
    from tests.deployment.test_replay_binding import THRESHOLD_PARAMETER as PAVED_THRESHOLD  # noqa: PLC0415
    from tests.products.test_paved_road import ASKED_AT as PAVED_ASKED_AT  # noqa: PLC0415

    return opened.answer(
        opened.question(
            subject=subject, asked_at=PAVED_ASKED_AT, intent="fixture-intent",
            freshness="fixture-freshness", parameters={PAVED_THRESHOLD: 1000},
        )
    )


@pytest.mark.parametrize("shape", ["population", "hybrid"])
@pytest.mark.parametrize("anchor", [FROM_DECISION, FROM_ENTITY_FRESHNESS])
def test_channel_1_a_declared_population_acquisition_does_not_reveal_a_late_withheld_subject(
    tmp_path: pathlib.Path, anchor: str, shape: str
) -> None:
    """Population-aware acquisition, Π withholding LATE, on the class-seeded paved road.

    The mechanism first, by name: the subject-independent half was invoked
    once per question with a ``PopulationAcquisitionContext`` that carries no
    request, so no subject can reach it. Then the withheld subject (whose
    acquisition the source answers) and a nonexistent one, compared as the
    controls compare.
    """
    from tests.products.test_paved_road import _open, _write_tree  # noqa: PLC0415

    source = _PopulationSource(hybrid=shape == "hybrid")
    root = _write_tree(tmp_path, config=sec020._paved_config(anchor=anchor, seeding=CLASS_SEEDED))
    with _open(root, tmp_path / "scratch", acquire=source, project=_constant_withholding) as opened:
        withheld = _paved_ask(opened, sec020.PAVED_WITHHELD)
        nonexistent = _paved_ask(opened, sec020.PAVED_ABSENT)

    case = f"{anchor}, {shape}, class-seeded paved road"
    assert len(source.population_contexts) == 2, (
        f"[{case}] the subject-independent half must be invoked once per question;"
        f" it was invoked {len(source.population_contexts)} time(s)"
    )
    for context in source.population_contexts:
        assert type(context).__name__ == "PopulationAcquisitionContext", type(context)
        assert not hasattr(context, "request"), (
            f"[{case}] the population half was handed a request, so a subject can reach it"
        )
        assert "subject" not in type(context.question).model_fields, (
            f"[{case}] the population half's question carries a subject"
        )
    assert [context.request.subject for context in source.subject_contexts] == [
        sec020.PAVED_WITHHELD, sec020.PAVED_ABSENT,
    ], f"[{case}] the subject-keyed half runs once per question, with the asked subject"
    _assert_indistinguishable(withheld, nonexistent, case=case)


@pytest.mark.parametrize("shape", ["population", "hybrid"])
@pytest.mark.parametrize("anchor", [FROM_DECISION, FROM_ENTITY_FRESHNESS])
def test_channel_1_an_early_withheld_subject_is_indistinguishable_under_any_acquisition_shape(
    tmp_path: pathlib.Path, anchor: str, shape: str
) -> None:
    """Early disclosure, ONE ordinary seam (no population declaration), the class-seeded paved road.

    The source puts its population in its one ``acquire``; under the hole as
    worded the withheld subject is rendered over the fabric before
    acquisition, and a nonexistent subject walks the population. With the
    disclosure decided first, the seam is asked once, about the declared
    undisclosed subject, and acquires what it acquires for any identifier it
    does not hold — the population.
    """
    from tests.products.test_paved_road import _open, _write_tree  # noqa: PLC0415

    class _OneSeam(_PopulationSource):
        def __call__(self, context: Any) -> tuple[SignalEnvelope, ...]:
            self.subject_contexts.append(context)
            refs = ["acct-2"] if self._hybrid else [sec020.PAVED_WITHHELD_REF, "acct-2"]
            if self._hybrid and context.request.subject == sec020.PAVED_WITHHELD:
                refs.append(sec020.PAVED_WITHHELD_REF)
            return tuple(self._envelope(ref, context) for ref in refs)

    # A seam with no population capability at all: strip the method.
    source = _OneSeam(hybrid=shape == "hybrid")
    seam = _PlainAcquire(source)
    project = _EarlyDisclosing(withhold=sec020.PAVED_WITHHELD, inner=_constant_withholding)
    root = _write_tree(tmp_path, config=sec020._paved_config(anchor=anchor, seeding=CLASS_SEEDED))
    with _open(root, tmp_path / "scratch", acquire=seam, project=project) as opened:
        withheld = _paved_ask(opened, sec020.PAVED_WITHHELD)
        nonexistent = _paved_ask(opened, sec020.PAVED_ABSENT)

    case = f"{anchor}, {shape}, early disclosure, class-seeded paved road"
    _assert_indistinguishable(withheld, nonexistent, case=case)
    assert [context.request.subject for context in source.subject_contexts] == [
        UNDISCLOSED, sec020.PAVED_ABSENT,
    ], (
        f"[{case}] the seam must be invoked once per question, and for the"
        " withheld subject with the declared undisclosed subject:"
        f" {[context.request.subject for context in source.subject_contexts]}"
    )


class _PlainAcquire:
    """The paved road's ordinary ``acquire``: one callable, no population capability."""

    def __init__(self, inner: Any) -> None:
        self._inner = inner

    def __call__(self, context: Any) -> Any:
        return self._inner(context)


# --- channel 4: composite children (I-1) -----------------------------------------------

COMPOSITE_WITHHELD = sec020._uri("acct-1")  # the fixture signal batch ingests acct-1
COMPOSITE_MISSING = sec020._uri("acct-never")


def _composite_boot(tmp_path: pathlib.Path, *, child_anchor: str, ingest_batch: bool = True) -> _Booted:
    """The reviewer's composite probe boot (`R/review/probe_sec020_composite.py`)."""
    root = tmp_path / "deployment"
    root.mkdir(parents=True)
    for key, filename, _cid, _role, _reg, document in ARTIFACT_SET:
        document = copy.deepcopy(document)
        if key == PRODUCT_CLASS_KEY:
            document["requires"] = cf._parent_requires()
        if key == HALF_LIFE_KEY:
            document = sec020._table_document()
        write_artifact(root, filename, document)
    child = child_product_class()
    child["required_operator_keys"] = ["traversal.typed-neighborhood"]
    child["ttl_anchor"] = child_anchor
    write_artifact(root, "product-class-child.yaml", child)
    write_artifact(root, "product-class-higher.yaml", cf.higher_product_class())
    write_artifact(root, "request-contract-higher.yaml", cf.higher_request_contract())
    write_artifact(root, "request-contract.yaml", copy.deepcopy(REQUEST_CONTRACT_DOCUMENT))
    write_artifact(root, "request-contract-child.yaml", child_request_contract())
    write_artifact(root, "debt-profile.yaml", {
        "semver": "1.0.0", "risk_sensitivity": "1", "forced_llm_threshold": "0.30",
        "fail_closed_threshold": "0.70",
        "signal_obligations": [{"signal": "ok", "obligation_ref": cf.OBLIGATION_ON_OK}],
    })
    body = manifest_document()
    extra = [
        ("product-class-child.yaml", CHILD_CLASS_KEY, "ccf.product-class", "register"),
        ("product-class-higher.yaml", cf.HIGHER_CLASS_KEY, "ccf.product-class", "register"),
        ("request-contract-higher.yaml", cf.HIGHER_REQUEST_CONTRACT_KEY, REQUEST_CONTRACT_CLASS_ID, "load"),
        ("request-contract.yaml", REQUEST_CONTRACT_KEY, REQUEST_CONTRACT_CLASS_ID, "load"),
        ("request-contract-child.yaml", CHILD_REQUEST_CONTRACT_KEY, REQUEST_CONTRACT_CLASS_ID, "load"),
        ("debt-profile.yaml", DEBT_PROFILE_KEY, "ccf.debt-profile", "register"),
    ]
    body["artifacts"] = [*body["artifacts"], *[
        {"path": p, "key": k, "class_id": c, "role": r, "registration": "typed"} for p, k, c, r in extra]]
    manifest = write_artifact(root, "manifest.yaml", body)
    control_plane = ControlPlaneRegistry()
    fabric = load_and_boot(manifest, registry=control_plane, connection={"database_path": str(tmp_path / "c.sqlite3")})
    declare_wide_temporal_boundary(control_plane, tenant_id=fabric.tenant_id)
    if ingest_batch:
        for envelope in fabric.artifacts[SIGNAL_BATCH_KEY].envelopes:
            fabric.handle.worker.ingest(envelope)
    store = declaring_store(tmp_path / "artifacts", REPLAY_RECORD_CLASS, QUERY_PIN_CLASS,
                            ADMITTED_CHILD_CONTRACT_CLASS, CHILD_QUESTION_CLASS)
    return _Booted(fabric=fabric, control_plane=control_plane, store=store, root=root)


#: When the child's source observed ``acct-1``, per child anchor. ``11:30`` is
#: the reviewer's measured case. For an evidence-anchored child the claim must
#: lie inside the child's 600-second window at decision (12:00) and at
#: admission (12:07), so it is observed at ``11:59`` — a test-side calibration
#: that makes the withheld subject's child SERVE while a nonexistent
#: subject's child, with no evidence instant, refuses (`D-IMPL-341` R-3).
CHILD_OBSERVED = {
    FROM_DECISION: "2026-03-02T11:30:00Z",
    FROM_ENTITY_FRESHNESS: "2026-03-02T11:59:00Z",
}


class _ChildSourceBySubject:
    """The child deployment's subject-keyed source: claims for ``acct-1`` only."""

    def __init__(self, fabric: Any, *, observed: str) -> None:
        self._fabric = fabric
        self._observed = observed

    def __call__(self, *, request: ProductRequest, perspective: Perspective) -> None:
        if request.subject == COMPOSITE_WITHHELD:
            self._fabric.handle.worker.ingest(SignalEnvelope.model_validate({
                "tenant_id": TENANT, "envelope_id": "child-acq-acct-1",
                "source": {"system_id": "fixture-system"},
                "ingestion_timestamp": "2026-03-02T11:00:00Z",
                "observed_time": self._observed,
                "raw_payload": {"account_ref": "acct-1", "classification": "fixture-open",
                                "label": "fixture account"}}))


def _child_door(
    child: _Booted, *, asked: list[str], observed: str
) -> Callable[[Mapping[str, str]], Mapping[str, str]]:
    """A local child door over the child deployment's own fabric, recording every subject asked."""
    arguments = _arguments(child)
    arguments.update(
        acquisition=_ChildSourceBySubject(child.fabric, observed=observed), half_life_key=HALF_LIFE_KEY,
        product_class_key=CHILD_CLASS_KEY, request_contract_key=CHILD_REQUEST_CONTRACT_KEY,
        operator_parameter_keys=(TRAVERSAL_KEY,), composite_children=None,
        debt_scorer=AssemblyDebtScorer(table=sec020._table(), profile=profile(),
                                       completeness=DeclaredFactor(value=DECLARED),
                                       semantic_consistency=DeclaredFactor(value=DECLARED)),
    )
    resolver = GovernedResolver(**arguments)

    def answer(args: Mapping[str, str]) -> Mapping[str, str]:
        asked.append(args["subject"])
        request = ProductRequest(schema_name=CHILD_CLASS, schema_version="1.0.0", subject=args["subject"],
                                 intent="fixture-intent", freshness="fixture-freshness",
                                 asked_at=datetime.fromisoformat(args["asked_at"]),
                                 parameters={THRESHOLD_PARAMETER: int(args["threshold"])})
        resolved = resolver(tenant=TENANT, product_class=CHILD_CLASS, version="1.0.0",
                            perspective=PERSPECTIVE, request=request)
        return {"outcome": door_answer(resolved, echo=WireRequest(
            product_id=CHILD_CLASS, parameters={"subject": args["subject"]},
            temporal_boundary=request.asked_at), resolved_request=request).decode()}

    return answer


class _ChildArgumentsFromTheRequest:
    """A request-aware child resolver whose child arguments come from the request it is handed.

    The deployment's statement of what each child is asked, derived from the
    composite's EFFECTIVE request as the resolver hands it to ``resolve_for`` —
    never from state closed over beside the governed path.
    """

    def __init__(self) -> None:
        self.subject: str | None = None
        self.inner: Any = None

    def arguments(self, requirement: Any, asked_at: datetime) -> Mapping[str, str]:
        assert self.subject is not None, "child arguments asked for outside resolve_for"
        return {"subject": self.subject, "asked_at": asked_at.isoformat(), "threshold": "1000"}

    def resolve_for(self, **kwargs: Any) -> dict[str, object]:
        self.subject = kwargs["request"].subject
        return dict(self.inner.resolve_for(**kwargs))


def _ask_composite(
    tmp_path: pathlib.Path, subject: str, *, child_anchor: str
) -> tuple[Any, list[str], _EarlyDisclosing]:
    parent = _composite_boot(tmp_path / "parent", child_anchor=child_anchor)
    child_own = _composite_boot(tmp_path / "child", child_anchor=child_anchor, ingest_batch=False)
    # The child's replay record lands in the store the composite reads (a local child).
    child = _Booted(fabric=child_own.fabric, control_plane=child_own.control_plane,
                    store=parent.store, root=child_own.root)
    asked: list[str] = []
    mapping = _ChildArgumentsFromTheRequest()
    project = _EarlyDisclosing(withhold=COMPOSITE_WITHHELD)
    try:
        composite, children = cf.build_composite(
            parent,
            child_door=_child_door(child, asked=asked, observed=CHILD_OBSERVED[child_anchor]),
            child_arguments=mapping.arguments,
        )
        mapping.inner = children
        composite = dataclasses.replace(composite, composite_children=mapping, plan_factory=project)
        outcome = composite(
            tenant=TENANT, product_class=PRODUCT_CLASS, version=PRODUCT_VERSION, perspective=PERSPECTIVE,
            request=ProductRequest(schema_name=PRODUCT_CLASS, schema_version=PRODUCT_VERSION, subject=subject,
                                   intent="fixture-intent", freshness="fixture-freshness", asked_at=ASKED_AT,
                                   parameters={THRESHOLD_PARAMETER: 1000}))
    finally:
        parent.fabric.handle.close()
        child.fabric.handle.close()
    return outcome, asked, project


@pytest.mark.parametrize("child_anchor", [FROM_DECISION, FROM_ENTITY_FRESHNESS])
def test_channel_4_a_withheld_composite_composes_what_a_nonexistent_subjects_composite_does(
    tmp_path: pathlib.Path, child_anchor: str
) -> None:
    """I-1, as the close-out words it: a child asked about the composite's own subject.

    The composite's children are asked BEFORE its plan runs, so a post-plan
    rendering cannot reach them. Under early disclosure the composite asks its
    child about the declared undisclosed subject, exactly as it would ask about
    any identifier that names nothing. Both child anchors: under
    ``from_entity_freshness`` a nonexistent subject's child has no evidence
    instant to anchor on, so the composite may refuse BEFORE its plan runs —
    a refusal no rendering after the plan could repair.
    """
    withheld, asked_w, _ = _ask_composite(tmp_path / "w", COMPOSITE_WITHHELD, child_anchor=child_anchor)
    nonexistent, asked_n, _ = _ask_composite(tmp_path / "n", COMPOSITE_MISSING, child_anchor=child_anchor)
    case = f"composite, subject-keyed child, child anchor {child_anchor}"
    assert asked_n == [COMPOSITE_MISSING], f"[{case}] the case was not constructed: {asked_n}"
    _assert_indistinguishable(withheld, nonexistent, case=case)
    assert asked_w == [UNDISCLOSED], (
        f"[{case}] the withheld composite's child must be asked about the declared"
        f" undisclosed subject, never the withheld one: {asked_w}"
    )


# --- early disclosure: its obligations and its replay ----------------------------------


def test_early_disclosure_acquires_nothing_about_the_undisclosed_subject(tmp_path: pathlib.Path) -> None:
    """Channel 6 for an early-withheld subject: its question writes nothing about it.

    On a long-lived fabric the subject-keyed source is asked about the declared
    undisclosed subject, so nothing about the withheld account is ingested and
    the fabric any later question reads is the one before the question.
    """
    booted = _long_lived(tmp_path, "early", FROM_DECISION)
    source = _RefreshWhenAsked(booted[0])
    try:
        before = booted[0].handle.reader.as_of(tenant_id=TENANT, at=ASKED_AT)
        outcome = _governed(
            booted, acquisition=source, plan_factory=_EarlyDisclosing(withhold=sec020.WITHHELD)
        )(
            tenant=TENANT, product_class=PRODUCT_CLASS, version=PRODUCT_VERSION,
            perspective=PERSPECTIVE, request=_question(sec020.WITHHELD),
        )
        after = booted[0].handle.reader.as_of(tenant_id=TENANT, at=ASKED_AT)
        assert isinstance(outcome, ServedProduct), outcome
        assert source.asked == [UNDISCLOSED], source.asked
        assert source.ingested == 0
        assert content_hash(after) == content_hash(before), (
            "the early-withheld subject's question changed the fabric a later question reads"
        )
    finally:
        booted[0].handle.close()


class _AnsweringProjection(_EarlyDisclosing):
    """A factory that does NOT disclose the withheld account and whose Π answers it anyway."""

    def __call__(self, *, required: tuple[str, ...], request: ProductRequest) -> Any:
        return sec020._SubjectScopedProjection(
            required=required, request=request, withhold=frozenset(), blank=frozenset()
        )


def test_early_disclosure_refuses_a_projection_that_answers_an_undisclosed_subject(
    tmp_path: pathlib.Path,
) -> None:
    """The obligation that makes the early decision safe: Π must withhold what was not disclosed.

    A factory that declares the subject undisclosed and then answers it would
    serve the subject's own payload. The resolver raises by name instead —
    a deployment defect, raised before anything is recorded or served.
    """
    booted = _long_lived(tmp_path, "answering", FROM_DECISION)
    try:
        with pytest.raises(ProductNotResolvable) as raised:
            _governed(
                booted,
                acquisition=_RefreshWhenAsked(booted[0]),
                plan_factory=_AnsweringProjection(withhold=sec020.WITHHELD),
            )(
                tenant=TENANT, product_class=PRODUCT_CLASS, version=PRODUCT_VERSION,
                perspective=PERSPECTIVE, request=_question(sec020.WITHHELD),
            )
        assert type(raised.value).__name__ == "UndisclosedSubjectAnswered", repr(raised.value)
    finally:
        booted[0].handle.close()


@pytest.mark.parametrize("subject", [sec020.PAVED_WITHHELD, sec020.PAVED_ABSENT], ids=["early-withheld", "never-acquired"])
def test_early_disclosure_each_decision_replays_to_its_own_address(
    tmp_path: pathlib.Path, subject: str
) -> None:
    """Control (4) under early disclosure: the class-seeded paved road, the shipped RecordedEnvironment.

    The plan is still built from the caller's request and the record keeps the
    caller's request, so replay re-executes the recorded read and rehydrates the
    rendered vessel exactly as it does for a late withhold.
    """
    from ccf.deployment import load_config_and_boot  # noqa: PLC0415
    from ccf.replay.engine import replay  # noqa: PLC0415
    from ccf.replay.environment import RecordedEnvironment  # noqa: PLC0415
    from tests.products.test_paved_road import _open, _write_tree  # noqa: PLC0415

    project = _EarlyDisclosing(
        withhold=sec020.PAVED_WITHHELD, inner=sec020._paved_withholding_project
    )
    root = _write_tree(
        tmp_path, config=sec020._paved_config(anchor=FROM_DECISION, seeding=CLASS_SEEDED)
    )
    scratch = tmp_path / "scratch"
    with _open(root, scratch, acquire=sec020._AcquireForSubject(), project=project) as opened:
        served = _paved_ask(opened, subject)
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
    recorded = record.content_generation_path.product_content_address
    assert content_hash(outcome.product) == recorded == content_hash(served.product)
    assert record.content_generation_path.request.subject == subject, (
        "the record keeps the CALLER's request; the undisclosed subject is never recorded as the question"
    )


__all__: Sequence[str] = ()
