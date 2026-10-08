"""Does a policy-emptied view disclose anything to the principal it was emptied for?

The Gate-0 A6 measurement (Dave, 2026-09-20: *"When policy removes everything, does
the response reveal anything the user isn't entitled to know? If no, continue. If
yes, fix the disclosure behavior — not the graph, transport, or product model."*).
Recorded in ``docs/GATE-0-COVERAGE-CP15-24.md`` §5.1 (A6) and §8 (Q8).

The channel under measurement
-----------------------------
``D-IMPL-242`` amendment 1 serves an operator that ran and returned nothing WITH
its search attached: :attr:`ccf.products.contract.ContextProductContract.computed_empty`
names every operator key whose output view was empty, including the Policy
operator's. The vessel crosses every door verbatim (the disclosure layer shapes
refusal envelopes only), so whatever the finding says reaches whoever was
entitled to the class. The question is whether, for a principal whose policy
filter removed EVERY claim about a subject, that finding — or anything else on
the served vessel — says *"there was something here and policy removed it"*.

The standard applied
--------------------
The one the SDK already holds at the delivery boundary (``D-IMPL-253`` Q27;
``tests/mcp/test_egress_disclosure.py``): an unauthorized outcome must be
consumer-observationally equivalent to a nonexistent one. Here the two outcomes
are, for ONE principal entitled to the class but not to the classification:

* **R** — a subject whose only claims carry a classification the principal's
  ``permitted_classifications`` does not admit (policy empties the view);
* **M** — a subject with no claims at all.

The vessels are compared whole, path by path, and every differing path is
reported by name. No allowlist of "legitimately different" members is
hand-picked: the vessel carries no subject echo (measured below — the echo
travels on the door outcome, not the vessel), so the standard is equality.

How a subject scopes a product, and why two fabrics
---------------------------------------------------
The typed-neighborhood walk starts from EVERY entity of its seed classes;
explicit request seeds only ADD starting points, intersected with the in-scope
view (``src/ccf/graph/fallback.py`` (``_walk``); ``GQ-11``). A subject therefore
never narrows a walk by itself — a product is scoped to its subject by what
acquisition put in the per-request fabric (the paved road's model: the fabric
for a question about R holds R's claims and nothing else). The faithful
comparison is thus a fabric holding only R's restricted claims against a fabric
holding nothing, asked as R and as M respectively. A third, long-lived fabric
holding an admitted subject beside the restricted one is measured too, because
that is the shape a shared L3 would have, and the instrument's positive control
is taken across it.

Why the shipped resolver and a booted deployment
------------------------------------------------
The paved road never mints ``cause="nonexistent"`` for a missing subject —
:class:`ccf.products.resolver.ProductNotResolvable` fires for a wrong tenant, a
missing request or a broken manifest, never for subject absence — so both R and
M travel the SERVED path (``tests/examples/test_hw1_empty_fabric_refusal.py``
holds the empty fabric to that). The comparison is therefore made on the served
vessel, through the shipped :class:`~ccf.products.resolver.GovernedResolver`
over a real booted ``tests/deployment`` fixture, wired as
``tests/products/test_evidence_derived_debt.py`` wires it, with two changes that
module did not need: the Policy operator is declared on the class (the stock
fixture class declares the walk alone — the first run of this module found the
restricted entity assembled for exactly that reason), and the subjects are the
entity URIs the assembly worker mints (a bare account reference matches no
entity and seeds nothing).

Every domain value — classifications, labels, subjects, the half-life, the
declared factors — is fixture vocabulary (CINV-01, CLAUDE.md §11).
"""

from __future__ import annotations

import pathlib
from collections.abc import Iterator, Sequence
from datetime import UTC, datetime
from typing import Any

import pytest

from ccf.artifacts.file_store import FileArtifactStore
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.controlplane.artifacts import HalfLifeEntry, HalfLifeTable
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.deployment import load_and_boot
from ccf.halflife.assessment import NO_SOURCE_REFRESH_RECENCY
from ccf.products.constraints import ReferencePolicyConstraintResolver
from ccf.products.debt_scorer import AssemblyDebtScorer, DeclaredFactor
from ccf.products.entitlement import product_entitlement_key
from ccf.products.request import ProductRequest
from ccf.products.resolver import GovernedResolver, ReplayRefusalRecorder
from ccf.replay.serve import ServedProduct
from ccf.signal.envelope import SignalEnvelope
from tests.deployment.conftest import (
    ARTIFACT_SET,
    POLICY_BUNDLE_KEY,
    POLICY_PARAMS_KEY,
    PRODUCT_CLASS_KEY,
    TENANT,
    TRAVERSAL_KEY,
    manifest_document,
    write_artifact,
)
from tests.products.test_evidence_derived_debt import (
    DECLARED,
    _EmptyProjection,
    profile,
)
from tests.products.test_resolver_seam import (
    ASKED_AT,
    MAX_TTL_SECONDS,
    PERSPECTIVE,
    PRODUCT_CLASS,
    PRODUCT_TTL_SECONDS,
    PRODUCT_VERSION,
    QUERY_PIN_CLASS,
    REPLAY_RECORD_CLASS,
    REQUEST_CONTRACT_CLASS_ID,
    REQUEST_CONTRACT_DOCUMENT,
    REQUEST_CONTRACT_KEY,
    THRESHOLD_PARAMETER,
)
from tests.composition import declare_wide_temporal_boundary, composition_replay_mint, declaring_store
from ccf.products.composite import ADMITTED_CHILD_CONTRACT_CLASS

# --- fixture vocabulary --------------------------------------------------------

#: The classification the fixture deployment's policy operator ADMITS
#: (``tests/deployment/conftest.py``, ``permitted_classifications``).
PERMITTED = "fixture-open"

#: A classification it does not admit. Fixture vocabulary; the wall.
RESTRICTED = "fixture-restricted"

#: The account whose only claims are restricted — the policy-emptied case.
RESTRICTED_REF = "acct-restricted"

#: A label that must never cross to the unentitled principal.
RESTRICTED_LABEL = "restricted engagement — must not cross"

#: Accounts nothing was ever ingested for.
MISSING_ONE_REF = "acct-missing-one"
MISSING_TWO_REF = "acct-missing-two"

#: The entitled control account, admitted by the policy operator.
OPEN_REF = "acct-open"

#: One instant before the fixture's decision instant, so every claim is
#: valid at the boundary the resolver asks at.
INGESTED_AT = datetime(2026, 3, 2, 11, 0, tzinfo=UTC)

#: The observation type the fixture's resolution spec mints for an ``account_ref``
#: claim — the entity class. The sibling module's table calibrates a type its
#: (empty) views never carry; this fabric holds real claims, and a scorer asked
#: to decay an observation with no declared rate refuses by name
#: (``MissingHalfLife``), so the rate is declared here. A fixture calibration.
OBSERVATION_TYPE = "account"
HALF_LIFE_SECONDS = 3600

#: The plan this measurement needs: the Policy operator and the typed
#: neighborhood walk (``CATEGORY_ORDER`` runs policy first regardless of
#: declaration order).
REQUIRED_OPERATORS = ["policy.principal-subgraph", "traversal.typed-neighborhood"]

#: The Policy operator's key, as the finding would name it.
POLICY_OPERATOR_KEY = "policy.principal-subgraph"


def _uri(account_ref: str) -> str:
    """The entity URI the fixture's resolution spec mints for ``account_ref``.

    ``<entity_class>://<content hash of the declared identity>``
    (``src/ccf/assembly/worker.py``), the identity being the declared identity
    keys beside their values.
    """
    return f"account://{content_hash({'account_ref': account_ref})}"


RESTRICTED_SUBJECT = _uri(RESTRICTED_REF)
MISSING_ONE = _uri(MISSING_ONE_REF)
MISSING_TWO = _uri(MISSING_TWO_REF)
OPEN_SUBJECT = _uri(OPEN_REF)


def table() -> HalfLifeTable:
    """The sibling's table shape, calibrated for the claims this fabric holds."""
    return HalfLifeTable(
        semver="1.0.0",
        entries={
            OBSERVATION_TYPE: HalfLifeEntry(
                half_life_seconds=HALF_LIFE_SECONDS,
                decay_driver="fixture-driver",
                supersession_event="fixture-supersession",
            )
        },
    )


def _envelope(subject: str, *, classification: str, label: str) -> SignalEnvelope:
    """One claim about ``subject`` carrying ``classification``, in the fixture's shape."""
    return SignalEnvelope.model_validate(
        {
            "tenant_id": TENANT,
            "envelope_id": f"envelope-{subject}",
            "source": {"system_id": "fixture-system"},
            "ingestion_timestamp": INGESTED_AT.isoformat().replace("+00:00", "Z"),
            "raw_payload": {
                "account_ref": subject,
                "classification": classification,
                "label": label,
            },
        }
    )


RESTRICTED_ONLY: tuple[SignalEnvelope, ...] = (
    _envelope(RESTRICTED_REF, classification=RESTRICTED, label=RESTRICTED_LABEL),
)
MIXED: tuple[SignalEnvelope, ...] = (
    _envelope(RESTRICTED_REF, classification=RESTRICTED, label=RESTRICTED_LABEL),
    _envelope(OPEN_REF, classification=PERMITTED, label="open account"),
)


# --- the booted fixture, with its contents varied ------------------------------


def _boot(tmp_path: pathlib.Path, *, name: str, envelopes: Sequence[SignalEnvelope]) -> Any:
    """Boot the ``tests/deployment`` fixture and ingest ``envelopes`` through L2.

    The boot is ``test_evidence_derived_debt.booted_empty``'s; the ingestion is
    the single-writer path every test in ``tests/deployment`` uses
    (``fabric.handle.worker.ingest``). Nothing here reaches the graph any other
    way. The product class is the fixture's with the Policy operator declared —
    authored here, in a test-side variant of the fixture document, never in
    ``src/`` (CINV-01).
    """
    root = tmp_path / name
    root.mkdir()
    for key, filename, _class_id, _role, _registration, document in ARTIFACT_SET:
        if key == PRODUCT_CLASS_KEY:
            document = {**document, "required_operator_keys": REQUIRED_OPERATORS}
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
    # `D-IMPL-358` step 5 ruling 11: a deployment declaring no temporal boundary
    # refuses every question, so a fixture that means to serve declares one. Wide
    # on purpose — the window is not what these tests are about.
    declare_wide_temporal_boundary(control_plane, tenant_id=fabric.tenant_id)
    for envelope in envelopes:
        fabric.handle.worker.ingest(envelope)
    return (
        fabric,
        control_plane,
        declaring_store(root / "artifacts", REPLAY_RECORD_CLASS, QUERY_PIN_CLASS, ADMITTED_CHILD_CONTRACT_CLASS),
    )


@pytest.fixture()
def empty(tmp_path: pathlib.Path) -> Iterator[Any]:
    """A subject that does not exist: the per-request fabric holds nothing."""
    booted = _boot(tmp_path, name="empty", envelopes=())
    try:
        yield booted
    finally:
        booted[0].handle.close()


@pytest.fixture()
def restricted_only(tmp_path: pathlib.Path) -> Iterator[Any]:
    """The wall case: the per-request fabric holds ONLY claims the principal may not see."""
    booted = _boot(tmp_path, name="restricted", envelopes=RESTRICTED_ONLY)
    try:
        yield booted
    finally:
        booted[0].handle.close()


@pytest.fixture()
def mixed(tmp_path: pathlib.Path) -> Iterator[Any]:
    """A long-lived fabric: an admitted subject beside the restricted one."""
    booted = _boot(tmp_path, name="mixed", envelopes=MIXED)
    try:
        yield booted
    finally:
        booted[0].handle.close()


def _serve(booted: Any, subject: str) -> Any:
    """One governed serve for ``subject`` as the fixture principal, shipped resolver.

    The wiring is ``test_evidence_derived_debt._ask_the_empty_fabric``'s, member
    for member, with the subject a parameter and the Policy operator's
    parameters wired. The principal is the fixture's one perspective, entitled
    to the class and — by the policy operator's declared
    ``permitted_classifications`` — to ``fixture-open`` claims only.
    """
    fabric, control_plane, store = booted
    resolver = GovernedResolver(
        composite_children=None,
        acquisition=None,
        population_acquisition=None,
        # `PKG-F-08`: stated, never defaulted.
        packaging_trace=None,
        half_life_key=None,
        admission_clock=lambda: datetime(2026, 3, 2, 12, 7, tzinfo=UTC),
        decision_instant_parameter=None,
        source_refresh_recency=NO_SOURCE_REFRESH_RECENCY,
        fabric=fabric,
        control_plane=control_plane,
        product_class_key=PRODUCT_CLASS_KEY,
        request_contract_key=REQUEST_CONTRACT_KEY,
        operator_parameter_keys=(POLICY_PARAMS_KEY, TRAVERSAL_KEY),
        policy_bundle_key=POLICY_BUNDLE_KEY,
        debt_profile_key=None,
        plan_factory=lambda *, required, request: _EmptyProjection(
            required=required, request=request
        ),
        debt_scorer=AssemblyDebtScorer(
            table=table(),
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
        product_ttl_seconds=PRODUCT_TTL_SECONDS,
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


# --- the observational comparison ------------------------------------------------


def _vessel(outcome: Any) -> dict[str, Any]:
    """What a consumer reads: the served vessel, as JSON-mode data."""
    assert isinstance(outcome, ServedProduct), (
        f"not served — {type(outcome).__name__}; the equivalence below is a"
        " statement about two SERVED vessels, and a refusal on one side is"
        " itself the loudest possible difference"
    )
    return outcome.product.model_dump(mode="json")


def _diff_paths(a: Any, b: Any, prefix: str = "") -> set[str]:
    """Every dotted path at which ``a`` and ``b`` differ."""
    if isinstance(a, dict) and isinstance(b, dict):
        paths: set[str] = set()
        for key in set(a) | set(b):
            path = f"{prefix}.{key}" if prefix else str(key)
            if key not in a or key not in b:
                paths.add(path)
            else:
                paths |= _diff_paths(a[key], b[key], path)
        return paths
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return {f"{prefix}[len]"}
        paths = set()
        for index, (left, right) in enumerate(zip(a, b, strict=True)):
            paths |= _diff_paths(left, right, f"{prefix}[{index}]")
        return paths
    return set() if a == b else {prefix or "<root>"}


# --- the measurement -------------------------------------------------------------


def test_a_policy_emptied_subject_is_indistinguishable_from_a_nonexistent_one(
    restricted_only: Any, empty: Any
) -> None:
    """The paved-road shape: R's fabric holds only what policy removes; M's holds nothing.

    Whatever the vessel says about the subject whose claims policy removed, it
    must say — path for path — about a subject that never existed. Any
    differing path is a channel the restricted claims moved: the leak Q8 asks
    about, whatever member it lands on.
    """
    walled = _vessel(_serve(restricted_only, RESTRICTED_SUBJECT))
    nonexistent = _vessel(_serve(empty, MISSING_ONE))
    leaked = _diff_paths(walled, nonexistent)
    assert not leaked, (
        "the served vessel distinguishes a policy-emptied subject from a"
        f" nonexistent one at {sorted(leaked)}"
    )


def test_on_a_shared_fabric_the_restricted_subject_and_a_missing_one_read_the_same(
    mixed: Any,
) -> None:
    """The long-lived-fabric shape: an admitted subject sits beside the restricted one.

    Here the Policy operator's output is non-empty (the admitted account
    survives it) and the walk starts from every admitted account, so both
    questions assemble the same admitted view. What is measured is that no
    member — finding, debt, payload, lineage — carries the restricted
    subject's existence on top of that.
    """
    walled = _vessel(_serve(mixed, RESTRICTED_SUBJECT))
    nonexistent = _vessel(_serve(mixed, MISSING_ONE))
    leaked = _diff_paths(walled, nonexistent)
    assert not leaked, (
        "on a shared fabric the served vessel distinguishes a policy-emptied"
        f" subject from a nonexistent one at {sorted(leaked)}"
    )


def test_nothing_from_the_restricted_claims_reaches_any_vessel(
    restricted_only: Any, mixed: Any
) -> None:
    """The direct half, on both fabric shapes: nothing restricted assembled, nothing crossed."""
    for booted, expected_assembled in ((restricted_only, 0), (mixed, 1)):
        outcome = _serve(booted, RESTRICTED_SUBJECT)
        assert isinstance(outcome, ServedProduct)
        product = outcome.product
        assert product.payload["assembled"] == expected_assembled, (
            "the projection assembled a different universe than the admitted one —"
            f" {product.payload}"
        )
        rendered = canonical_bytes(product)
        for forbidden in (RESTRICTED, RESTRICTED_LABEL, RESTRICTED_SUBJECT):
            assert forbidden.encode("utf-8") not in rendered, (
                f"the restricted value {forbidden!r} is on the served vessel"
            )


def test_the_finding_is_a_fact_about_the_view_not_about_the_subject(
    restricted_only: Any, empty: Any
) -> None:
    """What the empty finding names, measured rather than argued.

    On the walled fabric the Policy operator's output IS empty, so the finding
    names it. On the EMPTY fabric — a subject that never existed — the Policy
    operator's output is empty too, and the finding names it identically. The
    marker is therefore a statement about this principal's admitted view (it is
    empty), never about whether a particular subject had restricted material
    behind it: *"your admitted universe is empty"*, not *"there was something
    here"*. Both findings are attested (a query ran against a tier-1 source),
    so the emptiness classification does not separate them either.
    """
    walled = _serve(restricted_only, RESTRICTED_SUBJECT)
    nonexistent = _serve(empty, MISSING_ONE)
    assert isinstance(walled, ServedProduct) and isinstance(nonexistent, ServedProduct)
    finding_r = walled.product.computed_empty
    finding_m = nonexistent.product.computed_empty
    assert finding_r is not None and finding_m is not None, (
        "an empty answer was served with no record of the search behind it"
    )
    assert finding_r == finding_m, (
        "the empty finding differs between a policy-emptied subject and a"
        f" nonexistent one: {finding_r} vs {finding_m}"
    )
    assert POLICY_OPERATOR_KEY in finding_r.operators_returned_empty, (
        "the walled fabric did not empty the Policy operator's output; the case"
        f" under measurement was not constructed: {finding_r.operators_returned_empty}"
    )
    assert finding_r.emptiness == "attested"


def test_the_instrument_can_see_a_difference(mixed: Any, empty: Any) -> None:
    """Positive control: an ENTITLED, assembled subject differs from a nonexistent one.

    Without this the equivalence tests above could pass against an instrument
    that reports no difference for anything. The admitted account is assembled
    on the shared fabric (payload ``assembled == 1``, no empty finding), the
    nonexistent subject on the empty fabric is not, and the comparison must
    name the payload and the finding among the paths that differ.
    """
    open_vessel = _vessel(_serve(mixed, OPEN_SUBJECT))
    nonexistent = _vessel(_serve(empty, MISSING_ONE))
    assert open_vessel["payload"]["assembled"] == 1, "the control subject was not assembled"
    differing = _diff_paths(open_vessel, nonexistent)
    assert any(path.startswith("payload") for path in differing), (
        f"the comparison cannot see an assembled payload: {sorted(differing)}"
    )
    assert any(path.startswith("computed_empty") for path in differing), (
        f"the comparison cannot see the empty finding come and go: {sorted(differing)}"
    )


def test_the_vessel_carries_no_subject_echo_so_equality_is_the_standard(empty: Any) -> None:
    """Two different nonexistent subjects yield byte-identical vessels.

    The question's echo travels on the door outcome, not on the vessel, so no
    path on the vessel is "legitimately" subject-caused and the equivalence
    tests above are held to plain equality. Measured rather than assumed: were a
    subject string ever to reach the vessel, this test names the path.
    """
    one = _serve(empty, MISSING_ONE)
    two = _serve(empty, MISSING_TWO)
    assert isinstance(one, ServedProduct) and isinstance(two, ServedProduct)
    moved = _diff_paths(_vessel(one), _vessel(two))
    assert not moved, f"the subject alone moves the vessel at {sorted(moved)}"
    for subject in (MISSING_ONE, MISSING_TWO):
        assert subject.encode("utf-8") not in canonical_bytes(one.product)
