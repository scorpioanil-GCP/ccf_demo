"""`D-29` — the SDK's own assemble → gate → serve composition, and its refusals.

Amendment 1 §B of ``docs/superpowers/specs/2026-08-15-ccf-client-design.md``
ruled that the resolver Protocol **and** its reference implementation both live
in ``src/``. :class:`~ccf.products.resolver.GovernedResolver` is that reference
implementation, and these are the tests of what it composes.

**The refusal legs carry the weight here, and deliberately so.** The success
leg is transcribed from a working example — the rejected first example's spine
ran exactly this sequence and its output is asserted elsewhere. The refusal
legs are the surface **no shipped door has ever exercised**: the seams under
the two MCP doors are typed to return a servable product and admit no refusal
in their union, so until this module every fabric refusal produced behind a
resolver had nowhere to go. Untested new surface is where a defect would sit,
so it gets the tests.

What each test pins, and why the property is worth a test rather than a
docstring:

1. **A question the class does not answer costs nothing.** The request
   conformity verdict is reached *before* the graph is touched — asserted by
   observing a recording reader, never by timing. A resolver that read first
   and refused second would pass every assertion about the refusal's contents
   and still have paid for an answer it threw away.
2. **A gate refusal is a value.** ``run_gates`` returns a refusal rather than
   raising, and this composition must carry that posture across the seam: a
   refused candidate comes back as an envelope with the gate's own typed fields
   intact, and nothing is served.
3. **Delivery is unreachable without a recorded decision.** A store that
   refuses the replay append yields no served product at all — the property
   :mod:`ccf.replay.serve` makes structural, re-asserted *through* the
   composition because that is where a later edit could add the branch the
   serve seam has none of.
4. **Two questions are two products.** Two requests differing only in a
   parameter value produce two different content addresses, through the
   resolver — `D-23`'s standing property re-asserted at the new seam.
5. **No value the deployment owns has a default.** Omitting any constructor
   argument is a ``TypeError`` at construction, never a silent default at call
   time. This is the No-Hardcoding Rule (CLAUDE.md §6.4) with a failing test
   behind it.

Every domain value here — the product class, the parameter names, the
thresholds, the TTL figures, the artifact-class vocabulary — comes from the
fixture deployment under ``tests/deployment/``, reached through a real
``load_and_boot``. Nothing is read from ``src/``, because there is nothing in
``src/`` to read: that is the property the module under test exists to have.
"""

from __future__ import annotations

import copy
import dataclasses
import inspect
import pathlib
from collections.abc import Iterator, Mapping
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest

from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.protocol import ArtifactRef
from ccf.contracts.canonical import content_hash
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.deployment import BootedFabric, load_and_boot
from ccf.graph.protocols import GraphQuery, GraphReader, GraphView
from ccf.halflife.debt import DebtAssessment, DebtFactors, DebtSignal
from ccf.products.constraints import ReferencePolicyConstraintResolver
from ccf.products.contract import ContextProductContract
from ccf.products.debt_scorer import ExecutionEvidence
from ccf.products.entitlement import product_entitlement_key
from ccf.products.gates import DEBT_TOLERANCE_PARAMETER
from ccf.products.disclosure import DisclosureDecision
from ccf.products.refusal import NO_REPLAY_REFERENCE, RefusalEnvelope
from ccf.products.request import ProductRequest
from ccf.replay.record import (
    NO_FABRIC_READ,
    NO_PRODUCT_ADDRESS,
    DecisionReplayRecord,
    PolicyBinding,
    ResolutionNotApplicable,
)
from ccf.products import resolver as resolver_module
from ccf.products.resolver import (
    GovernedResolver,
    ProductNotResolvable,
    RefusalRecorderProtocol,
    ReplayRefusalRecorder,
    ServedProductResolverProtocol,
)
from ccf.projection.plan import Perspective, ProjectionOutput
from ccf.replay.serve import ServedProduct

from tests.deployment.conftest import (
    ARTIFACT_SET,
    POLICY_BUNDLE_KEY,
    PRODUCT_CLASS_KEY,
    SIGNAL_BATCH_KEY,
    TENANT,
    TRAVERSAL_KEY,
    manifest_document,
    write_artifact,
)

# --- the fixture deployment's vocabulary ------------------------------------
#
# Test-side names, never SDK values (CINV-01). They are spelled here rather
# than reached for out of `src/` precisely because the module under test holds
# none of them.

#: The manifest key the request contract is authored under.
REQUEST_CONTRACT_KEY = "fixture/request-contract"

#: The class id it is declared as — an adopter namespace, so a manifest
#: resolves it to a `DeclaredArtifact` and the resolver reads it through
#: `ProductRequestContract.from_declared` (`D-IMPL-126`).
REQUEST_CONTRACT_CLASS_ID = "fixture.request-contract"

#: The one declared parameter, and the only thing two calls differ by.
THRESHOLD_PARAMETER = "revenue_threshold"

#: The ceiling the `booted_with_ceiling` class declares (`24.5-L-14`). A
#: fixture figure, authored in this module's own document and nowhere in `src/`.
CEILING_DECLARED = "0.5"

#: The product class the fixture deployment declares, and its lane.
PRODUCT_CLASS = "fixture.manifest-product"
PRODUCT_VERSION = "1.0.0"

#: The artifact classes the deployment files replay records and query bytes
#: under. Deployment vocabulary; the SDK assumes neither.
REPLAY_RECORD_CLASS = "fixture.replay-record"
QUERY_PIN_CLASS = "fixture.graph-query"

#: The two independently authored TTL figures. They must stay two: Gate 3
#: compares `expires_at` against the registered ceiling, and one figure serving
#: as both would compare a ceiling against itself.
PRODUCT_TTL_SECONDS = 600
MAX_TTL_SECONDS = 3600

#: The instant every request is asked as of. Data, never a clock read — the
#: property `ccf.products.request` exists to preserve.
ASKED_AT = datetime(2026, 3, 2, 12, 0, tzinfo=UTC)

#: The perspective a calling surface would have resolved and entitled.
PERSPECTIVE = Perspective(principal_id="principal-fixture", role="role-fixture")


REQUEST_CONTRACT_DOCUMENT: dict[str, Any] = {
    "semver": "1.0.0",
    "class_id": REQUEST_CONTRACT_CLASS_ID,
    "declaration": {
        "schema_name": PRODUCT_CLASS,
        "schema_version": PRODUCT_VERSION,
        "arguments": {
            "properties": {
                THRESHOLD_PARAMETER: {
                    "type": "number",
                    "description": "Fixture parameter; no default anywhere.",
                }
            },
            "required": [THRESHOLD_PARAMETER],
        },
    },
}


# --- the deployment's own Π and its debt scorer -----------------------------


class _ThresholdProjection:
    """The deployment's projection: put the caller's number in the payload.

    Deliberately the shape ``s1-00``'s projection has — the parameter is
    applied *at* Π and never in the graph query, so what a caller's number
    changes is the payload, and therefore the product's content address, rather
    than what was read.
    """

    def __init__(self, *, required: tuple[str, ...], request: ProductRequest) -> None:
        self._required = required
        self._request = request

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
        threshold = Decimal(str(self._request.parameters[THRESHOLD_PARAMETER]))
        return ProjectionOutput(
            plan_id=self.plan_id,
            payload={
                "role": perspective.role,
                "threshold": str(threshold),
                "assembled": len(list(view.entities)),
            },
        )


def _plan_factory(
    *, required: tuple[str, ...], request: ProductRequest
) -> _ThresholdProjection:
    return _ThresholdProjection(required=required, request=request)


def _debt_scorer(
    *, view: GraphView, evidence: ExecutionEvidence | None = None
) -> DebtAssessment:
    """A fixture scorer. What debt is measured over is deployment policy.

    ``evidence`` is accepted and unread: ``24.6-05`` widened
    :class:`~ccf.products.resolver.AssemblyDebtScorerProtocol` so a scorer is
    told what the execution observed about its own search (``D-IMPL-255``
    (2)), and the governed resolver always passes it.
    """
    return DebtAssessment(
        debt=Decimal("0"),
        signal=DebtSignal.OK,
        factors=DebtFactors(
            freshness=Decimal("1"),
            completeness=Decimal("1"),
            semantic_consistency=Decimal("1"),
        ),
        scorers=(),
    )


# --- observers -------------------------------------------------------------


class _RecordingReader:
    """A reader that records every call made through it.

    Wraps the real reader rather than replacing it, so the composition it is
    handed to behaves identically — the whole point is to observe *whether* the
    graph was reached, not to change what happens when it is. Asserting the
    refusal leg by observation is what makes the claim checkable; asserting it
    by timing would pass on a resolver that read the graph and threw the read
    away.
    """

    def __init__(self, inner: GraphReader) -> None:
        self._inner = inner
        self.calls: list[str] = []

    def as_of(self, *, tenant_id: str, at: datetime) -> GraphView:
        self.calls.append("as_of")
        return self._inner.as_of(tenant_id=tenant_id, at=at)

    def query(self, q: GraphQuery) -> GraphView:
        self.calls.append("query")
        return self._inner.query(q)

    def attestation(self, *args: Any, **kwargs: Any) -> Any:
        self.calls.append("attestation")
        return self._inner.attestation(*args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        self.calls.append(name)
        return getattr(self._inner, name)


class _RefusingStore:
    """An artifact store whose append always fails.

    The negative half of the delivery invariant: `serve` grants the capability
    to deliver *only* out of a completed append, so a store that never
    completes one must yield no served product by construction rather than by a
    branch nobody took.
    """

    def __init__(self, root: pathlib.Path) -> None:
        self._inner = FileArtifactStore(root=root)
        self.attempts = 0

    def put(
        self, *, tenant_id: str, artifact_class: str, name: str, artifact: object
    ) -> ArtifactRef:
        self.attempts += 1
        raise OSError("the artifact substrate refused the append (fixture)")

    def get(self, *, content_address: str) -> bytes:
        return self._inner.get(content_address=content_address)

    def exists(self, *, content_address: str) -> bool:
        return self._inner.exists(content_address=content_address)

    def resolve_uri(self, uri: str) -> bytes:
        return self._inner.resolve_uri(uri)


# --- fixtures ---------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class _Booted:
    """A booted fixture deployment plus the pieces a resolver is wired from."""

    fabric: BootedFabric
    control_plane: ControlPlaneRegistry
    store: FileArtifactStore
    root: pathlib.Path


@pytest.fixture()
def booted(tmp_path: pathlib.Path) -> Iterator[_Booted]:
    """Boot the ``tests/deployment`` fixture deployment, plus a request surface.

    The artifact set and the manifest body are imported rather than restated —
    a second copy of a fixture deployment is a second thing to keep in step,
    and the point here is the resolver, not the documents. The stock manifest
    declares no request surface, because nothing in ``tests/deployment`` needed
    one; this adds a ``role: load`` entry for it in an **adopter** namespace,
    so the manifest resolves it to a declared artifact and the resolver reads
    it with the shipped constructor rather than a hand-build — the ordinary
    authoring shape, not a convenience.
    """
    yield from _boot(tmp_path)


@pytest.fixture
def booted_with_ceiling(tmp_path: pathlib.Path) -> Iterator[_Booted]:
    """The same deployment, with the class declaring a ``D_c`` ceiling and the
    request contract declaring the Standard's universal ``debt_tolerance``.

    The number is authored HERE, in a test-side document, never in ``src/``
    (CINV-01): ``0.5`` is a fixture figure. This is the deployment WR-02 needs
    — a ceiling that is live, so a tolerance the boundary lets through would
    reach the debt gate and be visible as a ``409``.
    """
    product_class = copy.deepcopy(
        next(doc for key, *_rest, doc in ARTIFACT_SET if key == PRODUCT_CLASS_KEY)
    )
    product_class["serve_obligations"] = {
        "default_debt_tolerance": CEILING_DECLARED
    }
    request_contract = copy.deepcopy(REQUEST_CONTRACT_DOCUMENT)
    request_contract["declaration"]["arguments"]["properties"][
        DEBT_TOLERANCE_PARAMETER
    ] = {"type": "number", "description": "Fixture tolerance; a proportion."}
    yield from _boot(
        tmp_path, product_class=product_class, request_contract=request_contract
    )


def _product_class_declaring(intents: list[str]) -> dict[str, Any]:
    """The fixture class document with a ``discovery`` block DECLARED.

    24.7-07, `D-IMPL-264` D-01 as amended (F-1 a). The block is authored
    HERE, in a test-side document, never in ``src/`` (CINV-01): the domain
    and the intent vocabulary are fixture figures. A declared set — even an
    empty one — is the state the stock document (no ``discovery:`` block,
    which reads as :data:`~ccf.products.contract.NOT_DISCOVERABLE`) is NOT.
    """
    product_class = copy.deepcopy(
        next(doc for key, *_rest, doc in ARTIFACT_SET if key == PRODUCT_CLASS_KEY)
    )
    product_class["discovery"] = {
        "domain": "fixture-domain",
        "intents": intents,
        "capabilities": [],
        "audiences": [],
    }
    return product_class


@pytest.fixture
def booted_with_intents(tmp_path: pathlib.Path) -> Iterator[_Booted]:
    """The same deployment, with the class DECLARING that it serves exactly
    the fixture intent — the authoritative state."""
    yield from _boot(tmp_path, product_class=_product_class_declaring(["fixture-intent"]))


@pytest.fixture
def booted_with_no_intents(tmp_path: pathlib.Path) -> Iterator[_Booted]:
    """The same deployment, with the class declaring an EMPTY intent set —
    *"serves none"* (F-1 a), which is not the sentinel's state."""
    yield from _boot(tmp_path, product_class=_product_class_declaring([]))


def _boot(
    tmp_path: pathlib.Path,
    *,
    product_class: dict[str, Any] | None = None,
    request_contract: dict[str, Any] | None = None,
) -> Iterator[_Booted]:
    """The one boot, so the two fixtures cannot drift into two deployments."""
    root = tmp_path / "deployment"
    root.mkdir()
    for key, filename, _class_id, _role, _registration, document in ARTIFACT_SET:
        if key == PRODUCT_CLASS_KEY and product_class is not None:
            document = product_class
        write_artifact(root, filename, document)
    write_artifact(
        root,
        "request-contract.yaml",
        REQUEST_CONTRACT_DOCUMENT if request_contract is None else request_contract,
    )
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
        connection={"database_path": str(tmp_path / "resolver-seam.sqlite3")},
    )
    # 24.5-L-24, kept under 24.6-L-06: the fixture ingests the deployment's
    # OWN signal batch (the one `acct-1` envelope `tests/deployment` ships, an
    # hour before `ASKED_AT`) so the traversal has something to assemble. This
    # fixture once served over an EMPTY fabric — `"assembled": 0` — which
    # 24.5-L-24 turned into a refusal and 24.6-05 turns back into a served
    # computed-empty product (`D-IMPL-242` amendment 1). The seeding stays
    # either way, and for the reason it was always the right fixture: the seam
    # under test is the composition (assemble → gate → serve, and its refusal
    # legs), not emptiness. A success leg that assembled nothing would be
    # testing the empty case wearing the success case's name.
    for envelope in fabric.artifacts[SIGNAL_BATCH_KEY].envelopes:
        fabric.handle.worker.ingest(envelope)
    try:
        yield _Booted(
            fabric=fabric,
            control_plane=control_plane,
            store=FileArtifactStore(root=tmp_path / "artifacts"),
            root=tmp_path,
        )
    finally:
        fabric.handle.close()


def _resolver(booted: _Booted, **overrides: Any) -> GovernedResolver:
    """The wiring a deployment writes once, with per-test variation.

    **Reads** :func:`_arguments` **rather than restating it** (``24.6-07``).
    The two were duplicate literals, and the exhaustiveness assertion below
    (``test_the_argument_enumeration_is_exhaustive``) reads only the second —
    so a field added to the resolver and to one copy would have left the other
    stale, which is exactly what happened to both when the recorder joined.
    One dict is the same discipline ``_boot``'s own docstring already states
    for the two fixtures.
    """
    arguments = _arguments(booted)
    arguments.update(overrides)
    return GovernedResolver(**arguments)


def _request(**overrides: Any) -> ProductRequest:
    fields: dict[str, Any] = {
        "schema_name": PRODUCT_CLASS,
        "schema_version": PRODUCT_VERSION,
        "subject": "acct-1",
        "intent": "fixture-intent",
        "freshness": "fixture-freshness",
        "asked_at": ASKED_AT,
        "parameters": {THRESHOLD_PARAMETER: 1000},
    }
    fields.update(overrides)
    return ProductRequest(**fields)


def _ask(resolver: GovernedResolver, request: ProductRequest | None) -> Any:
    return resolver(
        tenant=TENANT,
        product_class=PRODUCT_CLASS,
        version=PRODUCT_VERSION,
        perspective=PERSPECTIVE,
        request=request,
    )


def _internal(booted: _Booted, shell: RefusalEnvelope) -> RefusalEnvelope:
    """The INTERNAL envelope behind a disclosed shell, read from its own record.

    ``24.6-08``. As of ``D-IMPL-253`` Q17 the seam returns the shell Policy
    permitted, while the record holds what the fabric actually determined
    (``D-IMPL-254``: *"Don't destroy audit truth merely to achieve external
    suppression silence."*). A test about internal truth therefore reads it
    from the record, and a test about the shell reads the shell — which is a
    stronger pair than either alone, because the two must agree about the
    determination and disagree about what crossed.

    Resolution IS part of the assertion: the store refuses bytes that do not
    hash to the address asked for.
    """
    assert shell.replay_reference != NO_REPLAY_REFERENCE, (
        "a shell with no record cannot have an internal form to read; the seam"
        " mints before it returns (D-IMPL-256)"
    )
    record = DecisionReplayRecord.model_validate_json(
        booted.store.get(
            content_address=booted.store.resolve_uri(uri=shell.replay_reference)
        )
    )
    return RefusalEnvelope.model_validate_json(
        record.content_generation_path.assembly_refusal
    )


def _disclosure(booted: _Booted, shell: RefusalEnvelope) -> DisclosureDecision:
    """The :class:`DisclosureDecision` dimension 5 recorded for ``shell``."""
    record = DecisionReplayRecord.model_validate_json(
        booted.store.get(
            content_address=booted.store.resolve_uri(uri=shell.replay_reference)
        )
    )
    return DisclosureDecision.model_validate_json(
        record.content_generation_path.disclosure_decision
    )


# --- conformance ------------------------------------------------------------


def test_the_reference_resolver_conforms_to_the_protocol(booted: _Booted) -> None:
    """The Protocol is `@runtime_checkable`, so this is a real check."""
    assert isinstance(_resolver(booted), ServedProductResolverProtocol)


# --- 24.7-04: the recorder seam requires the explicit resolution state -------


def _requires_the_resolution_state(function: Any) -> bool:
    """True when ``resolution`` is keyword-only with NO default.

    ``D-IMPL-264`` D-10 am.1 (F-3 a), Dave verbatim: *"Any API that
    constructs or delegates construction of a replay record must require an
    explicit resolution state: effective/partial resolution or explicit
    not-applicable marker. No intermediate layer may manufacture the marker
    from omission."* The ``@runtime_checkable`` Protocol check covers the
    presence of ``record``, not its signature, so the signature is read
    here directly.
    """
    parameter = inspect.signature(function).parameters["resolution"]
    return (
        parameter.default is inspect.Parameter.empty
        and parameter.kind is inspect.Parameter.KEYWORD_ONLY
    )


@pytest.mark.parametrize(
    "seam",
    [
        pytest.param(RefusalRecorderProtocol.record, id="RefusalRecorderProtocol.record"),
        pytest.param(ReplayRefusalRecorder.record, id="ReplayRefusalRecorder.record"),
        pytest.param(GovernedResolver._record_refusal, id="GovernedResolver._record_refusal"),
    ],
)
def test_no_recorder_signature_defaults_the_resolution_state(seam: Any) -> None:
    """The three APIs that construct or delegate construction of a record all
    require the state; a default on any of them would be the one call frame
    of omission the ruling closed.
    """
    assert _requires_the_resolution_state(seam), inspect.signature(seam)


def test_the_conformance_check_sees_a_defaulted_signature() -> None:
    """The planted decoy: a recorder whose ``record`` defaults the state is
    exactly what the check above refuses. If this ever passes the check,
    the check has stopped reading signatures and the test above is vacuous.
    """

    class _Defaulting:
        def record(
            self,
            envelope: RefusalEnvelope,
            *,
            perspective: Perspective,
            recorded_at: datetime,
            resolution: Any = None,
        ) -> RefusalEnvelope:
            return envelope

    class _Positional:
        def record(
            self, envelope: RefusalEnvelope, resolution: Any
        ) -> RefusalEnvelope:
            return envelope

    # Presence is what `@runtime_checkable` sees; the signature is not.
    assert isinstance(_Defaulting(), RefusalRecorderProtocol)
    assert not _requires_the_resolution_state(_Defaulting.record)
    assert not _requires_the_resolution_state(_Positional.record)


# --- 24.7-07: intent is judged against the DECLARED discovery set -----------
#
# `D-IMPL-264` D-01 as amended by amendment 1 F-1 a (Dave, verbatim):
# *"Absence of a discovery declaration is non-applicability. Presence of a
# discovery declaration makes its intent set authoritative, including an
# explicitly empty set."* Three states, hosted in `GovernedResolver.resolve`
# beside the address check, before any resolution step (D-09: no resolution
# ran, said so positively) — and the deciding class declaration IS pinned on
# the record (amendment 3 B-3 a: *"replay should preserve the declaration
# that actually governed the outcome"*). Criterion 10.
#
# Sabotage (recorded in the plan SUMMARY, F-1 reading (b)): judge whenever
# `discovery.intents == frozenset()` and the FIRST test below reds — along
# with every other test in this module, because every fixture serves under
# `NOT_DISCOVERABLE`. That is the reading Dave rejected.


def test_intent_is_unjudged_when_no_discovery_is_declared(booted: _Booted) -> None:
    """The stock fixture declares no `discovery`: any intent serves.

    The D-01 am.1 control — including an intent no class anywhere declares.
    Every existing deployment, hw1 and the governed-resolver roster serve
    exactly as they did before this phase.
    """
    assert isinstance(
        _ask(_resolver(booted), _request(intent="fixture-intent")), ServedProduct
    )
    assert isinstance(
        _ask(_resolver(booted), _request(intent="never-declared")), ServedProduct
    )


def test_a_declared_intent_serves_and_an_undeclared_one_is_refused_as_data(
    booted_with_intents: _Booted,
) -> None:
    """Declared → authoritative: the member serves, a non-member is refused
    as data, before the graph is touched, with the deciding declaration pinned.

    The record: dimension 2 says positively that no resolution ran
    (`refused-before-resolution`), its bindings are EXACTLY the recorder's
    bundle pin plus the class-declaration pin — minted the way `class_source`
    mints it, so it resolves to the exact bytes that declared the intent set
    — and NO request-contract pin, because none was resolved against (which
    is why plan 09's D-11 inference reads request-contract + constraint pins
    and never a class-declaration pin). Sabotage (recorded in the SUMMARY):
    drop the pin and the bindings assertion reds.
    """
    reader = _RecordingReader(booted_with_intents.fabric.handle.reader)
    fabric = dataclasses.replace(
        booted_with_intents.fabric,
        handle=_HandleWithReader(booted_with_intents.fabric.handle, reader),
    )
    resolver = _resolver(booted_with_intents, fabric=fabric)

    served = _ask(resolver, _request(intent="fixture-intent"))
    assert isinstance(served, ServedProduct)
    reads_for_the_served_product = len(reader.calls)
    assert reads_for_the_served_product > 0

    outcome = _ask(resolver, _request(intent="other"))
    assert isinstance(outcome, RefusalEnvelope)
    assert outcome.kind == "product-request-violation"
    assert outcome.reason == "class-mismatch"
    assert outcome.key == "intent"
    assert outcome.pre_assembly_lineage is None
    assert outcome.request.product_id == PRODUCT_CLASS
    # An addressing verdict costs nothing: no read beyond the served product's.
    assert len(reader.calls) == reads_for_the_served_product

    assert outcome.replay_reference != NO_REPLAY_REFERENCE
    record = DecisionReplayRecord.model_validate_json(
        booted_with_intents.store.get(
            content_address=booted_with_intents.store.resolve_uri(
                uri=outcome.replay_reference
            )
        )
    )
    assert ResolutionNotApplicable.model_validate_json(
        record.policy_bindings.request_resolution
    ) == ResolutionNotApplicable(reason="refused-before-resolution")
    class_pin = PolicyBinding(
        key=PRODUCT_CLASS_KEY,
        version=booted_with_intents.fabric.pins.version_for(PRODUCT_CLASS_KEY),
    )
    # The pin the manifest minted IS the declaration's content address — the
    # same address `class_source` carries on a defaulted value.
    assert class_pin.version == content_hash(resolver._declaration())
    bundle_pin = PolicyBinding(
        key=POLICY_BUNDLE_KEY,
        version=booted_with_intents.fabric.pins.version_for(POLICY_BUNDLE_KEY),
    )
    assert set(record.policy_bindings.bindings) == {bundle_pin, class_pin}
    assert all(
        binding.key != REQUEST_CONTRACT_KEY for binding in record.policy_bindings.bindings
    )
    # Dimension 1 says nothing was read; dimension 5 says no product came of it.
    assert record.context_fabric_snapshot.store_watermark == NO_FABRIC_READ
    assert record.content_generation_path.product_content_address == (
        NO_PRODUCT_ADDRESS
    )


def test_a_declared_empty_set_serves_none(booted_with_no_intents: _Booted) -> None:
    """F-1 a: *"An explicitly declared empty set means 'serves none.'"*"""
    outcome = _ask(_resolver(booted_with_no_intents), _request(intent="fixture-intent"))

    assert isinstance(outcome, RefusalEnvelope)
    assert outcome.kind == "product-request-violation"
    assert outcome.reason == "class-mismatch"
    assert outcome.key == "intent"


# --- behavior 1: a bad question is refused before the graph is touched -------


def test_a_question_the_class_does_not_answer_is_refused(booted: _Booted) -> None:
    outcome = _ask(_resolver(booted), _request(parameters={}))

    assert isinstance(outcome, RefusalEnvelope)
    assert outcome.kind == "product-request-violation"
    assert outcome.reason == "missing-required-parameter"
    assert outcome.key == THRESHOLD_PARAMETER


def test_the_refused_question_travels_with_its_own_identity(
    booted: _Booted,
) -> None:
    """`D-09`: a refusal stays auditable because the question survives it."""
    outcome = _ask(_resolver(booted), _request(parameters={}))

    assert isinstance(outcome, RefusalEnvelope)
    assert outcome.request.product_id == PRODUCT_CLASS
    assert outcome.request.product_version == PRODUCT_VERSION
    assert outcome.request.parameters == {}
    assert outcome.request.temporal_boundary == ASKED_AT
    # A request-conformity verdict precedes the graph entirely, so offering it
    # a lineage would be a category error rather than extra information.
    assert outcome.pre_assembly_lineage is None


def test_the_request_refusal_leg_never_reads_the_graph(booted: _Booted) -> None:
    """Asserted by observing the reader, never by timing."""
    reader = _RecordingReader(booted.fabric.handle.reader)
    fabric = dataclasses.replace(
        booted.fabric, handle=_HandleWithReader(booted.fabric.handle, reader)
    )

    outcome = _ask(_resolver(booted, fabric=fabric), _request(parameters={}))

    assert isinstance(outcome, RefusalEnvelope)
    assert reader.calls == [], (
        "a question this class does not answer must cost nothing: the conformity"
        f" verdict is reached before the graph is touched, and the reader saw"
        f" {reader.calls}"
    )


def test_a_tolerance_that_is_not_a_proportion_is_refused_at_the_boundary_not_as_a_409(
    booted_with_ceiling: _Booted,
) -> None:
    """WR-02 (Dave, 2026-09-02): a negative ``debt_tolerance`` is refused BY NAME at the boundary and never coerces the serve into a ``409``.

    The class declares a ceiling and the fixture scorer measures ``D_c = 0``,
    so before this ruling ``-1`` reached the debt gate as a
    "tightening", every product was refused ``declared-obligation-refusal``
    and ``declared`` read ``"-1"`` — a number no class declared. Now the
    request-conformity verdict names the parameter, carries no lineage
    (the graph was never touched), and the ``409`` family is never reached.

    **Re-derived at ``24.6-03``, and the verdict travels one step further
    back.** The conformity comparison now runs inside the resolution, over the
    EFFECTIVE request — defaults applied, policy bounds in force — rather than
    over the caller's raw parameters. Nothing about this case moves: the class
    declares no default for the tolerance and no constraint is registered here,
    so the effective value is the caller's ``-1``, and the interval refusal
    names it before the graph is touched exactly as before.

    Sabotage: restore acceptance of ``-1`` in ``refuse_request`` and this
    goes RED on the first assertion with ``kind == "declared-obligation-refusal"``.
    """
    outcome = _ask(
        _resolver(booted_with_ceiling),
        _request(parameters={THRESHOLD_PARAMETER: 1000, DEBT_TOLERANCE_PARAMETER: -1}),
    )

    assert isinstance(outcome, RefusalEnvelope)
    assert outcome.kind == "product-request-violation", outcome
    assert outcome.reason == "not-a-proportion"
    assert outcome.key == DEBT_TOLERANCE_PARAMETER
    assert outcome.pre_assembly_lineage is None
    assert "-1" not in outcome.fields.get("declared", "")


def test_a_proportion_tolerance_still_reaches_the_live_ceiling(
    booted_with_ceiling: _Booted,
) -> None:
    """The control for the test above: the ceiling class is LIVE, and a conformant tolerance is honored.

    ``D_c = 0`` under a tolerance of ``0`` serves (``0 > 0`` is false), so the
    served leg proves the boundary let a proportion through; the ceiling
    itself is proven live by the sibling structural-gate tests, and by the
    fact that a bypassed boundary turns the test above into a ``409``.

    **Re-derived at ``24.6-03``:** the number now reaches the gate as the
    *effective* tolerance — resolved with authority ``caller``, since no
    constraint is registered in this deployment — rather than as a raw request
    parameter the gate folds. The observable outcome is the same, which is the
    point: the sequence changed, the answer did not.
    """
    outcome = _ask(
        _resolver(booted_with_ceiling),
        _request(
            parameters={THRESHOLD_PARAMETER: 1000, DEBT_TOLERANCE_PARAMETER: Decimal("0")}
        ),
    )

    assert isinstance(outcome, ServedProduct), outcome


def test_the_success_leg_does_read_the_graph(booted: _Booted) -> None:
    """The control for the test above — a guard that cannot fire proves nothing.

    Without this, a resolver that never read the graph on *any* path would pass
    the refusal-leg assertion, and the assertion would be measuring nothing.
    """
    reader = _RecordingReader(booted.fabric.handle.reader)
    fabric = dataclasses.replace(
        booted.fabric, handle=_HandleWithReader(booted.fabric.handle, reader)
    )

    outcome = _ask(_resolver(booted, fabric=fabric), _request())

    assert isinstance(outcome, ServedProduct)
    assert reader.calls != []


# --- behavior 2: an answerable question yields a served product -------------


def test_an_answerable_question_yields_a_served_product(booted: _Booted) -> None:
    outcome = _ask(_resolver(booted), _request())

    assert isinstance(outcome, ServedProduct)
    assert isinstance(outcome.product, ContextProductContract)
    assert outcome.product.schema_name == PRODUCT_CLASS
    assert outcome.product.temporal_boundary == ASKED_AT
    assert outcome.product.expires_at == ASKED_AT + timedelta(
        seconds=PRODUCT_TTL_SECONDS
    )


def test_the_success_leg_assembles_the_fixtures_own_entity(booted: _Booted) -> None:
    """The positive control for the seeded fixture (``24.5-L-24``, ``24.6-L-06``).

    The success leg is a success leg because the traversal assembled the ONE
    entity the deployment's own signal batch carries. Since ``24.6-05`` an
    empty assembly is SERVED rather than refused, which makes this control
    more load-bearing than it was, not less: a fixture that quietly went green
    with ``"assembled": 0`` would now serve, and every assertion about the
    success leg would be an assertion about the empty case. The count is what
    tells the two apart.
    """
    outcome = _ask(_resolver(booted), _request())

    assert isinstance(outcome, ServedProduct)
    assert outcome.product.payload["assembled"] == 1


def test_the_served_products_replay_reference_resolves(booted: _Booted) -> None:
    """`DIV-2`: the reference is the whole reason the seam widened."""
    resolver = _resolver(booted)
    outcome = _ask(resolver, _request())

    assert isinstance(outcome, ServedProduct)
    assert isinstance(outcome.replay_ref, ArtifactRef)
    assert booted.store.exists(content_address=outcome.replay_ref.content_address)
    assert booted.store.get(content_address=outcome.replay_ref.content_address)


# --- behavior 3: a gate refusal is a value, not an exception ----------------


def test_a_gate_refusal_comes_back_as_an_envelope(booted: _Booted) -> None:
    """Gate 3 fires when the product outlives the class's declared ceiling."""
    outcome = _ask(
        _resolver(booted, product_ttl_seconds=MAX_TTL_SECONDS + 1), _request()
    )

    assert isinstance(outcome, RefusalEnvelope)
    assert outcome.kind == "ttl-refusal"
    assert outcome.reason == "ttl-bounds"


def test_a_gate_refusal_keeps_the_gates_own_typed_fields(booted: _Booted) -> None:
    """Constraint (a): nothing is flattened out on the way across the seam."""
    outcome = _ask(
        _resolver(booted, product_ttl_seconds=MAX_TTL_SECONDS + 1), _request()
    )

    assert isinstance(outcome, RefusalEnvelope)
    # Field PRESENCE is identical whatever disclosure withheld (`D-IMPL-253`
    # amendment 2 (4)): every key the gate declared is on the shell, and only
    # the VALUES a policy did not permit are replaced.
    assert "expires_at" in outcome.fields
    assert "max_ttl_seconds" in outcome.fields
    # The declared ceiling survives at `minimal` — a caller can act on it.
    assert str(MAX_TTL_SECONDS) in outcome.fields["max_ttl_seconds"]

    # The INTERNAL determination, read from the record the shell points at
    # (`24.6-08`). A gate refusal has a candidate behind it, so it has a real
    # lineage — and carrying it is what keeps the pre/post-assembly split
    # structural. The fixture registers no entitlement policy, so the shell
    # discloses at the safe default and the lineage does not cross.
    internal = _internal(booted, outcome)
    assert internal.pre_assembly_lineage is not None
    assert set(internal.fields) == set(outcome.fields)
    # The gate's own measurement is retained internally and withheld on the
    # shell, which is the whole shape of `D-IMPL-254`.
    assert internal.fields["expires_at"] != outcome.fields["expires_at"]
    assert internal.disclosure is None
    assert outcome.pre_assembly_lineage is None
    assert outcome.disclosure == "minimal"


def test_a_gate_refusal_serves_nothing_and_records_everything(
    booted: _Booted,
) -> None:
    """No product is delivered — and the decision IS recorded (``24.6-07``).

    **This assertion is the inverse of the one it replaces**, and the
    inversion is the row. It read *"no replay record is appended for a product
    that was never admitted"*, which was true of the composition and false of
    ``D-IMPL-253`` Q13: *"Refusal is itself a decision and deserves the same
    five-dimensional replay model. Do not create second-class replay."* A
    product that was never admitted is still a determination the fabric
    reached, and the thing it must not produce is a **delivery**, not a record.

    Both halves are asserted because neither implies the other: a composition
    could record and still hand back a servable shape, and one could return the
    shell and quietly append nothing — which is the state this row corrected.
    """
    resolver = _resolver(booted, product_ttl_seconds=MAX_TTL_SECONDS + 1)
    outcome = _ask(resolver, _request())

    assert isinstance(outcome, RefusalEnvelope)
    assert not isinstance(outcome, ServedProduct)
    # The decision is recorded, and the shell names where.
    assert outcome.replay_reference != NO_REPLAY_REFERENCE
    record = DecisionReplayRecord.model_validate_json(
        booted.store.get(
            content_address=booted.store.resolve_uri(uri=outcome.replay_reference)
        )
    )
    # A gate refusal has a real execution behind it, so dimension 1 is built
    # exactly as a served product's would be — the graph WAS read.
    assert record.context_fabric_snapshot.store_watermark != NO_FABRIC_READ
    # And dimension 5 says positively that no product came of it.
    assert record.content_generation_path.product_content_address == (
        NO_PRODUCT_ADDRESS
    )


# --- behavior 4: no delivery without a recorded decision --------------------


def test_a_failed_replay_append_yields_no_served_product(
    booted: _Booted, tmp_path: pathlib.Path
) -> None:
    store = _RefusingStore(tmp_path / "refusing-artifacts")
    resolver = _resolver(booted, artifact_store=store)

    with pytest.raises(OSError):
        _ask(resolver, _request())

    assert store.attempts >= 1, (
        "the store must have been reached: a composition that never attempted"
        " the append would pass this test without having the property"
    )


# --- behavior 5: two questions are two products -----------------------------


def test_two_parameter_values_produce_two_content_addresses(
    booted: _Booted,
) -> None:
    """`D-23`, re-asserted through the new seam."""
    resolver = _resolver(booted)
    low = _ask(resolver, _request(parameters={THRESHOLD_PARAMETER: 1000}))
    high = _ask(resolver, _request(parameters={THRESHOLD_PARAMETER: 2000}))

    assert isinstance(low, ServedProduct)
    assert isinstance(high, ServedProduct)
    assert content_hash(low.product) != content_hash(high.product)


# --- `R-11`: the product-gate seam, and where it runs ------------------------


def test_the_product_gate_seam_is_a_runtime_checkable_protocol() -> None:
    """`24.10-02` / `R-11`: the seam is a Protocol, on `debt_scorer`'s shape.

    `D-IMPL-282` option 1a names `debt_scorer` as the model, so the properties
    that make that seam what it is are asserted of this one: a
    ``runtime_checkable`` Protocol, exported from the module (a Protocol a
    deployment cannot import is a Protocol nothing can conform to on purpose),
    keyword-only, and returning ``str | None`` — never an identity, which is
    the Control Plane's half.
    """
    import typing

    from ccf.products.resolver import ProductGateProtocol

    assert "ProductGateProtocol" in resolver_module.__all__
    assert getattr(ProductGateProtocol, "_is_runtime_protocol", False), (
        "a Protocol that is not runtime_checkable cannot be asserted against"
        " at a wiring boundary, which is what `AssemblyDebtScorerProtocol` is"
    )

    signature = inspect.signature(ProductGateProtocol.__call__)
    parameters = tuple(signature.parameters)
    assert parameters == ("self", "candidate", "evidence"), parameters
    for name in ("candidate", "evidence"):
        assert (
            signature.parameters[name].kind is inspect.Parameter.KEYWORD_ONLY
        ), name
    assert signature.parameters["evidence"].default is None
    assert signature.return_annotation == "str | None", (
        "the callable returns a violation detail or nothing; a gate that"
        " returned its own identity could mislabel which gate refused"
    )
    hints = typing.get_type_hints(ProductGateProtocol.__call__)
    assert hints["candidate"] is ContextProductContract


def test_the_gate_runs_after_the_universal_gates_and_before_fitness() -> None:
    """`D-12`, observed in the source rather than asserted in a comment.

    The ruling is an ORDER — *"after candidate construction and before
    fitness/fulfillment"* — and an order is a property of where the call sits,
    so it is read off the module's own text. A behavioral test that a
    double-violating candidate yields the product-invariant refusal rather
    than the tolerance one lives in
    ``tests/products/test_runtime_product_gate.py``; this is the structural
    half, and it fails the moment somebody moves the call even if no shipped
    fixture happens to violate both at once.
    """
    source = pathlib.Path(resolver_module.__file__).read_text(encoding="utf-8")
    lines = source.splitlines()

    def line_of(fragment: str) -> int:
        matches = [i for i, line in enumerate(lines) if fragment in line]
        assert len(matches) == 1, (fragment, matches)
        return matches[0]

    admitted = line_of("gated = run_gates(")
    invariant = line_of("gate_violation = self.product_gate(")
    fitness = line_of("withheld = refuse_over_tolerance(")
    assert admitted < invariant < fitness, (admitted, invariant, fitness)


def test_a_wired_gate_that_admits_serves_and_the_candidate_is_the_product(
    booted: _Booted,
) -> None:
    """The seam is live and it is handed the ANSWER, not the view.

    The vacuity guard for every gate test: a resolver that never called its
    gate would pass any assertion about a gate that admits. This one records
    what it was handed and asserts the served product is that exact value —
    which is also the argument for ``candidate`` over ``view``, made
    observable rather than argued.
    """
    seen: list[ContextProductContract] = []

    def gate(
        *,
        candidate: ContextProductContract,
        evidence: ExecutionEvidence | None = None,
    ) -> str | None:
        seen.append(candidate)
        assert evidence is not None, (
            "the resolver always passes evidence; a resolver that decided"
            " per-gate whether to tell the truth about the search would be two"
            " seams wearing one name"
        )
        return None

    outcome = _ask(_resolver(booted, product_gate=gate), _request())

    assert isinstance(outcome, ServedProduct)
    assert len(seen) == 1, "the gate runs exactly once per determination"
    assert content_hash(seen[0]) == content_hash(outcome.product)


# --- behavior 6: nothing the deployment owns has a default ------------------


#: Every constructor argument, so the assertion below ranges over the whole set
#: rather than over a sample somebody chose. A field added to
#: :class:`~ccf.products.resolver.GovernedResolver` and not added here fails
#: the exhaustiveness check beside it.
DEPLOYMENT_OWNED_ARGUMENTS: tuple[str, ...] = (
    "fabric",
    "control_plane",
    "product_class_key",
    "request_contract_key",
    "operator_parameter_keys",
    "policy_bundle_key",
    "plan_factory",
    "debt_scorer",
    # `24.10-02` / `R-11`: the deployment's implementation of its class's own
    # declared invariant (`D-IMPL-282` option 1a). No default for
    # `debt_scorer`'s reason and for one of its own — `None` is a POSITIVE
    # statement that this class declares no runtime invariant, and a resolver
    # that defaulted it would let a class declare a gate that silently never
    # ran. `build_governed_resolver` refuses both halves of that mismatch at
    # build time; this class refuses the omission at construction.
    "product_gate",
    "artifact_store",
    "replay_record_class",
    "query_pin_class",
    "constraint_resolver",
    "capabilities",
    # 24.6-07: the one minting seam (`D-IMPL-253` Q13). No default, for every
    # other argument's reason — and for one of its own: a resolver that
    # defaulted its recorder into existence would be a delivery boundary that
    # decided, on its own authority, where a deployment's audit records land.
    "refusal_recorder",
    "max_ttl_seconds",
    "product_ttl_seconds",
)


def test_the_argument_enumeration_is_exhaustive() -> None:
    """A guard over a sample is a guard that stops covering what it names."""
    declared = tuple(f.name for f in dataclasses.fields(GovernedResolver))
    assert set(declared) == set(DEPLOYMENT_OWNED_ARGUMENTS)


@pytest.mark.parametrize("omitted", DEPLOYMENT_OWNED_ARGUMENTS)
def test_omitting_any_deployment_owned_value_is_a_construction_error(
    booted: _Booted, omitted: str
) -> None:
    """CLAUDE.md §6.4 — a default is a value nobody chose."""
    arguments = {
        name: value
        for name, value in _arguments(booted).items()
        if name != omitted
    }
    with pytest.raises(TypeError):
        GovernedResolver(**arguments)


def test_no_constructor_argument_carries_a_default() -> None:
    """The positive half: read off the dataclass rather than off a message."""
    for field in dataclasses.fields(GovernedResolver):
        assert field.default is dataclasses.MISSING, field.name
        assert field.default_factory is dataclasses.MISSING, field.name


# --- the address the resolver does not serve --------------------------------


def test_an_address_this_resolver_was_never_wired_to_serve_raises(
    booted: _Booted,
) -> None:
    """A mis-wiring is not a governed no, and must not read like one."""
    resolver = _resolver(booted)
    with pytest.raises(ProductNotResolvable):
        resolver(
            tenant=TENANT,
            product_class="fixture.some-other-class",
            version=PRODUCT_VERSION,
            perspective=PERSPECTIVE,
            request=_request(),
        )


def test_another_tenants_address_raises_rather_than_serving(
    booted: _Booted,
) -> None:
    resolver = _resolver(booted)
    with pytest.raises(ProductNotResolvable):
        resolver(
            tenant="some-other-tenant",
            product_class=PRODUCT_CLASS,
            version=PRODUCT_VERSION,
            perspective=PERSPECTIVE,
            request=_request(),
        )


def test_a_call_carrying_no_request_raises_rather_than_guessing(
    booted: _Booted,
) -> None:
    """The seam admits ``None``; this reference implementation does not.

    The argument list is copied from the door seam exactly, ``None`` included,
    so one resolver shape serves both. But this composition validates the
    request against the class's declared surface and derives the decision
    instant from it, and the SDK may invent neither — so a deployment wiring a
    request-less surface to this resolver has a wiring defect, and hears about
    it rather than receiving an answer to a question nobody asked.
    """
    with pytest.raises(ProductNotResolvable):
        _ask(_resolver(booted), None)


# --- helpers ----------------------------------------------------------------


def _arguments(booted: _Booted) -> dict[str, Any]:
    return {
        "fabric": booted.fabric,
        "control_plane": booted.control_plane,
        "product_class_key": PRODUCT_CLASS_KEY,
        "request_contract_key": REQUEST_CONTRACT_KEY,
        "operator_parameter_keys": (TRAVERSAL_KEY,),
        "policy_bundle_key": POLICY_BUNDLE_KEY,
        "plan_factory": _plan_factory,
        "debt_scorer": _debt_scorer,
        # `24.10-02` / `R-11`: the deployment's implementation of its class's
        # own declared invariant. `None` here because the fixture class
        # declares no gate — a POSITIVE value, stated rather than defaulted,
        # which is why the field carries no default on the dataclass.
        "product_gate": None,
        # 24.6-03: the Authority layer's two inputs. The reference resolver
        # over this fixture's own registry — which holds no policy constraint
        # and no entitlement policy, so it resolves defaults and caller values
        # and nothing else — and no technical capability, which is what a
        # SQLite-backed deployment reports.
        "constraint_resolver": ReferencePolicyConstraintResolver(
            control_plane=booted.control_plane,
            entitlement_key=product_entitlement_key(tenant_id=TENANT),
        ),
        "capabilities": (),
        # 24.6-07: the one seam every governed refusal this composition
        # produces reaches the replay writer through (`D-IMPL-253` Q13). The
        # SAME store the served path writes to — one writer, one store, and no
        # second writer to the graph — with the four required inputs and no
        # bundle pin, which is the shape a door-side helper wires too.
        "refusal_recorder": ReplayRefusalRecorder(
            artifact_store=booted.store,
            replay_record_class=REPLAY_RECORD_CLASS,
            tenant_id=TENANT,
            assembly_mode="algorithmic",
            # The bundle the manifest put in force, read the way
            # `build_governed_resolver` reads it — so this fixture wires the
            # recorder the way the shipped helper does rather than a simpler
            # way that would leave dimension 2 thinner on the refusal path
            # than on the served one.
            policy_bundle_pin=PolicyBinding(
                key=POLICY_BUNDLE_KEY,
                version=booted.fabric.pins.version_for(POLICY_BUNDLE_KEY),
            ),
        ),
        "artifact_store": booted.store,
        "replay_record_class": REPLAY_RECORD_CLASS,
        "query_pin_class": QUERY_PIN_CLASS,
        "max_ttl_seconds": MAX_TTL_SECONDS,
        "product_ttl_seconds": PRODUCT_TTL_SECONDS,
    }


class _HandleWithReader:
    """The booted handle with its reader swapped for an observer."""

    def __init__(self, inner: Any, reader: Any) -> None:
        self._inner = inner
        self.reader = reader

    @property
    def worker(self) -> Any:
        return self._inner.worker

    def close(self) -> None:
        self._inner.close()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)
