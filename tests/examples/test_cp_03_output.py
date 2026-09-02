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
    #: Optional: a list the caller owns, so it can inspect the spine's value
    #: after a refusal. See `OFS-G06` for the only legitimate use.
    external = kwargs.pop("_observer", None)

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
        captured: list[object] = [] if external is None else external
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

    # THE INSTRUMENT IS CHECKED FIRST, AND IT IS CHECKED FOR REAL.
    # This read `assert population == population` until the close panel named
    # it: a value compared against itself is true for every value, so it tested
    # nothing at all. It was written as a "control" and was a tautology — the
    # same defect class this module was built to catch, in the gate's own
    # instrument. What actually needs proving is that the measurement is
    # REPEATABLE and DISCRIMINATING: re-measuring gives the same set, and two
    # different grants do not collapse to one.
    for principal in sorted(declared):
        again = _visible_population(seeded, principal)
        assert again == visible[principal], (
            f"{principal} measured twice gives two different sets"
            f" ({len(visible[principal])} then {len(again)}); the instrument is"
            " unstable and every reading below is meaningless"
        )
    assert len(set(visible.values())) > 1, (
        "every principal resolves to the SAME set, so the measurement cannot"
        " discriminate at all and the counts below would be a coincidence"
    )

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
    # WITNESSES ARE DECLARED, NOT SORTED OUT OF TODAY'S ESTATE.
    # These were `max()` and `min()` over the population counts, and the ghost
    # was a string invented here. Both are the gate choosing its own subject —
    # house rule 2 — and both break quietly if two principals tie or the
    # estate's shape shifts. Close-panel finding, 2026-08-31.
    granted = _witness("principal_broadly_granted")
    ungranted = _witness("principal_granted_nothing")
    ghost = _witness("obligor_that_does_not_exist")
    assert declared[ungranted] == 0, (
        "this test needs a principal that sees nothing; expected.yaml declares"
        f" {ungranted} sees {declared[ungranted]}"
    )
    assert declared[granted] > 0, (
        f"{granted} is declared to see {declared[granted]} obligors, so the"
        " positive control below would be vacuous"
    )

    deployment = _load("deployment")
    anchor = deployment.demonstration_anchor()

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


# ---------------------------------------------------------------------------
# Source-level gates. These read the example's CODE, and they read it through
# `ast` rather than as text — deliberately.
#
# Every one of these modules DISCUSSES the stores it does not open and the
# stages it does not have: `deployment.py`'s own docstring names Fluree in
# order to say Fluree is not read. A text scan would go red on the sentence
# explaining the invariant while the code violating it slipped past. That is
# the same defect `OFS-G01` was found to have — a check reading a token that
# appears in both the compliant and the violating case — so these gates parse
# out docstrings and comments and look only at what executes.
# ---------------------------------------------------------------------------


def _module_paths() -> list[pathlib.Path]:
    return sorted(EXAMPLE.glob("*.py"))


def _executable_strings(path: pathlib.Path) -> list[str]:
    """Every string literal that is NOT a docstring, plus every imported name."""
    import ast

    tree = ast.parse(path.read_text(encoding="utf-8"))
    docstrings: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", [])
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                docstrings.add(id(body[0].value))
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if id(node) not in docstrings:
                found.append(node.value)
        elif isinstance(node, ast.Import):
            found.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            # THE MODULE **AND** THE NAMES, AND EVERY DOTTED SEGMENT OF BOTH.
            # Recording only `node.module` missed `from ccf.integrations import
            # llm` — the module is `ccf.integrations`, which starts with
            # neither forbidden token, so an LLM client could be imported past
            # `OFS-G07` in a spelling nobody would think to look for.
            # Close-panel finding, 2026-08-31.
            found.append(node.module or "")
            found.extend(alias.name for alias in node.names)
    for dotted in list(found):
        found.extend(dotted.split("."))
    return found


def test_ofs_g02_resolution_goes_through_the_crosswalk(seeded: str) -> None:
    """`OFS-G02` — identity comes from `crosswalk`, never from `financial_fact.cik`.

    Rung 01 owns identity. This product resolves an obligor by asking the
    crosswalk, and a build in a hurry would shortcut it: `financial_fact`
    already carries a `cik`, so joining straight to it "works" and silently
    makes this product its own system of record for identity.

    Both halves are asserted, because either alone is satisfiable by the wrong
    code: the resolution query must NAME the crosswalk, and the payload's
    identity must be derived from the crosswalk's `lei` rather than from the
    fact table's `cik`.
    """
    import ast
    import inspect
    import textwrap

    deployment = _load("deployment")

    # THE NAMES THE FUNCTION'S CODE REFERENCES, NOT THE WORDS ITS PROSE USES.
    # A first version of this gate asserted `"crosswalk" in
    # inspect.getsource(...)` and was VACUOUS: the function's own docstring
    # opens "Resolve the anchor THROUGH rung 01's crosswalk", so the check
    # passed on the sentence describing the invariant while the code violating
    # it went by. That is the same defect `OFS-G01` was caught having, found
    # here by sabotage rather than by review.
    tree = ast.parse(textwrap.dedent(inspect.getsource(deployment._resolve_obligor)))
    referenced = {
        node.id for node in ast.walk(tree) if isinstance(node, ast.Name)
    }
    assert "TABLE_CROSSWALK" in referenced, (
        "the resolution query's code does not reference the crosswalk table."
        " `financial_fact` already carries a cik, so resolving from it 'works'"
        " and silently makes this product its own system of record for"
        f" identity. Names referenced: {sorted(referenced)}"
    )

    assembled = _serve(seeded)
    obligor = dict(assembled.product.payload)["obligor"]
    assert obligor["lei"], "the payload carries no lei"
    assert obligor["entity_id"].startswith("obligor://"), (
        "the entity id is not the crosswalk-derived address"
    )


def test_ofs_g05_no_store_but_postgres_is_opened(seeded: str) -> None:
    """`OFS-G05` — one store, and `spread_observation` is never read.

    §F.3 checked all five stores and read one. The other four are DISCUSSED at
    length in these modules, which is exactly why this gate parses rather than
    greps: the sentence "no Fluree connection is opened" contains the word
    Fluree.

    `spread_observation` is called out separately from the other stores because
    it lives in the SAME Postgres this product does open, so no connection
    check would catch it. It holds 47,849 rows of pre-computed spreads — the
    thing this product exists to assemble rather than look up.
    """
    forbidden_stores = ("fluree", "mongo", "neo4j", "sqlite", "bolt://", "8090", "27017")

    # THE LOOP MUST HAVE RUN. A gate whose assertions live inside a loop that
    # iterates zero times passes without asking its question, and an empty
    # `EXAMPLE.glob` is exactly how that happens — a moved directory, a renamed
    # example. Close-panel finding, 2026-08-31.
    scanned = 0
    for path in _module_paths():
        for literal in _executable_strings(path):
            lowered = literal.lower()
            assert "spread_observation" not in lowered, (
                f"{path.name} names spread_observation in executable code."
                " This product ASSEMBLES the spread; reading a pre-computed"
                " one would make the whole assembly decorative"
            )
            scanned += 1
            for store in forbidden_stores:
                assert store not in lowered, (
                    f"{path.name} reaches a store other than PostgreSQL"
                    f" ({store!r} in {literal[:60]!r})"
                )
    assert len(_module_paths()) >= 4, (
        f"only {len(_module_paths())} modules found at {EXAMPLE}; this gate"
        " scans the example's code and has just scanned almost none of it"
    )
    assert scanned > 0, (
        "no executable string or import was scanned, so this gate asserted"
        " nothing about which stores the example reaches"
    )


def test_ofs_g07_no_llm_client_is_reachable(seeded: str) -> None:
    """`OFS-G07` — Assembly Mode 1: no semantic stage exists.

    The product declares `assembly_mode: 1`, which is a registration-time
    commitment that no step calls a model. This gate makes the commitment
    checkable rather than asserted: an LLM client that became reachable from
    any step would turn the deployment into Mode 2 without the declaration
    changing.
    """
    expected = _expected()
    assert int(expected["assembly_mode"]) == 1, (
        "expected.yaml no longer declares Assembly Mode 1; this gate is"
        " asserting a commitment the product has stopped making"
    )
    clients = ("anthropic", "openai", "llm", "langchain", "transformers", "ollama")
    scanned = 0
    for path in _module_paths():
        for literal in _executable_strings(path):
            lowered = literal.lower()
            scanned += 1
            for client in clients:
                assert not lowered.startswith(client), (
                    f"{path.name} imports {literal!r}. A model reachable from"
                    " any step makes this Assembly Mode 2, and the declared 1"
                    " becomes false"
                )
    assert scanned > 0, (
        "no executable string or import was scanned, so this gate asserted"
        " nothing about model reachability"
    )


def test_ofs_g06_as_of_is_refused_and_never_silently_honored(seeded: str) -> None:
    """`OFS-G06` — a parameter this tier declares and always refuses.

    `as_of` asks the product to reconstruct the spread as it stood on a past
    date. That is a Tier 3 capability and this is a Tier 1 product. The
    dangerous outcome is not the refusal; it is ACCEPTING the parameter and
    ignoring it, which answers a question about today while the caller believes
    they asked about last March.

    Rewritten under 24.5-FLIP-ROSTER.md (`24.5-L-12`, `24.5-L-13`): the
    refusal is now the SDK's own `not-supported-at-tier` verdict, returned as
    DATA by the tier step of `refuse_request` before the product's inert
    branch is reached, so nothing raises and the observer sees the verdict.
    """
    deployment = _load("deployment")

    declared = deployment.unsupported_arguments()
    assert deployment.PARAM_AS_OF in declared, (
        "as_of is no longer declared unsupported, so this gate is checking a"
        " refusal the deployment has stopped promising"
    )

    from ccf.agents.errors import AssemblyRefused

    # THE SPINE'S VALUE IS READ HERE, ON A REFUSAL, WHICH `_serve` OTHERWISE
    # REFUSES TO DO. It is safe in this one gate and nowhere else: the
    # assertion below is that the captured value IS a `ParameterNotSupported`,
    # a type that cannot be mistaken for a served product. The trap `_serve`
    # guards against is reading a captured value that CARRIES a product; here
    # a captured product would fail the very first assertion.
    captured: list[object] = []
    raised = False
    try:
        served = _serve(
            seeded, _observer=captured, **{deployment.PARAM_AS_OF: "2026-03-31"}
        )
    except AssemblyRefused:
        raised = True
        served = captured[0] if captured else None

    # THE REFUSAL IS RETURNED, NOT RAISED. The tier step of `refuse_request`
    # (`24.5-L-13`) answers `as_of` with the SDK's own `not-supported-at-tier`
    # verdict as DATA, before the product's inert branch, so the observer sees
    # the verdict and nothing raises. A raise here would mean the SDK step did
    # not fire and the product's own branch answered instead; a served spread
    # would mean neither did. The raise this replaced was the close-panel
    # finding of 2026-08-31; rewritten under 24.5-FLIP-ROSTER.md.
    from ccf.products.request import ProductRequestViolation

    assert not raised, (
        "the refusal arrived as a raise from the product's own branch; the"
        " SDK's tier verdict (not-supported-at-tier) did not fire first"
    )
    assert isinstance(served, ProductRequestViolation), (
        "as_of was accepted rather than refused; got"
        f" {type(served).__name__}. A silently ignored as_of answers a"
        " question about today while the caller believes they asked about a"
        " past date, and nothing in the payload would say so"
    )
    assert served.reason == "not-supported-at-tier", (
        f"the refusal reads {served.reason!r} rather than not-supported-at-tier"
    )
    assert served.key == deployment.PARAM_AS_OF, (
        f"the refusal names {served.key!r} rather than as_of"
    )
    assert "400 not_supported_at_tier" in served.detail, (
        "the refusal's detail does not carry the Standard's status token"
    )

    # `not_supported_at_tier` is the SPEC's name for this condition and is not
    # a value anywhere in the SDK: `ProductRequestViolation.reason` is a closed
    # Literal with no member for it, which is why the assembler RAISES rather
    # than returning a violation. Recorded at §F.4; asserted here so that a
    # future SDK member for it is noticed rather than silently unused.
    members = getattr(
        ProductRequestViolation.model_fields["reason"].annotation, "__args__", ()
    )
    # green by spelling — 24.5-FLIP-ROSTER.md
    assert "not_supported_at_tier" not in members, (
        "the SDK now has a not_supported_at_tier refusal member. This product"
        " should return it rather than raising, and §F.4's finding closes"
    )


def test_ofs_g10_exactly_one_operator_and_no_enrich(seeded: str) -> None:
    """`OFS-G10` — one operator in the plan, and no `Enrich` registered.

    An empty operator plan fails the SDK's own empty-operator guard, so this
    product cannot serve without its Policy operator — which is the point: the
    entitlement filter is not optional decoration, it is the only thing between
    a principal and rows they may not see.

    **This gate turns RED if the eight-member operator vocabulary is later
    adopted, and that redness is a signal rather than a regression** — it means
    §F.2 row 1 needs reopening, not that the build broke.
    """
    expected = _expected()
    declared = [
        invariant
        for invariant in expected["invariants"]
        if invariant["name"] == "one-operator"
    ]
    assert declared, "expected.yaml no longer declares the one-operator invariant"

    assembled = _serve(seeded)
    invoked = sorted(assembled.operators_invoked)
    assert len(invoked) == 1, (
        f"the plan invoked {len(invoked)} operators, not one: {invoked}"
    )
    # AND IT MUST BE THE POLICY OPERATOR, NAMED FROM THE ARTIFACT.
    # The gate asserted only "exactly one, and not an Enrich" until the close
    # panel observed that a single no-op operator called anything else would
    # satisfy that while the entitlement filter was absent altogether — the
    # count is not the invariant, the operator is.
    assert invoked[0] == _witness("sole_operator"), (
        f"the plan's one operator is {invoked[0]!r}, not the"
        f" {_witness('sole_operator')!r} expected.yaml declares. A count of one"
        " says nothing about whether the entitlement filter ran"
    )
    assert "enrich" not in invoked[0].lower(), (
        f"an Enrich operator is in the plan ({invoked[0]}). Enrichment at read"
        " time is the fabric doing work the assembly should have done"
    )


# ---------------------------------------------------------------------------
# Data gates. Each addresses a witness DECLARED in `expected.yaml`, never one
# discovered here — a gate that picked its own subject would pick the subject
# that makes it pass.
# ---------------------------------------------------------------------------


CENSUS = yaml.safe_load(
    (FIXTURES / "cp_03_census_expected.yaml").read_text(encoding="utf-8")
)


def _witness(name: str) -> str:
    return str(_expected()["gate_witnesses"][name])


def _restatement_artifact() -> Any:
    deployment = _load("deployment")
    document = yaml.safe_load(deployment.RESTATEMENT.read_text(encoding="utf-8"))
    return document[deployment.DECLARATION]


def _restated_cells(seeded: str, key: list[str]) -> int:
    """The restatement census under an ARBITRARY key, so the key can be varied.

    A cell is restated when the same fact — same key — carries more than one
    distinct value across the filings that reported it. Varying the key is the
    whole experiment: the correct key yields 321 and every looser one yields
    more, because a looser key merges facts that were never the same fact.
    """
    columns = ", ".join("f." + column for column in key)
    with psycopg.connect(seeded) as db, db.cursor() as cur:
        cur.execute(
            f"""
            select count(*) from (
              select {columns}
                from ccf_v2.financial_fact f
                join ccf_v2.crosswalk x on x.cik = f.cik
               group by {columns}
              having count(distinct f.value) > 1
            ) restated
            """
        )
        row = cur.fetchone()
        assert row is not None
        return int(row[0])


def test_ofs_g03_the_restatement_key_is_the_estates_own(seeded: str) -> None:
    """`OFS-G03` — the key is declared in an artifact, and it is load-bearing.

    What counts as "the same fact" is a credit-policy judgment wearing numeric
    clothing, so it lives in `artifacts/restatement.yaml` rather than as a
    constant in a module where no reviewer would look for a policy.

    **The gate varies the key rather than asserting a number**, because the
    number alone would keep passing if the key stopped being read. A LOOSER key
    merges facts that were never the same fact and the census goes UP — which
    is the direction a build under time pressure moves it, since 410 looks like
    more findings rather than fewer.
    """
    declared = _restatement_artifact()["fact_identity_key"]
    assert declared == CENSUS["census"]["key"], (
        "the artifact's key and the census fixture's key disagree, so one of"
        f" the two documents is stale: {declared} vs {CENSUS['census']['key']}"
    )

    correct = _restated_cells(seeded, list(declared))
    assert correct == CENSUS["census"]["restatement_cells"], (
        f"the declared key yields {correct} restated cells, not"
        f" {CENSUS['census']['restatement_cells']}"
    )

    # AND THE PRODUCT MUST ACTUALLY READ IT — the half this gate lacked.
    #
    # Everything above compares the artifact against a census written in this
    # module. It never serves the product, so it could not see the product
    # IGNORING the artifact — which is what it was doing: the assembly query
    # hard-coded a partition including `period_start`, a key
    # `artifacts/restatement.yaml` names and rejects, and four real corrections
    # went unreported. The gate was written to catch exactly that and could
    # not. Close-panel finding, 2026-08-31.
    #
    # So the artifact's key is CHANGED and the product re-served. If the
    # detection moves, the product read it. If it does not, the key in force is
    # a constant somewhere in the code.
    from datetime import datetime

    deployment = _load("deployment")
    artifact = deployment.RESTATEMENT
    original = artifact.read_text(encoding="utf-8")
    witness = _witness("key_sensitive_obligor")
    window = {
        "anchor": witness,
        deployment.PARAM_PERIODS: int(
            _expected()["gate_witnesses"]["key_sensitive_periods"]
        ),
        "asked_at": datetime.fromisoformat(
            str(_expected()["gate_witnesses"]["key_sensitive_asked_at"])
        ),
    }

    def flags() -> dict[tuple[str, str], Any]:
        payload = dict(_serve(seeded, **window).product.payload)
        return {
            (str(period["period_end"]), str(name)): line.get("restated")
            for period in payload["periods"]
            for name, line in period["lines"].items()
            if isinstance(line, dict) and "restated" in line
        }

    before = flags()
    assert before, f"{witness} served no cells carrying a restatement flag"
    try:
        artifact.write_text(
            original.replace(
                "    - period_end\n", "    - period_start\n    - period_end\n"
            ),
            encoding="utf-8",
        )
        assert "period_start" in _restatement_artifact()["fact_identity_key"], (
            "the artifact's key was not rewritten, so the comparison below"
            " would be two identical runs"
        )
        after = flags()
    finally:
        artifact.write_text(original, encoding="utf-8")

    assert after != before, (
        "the fact-identity key was lengthened in the artifact and the product"
        " reported exactly the same restatements. The key in force is not the"
        " declared one — it is a constant in the code that happens to agree"
        " with the artifact today"
    )

    short = _restated_cells(seeded, ["lei", "tag", "period_end"])
    assert short == CENSUS["wrong_methods"]["short_key"]["yields"], (
        f"the short key yields {short}, not the"
        f" {CENSUS['wrong_methods']['short_key']['yields']} it is recorded as"
        " producing; the control has stopped discriminating"
    )
    assert short > correct, (
        "a looser key did not inflate the census, so the key is not being"
        " applied at all and the correct number above is a coincidence"
    )


def test_ofs_g04_item_402_corroborates_and_never_detects(seeded: str) -> None:
    """`OFS-G04` — a non-reliance filing is evidence, not the detector.

    Item 4.02 is an 8-K saying "do not rely on our previously issued
    statements." It is the obvious place to look for restatements and it is the
    wrong place to look FROM, for two independent reasons, and this gate
    asserts both because either alone is satisfiable by a broken detector.

    **Most restatements never file one.** 28 of the 37 restated obligors here
    have no 4.02 at all. A detector built on 4.02 would miss three quarters of
    them and report a healthy book.

    **And a 4.02 does not mean a number moved.** Two obligors filed one and
    changed no value in the window. A detector built on 4.02 would report them
    restated, and a credit officer would go looking for a change that is not
    there.
    """
    artifact = _restatement_artifact()
    assert artifact["detected_by"] == "distinct_value_across_accessions", (
        "restatement is no longer declared as detected by value comparison;"
        f" the artifact says {artifact['detected_by']!r}"
    )

    counts = CENSUS["census"]["item_402"]
    assert counts["restated_without_filing"] > 0, (
        "no obligor is restated without a 4.02, so this estate cannot"
        " distinguish a value-comparison detector from a 4.02 detector and the"
        " gate is vacuous here"
    )

    # The decisive half, through the served product: a 4.02 with nothing moved.
    witness = _witness("filed_402_without_value_change")
    assembled = _serve(seeded, anchor=witness)
    payload = dict(assembled.product.payload)
    assert payload["obligor"]["formally_restated"] is True, (
        f"{witness} is declared to carry an Item 4.02 and the payload says it"
        " does not; the witness or the estate has moved"
    )
    # EVERY LINE SHAPE IS CHECKED HERE, NOT ONLY THE REPORTED ONES, AND THE
    # REASON IS THE FIX THAT PRECEDED IT. `_reported_lines` exists because
    # `OFS-G01` was counting placeholders as facts. Used HERE it would do the
    # opposite harm: a broken detector that marked `restated` on a slim,
    # placeholder-shaped line would have those lines filtered away and the gate
    # would pass. A filter that removes noise for one gate removes evidence for
    # another. Close-panel finding, 2026-08-31.
    payload_lines = [
        line
        for period in payload["periods"]
        for line in period["lines"].values()
        if isinstance(line, dict)
    ]
    assert payload_lines, f"{witness} served no lines at all"
    restated = [line for line in payload_lines if line.get("restated") is True]
    assert not restated, (
        f"{witness} filed a 4.02 and changed no value, yet {len(restated)}"
        " lines are reported restated. That is a detector reading the filing"
        " rather than the figures"
    )


def test_ofs_g08_absence_is_a_word_and_never_a_zero(seeded: str) -> None:
    """`OFS-G08` — the revenue-less obligor serves NOT_EVALUABLE, never `0`.

    One obligor of 50 files none of the four revenue tags. Serving `0` would
    describe a company with no sales; the absence of an answer is not an answer
    of zero, and every ratio built on it would inherit the lie silently.

    **The vacuity guard matters here specifically.** A line the obligor never
    filed carries `NOT_EVALUABLE` whatever the code does, so asserting only
    "revenue reads NOT_EVALUABLE" would pass against a product that served the
    token for everything. So the gate also requires this payload to carry real
    reported figures, and requires a DIFFERENT obligor's revenue to be a
    number — proving the product can tell the two cases apart.
    """
    expected = _expected()
    token = expected["not_evaluable_token"]
    witness = _witness("obligor_without_revenue_tag")

    assembled = _serve(seeded, anchor=witness)
    reported = _reported_lines(assembled)
    assert reported, (
        f"{witness} served no reported figures at all, so its NOT_EVALUABLE"
        " revenue proves nothing about the vocabulary of absence"
    )

    payload = dict(assembled.product.payload)
    revenue_values = {
        line.get("value")
        for period in payload["periods"]
        for name, line in period["lines"].items()
        if isinstance(line, dict) and "revenue" in name.lower()
    }
    assert revenue_values, f"{witness}'s payload carries no revenue line at all"
    assert revenue_values == {token}, (
        f"{witness} files no revenue tag, so every revenue figure must read"
        f" {token}; got {sorted(str(v) for v in revenue_values)}"
    )
    assert "0" not in {str(value) for value in revenue_values}, (
        "a revenue of 0 describes a company with no sales, which is not what"
        " this estate knows about this obligor"
    )

    # THE DISCRIMINATION CHECK: another obligor's revenue is a real number.
    other = _serve(seeded, anchor=_witness("full_ratio_block"))
    other_payload = dict(other.product.payload)
    numbers = {
        line.get("value")
        for period in other_payload["periods"]
        for name, line in period["lines"].items()
        if isinstance(line, dict) and "revenue" in name.lower()
    } - {token}
    assert numbers, (
        "no obligor in this estate serves a numeric revenue, so the assertion"
        " above cannot distinguish a working product from one that serves"
        f" {token} for everything"
    )


def test_ofs_g11_basis_changes_the_address_only_where_it_changes_the_answer(
    seeded: str,
) -> None:
    """`OFS-G11` — `basis` is in the content address, and only when it matters.

    `as-reported` and `latest-restated` are BOTH correct answers to different
    questions: what the obligor said at the time, and what it says now. The
    decision picks. So the two must be addressable separately — an identical
    content address would make a cache serve one for the other.

    **Both halves are required.** A `basis` folded into the hash
    unconditionally satisfies the first half while telling you nothing: for an
    obligor with no restatement in the window the two answers are the same
    document, and a differing address there would mean the address is keyed on
    the question rather than on the answer.
    """
    from ccf.contracts.canonical import content_hash

    deployment = _load("deployment")

    def figures(lei: str, basis: str) -> dict[tuple[str, str], Any]:
        """Every figure by period and line name — VALUES ONLY, not provenance.

        `accession` is deliberately excluded, and measuring taught the reason.
        For an unrestated obligor the two bases return the SAME NUMBER from
        DIFFERENT FILINGS: `as-reported` names the filing that first reported
        it, `latest-restated` the most recent one to repeat it, and the figure
        being equal across those filings is precisely what makes the obligor
        unrestated. Comparing provenance would fail correct data.
        """
        assembled = _serve(seeded, anchor=lei, **{deployment.PARAM_BASIS: basis})
        payload = dict(assembled.product.payload)
        return {
            (str(period["period_end"]), str(name)): line.get("value")
            for period in payload["periods"]
            for name, line in period["lines"].items()
            if isinstance(line, dict)
        }

    def address(lei: str, basis: str) -> str:
        assembled = _serve(seeded, anchor=lei, **{deployment.PARAM_BASIS: basis})
        return str(content_hash(assembled.product))

    restated = _witness("restated_in_window")
    unrestated = _witness("unrestated_in_window")

    # THE FIGURES ARE ASSERTED, NOT ONLY THE ADDRESS, AND SABOTAGE IS WHY.
    # A first version asserted only that the two content addresses differ for a
    # restated obligor. It survived a sabotage that stopped `basis` selecting
    # the filing at all — because the payload ECHOES `basis_applied` on every
    # line, so the two documents differ whatever the figures do. The address
    # test could not tell "the basis changed the answer" from "the basis
    # appeared in the document". It is the third time in this module that a
    # check read a token present in both the compliant and the violating case.
    assert figures(restated, "as-reported") != figures(
        restated, "latest-restated"
    ), (
        f"{restated} carries a restatement in the window and NO FIGURE moved"
        " between the two bases. The basis is not selecting which filing's"
        " value wins, so the two answers are the same answer under two names"
    )
    assert address(restated, "as-reported") != address(restated, "latest-restated"), (
        f"{restated}'s two answers differ and share a content address; a cache"
        " would serve one for the other"
    )

    # THE OTHER HALF, AS AMENDED. §D.4 and criterion 38 once required IDENTICAL
    # content addresses for an obligor with no restatement in the window. That
    # could not hold as built, and `D-IMPL-222` (Dave, 2026-08-31) amended the
    # criterion rather than the product.
    #
    # The first report of the conflict said the payload merely echoes
    # `basis_applied`, which was incomplete. Measured field by field: the label
    # differs on 75 of 75 cells, but `accession` and `filed_date` differ on 20
    # of 75 — the two bases genuinely READ DIFFERENT FILINGS and report the same
    # number from each. No `value` moves. So the answer is identical and the
    # DOCUMENT is not, and the content address seals the document.
    #
    # Making the addresses match would have required suppressing provenance
    # wherever the value agreed, which deletes a true fact to make a hash match
    # at the rung whose subject is which filing asserted which figure. What is
    # asserted here is what the criterion was reaching for.
    assert figures(unrestated, "as-reported") == figures(
        unrestated, "latest-restated"
    ), (
        f"{unrestated} carries no restatement, so no figure may move between"
        " the two bases. A figure that moves here means the basis is being"
        " applied to facts that were never restated"
    )


def test_ofs_g12_every_derived_line_names_what_it_consumed(seeded: str) -> None:
    """`OFS-G12` — a ratio names its inputs, and they are in the same payload.

    A derived figure with no lineage is a number a credit officer cannot check.
    The obligation is closed over the payload: every name in `inputs` resolves
    to a line present in the SAME period of the SAME served document, so a
    reader needs nothing but what they were handed.

    **The witness is NOT the demonstration anchor, and that is the whole
    subtlety.** The anchor files no depreciation, so EBITDA and its three
    dependents are permanently NOT_EVALUABLE and carry no inputs — a gate run
    against it would check zero derived lines and report green. That is exactly
    the vacuity `OFS-G01` was caught having. The witness is the obligor that
    carries the full ratio block, and the count of lines checked is asserted to
    be non-zero rather than assumed.
    """
    expected = _expected()
    token = expected["not_evaluable_token"]
    assembled = _serve(seeded, anchor=_witness("full_ratio_block"))
    payload = dict(assembled.product.payload)

    checked = 0
    for period in payload["periods"]:
        names = set(period["lines"])
        for name, line in period["lines"].items():
            if not isinstance(line, dict) or not line.get("derived"):
                continue
            if line.get("value") == token:
                continue  # nothing was computed, so nothing was consumed
            checked += 1
            inputs = line.get("inputs")
            assert inputs, (
                f"derived line {name!r} in {period['period_end']} carries a"
                " value and no inputs; the figure cannot be checked"
            )
            for consumed in inputs:
                assert consumed in names, (
                    f"{name!r} names input {consumed!r}, which is not a line in"
                    " the same period of this payload. The lineage is not"
                    " closed over the document the reader was handed"
                )

    assert checked > 0, (
        "no evaluable derived line was checked, so this gate asserted nothing."
        " The witness must be an obligor that actually computes ratios"
    )


def test_ofs_g13_the_severity_threshold_comes_from_the_artifact(
    seeded: str,
) -> None:
    """`OFS-G13` — moving the artifact's threshold moves cells between classes.

    Whether a 0.8% correction is *material* or *precision* is a credit-policy
    judgment. §E.5 measured the distribution and found it continuous from
    rounding to restatement with no natural gap, so there is no number the data
    could have supplied — it has to be declared, and declared where a reviewer
    looks.

    **The gate rewrites the artifact and re-serves.** Asserting that the served
    classes merely LOOK right would pass against a hard-coded constant that
    happens to match the artifact today. Changing the declaration and watching
    the answer move is the only check that distinguishes reading from
    coinciding. The artifact is restored in a `finally`.
    """
    deployment = _load("deployment")
    artifact = deployment.RESTATEMENT
    original = artifact.read_text(encoding="utf-8")
    declared = _restatement_artifact()["material_threshold"]

    def classes(lei: str) -> set[str]:
        assembled = _serve(seeded, anchor=lei)
        return {
            str(line.get("restatement_class"))
            for line in _reported_lines(assembled)
            if line.get("restated") is True
        }

    anchor = _witness("restated_in_window")
    before = classes(anchor)
    assert before, (
        f"{anchor} serves no restated line, so no cell can change class and"
        " this gate would pass without asking its question"
    )

    try:
        artifact.write_text(
            original.replace(
                f'material_threshold: "{declared}"', 'material_threshold: "0.99"'
            ),
            encoding="utf-8",
        )
        assert _restatement_artifact()["material_threshold"] == "0.99", (
            "the artifact was not rewritten, so the comparison below would be"
            " two identical runs"
        )
        after = classes(anchor)
    finally:
        artifact.write_text(original, encoding="utf-8")

    assert after != before, (
        f"the material threshold moved from {declared} to 0.99 and every cell"
        f" kept its class ({sorted(before)}). The classification is not"
        " reading the artifact — it is a constant that happens to agree with"
        " it today"
    )
