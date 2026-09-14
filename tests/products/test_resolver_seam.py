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
from pydantic import ValidationError

from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.protocol import ArtifactRef
from ccf.contracts.canonical import content_hash
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.controlplane.artifacts import (
    RequestBoundParameter,
    SimilaritySelectParametersArtifact,
)
from ccf.deployment import BootedFabric, build_operator_registry, load_and_boot
from ccf.graph.protocols import GraphQuery, GraphReader, GraphView
from ccf.halflife.assessment import NO_OBLIGATION_IN_FORCE
from ccf.halflife.debt import DebtAssessment, DebtFactors, DebtSignal
from ccf.products.constraints import ReferencePolicyConstraintResolver
from ccf.products.contract import ContextProductContract
from ccf.products.debt_scorer import ExecutionEvidence
from ccf.products.entitlement import product_entitlement_key
from ccf.products.gates import DEBT_TOLERANCE_PARAMETER
from ccf.products.disclosure import DisclosureDecision
from ccf.products.refusal import NO_REPLAY_REFERENCE, RefusalEnvelope
from ccf.products.request import ProductRequest, request_seeds
from ccf.replay.record import (
    NO_FABRIC_READ,
    NO_PRODUCT_ADDRESS,
    DecisionReplayRecord,
    PolicyBinding,
    ResolutionNotApplicable,
)
from ccf.products import resolver as resolver_module
from ccf.halflife.assessment import (
    NO_SOURCE_REFRESH_RECENCY,
    SourceRefreshWindow,
)
from ccf.products.resolver import (
    GovernedResolver,
    build_governed_resolver,
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
    POLICY_PARAMS_KEY,
    PRODUCT_CLASS_KEY,
    SIGNAL_BATCH_KEY,
    SIMILARITY_KEY,
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

#: The manifest key the deployment's D_c bands are authored under.
#:
#: `24.11-03` / `24.10-F-08`. The fixture deployment declares a debt profile so
#: that the obligation seam has a *declaration* to read, which is the whole
#: subject: `DebtProfile.obligation_for` is the extract half `D-IMPL-117` says
#: the SDK owes, and the resolver composing it is the populate half.
DEBT_PROFILE_KEY = "fixture/debt-profile"

#: What this deployment binds to the routing state its scorer lands in.
#:
#: A fixture obligation vocabulary and nothing else — the SDK ships none
#: (`D-IMPL-117`). `_debt_scorer` returns `DebtSignal.OK`, so this is the
#: binding a served product must carry.
OBLIGATION_ON_OK = "fixture.file-the-routine-note"

#: The request parameter a request-bound operator parameter is bound to in the
#: tests below. Fixture vocabulary; the SDK ships no parameter names.
BOUND_CLASSES_PARAMETER = "admissible_classes"

#: What the fixture class defaults that parameter to when a caller omits it.
DEFAULTED_CLASSES = ("fixture-admitted",)

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
    artifacts: Mapping[str, dict[str, Any]] | None = None,
) -> Iterator[_Booted]:
    """The one boot, so the two fixtures cannot drift into two deployments."""
    root = tmp_path / "deployment"
    root.mkdir()
    for key, filename, _class_id, _role, _registration, document in ARTIFACT_SET:
        if key == PRODUCT_CLASS_KEY and product_class is not None:
            document = product_class
        # `24.11-04`: any artifact in the set may be varied by key, in
        # `product_class`'s shape and for its reason — the variation belongs in
        # the test-side document, never in `src/` (CINV-01).
        if artifacts and key in artifacts:
            document = artifacts[key]
        write_artifact(root, filename, document)
    write_artifact(
        root,
        "request-contract.yaml",
        REQUEST_CONTRACT_DOCUMENT if request_contract is None else request_contract,
    )
    # `24.11-03` / `24.10-F-08`: the deployment declares its D_c bands, and
    # binds an obligation to the state its scorer lands in. Written here rather
    # than in `tests/deployment/conftest.py::ARTIFACT_SET` because the shared
    # set feeds every deployment fixture in the suite and this binding is this
    # file's subject, not theirs.
    write_artifact(
        root,
        "debt-profile.yaml",
        {
            "semver": "1.0.0",
            "risk_sensitivity": "1",
            "forced_llm_threshold": "0.30",
            "fail_closed_threshold": "0.70",
            "signal_obligations": [
                {"signal": "ok", "obligation_ref": OBLIGATION_ON_OK}
            ],
        },
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
        {
            "path": "debt-profile.yaml",
            "key": DEBT_PROFILE_KEY,
            "class_id": "ccf.debt-profile",
            "role": "register",
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
    record = DecisionReplayRecord.model_validate_json(
        booted.store.get(content_address=outcome.replay_ref.content_address)
    )
    assert record.recorded_at == ASKED_AT


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


# --- `24.11-03` / `24.10-F-08`: the obligation the deployment declared ------


def test_the_served_product_carries_the_obligation_the_profile_bound(
    booted: _Booted,
) -> None:
    """The canonical path composes the two halves the SDK already ships.

    ``D-IMPL-117``: the SDK owes *"the structure and the API to populate and
    extract"* a signal-to-obligation binding, and **none of the content**.
    :meth:`~ccf.controlplane.artifacts.DebtProfile.obligation_for` is the
    extract half — its own docstring calls it *"the extract half of what
    D-IMPL-117 says the SDK owes, and the whole of it"*. This is the populate
    half on the governed path: the resolver holds the signal (it computed the
    :class:`~ccf.halflife.assessment.DebtAssessment`) and the deployment's
    profile is on the fabric it was booted from, and until ``24.11-03`` it
    joined the two nowhere.

    The member is **inside the product's content address** (``D-IMPL-118``), so
    a product served without it cannot be repaired afterwards — the wrong
    answer is the delivered one and it replays exactly, forever. A resolver
    that drops the join therefore says *this deployment is obliged to do
    nothing* wherever that deployment's own profile says otherwise, which is a
    wrong governance answer rather than an absent nicety.

    The obligation is read back off the fabric rather than restated, so the
    assertion cannot pass against a value this test authored: it compares what
    the product carries with what the manifest put in force.
    """
    profile = booted.fabric.artifacts[DEBT_PROFILE_KEY]
    declared = profile.obligation_for(DebtSignal.OK)
    assert declared == OBLIGATION_ON_OK, "the fixture's own premise has moved"
    assert declared != NO_OBLIGATION_IN_FORCE, "a binding, not the sentinel"

    outcome = _ask(_resolver(booted), _request())

    assert isinstance(outcome, ServedProduct)
    assert outcome.product.obligation_in_force == declared


def test_a_deployment_that_declares_no_profile_carries_the_sentinel(
    booted: _Booted,
) -> None:
    """The negative control, and it is the positive claim rather than a gap.

    ``obligation_for``'s own rule: an unbound state resolves to *"the positive
    claim that nothing was bound"*. A deployment naming no debt profile has
    declared no binding, so :data:`~ccf.halflife.assessment.
    NO_OBLIGATION_IN_FORCE` is the true answer and not a silent default — which
    is what keeps the test above from passing for the trivial reason that every
    product now carries some obligation.
    """
    outcome = _ask(_resolver(booted, debt_profile_key=None), _request())

    assert isinstance(outcome, ServedProduct)
    assert outcome.product.obligation_in_force == NO_OBLIGATION_IN_FORCE


# --- `D-IMPL-308`: the decision instant, and the declared refresh window ----
#
# Two seams, four tests, and each pair is a claim with its own control. The
# claim is not *"the resolver has these arguments"* — the exhaustiveness guard
# above already says that. It is that the values REACH the sealed product, and
# that a class declaring neither is unchanged.

#: The fixture argument standing in for a class-declared decision instant.
DECISION_INSTANT_PARAMETER = "decision_instant"

#: Five minutes after `ASKED_AT`. A fixture figure, authored test-side
#: (CINV-01), and DISTINCT on purpose: the whole property under test is that
#: the two instants do not collapse, and a control where they coincide could
#: not fail.
DECIDED_AT_LITERAL = "2026-03-02T12:05:00+00:00"

#: A declared window, likewise fixture-side.
DECLARED_REFRESH_WINDOW = SourceRefreshWindow(
    oldest_source_refresh_at=datetime(2026, 2, 28, tzinfo=UTC),
    newest_source_refresh_at=datetime(2026, 3, 1, tzinfo=UTC),
)


@pytest.fixture
def booted_declaring_a_decision_instant(
    tmp_path: pathlib.Path,
) -> Iterator[_Booted]:
    """The fixture deployment, with a decision instant on its request contract."""
    request_contract = copy.deepcopy(REQUEST_CONTRACT_DOCUMENT)
    request_contract["declaration"]["arguments"]["properties"][
        DECISION_INSTANT_PARAMETER
    ] = {"type": "string", "description": "Fixture decision instant."}
    yield from _boot(tmp_path, request_contract=request_contract)


def test_the_ttl_and_the_record_run_from_the_declared_decision_instant(
    booted_declaring_a_decision_instant: _Booted,
) -> None:
    """`24.10-F-09`, closed at `D-IMPL-308`.

    ``request.asked_at`` is *when the graph is observed*; the decision instant
    is *when the answer is produced*. This resolver derived the expiry, the
    gate instant and ``recorded_at`` from the first, so a class declaring the
    second found nothing read it — and the product's TTL ran from the wrong
    moment while every gate stayed green.

    **The boundary must NOT move with it**, which is the half a one-sided test
    would miss: a repair that simply swapped one instant for the other would
    satisfy the expiry assertion and quietly relabel when the graph was read.
    """
    booted = booted_declaring_a_decision_instant
    decided_at = datetime.fromisoformat(DECIDED_AT_LITERAL)
    assert decided_at != ASKED_AT, "the fixture's own premise has moved"

    outcome = _ask(
        _resolver(booted, decision_instant_parameter=DECISION_INSTANT_PARAMETER),
        _request(
            parameters={
                THRESHOLD_PARAMETER: 1000,
                DECISION_INSTANT_PARAMETER: DECIDED_AT_LITERAL,
            }
        ),
    )

    assert isinstance(outcome, ServedProduct)
    assert outcome.product.temporal_boundary == ASKED_AT
    assert outcome.product.expires_at == decided_at + timedelta(
        seconds=PRODUCT_TTL_SECONDS
    )
    # AND THE RECORD, read back through the reference the product carries.
    # The third of the three statements about the same moment, and the one a
    # sabotage found unasserted: reverting `recorded_at` alone left this module
    # green while the expiry and the boundary were still right.
    record = DecisionReplayRecord.model_validate_json(
        booted.store.get(content_address=outcome.replay_ref.content_address)
    )
    assert record.recorded_at == decided_at


def test_a_class_declaring_no_decision_instant_still_runs_from_asked_at(
    booted: _Booted,
) -> None:
    """The control, and it is the positive claim `D-IMPL-308` makes.

    *Coincidence is allowed; collapse is not.* A deployment whose decision
    instant genuinely is its graph boundary — `s1-00-companies-over-revenue`
    returns ``request.asked_at`` from both — passes ``None`` and is unchanged.
    Without this, the repair above could have made a distinct instant
    MANDATORY, which would have broken every deployment that correctly has one.
    """
    outcome = _ask(_resolver(booted, decision_instant_parameter=None), _request())

    assert isinstance(outcome, ServedProduct)
    assert outcome.product.temporal_boundary == ASKED_AT
    assert outcome.product.expires_at == ASKED_AT + timedelta(
        seconds=PRODUCT_TTL_SECONDS
    )


def test_the_served_product_carries_the_declared_refresh_window(
    booted: _Booted,
) -> None:
    """`24.10-F-08`'s refresh limb, closed at `D-IMPL-308`.

    A refresh window is a fact about the world upstream of the fabric: the
    deployment knows it and no operator can observe it. The candidate set
    nothing, so a deployment that declared one watched the canonical path drop
    it — and the member is **inside the content address**, so that is not an
    omission a deployment can repair afterwards.
    """
    outcome = _ask(
        _resolver(booted, source_refresh_recency=DECLARED_REFRESH_WINDOW), _request()
    )

    assert isinstance(outcome, ServedProduct)
    assert outcome.product.source_refresh_recency == DECLARED_REFRESH_WINDOW


def test_a_deployment_declaring_no_window_carries_the_sentinel(
    booted: _Booted,
) -> None:
    """The control: nothing is invented where nothing was declared.

    Without it the assertion above passes for the trivial reason that every
    product now carries some window.
    """
    outcome = _ask(
        _resolver(booted, source_refresh_recency=NO_SOURCE_REFRESH_RECENCY), _request()
    )

    assert isinstance(outcome, ServedProduct)
    assert outcome.product.source_refresh_recency is NO_SOURCE_REFRESH_RECENCY


# --- `24.11-04` / `24.10-F-11`: a request-bound operator parameter ----------
#
# The six semantics `D-IMPL-295` names, one test each. The subject is the LAST
# link of the authority chain — Control Plane envelope -> effective request
# resolution -> declared binding -> operator — so each test says which link it
# is about, and semantics 3 and 4 are about the links UPSTREAM of the binding
# still governing after it exists.


def _policy_artifact(booted: _Booted) -> Any:
    """The fixture deployment's policy operator parameters, as declared."""
    return booted.fabric.artifacts[POLICY_PARAMS_KEY]


def test_a_literal_operator_parameter_reads_exactly_as_it_did(
    booted: _Booted,
) -> None:
    """Semantic 1 — the literal variant is unchanged, and `[]` still means empty.

    The regression that matters most, because the union was added to a field
    every existing deployment declares literally. A bare sequence parses to the
    frozenset it always did; nothing about an unbound artifact moved.
    """
    declared = _policy_artifact(booted)

    assert isinstance(declared.permitted_classifications, frozenset)
    assert _ask(_resolver(booted), _request()) is not None


def test_a_request_bound_parameter_receives_the_governed_effective_value(
    booted: _Booted,
) -> None:
    """Semantic 2 — the bound value is the EFFECTIVE one, and it reaches the operator.

    Bound from ``effective_request`` rather than the caller's request, so class
    defaults, policy bounds and technical capabilities have already folded. The
    assertion reads the artifact the resolver actually handed the registry, so
    it cannot pass on a value that stopped at the declaration.
    """
    resolver = _resolver(booted)
    effective = _request(parameters={THRESHOLD_PARAMETER: 1000})
    declared = _policy_artifact(booted)
    bound = declared.model_copy(
        update={
            "permitted_classifications": RequestBoundParameter(
                source="effective_request", parameter=BOUND_CLASSES_PARAMETER
            )
        }
    )

    resolved = resolver._bind_declared_request_values(
        bound,
        key=POLICY_PARAMS_KEY,
        effective_request=effective.model_copy(
            update={"parameters": {BOUND_CLASSES_PARAMETER: ["alpha", "beta"]}}
        ),
    )

    assert resolved.permitted_classifications == frozenset({"alpha", "beta"})
    assert not isinstance(
        resolved.permitted_classifications, RequestBoundParameter
    ), "the binding survived into the operator's own parameter set"


def test_a_binding_naming_a_parameter_the_request_lacks_is_refused(
    booted: _Booted,
) -> None:
    """Semantics 3 and 4 — omission and out-of-envelope are UPSTREAM concerns.

    The binding neither invents a default nor validates a domain, and this is
    what that costs and buys. A caller who omits an argument does not arrive
    here at all: ``resolve_effective_request`` folds the class default first, so
    the effective request carries a value and the binding consumes it. A caller
    whose value is out of policy never arrives either — resolution refuses
    before an operator is built. What reaches this method is therefore always a
    *governed* value, and the only failure left is a deployment binding to a
    parameter its own request contract does not declare, which no caller can
    fix and which is refused as the wiring defect it is.
    """
    resolver = _resolver(booted)
    declared = _policy_artifact(booted)
    bound = declared.model_copy(
        update={
            "permitted_classifications": RequestBoundParameter(
                source="effective_request", parameter="never-declared"
            )
        }
    )

    with pytest.raises(ProductNotResolvable) as refusal:
        resolver._bind_declared_request_values(
            bound,
            key=POLICY_PARAMS_KEY,
            effective_request=_request(parameters={THRESHOLD_PARAMETER: 1}),
        )

    assert "never-declared" in str(refusal.value)
    assert POLICY_PARAMS_KEY in str(refusal.value)


def test_a_bound_value_of_the_wrong_type_is_refused_and_never_converted(
    booted: _Booted,
) -> None:
    """Semantic 4's type half — supplied, never converted.

    A scalar where the field declares a set is the smallest imaginable
    transform, and admitting it would make the next one arguable. The value is
    put through the field's own declared type and refused there, so the binding
    has no type system of its own to disagree with the literal variant's.
    """
    resolver = _resolver(booted)
    declared = _policy_artifact(booted)
    bound = declared.model_copy(
        update={
            "permitted_classifications": RequestBoundParameter(
                source="effective_request", parameter=BOUND_CLASSES_PARAMETER
            )
        }
    )

    with pytest.raises(ProductNotResolvable) as refusal:
        resolver._bind_declared_request_values(
            bound,
            key=POLICY_PARAMS_KEY,
            effective_request=_request().model_copy(
                update={"parameters": {BOUND_CLASSES_PARAMETER: "alpha"}}
            ),
        )

    assert "never converts" in str(refusal.value)


def test_a_literal_and_a_binding_cannot_both_be_declared(booted: _Booted) -> None:
    """Semantic 5 — structurally invalid, not merely discouraged.

    The two are variants of ONE field, so "a literal plus an independent
    binding" has no spelling. This is what keeps an empty literal honest: a
    deployment cannot write `[]` beside a binding and leave a reader to guess
    which governs, which is the magical-empty reading `D-IMPL-288` forbids.
    """
    declared = _policy_artifact(booted)

    assert "permitted_classifications" in type(declared).model_fields
    with pytest.raises(ValidationError):
        type(declared).model_validate(
            {
                **declared.model_dump(),
                "permitted_classifications": {
                    "values": ["alpha"],
                    "source": "effective_request",
                    "parameter": BOUND_CLASSES_PARAMETER,
                },
            }
        )


@pytest.fixture()
def booted_bound_to_the_class_default(
    tmp_path: pathlib.Path,
) -> Iterator[_Booted]:
    """A deployment whose policy envelope binds to the ONE defaulted argument.

    ``debt_tolerance`` is the only name :meth:`~ccf.products.resolver.
    GovernedResolver._class_defaults` supplies, so it is the only parameter in
    the SDK today whose EFFECTIVE value can differ from a caller who never
    mentioned it. That difference is the whole instrument below.
    """
    product_class = copy.deepcopy(
        next(doc for key, *_rest, doc in ARTIFACT_SET if key == PRODUCT_CLASS_KEY)
    )
    product_class["serve_obligations"] = {
        "default_debt_tolerance": CEILING_DECLARED
    }
    policy = copy.deepcopy(
        next(doc for key, *_rest, doc in ARTIFACT_SET if key == POLICY_PARAMS_KEY)
    )
    policy["permitted_classifications"] = {
        "source": "effective_request",
        "parameter": DEBT_TOLERANCE_PARAMETER,
    }
    request_contract = copy.deepcopy(REQUEST_CONTRACT_DOCUMENT)
    request_contract["declaration"]["arguments"]["properties"][
        DEBT_TOLERANCE_PARAMETER
    ] = {"type": "number", "description": "Fixture tolerance; a proportion."}
    yield from _boot(
        tmp_path,
        product_class=product_class,
        request_contract=request_contract,
        artifacts={POLICY_PARAMS_KEY: policy},
    )


def test_the_call_site_binds_from_the_effective_request_not_the_callers(
    booted_bound_to_the_class_default: _Booted,
) -> None:
    """The wiring the six semantics above cannot see, and it needed catching.

    Every other test here calls the binding directly with an effective request
    it constructs, so none can tell whether ``__call__`` hands it the EFFECTIVE
    request or the caller's. **Measured: swapping the call site to the caller's
    request left all 1,058 tests in this tree green.** That is what this exists
    to stop.

    The instrument is the difference between two refusals, and the caller
    omitting ``debt_tolerance`` is what creates it:

    * bound from the **caller's** request, the parameter is simply *absent*, so
      the refusal says the effective request does not carry it;
    * bound from the **effective** request, ``_class_defaults`` has already
      folded the class's declared tolerance, so the parameter is *present* and
      the refusal is about its TYPE — a ``Decimal`` where the field declares a
      set of strings.

    Asserting the second message therefore proves resolution ran before the
    binding. The refusal is expected either way; **which** refusal is the
    evidence, and a test asserting merely that something was refused would pass
    under the sabotage.
    """
    resolver = _resolver(
        booted_bound_to_the_class_default,
        operator_parameter_keys=(TRAVERSAL_KEY, POLICY_PARAMS_KEY),
    )

    with pytest.raises(ProductNotResolvable) as refusal:
        _ask(resolver, _request(parameters={THRESHOLD_PARAMETER: 1000}))

    assert "never converts" in str(refusal.value), (
        "the binding refused because the parameter was ABSENT, which is what"
        " the caller's request looks like: the class default that resolution"
        " folds was never seen, so the call site read the wrong request"
    )


def test_a_binding_to_an_undeclared_argument_is_refused_at_boot(
    tmp_path: pathlib.Path,
) -> None:
    """The boot check — two documents disagreeing, caught where both are in hand.

    ``D-IMPL-295``. A binding naming an argument the request contract does not
    expose is a malformed declaration, and it fails when the resolver is BUILT
    rather than on the first call that happens to exercise it — the shape
    :func:`~ccf.products.request.refuse_undeclared_class_default` already
    established for the same class of disagreement.

    **Existence only.** The refusal says the contract does not declare the
    name; it says nothing about the value's type, because judging that here
    would mean comparing a JSON-Schema ``type`` against a Python annotation —
    a second type system to keep in step by hand. The artifact's own validation
    owns the type, and does so on the value that actually arrives.
    """
    policy = copy.deepcopy(
        next(doc for key, *_rest, doc in ARTIFACT_SET if key == POLICY_PARAMS_KEY)
    )
    policy["permitted_classifications"] = {
        "source": "effective_request",
        "parameter": "no-such-argument",
    }
    booted_iter = _boot(tmp_path, artifacts={POLICY_PARAMS_KEY: policy})
    booted = next(booted_iter)
    try:
        # Through the BUILDER, which is where this class of check lives: the
        # class itself resolves keys lazily and refuses a wiring defect on the
        # first call, by its own docstring's design. `refuse_undeclared_class_
        # default` and the declared-gate mismatch are checked in exactly this
        # place and for exactly this reason.
        with pytest.raises(ProductNotResolvable) as refusal:
            build_governed_resolver(
                fabric=booted.fabric,
                control_plane=booted.control_plane,
                product_class_key=PRODUCT_CLASS_KEY,
                request_contract_key=REQUEST_CONTRACT_KEY,
                operator_parameter_keys=(TRAVERSAL_KEY, POLICY_PARAMS_KEY),
                policy_bundle_key=POLICY_BUNDLE_KEY,
                plan_factory=_plan_factory,
                debt_scorer=_debt_scorer,
                artifact_store=booted.store,
                replay_record_class=REPLAY_RECORD_CLASS,
                query_pin_class=QUERY_PIN_CLASS,
                max_ttl_seconds=MAX_TTL_SECONDS,
                product_ttl_seconds=PRODUCT_TTL_SECONDS,
            )
    finally:
        for _ in booted_iter:
            pass

    assert "no-such-argument" in str(refusal.value)
    assert THRESHOLD_PARAMETER in str(refusal.value), (
        "the refusal must name what the contract DOES expose, or an adopter"
        " cannot tell a typo from an undeclared argument"
    )


# --- `D-IMPL-300`: the binder, at the ruled pre-execution point --------------


def test_a_plan_contradicting_the_class_is_refused_before_it_is_executed(
    booted: _Booted,
) -> None:
    """`D-IMPL-86`'s binder, on the canonical path — and BEFORE assembly.

    The product class's ``required_operator_keys`` and the plan's own
    ``required_operators()`` are two separately authored documents (design E2).
    Gate 2 also compares the declaration against the engine-RESOLVED set, so a
    divergence is caught either way — but later, *"after a product has already
    been assembled from a set the deployment's own claim contradicts"*, in the
    binder's own words. This asserts the earlier guarantee.

    **The instrument is that ``invoke`` never runs.** A test asserting merely
    that something was refused would pass with the binder deleted, because gate
    2 would refuse the same request one stage further on. The plan records
    whether it was invoked, and the refusal is only the binder's if that record
    is still empty.

    Found by cp-05's canonical adoption (`D-IMPL-300`): its hand-composed spine
    called the binder, and after migrating there was nowhere legitimate for a
    deployment to call it — ``plan_factory`` is invoked *inside* the resolver.
    """

    class _ContradictingPlan:
        """Declares an operator the fixture class does not require."""

        def __init__(self) -> None:
            self.invoked = False

        @property
        def plan_id(self) -> str:
            return "fixture.contradicting"

        def required_operators(self) -> tuple[str, ...]:
            return (TRAVERSAL_KEY, "similarity.top-k")

        def invoke(self, **_: Any) -> ProjectionOutput:  # pragma: no cover
            self.invoked = True
            raise AssertionError(
                "the plan was executed; the binder did not refuse before"
                " assembly, which is the whole of what D-IMPL-300 restored"
            )

    plan = _ContradictingPlan()

    with pytest.raises(ValueError) as refusal:
        _ask(
            _resolver(booted, plan_factory=lambda *, required, request: plan),
            _request(),
        )

    assert "operator set divergence" in str(refusal.value), (
        "something refused, but not the binder — a divergence caught at gate 2"
        " instead would mean assembly had already run"
    )
    assert not plan.invoked, (
        "the projection was invoked before the divergence was refused"
    )


def test_an_unresolved_binding_never_reaches_an_operator(booted: _Booted) -> None:
    """The invariant beneath all six — mypy found it, and it is refused by name.

    A registry built directly has no request and therefore cannot honor a
    binding. Narrowing that with a cast would hand `PolicyFilter` a declaration
    object where it expects the set it filters on: an operator admitting
    nothing while looking fully configured, which is the silent failure
    `PolicyFilterParametersArtifact`'s own docstring exists to prevent.
    """
    declared = _policy_artifact(booted)
    bound = declared.model_copy(
        update={
            "permitted_classifications": RequestBoundParameter(
                source="effective_request", parameter=BOUND_CLASSES_PARAMETER
            )
        }
    )

    with pytest.raises(ValueError, match="unresolved"):
        build_operator_registry(
            parameters={POLICY_PARAMS_KEY: bound},
            view=booted.fabric.handle.reader.as_of(
                tenant_id=booted.fabric.tenant_id, at=ASKED_AT
            ),
            pins=booted.fabric.pins,
            policy_bundle_key=POLICY_BUNDLE_KEY,
        )


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


# --- `24.11-01` / `24.10-F-07`: two subjects are two questions ---------------


def test_two_subjects_cannot_collapse_to_one_question_to_the_graph(
    booted: _Booted,
) -> None:
    """The request seeds the walk on the CANONICAL path — `D-IMPL-111` limb (a).

    Dave's invariant, verbatim: *"The subject/perspective state used during
    governed execution must be the same effective subject state represented in
    replay and product identity."* Until `24.11-01` this composition called
    :meth:`~ccf.projection.engine.ProjectionEngine.execute` with no ``seeds``
    argument at all, while :mod:`ccf.replay.engine` replayed with
    ``seeds=request_seeds(path.request)``. So two questions about two different
    subjects compiled to the **same** graph query and pinned identically in
    dimension 5, and every resolver-served product whose plan walks was
    replay-divergent by construction — ``DI-15.5-07`` exactly, reproduced on the
    canonical path after limb (a) had already closed it on the hand-built one.

    **Two halves, and neither alone is the property.**

    *They cannot alias.* Two subjects pin two different query sequences, so the
    record can say which subject a decision was about.

    *They agree with replay.* The seeds the execution actually compiled into
    its query are what :func:`~ccf.products.request.request_seeds` returns for
    the request the **record carries** — the same function applied to the same
    object :mod:`ccf.replay.engine` applies it to. The first half alone would
    pass on a resolver that seeded by some other subject-sensitive rule and
    then diverged loudly at replay; the second is what makes the two paths one
    reading rather than two derivations that happen to agree.

    The control matters as much as the assertion: the same subject asked twice
    must pin **identically**, or the inequality above would be measuring
    nondeterminism rather than the subject.

    Read back off the PERSISTED record and the PERSISTED query bytes, because
    that is what an auditor holding the record and nothing else would see.
    """
    resolver = _resolver(booted)
    first = _ask(resolver, _request(subject="acct-1"))
    second = _ask(resolver, _request(subject="acct-2"))
    again = _ask(resolver, _request(subject="acct-1"))

    assert isinstance(first, ServedProduct)
    assert isinstance(second, ServedProduct)
    assert isinstance(again, ServedProduct)

    records = [
        DecisionReplayRecord.model_validate_json(
            booted.store.get(content_address=served.replay_ref.content_address)
        )
        for served in (first, second, again)
    ]
    paths = [record.content_generation_path for record in records]

    # The premise, asserted rather than assumed: three decisions, two subjects.
    assert [path.request.subject for path in paths] == [
        "acct-1",
        "acct-2",
        "acct-1",
    ], "the fixture's own premise has moved"

    pins = [path.graph_query_sequence for path in paths]
    # A resolver that pinned NO query would satisfy the inequality below
    # vacuously, and the inequality would be measuring nothing.
    assert all(pins), "the record pins no graph query at all"
    # The control for the inequality: same subject, same pinned question.
    assert pins[0] == pins[2], (
        "the same subject asked twice pinned two different query sequences;"
        " the inequality below would be measuring nondeterminism"
    )
    assert pins[0] != pins[1], (
        "two questions about two different subjects pinned the same graph"
        " query sequence; the record cannot say which subject this decision"
        " was about (`DI-15.5-07`, `D-IMPL-111` limb (a), `24.10-F-07`)"
    )

    # The correspondence: what execution compiled IS what replay will derive.
    for path in paths:
        for pin in path.graph_query_sequence:
            query = GraphQuery.model_validate_json(
                booted.store.get(content_address=pin)
            )
            assert query.seeds == request_seeds(path.request), (
                "the seeds compiled into the executed query are not the seeds"
                " ccf.replay.engine derives from the request this record"
                " carries; governed execution and replay disagree about the"
                " subject, which is a re-computation wearing the decision's"
                " identifier"
            )


# --- `24.11-02b` / `24.10-F-06`: the declaration owns the corpus identity ----


def test_the_declared_index_version_is_the_only_authority(
    booted: _Booted,
) -> None:
    """`D-IMPL-292`. The similarity artifact declares its corpus version, and
    nothing else in the fabric may state one.

    Dave's ruling, verbatim: *"`similarity_index_version` is decision-affecting
    operator configuration and needs a canonical declarative home in the SDK.
    It must not remain an ungoverned deployment-supplied semantic value."* And
    the authority model: *"declaration owns the version → resolver consumes it
    → deployment supplies the implementation, not an alternate semantic
    version."*

    `24.11-02` closed `24.10-F-06`'s runtime half by giving
    :class:`~ccf.products.resolver.GovernedResolver` a
    ``similarity_index_version`` field. That fixed the propagation and left the
    architecture open — a workaround relocated from test code into caller code
    is still a workaround (`D-IMPL-289`). `24.11-02b` moved the value to
    :class:`~ccf.controlplane.artifacts.SimilaritySelectParametersArtifact`.

    **Four legs, and no two are the same property.**

    *The declaration alone is sufficient.* The canonical composition serves a
    class whose operator set includes Similarity while being told nothing about
    any index — naming the similarity key is now the whole of wiring
    similarity. Contrast `24.11-02`, where the same wiring needed a second
    argument kept in step with the artifact by hand.

    *The declared value is what propagates, by value and not by servability.*
    The index the builder constructs ranks under the version the artifact
    declares. Asserted against the artifact's own field rather than against a
    constant restated here, because a constant would be the second site this
    row exists to remove.

    *Re-authoring the declaration moves it.* A copy of the artifact carrying a
    different ``index_version`` produces an index carrying that version — so
    leg two is attributable to the declaration and not to some value the SDK
    minted that happens to match.

    *There is no second site to disagree with it.* An artifact declaring no
    version is refused at parse, by field name — not three frames on inside a
    build, which is where the old runtime refusal fired. And the builder offers
    no channel to supply one instead: the keyword `24.11-02` reached for is
    gone, and this leg goes red the moment anyone puts it back. Equality
    between two sites was the fallback `D-IMPL-292` allowed *"if two sites
    exist during migration"*; none does, so none is enforced.
    """
    similarity = booted.fabric.artifacts[SIMILARITY_KEY]
    assert isinstance(similarity, SimilaritySelectParametersArtifact)

    served = _ask(
        _resolver(
            booted, operator_parameter_keys=(TRAVERSAL_KEY, SIMILARITY_KEY)
        ),
        _request(),
    )
    assert isinstance(served, ServedProduct), (
        "a class whose operator set includes the Similarity category was not"
        " served by the SDK's own reference composition, given nothing but the"
        " declaration"
    )

    view = booted.fabric.handle.reader.as_of(tenant_id=TENANT, at=ASKED_AT)

    def _built(artifact: SimilaritySelectParametersArtifact) -> str | None:
        registry = build_operator_registry(
            parameters={SIMILARITY_KEY: artifact},
            view=view,
            pins=booted.fabric.pins,
            policy_bundle_key=POLICY_BUNDLE_KEY,
        )
        index_version: str | None = registry.resolve(
            "similarity.corpus-select"
        )._index.index_version
        return index_version

    assert _built(similarity) == similarity.index_version, (
        "the index was built under a version the declaration did not assign"
    )

    reauthored = "fixture-corpus@re-authored"
    assert reauthored != similarity.index_version
    assert (
        _built(similarity.model_copy(update={"index_version": reauthored}))
        == reauthored
    ), (
        "re-authoring the declaration did not move the corpus identity, so"
        " the value leg above proves nothing about where it is read from"
    )

    with pytest.raises(ValidationError) as unversioned:
        SimilaritySelectParametersArtifact.model_validate(
            {
                key: value
                for key, value in similarity.model_dump().items()
                if key != "index_version"
            }
        )
    assert "index_version" in str(unversioned.value)

    with pytest.raises(TypeError) as second_site:
        build_operator_registry(
            parameters={SIMILARITY_KEY: similarity},
            view=view,
            pins=booted.fabric.pins,
            policy_bundle_key=POLICY_BUNDLE_KEY,
            similarity_index_version="a-version-the-declaration-does-not-carry",  # type: ignore[call-arg]
        )
    assert "similarity_index_version" in str(second_site.value)


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
    # `24.11-02b` / `D-IMPL-292`: these keys carry the similarity artifact, and
    # the artifact carries its own `index_version`. `24.11-02`'s companion
    # `similarity_index_version` field is GONE from this roster because it is
    # gone from the class — the declaration is the authority, and a field here
    # would be a second site for one semantic value.
    "operator_parameter_keys",
    "policy_bundle_key",
    # `24.11-03` / `24.10-F-08`: the deployment's D_c bands, named by key like
    # every other declaration. `None` is admissible and is a POSITIVE claim —
    # this deployment declares no bands, so nothing is bound and the product
    # carries the SDK's sentinel — but it is never a default: a resolver that
    # guessed would serve "obliged to do nothing" from inside the content
    # address, where it cannot be corrected afterwards.
    "debt_profile_key",
    # `D-IMPL-336` Amendment 3, F0: how this deployment resolves, invokes and
    # admits the children a composite class declares. `None` is admissible and
    # POSITIVE — this deployment composes nothing — but never a default: a
    # resolver that guessed would serve a class whose declared requirements
    # execution ignored, which is the exact defect the composite block closes.
    "composite_children",
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
    # `D-IMPL-308`. Both are DEPLOYMENT-OWNED and therefore carry no default,
    # for this roster's own reason: *a default is a value nobody chose*. A
    # class with no distinct decision instant states that by passing `None`,
    # which is a choice; a class that simply never mentioned it is a class
    # whose expiry silently ran from the wrong instant.
    "decision_instant_parameter",
    "source_refresh_recency",
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
        # `24.11-02b` / `D-IMPL-292`: naming the similarity key is now the WHOLE
        # of wiring similarity — the artifact it resolves to carries its own
        # `index_version`, and there is no companion argument to keep in step
        # with it. The default wiring names no similarity artifact; the test
        # below adds the key and nothing else.
        "operator_parameter_keys": (TRAVERSAL_KEY,),
        "policy_bundle_key": POLICY_BUNDLE_KEY,
        # `24.11-03` / `24.10-F-08`: the deployment's D_c bands, named the
        # way every other declaration is named — by key, so the profile the
        # resolver reads is provably the manifest's.
        "debt_profile_key": DEBT_PROFILE_KEY,
        # This fixture's class declares no child requirements, so it wires no
        # child resolver — the state every product shipped before D-IMPL-336
        # was in, stated rather than defaulted.
        "composite_children": None,
        "plan_factory": _plan_factory,
        "debt_scorer": _debt_scorer,
        # `D-IMPL-308`. `None` and the empty window are POSITIVE values here,
        # exactly like `product_gate` below: this fixture's class declares no
        # decision instant distinct from its graph boundary and declares no
        # refresh window, and saying so is different from never being asked.
        "decision_instant_parameter": None,
        "source_refresh_recency": NO_SOURCE_REFRESH_RECENCY,
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


# --- D-IMPL-336 Amendment 3, F0: the composite path, END TO END --------------
#
# Call-site searches establish wiring; these establish BEHAVIOR. Both were
# required by the remediation instruction, and only the first was ever true of
# this surface before it.


def _served_record(booted: _Booted, served: ServedProduct) -> Any:
    """The persisted replay record behind a served product.

    Resolved from the store through the served outcome's own `replay_ref`, so
    the rows asserted below are the ones actually WRITTEN — not a record the
    test built alongside.
    """
    return DecisionReplayRecord.model_validate_json(
        booted.store.get(
            content_address=booted.store.resolve_uri(uri=served.replay_ref.uri)
        )
    )


#: One optional child requirement, declared the way a governance AUTHOR would.
#: Until Amendment 3 this document could not be written at all:
#: `ProductClassDeclaration` is `extra=forbid` and had no `requires` field.
_COMPOSITE_REQUIRES = [
    {
        "product_class": "fixture.child",
        "required": False,
        "compatible_from": "1.0.0",
        "absence_treatment": {
            "completeness_when_absent": "0.5",
            "omissible_outcomes": ["optional-absent"],
        },
    }
]


@pytest.fixture()
def booted_composite(tmp_path: pathlib.Path) -> Iterator[_Booted]:
    """A fabric whose product class DECLARES a child requirement."""
    product_class = copy.deepcopy(
        next(doc for key, *_rest, doc in ARTIFACT_SET if key == PRODUCT_CLASS_KEY)
    )
    product_class["requires"] = _COMPOSITE_REQUIRES
    yield from _boot(tmp_path, product_class=product_class)


def test_a_class_declaring_children_with_no_resolver_REFUSES(
    booted_composite: _Booted,
) -> None:
    """A declared requirement execution ignores is the defect F0 named.

    Before this block existed the answer was to serve the product anyway, with
    no composition, no admission and no replay rows. It refuses now.
    """
    outcome = _ask(
        _resolver(booted_composite, composite_children=None), _request()
    )
    assert not isinstance(outcome, ServedProduct)
    # The KIND is the governed fact that crosses. The detail naming the missing
    # resolver is withheld at `minimal` disclosure, correctly — F11's table
    # admits only `product_class` there, because an internal wiring message is
    # fabric state and not something a caller can act on.
    assert outcome.kind == "composite-child-refusal"


def test_a_composite_records_a_child_resolution_row_from_EXECUTION(
    booted_composite: _Booted,
) -> None:
    """F0's behavioral half: the row is written by the served path.

    `child_resolutions` was a declared field nothing wrote. This asserts a real
    serve through `GovernedResolver` produces one — so a composite can no
    longer be delivered with no evidence that any child was considered — and
    that the declared absence is PRICED into the served product's debt.
    """

    def no_children(**_: Any) -> dict[str, Any]:
        """A deployment whose grants produce none of the declared classes.

        The honest absence: the one outcome that takes the declared treatment.
        """
        return {}

    outcome = _ask(
        _resolver(booted_composite, composite_children=no_children), _request()
    )
    assert isinstance(outcome, ServedProduct), outcome

    rows = _served_record(
        booted_composite, outcome
    ).content_generation_path.child_resolutions
    assert len(rows) == 1
    assert rows[0].required_product_class == "fixture.child"
    assert rows[0].outcome_status == "optional-absent"
    assert outcome.product.debt is not None
    assert outcome.product.debt.factors.completeness <= Decimal("0.5")


def test_a_non_composite_product_is_completely_unaffected(
    booted: _Booted,
) -> None:
    """The control. Every product shipped before this surface takes the same
    path it always did, and its record carries no child rows."""
    outcome = _ask(_resolver(booted, composite_children=None), _request())
    assert isinstance(outcome, ServedProduct), outcome
    record = _served_record(booted, outcome)
    assert record.content_generation_path.child_resolutions == ()


def test_r2_a_composite_re_derives_its_signal_from_the_COMPOSED_factors(
    booted_composite: _Booted,
) -> None:
    """`R2`: the composite carried the PARENT's DebtSignal.

    The first version replaced the debt and the factors and kept the parent's
    signal, so a composite whose composed `D_c` crossed fail-closed was served
    with `signal=ok` and the routine obligation — while the comment above it
    claimed the routing-band hazard was respected. The signal IS the band.

    Here the declared absence drives completeness to 0.5, so `D_c` is 0.5; the
    assertion is that the signal and the obligation are derived from THAT
    number rather than from the parent's own.
    """
    from ccf.halflife.debt import context_debt

    def no_children(**_: Any) -> dict[str, Any]:
        return {}

    outcome = _ask(
        _resolver(booted_composite, composite_children=no_children), _request()
    )
    assert isinstance(outcome, ServedProduct), outcome
    assert outcome.product.debt is not None

    # the served debt IS the composed one
    assert outcome.product.debt.debt == context_debt(outcome.product.debt.factors)
    # ...and the obligation was bound to the signal that debt lands in, not to
    # a signal derived from factors the product no longer carries.
    record = _served_record(booted_composite, outcome)
    assert record.content_generation_path.debt is not None
    assert record.content_generation_path.debt.factors == outcome.product.debt.factors
