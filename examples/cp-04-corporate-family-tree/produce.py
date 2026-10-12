# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""The spine — one question, end to end, for `reference.corporate-family`.

[MECHANISM] everything below the deployment seam. [ADAPT] nothing here: this
module names no company, no predicate, no store, no table, no class and no
depth. Every value it works with arrives from `deployment.py`, which interprets
the documents beside it.

**THE SPECIFICATION'S SECTION D READ AS CODE**, and the ordering is not a
convenience. `Policy` runs before anything reads graph state (§D.3 step 2;
`CATEGORY_ORDER` at `src/ccf/operators/base.py` puts Policy first and
INV-CH7-26 says why — admissibility is settled before a walk expands, so a node
the principal may not see is never materialized and no edge to it is ever
built). The replay record is written before the product is delivered
(INV-CH7-79). And `ServableProduct` is not constructible outside `run_gates`,
so holding one IS the evidence the gates ran rather than a claim that they did.

**WHAT THIS RUNG ADDS TO THE SHAPE RUNGS 00 THROUGH 03 ESTABLISHED, and it is
visible in the `operators` region rather than in a comment.** This is the FIRST
rung on the ladder whose `lineage.operators_invoked` carries MORE THAN ONE
ENTRY. Rungs 01, 02 and 03 each declare `policy.principal-subgraph` alone
because none of them has a relationship to walk; this product's subject IS the
relationships, so `traversal.typed-neighborhood` is a registered L4 operator
beside it and the set is exactly two. A reader arriving from those rungs will
expect one.

**FOUR REFUSALS ARE RETURNED AS DATA rather than raised** — the four values
:func:`assemble_and_serve` can hand back beside an `Assembled`. A question this
class does not answer is a `ProductRequestViolation`; an anchor that resolves to
no entity is an `AnchorUnresolvable`; an anchor that resolves to more than one
is an `AnchorAmbiguous`; an undeclared role reached at the deployment seam is
an `AssemblyRefusal`. None is an exception, because a bad question, a missing
company and a role nobody declared are not broken deployments, and a verdict
returned as a value cannot be swallowed by a bare `except`.

SUPERSEDED 2026-09-04 (`24.6-L-13`): this paragraph counted THREE and listed a
fifth value, `ParameterNotSupported`, that the function no longer returns —
its branch was dead by construction and is deleted. `AnchorAmbiguous`, which
the count had omitted since 24.5.1 added it, is named above.

SUPERSEDED 2026-09-04 (`24.6-L-01`, `D-IMPL-253` Q21): the fourth value was a
depth-out-of-bounds type, described as *"a max_depth above the declared
ceiling"*. That bound is deleted and the depth outcomes are the SDK's: a
non-integer depth comes back as a `ProductRequestViolation` and a depth over
the substrate's traversal capability as a `ConstraintRefusal`, both settled
before this function is called at all.

**AN EMPTY PAYLOAD IS THE DANGEROUS FAILURE ON THIS RUNG IN PARTICULAR.** An
empty family reads as *this company has no subsidiaries*, which is a claim about
the world rather than about the request. §D.2 makes an unresolvable anchor a
`404` BEFORE the graph is touched: there is no ingest, no view and no projection
for a family that does not exist, and inventing an empty one to keep a happy
path alive is the defect that branch prevents.

**TEN STEPS IN SEVEN REGIONS, AND THE TWO COUNTS ARE DIFFERENT THINGS.**
`artifacts/assembly-recipe.yaml` declares TEN steps and the specification's §D.2
table carries the same ten; the seven regions are the documentation page's
include surface, not a step count. Every one of the ten is named below on its own
numbered line, in the region that runs it — so a reader can count ten in this
file, ten in the artifact and ten in the specification, and a step that quietly
stopped happening would be a numbered line with no code under it.

**FOUR OF THE TEN RUN BEHIND THE DEPLOYMENT SEAM**, and they are named here
rather than left implicit. Steps 1, 3, 4, 6, 7 and 8 are the two source reads,
the normalization and the two detectors — they name stores, predicates and
columns, so they belong in `deployment.py` and the one line that crosses the seam
is `read(...)`. The spine names which of them it is causing and does not
reimplement any.

**THE SEVEN CANONICAL REGIONS ARE THE PUBLISHED SNIPPET SURFACE.** They are what
the documentation page's ``--8<--`` includes address, and they are opened in the
order the fabric is called in — `boot`, `ingest`, `operators`, `project`, `gate`,
`record`, `serve`. This module FILLS the regions the wave-3 stub opened; it does
not renumber or restructure them.

**This module is SILENT and stays silent.** Presentation belongs to `run.py`. A
printed line inside a published region is snippet surface an adopter would never
write.

AMENDED 2026-10-11 — compatibility repair (Dave, ruling 3 of 2026-10-11 16:23
MST; ``examples/AMENDMENTS-2026-10-11.md``). Everything above describes the
spine as it was frozen and is kept as that record; the original text of this
file is in git at the specimen's branch point. The hand-composed half — the
operator registry, the projection engine, registering the MaxTTL and the
request contract, ``run_gates``, ``build_replay_record`` and ``serve`` with the
deployment's own writers — no longer exists on the SDK's surface: since
``D-IMPL-353``/``D-IMPL-354`` a Control Plane registration or a replay write
needs a capability only an SDK composition root mints. So those steps now run
inside :func:`~ccf.products.resolver.build_governed_resolver`, which executes
the same two declared operators (Policy first), the same Π, the three L6
gates and the five-dimension record before it delivers. The regions follow the
SDK's canonical shape (``D-IMPL-306``): ``boot`` unchanged; ``acquire`` is the
deployment's read and the old ``ingest``; ``govern`` hands the resolver this
deployment's Π and D_c and asks it the question. The four refusals above are
still returned as data, before the graph is touched. What the request carries
for the two per-request operator values (the family and the depth) is
explained in ``deployment.py::read``.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Protocol

from ccf.agents.errors import AssemblyRefusal
from ccf.artifacts.file_store import FileArtifactStore
from ccf.contracts.claims import RelationshipClaim
from ccf.controlplane.artifacts import (
    DebtProfile,
    HalfLifeTable,
    ProductClassDeclaration,
)
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.deployment import BootedFabric, load_config_and_boot
from ccf.erasure import ErasureTrust, erasure_index_at
from ccf.graph.protocols import GraphView
from ccf.halflife.assessment import DebtAssessment, DebtFactors
from ccf.halflife.debt import FreshnessScorer, assess_debt
from ccf.halflife.decay import Observation
from ccf.products.contract import ContextProductContract
from ccf.products.provenance import EffectiveRequest
from ccf.products.refusal import RefusalEnvelope
from ccf.products.request import (
    ProductRequest,
    ProductRequestContract,
    ProductRequestViolation,
    refuse_request,
)
from ccf.products.resolver import build_governed_resolver
from ccf.projection.plan import ProjectionPlan
from ccf.replay.record import DecisionReplayRecord
from ccf.replay.serve import ServedProduct
from ccf.signal.envelope import SignalEnvelope

class Scenario(Protocol):
    """What this spine asks a deployment to supply.

    Structural, never inherited: `deployment.py` satisfies this by HAVING the
    members, not by importing anything from here. That is what keeps the
    dependency pointing one way — the spine knows the SHAPE of a deployment's
    answers and nothing about this particular product.
    """

    @property
    def envelopes(self) -> Sequence[SignalEnvelope]: ...

    @property
    def envelopes_by_node(self) -> Mapping[str, str]: ...

    @property
    def request(self) -> ProductRequest: ...

    @property
    def request_contract(self) -> ProductRequestContract: ...

    @property
    def request_contract_key(self) -> str: ...

    @property
    def product_class(self) -> ProductClassDeclaration: ...

    @property
    def perspective(self) -> Any: ...

    @property
    def operator_parameters(self) -> Mapping[str, Any]: ...

    @property
    def policy_bundle_key(self) -> str: ...

    #: AMENDED 2026-10-11: the placed key the class declaration is filed under.
    @property
    def product_class_key(self) -> str: ...

    #: AMENDED 2026-10-11: the declared product lifetime the resolver anchors.
    @property
    def ttl_seconds(self) -> int: ...

    #: AMENDED 2026-10-11: the technical capabilities the request binds to.
    @property
    def capabilities(self) -> tuple[Any, ...]: ...

    #: AMENDED 2026-10-11: the store, declared with its write kinds.
    def artifact_store(self, *, root: Path) -> FileArtifactStore: ...

    @property
    def plan_id(self) -> str: ...

    @property
    def temporal_boundary(self) -> datetime: ...

    @property
    def now(self) -> datetime: ...

    @property
    def expires_at(self) -> datetime: ...

    @property
    def max_ttl_seconds(self) -> int: ...

    @property
    def replay_record_class(self) -> str: ...

    @property
    def query_pin_class(self) -> str: ...

    @property
    def artifact_store_dirname(self) -> str: ...

    @property
    def half_life_table(self) -> HalfLifeTable: ...

    @property
    def debt_profile(self) -> DebtProfile: ...

    @property
    def ledger_t(self) -> int | None: ...

    @property
    def facts(self) -> Mapping[str, Any]: ...

    @property
    def findings(self) -> Sequence[Any]: ...

    @property
    def stores_opened(self) -> Sequence[str]: ...

    @property
    def duplicate_finding_type(self) -> str: ...

    @property
    def required_signal_classes(self) -> Sequence[str]: ...


@dataclass(frozen=True)
class AnchorUnresolvable:
    """§D.2 step 1's fail-closed refusal — `404`, never an empty payload.

    Returned as DATA, so a caller renders it rather than catching it.

    **An empty payload would be a false statement rather than a thin one.** A
    family with no members reads as *this company has no subsidiaries*, which is
    a claim about the world. The absence of an answer is not an answer of zero —
    the same distinction §C.4 trap 5 draws inside the payload, drawn here at the
    payload's edge.
    """

    anchor: str
    status: int = 404
    reason: str = "anchor-unresolvable"


@dataclass(frozen=True)
class AnchorAmbiguous:
    """§D.2 step 1 resolved the LEI to MORE THAN ONE node — returned as DATA.

    The spine branches on it exactly as it branches on ``None``: before the
    graph is touched, before anything is ingested, before any envelope is
    built. The assembler seam turns it into the SDK kind
    ``ccf.products.request.AnchorAmbiguityRefusal`` and RETURNS that through
    the D-60 channel, so a door carries it as ``anchor-ambiguity-refusal``.

    **Why neither of the two nearby answers is this one** (`D-IMPL-245` (4),
    Dave: *"Not 404, and definitely not 'serve with a finding'"*). A 404 says
    *nothing resolved*, which is false — two things did. Serving one candidate
    with a finding attached would let ambiguity in E flow downstream as merely
    another finding, and the whitepaper's E-dimension invariant is that when
    the anchor is ambiguous, everything attached to it is unreliable. *"Ambiguity
    should therefore fail closed as typed ambiguity data."*

    No HTTP status field: cp-04 ships no HTTP door and the SDK kind carries
    none. ``candidates`` is every IRI that answered, sorted and distinct, so
    the refusal names the collision rather than a row-order winner.
    """

    anchor: str
    candidates: tuple[str, ...]
    reason: str = "anchor-ambiguous"


@dataclass(frozen=True)
class ParameterNotSupported:
    """Standard §2.4's declared-but-inert refusal — `400`, returned as data.

    *"A parameter that appears to work and does not will be relied on in a
    dispute."* The parameter IS part of the uniform surface — it is declared in
    the request contract, so a caller can discover it — and it fails explicitly
    rather than succeeding silently against current state. Those are the two
    halves of §2.4 and neither works without the other.

    **`as_of` is the one this tier declares and refuses** (§B.4.3, gate
    `CFT-G06`), and the pressure on it is specific rather than theoretical: this
    is the first rung whose store carries a time axis of its own. Fluree's `t` is
    TRANSACTION time and `D-IMPL-88` rules it must not implement `as_of`;
    Fluree's `@iso:` searches EVENT time, nearest-at-or-before, and is
    BACKDATABLE. Neither is what `as_of` asks, so answering with today's family
    would be the most plausible wrong answer this product could give.

    **CONSTRUCTED ONLY AS A TEST CONTROL SINCE `24.5.1` am.3 / `24.6-L-13`.**
    Nothing in this module returns it: the SDK's own tier step refuses a
    declared-but-inert parameter as `not-supported-at-tier` data before any
    product branch runs, and the branch that returned this class was deleted as
    unreachable. The class is KEPT because
    `tests/examples/test_cp_04_payload.py` constructs it to prove the payload
    shape §2.4 asks for, and deleting the type would delete that control's
    subject.
    """

    parameter: str
    reason: str
    status: int = 400


@dataclass(frozen=True)
class Assembled:
    """What one run produced, for a caller to inspect.

    The spine *returns* its state rather than checking it, so the assertions can
    live where a test runner will actually run them.

    :attr:`view` is the composed graph state Π ran over — the last readable
    evidence that the write path executed at all, and an empty one is what a
    mis-set boundary produces. :attr:`gated` is the
    :class:`~ccf.products.gates.ServableProduct` itself rather than only the
    contract inside it: the type is not constructible outside
    :func:`~ccf.products.gates.run_gates`, so holding one is direct evidence the
    gates ran.

    :attr:`stores_opened` is what gate `CFT-G10` reads, and it is recorded WHERE
    THE CONNECTIONS ARE MADE — inside the deployment's own source read — rather
    than asserted by a caller who could have been handed a pre-populated graph.
    """

    tenant_id: str
    scenario: Scenario
    product: ContextProductContract
    #: AMENDED 2026-10-11: the resolver's delivery. ``ServableProduct`` is no
    #: longer handed to a deployment — the gates run inside the SDK's resolver,
    #: whose only path to a ``ServedProduct`` is ``DeliveryCapability.deliver``
    #: over a ``ServableProduct`` after the record is appended — so holding
    #: this, with its record readable from :attr:`store`, is the evidence.
    gated: ServedProduct
    operators_invoked: frozenset[str]
    view: GraphView
    record: DecisionReplayRecord
    served: ServedProduct
    store: FileArtifactStore
    minted: Mapping[str, str]
    stores_opened: tuple[str, ...]


# --8<-- [start:boot]
def _boot(
    *,
    config: Path,
    connection: Mapping[str, object],
    registry: ControlPlaneRegistry,
) -> BootedFabric:
    """The boot. **Not one of §D's ten steps** — the ten begin once a fabric
    exists, and saying so keeps the counts honest.

    One call replaces the registration prologue and the boot. The single
    `ccf_config.yaml` names every section in force, `load_config_and_boot`
    derives and parses all of them, registers the `role: register` ones, and
    boots on the resulting pins.

    **CONNECTION VALUES ARRIVE HERE, FROM THE CALLER — never from the config**,
    which declares the backend as a KIND only. A DSN or a URL inside a
    content-hashed artifact is one persisted into the audit plane forever.

    The fabric's own L3 is per-run SQLite. The two SOURCE stores this product
    reads — Fluree for edges and ontology, PostgreSQL for attributes — are
    reached from `backends.yaml` by the deployment, and neither is opened here.
    """
    return load_config_and_boot(config, registry=registry, connection=connection)
# --8<-- [end:boot]


# --8<-- [start:acquire]
def _ingest(
    booted: BootedFabric,
    *,
    scenario: Scenario,
    claims: Callable[..., Sequence[RelationshipClaim]],
) -> Mapping[str, str]:
    """§D steps 1, 3, 4, 6, 7 and 8 land here, and only the write is the spine's.

    1. **Resolve the anchor** — L2, in the deployment's source read. Fails closed
       to a `404` before this function is reached; there is no envelope for a
       family that does not exist.
    3. **Read the family from Fluree** — six predicates, unioned fixed-length
       SPARQL patterns to the DECLARED CEILING, plus the `ledger_t` read at.
    4. **Normalize to parent→child** — per-predicate direction from the
       declaration, set semantics: 1,058 raw triples to 722 distinct edges over
       the whole ledger, and the collapse reported rather than hidden.
    6. **Resolve attributes from PostgreSQL** — ONE batched select over the
       collected LEIs against `legal_entity`, with a NULL RESOLUTION for the
       LEIs that do not resolve and never a dropped member.
    7. **Detect cycles** — application-side elementary-circuit enumeration,
       canonicalized by rotation to the lexicographically smallest member.
    8. **Surface the duplicate pair** — label-and-identity comparison.

    **All six name a store, a predicate or a column, so all six live behind the
    deployment seam and this function does not reimplement one.** What the spine
    owns is the WRITE: `booted.handle.worker` is the single writer
    (CLAUDE.md §10, INV-CH7-10). The two estates the deployment READ from are
    not reachable from here at all: the fabric's write path leads into the
    fabric's own state and nowhere else.

    **ONE ENVELOPE PER NODE, AND THE SHAPE IS FORCED BY A MEASURED PROPERTY OF
    THE SDK** (`D-35`). `src/ccf/assembly/worker.py::AssemblyWorker.ingest`
    mints relationship claims by CLASS CO-OCCURRENCE: every declared rule whose
    subject and object classes both resolve from one envelope fires, and nothing
    selects the relationship type from the payload. Measured live, one envelope
    carrying one `entity_uri` minted 2 entities and TWELVE relationships, SIX of
    them self-loops, across all six declared predicates. So `ccf_config.yaml`
    declares `relationship_rules: []` and each normalized edge is admitted
    instead through `worker.admit_relationship_claim`, carrying ITS TRUE
    PREDICATE. Still one writer, still L2, and no file under `src/` changes.

    Returns the SOURCE-IRI → MINTED-URI map, which is knowable only here. The
    graph mints `<entity-class>://<identity-hash>` and the identity keys are
    consumed by the resolver rather than stored back as attributes, so nothing
    downstream can recompute it without reimplementing L2's identity rule.
    """
    by_envelope = {
        envelope_id: uri for uri, envelope_id in scenario.envelopes_by_node.items()
    }
    minted: dict[str, str] = {}
    for envelope in scenario.envelopes:
        result = booted.handle.worker.ingest(envelope)
        source = by_envelope[envelope.envelope_id]
        for upsert in result.entities:
            minted[source] = upsert.node_key
    for claim in claims(minted=minted):
        booted.handle.worker.admit_relationship_claim(
            tenant_id=booted.tenant_id, claim=claim
        )
    return minted
# --8<-- [end:acquire]


# --8<-- [start:govern]
def _govern(
    booted: BootedFabric,
    *,
    scenario: Scenario,
    registry: ControlPlaneRegistry,
    plan_class: Callable[..., ProjectionPlan],
    minted: Mapping[str, str],
    root: Path,
) -> tuple[ServedProduct | RefusalEnvelope, FileArtifactStore, Mapping[str, Any]]:
    """§D steps 2, 5, 9 and 10, and the gates, the record and the delivery.

    AMENDED 2026-10-11. The governed resolver registers this class's MaxTTL and
    request surface from the deployment's declarations, builds the two
    DECLARED operators (Policy first — step 2 — then the walk, step 5), runs
    Π (step 9), holds the claimed lineage to what ran, runs the three L6
    gates, and appends the five-dimension record before it delivers (step 10).
    What is left here is this deployment's seams: which keys, which Π, which
    D_c. Every argument is a NAME or a number this deployment declared.

    The D_c is the same reading as before — ``measure_debt`` over the members
    Π SERVED — so the scorer reads the plan the factory built, after the
    resolver ran it. The view Π ran over is kept for the caller.
    """
    witnessed: dict[str, Any] = {}

    def plan_factory(
        *, required: tuple[str, ...], request: ProductRequest
    ) -> ProjectionPlan:
        plan = plan_class(
            plan_id=scenario.plan_id,
            required=required,
            scenario=scenario,
            minted=minted,
        )
        witnessed["plan"] = plan
        return plan

    def debt_scorer(*, view: GraphView, evidence: object = None) -> DebtAssessment:
        witnessed["view"] = view
        return measure_debt(scenario, served=witnessed["plan"].served_members)

    store = deployment_store(scenario, root=root)
    resolve = build_governed_resolver(
        fabric=booted,
        control_plane=registry,
        product_class_key=scenario.product_class_key,
        request_contract_key=scenario.request_contract_key,
        operator_parameter_keys=tuple(scenario.operator_parameters),
        policy_bundle_key=scenario.policy_bundle_key,
        plan_factory=plan_factory,
        debt_scorer=debt_scorer,
        artifact_store=store,
        # SEC-009 (D-IMPL-374 (4), C1): the declared durable erasure index.
        erasure_trust=ErasureTrust(authorities={}),
        erasure_index=erasure_index_at(store.root),
        replay_record_class=scenario.replay_record_class,
        query_pin_class=scenario.query_pin_class,
        max_ttl_seconds=scenario.max_ttl_seconds,
        product_ttl_seconds=scenario.ttl_seconds,
        # The substrate capability `max_depth` is bound to — the same one the
        # assembler's own resolution is handed.
        capabilities=scenario.capabilities,
    )
    outcome = resolve(
        tenant=booted.tenant_id,
        product_class=scenario.product_class.schema_name,
        version=scenario.product_class.schema_version,
        perspective=scenario.perspective,
        request=scenario.request,
    )
    return outcome, store, witnessed
# --8<-- [end:govern]


def deployment_store(scenario: Scenario, *, root: Path) -> FileArtifactStore:
    """The store the record lands in, declared with its write kinds.

    AMENDED 2026-10-11: ``FileArtifactStore`` takes a required ``write_kinds``
    (D-IMPL-353 §1.2). A deployment-side call, so the spine imports nothing
    from the example: the store is the one ``deployment.artifact_store``
    declares, reached through the scenario's own module.
    """
    return scenario.artifact_store(root=root)


def measure_debt(scenario: Scenario, *, served: Sequence[str]) -> DebtAssessment:
    """`D_c` over what this question assembled — whitepaper §7.7, spec §E.2.

    **`served` IS THE ROSTER THIS PAYLOAD EMITTED, AND IT IS AN ARGUMENT RATHER
    THAN A LOOKUP.** `S` below is taken over it. Taking `S` over the
    deployment's SOURCE-READ population instead is the defect the 2026-09-01
    close panel found (Dave: *"a wrong denominator"*): the source read is bounded
    by the DECLARED CEILING and the caller's `max_depth` is applied downstream of
    it by the L4 traversal, so a `max_depth=1` request that served 20 members
    still reported `20/22`, and `D_c` read `0.0909` at depth 1, 2 and 3 alike —
    a scalar that cannot move with what was actually served, which is the
    idle-gate class arriving through a float.

    **F — FRESHNESS, NORMALIZED OVER THE REQUIRED SIGNAL CLASSES AND NOT OVER
    THE CLASSES PRESENT.** §E.1 states the rule and says why: normalizing over
    what is present would let a missing source improve the score. `λ_c` is per
    signal class, so one payload carries an ownership edge decaying at ~180 days
    beside an Exhibit 21 subsidiary at ~365 and an attribute row at ~30.

    **EVERY OBSERVATION IS DATED AT THE READ INSTANT, AND THAT IS A FINDING
    RATHER THAN A CONVENIENCE.** Measured over the committed fixture, **no
    family node and no family edge carries an assertion date of any kind** — the
    ledger holds the six predicates, `ex:lei`, `rdfs:label` and `rdf:type`, and
    no timestamp — so every envelope carries `observed_time=None`, which
    `SignalEnvelope`'s own contract defines as *unknown*. Fluree's `t` is
    TRANSACTION time and `D-IMPL-88` rules it must not stand in for an
    observation, so there is no second candidate in the store either. The honest
    consequence is that F reads 1 at every read, and that is recorded here
    rather than presented as freshness. See
    `deployment.py::FamilyScenario.expires_at` for what the same absence costs
    the declared TTL anchor.

    **C — COMPLETENESS, over the elements §E.2 declares REQUIRED.** The
    whitepaper defines C as *"the fraction of required fields actually populated
    across the assembled sources"*, and §E.2's table names which elements may be
    absent and which may not. The four that may NOT — the anchor's own
    resolution, the policy envelope, the Fluree family read, and the class chain
    on every returned node — are fail-closed conditions reached long before this
    function: a product holding a gated vessel has all four. Cycle detection is
    the fifth and runs unconditionally. So C is 1 whenever this function is
    reached, and it is a structural property rather than a measurement that
    could have come out otherwise.

    **S — SEMANTIC CONSISTENCY, and this is the first rung on the ladder that
    can have one.** The whitepaper defines S as *"the fraction of assembled
    sources whose structured assertions agree on the entities, relationships and
    magnitudes the decision cares about"*. Rung 03 recorded S as a structural 1
    because it read ONE store and nothing could disagree. This product reads TWO
    and its graph leg contains a measured self-disagreement: the
    duplicate-identity finding, the same company entered twice one hop from the
    anchor. S is therefore the fraction of served members whose identity no
    finding disputes, which for the demonstration anchor AT THE DECLARED DEFAULT
    DEPTH OF 3 is 20 of 22 — two nodes naming one company.

    **DEPTH IS A REAL BOUNDARY FOR THIS SCALAR AND THE FIGURE IS NOT A
    CONSTANT.** Both disputed members sit one hop from the anchor, so they
    survive every depth the product accepts while the denominator shrinks with
    it: at `max_depth=1` the payload carries 20 members and `S` is `18/20 = 0.9`,
    giving `D_c = 0.1`. Measured, both of them, and pinned as data in
    `artifacts/expected.yaml::debt_by_depth`.

    **ONE PART OF §E.2 IS NOT IMPLEMENTED HERE AND IT IS RECORDED RATHER THAN
    RESOLVED.** The table routes *"attribute resolution for a given node"* to
    `S` with the behavior *"serve with a null resolution and elevated `D_c`"*.
    Those two cannot both hold at this rung's declared numbers, and the conflict
    is arithmetic rather than editorial: 20 of the SMCI subtree's 22 members hold
    no `ccf_v2.legal_entity` row, so folding attribute coverage into `S`
    multiplicatively gives `S = 2/22` and `D_c ≈ 0.909` against a declared
    `debt_tolerance` of `0.25` — the product would refuse `409` and never serve
    the tree that criteria 12 and 33 and gate `CFT-G09` exist to protect. The
    reconciling per-component weights are `[TBC — this build]` in §E.2's own
    words, so there is no declared value to apply and inventing one would be
    choosing the number that decides whether this product's headline
    demonstration exists.

    **So the shortfall is SERVED AS DATA rather than folded into a scalar
    nobody chose.** The 20 members surface as an `unresolved_jurisdiction`
    finding carrying their ROSTER (`D-IMPL-229`), each carries `attributes:
    null`, and *"the group is these 22 entities and we hold reference data on
    two of them"* reaches the consumer as a decision input rather than through a
    debt figure. **`606 of 748` is not a defect report; it is the answer.**
    Whether §E.2's `S` routing is amended, whether `debt_tolerance` moves, or
    whether the weights are declared is a ruling this build does not take.
    """
    observations = tuple(
        Observation(
            observation_type=signal_class,
            observed_at=scenario.now,
            subject=f"{scenario.request.subject}:{signal_class}",
        )
        for signal_class in sorted(set(scenario.required_signal_classes))
    )
    if not observations:
        # `FreshnessScorer` refuses an empty sequence by design: "the fabric
        # retrieved nothing" is a coverage statement, and letting it enter as
        # perfect freshness would launder a source outage into a low-debt
        # reading. A family whose read produced no signal class at all is that
        # outage, so this is the maximum rather than a score for nothing.
        return assess_debt(
            DebtFactors(
                freshness=Decimal(0),
                completeness=Decimal(0),
                semantic_consistency=Decimal(1),
            ),
            profile=scenario.debt_profile,
        )
    scorer = FreshnessScorer(
        table=scenario.half_life_table,
        risk_sensitivity=scenario.debt_profile.risk_sensitivity,
    )
    return assess_debt(
        DebtFactors(
            freshness=scorer.score(observations, now=scenario.now),
            completeness=Decimal(1),
            semantic_consistency=_agreement(scenario, served),
        ),
        profile=scenario.debt_profile,
    )


def _agreement(scenario: Scenario, served: Sequence[str]) -> Decimal:
    """S — the fraction of served members whose identity no finding disputes.

    Measured rather than declared. The duplicate-identity finding is a real
    disagreement inside the graph leg: two nodes carrying labels that fold to
    one company, exactly one of which holds an LEI — so an LEI-keyed comparison
    finds nothing and a URI-prefix rule fires on all seventeen Exhibit 21 stubs
    beside them. A family that double-counts a subsidiary is a concentration
    denominator wrong in the safe-looking direction.

    **THE DENOMINATOR IS `served` AND NOT `scenario.facts`.** The two are the
    same set at the declared default depth and differ at every other one, which
    is exactly why the substitution went unnoticed until the 2026-09-01 close
    panel: `scenario.facts` is the SOURCE READ, bounded by the declared ceiling,
    and the caller's `max_depth` is applied after it by the L4 traversal. Taking
    `S` over the source read makes this scalar a function of the estate alone,
    unable to move with the question — the docstring above said *served* while
    the code said *read*, and the code was the wrong one.

    An empty family scores 0 rather than 1: perfect agreement among no members
    is the vacuous pass, not the clean one.
    """
    members = tuple(sorted(set(served)))
    if not members:
        return Decimal(0)
    disputed = {
        uri
        for finding in scenario.findings
        if finding.type == scenario.duplicate_finding_type
        for uri in finding.members
    }
    return Decimal(len(members) - len(disputed & set(members))) / Decimal(len(members))


def assemble_and_serve(
    *,
    config: Path,
    connection: Mapping[str, object],
    read: Callable[..., Scenario | None],
    plan_class: Callable[..., ProjectionPlan],
    claims: Callable[..., Sequence[RelationshipClaim]],
    request: ProductRequest,
    root: Path,
    max_depth: int,
    assembler_id: str,
    assembler_version: str,
    role: str | None = None,
    unsupported: Mapping[str, str] | None = None,
    resolution: EffectiveRequest | None = None,
) -> (
    Assembled
    | ProductRequestViolation
    | AnchorUnresolvable
    | AnchorAmbiguous
    | AssemblyRefusal
    | RefusalEnvelope
):
    """Answer one question, end to end, against ``root`` as scratch space.

    The steps run in the order the specification's section D fixes them and the
    seven snippet regions above are opened in that same order.

    ``unsupported`` is THE DECLARED SET, FOR THE RECORD, and nothing reads it
    here (``24.6-L-13``). It used to feed a loop below ``refuse_request`` that
    returned :class:`ParameterNotSupported` for a declared-but-inert parameter.
    That loop was dead by construction: ``refuse_request``'s tier step reads
    ``declared.unsupported_arguments`` from the SAME ``ccf_config.yaml`` block
    the caller fills this argument from, so it had already returned
    ``not-supported-at-tier`` as data for every key the loop could match. The
    loop is deleted and ``ParameterNotSupported`` leaves this return union; the
    parameter stays so the call site keeps naming the declared set explicitly.
    """
    registry = ControlPlaneRegistry()

    # `max_depth` IS AN INTEGER AND THAT IS ESTABLISHED, NOT HOPED. The
    # effective request was resolved before this call — defaults, caller,
    # policy, then the substrate's traversal capability — and every value was
    # held to the declared surface there, so a depth that was not an integer
    # never reached a call to this function (`24.6-L-01`). SUPERSEDED
    # 2026-09-04: an `isinstance` branch stood here returning the deployment's
    # own over-bound refusal value as data.

    booted = _boot(config=config, connection=connection, registry=registry)
    try:
        # The one line that crosses the deployment seam: the deployment names
        # its own artifact keys, opens its own two stores, and hands back this
        # question's values.
        #
        # `None` means the anchor resolved to no entity. §D.2 makes that a 404
        # BEFORE the graph is touched.
        scenario = read(booted, request, max_depth=max_depth, role=role)
        if scenario is None:
            return AnchorUnresolvable(anchor=request.subject)

        # AN UNDECLARED ROLE REACHED AT THE DEPLOYMENT SEAM IS A DETERMINATION
        # AND IS RETURNED (`24.6-L-02`, D-15). It is in `REFUSAL_KINDS`, so
        # both callers envelope it with no edit of their own.
        if isinstance(scenario, AssemblyRefusal):
            return scenario

        # MORE THAN ONE NODE ANSWERED TO THE ANCHOR. Returned as the typed value
        # it arrived as — never a 404, never one candidate with a finding
        # (`D-IMPL-245` (4)) — and before the graph is touched, exactly as the
        # ``None`` case above. The class is this module's own, so the branch
        # is a real ``isinstance`` rather than a duck-typed attribute probe.
        if isinstance(scenario, AnchorAmbiguous):
            return scenario

        # AMENDED 2026-10-11: a caller-stated `families` that disagrees with
        # the subject's family is refused by the deployment's read, as data.
        if isinstance(scenario, ProductRequestViolation):
            return scenario

        # Checked before the graph is touched, so a question this class does not
        # answer costs nothing and returns a reason rather than an approximation.
        violation = refuse_request(
            request=scenario.request, declared=scenario.request_contract
        )
        if violation is not None:
            return violation

        minted = _ingest(booted, scenario=scenario, claims=claims)

        outcome, store, witnessed = _govern(
            booted,
            scenario=scenario,
            registry=registry,
            plan_class=plan_class,
            minted=minted,
            root=root,
        )
        # AMENDED 2026-10-11: a governed refusal the resolver reached (an
        # expired question, a stale `asked_at`, a gate) is ALREADY RECORDED —
        # the resolver appends its five-dimension record before it returns —
        # so it is handed back as data, beside the four refusals above.
        if not isinstance(outcome, ServedProduct):
            return outcome
        record = DecisionReplayRecord.model_validate_json(
            store.get(content_address=outcome.replay_ref.content_address)
        )
        return Assembled(
            tenant_id=booted.tenant_id,
            scenario=scenario,
            product=outcome.product,
            gated=outcome,
            # From the RECORD's own account of the plan.
            operators_invoked=frozenset(record.content_generation_path.operator_plan),
            view=witnessed["view"],
            record=record,
            served=outcome,
            store=store,
            minted=minted,
            stores_opened=tuple(scenario.stores_opened),
        )
    finally:
        booted.handle.close()
