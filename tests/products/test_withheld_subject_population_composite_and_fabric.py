"""SEC-020 channels 1, 4 and 6 under Dave's rulings Q7–Q10 (``D-IMPL-378``, 2026-10-07 19:31 MST).

SEC-020 is OPEN: these tests measure the mechanisms Dave ruled; they close
nothing. Lane ``378-s020design``; ported from the proposal tests of
``lane-378-s020design`` (red commits ``98691129`` and ``450102db``).

The rulings, verbatim, and what each test holds:

* **Q7** — *"Approve an explicit population-fetch mode. Subject-independent
  acquisition must not receive the requested subject indirectly through
  context or closures. Unsupported combinations must refuse construction."*
  A population phase is declared on its own, is handed a question with no
  subject, runs before anything in the question is fetched for the subject,
  and a walk of everything reachable from what it is handed never finds the
  asked identifier. A population phase that shares its owner with the
  subject-keyed phase refuses construction.
* **Q8** — *"Require early withholding for affected composites. Make it an
  enforced policy decision before subject-dependent fetches, child resolution
  or scoring. It cannot depend on learning whether the subject exists."* The
  decision is the SDK's, taken from the request and a declared
  ``SubjectDisclosurePolicy`` alone; it is identical for a subject the source
  holds and one it does not; a composite that withholds late is refused.
* **Q9** — *"Enforce a fresh fabric per question whenever acquisition exists,
  including concurrent use."* A fabric must be booted for its question before
  a seam may write into it, and it answers one such question: a second one,
  concurrent or not, is refused before anything is read or fetched.
* **Q10** — *"Two declared acquisition phases are permitted, each once. This
  does not authorize recomputing the product twice or fetching a synthetic
  nonexistent subject as a comparison."* Each phase is called once per
  question; under early withholding the stand-in REPLACES the subject (it is
  never fetched in addition), and the product is computed once, along the
  path a nonexistent subject's question takes.

Equality is the controls' standard
(``tests/products/test_withheld_is_indistinguishable_from_absent.py``):
served-or-refused first, then the vessel path for path, or the refusal shell in
every member but its own ``replay_reference``. Every domain value here is
fixture vocabulary (CINV-01, CLAUDE.md §11).
"""

from __future__ import annotations

import copy
import dataclasses
import functools
import inspect
import pathlib
import threading
import types
import uuid
from collections.abc import Callable, Iterator, Mapping, Sequence
from datetime import datetime
from typing import Any

import pytest

from ccf.contracts.canonical import content_hash
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.deployment import load_and_boot
from ccf.graph.protocols import GraphView
from ccf.halflife.assessment import NO_SOURCE_REFRESH_RECENCY
from ccf.products.composite import ADMITTED_CHILD_CONTRACT_CLASS, CHILD_QUESTION_CLASS
from ccf.products.constraints import ReferencePolicyConstraintResolver
from ccf.products.debt_scorer import AssemblyDebtScorer, DeclaredFactor
from ccf.products.door import WireRequest, door_answer
from ccf.products.entitlement import product_entitlement_key
from ccf.products.refusal import RefusalEnvelope
from ccf.products.request import ProductRequest
from ccf.products.resolver import GovernedResolver, ProductNotResolvable, ReplayRefusalRecorder
from ccf.projection.plan import Perspective, ProjectionOutput
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
SUBJECT_SEEDED = sec020.SUBJECT_SEEDED

#: The identifier the fixture deployments declare as their undisclosed
#: subject: one that names nothing in any of their sources, children or fabrics.
UNDISCLOSED = sec020._uri("acct-undisclosed-fixture")

_assert_indistinguishable = sec020._assert_indistinguishable


def _resolver_module() -> Any:
    import ccf.products.resolver as module  # noqa: PLC0415

    return module


def _named(raised: BaseException, name: str) -> bool:
    """The mechanism, by its type's name (the class may not exist on a tree without it)."""
    return any(klass.__name__ == name for klass in type(raised).__mro__)


# --- booting ------------------------------------------------------------------------


def _boots_for_a_question() -> bool:
    """Whether this tree's boot takes the question-fabric declaration (Q9)."""
    return "for_question" in inspect.signature(load_and_boot).parameters


def _boot(
    tmp_path: pathlib.Path,
    name: str,
    *,
    anchor: str,
    envelopes: Sequence[SignalEnvelope],
    seeding: str = CLASS_SEEDED,
    for_question: bool,
) -> Any:
    """``sec020._boot`` (the controls' boot), with the question-fabric declaration stated.

    ``for_question=True`` boots the fabric for one question, as a fabric with
    an acquisition seam must be booted (Q9); on a tree whose boot takes no such
    declaration the fabric is booted plainly, which is all that tree requires.
    Single-writer ingestion (``fabric.handle.worker.ingest``) is the only way
    anything reaches the graph. Test-side document variants only (CINV-01).
    """
    root = tmp_path / name
    root.mkdir()
    for key, filename, _class_id, _role, _registration, document in ARTIFACT_SET:
        if key == PRODUCT_CLASS_KEY:
            document = {
                **document,
                "required_operator_keys": sec020.REQUIRED_OPERATORS,
                "ttl_anchor": anchor,
            }
        if key == HALF_LIFE_KEY:
            document = sec020._table_document()
        if seeding == SUBJECT_SEEDED and key == RESOLUTION_SPEC_KEY:
            document = {
                **document,
                "entity_rules": [*document["entity_rules"], sec020._UNHELD_RULE],
            }
        if seeding == SUBJECT_SEEDED and key == TRAVERSAL_KEY:
            document = {**document, "seed_entity_classes": [sec020.UNHELD_CLASS]}
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
    extra = {"for_question": True} if (for_question and _boots_for_a_question()) else {}
    fabric = load_and_boot(
        manifest,
        registry=control_plane,
        connection={"database_path": str(root / "graph.sqlite3")},
        **extra,
    )
    declare_wide_temporal_boundary(control_plane, tenant_id=fabric.tenant_id)
    for envelope in envelopes:
        fabric.handle.worker.ingest(envelope)
    return (
        fabric,
        control_plane,
        declaring_store(root / "artifacts", REPLAY_RECORD_CLASS, QUERY_PIN_CLASS, ADMITTED_CHILD_CONTRACT_CLASS),
    )


def _base_accounts(*, withheld_observed: datetime | None = None) -> tuple[SignalEnvelope, ...]:
    """The withheld account and two siblings, the fabric's state before any question."""
    withheld = (
        sec020._observed_at(sec020.WITHHELD_REF, withheld_observed)
        if withheld_observed is not None
        else sec020._envelope(sec020.WITHHELD_REF)
    )
    return (withheld, sec020._envelope(sec020.BLANK_REF), sec020._envelope(sec020.OTHER_REF))


# --- one governed call, composed by hand -------------------------------------------


def _governed(
    booted: Any,
    *,
    plan_factory: Any,
    acquisition: Any = None,
    population_acquisition: Any = None,
) -> GovernedResolver:
    """The controls' resolver (``sec020._serve``), with the seams and the factory stated."""
    fabric, control_plane, store = booted
    return GovernedResolver(
        composite_children=None,
        acquisition=acquisition,
        population_acquisition=population_acquisition,
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
            authorized=composition_replay_mint(control_plane, tenant=TENANT, artifact_class=REPLAY_RECORD_CLASS),
            artifact_store=store,
            assembly_mode="algorithmic",
        ),
        artifact_store=store,
        replay_record_class=REPLAY_RECORD_CLASS,
        query_pin_class=QUERY_PIN_CLASS,
        max_ttl_seconds=MAX_TTL_SECONDS,
        product_ttl_seconds=sec020.WINDOW_SECONDS,
    )


def _ask(resolver: GovernedResolver, subject: str) -> Any:
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


# --- the projections: late and early ------------------------------------------------


class _Counted:
    """A projection that counts its invocations into a shared tally, else delegates."""

    def __init__(self, inner: Any, tally: list[str]) -> None:
        self._inner = inner
        self._tally = tally

    @property
    def plan_id(self) -> str:
        return str(self._inner.plan_id)

    def required_operators(self) -> tuple[str, ...]:
        return tuple(self._inner.required_operators())

    def invoke(self, **kwargs: Any) -> ProjectionOutput:
        self._tally.append("invoke")
        output: ProjectionOutput = self._inner.invoke(**kwargs)
        return output


def _policy(withhold: frozenset[str]) -> Any:
    """The declared early-disclosure policy: these subjects are not told to the fixture principal."""
    from ccf.products.subject_disclosure import SubjectDisclosurePolicy  # noqa: PLC0415

    return SubjectDisclosurePolicy(
        undisclosed_subject=UNDISCLOSED,
        by_principal={PERSPECTIVE.principal_id: withhold},
        by_role={},
    )


class _Withholding:
    """A plan factory whose Π withholds ``withhold`` inside the projection, declaring nothing early.

    ``build`` makes the projection and is handed the same ``withhold`` set;
    ``tally`` counts the projections' invocations.
    """

    def __init__(self, *, withhold: frozenset[str], build: Callable[..., Any]) -> None:
        self._withhold = withhold
        self._build = build
        self.tally: list[str] = []

    def __call__(self, *, required: tuple[str, ...], request: ProductRequest) -> Any:
        return _Counted(self._build(required=required, request=request, withhold=self._withhold), self.tally)


class _EarlyWithholding(_Withholding):
    """The same factory, declaring the early-disclosure capability over the same subjects (Q8)."""

    def subject_disclosure(self) -> Any:
        return _policy(self._withhold)


class _LateOnlyWithholding(_Withholding):
    """Declares that its projection withholds, with NO early policy (late only)."""

    def subject_disclosure(self) -> Any:
        return None


def _scoped(*, required: tuple[str, ...], request: ProductRequest, withhold: frozenset[str]) -> Any:
    """The controls' subject-scoped Π."""
    return sec020._SubjectScopedProjection(
        required=required, request=request, withhold=withhold, blank=frozenset()
    )


class _ConstantWithholding:
    """The reviewer's paved Π (``probe_acquisition_shapes.py``): a constant payload, the typed signal for ``withhold``."""

    def __init__(self, *, required: tuple[str, ...], request: ProductRequest, withhold: frozenset[str]) -> None:
        self._required = required
        self._request = request
        self._withhold = withhold

    @property
    def plan_id(self) -> str:
        from tests.deployment.test_replay_binding import PRODUCT_CLASS as PAVED_CLASS  # noqa: PLC0415

        return PAVED_CLASS

    def required_operators(self) -> tuple[str, ...]:
        return self._required

    def invoke(self, *, view: Any, operator_outputs: Any, perspective: Perspective, temporal_boundary: datetime) -> ProjectionOutput:
        from tests.deployment.test_replay_binding import THRESHOLD_PARAMETER as PAVED_THRESHOLD  # noqa: PLC0415

        return ProjectionOutput(
            plan_id=self.plan_id,
            payload={"threshold": str(self._request.parameters[PAVED_THRESHOLD])},
            withheld=self._request.subject in self._withhold,
        )


class _PavedWithholding:
    """The controls' paved Π: for a withheld subject, the fixture Π's answer over an EMPTY view, with the signal."""

    def __init__(self, inner: Any, *, request: ProductRequest, withhold: frozenset[str]) -> None:
        self._inner = inner
        self._request = request
        self._withhold = withhold

    @property
    def plan_id(self) -> str:
        return str(self._inner.plan_id)

    def required_operators(self) -> tuple[str, ...]:
        return tuple(self._inner.required_operators())

    def invoke(self, *, view: Any, operator_outputs: Any, perspective: Perspective, temporal_boundary: datetime) -> ProjectionOutput:
        if self._request.subject not in self._withhold:
            output: ProjectionOutput = self._inner.invoke(
                view=view, operator_outputs=operator_outputs, perspective=perspective,
                temporal_boundary=temporal_boundary,
            )
            return output
        unseen = self._inner.invoke(
            view=GraphView(tenant_id=view.tenant_id, as_of=view.as_of), operator_outputs={},
            perspective=perspective, temporal_boundary=temporal_boundary,
        )
        return ProjectionOutput(plan_id=unseen.plan_id, payload=unseen.payload, withheld=True)


def _paved_withholding(*, required: tuple[str, ...], request: ProductRequest, withhold: frozenset[str]) -> Any:
    """A NAMED factory over the paved fixture's own Π (`D-IMPL-137`)."""
    from tests.deployment.test_replay_binding import _plan_factory  # noqa: PLC0415

    return _PavedWithholding(_plan_factory(required=required, request=request), request=request, withhold=withhold)


# --- the paved road ---------------------------------------------------------------


def _paved_ask(opened: Any, subject: str) -> Any:
    from tests.deployment.test_replay_binding import THRESHOLD_PARAMETER as PAVED_THRESHOLD  # noqa: PLC0415
    from tests.products.test_paved_road import ASKED_AT as PAVED_ASKED_AT  # noqa: PLC0415

    return opened.answer(
        opened.question(
            subject=subject, asked_at=PAVED_ASKED_AT, intent="fixture-intent",
            freshness="fixture-freshness", parameters={PAVED_THRESHOLD: 1000},
        )
    )


def _paved_envelope(ref: str, context: Any, *, observed: datetime | None = None, tag: str = "") -> SignalEnvelope:
    from tests.deployment.test_replay_binding import OBSERVED_AT as PAVED_OBSERVED  # noqa: PLC0415

    return SignalEnvelope.model_validate(
        {
            "tenant_id": context.tenant_id,
            "envelope_id": f"envelope-{tag}{ref}",
            "source": {"system_id": "fixture-system"},
            "ingestion_timestamp": context.instant,
            "observed_time": observed or PAVED_OBSERVED,
            "raw_payload": {"account_ref": ref, "classification": "fixture-open", "label": f"label {ref}"},
        }
    )


#: When the hybrid source's subject-keyed half observed the withheld account:
#: inside the paved class's 600-second window at the decision instant (12:00)
#: and at serve (12:07), while the population's claims (11:00) are not. A
#: rendering that walked the subject-keyed claim would SERVE an
#: evidence-anchored class where a nonexistent subject is refused; minimal
#: disclosure (which withholds a ``ttl-refusal``'s ``expires_at``) and the paved
#: fixture's constant debt rule would hide anything less. A test-side
#: calibration that makes the subject-keyed half's leak observable.
SUBJECT_OBSERVED = datetime.fromisoformat("2026-03-02T11:59:00+00:00")


class _SubjectPhase:
    """The paved road's ordinary ``acquire`` — the subject-keyed phase — recording what it was asked."""

    def __init__(self, *, hybrid: bool, population_inside: bool = False) -> None:
        self._hybrid = hybrid
        self._population_inside = population_inside
        self.asked: list[str] = []

    def __call__(self, context: Any) -> tuple[SignalEnvelope, ...]:
        self.asked.append(context.request.subject)
        found: list[SignalEnvelope] = []
        if self._population_inside:
            refs = ["acct-2"] if self._hybrid else [sec020.PAVED_WITHHELD_REF, "acct-2"]
            found.extend(_paved_envelope(ref, context, tag="population-") for ref in refs)
        if self._hybrid and context.request.subject == sec020.PAVED_WITHHELD:
            found.append(_paved_envelope(sec020.PAVED_WITHHELD_REF, context, observed=SUBJECT_OBSERVED, tag="subject-"))
        return tuple(found)


class _PopulationPhase:
    """The paved road's declared population phase: the same accounts whatever is asked."""

    def __init__(self, *, hybrid: bool) -> None:
        self._hybrid = hybrid
        self.contexts: list[Any] = []

    def __call__(self, context: Any) -> tuple[SignalEnvelope, ...]:
        self.contexts.append(context)
        refs = ("acct-2",) if self._hybrid else (sec020.PAVED_WITHHELD_REF, "acct-2")
        return tuple(_paved_envelope(ref, context, tag="population-") for ref in refs)


# --- Q9: a fresh fabric per question whenever acquisition exists --------------------


class _RefreshWhenAsked:
    """A subject-keyed seam composed by hand: asked about the withheld account it ingests a fresher claim."""

    def __init__(self, fabric: Any, *, held: bool = True) -> None:
        self._fabric = fabric
        self._held = held
        self.asked: list[str] = []
        self.ingested = 0

    def __call__(self, *, request: ProductRequest, perspective: Perspective) -> None:
        self.asked.append(request.subject)
        if self._held and request.subject == sec020.WITHHELD:
            document = sec020._observed_at(sec020.WITHHELD_REF, sec020.FRESHER_AT).model_dump(mode="json")
            document["envelope_id"] = "envelope-withheld-acquired-fresher"
            self._fabric.handle.worker.ingest(SignalEnvelope.model_validate(document))
            self.ingested += 1


def _late(withhold: frozenset[str] = frozenset({sec020.WITHHELD})) -> _Withholding:
    return _Withholding(withhold=withhold, build=_scoped)


@pytest.mark.parametrize("anchor", [FROM_DECISION, FROM_ENTITY_FRESHNESS])
def test_q9_m6_a_fabric_not_booted_for_its_question_takes_no_acquisition(tmp_path: pathlib.Path, anchor: str) -> None:
    """M-6 as the close-out words it, on a fabric booted plainly and kept for several questions.

    ``untouched`` answers a nonexistent identifier: the baseline. ``planted``
    answers the withheld account first — its source returns a fresher claim —
    and the same nonexistent identifier second. Either the later answer is the
    baseline, or the composition refuses by name before the seam writes
    anything: a fabric not booted for its question takes no acquisition (Q9).
    """
    untouched = _boot(tmp_path, "untouched", anchor=anchor, envelopes=_base_accounts(), for_question=False)
    planted = _boot(tmp_path, "planted", anchor=anchor, envelopes=_base_accounts(), for_question=False)
    try:
        source = _RefreshWhenAsked(planted[0])
        try:
            baseline = _ask(_governed(untouched, plan_factory=_late(), acquisition=_RefreshWhenAsked(untouched[0])), sec020.MISSING)
            _ask(_governed(planted, plan_factory=_late(), acquisition=source), sec020.WITHHELD)
            later = _ask(_governed(planted, plan_factory=_late(), acquisition=source), sec020.MISSING)
        except ProductNotResolvable as raised:
            assert _named(raised, "AcquisitionNeedsAQuestionFabric"), f"[{anchor}] refused for another reason: {raised!r}"
            assert source.asked == [] and source.ingested == 0, (
                f"[{anchor}] the refusal must come before the seam writes anything: {source.asked}"
            )
            return
        assert source.ingested == 1, f"[{anchor}] the case was not constructed: {source.asked}"
        _assert_indistinguishable(later, baseline, case=f"{anchor}, a fabric kept across questions, M-6")
    finally:
        untouched[0].handle.close()
        planted[0].handle.close()


@pytest.mark.parametrize("anchor", [FROM_DECISION, FROM_ENTITY_FRESHNESS])
def test_q9_m6_across_a_second_boot_of_the_same_store(tmp_path: pathlib.Path, anchor: str) -> None:
    """M-6 through a second handle: the store the withheld subject's question wrote into, booted again.

    The first question is asked on a fabric booted for it; the fabric is
    closed, and the SAME store is booted again — plainly, as a deployment that
    keeps its graph between questions would — and asked about an identifier
    that names nothing. The later answer must be the baseline, or the second
    boot must take no acquisition, refused by name before its seam writes.
    """
    untouched = _boot(tmp_path, "untouched", anchor=anchor, envelopes=_base_accounts(), for_question=True)
    planted = _boot(tmp_path, "planted", anchor=anchor, envelopes=_base_accounts(), for_question=True)
    try:
        baseline = _ask(_governed(untouched, plan_factory=_late(), acquisition=_RefreshWhenAsked(untouched[0])), sec020.MISSING)
        first = _RefreshWhenAsked(planted[0])
        _ask(_governed(planted, plan_factory=_late(), acquisition=first), sec020.WITHHELD)
        assert first.ingested == 1, f"[{anchor}] the case was not constructed: {first.asked}"
    finally:
        untouched[0].handle.close()
        planted[0].handle.close()
    fabric = load_and_boot(
        tmp_path / "planted" / "manifest.yaml",
        registry=planted[1],
        connection={"database_path": str(tmp_path / "planted" / "graph.sqlite3")},
    )
    again = (fabric, planted[1], planted[2])
    second = _RefreshWhenAsked(fabric)
    try:
        later = _ask(_governed(again, plan_factory=_late(), acquisition=second), sec020.MISSING)
    except ProductNotResolvable as raised:
        assert _named(raised, "AcquisitionNeedsAQuestionFabric"), f"[{anchor}] refused for another reason: {raised!r}"
        assert second.asked == [], f"[{anchor}] the refusal must come before the seam: {second.asked}"
        return
    finally:
        fabric.handle.close()
    _assert_indistinguishable(later, baseline, case=f"{anchor}, the same store booted again, M-6")


def test_q9_a_question_fabric_answers_one_question_whatever_the_second_asks(tmp_path: pathlib.Path) -> None:
    """Booted for its question: the first question is answered; a second, about any identifier, is refused.

    The refusal reads nothing about the subject — the second question names a
    different nonexistent identifier — and comes before the seam runs again.
    """
    booted = _boot(tmp_path, "question", anchor=FROM_DECISION, envelopes=_base_accounts(), for_question=True)
    source = _RefreshWhenAsked(booted[0], held=False)
    try:
        first = _ask(_governed(booted, plan_factory=_late(), acquisition=source), sec020.MISSING)
        assert isinstance(first, ServedProduct), first
        with pytest.raises(ProductNotResolvable) as raised:
            _ask(_governed(booted, plan_factory=_late(), acquisition=source), sec020._uri("acct-missing-2"))
        assert _named(raised.value, "AcquiredFabricReused"), repr(raised.value)
        assert source.asked == [sec020.MISSING], source.asked
    finally:
        booted[0].handle.close()


class _BlockingSeam:
    """Blocks inside the first question's seam until the second question has been decided."""

    def __init__(self) -> None:
        self.entered = threading.Event()
        self.second_decided = threading.Event()
        self.asked: list[str] = []

    def __call__(self, *, request: ProductRequest, perspective: Perspective) -> None:
        self.asked.append(request.subject)
        if len(self.asked) == 1:
            self.entered.set()
            self.second_decided.wait(timeout=30)


def test_q9_two_concurrent_questions_on_one_fabric_the_second_refuses(tmp_path: pathlib.Path) -> None:
    """Concurrent use: while the first question is inside its seam, a second on the same fabric is refused.

    The first question runs on this thread (the fabric's SQLite connection
    belongs to it) and blocks inside its seam; the second is asked from another
    thread while it is blocked. The second must be refused by name before the
    seam runs for it; the first then completes and is served.
    """
    booted = _boot(tmp_path, "concurrent", anchor=FROM_DECISION, envelopes=_base_accounts(), for_question=True)
    seam = _BlockingSeam()
    outcome: dict[str, Any] = {}

    def second() -> None:
        seam.entered.wait(timeout=30)
        try:
            outcome["second"] = _ask(_governed(booted, plan_factory=_late(), acquisition=seam), sec020._uri("acct-concurrent"))
        except BaseException as raised:  # noqa: BLE001 — recorded and asserted below
            outcome["second"] = raised
        finally:
            seam.second_decided.set()

    worker = threading.Thread(target=second)
    worker.start()
    try:
        first = _ask(_governed(booted, plan_factory=_late(), acquisition=seam), sec020.MISSING)
    finally:
        seam.second_decided.set()
        worker.join(timeout=60)
        booted[0].handle.close()
    assert isinstance(first, ServedProduct), first
    assert isinstance(outcome.get("second"), ProductNotResolvable) and _named(outcome["second"], "AcquiredFabricReused"), (
        f"the concurrent second question was not refused by the one-question claim: {outcome.get('second')!r}"
    )
    assert seam.asked == [sec020.MISSING], seam.asked


def test_q9_booting_for_a_question_over_a_store_that_exists_refuses(tmp_path: pathlib.Path) -> None:
    """A question fabric is a fresh one: a store that already exists is refused at boot, by name."""
    booted = _boot(tmp_path, "existing", anchor=FROM_DECISION, envelopes=_base_accounts(), for_question=False)
    booted[0].handle.close()
    manifest = tmp_path / "existing" / "manifest.yaml"
    with pytest.raises(ValueError) as raised:
        load_and_boot(
            manifest,
            registry=ControlPlaneRegistry(),
            connection={"database_path": str(tmp_path / "existing" / "graph.sqlite3")},
            for_question=True,
        )
    assert _named(raised.value, "QuestionFabricNotFresh"), repr(raised.value)


# --- Q7: an explicit population-fetch mode ------------------------------------------


@pytest.mark.parametrize("shape", ["population", "hybrid"])
@pytest.mark.parametrize("anchor", [FROM_DECISION, FROM_ENTITY_FRESHNESS])
def test_q7_a_declared_population_phase_does_not_reveal_a_late_withheld_subject(
    tmp_path: pathlib.Path, anchor: str, shape: str
) -> None:
    """The population phase declared on its own; Π withholds LATE; the class-seeded paved road.

    The mechanism first, by name: the population phase ran once per question,
    handed a ``PopulationAcquisitionContext`` with no request and a question with
    no subject; the subject-keyed phase ran once per question, with the asked
    subject. Then the withheld subject and a nonexistent one, as the controls
    compare them.
    """
    from tests.products.test_paved_road import _open, _write_tree  # noqa: PLC0415

    population = _PopulationPhase(hybrid=shape == "hybrid")
    subject = _SubjectPhase(hybrid=shape == "hybrid")
    project = _Withholding(withhold=frozenset({sec020.PAVED_WITHHELD}), build=_ConstantWithholding)
    root = _write_tree(tmp_path, config=sec020._paved_config(anchor=anchor, seeding=CLASS_SEEDED))
    with _open(root, tmp_path / "scratch", acquire=subject, acquire_population=population, project=project) as opened:
        withheld = _paved_ask(opened, sec020.PAVED_WITHHELD)
        nonexistent = _paved_ask(opened, sec020.PAVED_ABSENT)
    case = f"{anchor}, {shape}, declared population phase, class-seeded paved road"
    assert len(population.contexts) == 2, f"[{case}] the population phase runs once per question: {len(population.contexts)}"
    for context in population.contexts:
        assert type(context).__name__ == "PopulationAcquisitionContext", type(context)
        assert not hasattr(context, "request"), f"[{case}] the population phase was handed a request"
        assert "subject" not in type(context.question).model_fields, f"[{case}] its question carries a subject"
    assert subject.asked == [sec020.PAVED_WITHHELD, sec020.PAVED_ABSENT], (
        f"[{case}] the subject-keyed phase runs once per question, with the asked subject: {subject.asked}"
    )
    _assert_indistinguishable(withheld, nonexistent, case=case)


#: Types the walk does not descend into: they hold no instance state of the
#: composition (modules and classes) or are leaves.
_LEAVES = (int, float, complex, bool, type(None), datetime, type(Ellipsis))


def _reachable_strings(*roots: Any) -> Iterator[str]:
    """Every string reachable from ``roots``: attributes, slots, mappings, sequences, closures, bound selves.

    Modules, classes and a function's ``__globals__`` are not walked — they are
    the program, not what a call was handed. The walk is over Python objects;
    a graph store's rows are reached by reading the fabric (see the callers).
    """
    seen: set[int] = set()
    stack: list[Any] = list(roots)
    while stack:
        item = stack.pop()
        if id(item) in seen:
            continue
        seen.add(id(item))
        if isinstance(item, str):
            yield item
            continue
        if isinstance(item, (bytes, bytearray)):
            yield bytes(item).decode("utf-8", "replace")
            continue
        if isinstance(item, _LEAVES) or isinstance(item, (types.ModuleType, type)):
            continue
        if isinstance(item, Mapping):
            stack.extend(item.keys())
            stack.extend(item.values())
            continue
        if isinstance(item, (list, tuple, set, frozenset)):
            stack.extend(item)
            continue
        if isinstance(item, functools.partial):
            stack.extend([item.func, item.args, item.keywords])
            continue
        if isinstance(item, (types.FunctionType, types.MethodType)):
            function = getattr(item, "__func__", item)
            stack.append(getattr(item, "__self__", None))
            stack.extend(cell.cell_contents for cell in (getattr(function, "__closure__", None) or ()) if _filled(cell))
            stack.extend([getattr(function, "__defaults__", None), getattr(function, "__kwdefaults__", None)])
            stack.append(getattr(function, "__wrapped__", None))
            continue
        try:
            state = vars(item)
        except TypeError:
            state = {}
        stack.extend(state.values())
        for slot in getattr(type(item), "__slots__", ()) or ():
            stack.append(getattr(item, slot, None))
        if dataclasses.is_dataclass(item):
            stack.extend(getattr(item, field.name, None) for field in dataclasses.fields(item))
        model_fields = getattr(type(item), "model_fields", None)
        if isinstance(model_fields, Mapping):
            stack.extend(getattr(item, name, None) for name in model_fields)


def _filled(cell: Any) -> bool:
    try:
        cell.cell_contents  # noqa: B018 — an empty cell raises
    except ValueError:
        return False
    return True


def test_q7_the_paved_population_phase_cannot_reach_the_subject(tmp_path: pathlib.Path) -> None:
    """Everything reachable from what the paved population phase is handed, walked, never names the subject.

    Asked twice: about the withheld account (which the subject phase holds) and
    about a fresh identifier that appears nowhere but the question. The walk
    covers the context object, every attribute, mapping, sequence, closure cell
    and bound self reachable from it.
    """
    from tests.products.test_paved_road import _open, _write_tree  # noqa: PLC0415

    fresh = sec020._uri(f"acct-walk-{uuid.uuid4().hex}")
    asked: list[str] = []
    found: dict[str, list[str]] = {}

    def population(context: Any) -> tuple[SignalEnvelope, ...]:
        subject = asked[-1]
        found[subject] = [text for text in _reachable_strings(context) if subject in text]
        return ()

    subject_phase = _SubjectPhase(hybrid=True)
    project = _Withholding(withhold=frozenset({sec020.PAVED_WITHHELD}), build=_ConstantWithholding)
    root = _write_tree(tmp_path, config=sec020._paved_config(anchor=FROM_DECISION, seeding=CLASS_SEEDED))
    with _open(root, tmp_path / "scratch", acquire=subject_phase, acquire_population=population, project=project) as opened:
        for subject in (sec020.PAVED_WITHHELD, fresh):
            asked.append(subject)
            _paved_ask(opened, subject)
    assert set(found) == {sec020.PAVED_WITHHELD, fresh}, f"the population phase ran for {sorted(found)}"
    assert found == {sec020.PAVED_WITHHELD: [], fresh: []}, f"the asked subject is reachable from the population phase: {found}"


class _WalkingLowRoadPopulation:
    """A low-road population phase holding its fabric, as a real one must to ingest; it walks what it can reach."""

    def __init__(self, booted: Any) -> None:
        self._booted = booted
        self.walks: list[list[str]] = []
        self.target: list[str] = []

    def __call__(self, *, question: Any, perspective: Perspective) -> None:
        fabric = self._booted[0]
        view = fabric.handle.reader.as_of(tenant_id=fabric.tenant_id, at=question.asked_at)
        subject = self.target[-1]
        roots = (question, perspective, fabric, view)
        self.walks.append([text for text in _reachable_strings(*roots) if subject in text])


def test_q7_the_low_road_population_phase_cannot_reach_the_subject(tmp_path: pathlib.Path) -> None:
    """The low road: the question, the perspective, the fabric handle and the fabric's state, walked.

    The asked identifier is a fresh one that appears nowhere but the question,
    on a fabric booted for that question; nothing the population phase is
    handed or holds names it — and the subject-keyed phase, which runs after,
    is the only one that is handed it.
    """
    fresh = sec020._uri(f"acct-walk-{uuid.uuid4().hex}")
    booted = _boot(tmp_path, "walk", anchor=FROM_DECISION, envelopes=_base_accounts(), for_question=True)
    population = _WalkingLowRoadPopulation(booted)
    population.target.append(fresh)
    subject_phase = _RefreshWhenAsked(booted[0], held=False)
    try:
        _ask(_governed(booted, plan_factory=_late(), acquisition=subject_phase, population_acquisition=population), fresh)
    finally:
        booted[0].handle.close()
    assert population.walks == [[]], f"the asked subject is reachable from the population phase: {population.walks}"
    assert subject_phase.asked == [fresh], subject_phase.asked


class _BothPhases:
    """One object holding both phases: state on it could carry one question's subject into the next."""

    def __init__(self) -> None:
        self.last: str | None = None

    def subject_phase(self, *, request: ProductRequest, perspective: Perspective) -> None:
        self.last = request.subject

    def population_phase(self, *, question: Any, perspective: Perspective) -> None:
        return None


def test_q7_a_population_phase_sharing_an_owner_with_the_subject_phase_refuses_construction(
    tmp_path: pathlib.Path,
) -> None:
    """An unsupported combination: both phases bound to one object. Refused when the resolver is built."""
    booted = _boot(tmp_path, "shared", anchor=FROM_DECISION, envelopes=_base_accounts(), for_question=True)
    both = _BothPhases()
    try:
        with pytest.raises(ProductNotResolvable) as raised:
            _governed(booted, plan_factory=_late(), acquisition=both.subject_phase, population_acquisition=both.population_phase)
        assert _named(raised.value, "PopulationPhaseSharesAnOwner"), repr(raised.value)
    finally:
        booted[0].handle.close()


def test_q7_the_paved_road_refuses_a_population_phase_sharing_an_owner_at_open(tmp_path: pathlib.Path) -> None:
    """The same combination on the paved road is refused when the product is opened."""
    from tests.products.test_paved_road import _open, _write_tree  # noqa: PLC0415

    class _Both:
        def subject(self, context: Any) -> tuple[SignalEnvelope, ...]:
            return ()

        def population(self, context: Any) -> tuple[SignalEnvelope, ...]:
            return ()

    both = _Both()
    root = _write_tree(tmp_path, config=sec020._paved_config(anchor=FROM_DECISION, seeding=CLASS_SEEDED))
    with pytest.raises(ProductNotResolvable) as raised:
        _open(root, tmp_path / "scratch", acquire=both.subject, acquire_population=both.population)
    assert _named(raised.value, "PopulationPhaseSharesAnOwner"), repr(raised.value)


# --- channel 1 under early withholding (one ordinary seam) --------------------------


@pytest.mark.parametrize("shape", ["population", "hybrid"])
@pytest.mark.parametrize("anchor", [FROM_DECISION, FROM_ENTITY_FRESHNESS])
def test_channel_1_an_early_withheld_subject_is_indistinguishable_under_any_acquisition_shape(
    tmp_path: pathlib.Path, anchor: str, shape: str
) -> None:
    """Early disclosure, ONE ordinary seam that also reads the population, the class-seeded paved road.

    Under the hole as worded the withheld subject is rendered over the fabric
    before acquisition while a nonexistent subject walks the population. With
    the disclosure decided first, the seam is asked once, about the declared
    undisclosed subject, and acquires what it acquires for any identifier it
    does not hold.
    """
    from tests.products.test_paved_road import _open, _write_tree  # noqa: PLC0415

    seam = _SubjectPhase(hybrid=shape == "hybrid", population_inside=True)
    project = _EarlyWithholding(withhold=frozenset({sec020.PAVED_WITHHELD}), build=_ConstantWithholding)
    root = _write_tree(tmp_path, config=sec020._paved_config(anchor=anchor, seeding=CLASS_SEEDED))
    with _open(root, tmp_path / "scratch", acquire=seam, project=project) as opened:
        withheld = _paved_ask(opened, sec020.PAVED_WITHHELD)
        nonexistent = _paved_ask(opened, sec020.PAVED_ABSENT)
    case = f"{anchor}, {shape}, early disclosure, class-seeded paved road"
    _assert_indistinguishable(withheld, nonexistent, case=case)
    assert seam.asked == [UNDISCLOSED, sec020.PAVED_ABSENT], (
        f"[{case}] the seam is asked once per question, and for the withheld subject"
        f" with the declared undisclosed subject in its place: {seam.asked}"
    )


# --- Q8: early withholding, an enforced policy decision -------------------------------

COMPOSITE_WITHHELD = sec020._uri("acct-1")  # the fixture signal batch ingests acct-1
COMPOSITE_MISSING = sec020._uri("acct-never")

#: When the child's source observed ``acct-1``, per child anchor. ``11:30`` is
#: the reviewer's measured case. For an evidence-anchored child the claim must
#: lie inside the child's 600-second window at decision (12:00) and admission
#: (12:07), so it is observed at ``11:59`` — a test-side calibration that makes
#: the withheld subject's child SERVE while a nonexistent subject's child, with
#: no evidence instant, refuses (`D-IMPL-341` R-3).
CHILD_OBSERVED = {
    FROM_DECISION: "2026-03-02T11:30:00Z",
    FROM_ENTITY_FRESHNESS: "2026-03-02T11:59:00Z",
}


def _composite_boot(tmp_path: pathlib.Path, *, child_anchor: str, ingest_batch: bool = True, for_question: bool = False) -> _Booted:
    """The reviewer's composite probe boot (``R/review/probe_sec020_composite.py``)."""
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
    question = {"for_question": True} if (for_question and _boots_for_a_question()) else {}
    fabric = load_and_boot(manifest, registry=control_plane, connection={"database_path": str(tmp_path / "c.sqlite3")}, **question)
    declare_wide_temporal_boundary(control_plane, tenant_id=fabric.tenant_id)
    if ingest_batch:
        for envelope in fabric.artifacts[SIGNAL_BATCH_KEY].envelopes:
            fabric.handle.worker.ingest(envelope)
    store = declaring_store(tmp_path / "artifacts", REPLAY_RECORD_CLASS, QUERY_PIN_CLASS,
                            ADMITTED_CHILD_CONTRACT_CLASS, CHILD_QUESTION_CLASS)
    return _Booted(fabric=fabric, control_plane=control_plane, store=store, root=root)


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


def _child_door(child: _Booted, *, asked: list[str], observed: str) -> Callable[[Mapping[str, str]], Mapping[str, str]]:
    """A local child door over the child deployment's own fabric (booted for the one child question)."""
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
    """A request-aware child resolver whose child arguments come from the request it is handed."""

    def __init__(self) -> None:
        self.subject: str | None = None
        self.inner: Any = None

    def arguments(self, requirement: Any, asked_at: datetime) -> Mapping[str, str]:
        assert self.subject is not None, "child arguments asked for outside resolve_for"
        return {"subject": self.subject, "asked_at": asked_at.isoformat(), "threshold": "1000"}

    def resolve_for(self, **kwargs: Any) -> dict[str, object]:
        self.subject = kwargs["request"].subject
        return dict(self.inner.resolve_for(**kwargs))


class _LegacyChildren:
    """A child resolver offering only the request-less legacy call: it cannot receive a stand-in."""

    def __init__(self, inner: Any) -> None:
        self._inner = inner

    def __call__(self, **kwargs: Any) -> dict[str, object]:
        return dict(self._inner(**kwargs))


def _composite(
    tmp_path: pathlib.Path,
    *,
    child_anchor: str,
    project: Any,
    children: str = "request-aware",
) -> tuple[Callable[[str], Any], list[str], Callable[[], None]]:
    """A composite over a local child door; returns (ask, the subjects its child was asked, close)."""
    parent = _composite_boot(tmp_path / "parent", child_anchor=child_anchor)
    child_own = _composite_boot(tmp_path / "child", child_anchor=child_anchor, ingest_batch=False, for_question=True)
    child = _Booted(fabric=child_own.fabric, control_plane=child_own.control_plane, store=parent.store, root=child_own.root)
    asked: list[str] = []
    mapping = _ChildArgumentsFromTheRequest()

    def close() -> None:
        parent.fabric.handle.close()
        child.fabric.handle.close()

    try:
        built, granted = cf.build_composite(
            parent,
            child_door=_child_door(child, asked=asked, observed=CHILD_OBSERVED[child_anchor]),
            child_arguments=mapping.arguments,
        )
        mapping.inner = granted
        composite_children: Any = mapping if children == "request-aware" else _LegacyChildren(granted)
        composite = dataclasses.replace(built, composite_children=composite_children, plan_factory=project)
    except BaseException:
        close()
        raise

    def ask(subject: str) -> Any:
        return composite(
            tenant=TENANT, product_class=PRODUCT_CLASS, version=PRODUCT_VERSION, perspective=PERSPECTIVE,
            request=ProductRequest(schema_name=PRODUCT_CLASS, schema_version=PRODUCT_VERSION, subject=subject,
                                   intent="fixture-intent", freshness="fixture-freshness", asked_at=ASKED_AT,
                                   parameters={THRESHOLD_PARAMETER: 1000}))

    return ask, asked, close


def _early(withhold: frozenset[str] = frozenset({COMPOSITE_WITHHELD})) -> _Withholding:
    return _EarlyWithholding(withhold=withhold, build=_scoped)


@pytest.mark.parametrize("child_anchor", [FROM_DECISION, FROM_ENTITY_FRESHNESS])
def test_q8_a_withheld_composite_composes_what_a_nonexistent_subjects_composite_does(
    tmp_path: pathlib.Path, child_anchor: str
) -> None:
    """I-1, as the close-out words it: a child asked about the composite's own subject.

    The children are asked BEFORE the composite's plan runs, so nothing after
    the plan can reach them. Under the declared early policy the child is asked
    about the undisclosed subject, exactly as about any identifier that names
    nothing. Under ``from_entity_freshness`` a nonexistent subject's child has
    no evidence instant, so the composite refuses before its plan runs — a
    difference no rendering after the plan could repair.
    """
    outcomes: dict[str, Any] = {}
    asks: dict[str, list[str]] = {}
    for name, subject in (("withheld", COMPOSITE_WITHHELD), ("nonexistent", COMPOSITE_MISSING)):
        ask, asked, close = _composite(tmp_path / name, child_anchor=child_anchor, project=_early())
        try:
            outcomes[name] = ask(subject)
        finally:
            close()
        asks[name] = asked
    case = f"composite, subject-keyed child, child anchor {child_anchor}"
    assert asks["nonexistent"] == [COMPOSITE_MISSING], f"[{case}] the case was not constructed: {asks}"
    _assert_indistinguishable(outcomes["withheld"], outcomes["nonexistent"], case=case)
    assert asks["withheld"] == [UNDISCLOSED], (
        f"[{case}] the withheld composite's child is asked about the declared undisclosed subject, never the withheld one: {asks}"
    )


def test_q8_the_early_decision_is_the_same_for_a_subject_the_source_holds_and_one_it_does_not(
    tmp_path: pathlib.Path,
) -> None:
    """The decision is taken from the request and the declared policy alone, never from a lookup.

    The policy names two subjects: one the source holds, one it does not. Both
    are decided the same way — not disclosed — so the seam is asked about the
    stand-in for both. Two unnamed subjects, one held and one not, are both
    disclosed and asked about themselves. And the policy's own decision, asked
    directly, agrees.
    """
    from tests.products.test_paved_road import _open, _write_tree  # noqa: PLC0415

    held = sec020.PAVED_WITHHELD
    unheld = sec020._uri("acct-named-but-unheld")
    held_unnamed = sec020._uri("acct-2")
    unheld_unnamed = sec020._uri("acct-neither")

    class _Holds(_SubjectPhase):
        """A source holding acct-1 and acct-2."""

        def __call__(self, context: Any) -> tuple[SignalEnvelope, ...]:
            self.asked.append(context.request.subject)
            holds = {held: sec020.PAVED_WITHHELD_REF, held_unnamed: "acct-2"}
            ref = holds.get(context.request.subject)
            return () if ref is None else (_paved_envelope(ref, context),)

    named = frozenset({held, unheld})
    seam = _Holds(hybrid=False)
    project = _EarlyWithholding(withhold=named, build=_ConstantWithholding)
    root = _write_tree(tmp_path, config=sec020._paved_config(anchor=FROM_DECISION, seeding=CLASS_SEEDED))
    with _open(root, tmp_path / "scratch", acquire=seam, project=project) as opened:
        for subject in (held, unheld, held_unnamed, unheld_unnamed):
            _paved_ask(opened, subject)
    assert seam.asked == [UNDISCLOSED, UNDISCLOSED, held_unnamed, unheld_unnamed], (
        f"the decision must not depend on whether the source holds the subject: {seam.asked}"
    )
    policy = _policy(named)
    decided = {subject: policy.discloses(subject=subject, perspective=PERSPECTIVE) for subject in (held, unheld, held_unnamed, unheld_unnamed)}
    assert decided == {held: False, unheld: False, held_unnamed: True, unheld_unnamed: True}, decided


def test_q8_a_composite_whose_projection_withholds_late_is_refused(tmp_path: pathlib.Path) -> None:
    """A composite may withhold its subject only through the early policy; a late withhold is refused by name.

    Raised before anything is gated, recorded or served: a broken composition,
    not a governed answer.
    """
    ask, asked, close = _composite(tmp_path / "late", child_anchor=FROM_DECISION, project=_late(frozenset({COMPOSITE_WITHHELD})))
    try:
        with pytest.raises(ProductNotResolvable) as raised:
            ask(COMPOSITE_WITHHELD)
    finally:
        close()
    assert _named(raised.value, "CompositeWithheldLate"), repr(raised.value)


def test_q8_a_composite_declaring_late_only_withholding_refuses_construction(tmp_path: pathlib.Path) -> None:
    """An affected composite — its plan factory declares it withholds — must declare the early policy."""
    with pytest.raises(ProductNotResolvable) as raised:
        _composite(tmp_path / "declared-late", child_anchor=FROM_DECISION,
                   project=_LateOnlyWithholding(withhold=frozenset({COMPOSITE_WITHHELD}), build=_scoped))
    assert _named(raised.value, "CompositeNeedsAnEarlyPolicy"), repr(raised.value)


def test_q8_an_early_policy_whose_children_cannot_receive_the_stand_in_refuses_construction(
    tmp_path: pathlib.Path,
) -> None:
    """An unsupported combination: early withholding over a child resolver that is never handed the request."""
    with pytest.raises(ProductNotResolvable) as raised:
        _composite(tmp_path / "legacy", child_anchor=FROM_DECISION, project=_early(), children="legacy")
    assert _named(raised.value, "EarlyPolicyNeedsRequestAwareChildren"), repr(raised.value)


def test_q8_a_projection_that_answers_an_undisclosed_subject_is_refused(tmp_path: pathlib.Path) -> None:
    """The policy did not disclose the subject and Π answered it anyway: refused by name, nothing served."""

    def answers_everyone(*, required: tuple[str, ...], request: ProductRequest, withhold: frozenset[str]) -> Any:
        return _scoped(required=required, request=request, withhold=frozenset())

    booted = _boot(tmp_path, "answering", anchor=FROM_DECISION, envelopes=_base_accounts(), for_question=True)
    try:
        answering = _EarlyWithholding(withhold=frozenset({sec020.WITHHELD}), build=answers_everyone)
        with pytest.raises(ProductNotResolvable) as raised:
            _ask(_governed(booted, plan_factory=answering, acquisition=_RefreshWhenAsked(booted[0])), sec020.WITHHELD)
        assert _named(raised.value, "UndisclosedSubjectAnswered"), repr(raised.value)
    finally:
        booted[0].handle.close()


def test_q8_a_stand_in_that_names_a_withheld_subject_or_leaves_the_floor_is_refused() -> None:
    """The stand-in reaches the same seams any subject does: it must lie inside the subject floor and name no withheld subject."""
    from pydantic import ValidationError  # noqa: PLC0415

    from ccf.products.subject_disclosure import SubjectDisclosurePolicy  # noqa: PLC0415

    with pytest.raises(ValidationError):
        SubjectDisclosurePolicy(undisclosed_subject="has a space", by_principal={}, by_role={})
    with pytest.raises(ValidationError):
        SubjectDisclosurePolicy(
            undisclosed_subject=UNDISCLOSED,
            by_principal={PERSPECTIVE.principal_id: frozenset({UNDISCLOSED})},
            by_role={},
        )


# --- Q10: two phases, each once; the product computed once -----------------------------


def test_q10_each_phase_is_called_once_and_the_stand_in_replaces_the_subject(tmp_path: pathlib.Path) -> None:
    """Under early withholding, with both phases declared: each runs once per question.

    The population phase is handed no subject; the subject-keyed phase is
    handed the stand-in IN PLACE OF the withheld subject — never the subject
    itself, and never the stand-in in addition to it (no comparison fetch).
    """
    from tests.products.test_paved_road import _open, _write_tree  # noqa: PLC0415

    population = _PopulationPhase(hybrid=True)
    subject = _SubjectPhase(hybrid=True)
    project = _EarlyWithholding(withhold=frozenset({sec020.PAVED_WITHHELD}), build=_ConstantWithholding)
    root = _write_tree(tmp_path, config=sec020._paved_config(anchor=FROM_DECISION, seeding=CLASS_SEEDED))
    with _open(root, tmp_path / "scratch", acquire=subject, acquire_population=population, project=project) as opened:
        withheld = _paved_ask(opened, sec020.PAVED_WITHHELD)
        nonexistent = _paved_ask(opened, sec020.PAVED_ABSENT)
    assert len(population.contexts) == 2, len(population.contexts)
    assert subject.asked == [UNDISCLOSED, sec020.PAVED_ABSENT], subject.asked
    _assert_indistinguishable(withheld, nonexistent, case="both phases, early withholding")


@pytest.mark.parametrize("mode", ["early", "late"])
def test_q10_the_early_withheld_product_is_computed_once(tmp_path: pathlib.Path, mode: str) -> None:
    """The early path computes the product ONCE; route A's re-execution stays the late, non-composite path only.

    Counted where the computation is observable: Π's invocations. Early: one.
    Late (Π withholds inside the projection, a non-composite product): two —
    the re-execution ``D-IMPL-371``/``376`` authorized, recorded here so that a
    change widening it to the early path is seen.
    """
    booted = _boot(tmp_path, mode, anchor=FROM_DECISION, envelopes=_base_accounts(), for_question=True)
    project = (_EarlyWithholding if mode == "early" else _Withholding)(withhold=frozenset({sec020.WITHHELD}), build=_scoped)
    source = _RefreshWhenAsked(booted[0])
    try:
        outcome = _ask(_governed(booted, plan_factory=project, acquisition=source), sec020.WITHHELD)
    finally:
        booted[0].handle.close()
    assert isinstance(outcome, ServedProduct), outcome
    expected = 1 if mode == "early" else 2
    assert project.tally.count("invoke") == expected, (
        f"[{mode}] Π was invoked {project.tally.count('invoke')} time(s); expected {expected}"
    )


def test_q10_early_withholding_is_exact_where_the_fabric_already_holds_the_subject(tmp_path: pathlib.Path) -> None:
    """A subject-seeded plan over a fabric that holds the withheld account before its question.

    A nonexistent identifier's seed matches nothing, so its walk starts at the
    class seeds alone; the withheld subject's single computation must start
    there too — seeded with the stand-in, not with the subject, whose seed
    would admit its own records past the Policy operator.
    """
    outcomes: dict[str, Any] = {}
    for name, subject in (("withheld", sec020.WITHHELD), ("nonexistent", sec020.MISSING)):
        booted = _boot(tmp_path, name, anchor=FROM_DECISION, envelopes=(sec020._envelope(sec020.WITHHELD_REF),),
                       seeding=SUBJECT_SEEDED, for_question=True)
        try:
            outcomes[name] = _ask(
                _governed(booted, plan_factory=_EarlyWithholding(withhold=frozenset({sec020.WITHHELD}), build=_scoped),
                          acquisition=_RefreshWhenAsked(booted[0], held=False)),
                subject,
            )
        finally:
            booted[0].handle.close()
    _assert_indistinguishable(outcomes["withheld"], outcomes["nonexistent"], case="subject-seeded, the fabric holds the subject")


@pytest.mark.parametrize("subject", [sec020.PAVED_WITHHELD, sec020.PAVED_ABSENT], ids=["early-withheld", "never-acquired"])
def test_q10_an_early_withheld_decision_replays_to_its_own_address(tmp_path: pathlib.Path, subject: str) -> None:
    """Control (4) under early withholding: the class-seeded paved road, the shipped RecordedEnvironment.

    The record keeps the CALLER's question; the walk's starting point the
    single computation used — the stand-in — is recorded beside it, and replay
    re-executes from it.
    """
    from ccf.deployment import load_config_and_boot  # noqa: PLC0415
    from ccf.replay.engine import replay  # noqa: PLC0415
    from ccf.replay.environment import RecordedEnvironment  # noqa: PLC0415
    from tests.products.test_paved_road import _open, _write_tree  # noqa: PLC0415

    project = _EarlyWithholding(withhold=frozenset({sec020.PAVED_WITHHELD}), build=_paved_withholding)
    root = _write_tree(tmp_path, config=sec020._paved_config(anchor=FROM_DECISION, seeding=CLASS_SEEDED))
    scratch = tmp_path / "scratch"
    with _open(root, scratch, acquire=sec020._AcquireForSubject(), project=project) as opened:
        served = _paved_ask(opened, subject)
        assert isinstance(served, ServedProduct), served
        record = opened.record_of(served)
        minted = sorted(scratch.glob("paved_fixture*.sqlite3"))[-1]
        fabric = load_config_and_boot(opened.config_path, registry=opened.control_plane, connection={"database_path": str(minted)})
        try:
            outcome = replay(
                record_address=served.replay_ref.content_address, store=opened.artifact_store,
                reader=fabric.handle.reader, control_plane=opened.control_plane,
                environment=RecordedEnvironment(record=record, opened=opened, fabric=fabric),
            )
        finally:
            fabric.handle.close()
    path = record.content_generation_path
    assert content_hash(outcome.product) == path.product_content_address == content_hash(served.product)
    assert path.request is not None and path.request.subject == subject, "the record keeps the caller's question"
    expected = (UNDISCLOSED,) if subject == sec020.PAVED_WITHHELD else None
    assert path.executed_seeds == expected, path.executed_seeds


__all__: Sequence[str] = ()
