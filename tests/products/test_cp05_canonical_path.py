"""The stop rule, measured against cp-05 rather than inferred from ``s1-01``.

``24.10-05``. ``D-IMPL-280``'s stop rule names one product and this module is
where it is answered:

    *"When **cp-05** can use the canonical SDK path without rebuilding fabric
    behavior itself, Phase 24.10 stops."*

``D-IMPL-281`` (Dave, 2026-09-08) rules how the question is asked, and the
method is the whole reason this module exists rather than a rewiring commit:

    *"Keep the phase SDK-only. **Prove the stop rule by driving cp-05's
    existing declarations through** ``GovernedResolver`` **in a focused test**
    without changing cp-05's shipped files, transcripts, or published
    artifacts. After 24.10 closes, cp-05 can be rewired as the post-phase
    adoption step."*

    *"That preserves the spirit of ``D-IMPL-261``: the example remains the
    probe and evidence source rather than becoming the repair surface during
    SDK remediation."*

**Not one byte of cp-05 is written by this module.** Its four YAML documents
are read as test inputs — the use the phase boundary explicitly permits — and
none of its Python is imported. Nothing under ``examples/`` is rerun for
repair, re-pinned or republished.

The verdict
-----------
**The stop rule is NOT met.** cp-05's shipped declarations, driven unchanged
through :func:`~ccf.products.resolver.build_governed_resolver`, return a
**served product describing a family of 0** over an L3 holding **77 entities
and 100 relationship claims** — every universal gate green, a content address
minted, a replay record filed. That is not a thinner answer than cp-05's; it
is a confidently wrong one, and it is exactly the failure mode cp-05's own
specification §A exists to name.

**That outcome is a successful completion of this plan, not a failure of it.**
``D-IMPL-283`` (4), Dave, verbatim:

    *"'cannot adopt without an unruled SDK change' is an admissible
    **successful** phase outcome. The plans must not structurally force a
    workaround just to get a green completion check. That is exactly the
    ``D-IMPL-261`` lesson."*

So nothing here is worked around. The two findings this module measures are
left **executable**, marked ``xfail(strict=True)`` carrying their finding id,
so each fails today because a seam is absent and fails *loudly* — ``XPASS``
under ``strict`` — on the day a seam lands and its finding is not closed.

The findings
------------
``24.10-F-11``
    **cp-05's declared operator envelope cannot be bound to the question being
    asked.** :meth:`~ccf.products.resolver.GovernedResolver._operator_parameters`
    reads its operator-parameters artifacts verbatim off
    :attr:`~ccf.deployment.BootedFabric.artifacts` by key, with no request in
    scope. cp-05 declares ``permitted_classifications: []`` **on purpose** —
    *"The declaration is empty on purpose and admits nothing; the substitution
    is what makes it admit THIS family and no other"* — and binds the family
    per request. On the canonical path the empty declaration stands, the policy
    operator admits nothing, the traversal chains from its empty output, and
    the served family is 0. Measured both ways: unbridged **0**, and **77**
    with the same per-request substitution cp-05 already performs.

``24.10-F-12``
    **A request-contract declaration the Control Plane admits at boot is
    refused at resolver-build time.** cp-05's ``request_contract`` section
    authors ``unsupported_arguments`` as a *list*;
    :meth:`~ccf.products.request.ProductRequestContract.from_declared` requires
    a *mapping* of name to reason prose. ``load_config_and_boot`` accepts the
    document — the section is an adopter-owned ``DeclaredArtifact`` whose body
    is opaque at boot — and ``build_governed_resolver`` raises ``ValueError``
    from three frames down. The consequence for adoption is arithmetic: the
    config delta between cp-05's shipped document and one the canonical path
    can serve is **three** changes, not the two declarative additions waves 1
    and 2 created.

Which of plan 04's findings do NOT bite cp-05, stated rather than inferred
--------------------------------------------------------------------------
An absence measured is a result. ``24.10-04`` found four walls against
``s1-01``; against cp-05, one of them reproduces and three do not:

``24.10-F-06``
    **Not implicated.** cp-05 declares two operators —
    ``policy.principal-subgraph`` and ``traversal.typed-neighborhood`` — and no
    similarity artifact, so :func:`~ccf.deployment.build_operator_registry`
    never reads a corpus version identity off one (`24.11-02b`: the version is
    declared on the similarity artifact, and cp-05 declares none). The wall
    that stopped
    ``s1-01`` at step 4 of nine is not on cp-05's path at all, which is why
    cp-05 gets far enough to be *wrong* rather than far enough to *raise*.

``24.10-F-07``
    **Reproduced.** Two questions naming two different subjects pin
    **identically** on cp-05's path, exactly as they did on ``s1-01``'s. The
    finding's executable evidence stays where ``24.10-04`` filed it —
    ``tests/examples/test_s1_01_governed_resolver_adoption.py`` — rather than
    being re-minted here under a second id; the cp-05 measurement is recorded
    in this plan's SUMMARY with the command that produced it.

``24.10-F-08``
    **Not implicated.** cp-05 sets none of ``obligation_in_force``,
    ``source_refresh_recency`` or ``debt_evidence`` on the vessel; it carries
    its debt evidence inside ``payload["context_debt"]``. The three members
    are ``None``/sentinel under the resolver and were ``None``/sentinel under
    cp-05's own spine, so nothing about this product's answer moved.

``24.10-F-09``
    **Not implicated.** cp-05's TTL anchor is ``from_decision`` and its
    ``artifacts/ttl.yaml`` records why: *"``expires_at`` is REQUEST TIME + 4
    HOURS."* There is one instant, so collapsing two cannot cost it anything —
    measured, ``expires_at`` comes back at ``asked_at + 14400s``, which is what
    cp-05's own product produces.

What the harness supplies, and how each is classified
------------------------------------------------------
The point of this exercise is *what cp-05 still has to bring*, so every reach
into cp-05 is classified where it is made and the roster is written into the
SUMMARY. Two classes only: an **extension point** the SDK expects a deployment
to supply, or **fabric behavior cp-05 is rebuilding** — and the second class is
the finding set.

* the four YAML documents — **declarations**, the class the SDK expects a
  deployment to author;
* ``plan_factory`` — **extension point**, named as one by Dave;
* ``debt_scorer`` — **extension point**, named as one by Dave. The reference
  scorer could not be *selected* here: it keys ``λ_c`` by the **entity class**
  of each L3 row (:class:`~ccf.products.debt_scorer.AssemblyDebtScorer`'s own
  ``Raises:`` note), and cp-05's table is keyed by domain observation type —
  ``outstanding_balances``, ``ownership_edges`` and three more. So the override
  path is taken, which is what the two argument shapes are for. Recorded as an
  observation about the reference scorer's reach, **not** as a finding: the
  seam exists, is documented, and Dave names it by name.
* ``product_gate`` — **extension point as of wave 2**, and it works: test 4
  below is ``R-11``'s seam carrying cp-05's own declared invariant.
* ``bound_policy_envelope`` — **GONE at** ``24.11-04``, and its deletion is the
  finding's closure rather than tidying. It was a measurement device that
  performed the same runtime substitution cp-05's own ``populate_and_traverse``
  performs, so the wall behind ``24.10-F-11`` was observable. cp-05 now
  DECLARES the binding (``ccf_config.yaml``'s ``permitted_classifications:
  {source: effective_request, parameter: families}``), the SDK resolves it
  against the governed effective request, and there is nothing left for a
  bridge to bridge. The workaround is deleted **because the SDK made it
  unnecessary** — never relocated (``D-IMPL-289``).

Offline by construction
-----------------------
Population comes from ``24.10-03``'s captured fixture through
:class:`~ccf.signal.acquisition.FileRecordAcquisitionSource` and that plan's
own ``drive_into_l2``, imported rather than copied so this module and plan
03's cannot drift about what 77/100 means. This module carries **no**
``fluree`` marker and **no** environment-gated skip: a stop-rule test that
could pass by skipping would have proved nothing.
"""

from __future__ import annotations

import asyncio
import copy
import json
import pathlib
import uuid
from collections.abc import Iterator, Mapping, Sequence
from datetime import datetime
from decimal import Decimal
from typing import Any, NamedTuple

import pytest
import yaml

from ccf.controlplane.artifacts import HalfLifeTable, PolicyFilterParametersArtifact
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.deployment import BootedFabric, load_config_and_boot
from ccf.halflife.debt import DebtAssessment
from ccf.products.contract import ContextProductContract
from ccf.products.debt_scorer import AssemblyDebtScorer, DeclaredFactor
from ccf.products.refusal import RefusalEnvelope
from ccf.products.request import ProductRequest, ProductRequestContract
from ccf.products.resolver import GovernedResolver, build_governed_resolver
from ccf.projection.plan import Perspective, ProjectionOutput
from ccf.signal.acquisition import FileRecordAcquisitionSource
from ccf.signal.envelope import SignalEnvelope

from tests.signal_layer.test_cp05_acquisition_boundary import (
    ASKED_AT,
    FAMILY,
    FIXTURE,
    SOURCE,
    counts_off_l3,
    drive_into_l2,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

#: cp-05's shipped tree. **READ ONLY.** Nothing below opens any of these for
#: writing, and no module under this directory is imported.
CP_05 = REPO_ROOT / "examples" / "cp-05-credit-exposure-rollup"

CONFIG = CP_05 / "ccf_config.yaml"
REPLAY_ARTIFACT = CP_05 / "artifacts" / "replay.yaml"
QUESTION_ARTIFACT = CP_05 / "artifacts" / "question.yaml"
TTL_ARTIFACT = CP_05 / "artifacts" / "ttl.yaml"

DECLARATION = "declaration"

# --------------------------------------------------------------------------
# The manifest keys cp-05's config derives, named rather than discovered.
#
# A resolver's wiring IS a deployment naming its own keys — that is what
# `build_governed_resolver` asks for — so naming them here is part of what the
# adoption cost measurement is measuring, not a shortcut around it.
# `load_config_and_boot` keys each derived entry by its section label
# (`ccf.deployment.config::_RESERVED_SECTIONS`), and the two operator entries
# by the operator names cp-05's `operators:` mapping declares.
# --------------------------------------------------------------------------

PRODUCT_CLASS_KEY = "product_class"
REQUEST_CONTRACT_KEY = "request_contract"
POLICY_BUNDLE_KEY = "policy"
HALF_LIFE_KEY = "half_life"
DEBT_PROFILE_KEY = "debt_profile"
PERSPECTIVE_KEY = "default_perspective"
POLICY_OPERATOR_KEY = "policy.principal-subgraph"
TRAVERSAL_OPERATOR_KEY = "traversal.typed-neighborhood"
OPERATOR_PARAMETER_KEYS = (POLICY_OPERATOR_KEY, TRAVERSAL_OPERATOR_KEY)

# --------------------------------------------------------------------------
# The config delta — the measurement of what adoption still costs
# --------------------------------------------------------------------------

#: Wave 1's `R-12` addition: the `replay:` Control Plane section, populated
#: verbatim from the three members `artifacts/replay.yaml` already names.
#: Wave 1 chose those member names so this derivation involves no
#: transcription.
DELTA_REPLAY = "replay"


#: The gate identity cp-05 would declare for the invariant it already runs.
#: Test-side vocabulary, never an SDK value (CLAUDE.md §6.4): the gate's
#: IDENTITY is the Control Plane's half and its implementation is the
#: deployment's, and cp-05 authored neither because the seam post-dates it.
GATE_ID = "cp-05.reconciliation-guard"
GATE_VERSION = "1.0.0"

#: The refusal kind `R-11` added, so a runtime gate failure is distinguishable
#: in replay from a universal-gate refusal.
PRODUCT_INVARIANT_REFUSAL = "product-invariant-refusal"

#: cp-05's shipped figures, transcribed from its published run transcript as
#: test inputs (read, never edited). Gross exceeds adjusted by the 800,000,000
#: the guarantee dedup removed — the NOT-firing control for test 4.
CP05_GROSS_COMMITTED = 10_125_000_000
CP05_ADJUSTED_COMMITTED = 9_325_000_000

#: The plausible wrong answer cp-05's guard exists to catch: the same adjusted
#: figure against a gross the dedup was ALSO subtracted from. cp-05's own
#: words — *"step 5.2 removed the same exposure twice."*
DOUBLE_SUBTRACTED_GROSS = CP05_ADJUSTED_COMMITTED - 800_000_000

#: The family count `24.10-03` measured off L3 through the acquisition
#: boundary, and cp-05's own published family size.
DECLARED_FAMILY_SIZE = 77
DECLARED_RELATIONSHIP_CLAIMS = 100

#: The payload member this harness's Π emits. cp-05's own product carries a
#: much larger payload; the family size is the one member the wall is visible
#: in, and it is the one cp-05's own empty-operator guard reads.
FAMILY_SIZE_MEMBER = "family"


# --------------------------------------------------------------------------
# cp-05's declarations, loaded as test inputs
# --------------------------------------------------------------------------


def _load(path: pathlib.Path) -> dict[str, Any]:
    """One of cp-05's YAML documents, read and never written."""
    parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(parsed, dict)
    return parsed


def shipped_config() -> dict[str, Any]:
    """cp-05's Control Plane document exactly as it ships."""
    return _load(CONFIG)


def derived_config() -> dict[str, Any]:
    """cp-05's shipped document, used as it ships. **Nothing is added.**

    This function once returned cp-05's config plus the two declarative
    additions the canonical path required — a ``replay:`` binding and a
    ``declared_product_gate`` — and, while the SDK forced it, a third reshaping
    of ``unsupported_arguments``. All three are **gone from the overlay because
    they are gone from the problem**: `24.11-05` moved the third into cp-05's
    own declaration (`D-IMPL-296`), and `D-IMPL-299` moved the other two into
    the shipped ``ccf_config.yaml`` as part of cp-05 adopting the canonical
    path.

    Kept as a named function rather than inlined at its callers, and kept
    returning a **copy**, because the name is what the tests below read as
    *"the document the canonical path is driven with"* — and the whole claim
    now is that this is cp-05's own document, unmodified.
    """
    return copy.deepcopy(shipped_config())


def delta_paths(
    shipped: Mapping[str, Any], derived: Mapping[str, Any], *, prefix: str = ""
) -> frozenset[str]:
    """Every dotted path at which two documents disagree.

    Stops at the first differing level rather than descending into it, so an
    added section reports as one path and not as one path per leaf. A delta
    nobody enumerated is a delta nobody measured.
    """
    paths: set[str] = set()
    for key in set(shipped) | set(derived):
        here = f"{prefix}{key}"
        if key not in shipped or key not in derived:
            paths.add(here)
            continue
        left, right = shipped[key], derived[key]
        if isinstance(left, Mapping) and isinstance(right, Mapping):
            paths |= delta_paths(left, right, prefix=f"{here}.")
        elif left != right:
            paths.add(here)
    return frozenset(paths)


# --------------------------------------------------------------------------
# Booting cp-05's declarations, offline
# --------------------------------------------------------------------------


class Fabric(NamedTuple):
    """A booted, populated cp-05 fabric and everything a resolver needs."""

    booted: BootedFabric
    control_plane: ControlPlaneRegistry
    root: pathlib.Path
    entities: int
    relationships: int


def _boot(root: pathlib.Path) -> Fabric:
    """Boot the derived config and populate L3 from wave 3's fixture.

    The derived document is written into ``root`` rather than beside cp-05's
    own, which is the whole of what keeps ``examples/`` read-only here: every
    derived manifest entry's path is the config's own filename, resolved
    against the config's own directory, so a config in ``tmp_path`` reads and
    writes nothing outside it.
    """
    root.mkdir(parents=True, exist_ok=True)
    config_file = root / CONFIG.name
    config_file.write_text(
        yaml.safe_dump(derived_config(), sort_keys=False), encoding="utf-8"
    )
    control_plane = ControlPlaneRegistry()
    booted = load_config_and_boot(
        config_file,
        registry=control_plane,
        connection={"database_path": str(root / f"cp05_{uuid.uuid4().hex[:12]}.sqlite3")},
    )
    source = FileRecordAcquisitionSource(
        path=FIXTURE, source=SOURCE, clock=lambda: ASKED_AT
    )

    async def collect() -> list[SignalEnvelope]:
        return [
            envelope async for envelope in source.envelopes(tenant_id=booted.tenant_id)
        ]

    drive_into_l2(booted, asyncio.run(collect()))
    entities, relationships = counts_off_l3(booted)
    return Fabric(
        booted=booted,
        control_plane=control_plane,
        root=root,
        entities=entities,
        relationships=relationships,
    )


@pytest.fixture
def fabric(tmp_path: pathlib.Path) -> Iterator[Fabric]:
    """cp-05's declarations, booted and populated, with no estate reachable."""
    built = _boot(tmp_path / "fabric")
    try:
        yield built
    finally:
        built.booted.handle.close()


# --------------------------------------------------------------------------
# The extension points a deployment supplies, and the one measurement device
# --------------------------------------------------------------------------


class RollupPlan:
    """This harness's Π — the family L4 admitted, and the figures under test.

    Deliberately thin. cp-05's own :mod:`projection` applies a materiality
    threshold over assembled exposures, which needs the Postgres amounts
    estate; this harness has no estate and needs none, because what is being
    measured is **which entities reach L5 at all**.
    """

    def __init__(
        self, *, plan_id: str, required: Sequence[str], measures: Mapping[str, int]
    ) -> None:
        self._plan_id = plan_id
        self._required = tuple(required)
        self._measures = dict(measures)

    @property
    def plan_id(self) -> str:
        return self._plan_id

    def required_operators(self) -> tuple[str, ...]:
        """The declared set, HANDED IN — never a second copy authored here.

        cp-05 is a one-document deployment for operator requirements (Dave,
        2026-09-08), and :class:`~ccf.products.resolver.ProjectionPlanFactoryProtocol`
        passes ``required`` for exactly that reason.
        """
        return self._required

    def invoke(
        self,
        *,
        view: Any,
        operator_outputs: Mapping[str, Any],
        perspective: Perspective,
        temporal_boundary: datetime,
    ) -> ProjectionOutput:
        entities = view.entities
        materialized = (
            list(entities.values()) if isinstance(entities, dict) else list(entities)
        )
        return ProjectionOutput(
            plan_id=self._plan_id,
            payload={FAMILY_SIZE_MEMBER: len(materialized), **self._measures},
        )


def declared_debt_scorer(booted: BootedFabric) -> AssemblyDebtScorer:
    """cp-05's own ``λ_c`` and ``D_c`` bands, over the classes L3 actually holds.

    **The override path, and why it is taken.** The reference scorer keys
    ``λ_c`` by the **entity class** of each row it scores and surfaces
    :class:`~ccf.halflife.decay.MissingHalfLife` rather than defaulting when a
    class has none (``INV-CH7-58``, and the refusal is right). cp-05's table is
    keyed by domain observation type — ``ownership_edges``,
    ``outstanding_balances`` and three more — because that is the vocabulary
    the whitepaper §7.7 uses and the vocabulary cp-05's own
    ``assess_context_debt`` scores against. The two vocabularies do not meet,
    so the reference cannot be *selected* and the deployment supplies its own.

    The mapping is stated rather than hidden: the two entity classes cp-05's
    resolution spec mints — ``exposure_anchor`` and ``exposure_member`` — are
    the ownership-graph nodes acquired from the FIBO ledger, so they take
    cp-05's own ``ownership_edges`` entry. **Every number here is cp-05's**;
    the only harness decision is which of its declared entries governs which
    class, which is a deployment's decision to make.

    ``C`` and ``S`` are declared at ``1`` for the reason
    :class:`~ccf.halflife.assessment.DebtFactors` gives: the SDK has no
    measurement for either, and this harness is measuring the resolver's path
    rather than cp-05's confidence in an estate it cannot reach offline.
    """
    table = booted.artifacts[HALF_LIFE_KEY]
    assert isinstance(table, HalfLifeTable)
    entries = dict(table.entries)
    entries["exposure_anchor"] = entries["ownership_edges"]
    entries["exposure_member"] = entries["ownership_edges"]
    return AssemblyDebtScorer(
        table=table.model_copy(update={"entries": entries}),
        profile=booted.artifacts[DEBT_PROFILE_KEY],  # type: ignore[arg-type]
        completeness=DeclaredFactor(value=Decimal("1")),
        semantic_consistency=DeclaredFactor(value=Decimal("1")),
    )


def reconciliation_gate(
    *, candidate: ContextProductContract, evidence: Any
) -> str | None:
    """cp-05's fourth validation gate, as a ``ProductGateProtocol`` callable.

    The predicate reproduces
    ``examples/cp-05-credit-exposure-rollup/assembler.py::reconciliation_guard``
    — *"Gross must be >= guarantee-adjusted, per group. Adjusted exposure
    exceeding gross is arithmetically impossible; if it happens, step 5.2
    removed the same exposure twice. … The other three gates catch a broken
    pipeline. This one catches a PLAUSIBLE WRONG ANSWER."* cp-05 is **read**
    and not imported; the predicate is rewritten here.

    Returns a violation string or ``None`` and nothing else, because the gate's
    identity is the Control Plane's half — the resolver stamps
    ``declared_product_gate`` onto the refusal so a gate cannot claim to be a
    different gate than the one its class declared.
    """
    gross = int(candidate.payload["gross_committed"])
    adjusted = int(candidate.payload["adjusted_committed"])
    if adjusted > gross:
        return (
            f"adjusted committed {adjusted} exceeds gross {gross};"
            " the dedup logic double-subtracted"
        )
    return None


def _resolver(
    fabric: Fabric,
    *,
    measures: Mapping[str, int],
) -> GovernedResolver:
    """cp-05's declarations through ``build_governed_resolver``.

    Supplied with the ordinary extension points and **nothing else**: no
    ``replay_record_class``, no ``query_pin_class`` and no ``artifact_store``,
    so wave 1's declared binding is what supplies all three.
    """
    def plan_factory(*, required: tuple[str, ...], request: ProductRequest) -> Any:
        return RollupPlan(
            plan_id=f"cp-05.exposure-rollup/{request.subject}",
            required=required,
            measures=measures,
        )

    ttl = _load(TTL_ARTIFACT)[DECLARATION]
    return build_governed_resolver(
        fabric=fabric.booted,
        control_plane=fabric.control_plane,
        product_class_key=PRODUCT_CLASS_KEY,
        request_contract_key=REQUEST_CONTRACT_KEY,
        operator_parameter_keys=OPERATOR_PARAMETER_KEYS,
        policy_bundle_key=POLICY_BUNDLE_KEY,
        plan_factory=plan_factory,
        debt_scorer=declared_debt_scorer(fabric.booted),
        product_gate=reconciliation_gate,
        artifact_store_root=fabric.root,
        max_ttl_seconds=int(ttl["max_ttl_seconds"]),
        product_ttl_seconds=int(ttl["declared_ttl_seconds"]),
    )


def _ask(fabric: Fabric, resolver: GovernedResolver, *, subject: str | None = None) -> Any:
    """cp-05's declared question, put to the resolver."""
    config = shipped_config()
    question = _load(QUESTION_ARTIFACT)[DECLARATION]
    perspective_artifact = fabric.booted.artifacts[PERSPECTIVE_KEY]
    parameters: dict[str, Any] = {
        name: value
        for name, value in question["parameters"].items()
        if name != "intent"
    }
    # Text in the document, `Decimal` on the wire — cp-05's own interpreter
    # makes the same conversion, for the reason its config records: a float
    # materiality would make the content address platform-dependent.
    parameters["materiality"] = Decimal(str(parameters["materiality"]))
    request = ProductRequest(
        schema_name=config["product_class"]["schema_name"],
        schema_version=config["product_class"]["schema_version"],
        subject=subject or question["subject"],
        intent=question["parameters"]["intent"],
        freshness=question["freshness"],
        asked_at=datetime.fromisoformat(question["asked_at"]),
        parameters=parameters,
    )
    return resolver(
        tenant=fabric.booted.tenant_id,
        product_class=config["product_class"]["schema_name"],
        version=config["product_class"]["schema_version"],
        perspective=Perspective(
            principal_id=perspective_artifact.principal_id,  # type: ignore[attr-defined]
            role=perspective_artifact.role,  # type: ignore[attr-defined]
        ),
        request=request,
    )


# ---------------------------------------------------------------------------
# 1 — the config delta. `24.10-F-12`, measured rather than described.
# ---------------------------------------------------------------------------


def test_the_shipped_config_declares_what_the_canonical_path_requires() -> None:
    """The transitional delta test, replaced because its premise EXPIRED.

    It began as ``test_the_config_delta_is_two_declarative_additions`` and
    measured what adopting the canonical path COST cp-05: a ``replay:``
    binding, a ``declared_product_gate``, and — while `24.10-F-12` stood — a
    reshaped ``unsupported_arguments``. Dave, ruling `D-IMPL-299`: *"The
    transitional 'two declarative additions' test has fulfilled its purpose.
    Once those declarations are canonical, update the test so it verifies the
    shipped configuration itself contains the required declarations. Don't
    preserve an overlay merely so the old delta remains two."*

    So this asserts the END STATE rather than a cost, and the delta assertion
    survives inverted: it is now **empty**, which is the strongest form of the
    original claim. A harness that still had to add anything would fail here.

    The two additions are read from cp-05's own document rather than compared
    against constants this module authors, so the test cannot pass by agreeing
    with itself.
    """
    shipped = shipped_config()

    replay = shipped.get(DELTA_REPLAY)
    assert isinstance(replay, Mapping), (
        "cp-05 does not declare a `replay:` section; the canonical path has no"
        " binding to consume and `D-IMPL-299`'s adoption has been undone"
    )
    assert replay["record_class"], "the replay binding names no record class"
    assert replay["query_pin_class"], "the replay binding names no query pin class"
    assert replay["store_dirname"], "the replay binding names no store"

    gate = shipped["product_class"].get("declared_product_gate")
    assert isinstance(gate, Mapping), (
        "cp-05's class declares no product gate, so `R-11`'s seam has nothing"
        " to execute and a refusal could not name the gate that produced it"
    )
    assert gate["gate_id"] and gate["gate_version"], (
        "half an identity cannot answer WHICH gate at WHICH version in a"
        " replay record"
    )

    # And the delta, inverted: the harness adds NOTHING.
    assert delta_paths(shipped, derived_config()) == frozenset(), (
        "the harness still modifies cp-05's document before driving the"
        " canonical path, so something the example needs is still an overlay"
    )


def test_the_deployment_passes_the_authored_reason_through_unchanged() -> None:
    """`24.10-F-12` step 4 — the success signal, and it needs its own guard.

    Dave: *"That last deletion is the success signal. If the YAML gains a
    reason but Python continues recreating one, F-12 is not really finished."*
    Correcting the declaration while `deployment.py` kept minting
    ``"not supported at this tier"`` would leave cp-05 technically adopting the
    canonical schema **while still discarding the author's governed
    explanation at runtime** — which is why the deletion is mandatory rather
    than tidy (`D-IMPL-288` (2), `D-IMPL-289`).

    Two halves, because neither alone says it:

    * the SDK's own reader carries the authored sentence verbatim, so the
      declaration reaches a typed contract intact;
    * cp-05's interpreter contains no expression that manufactures a reason.
      Read as source and never imported, which is this harness's standing rule
      for cp-05.
    """
    authored = shipped_config()["request_contract"]["unsupported_arguments"]
    contract = ProductRequestContract.from_declared(
        _declared_request_contract(shipped_config())
    )

    assert contract.unsupported_arguments == authored, (
        "the SDK's typed reader did not carry cp-05's authored reasons"
        " verbatim"
    )

    interpreter = (CP_05 / "deployment.py").read_text(encoding="utf-8")
    minting = [
        line
        for line in interpreter.splitlines()
        if "unsupported_arguments" in line and "for name in" in line
    ]
    assert not minting, (
        "cp-05's interpreter manufactures its own unsupported-argument"
        f" reasons again: {minting}. The declaration authors them; this code"
        " passes them through (D-IMPL-288 (2) step 4)"
    )


def _declared_request_contract(config: Mapping[str, Any]) -> Any:
    """cp-05's ``request_contract`` section as the envelope a manifest resolves.

    Built here rather than read off a booted fabric so the refusal can be shown
    without first paying for a boot — and so the premise above is about the
    *document*, which is what cp-05 authored, rather than about a parse of it.
    """
    from ccf.controlplane.artifacts import DeclaredArtifact

    section = dict(config["request_contract"])
    return DeclaredArtifact(
        semver=str(section.pop("semver", "1.0.0")),
        class_id=str(section.pop("class_id")),
        declaration={
            name: value
            for name, value in section.items()
            if name not in {"role", "registration"}
        },
    )


# ---------------------------------------------------------------------------
# 2 — the declarations boot and populate offline. The non-vacuity control.
# ---------------------------------------------------------------------------


def test_cp05s_declarations_boot_and_populate_offline(fabric: Fabric) -> None:
    """cp-05's own Control Plane document boots, and L3 holds its family.

    **This is the control that makes every other result in this module
    attributable.** A stop-rule test that ran against an empty graph would
    report a family of 0 and mean nothing by it, so the graph the resolver
    reads is counted first — off L3 at the instant the question names, never
    off the acquisition walk.

    No estate is reachable and no environment variable is read: population is
    ``24.10-03``'s captured fixture through
    :class:`~ccf.signal.acquisition.FileRecordAcquisitionSource` and that
    plan's own ``drive_into_l2``.
    """
    assert fabric.booted.tenant_id == shipped_config()["tenant_id"]
    assert set(OPERATOR_PARAMETER_KEYS) <= set(fabric.booted.artifacts)
    assert (fabric.entities, fabric.relationships) == (
        DECLARED_FAMILY_SIZE,
        DECLARED_RELATIONSHIP_CLAIMS,
    ), "the fixture no longer reproduces wave 3's measured 77/100"


# ---------------------------------------------------------------------------
# 3 — the stop rule itself. `24.10-F-11`, measured UNBRIDGED.
# ---------------------------------------------------------------------------


def test_the_canonical_path_serves_cp05s_declared_family(fabric: Fabric) -> None:
    """Adoption requires the canonical path to answer cp-05's own question.

    Run **unbridged**: cp-05's declarations exactly as they ship, through
    :func:`~ccf.products.resolver.build_governed_resolver` supplied with the
    ordinary extension points and no replay arguments at all, so wave 1's
    declared binding is what files the record and wave 2's seam is what carries
    the gate.

    The resolver does not raise and does not refuse. It **serves**, and what it
    serves is wrong: the same graph that answers 77 to cp-05's own spine
    answers 0 here, and the product carries a content address and a replay
    record saying so.
    """
    resolver = _resolver(
        fabric,
        measures={
            "gross_committed": CP05_GROSS_COMMITTED,
            "adjusted_committed": CP05_ADJUSTED_COMMITTED,
        },
    )
    served = _ask(fabric, resolver)

    # The premises, asserted before the finding so the xfail is attributable.
    assert fabric.entities == DECLARED_FAMILY_SIZE, (
        "the graph the resolver read is not the one wave 3 measured"
    )
    assert getattr(served, "product", None) is not None, (
        "the canonical path did not serve a product at all; this finding is"
        " about a WRONG answer, so a refusal here means the premise moved"
    )
    assert (fabric.root / _load(REPLAY_ARTIFACT)[DECLARATION]["store_dirname"]).is_dir(), (
        "wave 1's declared replay binding did not supply the store"
    )

    assert served.product.payload[FAMILY_SIZE_MEMBER] == DECLARED_FAMILY_SIZE, (
        "the canonical path served a family of"
        f" {served.product.payload[FAMILY_SIZE_MEMBER]} over an L3 holding"
        f" {fabric.entities} entities: cp-05's declared policy envelope is"
        " empty by design and is bound per request, and the resolver has"
        " nowhere for that binding to go"
    )

    # `24.11-04` — UN-QUARANTINED, and the assertion above is the one it
    # carried. It held `xfail(strict=True)` for `24.10-F-11` and XPASSed the
    # moment cp-05 could DECLARE its per-request envelope and the resolver
    # could honor it. Nothing here was weakened to make it pass: the same
    # comparison against the same measured family size now reads 77 where it
    # read 0, because the declaration changed and the SDK learned to read it.


# ---------------------------------------------------------------------------
# 4 — `R-11`'s seam, live on cp-05's path, with its positive control.
# ---------------------------------------------------------------------------


def test_the_gate_seam_is_live_on_cp05s_path(fabric: Fabric) -> None:
    """cp-05's fourth validation gate, running as a governed refusal.

    Both directions, because a gate observed only in its firing state is a gate
    that might be refusing everything:

    * over the double-subtracted gross cp-05's guard exists to catch, the
      resolver yields a ``product-invariant-refusal`` naming the gate id the
      class declared — not an exception out of a deployment's spine;
    * over cp-05's shipped figures it does not fire, and a product is served.

    Ran with a bridge in force until ``24.11-04``, so the gate was held against
    a candidate assembled over a real family rather than over the empty one
    ``24.10-F-11`` produced. The bridge is gone and nothing replaced it: cp-05
    declares the binding and the resolver honors it, so this now runs on the
    ordinary governed path like every other test here.
    """
    refusing = _resolver(
        fabric,
        measures={
            "gross_committed": DOUBLE_SUBTRACTED_GROSS,
            "adjusted_committed": CP05_ADJUSTED_COMMITTED,
        },
    )
    refused = _ask(fabric, refusing)

    assert isinstance(refused, RefusalEnvelope), (
        "a rollup whose adjusted committed exceeds its gross was not refused"
    )
    assert refused.kind == PRODUCT_INVARIANT_REFUSAL
    assert refused.reason == GATE_ID, (
        "the disclosed shell does not name the gate the Control Plane"
        " declared, so an auditor cannot say which gate produced this refusal"
        " (D-IMPL-282 R-11: 'Replay should be able to say which gate ran and,"
        " if it refused, which gate produced the refusal')"
    )

    # `D-14`, the internal-truth half — asserted against the PERSISTED bytes
    # and never against the value the resolver returned in memory. The shell
    # above is what disclosure permitted (`minimal`, so the arithmetic is
    # generalized and the lane is undisclosed); the record is what governance
    # preserved. Determination → Authority → Disclosure → Delivery, observed
    # rather than described (`D-IMPL-254`).
    recorded = _recorded_refusal(fabric, refused)
    assert recorded["kind"] == PRODUCT_INVARIANT_REFUSAL
    assert str(DOUBLE_SUBTRACTED_GROSS) in recorded["detail"]
    assert str(CP05_ADJUSTED_COMMITTED) in recorded["detail"]
    assert GATE_VERSION in recorded["fields"]["gate_version"]

    # The positive control, and it is not optional.
    admitting = _resolver(
        fabric,
        measures={
            "gross_committed": CP05_GROSS_COMMITTED,
            "adjusted_committed": CP05_ADJUSTED_COMMITTED,
        },
    )
    served = _ask(fabric, admitting)

    assert not isinstance(served, RefusalEnvelope), (
        "cp-05's own shipped figures were refused by cp-05's own invariant;"
        " a gate that refuses its deployment's published answer is refusing"
        " everything"
    )
    assert served.product.payload[FAMILY_SIZE_MEMBER] == DECLARED_FAMILY_SIZE, (
        "the bridged run did not reach cp-05's declared family, so this test"
        " is measuring something other than the gate"
    )
    assert isinstance(served.product.debt, DebtAssessment)


def _recorded_refusal(fabric: Fabric, envelope: RefusalEnvelope) -> dict[str, Any]:
    """The refusal as it was PERSISTED, read back out of the declared store.

    Read off the store wave 1's declared binding supplied — never off an object
    the test kept a reference to — because the record is what an examiner with
    the decision and nothing else would hold.
    """
    from ccf.artifacts.file_store import FileArtifactStore

    reference = envelope.replay_reference
    assert reference, "a governed refusal was released with no replay reference"
    store = FileArtifactStore(
        root=fabric.root / _load(REPLAY_ARTIFACT)[DECLARATION]["store_dirname"]
    )
    document = json.loads(store.get(content_address=str(reference).split("@")[-1]))
    recorded = json.loads(document["content_generation_path"]["assembly_refusal"])
    assert isinstance(recorded, dict)
    return recorded
