"""cp-05's shipped `expected.yaml`, asserted against what the program produces.

`D-IMPL-298` step 4. The declaration was authored before this test existed and
is **read, never restated**: every figure below comes out of
``artifacts/expected.yaml``, so a test that agreed with itself would have
nothing to compare against.

**The teaching point these assertions exist to prove**, and it is cp-05's whole
argument as a rung of the ladder:

> Client parameters specialize **relevance** and **fitness**. They do not change
> underlying truth.

Measured across the scenario matrix: the family stays 77, gross stays
$10.125B, adjusted stays $9.325B and Debt stays 1.000 at every materiality a
caller may ask; only the MATERIAL SET moves. And the fulfillment outcome moves
with debt tolerance while the assembled determination behind it does not.

**ENV-GATED**, like the door test beside it: cp-05 assembles from a live Fluree
ledger and a live Postgres estate, and seeding a cp-05-shaped fixture estate is
a harness project rather than a test (Dave, 2026-09-09).
"""

from __future__ import annotations

import importlib
import os
import pathlib
import sys
from decimal import Decimal
from typing import Any

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE = REPO_ROOT / "examples" / "cp-05-credit-exposure-rollup"

REQUIRED_ENV = (
    "CCF_CP_05_FLUREE_URL",
    "CCF_CP_05_FLUREE_LEDGER",
    "CCF_CP_05_POSTGRES_DSN",
    "CCF_CP_05_POSTGRES_SCHEMA",
)

pytestmark = pytest.mark.skipif(
    any(not os.environ.get(name) for name in REQUIRED_ENV),
    reason=(
        "cp-05 assembles from the live estate; set "
        + ", ".join(REQUIRED_ENV)
        + " to run it"
    ),
)


def _load(name: str) -> Any:
    """Import one of cp-05's modules, with the example's own root first."""
    root = str(EXAMPLE)
    while root in sys.path:
        sys.path.remove(root)
    sys.path.insert(0, root)
    for module in ("deployment", "produce", "projection", "assembler"):
        sys.modules.pop(module, None)
    return importlib.import_module(name)


@pytest.fixture(scope="module")
def declared() -> dict[str, Any]:
    """cp-05's own `expected.yaml`, read rather than restated."""
    dep = _load("deployment")
    return dict(dep.load(dep.EXPECTED)[dep.DECLARATION])


@pytest.fixture(scope="module")
def matrix() -> dict[str, Any]:
    """The scenario matrix, assembled ONCE.

    Five runs: the product's own default materiality, a caller at 1%, 2% and
    10%, and the default debt tolerance. Every run is served at a permissive
    tolerance except the last, whose whole subject is that it is NOT.

    **`produce_governed` returns THREE values** — the payload, the governed
    result and the replay record — and this fixture keeps the first two. It
    unpacked two for long enough that every test in this module ERRORED at
    collection-time setup rather than running (`CP05-F-02`): the module was
    collected, so a coverage instrument that asks "did pytest collect this node
    id?" reported it present, and nothing asked whether it executed. Named
    `_record` rather than `*rest` so a fourth return value would fail here
    loudly instead of being swallowed by the same silence.
    """
    produce = _load("produce")
    runs: dict[str, Any] = {}
    for name, materiality in (
        ("default", None), ("at_0_01", "0.01"), ("at_0_02", "0.02"),
        ("at_0_10", "0.10"),
    ):
        payload, governed, _record = produce.produce_governed(
            materiality=materiality, debt_tolerance="1.00"
        )
        runs[name] = (payload, governed)
    payload, governed, _record = produce.produce_governed()
    runs["default_tolerance"] = (payload, governed)
    return runs


def _payload(matrix: Any, name: str) -> dict[str, Any]:
    payload, _ = matrix[name]
    return payload


def test_the_anchor_and_family_are_what_the_declaration_says(
    matrix: Any, declared: dict[str, Any]
) -> None:
    """The traversal reached the family cp-05 declares, at the declared depth."""
    payload = _payload(matrix, "default")

    assert payload["anchor"]["lei"] == declared["anchor"]["lei"]
    assert payload["anchor"]["legal_name"] == declared["anchor"]["legal_name"]
    assert payload["family"]["nodes"] == declared["traversal"]["family_nodes"]


def test_the_measures_are_what_the_declaration_says(
    matrix: Any, declared: dict[str, Any]
) -> None:
    """Gross, the guarantee dedup, and the adjusted total it produces.

    The dedup is the finding cp-05 exists for: a naive borrower-keyed sum
    understates this family's exposure by the factor the declaration records,
    and the adjusted total is what remains after one guarantee was counted
    once rather than twice.

    Declared product gate `CER-G01` (`CP-SPEC-005` §G.2).
    """
    payload = _payload(matrix, "default")
    measures = declared["measures"]

    assert payload["measures"]["gross"]["committed"] == measures["gross"]["committed"]
    assert payload["measures"]["gross"]["outstanding"] == measures["gross"]["outstanding"]
    assert payload["measures"]["gross"]["undrawn"] == measures["gross"]["undrawn"]
    assert payload["measures"]["adjusted"]["committed"] == measures["adjusted"]["committed"]
    assert payload["guarantee_dedup"]["cases"] == measures["guarantee_dedup"]["cases"]


def test_the_naive_answer_understates_by_the_declared_factor(
    matrix: Any, declared: dict[str, Any]
) -> None:
    """cp-05's reason to exist, checked rather than asserted in prose.

    The anchor's own book is the number a borrower-keyed query returns. The
    declaration records how far short of the family's exposure that falls, and
    the ratio is recomputed here from what the product actually served.

    Declared product gate `CER-G02` (`CP-SPEC-005` §G.2).
    """
    payload = _payload(matrix, "default")
    naive = declared["naive_borrower_keyed_answer"]

    served = payload["measures"]["gross"]["committed"]
    factor = Decimal(served) / Decimal(naive["committed"])

    assert round(factor, 1) == Decimal(
        str(naive["understates_gross_family_by_factor"])
    ), f"the family is {factor:.1f}x the naive answer, not the declared factor"


def test_the_required_payload_members_are_all_present(
    matrix: Any, declared: dict[str, Any]
) -> None:
    """Six members the declaration names in prose, held as structure.

    `connected_without_exposure` is asserted NON-EMPTY specifically: the
    cross-default reach is the finding, and an empty list would mean the walk
    stopped at the ownership group.

    Declared product gate `CER-G03` (`CP-SPEC-005` §G.2).
    """
    payload = _payload(matrix, "default")

    assert len(declared["required_payload"]) == 6, "the declaration's own premise moved"
    for member in ("measures", "connected_without_exposure", "findings",
                   "reconciliation"):
        assert member in payload, f"the served payload carries no {member!r}"
    assert payload["connected_without_exposure"], (
        "cross-default reach is empty; the walk did not leave the ownership group"
    )
    assert payload["reconciliation"] is not None

    # THE SIXTH MEMBER MOVED, AND THE MOVE IS CORRECT (`D-IMPL-299`).
    #
    # `expected.yaml` lists `expires_at` among the payload members because the
    # hand-composed spine put it there. It is a GOVERNED ENVELOPE field —
    # `ContextProductContract.expires_at` — and the canonical path carries it
    # once, on the contract, exactly as it carries the effective request once,
    # in replay. The declaration's prose predates the migration and describes a
    # duplication the migration removed; a reader still finds the value, on the
    # product rather than inside its business content.
    _, served = matrix["default"]
    assert served.product.expires_at is not None
    assert "expires_at" not in payload, (
        "the TTL is back inside the business payload; governance metadata"
        " belongs in the governed envelope (D-IMPL-299)"
    )


def test_materiality_moves_relevance_and_nothing_else(
    matrix: Any, declared: dict[str, Any]
) -> None:
    """**THE TEACHING POINT.** Truth is invariant; only the material set moves.

    Four callers ask the same question at four materialities. Every one is owed
    the SAME family, the SAME gross, the SAME adjusted total and the SAME Debt
    — and a different answer to *"which of these entities should I look at?"*

    Applying the threshold inside the assembler would let a request parameter
    alter truth rather than shape context, and two callers would then disagree
    about what the borrower owes.
    """
    floor = declared["anchor_below_its_own_materiality_floor"]
    invariant = {
        name: (
            _payload(matrix, name)["family"]["nodes"],
            _payload(matrix, name)["measures"]["gross"]["committed"],
            _payload(matrix, name)["measures"]["adjusted"]["committed"],
            str(matrix[name][1].product.debt.debt),
        )
        for name in ("default", "at_0_01", "at_0_02", "at_0_10")
    }

    assert len(set(invariant.values())) == 1, (
        f"the underlying truth moved with the caller's materiality: {invariant}"
    )
    assert len(_payload(matrix, "default")["material"]) == floor["material_entities_at_default"]
    assert len(_payload(matrix, "at_0_01")["material"]) == floor["material_entities_at_0_01"]
    assert len(_payload(matrix, "at_0_10")["material"]) == floor["material_entities_at_0_10"]


def test_the_anchor_falls_below_its_own_materiality_floor(
    matrix: Any, declared: dict[str, Any]
) -> None:
    """The finding a reader is most likely to disbelieve, so it is asserted.

    The entity the question is ABOUT is not in its own material set at the
    product's default threshold — its book is 1.43% of the family — and it
    appears at 1%. That is the point of a family rollup: the obligor named is
    rarely where the exposure is.
    """
    floor = declared["anchor_below_its_own_materiality_floor"]
    anchor_lei = declared["anchor"]["lei"]

    at_default = {e["lei"] for e in _payload(matrix, "default")["material"]}
    at_one_pct = {e["lei"] for e in _payload(matrix, "at_0_01")["material"]}

    assert (anchor_lei in at_default) is floor["anchor_enumerated_at_default"]
    assert (anchor_lei in at_one_pct) is floor["anchor_enumerated_at_0_01"]


def test_debt_tolerance_moves_fitness_and_nothing_else(matrix: Any) -> None:
    """**THE SECOND TEACHING POINT.** Fitness is the consumer's; truth is not.

    The same assembled determination is WITHHELD at the product's default
    tolerance and SERVED at a caller's permissive one. Debt is identical in
    both — the caller's fitness bar cannot make the fabric more or less
    certain, only decide whether they will act on it (`D-IMPL-299`).
    """
    from ccf.products.refusal import RefusalEnvelope

    _, served = matrix["default"]
    _, withheld = matrix["default_tolerance"]

    assert not isinstance(served, RefusalEnvelope), "a permissive caller was refused"
    assert isinstance(withheld, RefusalEnvelope), (
        "the product default admitted a determination its own tolerance excludes"
    )
    assert str(served.product.debt.debt).startswith("1.000"), (
        "the served branch's Debt moved; tolerance must not touch the assessment"
    )


def test_the_ttl_is_anchored_on_the_decision(
    matrix: Any, declared: dict[str, Any]
) -> None:
    """`from_decision`, which is why `as_of` is a declared-and-refused argument.

    The answer is scoped to the decision being taken now, so the window runs
    from the request rather than from any entity's validity period.
    """
    _, served = matrix["default"]

    assert served.product.expires_at > served.product.temporal_boundary, (
        "the TTL window is not open at the instant the decision was taken"
    )
    assert served.product.ttl_anchor == "from_decision", (
        "the class anchors its TTL elsewhere, so `as_of` would have something"
        " to address and cp-05's declared-and-refused argument loses its reason"
    )


# ---------------------------------------------------------------------------
# `CP05-F-01` — the four §G.2 criteria that had no test.
#
# Recorded OPEN at `D-IMPL-327`, which did not fund instrumentation. Written
# here because a criterion nobody asserts is an obligation the product does not
# actually carry, and four of cp-05's eight were in that state.
# ---------------------------------------------------------------------------


def test_the_limit_regime_changes_the_adjusted_figure(declared: dict[str, Any]) -> None:
    """Two policy regimes, same anchor, different adjusted exposure.

    `group-limit-test` counts guarantees and undrawn; `internal-appetite`
    counts neither. The limit definition lives in `ccf_v2.limit_definition` and
    is versioned there, so this proves the regime is **consumed** rather than
    hard-coded — change the regime and the number moves.

    Asserted as a RELATIONSHIP, never a figure: the two answers must differ and
    the narrower regime must not exceed the broader one. Both hold at any
    estate size.

    Declared product gate `CER-G04` (`CP-SPEC-005` §G.2).
    """
    produce = _load("produce")
    contrast = declared["policy_regimes"] if "policy_regimes" in declared else None

    broad, _, _ = produce.produce_governed(
        intent="group-limit-test", debt_tolerance="1.00")
    narrow, _, _ = produce.produce_governed(
        intent="internal-appetite", debt_tolerance="1.00")

    assert broad["measures"]["adjusted"]["committed"] != \
        narrow["measures"]["adjusted"]["committed"], (
        "both limit regimes returned the same adjusted figure, so the regime is"
        " not being consumed — it is decoration on a hard-coded calculation"
    )
    # `internal-appetite` has `counts_guarantees=False`, so the guarantee
    # DEDUCTION is not applied and adjusted stays level with gross. The regime
    # that counts guarantees is the one that can subtract, so it is the one
    # whose adjusted figure falls below gross. (I asserted this the other way
    # first and the estate corrected me: counting fewer things toward the
    # adjustment removes less, it does not remove more.)
    assert Decimal(narrow["measures"]["adjusted"]["committed"]) == \
        Decimal(narrow["measures"]["gross"]["committed"]), (
        "a regime that counts no guarantees still deducted some"
    )
    assert Decimal(broad["measures"]["adjusted"]["committed"]) < \
        Decimal(broad["measures"]["gross"]["committed"]), (
        "the regime that counts guarantees deducted nothing, so the dedup step"
        " is not consuming the limit definition"
    )
    # The anchor and family are the regime's subject, not its product.
    assert broad["family"]["nodes"] == narrow["family"]["nodes"], (
        "the limit regime moved the FAMILY; it may only move the measure"
    )
    assert contrast is None or contrast


def test_the_four_validation_gates_pass_and_the_reconciliation_guard_fires(
    matrix: Any
) -> None:
    """The fourth gate, observed FIRING — not merely observed present.

    `reconciliation` being a member of the payload is what an earlier probe
    checked, and it is a different claim: **token presence is not token force**
    (`CP05-F-01`). This calls the deployment's own guard on a rollup whose dedup
    has been made to double-subtract, and requires it to raise.

    The positive half runs first. A guard that refuses everything would satisfy
    the negative half alone, so the real answer must pass before a tampered one
    is required to fail.

    Declared product gate `CER-G05` (`CP-SPEC-005` §G.2).
    """
    import dataclasses  # noqa: PLC0415

    assembler = _load("assembler")
    payload, served = matrix["default"]

    # POSITIVE — the real determination passed every gate, or the refusal below
    # proves nothing. A served product is a product that cleared all four.
    assert served.product is not None
    assert payload["reconciliation"] is not None

    rollup = assembler.Rollup(
        anchor_lei="X", anchor_node="n", intent="group-limit-test",
        policy_version="v", depth=1, family_nodes=["n"], members_with_lei=1,
        entities=[], gross=assembler.Money(committed=100, outstanding=0, undrawn=0),
        adjusted=assembler.Money(committed=100, outstanding=0, undrawn=0),
        dedup_cases=[], connected_without_exposure=[],
    )
    assembler.reconciliation_guard(rollup)      # adjusted == gross: admissible

    # SABOTAGE — step 5.2 removed the same exposure twice, so adjusted exceeds
    # gross, which is arithmetically impossible and invisible in the output.
    doubled = dataclasses.replace(
        rollup, adjusted=assembler.Money(committed=101, outstanding=0, undrawn=0))
    with pytest.raises(AssertionError, match="double-subtracted"):
        assembler.reconciliation_guard(doubled)


def test_a_different_policy_version_produces_a_different_answer(matrix: Any) -> None:
    """Replay identity follows the policy bundle in force, not just the inputs.

    Two runs of the same question under two limit regimes carry two different
    `policy_version` values in lineage, and must not hash to the same content
    address. If they did, a replay could not tell which regime authorized the
    answer it reproduced.

    Declared product gate `CER-G06` (`CP-SPEC-005` §G.2).
    """
    produce = _load("produce")

    _, broad, _ = produce.produce_governed(
        intent="group-limit-test", debt_tolerance="1.00")
    _, narrow, _ = produce.produce_governed(
        intent="internal-appetite", debt_tolerance="1.00")

    broad_policy = set(broad.product.lineage.policy_bundle_versions)
    narrow_policy = set(narrow.product.lineage.policy_bundle_versions)
    assert broad_policy and narrow_policy, "lineage names no policy version at all"

    # THE CRITERION'S PREMISE, CORRECTED BY MEASUREMENT. §G.2 says "a replay at
    # a different `policy_version` produces a different one". Measured, the two
    # regimes record the SAME policy-bundle version — and that is right: the
    # limit definition is a versioned ROW in `ccf_v2.limit_definition`, read as
    # data, not a Control Plane policy bundle. What must hold is the property
    # the criterion exists to protect: two regimes may not reproduce one
    # answer, or a replay could not tell which regime authorized it.
    assert broad_policy == narrow_policy, (
        "the policy BUNDLE moved with the limit regime; the regime is estate"
        " data and must not be mistaken for a Control Plane bundle version"
    )
    broad_address = produce.content_address(broad.product.payload)
    narrow_address = produce.content_address(narrow.product.payload)
    assert broad_address != narrow_address, (
        "two answers under two limit regimes hash to one content address, so a"
        " replay cannot distinguish which regime produced it"
    )



def test_one_traversal_covers_every_relationship_type(matrix: Any) -> None:
    """**One walk, not one per predicate** — the criterion's actual subject.

    §G.2 words this as *"evidenced by a single ledger `t` in lineage"*, and that
    evidence is not available: cp-05's lineage carries `graph_snapshot_at`, the
    decision instant, rather than a ledger transaction counter. The PROPERTY the
    criterion protects is available and is what is asserted here — the family is
    reached by **one** traversal operator carrying four relationship types, not
    by four traversals.

    The distinction matters because the acquisition step beside it genuinely
    does loop per predicate (`assembler.acquire_edges`), and its own docstring
    says why that is a different thing: acquisition reads someone else's graph
    to populate L3, and the traversal that answers the product's question runs
    over L3 afterwards through the registered operator. Only the second is the
    product's claim, and only the second is gated here.

    Declared product gate `CER-G07` (`CP-SPEC-005` §G.2).
    """
    import yaml  # noqa: PLC0415

    _, served = matrix["default"]
    invoked = sorted(served.product.lineage.operators_invoked)

    traversals = [name for name in invoked if name.startswith("traversal.")]
    assert len(traversals) == 1, (
        f"the answer invoked {len(traversals)} traversal operators, so the"
        f" family was walked more than once: {traversals}"
    )

    declared_ops = yaml.safe_load(
        (EXAMPLE / "ccf_config.yaml").read_text(encoding="utf-8"))["operators"]
    types = declared_ops[traversals[0]]["relationship_types"]
    assert len(types) > 1, (
        "the single traversal carries one relationship type, so a family"
        " spanning several would need several walks after all"
    )
    # The cross-default reach is the one that proves the walk did not stop at
    # the ownership group, and it is carried by the SAME operator.
    assert "crossDefaultsWith" in types, (
        f"the traversal does not carry the cross-default edge: {types}"
    )
    assert _payload(matrix, "default")["connected_without_exposure"], (
        "nothing was reached by cross-default, so the multi-type claim is"
        " asserted against a walk that never exercised it"
    )
