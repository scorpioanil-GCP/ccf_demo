"""Granularity as a ceiling, a shape and a cost — the rung's headline.

Nine of the twenty-one declared gates of `CP-SPEC-016` §G.1 execute here:
`ABS-G05`, `ABS-G08`..`ABS-G15`.

Every assertion is a RELATIONSHIP or an IDENTITY and never an estate count.
**Reads the curated estate, seeds nothing** (CLAUDE.md §9).
"""

from __future__ import annotations

import pathlib
from collections.abc import Mapping
from typing import Any

import pytest
import yaml
from ccf.replay.serve import ServedProduct

from tests.examples.test_cp_16_surveillance import (  # noqa: F401 — fixtures travel with the import
    AS_OF,
    DESK,
    EXAMPLE,
    QUESTION,
    REPORTING,
    RISK,
    SUBJECT,
    Answer,
    answer,
    ask,
    estate,
    modules,
)

pytestmark = [pytest.mark.fluree, pytest.mark.postgres, pytest.mark.mongo]

PERSPECTIVES: dict[str, Any] = yaml.safe_load(
    (EXAMPLE / "artifacts" / "perspectives.yaml").read_text(encoding="utf-8"))["declaration"]
ORDER: list[str] = list(PERSPECTIVES["granularity_order"])


# =========================================================================
# ABS-G08 / ABS-G09 — two different refusals, and they are not the same kind
# =========================================================================


def test_a_granularity_outside_the_domain_is_a_request_violation(
    estate: None, modules: dict[str, Any], tmp_path: pathlib.Path,
) -> None:
    """Not a policy matter: `servicer` is not a meaningful question of this class.

    `D-IMPL-259` keeps the parameter's valid DOMAIN in the request contract and
    out of the constraint layer, and the SDK enforces it before the deployment
    is reached at all.

    Declared product gate `ABS-G08` (`CP-SPEC-016` §B.3, §G.1).
    """
    outcome = ask(modules, tmp_path, granularity="servicer")
    assert not isinstance(outcome, Answer), "a value outside the domain is never served"
    assert outcome.kind == "product-request-violation", (
        f"an out-of-domain value is a REQUEST violation, not a policy refusal; got {outcome.kind}"
    )
    assert outcome.reason == "not-in-domain"


def test_a_granularity_above_the_role_ceiling_is_a_policy_refusal(
    estate: None, modules: dict[str, Any], tmp_path: pathlib.Path,
) -> None:
    """`loan` is a meaningful question; this caller may not ask it.

    The two refusals are DIFFERENT KINDS. An out-of-domain value never reaches
    policy; an in-domain value above the ceiling is refused by policy, and the
    bound travels with the determination.

    Declared product gate `ABS-G09` (`CP-SPEC-016` §B.3, §F.4.2, §G.1).
    """
    outcome = ask(modules, tmp_path / "a", principal=REPORTING, granularity="loan", loan_sample=50)
    assert not isinstance(outcome, Answer), "a granularity above the ceiling is never served"
    assert outcome.kind != "product-request-violation", (
        "an in-domain value refused by policy is not a malformed request"
    )
    # The value IS in the domain — the same value is served to a role whose
    # ceiling reaches it, so the refusal is about the caller and not the value.
    served = answer(modules, tmp_path / "b", principal=DESK, granularity="loan", loan_sample=25)
    assert served.payload["effective_granularity"] == "loan"


def test_the_bound_travels_with_the_refusal_into_the_determination(
    estate: None, modules: dict[str, Any], tmp_path: pathlib.Path,
) -> None:
    """*Refused `not-in-allowed-set` carrying the bound* — where the bound lands.

    The caller-facing envelope is redacted by this deployment's `minimal`
    disclosure posture, so the bound reaches the EXAMINER rather than the
    caller. That is the standing posture of the ladder (the `CP17-F` family,
    closed at `D-IMPL-345`) and is recorded as `ABS-F-06`, not repaired here.

    Declared product gate `ABS-G09` (`CP-SPEC-016` §F.4.2, §G.1).
    """
    deployment = modules["deployment"]
    with modules["produce"].product(tmp_path) as opened:
        from ccf.projection.plan import Perspective  # noqa: PLC0415

        asked = opened.question(
            subject=SUBJECT, asked_at=_instant(), intent=QUESTION["question"]["intent"],
            freshness=QUESTION["question"]["freshness"],
            parameters={deployment.AS_OF: AS_OF, deployment.GRANULARITY: "loan",
                        deployment.LOAN_SAMPLE: 50},
        )
        outcome = opened.answer(
            asked, perspective=Perspective(principal_id=REPORTING[0], role=REPORTING[1]))
        assert not isinstance(outcome, ServedProduct)
        address = str(outcome.replay_reference).rsplit("@", 1)[-1]
        record = opened.artifact_store.get(content_address=address).decode()
    assert "not-in-allowed-set" in record, "the refusal is named in the determination"
    assert "ceiling" in record and "loan" in record, "and the bound that caused it travels with it"


def _instant():  # noqa: ANN202
    from datetime import datetime  # noqa: PLC0415

    return datetime.fromisoformat(AS_OF)


# =========================================================================
# ABS-G10 / ABS-G11 — the ceiling is stated, and the two authorities agree
# =========================================================================


def test_the_stated_ceiling_is_the_constraint_that_was_resolved(
    estate: None, modules: dict[str, Any], tmp_path: pathlib.Path,
) -> None:
    """POSITIVELY, for all three roles, so it cannot pass by coincidence.

    A vacuous *"if policy lowered it, say so"* assertion is refused by ruling:
    nothing ever lowers a granularity here, so that assertion would be true
    forever. This one reads the stated ceiling back against the resolved one.

    Declared product gate `ABS-G10` (`CP-SPEC-016` §F.4.2, §G.1).
    """
    projection = modules["projection"]
    stated: dict[str, str] = {}
    for index, principal in enumerate((DESK, RISK, REPORTING)):
        role = principal[1]
        ceiling = projection.PERSPECTIVE_CEILING[role]
        reply = answer(modules, tmp_path / f"r{index}", principal=principal,
                       granularity=ceiling,
                       # `loan` requires a bound: the product refuses to be
                       # asked to materialize the pool (`ABS-G13`).
                       loan_sample=10 if ceiling == "loan" else None)
        stated[role] = reply.payload["granularity_ceiling"]
        assert stated[role] == projection.PERSPECTIVE_CEILING[role], (
            f"role `{role}` states ceiling {stated[role]!r} but resolves"
            f" {projection.PERSPECTIVE_CEILING[role]!r}"
        )
    # THE THREE ARE DIFFERENT, so a single hard-coded value cannot satisfy all
    # three limbs at once.
    assert len(set(stated.values())) == 3, f"the three roles must differ: {stated}"


def test_the_control_plane_ceiling_agrees_with_the_estate(
    estate: None, modules: dict[str, Any], tmp_path: pathlib.Path,
) -> None:
    """Two authorities that can drift are checked against each other.

    Declared product gate `ABS-G11` (`CP-SPEC-016` §C.3 trap 5, §G.1).
    """
    acquisition = modules["acquisition"]
    deployment = modules["deployment"]
    with modules["produce"].product(tmp_path) as opened:
        settings = opened.sources[deployment.SOURCE_RELATIONAL]
        relational = acquisition._Relational(dsn=settings["dsn"], schema=settings["schema"])
        tables = acquisition.vocabulary()["relational"]["tables"]
        for role in modules["projection"].PERSPECTIVE_CEILING:
            ceiling = acquisition.ceiling_for(relational, role=role, tables=tables)
            assert ceiling.estate_value is not None, (
                f"the estate declares no ceiling for `{role}`; the cross-check is not vacuous"
            )
            assert ceiling.agrees_with_estate, (
                f"the Control Plane bounds `{role}` at {ceiling.ceiling!r} while the estate"
                f" declares {ceiling.estate_value!r}"
            )


# =========================================================================
# ABS-G12 — three roles, one door, three shapes
# =========================================================================


def test_the_payload_shape_follows_the_granularity_not_the_deal(
    estate: None, modules: dict[str, Any], tmp_path: pathlib.Path,
) -> None:
    """A role that may not ask for loan detail carries no empty loan member.

    An empty `cohort_performance` would read as *this deal has no cohorts*
    rather than *you may not ask*, which is the distinction the shape keeps.

    Declared product gate `ABS-G12` (`CP-SPEC-016` §D.3, §G.1).
    """
    projection = modules["projection"]
    shapes: dict[str, frozenset[str]] = {}
    for index, principal in enumerate((DESK, RISK, REPORTING)):
        role = principal[1]
        ceiling = projection.PERSPECTIVE_CEILING[role]
        reply = answer(modules, tmp_path / f"s{index}", principal=principal,
                       granularity=ceiling, loan_sample=10 if ceiling == "loan" else None)
        shapes[role] = frozenset(reply.payload)
        assert reply.payload["effective_granularity"] == ceiling

    assert len(set(shapes.values())) == 3, "three ceilings give three different shapes"
    # And they NEST: a coarser role's members are a subset of a finer one's.
    assert shapes["client-reporting"] < shapes["credit-risk"] < shapes["structured-finance-desk"]
    assert "cohort_performance" not in shapes["client-reporting"]
    assert "loan_sample_detail" not in shapes["credit-risk"]
    assert "loan_sample_detail" in shapes["structured-finance-desk"]


# =========================================================================
# ABS-G05 — acquisition is bounded at the DECISION INSTANT
# =========================================================================


def test_acquisition_is_bounded_at_the_decision_instant(
    estate: None, modules: dict[str, Any], tmp_path: pathlib.Path,
) -> None:
    """Residual `341-1`, live for the first time on the ladder.

    A filing made after the instant is never SELECTED, not filtered afterwards.
    The repurchase leg is the observable one: the estate's filings span the
    window, so an earlier instant admits strictly fewer of them.

    Declared product gate `ABS-G05` (`CP-SPEC-016` §F.4.1, §G.1).
    """
    late = answer(modules, tmp_path / "late", as_of="2026-06-30T00:00:00+00:00")
    early = answer(modules, tmp_path / "early", as_of="2025-09-30T00:00:00+00:00")
    late_filings = {row["repurchase_id"] for row in late.payload["repurchase_activity"]}
    early_filings = {row["repurchase_id"] for row in early.payload["repurchase_activity"]}
    assert early_filings < late_filings, "an earlier instant serves strictly fewer filings"
    for row in early.payload["repurchase_activity"]:
        assert row["filed_date"] <= "2025-09-30"

    # THE SERVED PAYLOAD CANNOT PROVE WHERE THE BOUND WAS APPLIED. The temporal
    # operator also cuts at the boundary, so a product that acquired everything
    # and filtered afterwards serves exactly the same rows (measured 2026-09-21,
    # `ABS-F-08`). What distinguishes them is what ACQUISITION materialized, so
    # the gate reads the cost rather than the answer.
    late_materialized = int(late.payload["assembly_cost"]["records_materialized"])
    early_materialized = int(early.payload["assembly_cost"]["records_materialized"])
    assert early_materialized < late_materialized, (
        f"acquisition materialized {early_materialized} records at the earlier instant and"
        f" {late_materialized} at the later one; equal counts would mean the filings were"
        f" acquired and then filtered, which is what residual 341-1 forbids"
    )


# =========================================================================
# ABS-G13 / ABS-G14 — the population is never materialized
# =========================================================================


def test_the_source_population_is_never_materialized(
    estate: None, modules: dict[str, Any], tmp_path: pathlib.Path,
) -> None:
    """LOAD-BEARING. What became claims tracks the ANSWER, not the population.

    Both numbers are asserted because they answer different questions:
    `records_materialized` is what entered the fabric, `records_scanned` is what
    the statements touched. A representative sample keeps the first small while
    leaving the second large — and that is the honest shape of sampling rather
    than a defect (`ABS-F-01`).

    Declared product gate `ABS-G13` (`CP-SPEC-016` §0.2, §G.1).
    """
    sample = 120
    reply = answer(modules, tmp_path, principal=DESK, granularity="loan", loan_sample=sample)
    cost = reply.payload["assembly_cost"]
    materialized = int(cost["records_materialized"])
    scanned = int(cost["records_scanned"])
    detail = reply.payload["loan_sample_detail"]

    assert len(detail) <= sample, "the sample bound is honored"
    # The claim count is bounded by the SAMPLE, not by the partition.
    assert materialized < scanned, (
        "materializing everything scanned is exactly what this product must not do"
    )
    assert materialized <= sample + 50, (
        f"{materialized} records became claims for a sample of {sample}; the count tracks the"
        f" population rather than the answer"
    )
    # And the partition really is large, so the gate is not vacuously true.
    assert scanned > 10 * sample, (
        f"only {scanned} rows were scanned; this deal-period is too small to demonstrate fan-out"
    )


def test_the_loan_sample_is_representative_and_not_a_prefix(
    estate: None, modules: dict[str, Any], tmp_path: pathlib.Path,
) -> None:
    """ABS-EE ordering makes a prefix unrepresentative — and it is cheaper.

    The cheap option is the one the source specification forbids, so the gate
    proves the sample is NOT the first N rows of the partition.

    Declared product gate `ABS-G14` (`CP-SPEC-016` §D.3, §G.1).
    """
    acquisition = modules["acquisition"]
    deployment = modules["deployment"]
    reply = answer(modules, tmp_path, principal=DESK, granularity="loan", loan_sample=80)
    sampled = [row["asset_number"] for row in reply.payload["loan_sample_detail"]]
    assert sampled, "a sample was drawn"

    with modules["produce"].product(tmp_path / "probe") as opened:
        settings = opened.sources[deployment.SOURCE_RELATIONAL]
        relational = acquisition._Relational(dsn=settings["dsn"], schema=settings["schema"])
        tables = acquisition.vocabulary()["relational"]["tables"]
        prefix = [
            str(row["asset_number"])
            for row in relational.rows(
                f"select asset_number from {tables['loan']} where deal_id = %s and period = %s"  # noqa: S608
                f" order by asset_number limit %s",
                (SUBJECT, reply.payload["pool_performance"]["period"], len(sampled)),
            )
        ]
    assert prefix, "the probe read the same partition"
    assert sampled != prefix, "the sample is the partition's prefix, which ABS-EE ordering forbids"


# =========================================================================
# ABS-G15 — cost is blocks and records, never time
# =========================================================================


def test_cost_is_reported_relationally_in_blocks_and_never_in_time(
    estate: None, modules: dict[str, Any], tmp_path: pathlib.Path,
) -> None:
    """The only step that changes cost materially is loan-or-not.

    The estate's own runs put one granularity's median between 0.148 ms and
    205.871 ms on identical data while its block count never moved, so a
    time-keyed assertion would invert the ordering this rung teaches.

    Declared product gate `ABS-G15` (`CP-SPEC-016` §A.2, §G.1).
    """
    aggregate = {
        level: answer(modules, tmp_path / level, principal=DESK, granularity=level)
        for level in ("deal", "tranche", "cohort")
    }
    loan = answer(modules, tmp_path / "loan", principal=DESK, granularity="loan", loan_sample=60)

    for level, reply in aggregate.items():
        cost = reply.payload["assembly_cost"]
        assert cost["cost_band"] == "aggregate-scale", f"`{level}` is an aggregate rung"
        assert "milliseconds" not in cost and "elapsed_ms" not in cost, "time is never a gate"
    assert loan.payload["assembly_cost"]["cost_band"] == "loan-scale"

    blocks = {level: int(reply.payload["assembly_cost"]["blocks_scanned"])
              for level, reply in aggregate.items()}
    loan_blocks = int(loan.payload["assembly_cost"]["blocks_scanned"])
    # THE RELATION, which holds at any pool size: the aggregate rungs sit
    # together and `loan` is an order of magnitude away from all of them.
    assert loan_blocks > 10 * max(blocks.values()), (
        f"loan cost {loan_blocks} blocks against aggregate {blocks}; the step that costs"
        f" something is not visible"
    )
    assert max(blocks.values()) < 5 * min(blocks.values()) + 50, (
        f"the three aggregate rungs should be indistinguishable in block terms: {blocks}"
    )


def test_the_product_tells_an_agent_what_more_detail_would_cost(
    estate: None, modules: dict[str, Any], tmp_path: pathlib.Path,
) -> None:
    """*An agent that cannot see cost will always choose maximum detail.*

    Declared product gate `ABS-G15` (`CP-SPEC-016` §A.2, §G.1).
    """
    at_cohort = answer(modules, tmp_path / "c", principal=DESK, granularity="cohort")
    nxt = at_cohort.payload["assembly_cost"]["next_level_down"]
    assert nxt["granularity"] == "loan"
    assert "loan-scale" in nxt["consequence"], "the consequence of descending is named"

    at_loan = answer(modules, tmp_path / "l", principal=DESK, granularity="loan", loan_sample=10)
    assert at_loan.payload["assembly_cost"]["next_level_down"]["granularity"] == "", (
        "the finest granularity says so rather than naming a level that does not exist"
    )
