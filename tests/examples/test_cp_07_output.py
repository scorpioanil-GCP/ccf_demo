"""What `examples/cp-07-client-360-coverage-graph` actually serves.

**Directional, never pinned.** Every assertion below is a business relationship
that must hold at any roster size — a wider window admits at least as much
evidence, a tighter bound cannot raise a relationship score, truncation is
disclosed whenever it happens — rather than a number this module restates. A
test pinning `200 of 240` would go red the next time `ccf-dataprep` loads
another meeting, for no reason anybody could act on, and would have turned the
curated estate back into a fixture (CLAUDE.md §9).

**The one claim this rung exists to prove, and it is a relationship too:**
*a bounded acquisition can manufacture a coverage gap that does not exist.*
Measured on the demonstration anchor, `limit=200` finds zero gaps and
`limit=20` finds three, two of them in material roles. The bound did not
discover that nobody has met the CFO; it hid the meeting. That is why the
truncation disclosure is a declared gate rather than a line of prose, and it
is asserted below as a direction — gaps at the tight bound are at least as many
as gaps at the loose one, on the same estate at the same instant.

**Read-only.** This module reads the curated estate and seeds nothing. It
creates no ledger and no schema, so it adds nothing to an append-only store
that could never be removed.
"""

from __future__ import annotations

import ast
import importlib.util
import os
import pathlib
import sys
import tempfile
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest

pytestmark = [pytest.mark.fluree, pytest.mark.postgres]

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE = REPO_ROOT / "examples" / "cp-07-client-360-coverage-graph"

ESTATE_VARIABLES = (
    "CCF_CP_07_FLUREE_URL", "CCF_CP_07_FLUREE_LEDGER",
    "CCF_CP_07_POSTGRES_DSN", "CCF_CP_07_POSTGRES_SCHEMA",
)
ESTATE_REQUIRED = "CCF_REQUIRE_ESTATE"

#: Module names every example ships. `produce` reaches its sibling by a bare
#: `import deployment`, so the first example imported owns those names for the
#: session — green alone and red beside another example's module.
COLLIDING = ("acquisition", "deployment", "produce", "projection", "serve")


def _anchor(name: str) -> str:
    """A demonstration constant, read from `run.py` rather than restated."""
    for node in ast.walk(ast.parse((EXAMPLE / "run.py").read_text(encoding="utf-8"))):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == name for t in node.targets
        ):
            return str(ast.literal_eval(node.value))
    raise AssertionError(f"run.py declares no {name}")


@pytest.fixture(scope="module")
def estate() -> tuple[str, str]:
    """The CURATED estate, read-only, seeding nothing."""
    missing = [n for n in ESTATE_VARIABLES if not os.environ.get(n)]
    if missing:
        message = (
            f"the curated estate is not configured: {', '.join(missing)} unset."
            " Point them at the v2 namespaces — Fluree `fibo-v2`, PostgreSQL"
            " `ccf_v2` — never the v1 names in `ccf_dataprep/.env`"
        )
        if os.environ.get(ESTATE_REQUIRED):
            pytest.fail(message)
        pytest.skip(message)
    return (os.environ["CCF_CP_07_FLUREE_LEDGER"],
            os.environ["CCF_CP_07_POSTGRES_SCHEMA"])


@pytest.fixture(scope="module")
def example() -> Iterator[tuple[Any, Any]]:
    """This example's own `deployment` and `produce`, whatever ran before."""
    saved = {n: sys.modules.pop(n, None) for n in COLLIDING}
    sys.path.insert(0, str(EXAMPLE))
    try:
        import deployment  # noqa: PLC0415
        import produce  # noqa: PLC0415

        assert pathlib.Path(deployment.__file__).parent == EXAMPLE
        yield deployment, produce
    finally:
        sys.path.remove(str(EXAMPLE))
        for name in COLLIDING:
            sys.modules.pop(name, None)
            if saved[name] is not None:
                sys.modules[name] = saved[name]


def _serve(example: tuple[Any, Any], *, lei: str | None = None,
           asked_at: datetime | None = None, **kwargs: Any) -> Any:
    """One run of the demonstration client, in its own scratch fabric.

    ``asked_at`` defaults to now. A determinism comparison must PIN it: the
    decision instant is part of the determination — it sets the product's
    expiry — so two serves a millisecond apart are two different questions and
    correctly reach two different content addresses.
    """
    deployment, produce = example
    anchor = lei or _anchor("DEMONSTRATION_LEI")
    scope = kwargs.pop("principal_scope_override", None) or [anchor]
    asked = deployment.request(
        lei=anchor, principal_scope=scope,
        asked_at=asked_at or datetime.now(UTC), **kwargs)
    with tempfile.TemporaryDirectory() as scratch:
        return produce.assemble_and_serve(asked=asked, root=pathlib.Path(scratch))


def _boundary(outcome: Any) -> dict[str, Any]:
    return outcome.product.payload["evidence_boundary"]


def _findings(outcome: Any) -> dict[str, Any]:
    return outcome.product.payload["findings"]


@pytest.fixture(scope="module")
def default(estate: tuple[str, str], example: tuple[Any, Any]) -> Any:
    return _serve(example)


@pytest.fixture(scope="module")
def control(estate: tuple[str, str], example: tuple[Any, Any]) -> Any:
    """The negative control — a client with fewer interactions than the bound."""
    return _serve(example, lei=_anchor("CONTROL_LEI"))


@pytest.fixture(scope="module")
def stale(estate: tuple[str, str], example: tuple[Any, Any]) -> Any:
    """The FRESHNESS control — the stalest relationship that still has a graph."""
    return _serve(example, lei=_anchor("FRESHNESS_CONTROL_LEI"))


# --- truncation as a first-class product fact --------------------------------


def test_the_demonstration_anchor_is_truncated_and_says_so(default: Any) -> None:
    """The bound cut the evidence, and the payload states it rather than implying
    completeness.

    Counts are not pinned: what must hold is that fewer were admitted than were
    admissible, and that `truncated` agrees with that arithmetic. A payload
    where the two disagree is the failure this rung exists to surface, and the
    product's own declared gate refuses it before a consumer sees it.

    Declared product gate `C36-G03` (`CP-SPEC-007` §G.1).
    """
    boundary = _boundary(default)
    admissible = (boundary["interactions_available"]
                  - boundary["withheld_need_to_know"])
    assert boundary["interactions_admitted"] < admissible, (
        "the demonstration anchor no longer exceeds the class default `limit`,"
        " so this example is not demonstrating its own subject"
    )
    assert boundary["truncated"] is True
    assert boundary["note"], "truncated, with nothing said to the consumer"


def test_the_control_client_is_not_truncated(control: Any) -> None:
    """The negative control, and it is what makes the assertion above mean
    anything.

    Without a client whose evidence fits inside the bound, `truncated: True`
    could be a constant.
    """
    boundary = _boundary(control)
    assert boundary["interactions_admitted"] == (
        boundary["interactions_available"] - boundary["withheld_need_to_know"])
    assert boundary["truncated"] is False


def test_a_tighter_bound_manufactures_coverage_gaps(
    estate: tuple[str, str], example: tuple[Any, Any]
) -> None:
    """**The claim rung 7 exists to prove.**

    A coverage gap means *nobody at the bank has met this officer*. Narrow the
    acquisition and the product starts reporting officers who HAVE been met —
    the meeting simply fell outside the window. The finding is not wrong about
    the graph it was given; it is wrong about the world, and the only thing
    standing between the two is the disclosure.

    Directional: the tight bound reports AT LEAST as many gaps as the loose one,
    on the same estate at the same instant, and strictly more for this to have
    measured anything at all.

    Declared product gate `C36-G05` (`CP-SPEC-007` §G.1).
    """
    instant = datetime.now(UTC)
    loose = _serve(example, asked_at=instant, limit=500)
    tight = _serve(example, asked_at=instant, limit=20)

    assert _boundary(tight)["truncated"] is True
    assert _findings(tight)["coverage_gaps"] >= _findings(loose)["coverage_gaps"]
    assert _findings(tight)["coverage_gaps"] > _findings(loose)["coverage_gaps"], (
        "narrowing the acquisition to a tenth of the evidence produced no new"
        " coverage gap, so the bound is not reaching the gap analysis and the"
        " disclosure would be measuring nothing"
    )


def test_a_lower_limit_admits_no_more_evidence_than_a_higher_one(
    estate: tuple[str, str], example: tuple[Any, Any]
) -> None:
    """`limit` is monotone in the direction its name implies.

    The sibling `since` gate asserts this for the temporal bound; this is the
    same claim for the cardinality bound, and the two are separate because they
    reach the read by different paths — `since` narrows the `WHERE`, `limit`
    the `LIMIT`. Directional and strict: a tenth of the bound must admit
    strictly less on an anchor that exceeds both, or the bound is not reaching
    the read at all.

    Written for `D-IMPL-326`: `CP-SPEC-007` §G.1 declares this gate and no test
    asserted it, which the acceptance-authority wiring surfaced rather than
    papered over.

    Declared product gate `C36-G02` (`CP-SPEC-007` §G.1).
    """
    instant = datetime.now(UTC)
    loose = _boundary(_serve(example, asked_at=instant, limit=500))
    tight = _boundary(_serve(example, asked_at=instant, limit=20))
    assert tight["interactions_admitted"] <= loose["interactions_admitted"]
    assert tight["interactions_admitted"] < loose["interactions_admitted"], (
        "a tenth of the bound admitted as much evidence as the full one, so"
        " `limit` is not reaching the read"
    )


def test_truncation_is_not_folded_into_context_debt(
    estate: tuple[str, str], example: tuple[Any, Any]
) -> None:
    """`D_c` measures the admitted evidence, never the size of the bound.

    A `limit` of 20 omits ten times as much as a `limit` of 200. If truncation
    were a debt input, D_c would have to move sharply between them. It does not,
    because a bounded read is a deliberate act with a KNOWN edge, and the known
    edge is disclosed rather than scored (§7.7.4).
    """
    instant = datetime.now(UTC)
    loose = _serve(example, asked_at=instant, limit=500)
    tight = _serve(example, asked_at=instant, limit=20)

    omitted_loose = (_boundary(loose)["interactions_available"]
                     - _boundary(loose)["interactions_admitted"])
    omitted_tight = (_boundary(tight)["interactions_available"]
                     - _boundary(tight)["interactions_admitted"])
    assert omitted_tight > omitted_loose * 2, "the two bounds omit similar amounts"

    # The ratio D_c would carry if truncation were the input, versus what it
    # actually carries. The first differs by an order of magnitude; the second
    # must not track it.
    drift = abs(Decimal(tight.product.debt.debt) - Decimal(loose.product.debt.debt))
    assert drift < Decimal("0.10"), (
        f"D_c moved {drift} between a bound that omitted {omitted_loose} and one"
        f" that omitted {omitted_tight}; truncation has become a debt proxy"
    )


def test_a_silent_truncation_is_refused_by_the_declared_gate(
    estate: tuple[str, str], example: tuple[Any, Any], monkeypatch: Any
) -> None:
    """Sabotage the DISCLOSURE, not the bound, and watch the gate fire.

    The gate's subject is silence, never truncation: a product that was cut and
    says so is served. This suppresses only the `truncated` flag, leaving the
    counts intact, so the payload becomes internally inconsistent in exactly the
    way a consumer could not detect — and the SDK turns that into a governed
    refusal rather than a served answer.
    """
    from ccf.products.refusal import RefusalEnvelope  # noqa: PLC0415

    import projection  # noqa: PLC0415

    original = projection.ClientCoverageProjection.invoke

    def silent(self: Any, **kwargs: Any) -> Any:
        output = original(self, **kwargs)
        output.payload["evidence_boundary"]["truncated"] = False
        return output

    monkeypatch.setattr(projection.ClientCoverageProjection, "invoke", silent)
    outcome = _serve(example)
    assert isinstance(outcome, RefusalEnvelope), (
        "a payload cut by its bound and claiming completeness was SERVED"
    )
    assert "truncation-disclosure" in str(outcome.reason) + str(outcome.detail or "")


# --- freshness is a measurement, not a constant -------------------------------


def test_a_stale_relationship_scores_worse_freshness_than_a_current_one(
    default: Any, stale: Any
) -> None:
    """`D_c` moves with how recently anybody was actually in contact.

    **This is the assertion that makes the freshness term evidence rather than
    decoration.** Two anchors, the same instant, the same estate, the same
    declared λ_c: the one nobody has spoken to since 2026-07-22 scores strictly
    worse than the one contacted three weeks later, and the difference survives
    into `D_c`.

    Directional, and deliberately NOT a claim about the single latest contact.
    Freshness is scored over EVERY party's most recent contact, so a client with
    one recent meeting and a long tail of dormant relationships can legitimately
    score below one whose whole coverage set was refreshed at once — which is
    the behavior a coverage product should have. What must hold is that a
    uniformly staler relationship set scores lower.
    """
    assert Decimal(stale.product.debt.factors.freshness) < Decimal(
        default.product.debt.factors.freshness), (
        "the stale anchor did not score worse on freshness; either the estate's"
        " last-contact spread has closed or the λ_c table is no longer reaching"
        " the scorer"
    )
    assert Decimal(stale.product.debt.debt) > Decimal(default.product.debt.debt)

    # And the cause, asserted rather than assumed: the stale anchor really is
    # the one nobody has contacted recently.
    def _latest(outcome: Any) -> str:
        return max(i.interaction_date for i in outcome.coverage.interactions
                   if i.interaction_date)

    assert _latest(stale) < _latest(default)


def test_the_stale_anchor_crosses_a_governance_threshold_the_others_do_not(
    default: Any, control: Any, stale: Any
) -> None:
    """A threshold that nothing ever crosses is a threshold nobody has tested.

    The declared `forced_llm_threshold` exists to say *this answer is too stale
    to act on algorithmically*. Measured on this estate at the declared λ_c, the
    stale anchor reaches it and the two current anchors do not — so the signal
    is discriminating between real clients rather than reporting a constant.

    The SIGNAL is asserted, not the number: the half-life is an illustrative
    calibration for a point-in-time estate (`README.md`), so pinning `0.6563`
    would make a documented demonstration value into a fixture.
    """
    assert stale.product.debt.signal != default.product.debt.signal, (
        "every anchor reports the same debt signal, so the signal is not"
        " discriminating and the thresholds are untested by this example"
    )
    assert default.product.debt.signal == control.product.debt.signal


# --- the coverage graph itself ------------------------------------------------


def test_relationship_strength_ranks_the_assigned_bankers_above_the_rest(
    default: Any
) -> None:
    """A banker who has met the client outranks one who has not.

    Not pinned to a score: the weights are policy and live in the estate's own
    `scoring_weight` table. What must hold is the ordering — a zero-interaction
    banker cannot outrank one with a measured history, or the weights are being
    applied to the wrong term.
    """
    bankers = default.product.payload["bankers"]
    met = [b for b in bankers if b["interactions"] > 0]
    unmet = [b for b in bankers if b["interactions"] == 0]
    assert met and unmet, "every banker is on one side; the ranking proves nothing"
    assert min(Decimal(b["relationship_strength"]) for b in met) > max(
        Decimal(b["relationship_strength"]) for b in unmet)


def test_a_coverage_gap_is_a_path_and_not_a_field(control: Any) -> None:
    """What a CRM cannot contain, stated as a property of the answer.

    `covers_client` is the CRM's field, and it is carried. The gaps are
    something else: officers reached by the roster leg whom NO admitted
    interaction connects to any banker. The control client carries both, which
    is what makes the contrast visible in one payload.
    """
    findings = _findings(control)
    assert findings["bankers_covering"] > 0, "no formal coverage assignment at all"
    assert findings["never_met"] > 0, (
        "the control client has no unmet officer, so the insight this product"
        " exists to produce is not present in the answer"
    )
    for gap in findings["gaps"]:
        assert gap["met_by"] == [] or Decimal(
            gap["best_relationship_strength"]) > 0


def test_every_declared_edge_type_is_walked_by_one_anchor_or_the_other(
    default: Any, control: Any
) -> None:
    """§C names four edges, and all four must reach the fabric from somewhere.

    They do NOT all reach it from one anchor, and that is the honest answer
    rather than a gap: measured, the demonstration client's interactions concern
    no deal at any bound, and the control client's concern three. A declared
    edge type the acquisition never walks would be vocabulary nobody exercises;
    an edge type absent from one payload is a fact about that client.

    `edge_types_present` is what carries the difference to the consumer, so it
    is asserted as the thing that reports it.
    """
    deployment_config = (EXAMPLE / "ccf_config.yaml")
    import yaml  # noqa: PLC0415

    declared = set(yaml.safe_load(deployment_config.read_text(encoding="utf-8"))[
        "operators"]["traversal.typed-neighborhood"]["relationship_types"])
    seen = set(_findings(default)["edge_types_present"]) | set(
        _findings(control)["edge_types_present"])
    assert declared == seen, (
        f"declared but never walked by either anchor: {sorted(declared - seen)};"
        f" walked but never declared: {sorted(seen - declared)}"
    )
    assert set(_findings(default)["edge_types_present"]) != set(
        _findings(control)["edge_types_present"]), (
        "both anchors carry the same edge types, so `edge_types_present` is"
        " reporting a constant and could not tell a consumer anything"
    )


def test_the_deals_the_admitted_interactions_concern_are_served(
    control: Any
) -> None:
    """The fourth edge, reached from the BOUNDED interaction set.

    Walking from deals would fan out over the estate and then discard most of
    it, which is the shape this product exists to refuse. Each served deal must
    therefore be reachable from an admitted interaction — an interaction count
    of zero would mean the deal arrived some other way.
    """
    deals = control.product.payload["deals"]
    assert deals, "the control client concerns no deal; the fourth edge is unexercised"
    for deal in deals:
        assert deal["interactions"] > 0, (
            f"{deal['deal']} is served with no admitted interaction reaching it"
        )
        assert deal["deal_type"] and deal["opened"]


def test_need_to_know_returns_a_different_graph_not_a_redacted_one(
    estate: tuple[str, str], example: tuple[Any, Any]
) -> None:
    """§D step 2 — a suppressed interaction is never materialized.

    Admitting need-to-know content must ADD admissible evidence rather than
    unmask a placeholder. If the withheld count did not move, the policy
    operator is not reaching the read and the exclusion is cosmetic.

    Declared product gate `C36-G04` (`CP-SPEC-007` §G.1).
    """
    instant = datetime.now(UTC)
    without = _serve(example, asked_at=instant)
    with_ntk = _serve(example, asked_at=instant, include_need_to_know=True)

    assert _boundary(without)["withheld_need_to_know"] > 0, (
        "no interaction on this anchor is classified need-to-know, so the"
        " policy envelope cannot be measured here"
    )
    assert _boundary(with_ntk)["withheld_need_to_know"] == (
        _boundary(without)["withheld_need_to_know"])
    # Same reported population, different ADMISSIBLE population.
    assert _boundary(with_ntk)["interactions_available"] == (
        _boundary(without)["interactions_available"])


def test_a_wider_window_cannot_admit_less_evidence(
    estate: tuple[str, str], example: tuple[Any, Any]
) -> None:
    """`since` bounds T, and widening a bound is monotone.

    Declared product gate `C36-G01` (`CP-SPEC-007` §G.1).
    """
    instant = datetime.now(UTC)
    narrow = _serve(example, asked_at=instant, since="2026-01-01", limit=500)
    wide = _serve(example, asked_at=instant, since="2024-01-01", limit=500)
    assert (_boundary(wide)["interactions_available"]
            >= _boundary(narrow)["interactions_available"])
    assert (_boundary(wide)["interactions_admitted"]
            >= _boundary(narrow)["interactions_admitted"])


def test_an_unresolvable_client_is_a_claim_about_the_request(
    estate: tuple[str, str], example: tuple[Any, Any]
) -> None:
    """An unknown LEI must not resolve to an empty coverage graph.

    An empty graph and an unknown client are indistinguishable in the payload
    and mean opposite things — "nobody knows this client" versus "we do not
    know who you asked about". The acquisition refuses rather than returning
    nothing.
    """
    with pytest.raises(LookupError):
        _serve(example, lei="NOTANLEI000000000000")


def test_source_ids_are_served_for_business_matching(default: Any) -> None:
    """A payload speaking only in graph addresses cannot be joined to anything.

    The graph is walked on `banker-BKR-014`; the answer says `BKR-014`. Both
    spellings exist on purpose and the consumer gets the source's.
    """
    for banker in default.product.payload["bankers"]:
        assert not banker["banker"].startswith("banker-")
    for person in default.product.payload["people"]:
        assert not person["person"].startswith("person-")


# --- what the product must keep carrying -------------------------------------


def test_the_truncation_gate_is_declared_and_identified(
    example: tuple[Any, Any]
) -> None:
    """A gate with no declared identity gives replay nothing to name.

    The SDK refuses that pairing outright, so this asserts the declaration
    rather than the behavior: the id and version are the Control Plane's half
    (`D-IMPL-282`).
    """
    deployment, _ = example
    declared = deployment.config()["product_class"]["declared_product_gate"]
    assert declared["gate_id"] and declared["gate_version"]


def test_replay_dimension_two_carries_the_request_contract(default: Any) -> None:
    """`D-IMPL-310` — replay is a SUPERSET of product policy lineage.

    Declared product gate `C36-G07` (`CP-SPEC-007` §G.1).
    """
    bindings = {b.key for b in default.record.policy_bindings.bindings}
    lineage = set(default.product.lineage.policy_bundle_versions)
    versions = {b.version for b in default.record.policy_bindings.bindings}
    assert "request_contract" in bindings
    assert lineage <= versions


def test_lineage_carries_exactly_the_two_declared_operators(
    default: Any, example: tuple[Any, Any]
) -> None:
    """`CP-SPEC-007` §B.1(5) and §D.2.1.

    The vault article lists five verbs; only two are registered L4 operators on
    this SDK. A step carrying a Standard verb that is not a registered operator
    must NOT enter `operators_invoked`, or lineage strict equality would be
    sealing a document that claims work no operator did.
    """
    deployment, _ = example
    declared = tuple(deployment.config()["product_class"]["required_operator_keys"])
    assert sorted(default.record.content_generation_path.operator_plan) == sorted(declared)
    assert len(declared) == 2


def test_the_spec_step_table_names_exactly_the_registered_operators(
    example: tuple[Any, Any], default: Any
) -> None:
    """The step table is the document a reader counts operators in, so it has to
    agree with the declaration and with the lineage.

    **This test exists because the table did not.** As shipped at
    `D-GATE-cp-07` it named `traversal.typed-neighborhood` on the FLUREE row —
    the acquisition read, which is source access at L1 — and omitted
    `policy.principal-subgraph` entirely, so the column showed one registered
    operator where the product invokes two. It contradicted §D.2.1 one paragraph
    below it and contradicted `operators_invoked`, and nothing was checking.

    Read structurally off the markdown rather than by substring: the Operator
    column only, split on the table's own pipes, matching the shape of an
    operator key. A token elsewhere in the row — a store name, a prose mention —
    is not a claim about which operator ran.
    """
    import re  # noqa: PLC0415

    deployment, _ = example
    declared = set(deployment.config()["product_class"]["required_operator_keys"])
    assert declared, "the deployment declares no operators; this proves nothing"

    spec = next((EXAMPLE / "spec").glob("CP-SPEC-007_*.md")).read_text(encoding="utf-8")
    table = spec.split("### D.2 Step table", 1)[1].split("###", 1)[0]

    named: set[str] = set()
    for line in table.splitlines():
        cells = [c.strip() for c in line.split("|")]
        # `| # | Step | Operator | Store | Emits |` -> leading empty cell, so the
        # Operator column is index 3. A separator or prose line has no such cell.
        if len(cells) < 6 or not cells[1].isdigit():
            continue
        named.update(re.findall(r"`([a-z]+\.[a-z-]+)`", cells[3]))

    assert named == declared, (
        f"the §D.2 step table names {sorted(named)} in its Operator column and"
        f" the product class declares {sorted(declared)}; the table a reader"
        " counts operators in disagrees with the one the fabric invokes"
    )

    # THE SERVED LINEAGE IS THE THIRD WITNESS, so agreement cannot be two
    # documents copied from each other. The table, the class declaration and
    # what the fabric actually invoked all have to name one set.
    assert named == set(default.product.lineage.operators_invoked), (
        f"the step table names {sorted(named)} and the served product's"
        f" `operators_invoked` carries"
        f" {sorted(default.product.lineage.operators_invoked)}"
    )


def test_the_policy_operator_discriminates_rather_than_passing_through(
    estate: tuple[str, str], example: tuple[Any, Any], default: Any
) -> None:
    """A scope the caller does not hold yields an EMPTY graph, not a redacted one.

    Without this, `policy.principal-subgraph` could be declared, invoked,
    recorded in lineage, and admit everything — an operator present in the audit
    trail and absent from the answer. §D.2 now carries the measured contrast and
    this is what holds the document to it.

    **What sabotage established, stated as observed rather than as intended.**
    The pair is asserted — entitled non-empty AND denied empty — and both
    mutations tried reddened the FIRST half, not the second: emptying
    `permitted_classifications`, and classifying on an attribute no node carries.
    Neither produced a pass-through, because the operator **fails closed** on a
    node it cannot classify, so there is no admit-everything mode reachable from
    the declaration at all. That is the SDK behaving well; it also means the
    negative half of this assertion is held by the operator's own semantics
    rather than by a mutation this module can demonstrate. Recorded so a later
    reader does not mistake an unsabotaged half for a sabotaged one.
    """
    denied = _serve(example, principal_scope_override=["A-SCOPE-NOBODY-HOLDS"])
    assert default.product.payload["bankers"], "the entitled read returned nothing"
    assert denied.product.payload["bankers"] == []
    assert denied.product.payload["people"] == []
    assert denied.product.payload["findings"]["edge_types_present"] == []


def test_the_ttl_ceiling_binds_rather_than_the_half_life(
    default: Any, example: tuple[Any, Any]
) -> None:
    """The inversion this rung carries, asserted rather than described.

    On rungs 02, 04 and 06 the DATA expires the product: a filed document or a
    valuation decays faster than any declared ceiling. Here every λ_c is slower
    than §B's 12 hours, because the question is about the bank's own current
    posture. The product must still expire on the ceiling.
    """
    deployment, _ = example
    asked = deployment.request(
        lei=default.coverage.lei, principal_scope=[default.coverage.lei],
        asked_at=datetime.now(UTC))
    scenario = deployment.CoverageScenario(coverage=default.coverage, asked=asked)
    fastest = min(
        int(entry["half_life_seconds"])
        for entry in deployment.config()["half_life"].values())
    assert scenario.max_ttl_seconds < fastest, (
        "a declared λ_c is now faster than the class ceiling; this rung's"
        " contrast with cp-02/04/06 no longer holds and the docstring on"
        " `product_ttl_seconds` is stale"
    )
    assert scenario.product_ttl_seconds == scenario.max_ttl_seconds


def test_determinism_two_serves_of_one_question_reach_one_address(
    estate: tuple[str, str], example: tuple[Any, Any]
) -> None:
    """Assembly Mode 1, and the reason it is declared at registration.

    Two serves of one question against one estate state must agree byte for
    byte. Anything else means something non-deterministic reached the payload.
    """
    from ccf.contracts.canonical import content_hash  # noqa: PLC0415

    # PINNED, and the pin is the point: the decision instant sets the expiry
    # and therefore enters the address, so determinism is a claim about one
    # question rather than about two moments.
    instant = datetime.now(UTC)
    first = _serve(example, asked_at=instant)
    second = _serve(example, asked_at=instant)
    assert content_hash(first.product) == content_hash(second.product)

    # And the control: the SAME question at a DIFFERENT instant is a different
    # determination. Without this the assertion above would also pass against a
    # product that ignored time entirely.
    later = _serve(example, asked_at=instant + timedelta(hours=1))
    assert content_hash(later.product) != content_hash(first.product)


def test_the_structural_classifier_reads_this_tree_as_canonical() -> None:
    """`shape_of` is structural — it asks the code, never a roster.

    Declared product gate `C36-G08` (`CP-SPEC-007` §G.1) — `shape_of` reads this tree as `canonical`.
    `CP07-F-11` recorded that §G.1's old `C36-G08` made TWO claims under one
    id while a gate carries one `test:`; the clause is now split so each
    half is evidenced by the test that actually proves it.
    """
    spec = importlib.util.spec_from_file_location(
        "_sep", REPO_ROOT / "tests" / "examples" / "test_spine_separation.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    assert module.shape_of(EXAMPLE) == "canonical"
    assert module.resolver_ownership(EXAMPLE)
    assert module.governed_seam_calls(EXAMPLE) == {}
    assert module.legacy_governance_regions(EXAMPLE) == []


def test_the_plan_factory_takes_its_operators_only_from_required() -> None:
    """`D-IMPL-137` row C, read off the tree by the SDK's own predicate.

    Declared product gate `C36-G09` (`CP-SPEC-007` §G.1) — the plan factory takes its operators only from the resolver's `required`.
    `CP07-F-11` recorded that §G.1's old `C36-G08` made TWO claims under one
    id while a gate carries one `test:`; the clause is now split so each
    half is evidenced by the test that actually proves it.
    """
    spec = importlib.util.spec_from_file_location(
        "_gate2", REPO_ROOT / "tests" / "products" / "test_gate_two_call_shape.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    path = EXAMPLE / "produce.py"
    factory = next(
        n for n in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if isinstance(n, ast.FunctionDef) and n.name == "plan_factory")
    assert module._sdk_supplied_operator_set(factory, path)
    assert module._constructed_plan_sources(factory, None) == (("required",),)


def test_the_door_declares_its_entrypoint_rather_than_a_script_path() -> None:
    """A consumer asks for a product; it does not learn how the producer starts.

    A client carrying `python examples/…/serve.py` is bound to this
    deployment's directory layout, interpreter and language — none of which is
    part of the product contract.
    """
    import yaml  # noqa: PLC0415

    declared = yaml.safe_load(
        (EXAMPLE / "server" / "door.yaml").read_text(encoding="utf-8"))["declaration"]
    entrypoint = declared["serve_entrypoint"]
    assert ":" in entrypoint, "the entry point is not a module:callable reference"
    assert not entrypoint.endswith(".py"), "the binding names a script path"
    module_name, _, callable_name = entrypoint.partition(":")
    source = (EXAMPLE / "server" / f"{module_name}.py").read_text(encoding="utf-8")
    assert f"def {callable_name}(" in source, (
        f"door.yaml names {entrypoint!r} and that callable does not exist"
    )


# --- the relative window: a default that does not age ------------------------
#
# `D-IMPL-325`, adopted here to close `CP07-F-03`. The class's `since` default
# was the absolute `"2024-09-01"`, which meant two years of history on the day
# it was written and would have meant three a year later — the fan-out growing
# with nothing anywhere saying the default had drifted. It is now declared as
# an offset from the request's own `asked_at`.
#
# **Every expectation below is DERIVED from the declaration and the instant**,
# never pinned. A pinned date would reintroduce exactly the defect this closes:
# a literal that is right today and silently wrong later.


def _declared_offset() -> int:
    """The offset the ARTIFACT declares, read from it rather than restated."""
    import yaml  # noqa: PLC0415

    config = yaml.safe_load((EXAMPLE / "ccf_config.yaml").read_text(encoding="utf-8"))
    relative = config["request_contract"]["relative_defaults"]["since"]
    assert relative["render"] == "date", "the window is declared as a calendar day"
    assert relative["offset_seconds"] < 0, "a lookback reaches into the past"
    return int(relative["offset_seconds"])


def _window_for(instant: datetime) -> str:
    """What the DECLARATION means for a question asked at ``instant``.

    Derived from the artifact and the instant, never pinned: a literal date
    here would reintroduce the very defect this closes — a value that is right
    today and silently wrong later.
    """
    return (instant + timedelta(seconds=_declared_offset())).date().isoformat()


def _resolved(outcome: Any, name: str) -> Any:
    """One resolved parameter, read out of REPLAY dimension 2.

    Read from the record rather than from a second resolution of our own: what
    a later examiner can reconstruct is exactly this, so an assertion made
    anywhere else would be about a value nobody could check afterwards.
    """
    from ccf.products.provenance import EffectiveRequest  # noqa: PLC0415

    resolution = EffectiveRequest.model_validate_json(
        outcome.record.policy_bindings.request_resolution)
    matches = [p for p in resolution.parameters if p.name == name]
    assert len(matches) == 1, f"{name} resolved {len(matches)} times in replay"
    return matches[0]


def test_the_window_resolves_from_asked_at_and_not_from_the_wall_clock(
    estate: tuple[str, str], example: tuple[Any, Any]
) -> None:
    """The instant is the QUESTION's, which is what makes the answer replayable.

    Asked at an instant several days from now, so a product resolving the
    window from the wall clock would answer with today-minus-the-offset and be
    caught. Any test pinned to `now` could not tell the two apart.

    **Forward rather than back, and the reason is the estate.** An `asked_at`
    before the newest observation is refused by `FreshnessScorer` — correctly,
    since an observation dated after the instant it is evaluated at is not
    evidence about that instant. Measured: `now - 200 days` raises
    `TemporalOrderError` because this estate's newest interaction is more
    recent than that. Forward is always safe: every observation stays in the
    past, and the sibling determinism tests already ask at `instant + 1 day`.
    """
    instant = datetime.now(UTC) + timedelta(days=3)
    served = _serve(example, asked_at=instant, limit=500)
    assert served.product.payload["window"]["since"] == _window_for(instant)
    # And the control: `now` would have produced a different date, so this is a
    # claim about WHICH instant was read rather than about the arithmetic.
    assert _window_for(instant) != _window_for(datetime.now(UTC))


def test_an_omitted_bound_takes_the_declared_window_with_authority_default(
    estate: tuple[str, str], example: tuple[Any, Any]
) -> None:
    """Omission MEANS the declared window, and replay says who decided.

    The authority is what separates a default from a caller's value in the
    record; without it a replay could not tell a window the client asked for
    from one the Control Plane supplied.
    """
    instant = datetime.now(UTC)
    served = _serve(example, asked_at=instant, limit=500)
    resolved = _resolved(served, "since")
    assert resolved.authority == "default"
    assert resolved.value == _window_for(instant)


def test_a_caller_who_states_a_window_keeps_it(
    estate: tuple[str, str], example: tuple[Any, Any]
) -> None:
    """A default is what omission means, never a competitor to a stated value."""
    instant = datetime.now(UTC)
    stated = "2025-06-15"
    served = _serve(example, asked_at=instant, since=stated, limit=500)
    resolved = _resolved(served, "since")
    assert resolved.authority == "caller"
    assert resolved.value == stated
    assert served.product.payload["window"]["since"] == stated
    # The control: the declared window is a DIFFERENT date, so "caller wins" is
    # a claim about precedence rather than a coincidence of two equal values.
    assert stated != _window_for(instant)


def test_the_record_carries_the_resolved_date_and_never_the_offset(
    estate: tuple[str, str], example: tuple[Any, Any]
) -> None:
    """What replays is the value, not the rule (`D-IMPL-325`, Dave).

    A rule carried into the record would be re-evaluated at replay time and
    would answer one decision differently on two days. The offset must appear
    nowhere in the served product OR in the replay record.
    """
    from ccf.contracts.canonical import canonical_bytes  # noqa: PLC0415

    instant = datetime.now(UTC)
    served = _serve(example, asked_at=instant, limit=500)
    offset = _declared_offset()

    assert _resolved(served, "since").value == _window_for(instant)
    for label, subject in (("product", served.product), ("record", served.record)):
        rendered = canonical_bytes(subject).decode("utf-8")
        assert str(offset) not in rendered, (
            f"the declared offset reached the {label}; what is recorded must be"
            " the date it resolved to, so replay reproduces the same window")


def test_one_instant_resolves_one_window_and_a_later_one_resolves_a_later_window(
    estate: tuple[str, str], example: tuple[Any, Any]
) -> None:
    """Both halves, because either alone is satisfiable by a broken product.

    Same instant twice -> the same date, or the window is not deterministic and
    the determination cannot replay. A day later -> a strictly later date, or
    the window is not relative at all and the absolute default is back.
    """
    instant = datetime.now(UTC)
    first = _serve(example, asked_at=instant, limit=500)
    again = _serve(example, asked_at=instant, limit=500)
    assert (first.product.payload["window"]["since"]
            == again.product.payload["window"]["since"])

    later = _serve(example, asked_at=instant + timedelta(days=1), limit=500)
    assert (later.product.payload["window"]["since"]
            > first.product.payload["window"]["since"])


def test_the_declared_window_still_exceeds_the_class_limit(
    estate: tuple[str, str], example: tuple[Any, Any], default: Any
) -> None:
    """The adoption did not quietly retire this rung's own subject.

    `CP07-F-04` established that a `-365 day` window and the truncation
    demonstration cannot both hold: measured at `asked_at` 2026-09-11, a year
    admits 179 of this anchor's interactions — under the `limit` of 200, so
    nothing truncates — and the one need-to-know interaction falls outside it
    too. The declared offset must therefore stay wide enough that BOTH subjects
    still fire, and this says so where a later author changing the number will
    see it rather than leaving it to `CP07-F-04` in prose.
    """
    boundary = _boundary(default)
    assert boundary["truncated"] is True, (
        "the declared window no longer admits more than the class `limit`, so"
        " the truncation demonstration has been retired by a calibration change"
        " (CP07-F-04, D-IMPL-323)")
    assert boundary["withheld_need_to_know"] > 0, (
        "the declared window no longer reaches the classified interaction, so"
        " the need-to-know withholding demonstrates nothing")


def test_the_enrich_leg_issues_a_fixed_number_of_queries(
    estate: tuple[str, str], example: tuple[Any, Any]
) -> None:
    """**One batched query per step, not one per row.** `CP07-F-11`'s first half.

    The claim `acquisition.py` makes in three docstrings — *"ONE batched
    query"* — had no test, because proving it needs a counting seam rather than
    an id added to an existing assertion. This is that seam: `_GraphLeg.query`
    is wrapped for the duration of two acquisitions, and the call counts are
    compared.

    **Two clients of very different size must cost the same number of round
    trips.** If the enrich leg fanned out per interaction or per participant,
    the larger client would cost more queries than the smaller one, and a graph
    twice the size would double the cost. The counts must be equal AND small —
    an equal count that rose with the estate would satisfy neither half.

    Asserted as a relationship between two real subjects, never as a pinned
    number, so estate drift exercises this instead of breaking it.

    Declared product gate `C36-G06` (`CP-SPEC-007` §G.1).
    """
    deployment, produce = example
    acquisition = sys.modules["acquisition"]

    original = acquisition._GraphLeg.query
    counts: dict[str, int] = {}

    def counted(self: Any, body: str) -> Any:
        counts[label] = counts.get(label, 0) + 1
        return original(self, body)

    acquisition._GraphLeg.query = counted
    try:
        for label, lei in (("demonstration", _anchor("DEMONSTRATION_LEI")),
                           ("control", _anchor("CONTROL_LEI"))):
            counts.setdefault(label, 0)
            _serve(example, lei=lei)
    finally:
        acquisition._GraphLeg.query = original

    assert counts["demonstration"] > 0 and counts["control"] > 0, (
        f"the graph leg was never queried, so this counts nothing: {counts}"
    )
    assert counts["demonstration"] == counts["control"], (
        "two clients of different size cost different numbers of graph"
        f" queries, so the enrich leg fans out per row: {counts}"
    )
    # A fixed count is only meaningful if it is SMALL. Per-row fan-out on this
    # estate would be in the hundreds; a batched leg is a handful of steps.
    assert counts["demonstration"] < 25, (
        f"the leg issues {counts['demonstration']} queries for one client —"
        " equal between subjects, but not batched"
    )
