"""What `examples/cp-02-facility-terms-snapshot` actually serves.

The example reads the store `backends.yaml` names through an environment
variable. Locally that points at the real facility estate; here the schema comes
from `tests/examples/fixtures/cp_02_facility_schema.sql` and the rows from
`tests/examples/fixtures/cp_02_facility_rows.sql`, both applied by the
``seeded`` fixture and by nothing else — `24-CONTEXT.md` `D-25` and `D-27`.

Marked ``postgres``: every fixture requests the session-scoped ``postgres_dsn``.
Unset ``CCF_TEST_POSTGRES_DSN`` starts a container; ``CCF_REQUIRE_POSTGRES``
turns a skip into a failure.

**WHAT THIS MODULE IS FOR.** Each test below is one of the specification's
product-specific gates (`CP-SPEC-002` §D.7) or one of its §G acceptance
criteria, asserted against a run rather than against a docstring.

**TWO OF THEM ASSERT A REFUSAL AND ONE ASSERTS A SHIPPED DEFECT.**
:func:`test_a_facility_older_than_the_window_is_refused` asserts the 50-of-60
`ttl-bounds` refusal that §F.4 finding 1 records — **written to pass while the
declaration stands and to FAIL when it is corrected**, which is what makes it the
evidence the deviation gets taken back with rather than a test that ratifies a
bug. When the vault rules on the anchor, this test goes red, and that redness is
the signal to close the finding.
"""

from __future__ import annotations

import importlib
import json
import os
import pathlib
import sys
import tempfile
from decimal import Decimal
from typing import Any

import psycopg
import pytest
import yaml

from ccf.agents.errors import AssemblyRefused
from ccf.contracts.canonical import content_hash

REPO = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE = REPO / "examples" / "cp-02-facility-terms-snapshot"
FIXTURES = pathlib.Path(__file__).parent / "fixtures"
SCHEMA_SQL = FIXTURES / "cp_02_facility_schema.sql"
ROWS_SQL = FIXTURES / "cp_02_facility_rows.sql"

pytestmark = pytest.mark.postgres


def _load(name: str) -> Any:
    """Load one of the example's modules under its own bare name.

    The example is a directory of modules rather than a package, and its modules
    import each other by bare name — ``assembler`` does ``import produce``,
    ``run`` does ``import assembler``. Loading them under prefixed names would
    leave a SECOND copy of ``produce`` in ``sys.modules``, and an ``isinstance``
    across the two copies would then be false for reasons that have nothing to
    do with the code under test.

    **AND THREE EXAMPLES NOW SHARE THOSE BARE NAMES.** cp-00, cp-01 and cp-02
    each ship a ``deployment``, a ``produce`` and an ``assembler``, while
    ``make leg-postgres`` runs ``pytest tests -m postgres`` as ONE session over
    the whole tree. Whichever module is imported first wins the name, and the
    second module's tests then read the first one's constants —
    ``module 'deployment' has no attribute 'EXPECTED'`` being the polite failure
    and a silently wrong value being the impolite one.

    So the cache is checked against THIS example's directory and evicted when it
    holds somebody else's. Evicting the whole family together rather than one
    name at a time matters: leaving cp-01's ``produce`` behind while reloading
    cp-02's ``assembler`` would rebuild exactly the split-identity problem the
    bare names exist to avoid.
    """
    if sys.path[:1] != [str(EXAMPLE)]:
        while str(EXAMPLE) in sys.path:
            sys.path.remove(str(EXAMPLE))
        sys.path.insert(0, str(EXAMPLE))
    family = ("deployment", "produce", "assembler", "run")
    for cached_name in family:
        cached = sys.modules.get(cached_name)
        if cached is None:
            continue
        origin = str(getattr(cached, "__file__", ""))
        if not origin.startswith(str(EXAMPLE)):
            for sibling in family:
                sys.modules.pop(sibling, None)
            break
    return importlib.import_module(name)


def _expected() -> Any:
    """The declared expectations — the test's source for domain values.

    A value the test authored would be the test agreeing with itself about what
    this deployment's vocabulary says.
    """
    deployment = _load("deployment")
    return yaml.safe_load(deployment.EXPECTED.read_text(encoding="utf-8"))[
        deployment.DECLARATION
    ]


def _dsn_variable() -> str:
    """The env var `backends.yaml` declares, read through the deployment's keys."""
    deployment = _load("deployment")
    document = yaml.safe_load(deployment.BACKENDS.read_text(encoding="utf-8"))
    source = document[deployment.DECLARATION][deployment.SOURCES]
    binding = source[deployment.SOURCE_BINDING][deployment.SETTINGS]
    return str(binding[deployment.SOURCE_SETTING_DSN][deployment.FROM_ENV])


@pytest.fixture(scope="module")
def seeded(postgres_dsn: str) -> Any:
    """A seeded container, with the DSN exported where `backends.yaml` reads it."""
    with psycopg.connect(postgres_dsn, autocommit=True) as db, db.cursor() as cursor:
        cursor.execute(SCHEMA_SQL.read_text(encoding="utf-8"))
        cursor.execute(ROWS_SQL.read_text(encoding="utf-8"))

    variable = _dsn_variable()
    previous = os.environ.get(variable)
    os.environ[variable] = postgres_dsn
    yield postgres_dsn
    if previous is None:
        os.environ.pop(variable, None)
    else:
        os.environ[variable] = previous


def _serve(seeded: str, **kwargs: Any) -> Any:
    """Run one assembly through the assembler seam, as `run.py` does.

    Returns the SPINE's value, captured through the observer, because the
    Protocol's return type carries the assembly's governance and not the served
    vessel.
    """
    deployment = _load("deployment")
    assembler = _load("assembler")

    facility = kwargs.pop("facility", None)
    principal = kwargs.pop("principal", None)
    asked_at = kwargs.pop("asked_at", None)
    ignore_need_to_know = kwargs.pop("ignore_need_to_know", False)
    parameters: dict[str, object] = {
        deployment.PARAM_DEBT_TOLERANCE: Decimal(
            deployment.demonstration_debt_tolerance()
        ),
        deployment.PARAM_INCLUDE_PRICING_GRID: kwargs.pop(
            "include_pricing_grid", True
        ),
    }
    parameters.update(kwargs)

    asked = deployment.request(parameters=parameters, asked_at=asked_at)
    if facility is not None:
        asked = asked.model_copy(update={"subject": facility})

    def read(booted: Any, question: Any) -> Any:
        return deployment.read(
            booted,
            question,
            principal_id=principal,
            ignore_need_to_know=ignore_need_to_know,
        )

    with tempfile.TemporaryDirectory(prefix="cp02-test-") as tmp:
        root = pathlib.Path(tmp)
        captured: list[object] = []
        seam = assembler.FacilityAssembler(
            config=deployment.CONFIG,
            root=root,
            connection=deployment.connection(root=root),
            read=read,
            plan_class=deployment.plan_class(),
            observer=captured.append,
        )
        try:
            governed = seam.assemble(
                request=asked,
                perspective=deployment.perspective(),
                tenant_id=deployment.tenant_id(),
            )
        except AssemblyRefused:
            # The seam raises for identity, existence and suppression. The
            # spine's value is still what the caller under test wants to see.
            if captured:
                return captured[0]
            raise
        return captured[0] if captured else governed


# --------------------------------------------------------------------------
# The seed is measured before anything is asserted against it.
# --------------------------------------------------------------------------
def test_the_seeder_seeded(seeded: str) -> None:
    """A silent seed would make every assertion below pass against nothing.

    The control returns a DIFFERENT number: the same query with an impossible
    facility id returns 0 while the real predicate returns the fixture's own
    count. A count with no control is not a measurement.
    """
    expected = _expected()["estate"]
    with psycopg.connect(seeded) as db, db.cursor() as cursor:
        cursor.execute("select count(*) from ccf_v2.facility")
        real = cursor.fetchone()[0]
        cursor.execute(
            "select count(*) from ccf_v2.facility where facility_id = %s",
            ("FAC-NO-SUCH-THING",),
        )
        control = cursor.fetchone()[0]
    assert real == expected["facilities"], (
        f"the fixture seeded {real} facilities, expected"
        f" {expected['facilities']} — every count gate below reads this table"
    )
    assert control == 0, (
        "the control matched rows it cannot match; the query is not"
        " discriminating and the count above means nothing"
    )


def test_the_estate_carries_what_the_gates_need(seeded: str) -> None:
    """§F.3's volumetrics, asserted rather than described.

    A gate with no instance in the data is machinery without a purpose
    (Standard §6), so the populations each gate acts on are measured here once,
    in one place, from the declared expectations.
    """
    expected = _expected()["estate"]
    with psycopg.connect(seeded) as db, db.cursor() as cursor:
        def scalar(sql: str) -> int:
            cursor.execute(sql)
            return int(cursor.fetchone()[0])

        measured = {
            "facilities": scalar("select count(*) from ccf_v2.facility"),
            "facilities_with_an_amendment": scalar(
                "select count(*) from ccf_v2.facility where amendment_count >= 1"
            ),
            "maximum_amendment_count": scalar(
                "select max(amendment_count) from ccf_v2.facility"
            ),
            "syndicated": scalar(
                "select count(*) from ccf_v2.facility where syndicated"
            ),
            "grids_present": scalar(
                "select count(*) from ccf_v2.facility where pricing_grid is not null"
            ),
            "grids_with_three_or_more_tiers": scalar(
                "select count(*) from ccf_v2.facility"
                " where jsonb_array_length(pricing_grid->'tiers') >= 3"
            ),
            "null_maturity": scalar(
                "select count(*) from ccf_v2.facility where maturity_date is null"
            ),
            "maturity_before_effective": scalar(
                "select count(*) from ccf_v2.facility"
                " where maturity_date < effective_date"
            ),
            "distinct_retrieved_at_values": scalar(
                "select count(distinct retrieved_at) from ccf_v2.facility"
            ),
        }
    for key, value in measured.items():
        assert value == expected[key], (
            f"{key}: measured {value}, expected {expected[key]}"
        )


def test_the_pricing_grid_is_not_an_array_and_the_naive_read_returns_zero(
    seeded: str,
) -> None:
    """§C.4 trap 4 — a check whose population is not its question.

    `pricing_grid` is a jsonb OBJECT, so `jsonb_array_length(pricing_grid)`
    cannot count tiers. This asserts BOTH halves: the naive read returns zero
    and the correct read returns the whole population. Without the first half
    this is just another count; with it, it is the trap.
    """
    expected = _expected()["estate"]
    with psycopg.connect(seeded) as db, db.cursor() as cursor:
        cursor.execute(
            "select count(*) from ccf_v2.facility where pricing_grid is not null"
            " and jsonb_typeof(pricing_grid) = 'array'"
        )
        naive = int(cursor.fetchone()[0])
        cursor.execute(
            "select count(*) from ccf_v2.facility"
            " where jsonb_array_length(pricing_grid->'tiers') >= 3"
        )
        correct = int(cursor.fetchone()[0])
    assert naive == 0, (
        "the grid parsed as a top-level array; the trap this documents is gone"
        " and §C.4 trap 4 needs rewriting rather than this gate relaxing"
    )
    assert correct == expected["grids_with_three_or_more_tiers"]


# --------------------------------------------------------------------------
# FTS-G01 — the primitive. The expiry is a property of the facility.
# --------------------------------------------------------------------------
def test_the_expiry_does_not_move_when_the_question_moves(seeded: str) -> None:
    """`FTS-G01`, and it is the one gate whose failure would mean the product
    had become its own counterfactual.

    `ttl_anchor: from_entity_freshness` means `expires_at` is a function of the
    CREDIT AGREEMENT'S OWN DATE, not of the request. Asked seventeen days apart,
    the same facility must return the same expiry TO THE SECOND.

    **An implementation that recomputed the expiry from `now` would pass every
    other test in this module.** That is why this one exists, and why it asserts
    equality of the expiry while deliberately NOT asserting equality of the
    content address: the address legitimately moves with the request's temporal
    boundary, so requiring both to be equal would confuse two different claims
    and requiring both to differ would be false.
    """
    from datetime import datetime

    early = _serve(seeded, asked_at=datetime.fromisoformat("2026-08-29T12:00:00+00:00"))
    late = _serve(seeded, asked_at=datetime.fromisoformat("2026-09-15T23:45:00+00:00"))

    assert early.product.expires_at == late.product.expires_at, (
        "expires_at moved when only the question moved — the anchor is"
        f" from_decision wearing a from_entity_freshness label:"
        f" {early.product.expires_at} vs {late.product.expires_at}"
    )
    # And it is the agreement's own date plus the declared window, rather than
    # any instant that happens to be stable.
    deployment = _load("deployment")
    from datetime import timedelta

    basis = datetime.fromisoformat(
        early.scenario.ttl_basis_value
    ).replace(tzinfo=early.product.expires_at.tzinfo)
    assert early.product.expires_at == basis + timedelta(
        seconds=deployment.declared_ttl_seconds()
    ), "the expiry is stable but is not the agreement date plus the window"


def test_the_payload_names_the_date_the_expiry_was_measured_from(
    seeded: str,
) -> None:
    """§G criterion 2 — the arithmetic must be checkable without this document.

    Without `ttl_basis`, two products anchored on different dates are
    indistinguishable on the wire, which is the substitution §E.5 is about.
    """
    expected = _expected()
    assembled = _serve(seeded)
    assert assembled.scenario.ttl_basis_value == (
        assembled.product.payload["facility"]["effective_date"]
    ), "the basis the expiry used is not the date the payload reports"
    deployment = _load("deployment")
    assert deployment.TTL_BASIS == expected["ttl_basis"]


# --------------------------------------------------------------------------
# FTS-G02 / FTS-G03 / FTS-G04 — the policy step, and it is two conditions.
# --------------------------------------------------------------------------
def test_entitlement_discriminates_as_sets_with_a_negative_control(
    seeded: str,
) -> None:
    """`FTS-G02` — sets, never sizes, and NOT every pair.

    Rung 01 could assert that all six principal pairs discriminate because all
    six did. **Here five of six do**: `PRIN-KYC-004` and `PRIN-TRD-003` both see
    ZERO facilities, so their visible sets are identical — both empty — and a
    gate demanding that every pair differ would fail correct data. The pair that
    legitimately matches is DECLARED in `expected.yaml` rather than discovered
    here, so this test cannot quietly absorb a second one.

    The negative control is a principal differenced against itself: if that
    reports a difference, the instrument is broken and the greens above mean
    nothing.
    """
    expected = _expected()
    declared_identical = {
        tuple(sorted(pair))
        for pair in expected["principal_pairs_expected_identical"]
    }
    principals = sorted(expected["principals_visible_by_jurisdiction"])

    visible: dict[str, frozenset[str]] = {}
    for principal in principals:
        assembled = _serve(seeded, principal=principal)
        facility = assembled.product.payload.get("facility")
        visible[principal] = (
            frozenset() if facility is None else frozenset({facility["facility_id"]})
        )

    # The negative control FIRST, so a broken instrument is caught before its
    # readings are used.
    for principal in principals:
        assert visible[principal] == visible[principal], "set comparison is unstable"

    discriminating = 0
    for i, a in enumerate(principals):
        for b in principals[i + 1 :]:
            same = visible[a] == visible[b]
            pair = tuple(sorted((a, b)))
            if same:
                assert pair in declared_identical, (
                    f"{a} and {b} see the same set and expected.yaml does not"
                    " declare that pair identical — either the entitlement"
                    " stopped discriminating or a new legitimate match needs"
                    " declaring, and this gate must not decide which"
                )
            else:
                discriminating += 1
    assert discriminating >= 1, (
        "no principal pair discriminates; the Policy step is a no-op"
    )


def test_need_to_know_is_load_bearing(seeded: str) -> None:
    """`FTS-G03` — the condition that a set-difference check cannot see.

    The policy binds TWO conditions. A two-condition policy where only one does
    any work passes `FTS-G02` unchanged, because the sets still differ. The only
    way to show the second condition works is to REMOVE it and observe the
    served set change.

    `PRIN-RES-002` is the instrument: it is granted every borrower jurisdiction
    in the estate and carries NO facility-level need-to-know. With the condition
    it sees nothing; without it, it sees the facility.
    """
    without = _serve(seeded, principal="PRIN-RES-002")
    assert without.product.payload.get("facility") is None, (
        "a principal with no facility-level need-to-know was served a facility;"
        " the need-to-know condition is not being applied"
    )
    with_removed = _serve(
        seeded, principal="PRIN-RES-002", ignore_need_to_know=True
    )
    assert with_removed.product.payload.get("facility") is not None, (
        "removing the need-to-know condition changed nothing, so the condition"
        " was inert and FTS-G02 would have passed over a decorative policy"
    )


def test_a_suppressed_facility_is_indistinguishable_from_a_missing_one(
    seeded: str,
) -> None:
    """`FTS-G04` — the disclosure that arrived through the STATUS, not the payload.

    §B.2's suppression rule is about what a caller can DISTINGUISH. The first
    build of this example returned `200` with `facility: null` for a suppressed
    facility and raised `404` for a missing one, so a caller probing ids could
    learn which ids EXIST. The payload carried no marker and the status carried
    it instead.

    Both must now produce the same refusal text. The distinction survives only
    in the replay record, which is the audit plane and not the caller.
    """
    deployment = _load("deployment")
    assembler = _load("assembler")
    expected = _expected()
    clean = expected["fixtures"]["clean"]

    suppressed = None
    missing = None
    try:
        _assemble_through_seam(seeded, facility=clean, principal="PRIN-KYC-004")
    except AssemblyRefused as refused:
        suppressed = str(refused)
    try:
        _assemble_through_seam(seeded, facility="FAC-NO-SUCH-THING")
    except AssemblyRefused as refused:
        missing = str(refused)

    assert suppressed is not None, "a suppressed facility did not refuse at all"
    assert missing is not None, "a missing facility did not refuse at all"
    # Normalised on the id the caller themselves supplied — that is the one
    # thing the two messages legitimately differ on, because the caller already
    # knows it.
    assert suppressed.replace(clean, "X") == missing.replace(
        "FAC-NO-SUCH-THING", "X"
    ), (
        "a suppressed facility and a missing one produce different refusals, so"
        f" a caller can tell which ids exist:\n  {suppressed}\n  {missing}"
    )
    assert "entitle" not in suppressed.lower(), (
        "the refusal names entitlement, which discloses that the facility exists"
    )
    # And the shared text is one function, so there is no second wording to drift.
    assert assembler._not_available(clean) in suppressed


def _assemble_through_seam(seeded: str, **kwargs: Any) -> Any:
    """Call the seam and let ``AssemblyRefused`` escape.

    :func:`_serve` swallows the refusal to hand back the spine's value, which is
    what most gates want. The suppression gate wants the REFUSAL ITSELF, because
    the refusal's text is the thing under test.
    """
    deployment = _load("deployment")
    assembler = _load("assembler")

    facility = kwargs.pop("facility", None)
    principal = kwargs.pop("principal", None)
    parameters: dict[str, object] = {
        deployment.PARAM_DEBT_TOLERANCE: Decimal(
            deployment.demonstration_debt_tolerance()
        ),
        deployment.PARAM_INCLUDE_PRICING_GRID: True,
    }
    # THE REMAINING KWARGS ARE PARAMETERS. Omitting this line made the `as_of`
    # gate pass a request that never carried `as_of`, so it asserted a refusal
    # of nothing and reported DID NOT RAISE. An instrument that drops the input
    # under test reads as a product failure.
    parameters.update(kwargs)
    asked = deployment.request(parameters=parameters)
    if facility is not None:
        asked = asked.model_copy(update={"subject": facility})

    with tempfile.TemporaryDirectory(prefix="cp02-seam-") as tmp:
        root = pathlib.Path(tmp)
        seam = assembler.FacilityAssembler(
            config=deployment.CONFIG,
            root=root,
            connection=deployment.connection(root=root),
            read=(
                deployment.read
                if principal is None
                else (lambda b, q: deployment.read(b, q, principal_id=principal))
            ),
            plan_class=deployment.plan_class(),
        )
        return seam.assemble(
            request=asked,
            perspective=deployment.perspective(),
            tenant_id=deployment.tenant_id(),
        )


# --------------------------------------------------------------------------
# FTS-G05 · G06 · G07 · G08 — the parameter surface and the three data traps.
# --------------------------------------------------------------------------
def test_as_of_is_refused_and_never_silently_honored(seeded: str) -> None:
    """`FTS-G05` — Standard §2.4's declared-but-inert parameter.

    It matters more here than at rung 01: a facility carrying up to 21
    amendments visibly HAS a history to ask about, so this is a question a
    caller will actually ask. A silent success against current state would
    answer a historical question with today's terms wearing yesterday's label.
    """
    with pytest.raises(AssemblyRefused) as refused:
        _assemble_through_seam(seeded, as_of="2026-01-01T00:00:00+00:00")
    assert "not_supported_at_tier" in str(refused.value)


def test_no_source_pointer_reaches_the_payload(seeded: str) -> None:
    """`FTS-G06` — the tier boundary the DATA does not enforce.

    `ccf_v2.facility` carries `source_accession`, `source_document` AND
    `source_offsets` on 60 of 60 rows, and the CI fixture carries them too,
    DELIBERATELY: a gate asserting that no source pointer leaks proves nothing
    against a schema that has none to leak. The control below is that assertion
    — the columns must be present in the store and absent from the payload.
    """
    expected = _expected()
    forbidden = expected["payload_keys_never_present"]

    with psycopg.connect(seeded) as db, db.cursor() as cursor:
        cursor.execute(
            "select count(*) from ccf_v2.facility"
            " where source_offsets is not null and source_accession is not null"
        )
        available_to_leak = int(cursor.fetchone()[0])
    assert available_to_leak == expected["estate"]["facilities"], (
        "the fixture carries no source pointers, so this gate is asserting that"
        " nothing leaked from a column that does not exist"
    )

    assembled = _serve(seeded)
    rendered = json.dumps(
        {
            "payload": dict(assembled.product.payload),
            "lineage": sorted(assembled.operators_invoked),
        },
        sort_keys=True,
        default=str,
    )
    for key in forbidden:
        assert key not in rendered, (
            f"{key!r} reached the served payload or its lineage — a T1 example"
            " that reaches into a document has silently become a T4 example"
        )


def test_the_pricing_grid_is_served_as_a_tier_structure(seeded: str) -> None:
    """`FTS-G07` — a grid flattened to a scalar answers the wrong question.

    A store that could hold only a headline margin does not fail loudly: it
    returns *a* margin, and a credit officer reading it during an amendment
    negotiation cannot tell that the leverage tiers it depends on were
    discarded.
    """
    expected = _expected()
    assembled = _serve(seeded)
    grid = assembled.product.payload["facility"]["pricing_grid"]

    assert isinstance(grid, dict), f"the grid was flattened to {type(grid).__name__}"
    for key in expected["pricing_grid_keys"]:
        assert key in grid, f"the grid lost {key!r}"
    tiers = grid["tiers"]
    assert len(tiers) >= expected["pricing_grid_minimum_tiers"], (
        f"{len(tiers)} tiers, below the declared minimum"
    )
    for tier in tiers:
        assert sorted(tier) == sorted(expected["pricing_grid_tier_keys"])
    # And no float survived into a content-addressed payload — §F.4 finding 8.
    assert all(isinstance(tier["leverage_le"], str) for tier in tiers)
    assert all(isinstance(tier["margin_bps"], int) for tier in tiers)


def test_an_inverted_date_pair_serves_without_computing_a_tenor(
    seeded: str,
) -> None:
    """`FTS-G08` — §C.4 trap 1, and it is arithmetic that must NOT be reported.

    Four facilities carry a maturity date 196 days BEFORE their effective date,
    all from one source accession. A negative tenor is not a short loan. The
    facility still serves — the dates are filed facts and repairing them would
    put an invented maturity into a payload claiming `public` provenance — and
    only the DERIVED claim is withheld.
    """
    deployment = _load("deployment")
    expected = _expected()
    inverted = expected["fixtures"]["inverted_tenor"]

    assembled = _serve(seeded, facility=inverted)
    facility = assembled.product.payload["facility"]

    assert facility is not None, "the inverted facility did not serve at all"
    assert facility["tenor_days"] == deployment.NOT_EVALUABLE, (
        f"tenor_days is {facility['tenor_days']!r}; a negative number here is"
        " arithmetic served as a term"
    )
    # Both dates are still served as filed — withholding them would hide the
    # defect rather than report it.
    assert facility["effective_date"] and facility["maturity_date"]
    assert facility["maturity_date"] < facility["effective_date"]


def test_a_facility_with_no_maturity_date_serves(seeded: str) -> None:
    """The completeness half of the same claim — absent, not inverted.

    Seven facilities carry no maturity date. `tenor_days` is NOT_EVALUABLE for
    the same reason and by a different route, and the two must not be conflated
    in the payload's shape even though they share a value.
    """
    deployment = _load("deployment")
    expected = _expected()
    assembled = _serve(seeded, facility=expected["fixtures"]["null_maturity"])
    facility = assembled.product.payload["facility"]
    assert facility["maturity_date"] is None
    assert facility["tenor_days"] == deployment.NOT_EVALUABLE


def test_the_amendment_count_is_served_and_no_amendment_date_is_claimed(
    seeded: str,
) -> None:
    """§C.4 trap 2 — the payload states what the estate can evidence.

    43 facilities carry an amendment count and NOT ONE carries a date any
    amendment took effect. A synthetic date here would look filed.
    """
    assembled = _serve(seeded)
    facility = assembled.product.payload["facility"]
    assert isinstance(facility["amendment_count"], int)
    assert not any("amend" in key and "date" in key for key in facility), (
        "the payload claims an amendment date; the estate holds none"
    )


# --------------------------------------------------------------------------
# FTS-G09 — the shipped finding. THIS TEST GOES RED WHEN THE DEFECT IS FIXED.
# --------------------------------------------------------------------------
def test_a_facility_older_than_the_window_is_refused(seeded: str) -> None:
    """`FTS-G09` — the 50-of-60 `ttl-bounds` refusal §F.4 finding 1 records.

    **THIS TEST ASSERTS A SHIPPED DEFECT AND IS WRITTEN TO FAIL WHEN IT IS
    FIXED.** `expires_at` is the credit agreement's effective date plus 90 days,
    effective dates span seven years, so 50 of the 60 facilities land in the past
    and `_refuse_ttl` rejects them on first call — including all 43 carrying an
    amendment history.

    When the vault rules on the anchor and the declaration changes, this test
    goes RED. That redness is the signal to close the finding, not a regression.
    The alternative — a test that tolerated both behaviors — would ratify the bug
    and let the finding die quietly.
    """
    expected = _expected()
    with pytest.raises(RuntimeError) as refused:
        _serve(seeded, facility=expected["fixtures"]["ttl_refused"])
    assert "ttl-bounds" in str(refused.value), (
        "the refusal was not the TTL gate's; this test is asserting the wrong"
        f" failure: {refused.value}"
    )


def test_the_population_the_finding_describes_is_the_population_that_refuses(
    seeded: str,
) -> None:
    """The finding's NUMBER, not just one instance of it.

    §F.4 finding 1 says 50 of 60. One refusing facility is consistent with any
    number from 1 to 60, so the count is measured against the store at the
    pinned instant rather than inferred from a single call.
    """
    expected = _expected()["estate"]
    deployment = _load("deployment")
    question = yaml.safe_load(
        deployment.QUESTION.read_text(encoding="utf-8")
    )[deployment.DECLARATION]

    # THE CUTOFF IS COMPUTED IN PYTHON, and that is not a style choice.
    # `interval '%s seconds'` looks like a parameter and is not one — the `%s`
    # sits inside a SQL string literal, so the driver leaves it alone and the
    # comparison silently becomes something else. It returned 0 live facilities
    # against a true answer of 10, and 0 is exactly what a broken TTL would also
    # return. A placeholder that does not bind fails as a plausible number.
    from datetime import datetime, timedelta

    asked_at = datetime.fromisoformat(question["asked_at"])
    cutoff = asked_at - timedelta(seconds=deployment.declared_ttl_seconds())
    with psycopg.connect(seeded) as db, db.cursor() as cursor:
        cursor.execute(
            "select count(*) from ccf_v2.facility where effective_date > %s",
            (cutoff.date(),),
        )
        live = int(cursor.fetchone()[0])
    assert live == expected["live_at_pinned_instant"], (
        f"{live} facilities are live at the pinned instant, the specification"
        f" says {expected['live_at_pinned_instant']}"
    )
    assert (
        expected["facilities"] - live == expected["refused_on_ttl_at_pinned_instant"]
    )


# --------------------------------------------------------------------------
# Determinism, and the shape of the served contract.
# --------------------------------------------------------------------------
def test_the_same_question_twice_is_byte_identical(seeded: str) -> None:
    """§D.4 — `deterministic`, asserted as hash equality between two runs.

    Compared to EACH OTHER rather than to a remembered number, so this is an
    independent instrument rather than a transcript.
    """
    first = _serve(seeded)
    second = _serve(seeded)
    assert content_hash(first.product) == content_hash(second.product)


def test_the_pricing_grid_parameter_changes_the_content_address(
    seeded: str,
) -> None:
    """§D.4 — the one parameter that changes the payload's SHAPE is in the hash.

    Two genuinely different payloads sharing a hash is a worse failure than two
    identical ones differing.
    """
    with_grid = _serve(seeded, include_pricing_grid=True)
    without = _serve(seeded, include_pricing_grid=False)
    assert "pricing_grid" in with_grid.product.payload["facility"]
    assert "pricing_grid" not in without.product.payload["facility"]
    assert content_hash(with_grid.product) != content_hash(without.product), (
        "two payloads of different shape share a content address"
    )


def test_the_served_contract_matches_the_declared_expectations(
    seeded: str,
) -> None:
    """§D.6 — the emitted contract's envelope and its required keys."""
    expected = _expected()
    assembled = _serve(seeded)
    product = assembled.product
    payload = product.payload

    assert product.schema_name == expected["product"]
    assert product.schema_version == expected["semantic_version"]
    assert product.ttl_anchor == expected["ttl_anchor"]
    for key in expected["payload_keys_always_present"]:
        assert key in payload, f"the payload lost {key!r}"
    for key in expected["facility_keys_always_present"]:
        assert payload["facility"].get(key) is not None, (
            f"{key!r} is absent or null and is declared always present"
        )


def test_the_recipe_steps_each_have_a_witness_that_fired(seeded: str) -> None:
    """`artifacts/assembly-recipe.yaml` — a step nothing executes is RED.

    A prose table cannot be held against a run. Each declared step names a
    witness; this evaluates every one against what the assembly produced.
    """
    deployment = _load("deployment")
    recipe = yaml.safe_load(deployment.RECIPE.read_text(encoding="utf-8"))[
        deployment.DECLARATION
    ]
    assembled = _serve(seeded)
    payload = dict(assembled.product.payload)

    for step in recipe["steps"]:
        witness = step["witness"]
        kind, argument = witness["kind"], witness["argument"]
        if kind == "operator_in_lineage":
            assert argument in assembled.operators_invoked, (
                f"step {step['step']} declares operator {argument!r} and the"
                " engine did not resolve it"
            )
        elif kind == "payload_key":
            cursor: Any = payload
            for part in argument.split("."):
                assert isinstance(cursor, dict) and part in cursor, (
                    f"step {step['step']}'s witness {argument!r} is not in the"
                    " served payload"
                )
                cursor = cursor[part]
            assert cursor is not None, (
                f"step {step['step']}'s witness {argument!r} is present but null"
            )
        elif kind == "vessel_held":
            from ccf.products.gates import ServableProduct

            assert isinstance(assembled.gated, ServableProduct), (
                "no ServableProduct was held, so the shipped gates are not"
                " known to have run"
            )
        else:  # pragma: no cover - the vocabulary is closed
            raise AssertionError(f"unknown witness kind {kind!r}")
