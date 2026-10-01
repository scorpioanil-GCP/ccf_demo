"""Delivery is deterministic, for a fulfilled product and for a refusal of each new kind.

``24.6-11`` Task 1; criterion 26. The ruling of record is ``D-IMPL-253``
amendment 3, and it is the sentence this whole module exists to turn into a
measurement. Dave, verbatim (``24.6-RULINGS.md`` §5):

    *"And I would expect the criteria to test the architectural properties, not
    just implementation artifacts. In particular, 24.6 should eventually be
    able to demonstrate:*

    *Same request + same governed state + same asked_at → same determination,
    authority resolution, disclosure decision, and replayable response.*

    *That is the end-to-end consequence of the architecture we've now settled."*

Four things are asserted to be the same, per case, because they are the four
layers ``D-IMPL-254`` separates and none of them implies another:

1. **The determination** — the outcome's own kind and value. A composition that
   answered two different questions the same way would satisfy nothing below.
2. **The authority resolution** — the :class:`~ccf.products.provenance.EffectiveRequest`
   recorded in replay dimension 2, compared as canonical bytes. Two runs could
   reach the same answer *by different authorities*, and that difference is
   exactly what ``D-IMPL-253`` Q1 refuses to let collapse.
3. **The disclosure decision** — the :class:`~ccf.products.disclosure.DisclosureDecision`
   recorded in dimension 5. Two runs could disclose the same determination at
   two levels; a consumer would see two different responses to one question.
4. **The replayable response** — the five dimensions of the
   :class:`~ccf.replay.record.DecisionReplayRecord`, compared dimension by
   dimension, plus the fulfilled product's content address or the refusal
   shell's canonical bytes modulo its own reference.

**Why the two references are asserted EQUAL rather than merely resolvable.**
A record is content-addressed (``D-IMPL-26``) and the governed path reads no
clock — ``GovernedResolver._record_refusal`` records at ``request.asked_at``
and the served path does the same — so two identical determinations produce
byte-identical records, which the store files under one address. The two calls
therefore each minted their own record and arrived at the same artifact. A
reference that differed would mean a record that differed, which is the
property failing rather than a store detail.

**The controls, because a sameness assertion over an inert path proves
nothing.** Two perturbations that MUST change the answer are asserted to change
it: moving ``asked_at`` across a constraint's effectivity boundary (a different
policy is in force, so a different authority resolves the question), and
registering a constraint at a different value under the same key (a new version
in force at the same instant). And the comparison helper itself is watched
reporting a planted difference, because a comparison that returned ``[]`` for
everything would make every test above green forever.

The deployment, the manifest, the product class and the wiring are
``tests/products/test_resolver_seam.py``'s, imported rather than restated for
that module's own stated reason: a second copy of a fixture deployment is a
second thing to keep in step. Every key, number, window and policy id below is
this module's own (CINV-01 reaches ``tests/``); none of them lives in ``src/``.
"""

from __future__ import annotations

import contextlib
import copy
import json
import pathlib
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest

from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.controlplane.artifacts import (
    POLICY_CONSTRAINT,
    ConstraintApplicability,
    PolicyConstraint,
)
from ccf.graph.protocols import GraphView
from ccf.halflife.debt import DebtAssessment, DebtFactors, DebtSignal
from ccf.products.constraints import (
    CAPABILITY_TRAVERSAL_DEPTH,
    ReferencePolicyConstraintResolver,
    TechnicalCapability,
)
from ccf.products.debt_scorer import ExecutionEvidence
from ccf.products.disclosure import DISCLOSURE_MINIMAL, DisclosureDecision
from ccf.products.disclosure import WITHHELD
from ccf.products.entitlement import product_entitlement_key
from ccf.products.gates import DEBT_TOLERANCE_PARAMETER
from ccf.products.provenance import EffectiveRequest, ProvenanceSource
from ccf.products.refusal import (
    NO_REPLAY_REFERENCE,
    REFUSAL_KINDS,
    RefusalEnvelope,
    RequestIdentity,
    SubjectUnavailableRefusal,
    envelope_for,
)
from ccf.products.request import ProductRequest
from ccf.replay.record import (
    NO_DISCLOSURE_DECISION,
    NO_REQUEST_RESOLUTION,
    DecisionReplayRecord,
    PolicyBinding,
    ResolutionNotApplicable,
)
from ccf.replay.serve import ServedProduct

from tests.deployment.conftest import ARTIFACT_SET, PRODUCT_CLASS_KEY, TENANT
from tests.products.test_resolver_seam import (
    ASKED_AT,
    PERSPECTIVE,
    PRODUCT_CLASS,
    PRODUCT_VERSION,
    REQUEST_CONTRACT_DOCUMENT,
    THRESHOLD_PARAMETER,
    _Booted,
    _ask,
    _boot,
    _request,
    _resolver,
)
from tests.composition import register_typed_at_composition

# --- this module's own vocabulary -------------------------------------------

#: The two adjacent effectivity windows the ``asked_at`` control moves across.
#: ``BOUNDARY`` is the instant the first window ends and the second begins, so
#: exactly one constraint is in force at every instant and the pair can never
#: raise :class:`~ccf.products.constraints.ConstraintEffectivityConflict`.
WINDOW_OPENS = datetime(2026, 1, 1, tzinfo=UTC)
BOUNDARY = datetime(2026, 6, 1, tzinfo=UTC)
# `D-IMPL-358` step 5 section H: ONE MINUTE before, not one day. The gap only
# has to CROSS the effectivity boundary, which is this module's subject; a full
# day also put the second serve outside the product's own validity window, so
# Gate 3 — measuring that window from the moment of service — refused it. A
# minute crosses the boundary and leaves both serves inside the window.
BEFORE_BOUNDARY = BOUNDARY - timedelta(minutes=1)

#: The two Control Plane keys the adjacent windows are registered under, and
#: the policy id each artifact carries. Key and policy id are deliberately
#: different strings, so a test that confused them fails rather than passing by
#: coincidence.
KEY_EARLY = "tenant-fixture/policy_constraints/early"
KEY_LATE = "tenant-fixture/policy_constraints/late"
POLICY_EARLY = "early"
POLICY_LATE = "late"

#: The two tolerances those constraints bound to, and what the caller asks for.
#: A ``maximum`` on the tolerance is the one worked case that clamps rather
#: than refuses, so both instants SERVE — which is what makes the control a
#: statement about the *resolution* rather than about which branch was taken.
TOLERANCE_EARLY = Decimal("0.20")
TOLERANCE_LATE = Decimal("0.10")
CALLER_TOLERANCE = Decimal("0.30")

#: The key the version control registers a threshold ceiling under, and the two
#: values it is registered at. A changed value is a changed content address, so
#: the second registration is a new VERSION of the same key.
KEY_THRESHOLD = "tenant-fixture/policy_constraints/threshold"
POLICY_THRESHOLD = "threshold"
THRESHOLD_MAXIMUM_FIRST = Decimal(500)
THRESHOLD_MAXIMUM_SECOND = Decimal(400)

#: What the caller asks for on the threshold parameter throughout. Above both
#: ceilings above, so both registrations refuse and the refusals differ only in
#: the bound they name — which is the difference the control measures.
CALLER_THRESHOLD = 1000

#: The depth parameter the ``constraint-refusal`` case declares and the
#: substrate bound it is refused against. The token is the SDK's own mechanism
#: token; the NUMBER is the fixture backend's, because a technical limit is a
#: property of a substrate and never an artifact (``D-IMPL-253`` amendment 2
#: (1)).
DEPTH_PARAMETER = "traversal_depth"
DEPTH_MAXIMUM = Decimal(6)
DEPTH_ASKED = 8
BACKEND_IDENTITY = "fixture-backend"

#: The two admitted sets whose intersection is empty — the deployment's own
#: Control Plane contradicting itself, which is a governed
#: ``policy-resolution-conflict`` rather than a silent pick.
KEY_SET_A = "tenant-fixture/policy_constraints/set_a"
KEY_SET_B = "tenant-fixture/policy_constraints/set_b"
POLICY_SET_A = "set-a"
POLICY_SET_B = "set-b"
ADMITTED_A = ("alpha",)
ADMITTED_B = ("beta",)

#: The observed Debt the tolerance case measures, and the class default it is
#: held against. The default is BELOW the observation, so fulfillment is
#: withheld by the class's own declared characteristic.
OBSERVED_DEBT = Decimal("0.20")
CLASS_DEFAULT_TOLERANCE = Decimal("0.10")

#: The internal statement the ``subject-unavailable`` case determines. It is
#: the fabric's own sentence and never what crosses: at ``minimal`` the
#: disclosure step replaces it with the one external statement the kind holds.
SUBJECT_DETAIL = "the fixture anchor resolved to nothing under this perspective"

#: The four kinds this module drives, by the token the vocabulary spells them
#: under. A roster rather than a count: a module driving four kinds one of
#: which was the wrong one would satisfy "four" forever
#: (``verify-rosters-not-counts``).
NEW_KINDS = (
    "constraint-refusal",
    "policy-resolution-conflict",
    "tolerance-exceeded",
    "subject-unavailable",
)

#: The five dimensions of a :class:`~ccf.replay.record.DecisionReplayRecord`,
#: by attribute name. Enumerated here so the comparison ranges over the whole
#: record rather than over a sample somebody chose; the exhaustiveness check
#: below reads the model's own fields and fails when a sixth appears.
DIMENSIONS: tuple[str, ...] = (
    "context_fabric_snapshot",
    "policy_bindings",
    "model_version",
    "perspective_conditioning",
    "content_generation_path",
)


# --- the comparison ----------------------------------------------------------


def record_dimensions_equal(
    a: DecisionReplayRecord, b: DecisionReplayRecord
) -> list[str]:
    """The dimensions of two records that DIFFER, by name; ``[]`` when none do.

    Canonical bytes per dimension rather than ``==`` on the records, for two
    reasons. The bytes are what replay actually compares, so a difference this
    reports is a difference an examiner would see. And reporting one entry per
    dimension makes a failure attributable to the dimension that caused it
    rather than to *"the records differ"* — the shape plan ``24.6-09``'s
    equivalence comparison established for the same reason.

    ``recorded_at`` and ``tenant_id`` are deliberately NOT compared here: they
    are not dimensions, and each test asserts them separately, so a helper that
    silently folded them in could not be used by a caller that wanted to hold
    them to a different standard.
    """
    return [
        name
        for name in DIMENSIONS
        if canonical_bytes(getattr(a, name)) != canonical_bytes(getattr(b, name))
    ]


def envelope_bytes_modulo_reference(shell: RefusalEnvelope) -> bytes:
    """A shell's canonical bytes with its own replay address blanked.

    The address is a fact ABOUT the record rather than part of the
    determination, and a shell that carried its own address into its own
    identity could not be compared with one that had not been recorded yet.
    The tests assert the addresses separately, so nothing is lost by taking
    them out of the byte comparison.
    """
    return canonical_bytes(
        shell.model_copy(update={"replay_reference": NO_REPLAY_REFERENCE})
    )


def _assert_same_determination(
    a: DecisionReplayRecord, b: DecisionReplayRecord
) -> None:
    """Every part of two records that must agree, asserted one claim at a time."""
    assert record_dimensions_equal(a, b) == [], record_dimensions_equal(a, b)
    assert a.tenant_id == b.tenant_id
    # Equal rather than "modulo": the governed path reads no clock at all — it
    # records at `request.asked_at` on the served path and on every refusal
    # path alike — so two runs of one question record at one instant.
    assert a.recorded_at == b.recorded_at


def _resolution_of(record: DecisionReplayRecord) -> str:
    """Dimension 2's authority resolution, as the record holds it."""
    return record.policy_bindings.request_resolution


def _disclosure_of(record: DecisionReplayRecord) -> str:
    """Dimension 5's disclosure decision, as the record holds it."""
    return record.content_generation_path.disclosure_decision


# --- the deployment ----------------------------------------------------------


@contextlib.contextmanager
def _deployment(root: pathlib.Path, **documents: Any) -> Iterator[_Booted]:
    """One booted fixture deployment, as a context manager.

    ``_boot`` is a generator fixture and the two perturbation controls need
    **two** deployments inside one test — two registries holding two different
    constraint versions — so it is driven directly here rather than through
    ``pytest``. ``close()`` raises ``GeneratorExit`` at the yield, which runs
    the generator's own ``finally`` and closes the fabric handle; nothing about
    the boot is reimplemented.
    """
    root.mkdir(parents=True, exist_ok=True)
    generator = _boot(root, **documents)
    booted = next(generator)
    try:
        yield booted
    finally:
        generator.close()


def _tolerance_documents(
    *, class_default: Decimal | None = None
) -> dict[str, Any]:
    """The two authored documents, with the tolerance declared on the contract."""
    product_class = copy.deepcopy(
        next(doc for key, *_rest, doc in ARTIFACT_SET if key == PRODUCT_CLASS_KEY)
    )
    if class_default is not None:
        product_class["serve_obligations"] = {
            "default_debt_tolerance": str(class_default)
        }
    request_contract = copy.deepcopy(REQUEST_CONTRACT_DOCUMENT)
    request_contract["declaration"]["arguments"]["properties"][
        DEBT_TOLERANCE_PARAMETER
    ] = {"type": "number", "description": "Fixture tolerance; a proportion."}
    return {"product_class": product_class, "request_contract": request_contract}


def _depth_documents() -> dict[str, Any]:
    """The request contract declaring a depth bound by a technical capability."""
    request_contract = copy.deepcopy(REQUEST_CONTRACT_DOCUMENT)
    request_contract["declaration"]["arguments"]["properties"][DEPTH_PARAMETER] = {
        "type": "number",
        "description": "Fixture depth; bounded by what the substrate can do.",
    }
    request_contract["declaration"]["capability_bindings"] = {
        DEPTH_PARAMETER: CAPABILITY_TRAVERSAL_DEPTH
    }
    return {"request_contract": request_contract}


def _governed(booted: _Booted, **overrides: Any) -> Any:
    """The seam's own wiring, with the reference resolver over this registry."""
    return _resolver(
        booted,
        constraint_resolver=ReferencePolicyConstraintResolver(
            control_plane=booted.control_plane,
            entitlement_key=product_entitlement_key(tenant_id=TENANT),
        ),
        **overrides,
    )


def _scorer(debt: Decimal) -> Any:
    """A deployment-owned debt scorer measuring exactly ``debt``."""

    def score(
        *, view: GraphView, evidence: ExecutionEvidence | None = None
    ) -> DebtAssessment:
        return DebtAssessment(
            debt=debt,
            signal=DebtSignal.OK,
            factors=DebtFactors(
                freshness=Decimal("1"),
                completeness=Decimal("1"),
                semantic_consistency=Decimal("1"),
            ),
            scorers=(),
        )

    return score


def _constraint(
    *,
    policy_id: str,
    parameter: str,
    operator: str,
    value: Any,
    effective_from: datetime = WINDOW_OPENS,
    effective_until: datetime | None = None,
) -> PolicyConstraint:
    """One applicable-to-everything constraint over one parameter."""
    return PolicyConstraint(
        semver="1.0.0",
        policy_id=policy_id,
        applies_to=ConstraintApplicability(),
        parameter=parameter,
        operator=operator,
        value=value,
        overridable=False,
        source_authority="fixture-authority",
        effective_from=effective_from,
        effective_until=effective_until,
        reason="a fixture reason",
    )


# --- reading the record back --------------------------------------------------


def _record_of(booted: _Booted, outcome: Any) -> DecisionReplayRecord:
    """The record an outcome points at, resolved through the store.

    Resolution IS part of the assertion: the file store refuses bytes that do
    not hash to the address asked for, so a record read back here is the record
    that was written.
    """
    if isinstance(outcome, ServedProduct):
        address = outcome.replay_ref.content_address
    else:
        assert isinstance(outcome, RefusalEnvelope), outcome
        assert outcome.replay_reference != NO_REPLAY_REFERENCE, (
            "a shell with no record is a determination with no audit; the seam"
            " mints before it returns (D-IMPL-256)"
        )
        address = booted.store.resolve_uri(uri=outcome.replay_reference)
    return DecisionReplayRecord.model_validate_json(
        booted.store.get(content_address=address)
    )


def _ask_twice(
    booted: _Booted, resolver: Any, request: ProductRequest
) -> tuple[Any, Any, DecisionReplayRecord, DecisionReplayRecord]:
    """The same question, asked twice, with both records read back.

    The same resolver instance rather than two: what is being held constant is
    the *governed state*, and rebuilding the resolver would also be re-reading
    the manifest, which is a second variable nobody asked about.
    """
    first = _ask(resolver, request)
    second = _ask(resolver, request)
    return first, second, _record_of(booted, first), _record_of(booted, second)


def _refusal_reference(booted: _Booted, shell: RefusalEnvelope) -> str:
    """The content address behind a shell's replay reference."""
    return booted.store.resolve_uri(uri=shell.replay_reference)


# --- the exhaustiveness of the comparison ------------------------------------


def test_the_dimension_enumeration_is_exhaustive() -> None:
    """A comparison over a sample stops covering what it names.

    :data:`DIMENSIONS` is read against the record's own declared fields, minus
    the two that are not dimensions. A sixth dimension added to the record and
    not added here would otherwise be compared by nobody, and every sameness
    assertion in this module would quietly stop covering it.
    """
    declared = set(DecisionReplayRecord.model_fields) - {"tenant_id", "recorded_at"}
    assert declared == set(DIMENSIONS)


def test_the_four_kinds_this_module_drives_are_in_the_vocabulary() -> None:
    """The roster is checked against the shipped vocabulary, never transcribed.

    A kind renamed in :data:`~ccf.products.refusal.REFUSAL_KINDS` and not
    renamed here would leave this module driving a kind that no longer exists
    — which is the *"a sabotage that exists only on paper"* shape one layer
    over.
    """
    vocabulary = set(REFUSAL_KINDS.values())
    assert set(NEW_KINDS) <= vocabulary, sorted(set(NEW_KINDS) - vocabulary)
    assert len(set(NEW_KINDS)) == len(NEW_KINDS)


# --- (1) a fulfilled product --------------------------------------------------


def test_a_fulfilled_product_is_the_same_determination_twice(
    tmp_path: pathlib.Path,
) -> None:
    """The served half of am.3: one question, one product, one record.

    The content address is the strongest available statement that the two runs
    produced the same product — it is a hash of the whole contract — and the
    dimension-by-dimension comparison is the statement that they produced it
    the same way.
    """
    with _deployment(tmp_path / "fulfilled") as booted:
        first, second, record_a, record_b = _ask_twice(
            booted, _governed(booted), _request()
        )

        assert isinstance(first, ServedProduct), first
        assert isinstance(second, ServedProduct), second
        assert content_hash(first.product) == content_hash(second.product)
        assert (
            first.replay_ref.content_address == second.replay_ref.content_address
        )
        _assert_same_determination(record_a, record_b)

        # The authority resolution is recorded and is the same one.
        assert _resolution_of(record_a) != NO_REQUEST_RESOLUTION, (
            "a served product with no recorded resolution cannot answer what"
            " bounded the question, or on whose authority (D-IMPL-254)"
        )
        assert _resolution_of(record_a) == _resolution_of(record_b)
        assert EffectiveRequest.model_validate_json(
            _resolution_of(record_a)
        ).asked_at == ASKED_AT

        # And the disclosure decision is the same — the sentinel on both,
        # because nothing was withheld from a product that was delivered.
        assert _disclosure_of(record_a) == NO_DISCLOSURE_DECISION
        assert _disclosure_of(record_b) == NO_DISCLOSURE_DECISION


# --- (2) constraint-refusal ---------------------------------------------------


def test_a_constraint_refusal_is_the_same_determination_twice(
    tmp_path: pathlib.Path,
) -> None:
    """A depth over what the substrate can do, refused identically twice.

    The bound is the fixture backend's own capability, whose provenance is a
    backend identity and never an artifact pin — so this case also holds the
    ``technical`` authority through two runs.
    """
    with _deployment(tmp_path / "constraint", **_depth_documents()) as booted:
        resolver = _governed(
            booted,
            capabilities=(
                TechnicalCapability(
                    capability=CAPABILITY_TRAVERSAL_DEPTH,
                    maximum=DEPTH_MAXIMUM,
                    identity=BACKEND_IDENTITY,
                ),
            ),
        )
        request = _request(
            parameters={
                THRESHOLD_PARAMETER: CALLER_THRESHOLD,
                DEPTH_PARAMETER: DEPTH_ASKED,
            }
        )
        first, second, record_a, record_b = _ask_twice(booted, resolver, request)

        assert isinstance(first, RefusalEnvelope), first
        assert first.kind == "constraint-refusal"
        assert first.kind == second.kind
        # `D-IMPL-260` P-F: which substrate set the bound is fabric state and
        # does not cross below `full`; the RECORD names it (Q27).
        assert BACKEND_IDENTITY not in first.fields["bound"], first.fields["bound"]
        assert BACKEND_IDENTITY in _refusal_block(record_a)
        _assert_two_shells_agree(booted, first, second, record_a, record_b)


def test_a_refused_request_records_the_override_it_attempted(
    tmp_path: pathlib.Path,
) -> None:
    """``D-IMPL-260`` P-I, criterion 10, measured on the RECORD.

    Dave: *"the refusal path must preserve the attempted override and the
    entitlement result in replay."* A caller names a policy to be resolved
    without, is not entitled to, and is refused on the technical ceiling
    anyway. The refusal's record — dimension 5's internal envelope — carries
    the attempt with ``entitled=False`` and ``honored=False``, exactly as a
    fulfilled resolution would have carried it on ``EffectiveRequest``.

    What would fail here: the shape the close review measured — a refused
    request whose record says nothing about the override it asked for, so an
    examiner could not tell an attempt that was refused as unentitled from no
    attempt at all.
    """
    with _deployment(tmp_path / "override", **_depth_documents()) as booted:
        register_typed_at_composition(booted.control_plane, KEY_THRESHOLD,
            _constraint(
                policy_id=POLICY_THRESHOLD,
                parameter=THRESHOLD_PARAMETER,
                operator="maximum",
                value=THRESHOLD_MAXIMUM_FIRST,
            ),
            POLICY_CONSTRAINT,
        )
        resolver = _governed(
            booted,
            capabilities=(
                TechnicalCapability(
                    capability=CAPABILITY_TRAVERSAL_DEPTH,
                    maximum=DEPTH_MAXIMUM,
                    identity=BACKEND_IDENTITY,
                ),
            ),
        )
        request = _request(
            parameters={
                THRESHOLD_PARAMETER: CALLER_THRESHOLD,
                DEPTH_PARAMETER: DEPTH_ASKED,
            },
            policy_overrides=(POLICY_THRESHOLD,),
        )
        shell = _ask(resolver, request)
        assert isinstance(shell, RefusalEnvelope), shell
        assert shell.kind == "constraint-refusal"
        record = _record_of(booted, shell)

    internal = RefusalEnvelope.model_validate_json(_refusal_block(record))
    attempted = json.loads(internal.fields["overrides"])
    assert len(attempted) == 1, attempted
    (attempt,) = attempted
    assert attempt["policy_id"] == POLICY_THRESHOLD
    assert attempt["entitled"] is False and attempt["honored"] is False
    assert attempt["principal_id"] == PERSPECTIVE.principal_id
    # And the dimension-2 resolution is the resolution that RAN: the attempt
    # rides on the refusal, AND the partial work resolution established before
    # the bound refused rides with it (`D-IMPL-264` D-07). The shipped tree
    # recorded the sentinel here — a refusal minted as if nothing had been
    # resolved — and that assertion was observed red before the fix.
    assert _resolution_of(record) != NO_REQUEST_RESOLUTION, _resolution_of(record)
    partial = EffectiveRequest.model_validate_json(_resolution_of(record))
    assert [o.policy_id for o in partial.overrides] == [POLICY_THRESHOLD]
    # The shell withholds it at this tenant's level — an entitlement verdict is
    # fabric state — so the record is where the attempt is answerable from.
    assert shell.fields["overrides"] == canonical_bytes(WITHHELD).decode("utf-8")


def test_a_refusal_minted_by_resolution_carries_the_partial_resolution_and_the_contract_pin(
    tmp_path: pathlib.Path,
) -> None:
    """``D-IMPL-264`` D-07, criterion 13, ledger row ``CP04-G-33`` — on the RECORD.

    Dave, verbatim (``24.7-RULINGS.md`` §3 Q7): *"Resolution participated
    whenever the resolution step actually ran. If it refuses halfway through,
    that partial work is still governed truth and belongs in replay. 'It
    failed before producing an effective request' must not erase what
    resolution already established."*

    The scenario is the override-attempt case above with one addition: the
    product class also declares a default tolerance, so that THREE
    version-bearing authorities were consulted before a bound refused — the
    request contract (its pin), the class declaration (its pin) and the
    threshold constraint (its pin) — plus the request's own identity and the
    unentitled override attempt. Every one of them is governed truth the
    refusal was reached with, and every one is asserted where replay reads
    it: the partial :class:`~ccf.products.provenance.EffectiveRequest` on
    dimension 2, the pins as ``PolicyBinding`` rows beside it, and the same
    partial record on the internal shell's ``provenance`` with its
    ``applied`` as the shell's ``policy_bindings`` — exactly what the two
    post-assembly refusal branches already record.

    What fails here on the shipped tree, and was OBSERVED failing before the
    fix (red-first, the plan's discipline): dimension 2 holds the sentinel
    ``no-request-resolution``, because the governed resolver's pre-assembly
    refusal branch minted the record with no resolution although defaults,
    constraints and capabilities had been resolved first. That is the one
    class-(c) omission ``CP04-G-33`` names inside the SDK.
    """
    documents = _tolerance_documents(class_default=CLASS_DEFAULT_TOLERANCE)
    contract = documents["request_contract"]["declaration"]
    contract["arguments"]["properties"][DEPTH_PARAMETER] = {
        "type": "number",
        "description": "Fixture depth; bounded by what the substrate can do.",
    }
    contract["capability_bindings"] = {DEPTH_PARAMETER: CAPABILITY_TRAVERSAL_DEPTH}
    with _deployment(tmp_path / "partial", **documents) as booted:
        register_typed_at_composition(booted.control_plane, KEY_THRESHOLD,
            _constraint(
                policy_id=POLICY_THRESHOLD,
                parameter=THRESHOLD_PARAMETER,
                operator="maximum",
                value=THRESHOLD_MAXIMUM_FIRST,
            ),
            POLICY_CONSTRAINT,
        )
        resolver = _governed(
            booted,
            capabilities=(
                TechnicalCapability(
                    capability=CAPABILITY_TRAVERSAL_DEPTH,
                    maximum=DEPTH_MAXIMUM,
                    identity=BACKEND_IDENTITY,
                ),
            ),
        )
        request = _request(
            parameters={
                THRESHOLD_PARAMETER: CALLER_THRESHOLD,
                DEPTH_PARAMETER: DEPTH_ASKED,
            },
            policy_overrides=(POLICY_THRESHOLD,),
        )
        shell = _ask(resolver, request)
        assert isinstance(shell, RefusalEnvelope), shell
        assert shell.kind == "constraint-refusal"
        record = _record_of(booted, shell)
        # The pins the resolver itself minted, computed the way it computes
        # them: a content address of the exact bytes it read (`D-IMPL-26`).
        declaration = resolver._declaration()
        declared = resolver._request_contract(declaration)
    contract_source = ProvenanceSource(
        kind="artifact",
        identity=resolver.request_contract_key,
        version=content_hash(declared),
    )
    class_source = ProvenanceSource(
        kind="artifact",
        identity=resolver.product_class_key,
        version=content_hash(declaration),
    )

    # Dimension 2 carries the resolution that ran, not the sentinel.
    assert _resolution_of(record) != NO_REQUEST_RESOLUTION, _resolution_of(record)
    partial = EffectiveRequest.model_validate_json(_resolution_of(record))
    assert contract_source in partial.applied, partial.applied
    assert class_source in partial.applied, partial.applied
    constraint_sources = [
        source
        for source in partial.applied
        if source.kind == "artifact" and source.identity == KEY_THRESHOLD
    ]
    assert len(constraint_sources) == 1, partial.applied
    assert partial.asked_at == request.asked_at
    assert [o.policy_id for o in partial.overrides] == [POLICY_THRESHOLD]
    assert partial.overrides[0].entitled is False
    # The defaulted tolerance the class declared WAS resolved before the bound
    # refused — the partial work D-07 refuses to erase.
    tolerance = partial.parameter(DEBT_TOLERANCE_PARAMETER)
    assert tolerance is not None and tolerance.authority == "default"
    assert tolerance.source == class_source

    # The version-bearing pins land as `PolicyBinding` rows, so the record is
    # falsifiable from pinned state (D-07, D-08; what D-11 infers from).
    bindings = record.policy_bindings.bindings
    assert (
        PolicyBinding(key=resolver.request_contract_key, version=content_hash(declared))
        in bindings
    ), bindings
    assert (
        PolicyBinding(key=resolver.product_class_key, version=content_hash(declaration))
        in bindings
    ), bindings
    assert any(binding.key == KEY_THRESHOLD for binding in bindings), bindings

    # And the internal shell says the same thing the record does — one value
    # serving both readers, so they cannot disagree (`D-IMPL-254`).
    internal = RefusalEnvelope.model_validate_json(_refusal_block(record))
    assert internal.provenance == partial
    assert internal.policy_bindings == partial.applied


# --- (3) policy-resolution-conflict -------------------------------------------


def test_a_policy_resolution_conflict_is_the_same_determination_twice(
    tmp_path: pathlib.Path,
) -> None:
    """Two admitted sets sharing no member, refused identically twice.

    The Control Plane contradicts itself about one parameter; the intersection
    is the comparable fold and an empty one is irreconcilable. Nothing about
    that is a clock read or a registry ordering, and this asserts it.
    """
    with _deployment(tmp_path / "conflict") as booted:
        for key, policy_id, admitted in (
            (KEY_SET_A, POLICY_SET_A, ADMITTED_A),
            (KEY_SET_B, POLICY_SET_B, ADMITTED_B),
        ):
            register_typed_at_composition(booted.control_plane, key,
                _constraint(
                    policy_id=policy_id,
                    parameter=THRESHOLD_PARAMETER,
                    operator="allowed_set",
                    value=admitted,
                ),
                POLICY_CONSTRAINT,
            )
        assert set(ADMITTED_A) & set(ADMITTED_B) == set(), (
            "the control on the fixture: two sets that shared a member would"
            " fold to that member and never reach the conflict branch"
        )

        first, second, record_a, record_b = _ask_twice(
            booted,
            _governed(booted),
            _request(parameters={THRESHOLD_PARAMETER: CALLER_THRESHOLD}),
        )

        assert isinstance(first, RefusalEnvelope), first
        assert first.kind == "policy-resolution-conflict"
        assert first.kind == second.kind
        _assert_two_shells_agree(booted, first, second, record_a, record_b)


# --- (4) tolerance-exceeded ---------------------------------------------------


def test_a_tolerance_exceeded_refusal_is_the_same_determination_twice(
    tmp_path: pathlib.Path,
) -> None:
    """Fulfillment withheld on the class's own declared default, twice alike.

    This is the one case that runs the WHOLE composition before refusing — the
    graph is read, the projection runs, the gates run, and only then is
    fulfillment withheld — so it is the case where a nondeterministic
    dimension 1 or dimension 5 would show.
    """
    with _deployment(
        tmp_path / "tolerance",
        **_tolerance_documents(class_default=CLASS_DEFAULT_TOLERANCE),
    ) as booted:
        assert CLASS_DEFAULT_TOLERANCE < OBSERVED_DEBT, (
            "the control on the fixture: a default at or above the observation"
            " would serve, and this test would be about the served path"
        )
        resolver = _governed(booted, debt_scorer=_scorer(OBSERVED_DEBT))
        first, second, record_a, record_b = _ask_twice(
            booted,
            resolver,
            _request(parameters={THRESHOLD_PARAMETER: CALLER_THRESHOLD}),
        )

        assert isinstance(first, RefusalEnvelope), first
        assert first.kind == "tolerance-exceeded"
        assert first.kind == second.kind
        assert first.fields["authority"] == '"default"', first.fields
        _assert_two_shells_agree(booted, first, second, record_a, record_b)

        # The graph WAS read on this path, so dimension 1 is a real snapshot
        # rather than the unread sentinel — which is what makes the sameness
        # above a statement about an execution rather than about a short
        # pre-assembly branch.
        assert record_a.content_generation_path.steps
        assert record_a.content_generation_path.steps == (
            record_b.content_generation_path.steps
        )


# --- (5) subject-unavailable --------------------------------------------------


def test_a_subject_unavailable_refusal_is_the_same_determination_twice(
    tmp_path: pathlib.Path,
) -> None:
    """The one shared outcome, minted twice through the one minting seam.

    ``subject-unavailable`` is reached by an assembler or a delivery boundary
    rather than by the resolver's own branches, so it is driven here the way a
    deployment reaches it: the determination is built, enveloped, and minted
    through the booted resolver's own
    :class:`~ccf.products.resolver.ReplayRefusalRecorder` — plan ``24.6-07``'s
    seam, the SAME recorder every other case in this module goes through, and
    the reason nothing here needs a second writer.

    The internal cause is ``nonexistent`` and the shell says ``undisclosed`` at
    ``minimal``: what is asserted twice is not only that the two runs agree,
    but that they agree on both sides of the disclosure boundary.
    """
    with _deployment(tmp_path / "subject") as booted:
        recorder = _governed(booted).refusal_recorder
        internal = envelope_for(
            SubjectUnavailableRefusal(
                cause="nonexistent", detail=SUBJECT_DETAIL, error_code=None
            ),
            request=RequestIdentity(
                product_id=PRODUCT_CLASS,
                product_version=PRODUCT_VERSION,
                parameters={THRESHOLD_PARAMETER: CALLER_THRESHOLD},
                temporal_boundary=ASKED_AT,
            ),
        )
        request = _request(parameters={THRESHOLD_PARAMETER: CALLER_THRESHOLD})

        shells = [
            recorder.record(
                internal,
                perspective=PERSPECTIVE,
                recorded_at=ASKED_AT,
                served_at=ASKED_AT,
                resolution=ResolutionNotApplicable(reason="no-resolution-step"),
                request=request,
                execution=None,
            )
            for _ in range(2)
        ]
        first, second = shells
        record_a = _record_of(booted, first)
        record_b = _record_of(booted, second)

        assert first.kind == "subject-unavailable"
        assert first.disclosure == DISCLOSURE_MINIMAL
        # The internal cause did not cross, and the shell's shape carries the
        # key all the same — so the two runs agree about what was withheld as
        # well as about what was determined.
        assert first.fields["cause"] == '"undisclosed"', first.fields
        assert SUBJECT_DETAIL not in canonical_bytes(first).decode("utf-8")
        _assert_two_shells_agree(booted, first, second, record_a, record_b)

        # And the record kept the truth the shell did not (Q27).
        assert SUBJECT_DETAIL in _refusal_block(record_a)
        assert _refusal_block(record_a) == _refusal_block(record_b)


def _refusal_block(record: DecisionReplayRecord) -> str:
    """The INTERNAL refusal dimension 5 recorded, as the record holds it."""
    return record.content_generation_path.assembly_refusal


def _assert_two_shells_agree(
    booted: _Booted,
    first: RefusalEnvelope,
    second: RefusalEnvelope,
    record_a: DecisionReplayRecord,
    record_b: DecisionReplayRecord,
) -> None:
    """Everything two identical refusals must agree about, one claim at a time.

    Four separate assertions rather than one, because they fail for four
    different reasons and a single ``==`` would report only that *something*
    moved.
    """
    # 1. The response a consumer received.
    assert envelope_bytes_modulo_reference(first) == (
        envelope_bytes_modulo_reference(second)
    )
    # 2. Each call minted its own record, and both are addressable.
    assert first.replay_reference != NO_REPLAY_REFERENCE
    assert second.replay_reference != NO_REPLAY_REFERENCE
    # A record is content-addressed and the path reads no clock, so two
    # identical determinations resolve to ONE artifact.
    assert _refusal_reference(booted, first) == _refusal_reference(booted, second)
    # 3. The replayable record, dimension by dimension.
    _assert_same_determination(record_a, record_b)
    # 4. The authority resolution and the disclosure decision.
    assert _resolution_of(record_a) == _resolution_of(record_b)
    disclosure = _disclosure_of(record_a)
    assert disclosure != NO_DISCLOSURE_DECISION, (
        "a refusal recorded with no disclosure decision cannot answer why the"
        " consumer saw the response it saw (D-IMPL-254)"
    )
    assert disclosure == _disclosure_of(record_b)
    assert DisclosureDecision.model_validate_json(
        disclosure
    ) == DisclosureDecision.model_validate_json(_disclosure_of(record_b))


# --- the controls: what MUST change the answer --------------------------------


def test_moving_served_at_across_the_effectivity_boundary_changes_the_determination(
    tmp_path: pathlib.Path,
) -> None:
    """REWRITTEN by `D-IMPL-358` step 5 ruling B, not deleted — the property inverts.

    This control's job is unchanged: it is the control on every sameness assertion
    above, and without it each "same" could be the answer of a composition that
    ignored the governing instant entirely. What changed is WHICH instant governs.

    It previously moved ``asked_at`` across the boundary and asserted the
    determination moved (``D-IMPL-253`` Q6). Ruling B makes policy effectivity a
    reading at the TRUSTED SERVE INSTANT, so that is no longer the property: the
    question's own instant does not select the policy any more. This version moves
    ``served_at`` across the boundary with ``asked_at`` HELD FIXED, and asserts the
    determination moves — and its sibling below asserts the complement, that moving
    ``asked_at`` with ``served_at`` held fixed does NOT move the policy. Between
    them the two axes are pinned apart, which neither the old control nor any other
    test in this tree did.

    The clocks are INJECTED and pinned. Relying on wall time would make the
    control's verdict depend on the day it ran, which is the calendar accident the
    old sibling test quietly depended on.

    A ``maximum`` on the tolerance clamps rather than refuses (worked case 3), so
    both instants SERVE: what changes is the authority, which is the layer
    ``D-IMPL-254`` names, rather than which branch was taken.
    """
    with _deployment(
        tmp_path / "effectivity", **_tolerance_documents()
    ) as booted:
        version_early = register_typed_at_composition(booted.control_plane, KEY_EARLY,
            _constraint(
                policy_id=POLICY_EARLY,
                parameter=DEBT_TOLERANCE_PARAMETER,
                operator="maximum",
                value=TOLERANCE_EARLY,
                effective_from=WINDOW_OPENS,
                effective_until=BOUNDARY,
            ),
            POLICY_CONSTRAINT,
        )
        version_late = register_typed_at_composition(booted.control_plane, KEY_LATE,
            _constraint(
                policy_id=POLICY_LATE,
                parameter=DEBT_TOLERANCE_PARAMETER,
                operator="maximum",
                value=TOLERANCE_LATE,
                effective_from=BOUNDARY,
                effective_until=None,
            ),
            POLICY_CONSTRAINT,
        )
        parameters = {
            THRESHOLD_PARAMETER: CALLER_THRESHOLD,
            DEBT_TOLERANCE_PARAMETER: CALLER_TOLERANCE,
        }
        # ONE question, asked at ONE instant, answered under two pinned serve
        # instants either side of the effectivity boundary.
        question = _request(asked_at=BEFORE_BOUNDARY, parameters=parameters)
        before = _ask(
            _governed(booted, admission_clock=lambda: BEFORE_BOUNDARY), question
        )
        after = _ask(_governed(booted, admission_clock=lambda: BOUNDARY), question)

        assert isinstance(before, ServedProduct), before
        assert isinstance(after, ServedProduct), after

        record_before = _record_of(booted, before)
        record_after = _record_of(booted, after)

        # The resolution moved, and it moved to the OTHER policy.
        resolved_before = EffectiveRequest.model_validate_json(
            _resolution_of(record_before)
        )
        resolved_after = EffectiveRequest.model_validate_json(
            _resolution_of(record_after)
        )
        tolerance_before = resolved_before.parameter(DEBT_TOLERANCE_PARAMETER)
        tolerance_after = resolved_after.parameter(DEBT_TOLERANCE_PARAMETER)
        assert tolerance_before is not None and tolerance_after is not None
        assert Decimal(str(tolerance_before.value)) == TOLERANCE_EARLY
        assert Decimal(str(tolerance_after.value)) == TOLERANCE_LATE
        assert tolerance_before.authority == "policy"
        assert tolerance_after.authority == "policy"

        # The applied set moved with it — one pin each, and not the same pin.
        assert _constraint_pins(resolved_before) == ((KEY_EARLY, version_early),)
        assert _constraint_pins(resolved_after) == ((KEY_LATE, version_late),)

        # And the RECORD differs while the PRODUCT does not — which is a sharper
        # statement of the property than the old control could make. One question
        # asked once has one content; what moved is which policy governed
        # answering it, and the record is where that shows. The old assertion that
        # the products differed held only because `asked_at` was moving too.
        assert record_dimensions_equal(record_before, record_after) != []
        assert content_hash(before.product) == content_hash(after.product), (
            "the question was held fixed, so its content must be — only the"
            " governance moved"
        )

        # THE COMPLEMENT, in the same fixture so the two cannot drift apart:
        # moving the QUESTION across the boundary under ONE pinned serve instant
        # leaves the policy determination where it was. Ruling B: *"Graph reads
        # stay at asked_at"* — the question's instant still governs what is read,
        # and no longer governs which policy governs the reading.
        pinned = _governed(booted, admission_clock=lambda: BOUNDARY)
        early_question = _ask(
            pinned, _request(asked_at=BEFORE_BOUNDARY, parameters=parameters)
        )
        later_question = _ask(
            pinned, _request(asked_at=BOUNDARY, parameters=parameters)
        )
        assert isinstance(early_question, ServedProduct), early_question
        assert isinstance(later_question, ServedProduct), later_question
        for served in (early_question, later_question):
            resolution = EffectiveRequest.model_validate_json(
                _resolution_of(_record_of(booted, served))
            )
            tolerance = resolution.parameter(DEBT_TOLERANCE_PARAMETER)
            assert tolerance is not None
            assert Decimal(str(tolerance.value)) == TOLERANCE_LATE, (
                "the question's own instant selected the policy; only served_at may"
            )
            assert _constraint_pins(resolution) == ((KEY_LATE, version_late),)


def _constraint_pins(resolved: EffectiveRequest) -> tuple[tuple[str, str], ...]:
    """The ``(key, version)`` pairs in ``applied`` that are this module's keys.

    Selected by key rather than by counting: the request contract's own pin is
    in ``applied`` too, because *"nothing applied"* is a claim that needs the
    same evidence as *"this applied"*.
    """
    known = {KEY_EARLY, KEY_LATE, KEY_THRESHOLD}
    return tuple(
        (source.identity, source.version or "")
        for source in resolved.applied
        if source.identity in known
    )


def test_a_new_constraint_version_changes_the_determination_at_the_same_instant(
    tmp_path: pathlib.Path,
) -> None:
    """The governed state moved, so the answer must move — the second control.

    ``asked_at`` is held at :data:`ASKED_AT` and the question is held word for
    word; what changes is the artifact in force under one key, registered at a
    different value. A registry mints a version as the CONTENT ADDRESS of what
    was registered (``D-IMPL-26``), so a changed value IS a new version — and
    the refusal names the new bound.

    Two deployments rather than two registrations under one key: two versions
    of one key in force at one instant is
    :class:`~ccf.products.constraints.ConstraintEffectivityConflict`, which is
    a different property with its own test. What this control needs is the
    Control Plane in two states, and the two states are two boots.
    """
    outcomes: list[RefusalEnvelope] = []
    internals: list[str] = []
    pins: list[str] = []
    for index, maximum in enumerate(
        (THRESHOLD_MAXIMUM_FIRST, THRESHOLD_MAXIMUM_SECOND)
    ):
        with _deployment(tmp_path / f"version-{index}") as booted:
            version = register_typed_at_composition(booted.control_plane, KEY_THRESHOLD,
                _constraint(
                    policy_id=POLICY_THRESHOLD,
                    parameter=THRESHOLD_PARAMETER,
                    operator="maximum",
                    value=maximum,
                ),
                POLICY_CONSTRAINT,
            )
            outcome = _ask(
                _governed(booted),
                _request(parameters={THRESHOLD_PARAMETER: CALLER_THRESHOLD}),
            )
            assert isinstance(outcome, RefusalEnvelope), outcome
            assert outcome.kind == "constraint-refusal"
            outcomes.append(outcome)
            internals.append(_refusal_block(_record_of(booted, outcome)))
            pins.append(version)

    first, second = outcomes
    assert THRESHOLD_MAXIMUM_FIRST != THRESHOLD_MAXIMUM_SECOND
    # The pin changed: a different value under the same key is a different
    # version, and the shell names it.
    assert pins[0] != pins[1]
    # The pin is the bound's `source`, which the RECORD keeps and the shell
    # does not carry below `full` (`D-IMPL-260` P-F).
    assert pins[0] in internals[0]
    assert pins[1] in internals[1]
    assert pins[0] not in first.fields["bound"]
    assert pins[1] not in second.fields["bound"]
    # And the determination changed with it.
    assert str(THRESHOLD_MAXIMUM_FIRST) in first.fields["bound"]
    assert str(THRESHOLD_MAXIMUM_SECOND) in second.fields["bound"]
    assert envelope_bytes_modulo_reference(first) != (
        envelope_bytes_modulo_reference(second)
    )


def test_the_dimension_comparison_refuses_a_planted_difference(
    tmp_path: pathlib.Path,
) -> None:
    """The comparison is watched reporting, before any emptiness is trusted.

    A helper that returned ``[]`` unconditionally would make every sameness
    test in this module green forever, and nothing else here would notice. So
    a real record is copied with ONE dimension mutated, per dimension, and the
    helper is asserted to name exactly that dimension.

    The mutation is a model copy: nothing is written, and the record in the
    store is untouched.
    """
    with _deployment(tmp_path / "planted") as booted:
        outcome = _ask(_governed(booted), _request())
        assert isinstance(outcome, ServedProduct), outcome
        record = _record_of(booted, outcome)

        assert record_dimensions_equal(record, record) == []

        planted = record.model_copy(
            update={
                "content_generation_path": (
                    record.content_generation_path.model_copy(
                        update={"plan_id": "a-plan-nobody-ran"}
                    )
                )
            }
        )
        assert record_dimensions_equal(record, planted) == [
            "content_generation_path"
        ]

        planted_tenant = record.model_copy(update={"tenant_id": "another-tenant"})
        # The helper is silent about what is not a dimension, which is why
        # `_assert_same_determination` asserts the tenant separately.
        assert record_dimensions_equal(record, planted_tenant) == []
        with pytest.raises(AssertionError):
            _assert_same_determination(record, planted_tenant)

        planted_instant = record.model_copy(
            update={"recorded_at": record.recorded_at + timedelta(seconds=1)}
        )
        assert record_dimensions_equal(record, planted_instant) == []
        with pytest.raises(AssertionError):
            _assert_same_determination(record, planted_instant)


def test_the_envelope_comparison_refuses_a_planted_difference(
    tmp_path: pathlib.Path,
) -> None:
    """The shell comparison, watched the same way.

    Two claims: the reference is genuinely excluded (two shells differing only
    there compare equal), and everything else is genuinely included (a changed
    kind is reported). Without the first, the sameness tests could be passing
    on an address that happens to match; without the second, they could be
    passing on a comparison that looks at nothing.
    """
    with _deployment(tmp_path / "planted-shell", **_depth_documents()) as booted:
        resolver = _governed(
            booted,
            capabilities=(
                TechnicalCapability(
                    capability=CAPABILITY_TRAVERSAL_DEPTH,
                    maximum=DEPTH_MAXIMUM,
                    identity=BACKEND_IDENTITY,
                ),
            ),
        )
        shell = _ask(
            resolver,
            _request(
                parameters={
                    THRESHOLD_PARAMETER: CALLER_THRESHOLD,
                    DEPTH_PARAMETER: DEPTH_ASKED,
                }
            ),
        )
        assert isinstance(shell, RefusalEnvelope), shell

        moved_reference = shell.model_copy(
            update={"replay_reference": "ccf-artifact://nowhere/nothing/0"}
        )
        assert envelope_bytes_modulo_reference(shell) == (
            envelope_bytes_modulo_reference(moved_reference)
        )
        assert canonical_bytes(shell) != canonical_bytes(moved_reference)

        moved_reason = shell.model_copy(update={"reason": "a-reason-nobody-reached"})
        assert envelope_bytes_modulo_reference(shell) != (
            envelope_bytes_modulo_reference(moved_reason)
        )
