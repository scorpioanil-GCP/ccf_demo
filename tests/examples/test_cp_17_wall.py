"""The wall, in-process — `MWE-G01`, `MWE-G02`, `MWE-G04`, `MWE-G05`, `MWE-G08`, `MWE-G10`, `MWE-G13`, `MWE-G20`, `MWE-G21`.

What `examples/cp-17-mnpi-wall-enforcement` serves to three principals asking
the same question of the same issuer at the same instant, on the paved road
with an explicit `Perspective` (`CP-SPEC-017` §A.2, §D.3, §G.1). Every figure
is MEASURED against the live estate at run time; what this module writes down
are the relationships between figures — three addresses differ while the
class, the plan and the operator set do not; a walled identifier the banker
was served is absent from every byte of the analyst's and the trader's
vessels; the analyst's member set is the role's at two instants; the wall
opens on the assertion clock and not on the valid clock alone — never a
number restated.

**Reads the estate, seeds nothing** (CLAUDE.md §9). Nothing here pins an
estate count or a date as a fact; the instants come from
`artifacts/question.yaml` and are the demonstration's own.
"""

from __future__ import annotations

import os
import pathlib
import sys
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

import pytest
import yaml

from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.products.product import OpenedProduct
from ccf.products.request import ProductRequest
from ccf.projection.plan import Perspective
from ccf.replay.record import DecisionReplayRecord
from ccf.replay.serve import ServedProduct

pytestmark = [pytest.mark.fluree, pytest.mark.postgres, pytest.mark.mongo]

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE = REPO_ROOT / "examples" / "cp-17-mnpi-wall-enforcement"

ESTATE_VARIABLES = (
    "CCF_CP_17_SQLITE_PATH",
    "CCF_CP_17_POSTGRES_DSN", "CCF_CP_17_POSTGRES_SCHEMA",
    "CCF_CP_17_FLUREE_URL", "CCF_CP_17_FLUREE_LEDGER",
    "CCF_CP_17_MONGO_URI", "CCF_CP_17_MONGO_DB",
)
ESTATE_REQUIRED = "CCF_REQUIRE_ESTATE"
COLLIDING = ("acquisition", "deployment", "produce", "projection", "serve", "server")

#: The demonstration question and its pinned instants — the artifact's, never
#: this module's (`CP-SPEC-017` §C.5).
QUESTION: dict[str, Any] = yaml.safe_load((EXAMPLE / "artifacts" / "question.yaml").read_text(encoding="utf-8"))["declaration"]
SUBJECT: str = QUESTION["question"]["subject"]
INTENT: str = QUESTION["question"]["intent"]
FRESHNESS: str = QUESTION["question"]["freshness"]
INSTANTS: dict[str, datetime] = {name: datetime.fromisoformat(value) for name, value in QUESTION["instants"].items()}
CONFIG: dict[str, Any] = yaml.safe_load((EXAMPLE / "ccf_config.yaml").read_text(encoding="utf-8"))

#: The three entitled principals, by identity, and the role each asserts
#: (`CP-SPEC-017` §D.3 step 0); the estate's own register is checked against
#: this table before any question is asked.
BANKER = Perspective(principal_id="PRIN-COV-001", role="coverage-banker")
ANALYST = Perspective(principal_id="PRIN-RES-002", role="research-analyst")
TRADER = Perspective(principal_id="PRIN-TRD-003", role="trader")

#: The classification the wall keys, and the member that carries the event
#: (`artifacts/source-vocabulary.yaml`, `CP-SPEC-017` §D.6).
WALLED = "internal-restricted"
PUBLIC = "public-filed"
REG_FD_MEMBER = "reg_fd_disclosure"
ENGAGEMENT_MEMBERS = ("deal_engagements", "interactions")
MNPI_EDGE = "hasMnpiEngagement"
POLICY_OPERATOR = "policy.principal-subgraph"
CATEGORIES = frozenset({"policy", "similarity", "temporal", "traversal"})


# --- fixtures and helpers -----------------------------------------------------------


@pytest.fixture(scope="module")
def estate() -> None:
    """The CURATED estate, read-only, seeding nothing."""
    missing = [n for n in ESTATE_VARIABLES if not os.environ.get(n)]
    if missing:
        message = (
            f"the curated estate is not configured: {', '.join(missing)} unset."
            " Point them at the v2 namespaces — Fluree `fibo-v2`, PostgreSQL `ccf_v2`, MongoDB `fibo_v2`"
        )
        if os.environ.get(ESTATE_REQUIRED):
            pytest.fail(message)
        pytest.skip(message)


@contextmanager
def _tree_modules(tree: pathlib.Path) -> Iterator[dict[str, Any]]:
    """One example tree's modules, whatever ran before — evicted in and out."""
    saved = {n: sys.modules.pop(n, None) for n in COLLIDING}
    sys.path.insert(0, str(tree))
    try:
        import acquisition  # noqa: PLC0415
        import deployment  # noqa: PLC0415
        import produce  # noqa: PLC0415
        import projection  # noqa: PLC0415

        assert pathlib.Path(deployment.__file__).parent == tree, "the eviction did not hold"
        yield {"acquisition": acquisition, "deployment": deployment, "produce": produce, "projection": projection}
    finally:
        sys.path.remove(str(tree))
        for name in COLLIDING:
            sys.modules.pop(name, None)
            if saved[name] is not None:
                sys.modules[name] = saved[name]


@pytest.fixture(scope="module")
def modules() -> Iterator[dict[str, Any]]:
    with _tree_modules(EXAMPLE) as loaded:
        yield loaded


@dataclass(frozen=True)
class _Answer:
    """One served answer with its record, for the assertions below."""

    perspective: Perspective
    product: Any
    record: DecisionReplayRecord
    served: ServedProduct
    plan_row: Any


def _question(
    opened: OpenedProduct, deployment: Any, *, asked_at: datetime, known_as_of: str | None = None,
    debt_tolerance: str | None = None,
) -> ProductRequest:
    parameters: dict[str, Any] = {}
    if known_as_of is not None:
        parameters[deployment.KNOWN_AS_OF] = known_as_of
    if debt_tolerance is not None:
        parameters[deployment.DEBT_TOLERANCE] = debt_tolerance
    return opened.question(subject=SUBJECT, asked_at=asked_at, intent=INTENT, freshness=FRESHNESS, parameters=parameters)


def _plan_row(opened: OpenedProduct, modules: dict[str, Any], principal_id: str) -> Any:
    """The principal's own projection-plan row, read from the estate directly."""
    acquisition, deployment = modules["acquisition"], modules["deployment"]
    settings = opened.sources[deployment.SOURCE_RELATIONAL]
    relational = acquisition._Relational(dsn=settings["dsn"], schema=settings["schema"])
    table = acquisition.vocabulary()["relational"]["tables"]["projection_plan"]
    return acquisition.plan_for(relational, principal_id=principal_id, table=table)


def _answer(modules: dict[str, Any], scratch: pathlib.Path, *, perspective: Perspective, **question: Any) -> _Answer:
    """One question on the paved road, in its own scratch, as the stated principal."""
    with modules["produce"].product(scratch) as opened:
        roles = modules["acquisition"].principal_roles(relational_settings=opened.sources[modules["deployment"].SOURCE_RELATIONAL])
        assert roles.get(perspective.principal_id) == perspective.role, f"`{perspective.principal_id}` register mismatch"
        outcome = opened.answer(_question(opened, modules["deployment"], **question), perspective=perspective)
        assert isinstance(outcome, ServedProduct), getattr(outcome, "detail", outcome)
        return _Answer(
            perspective=perspective, product=outcome.product, record=opened.record_of(outcome), served=outcome,
            plan_row=_plan_row(opened, modules, perspective.principal_id),
        )


def _walled_identifiers(answer: _Answer) -> set[str]:
    """Every deal id and interaction id the banker was served under the walled classification."""
    payload = answer.product.payload
    deals = {item["deal_id"] for item in payload.get("deal_engagements", ()) if item["classification"] == WALLED}
    interactions = {item["interaction_id"] for item in payload.get("interactions", ()) if item["classification"] == WALLED}
    return deals | interactions


def _classifications(answer: _Answer, member: str) -> set[str]:
    return {item["classification"] for item in answer.product.payload.get(member) or ()}


def _factor(answer: _Answer, name: str) -> Decimal:
    return Decimal(str(getattr(answer.product.debt.factors, name)))


def _present_fraction(answer: _Answer, modules: dict[str, Any]) -> Decimal:
    """Required classes present ÷ required, computed from the served payload alone."""
    payload = answer.product.payload
    member_by_class = modules["projection"].MEMBER_BY_CLASS
    required = list(payload["plan"]["required_classes"])
    assert required, "the plan requires no class at all"
    present = 0
    for entity_class in required:
        if entity_class == "issuer":
            present += payload["issuer"] is not None
        else:
            present += bool(payload.get(member_by_class[entity_class]))
    return (Decimal(present) / Decimal(len(required))).quantize(Decimal("0.0001"))


@pytest.fixture(scope="module")
def banker(estate: None, modules: dict[str, Any], tmp_path_factory: pytest.TempPathFactory) -> _Answer:
    """The coverage banker at `T1`, over the wall."""
    return _answer(modules, tmp_path_factory.mktemp("banker"), perspective=BANKER, asked_at=INSTANTS["T1"])


@pytest.fixture(scope="module")
def analyst(estate: None, modules: dict[str, Any], tmp_path_factory: pytest.TempPathFactory) -> _Answer:
    """The research analyst at `T1`, on the public side."""
    return _answer(modules, tmp_path_factory.mktemp("analyst"), perspective=ANALYST, asked_at=INSTANTS["T1"])


@pytest.fixture(scope="module")
def trader(estate: None, modules: dict[str, Any], tmp_path_factory: pytest.TempPathFactory) -> _Answer:
    """The trader at `T1`, on the public side."""
    return _answer(modules, tmp_path_factory.mktemp("trader"), perspective=TRADER, asked_at=INSTANTS["T1"])


@pytest.fixture(scope="module")
def analyst_t0(estate: None, modules: dict[str, Any], tmp_path_factory: pytest.TempPathFactory) -> _Answer:
    """The research analyst at `T0`, before the Reg FD event."""
    return _answer(modules, tmp_path_factory.mktemp("analyst-t0"), perspective=ANALYST, asked_at=INSTANTS["T0"])


@pytest.fixture(scope="module")
def analyst_before_mnpi(estate: None, modules: dict[str, Any], tmp_path_factory: pytest.TempPathFactory) -> _Answer:
    """The research analyst at an instant before any of the issuer's MNPI-bearing records existed."""
    return _answer(modules, tmp_path_factory.mktemp("analyst-before"), perspective=ANALYST, asked_at=INSTANTS["before_any_mnpi_record"])


@pytest.fixture(scope="module")
def banker_tw(estate: None, modules: dict[str, Any], tmp_path_factory: pytest.TempPathFactory) -> _Answer:
    """The banker at `TW`, `known_as_of` omitted — inside the crossing's recording lag."""
    return _answer(modules, tmp_path_factory.mktemp("banker-tw"), perspective=BANKER, asked_at=INSTANTS["TW"])


@pytest.fixture(scope="module")
def banker_tw_known_later(estate: None, modules: dict[str, Any], tmp_path_factory: pytest.TempPathFactory) -> _Answer:
    """The banker at `TW`, re-asked with the control room's later knowledge."""
    return _answer(
        modules, tmp_path_factory.mktemp("banker-tw-later"), perspective=BANKER, asked_at=INSTANTS["TW"],
        known_as_of=INSTANTS["TW_known_later"].isoformat(),
    )


# --- G01: three credentials, one question, one instant --------------------------------


def test_three_principals_get_three_addresses_under_one_class_plan_and_operator_set(
    banker: _Answer, analyst: _Answer, trader: _Answer,
) -> None:
    """Three credentials asking the same question of the same issuer at the
    same instant are served three distinct content addresses, while the
    schema, the `plan_id` and the operator set are one — the product differs
    by credential, never by a parameter.

    Declared product gate `MWE-G01` (`CP-SPEC-017` §G.1).
    """
    answers = (banker, analyst, trader)
    addresses = {content_hash(answer.product) for answer in answers}
    assert len(addresses) == len(answers), "the three vessels share an address"
    for answer in answers:
        assert content_hash(answer.product) == answer.record.content_generation_path.product_content_address
    schemas = {(answer.product.schema_name, answer.product.schema_version) for answer in answers}
    plans = {answer.product.plan_id for answer in answers}
    operator_sets = {frozenset(answer.product.lineage.operators_invoked) for answer in answers}
    assert len(schemas) == 1 and len(plans) == 1 and len(operator_sets) == 1
    assert next(iter(operator_sets)) == frozenset(CONFIG["product_class"]["required_operator_keys"])


# --- G02: classification containment ----------------------------------------------------


def test_no_served_classification_escapes_the_principal_envelope_and_no_mnpi_identifier_crosses(
    banker: _Answer, analyst: _Answer, trader: _Answer, modules: dict[str, Any],
) -> None:
    """Every classification a bounded member carries is inside the served
    principal's own `permitted_classifications`, and no identifier of an
    MNPI-bearing deal or interaction the banker was served appears in any
    byte of the analyst's or the trader's vessel — payload, lineage or debt.

    Declared product gate `MWE-G02` (`CP-SPEC-017` §G.1).
    """
    bounded = modules["projection"].CLASSIFICATION_BOUNDED_MEMBERS
    for answer in (banker, analyst, trader):
        permitted = set(answer.product.payload["plan"]["permitted_classifications"])
        for member in bounded:
            assert _classifications(answer, member) <= permitted, f"`{member}` escapes the envelope"
    walled = _walled_identifiers(banker)
    assert walled, "the banker was served nothing walled"
    assert WALLED not in set(analyst.product.payload["plan"]["permitted_classifications"])
    assert WALLED not in set(trader.product.payload["plan"]["permitted_classifications"])
    for public_side in (analyst, trader):
        vessel = canonical_bytes(public_side.product)
        record = canonical_bytes(public_side.record)
        for identifier in walled:
            assert identifier.encode("utf-8") not in vessel, f"`{identifier}` crossed the wall"
            assert identifier.encode("utf-8") not in record, f"`{identifier}` in the record"


# --- G04: no disclosure — the shape is the role's ----------------------------------------


def test_the_analyst_member_set_is_the_role_declared_shape_at_both_instants(
    analyst: _Answer, analyst_before_mnpi: _Answer, modules: dict[str, Any],
) -> None:
    """The analyst's payload member set on the demonstration issuer at `T1`
    equals its member set at an instant before any MNPI-bearing record of
    that issuer existed, and both equal the shape `artifacts/perspectives.yaml`
    declares for the role — a function of the role, never of the subject.

    Declared product gate `MWE-G04` (`CP-SPEC-017` §G.1).
    """
    declared = modules["projection"].members_for(ANALYST.role)
    at_t1 = set(analyst.product.payload)
    before = set(analyst_before_mnpi.product.payload)
    assert at_t1 == before == declared, sorted(at_t1 ^ before ^ declared)
    assert not set(ENGAGEMENT_MEMBERS) & declared, "an engagement member is in the analyst's shape"
    assert analyst.product.payload["role"] == analyst_before_mnpi.product.payload["role"] == ANALYST.role


# --- G05: policy first ----------------------------------------------------------------------


def test_the_served_plan_runs_policy_first_and_invokes_all_four_categories(
    banker: _Answer, analyst: _Answer, trader: _Answer,
) -> None:
    """Every served record's operator plan lists `policy.principal-subgraph`
    first, ahead of similarity, temporal and traversal, and all four
    categories are invoked and recorded step for step.

    Declared product gate `MWE-G05` (`CP-SPEC-017` §G.1).
    """
    for answer in (banker, analyst, trader):
        path = answer.record.content_generation_path
        assert path.operator_plan, "the record carries no operator plan"
        assert path.operator_plan[0] == POLICY_OPERATOR
        assert {key.split(".", 1)[0] for key in path.operator_plan} == CATEGORIES
        assert tuple(step.operator_key for step in path.steps) == path.operator_plan
        assert frozenset(path.operator_plan) == frozenset(answer.product.lineage.operators_invoked)


# --- G08: the bitemporal wall -----------------------------------------------------------


def test_the_wall_opens_on_the_assertion_clock_not_the_valid_clock_alone(
    banker_tw: _Answer, banker_tw_known_later: _Answer,
) -> None:
    """Inside the crossing's recording lag the banker asking at `TW` with
    `known_as_of` defaulted is served no `hasMnpiEngagement` edge and no
    walled item; the same question with `known_as_of` after the crossing was
    asserted serves both — and the two vessels have different addresses.

    Declared product gate `MWE-G08` (`CP-SPEC-017` §G.1).
    """
    unaware, aware = banker_tw.product.payload, banker_tw_known_later.product.payload
    assert unaware["known_as_of"] != aware["known_as_of"]
    assert MNPI_EDGE not in unaware["edge_types_served"]
    assert MNPI_EDGE in aware["edge_types_served"]
    assert not {WALLED} & (_classifications(banker_tw, "deal_engagements") | _classifications(banker_tw, "interactions"))
    assert WALLED in _classifications(banker_tw_known_later, "deal_engagements")
    assert content_hash(banker_tw.product) != content_hash(banker_tw_known_later.product)
    assert {item["deal_id"] for item in unaware["deal_engagements"]} < {item["deal_id"] for item in aware["deal_engagements"]}


# --- G10: Reg FD as a member change ----------------------------------------------------------


def test_reg_fd_is_a_dated_member_on_the_issuer_and_admits_no_engagement_content(
    analyst_t0: _Answer, analyst: _Answer, banker: _Answer,
) -> None:
    """For the analyst the issuer's `reg_fd_disclosure` member is null at `T0`
    and carries the event as a public-filed mapping at `T1`; outside the
    dated members the two vessels agree, and no engagement content — no
    engagement member, no walled identifier — is admitted on the strength of
    the label at either instant.

    Declared product gate `MWE-G10` (`CP-SPEC-017` §G.1).
    """
    before, after = analyst_t0.product.payload, analyst.product.payload
    assert before["issuer"][REG_FD_MEMBER] is None
    event = after["issuer"][REG_FD_MEMBER]
    assert isinstance(event, Mapping) and event["classification"] == PUBLIC and event["event_id"]
    undated = ("role", "plan", "family")
    for member in undated:
        assert before[member] == after[member], f"`{member}` moved between instants"
    issuer_before = {k: v for k, v in before["issuer"].items() if k != REG_FD_MEMBER}
    issuer_after = {k: v for k, v in after["issuer"].items() if k != REG_FD_MEMBER}
    assert issuer_before == issuer_after
    walled = _walled_identifiers(banker)
    assert walled, "the banker was served nothing walled"
    for answer in (analyst_t0, analyst):
        assert not set(ENGAGEMENT_MEMBERS) & set(answer.product.payload)
        vessel = canonical_bytes(answer.product)
        assert all(identifier.encode("utf-8") not in vessel for identifier in walled)


# --- G13: one plan, three roles ----------------------------------------------------------------


def test_one_plan_id_three_roles_and_the_principal_own_plan_version_is_served(
    banker: _Answer, analyst: _Answer, trader: _Answer,
) -> None:
    """Dimension 5 `plan_id` is equal across the three records and dimension 4
    `role` is distinct; the plan member each principal is served carries its
    OWN projection-plan row — id and version equal to the estate's row for
    that principal, and no other principal's.

    Declared product gate `MWE-G13` (`CP-SPEC-017` §G.1).
    """
    answers = (banker, analyst, trader)
    assert len({answer.record.content_generation_path.plan_id for answer in answers}) == 1
    assert {answer.record.perspective_conditioning.role for answer in answers} == {a.perspective.role for a in answers}
    assert len({answer.record.perspective_conditioning.role for answer in answers}) == len(answers)
    served_plans = {}
    for answer in answers:
        assert answer.record.perspective_conditioning.principal_id == answer.perspective.principal_id
        plan = answer.product.payload["plan"]
        assert answer.plan_row is not None, f"`{answer.perspective.principal_id}` has no plan row"
        assert (plan["plan_id"], plan["plan_version"]) == (answer.plan_row.plan_id, answer.plan_row.plan_version)
        assert plan["plan_version"], "the served plan carries no version"
        served_plans[answer.perspective.principal_id] = plan["plan_id"]
    assert len(set(served_plans.values())) == len(answers), "two principals were served one plan"


# --- G20: debt is entitlement-neutral ----------------------------------------------------------


def test_the_analyst_completeness_is_measured_over_its_own_required_classes(
    analyst: _Answer, banker: _Answer, modules: dict[str, Any],
) -> None:
    """The analyst's `C_required` excludes the engagement classes the banker
    requires, so its completeness equals the fraction of its OWN required
    classes present in its payload — the MNPI it may not see raises no debt.

    Declared product gate `MWE-G20` (`CP-SPEC-017` §G.1).
    """
    analyst_required = set(analyst.product.payload["plan"]["required_classes"])
    banker_required = set(banker.product.payload["plan"]["required_classes"])
    withheld_classes = {modules["projection"].CLASS_BY_MEMBER[member] for member in ENGAGEMENT_MEMBERS}
    assert withheld_classes <= banker_required, "the banker does not require the engagement classes"
    assert not withheld_classes & analyst_required, "a withheld class is in `C_required`"
    assert _factor(analyst, "completeness") == _present_fraction(analyst, modules)
    assert _factor(banker, "completeness") == _present_fraction(banker, modules)
    assert _factor(analyst, "completeness") == Decimal(1)
    assert Decimal(str(analyst.product.debt.debt)) <= Decimal(str(banker.product.debt.debt))


# --- G21: the Policy Blind control --------------------------------------------------------------


def test_the_policy_blind_control_differs_from_the_served_analyst_vessel(
    banker: _Answer, analyst: _Answer, modules: dict[str, Any],
) -> None:
    """A display filter — the banker's served payload re-cut to the analyst's
    member set, engagement members dropped and `research` supplied from
    nowhere — differs from the analyst's real served payload, whose
    `research` member is populated from the analyst's own governed fabric.

    Declared product gate `MWE-G21` (`CP-SPEC-017` §G.1).
    """
    projection = modules["projection"]
    shape = projection.members_for(ANALYST.role)
    source = banker.product.payload
    blind: dict[str, Any] = {member: source[member] for member in shape if member in source}
    for member in shape - set(blind):
        blind[member] = []
    blind["role"] = ANALYST.role
    assert set(blind) == set(analyst.product.payload) == shape
    assert canonical_bytes(blind) != canonical_bytes(dict(analyst.product.payload))
    assert analyst.product.payload["research"] and not blind["research"]
    assert blind["plan"]["plan_id"] != analyst.product.payload["plan"]["plan_id"]
    assert content_hash(blind) != content_hash(dict(analyst.product.payload))
