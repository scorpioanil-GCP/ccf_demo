"""cp-03's validation gates, served rather than described.

**WHAT THIS MODULE IS FOR.** ``CP-SPEC-003`` §G.2 declares fourteen gates and
says of them: *"Every gate must be made to fail deliberately once. A gate that
has never been observed red is not evidence that it runs."* Before this module
existed, none of the fourteen ran at all — every ``OFS-G`` in the example's four
modules was a comment, ``artifacts/expected.yaml`` was read by nothing, and the
example's only test answered census questions with SQL. A census question is
answered by COUNTING ROWS; a gate is answered by SERVING THE PRODUCT, and the
two need different machinery.

**THREE OF THE FOURTEEN ARE HERE** — ``OFS-G01``, ``OFS-G09`` and ``OFS-G15``,
chosen to span the three different shapes a gate takes, so the shape can be
reviewed before the remaining eleven are written to it:

===========  ==============================================================
``OFS-G01``  a claim about the PAYLOAD's contents
``OFS-G09``  a claim about the ENVELOPE — a value beside the payload
``OFS-G15``  a claim about a POPULATION, which no single request can see
===========  ==============================================================

**EXPECTATIONS COME FROM ``expected.yaml``, NEVER FROM THIS FILE.** A number
authored here would be the test agreeing with itself about what this
deployment's vocabulary says. Where this module computes something, it computes
it from the estate through the deployment's own code, and compares against the
declared value.

**THE SEED IS MEASURED BEFORE IT IS TRUSTED.** ``test_the_seed_carries_what
_these_gates_need`` runs first and is a positive control: the gates below are
about entitlement and fact kinds, and every one of them would pass VACUOUSLY
against a fixture missing the tables that make those questions real.
"""

from __future__ import annotations

import importlib
import os
import pathlib
import sys
from datetime import timedelta
from decimal import Decimal
from typing import Any

import psycopg
import pytest
import yaml

REPO = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE = REPO / "examples" / "cp-03-obligor-financial-spread"
FIXTURES = pathlib.Path(__file__).parent / "fixtures"
SCHEMA_SQL = FIXTURES / "cp_03_census_schema.sql"
ROWS_SQL = FIXTURES / "cp_03_census_rows.sql"

pytestmark = pytest.mark.postgres


def _load(name: str) -> Any:
    """Load one of the example's modules under its own bare name.

    The example is a directory of modules rather than a package, and its modules
    import each other by bare name. **Four examples now share those names** —
    cp-00, cp-01, cp-02 and cp-03 each ship a ``deployment``, a ``produce`` and
    an ``assembler``, while ``make leg-postgres`` runs one pytest session over
    the whole tree. Whichever module is imported first wins the name, and the
    others then read its constants; a missing attribute is the polite failure
    and a silently wrong value is the impolite one.

    So the cache is checked against THIS example's directory and the whole
    family is evicted together when it holds somebody else's. Evicting one name
    at a time would rebuild the split-identity problem the eviction prevents.
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
        if not str(getattr(cached, "__file__", "")).startswith(str(EXAMPLE)):
            for sibling in family:
                sys.modules.pop(sibling, None)
            break
    return importlib.import_module(name)


def _expected() -> Any:
    """The declared expectations — this module's only source for domain values."""
    deployment = _load("deployment")
    document = yaml.safe_load(deployment.EXPECTED.read_text(encoding="utf-8"))
    return document[deployment.DECLARATION]


def _dsn_variable() -> str:
    """The env var `backends.yaml` declares, read through the deployment's keys."""
    deployment = _load("deployment")
    document = yaml.safe_load(deployment.BACKENDS.read_text(encoding="utf-8"))
    source = document[deployment.DECLARATION][deployment.SOURCES]
    binding = source[deployment.SOURCE_BINDING][deployment.SETTINGS]
    return str(binding[deployment.SOURCE_SETTING_DSN][deployment.FROM_ENV])


@pytest.fixture(scope="module")
def seeded(postgres_dsn: str) -> Any:
    """A seeded estate, with the DSN exported where `backends.yaml` reads it."""
    with psycopg.connect(postgres_dsn, autocommit=True) as db, db.cursor() as cur:
        cur.execute(SCHEMA_SQL.read_text(encoding="utf-8"))
        cur.execute(ROWS_SQL.read_text(encoding="utf-8"))

    variable = _dsn_variable()
    previous = os.environ.get(variable)
    os.environ[variable] = postgres_dsn
    yield postgres_dsn
    if previous is None:
        os.environ.pop(variable, None)
    else:
        os.environ[variable] = previous


def _serve(seeded: str, **kwargs: Any) -> Any:
    """Assemble one spread through the seam, exactly as ``run.py`` does.

    Returns the SPINE's value, captured through the observer, because the
    Protocol's return type carries the assembly's governance rather than the
    served vessel.

    **A REFUSAL PROPAGATES. It is not replaced by the captured value, and this
    is the one place this helper deliberately departs from cp-02's.** cp-02's
    equivalent falls back to ``captured[0]`` when the seam raises, on the
    reasoning that the spine's value is still what the caller wants to see.
    Here that fallback is a trap: for a SUPPRESSED obligor the observer has
    already fired with an ``Assembled`` **carrying a product**, so returning it
    reports a served spread for a principal entitled to nothing. Measured, not
    reasoned about — ``PRIN-KYC-004`` raises ``AssemblyRefused`` and captures
    one object whose ``product`` is not ``None``.

    That is not a defect in the seam. ``run.py`` catches the refusal before it
    ever consults ``captured``, so nothing on the shipped path is misled. It is
    a defect in a test helper that would have made ``OFS-G15`` report green
    while entitlement did nothing at all — which is precisely the failure the
    gate exists to catch, arriving through the gate's own instrument.
    """
    import tempfile

    deployment = _load("deployment")
    assembler = _load("assembler")

    anchor = kwargs.pop("anchor", None)
    principal = kwargs.pop("principal", None)
    asked_at = kwargs.pop("asked_at", None)

    declared = deployment.demonstration_parameters()
    parameters: dict[str, object] = {
        deployment.PARAM_INTENT: declared[deployment.PARAM_INTENT],
        deployment.PARAM_PERIODS: int(declared[deployment.PARAM_PERIODS]),
        deployment.PARAM_BASIS: str(declared[deployment.PARAM_BASIS]),
        deployment.PARAM_INCLUDE_PEERS: bool(
            declared[deployment.PARAM_INCLUDE_PEERS]
        ),
        deployment.PARAM_PEER_BASIS: str(declared[deployment.PARAM_PEER_BASIS]),
        deployment.PARAM_DEBT_TOLERANCE: Decimal(
            str(declared[deployment.PARAM_DEBT_TOLERANCE])
        ),
    }
    parameters.update(kwargs)

    asked = deployment.request(parameters=parameters, asked_at=asked_at)
    if anchor is not None and anchor != deployment.demonstration_anchor():
        asked = asked.model_copy(update={"subject": anchor})

    def read(booted: Any, question: Any) -> Any:
        if principal is None:
            return deployment.read(booted, question)
        return deployment.read(booted, question, principal_id=principal)

    with tempfile.TemporaryDirectory(prefix="cp03-gate-") as tmp:
        root = pathlib.Path(tmp)
        captured: list[object] = []
        seam = assembler.SpreadAssembler(
            config=deployment.CONFIG,
            root=root,
            connection=deployment.connection(root=root),
            read=read,
            plan_class=deployment.plan_class(),
            observer=captured.append,
        )
        governed = seam.assemble(
            request=asked,
            perspective=deployment.perspective(),
            tenant_id=deployment.tenant_id(),
        )
        return captured[0] if captured else governed


def _reported_lines(assembled: Any) -> list[dict[str, Any]]:
    """Only lines that carry a FILED FACT, flattened across periods.

    **The distinction is load-bearing and it was learned by sabotage.** A period
    holds three shapes of line: a reported fact, a derived ratio, and a
    placeholder for a line this deployment declares but the obligor never filed.
    All three carry a ``kind`` — the placeholder carries the DECLARED kind from
    ``spread-lines.yaml``, describing the line the estate expected rather than
    any fact it holds.

    A first version of ``OFS-G01`` flattened all three, and a payload with every
    reported fact forced to ``duration`` still passed: 54 placeholders went on
    saying ``instant``. The gate was asserting that the payload MENTIONS the
    word, not that it CARRIES the fact.

    "Reported" is defined by ``expected.yaml``'s ``reported_line_keys_when_
    filed`` rather than by a list written here, so a change to the emitted
    contract moves this filter with it instead of leaving it quietly stale.
    """
    required = set(_expected()["reported_line_keys_when_filed"])
    payload = dict(assembled.product.payload)
    return [
        line
        for period in payload["periods"]
        for line in period["lines"].values()
        if isinstance(line, dict) and required.issubset(line.keys())
    ]


# ---------------------------------------------------------------------------
# The seed is measured before anything is asserted against it.
# ---------------------------------------------------------------------------


def test_the_seed_carries_what_these_gates_need(seeded: str) -> None:
    """A positive control, and it runs FIRST because the greens depend on it.

    Every gate below would pass VACUOUSLY against a fixture that could not raise
    its question. ``OFS-G15`` compares visible populations, and four principals
    each seeing nothing is a set of four identical empty sets — which a badly
    written gate reads as agreement rather than as an absent table. ``OFS-G01``
    asserts both fact kinds are present, and a payload with no lines at all
    carries no counter-example either.

    This test exists because the fixture DID lack those tables until the gates
    were written: it was dumped to answer census questions, and a census needs
    no ``principal``. The gates found the gap, which is the whole argument for
    writing them.
    """
    expected = _expected()
    with psycopg.connect(seeded) as db, db.cursor() as cur:
        for table in ("principal", "principal_jurisdiction", "peer_entity"):
            cur.execute(f"select count(*) from ccf_v2.{table}")
            row = cur.fetchone()
            assert row is not None and row[0] > 0, (
                f"ccf_v2.{table} is empty or absent; every gate below would"
                " pass without ever asking its question"
            )

        cur.execute(
            "select count(distinct principal_id) from ccf_v2.principal_jurisdiction"
        )
        row = cur.fetchone()
        assert row is not None
        declared = expected["populations"]["obligors_visible_per_principal"]
        assert row[0] == len(declared), (
            f"{row[0]} principals carry grants but expected.yaml declares"
            f" {len(declared)}; the gate's population and its expectation are"
            " describing different estates"
        )


# ---------------------------------------------------------------------------
# `OFS-G01` — a claim about the PAYLOAD's contents.
# ---------------------------------------------------------------------------


def test_ofs_g01_the_payload_carries_both_fact_kinds(seeded: str) -> None:
    """`OFS-G01` — at least one instant AND at least one duration fact.

    **A duration-only payload fails**, and that is the whole point of the gate
    rather than a detail of it. §C.5: a join written ``USING (period_start)``
    silently drops all 8,088 instant facts, reports a tidy number and raises no
    error. The census gates that defect at the SQL; this gates it at the
    payload, so a spread that lost its balance-sheet half on the way out is
    caught even when the query underneath was right.

    The two kinds are not decoration. An instant fact is a stock — cash, assets,
    debt at a moment. A duration fact is a flow — revenue, interest expense over
    a window. A spread that carries only flows is not a spread.
    """
    assembled = _serve(seeded)
    lines = _reported_lines(assembled)
    assert lines, "the served payload carries no reported lines at all"

    kinds = {line.get("kind") for line in lines}
    assert "instant" in kinds, (
        "the payload carries no instant fact. A duration-only spread is what"
        " a NULL-dropping join produces (§C.5), and it is exactly the shape"
        " this gate exists to refuse"
    )
    assert "duration" in kinds, (
        "the payload carries no duration fact; the spread has stocks and no"
        " flows, which is not a spread"
    )


# ---------------------------------------------------------------------------
# `OFS-G09` — a claim about the ENVELOPE, beside the payload.
# ---------------------------------------------------------------------------


def test_ofs_g09_the_expiry_is_anchored_on_the_filing_not_the_question(
    seeded: str,
) -> None:
    """`OFS-G09` — `expires_at` follows the payload's LATEST filing.

    Two claims, and the second is the one that catches the plausible error.

    **It is anchored on the latest filing**, not the earliest. A spread is
    stitched from many filings; anchoring on the earliest would expire a
    perfectly current product because it also carries a five-year-old annual.
    The declared arithmetic — ``latest_filed_date_in_payload`` plus
    ``declared_ttl_days`` — is read from ``expected.yaml``, so a reader checks it
    without running anything.

    **And it does not move when the question moves.** Asking the same question
    an hour later must not extend the answer's life. An expiry that tracked
    ``asked_at`` would make every product permanently fresh, and the freshness
    numbers would look healthy forever — the failure mode ``from_entity_
    freshness`` exists to prevent.
    """
    expected = _expected()
    assert expected["ttl_basis"] == "latest_filed_date_in_payload", (
        "expected.yaml no longer declares the anchor this gate asserts"
    )
    ttl_days = int(expected["declared_ttl_days"])

    assembled = _serve(seeded)
    product = assembled.product
    filed = sorted(
        line["filed_date"] for line in _reported_lines(assembled) if line.get("filed_date")
    )
    assert filed, "no line in the payload carries a filing date"

    latest = filed[-1]
    expires = product.expires_at.date()
    assert str(latest) == str(assembled.scenario.latest_filed_in_payload), (
        "the payload's latest filing and the scenario's disagree, so the"
        " expiry is anchored on something the payload does not show"
    )

    from datetime import date

    anchor_date = date.fromisoformat(str(latest))
    assert expires == anchor_date + timedelta(days=ttl_days), (
        f"expires_at is {expires}, but the payload's latest filing is"
        f" {anchor_date} and expected.yaml declares a {ttl_days}-day TTL."
        " Anchoring on the EARLIEST filing is the plausible wrong answer here"
    )

    # The question moves; the answer's life must not.
    later = _serve(
        seeded,
        asked_at=assembled.scenario.request.asked_at + timedelta(hours=1),
    )
    assert later.product.expires_at == product.expires_at, (
        "expires_at moved when asked_at moved. The expiry would then track the"
        " question rather than the filing, and every product would be"
        " permanently fresh"
    )


# ---------------------------------------------------------------------------
# `OFS-G15` — a claim about a POPULATION no single request can see.
# ---------------------------------------------------------------------------


def _visible_population(seeded: str, principal: str) -> frozenset[str]:
    """The obligors a principal can see, through the deployment's OWN expansion.

    ``_permitted_jurisdictions`` is the function that was wrong once: a
    principal is granted a jurisdiction PREFIX, ``US`` reaches ``US-DE``, and a
    prefix handed to the SDK's exact-membership filter unexpanded matches
    nothing and empties the view. Measuring the population with a query written
    HERE would test this module's idea of the rule instead of the deployment's,
    so the expansion comes from the deployment and only the roster is local.
    """
    deployment = _load("deployment")
    with psycopg.connect(seeded) as db, db.cursor() as cur:
        granted = set(
            deployment._permitted_jurisdictions(cur, principal_id=principal)
        )
        cur.execute(
            """
            select le.lei, le.legal_jurisdiction
              from ccf_v2.legal_entity le
             where le.is_anchor
            """
        )
        return frozenset(
            str(lei) for lei, jurisdiction in cur.fetchall() if jurisdiction in granted
        )


def test_ofs_g15_entitlement_discriminates_as_sets_with_a_negative_control(
    seeded: str,
) -> None:
    """`OFS-G15` — sets and a ROSTER, never a pair of counts.

    **The two zeroes are why this gate is shaped the way it is.**
    ``PRIN-KYC-004`` and ``PRIN-TRD-003`` legitimately see nothing: they carry
    nine and four jurisdiction prefixes respectively, and no obligor in this
    estate files under any of them. They are *granted elsewhere*, not *granted
    nothing* — a principal with an empty grant would prove far less, because it
    could not tell a working filter from one that returns nothing at all.

    An always-empty implementation satisfies both zeroes. So the negative
    controls never travel alone: the positive control ``49 != 47`` is asserted
    beside them, and an implementation that returns nothing fails it.

    **And the count is not enough either.** A right count with a wrong member
    audits clean forever. ``expected.yaml`` names the two obligors that separate
    the top pair — both Canadian, and ``PRIN-RES-002``'s grant carries ``CA``
    where ``PRIN-COV-001``'s does not — so swapping a member while keeping the
    count turns this red where ``49`` and ``47`` would not.
    """
    expected = _expected()
    populations = expected["populations"]
    declared = populations["obligors_visible_per_principal"]

    visible = {
        principal: _visible_population(seeded, principal)
        for principal in sorted(declared)
    }

    # The negative control FIRST: a set compared against itself must match, or
    # the instrument is broken and every reading below is meaningless.
    for principal, population in visible.items():
        assert population == population, "set comparison is unstable"

    for principal, count in sorted(declared.items()):
        assert len(visible[principal]) == count, (
            f"{principal} sees {len(visible[principal])} obligors and"
            f" expected.yaml declares {count}"
        )

    # THE POSITIVE CONTROL, paired with the zeroes so neither travels alone.
    top = sorted(declared, key=lambda p: -declared[p])[:2]
    assert visible[top[0]] != visible[top[1]], (
        f"{top[0]} and {top[1]} see the SAME set. The two zeroes below would"
        " still pass, which is exactly the condition under which an"
        " always-empty entitlement looks correct"
    )

    # THE ROSTER, not only the cardinality.
    separating = {
        str(row["lei"]) for row in populations["separating_the_top_two_principals"]
    }
    assert visible[top[0]] - visible[top[1]] == separating, (
        "the obligors separating the top two principals are not the ones"
        " expected.yaml names. A right count with a wrong member audits clean"
        " forever, which is why this line exists beside the counts"
    )

    invisible = {str(row["lei"]) for row in populations["visible_to_no_principal"]}
    seen_by_anyone: frozenset[str] = frozenset().union(*visible.values())
    assert invisible.isdisjoint(seen_by_anyone), (
        "an obligor expected.yaml declares visible to no principal is visible"
        " to one"
    )


def _outcome(seeded: str, lei: str, principal: str) -> str:
    """A coarse label for what the seam did, so two requests can be compared.

    ``"served"``, ``"not-available"`` (§D.2's fail-closed 404, which is also
    what SUPPRESSION looks like — that identity is the point), or the name of
    the SDK validation gate that refused.
    """
    from ccf.agents.errors import AssemblyRefused

    try:
        served = _serve(seeded, anchor=lei, principal=principal)
    except AssemblyRefused as refused:
        return "not-available" if "not available" in str(refused) else "refused"
    except RuntimeError as refused:
        detail = str(refused)
        gate = detail.partition("gate='")[2].partition("'")[0]
        return f"gate:{gate or 'unknown'}"
    return "served" if getattr(served, "product", None) is not None else "empty"


def test_ofs_g15_suppression_is_indistinguishable_from_absence(
    seeded: str,
) -> None:
    """`OFS-G15`, second half — the population is bound to the shipped seam.

    The test above measures a population of fifty through the deployment's own
    grant expansion, because serving fifty obligors four times over is two
    hundred assemblies. That saving is only legitimate if the cheap measurement
    and a real request agree, so this test spends four requests binding them.

    **It does NOT use the two obligors that separate the top two principals,
    and the reason is worth recording rather than rediscovering.** Both of them
    are among the 27 of 50 that refuse on ``ttl-bounds`` at this pin — their
    newest filing is older than the window — so ``PRIN-RES-002`` and
    ``PRIN-COV-001`` receive the SAME refusal for both, and the entitlement
    difference that makes ``49 != 47`` true is invisible through a served
    product at this pin. A first version of this test asserted that a granted
    obligor serves, and failed against entirely correct data and entirely
    correct entitlement.

    So the binding uses the pair that IS observable, and it asserts the stronger
    property anyway — §B.2's commitment that **a principal whose grant does not
    reach the subject receives what an obligor that does not exist receives.**
    Only the replay record separates them. A suppression that announced itself
    ("you are not permitted to see this") would leak the obligor's existence to
    a principal not entitled to know it.
    """
    expected = _expected()
    declared = expected["populations"]["obligors_visible_per_principal"]
    granted = max(declared, key=lambda p: declared[p] if declared[p] else -1)
    ungranted = min(declared, key=lambda p: declared[p])
    assert declared[ungranted] == 0, (
        "this test needs a principal that sees nothing; expected.yaml declares"
        f" {ungranted} sees {declared[ungranted]}"
    )

    deployment = _load("deployment")
    anchor = deployment.demonstration_anchor()
    ghost = "0" * 16 + "GHOST"

    # POSITIVE CONTROL FIRST. If the anchor does not serve for a principal that
    # is entitled to it, every suppression reading below is meaningless — an
    # implementation that refused everything would satisfy the negative control
    # on its own.
    assert _outcome(seeded, anchor, granted) == "served", (
        f"the demonstration anchor does not serve for {granted}, which is"
        " entitled to it; the negative control below would then be vacuous"
    )

    # THE NEGATIVE CONTROL, and the identity §B.2 commits to.
    suppressed = _outcome(seeded, anchor, ungranted)
    absent = _outcome(seeded, ghost, ungranted)
    assert suppressed == "not-available", (
        f"{ungranted} is granted nothing in this estate and the anchor did not"
        f" fail closed for it: {suppressed}"
    )
    assert suppressed == absent, (
        "a suppressed obligor and an obligor that does not exist produce"
        f" different outcomes ({suppressed} vs {absent}). §B.2 requires them to"
        " be indistinguishable, because the difference would tell an"
        " unentitled principal that the obligor exists"
    )

    # And the same absence for a principal that IS broadly granted, so the
    # ghost's refusal is a property of the ghost rather than of the grant.
    assert _outcome(seeded, ghost, granted) == "not-available", (
        "a nonexistent obligor did not fail closed for a broadly granted"
        " principal, so the comparison above is not measuring suppression"
    )
