"""CP-00's assertions, under a runner that can actually fail.

``examples/cp-00-institutional-holders/run.py`` prints; it asserts nothing. The
assertions live here, because an assertion inside a driver only fails a build if
somebody remembers to run the driver.

**The example points at a real 13F estate; this module does not.** Locally the
example reads the store `backends.yaml` names through an environment variable
(`24-CONTEXT.md` `D-15`, which accepts that cost deliberately). CI cannot reach
that host, so this module seeds a `postgres:16` service container **itself**
from `tests/examples/fixtures/cp_00_13f_schema.sql` and
`cp_00_13f_rows.sql`, and runs the example's own modules against it —
`24-CONTEXT.md` `D-25` and `D-27`: *the fixture is seeded by the test, never
committed as a database.* One code path, two substrates.

**The expected answer is never inlined.** It is computed by issuing the very
``SELECT`` this example argues against — the group-and-rank that finds the
dominant security, then the pinned, thresholded read over the same seeded rows.
A count this module authored would be the test agreeing with itself. Every
domain value it needs comes from the example's own artifacts or from the seeded
table; `tools/lints/no_hardcoding.py`'s `RULE_TREE_SCOPE` includes ``tests``,
and the discipline is the point rather than the lint.

**There is no ``issuer_match_band`` filter, and nothing here may add one.**
`24-CONTEXT.md` `D-61`: the specification, the data probe and
``artifacts/expected.yaml`` all rule against one, and applying it would be a
silent 6.6% under-count. The band travels with the row and is filtered nowhere.
The fixture seeds three ``weak`` rows on the *dominant* security precisely so
that a band filter, if one were ever introduced, would change an assertion here.

Marked ``postgres``: every fixture requests the session-scoped ``postgres_dsn``.
Unset ``CCF_TEST_POSTGRES_DSN`` starts a container; ``CCF_REQUIRE_POSTGRES``
turns a skip into a failure. ``make leg-postgres`` is what runs this module.
"""

from __future__ import annotations

import contextlib
import importlib
import io
import json
import os
import pathlib
import re
import sys
from datetime import timedelta
from typing import Any

import psycopg
import pytest
import yaml

from ccf.agents.assembler import (
    NO_CONSULTATIONS,
    AssemblyOutcome,
    ContextAssemblerProtocol,
)
from ccf.agents.errors import AssemblyRefused
from ccf.contracts.canonical import content_hash
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.products.contract import (
    ContextProductContract,
    MaxTTL,
    ProductLineage,
    register_product_class,
)
from ccf.products.gates import (
    LineageMismatchRefusal,
    ServableProduct,
    run_gates,
)
from ccf.products.request import ProductRequestViolation
from ccf.replay.record import DecisionReplayRecord

pytestmark = pytest.mark.postgres

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE = REPO_ROOT / "examples" / "cp-00-institutional-holders"
FIXTURES = pathlib.Path(__file__).parent / "fixtures"
SCHEMA_SQL = FIXTURES / "cp_00_13f_schema.sql"
ROWS_SQL = FIXTURES / "cp_00_13f_rows.sql"

#: The section letters the Standard's skeleton fixes. Structure, not domain
#: vocabulary: the heading text itself lives in the specification.
SECTION_LETTERS = tuple("ABCDEFG")

#: What ``run.py`` prints between the specification and the JSON.
DATASET_BANNER = "THE DATASET THE SPECIFICATION ABOVE DESCRIBES"

#: The first line of the report ``run.py`` prints *below* the JSON.
REPORT_BANNER = "What a plain SELECT would not have told you:"


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


# --------------------------------------------------------------------------
# Seeding the container, and PROVING the seed happened.
# --------------------------------------------------------------------------
def declared_rows(sql_text: str, *, table: str) -> int:
    """How many value tuples ``sql_text`` declares for ``table``.

    A predicate over its subject rather than a second description of the
    fixture: :func:`test_the_seeder_seeded` feeds it the real file AND a copy
    with rows removed, so the instrument is shown to move.
    """
    statements = [
        chunk for chunk in sql_text.split("insert into") if table in chunk.split("\n")[0]
    ]
    return sum(
        len(re.findall(r"(?m)^\s{4}\('", statement)) for statement in statements
    )


def _dsn_variable() -> str:
    """The environment-variable NAME ``backends.yaml`` declares for the source.

    Read out of the artifact through the deployment's own key constants, so a
    rename of the variable moves one document and this module follows.
    """
    deployment = _load("deployment")
    document = yaml.safe_load(deployment.BACKENDS.read_text(encoding="utf-8"))
    source = document[deployment.DECLARATION][deployment.SOURCES]
    binding = source[deployment.SOURCE_BINDING][deployment.SETTINGS]
    return str(binding[deployment.SOURCE_SETTING_DSN][deployment.FROM_ENV])


@pytest.fixture(scope="module")
def seeded(postgres_dsn: str) -> Any:
    """A seeded container, with the DSN exported where `backends.yaml` reads it.

    `D-27`: the test seeds; nothing is committed as a database. Both statements
    are `if not exists` / `on conflict do update`, so a repeated leg against a
    long-lived server converges rather than failing.
    """
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


def _count(dsn: str, *, lei: str) -> int:
    """Rows in the holdings table for one issuer — figure and control alike."""
    deployment = _load("deployment")
    with psycopg.connect(dsn) as db, db.cursor() as cursor:
        cursor.execute(  # noqa: S608 — names come from the deployment's own block
            f"select count(*) from {deployment.SOURCE_SCHEMA}"  # noqa: S608
            f".{deployment.TABLE_HOLDINGS}"
            f" where {deployment.COLUMN_ISSUER_LEI} = %s",
            (lei,),
        )
        return int(cursor.fetchone()[0])


def _anchor() -> str:
    """The anchor issuer LEI, from the example's own question artifact."""
    deployment = _load("deployment")
    document = yaml.safe_load(deployment.QUESTION.read_text(encoding="utf-8"))
    return str(document[deployment.DECLARATION]["subject"])


def test_the_seeder_seeded(seeded: str) -> None:
    """A silent seed would make several assertions below pass against nothing.

    Both numbers are in the message, and the control returns a DIFFERENT one:
    the same query with an impossible LEI returns 0 while the real predicate
    returns the fixture's own row count. A count with no control is not a
    measurement.
    """
    deployment = _load("deployment")
    declared = declared_rows(
        ROWS_SQL.read_text(encoding="utf-8"), table=deployment.TABLE_HOLDINGS
    )
    # NON-VACUITY: the instrument moves when its subject does. Feeding it the
    # fixture with every value tuple stripped must return zero, or the count
    # above proves nothing about the file it read.
    stripped = re.sub(
        r"(?m)^\s{4}\('.*$", "", ROWS_SQL.read_text(encoding="utf-8")
    )
    assert (
        declared_rows(stripped, table=deployment.TABLE_HOLDINGS) == 0
    ), "the row counter does not read the file it is handed"
    assert declared > 0, "the fixture declares no rows — the parser or the file"

    figure = _count(seeded, lei=_anchor())
    control = _count(seeded, lei="__NO_SUCH_LEI__")
    assert figure == declared and control == 0, (
        f"seeded rows for the anchor = {figure}, the fixture declares"
        f" {declared}, and the impossible-LEI control returns {control}"
    )


# --------------------------------------------------------------------------
# The oracle: the SELECT this example argues against.
# --------------------------------------------------------------------------
def _dominant_cusip(dsn: str) -> str:
    """The dominant security, re-derived by plain SQL.

    This is the one-big-query a data engineer writes instead of building a
    Context Product, and that is exactly why it is the oracle: the fabric must
    reach the same security by a different route.

    The tie-break is deliberately NOT load-bearing here — the operator breaks
    ties on the security's URI, which is a content hash and therefore not in
    CUSIP order. :func:`test_the_resolve_reaches_the_same_security` asserts the
    top count is strictly greater than the second, so the two orderings cannot
    disagree on this fixture.
    """
    deployment = _load("deployment")
    with psycopg.connect(dsn) as db, db.cursor() as cursor:
        cursor.execute(
            f"select {deployment.COLUMN_CUSIP}, count(*)"  # noqa: S608
            f" from {deployment.SOURCE_SCHEMA}.{deployment.TABLE_HOLDINGS}"
            f" where {deployment.COLUMN_ISSUER_LEI} = %s"
            f" and {deployment.COLUMN_PERIOD} = %s"
            f" group by 1 order by 2 desc, 1 asc",
            (_anchor(), deployment.reported_period()),
        )
        return cursor.fetchall()


def _oracle(dsn: str, threshold: int, *, comparison: str) -> list[tuple[str, str]]:
    """The pinned, thresholded read, ordered as `expected.yaml` declares.

    ``comparison`` is a parameter rather than a constant so
    :func:`test_a_row_exactly_at_the_threshold_is_served` can ask the SAME
    instrument for both ``>=`` and ``>`` and compare the two answers.
    """
    deployment = _load("deployment")
    with psycopg.connect(dsn) as db, db.cursor() as cursor:
        cursor.execute(
            f"select {deployment.COLUMN_MANAGER_CIK},"  # noqa: S608
            f" {deployment.COLUMN_VALUE}"
            f" from {deployment.SOURCE_SCHEMA}.{deployment.TABLE_HOLDINGS}"
            f" where {deployment.COLUMN_ISSUER_LEI} = %s"
            f" and {deployment.COLUMN_PERIOD} = %s"
            f" and {deployment.COLUMN_CUSIP} = %s"
            f" and {deployment.COLUMN_VALUE} {comparison} %s"
            f" order by {deployment.COLUMN_VALUE} desc,"
            f" {deployment.COLUMN_MANAGER_CIK} asc",
            (
                _anchor(),
                deployment.reported_period(),
                _dominant_cusip(dsn)[0][0],
                threshold,
            ),
        )
        return [(row[0], str(row[1])) for row in cursor.fetchall()]


def _thresholds(dsn: str) -> tuple[int, int, int]:
    """Three thresholds the SEEDED estate separates, none of them authored here.

    ``low`` is the smallest position on the dominant security, so it admits
    every assembled row including the ``weak``-band ones. ``high`` is the
    demonstration threshold the example's own question artifact declares.
    ``exact`` is a value some seeded row carries EXACTLY, with rows both above
    and below it — the case §F marker 14 requires the CI fixture to contain,
    because product gate `IH-G04` cannot fail without one.
    """
    deployment = _load("deployment")
    table = f"{deployment.SOURCE_SCHEMA}.{deployment.TABLE_HOLDINGS}"
    where = (
        f" where {deployment.COLUMN_ISSUER_LEI} = %s"
        f" and {deployment.COLUMN_PERIOD} = %s"
        f" and {deployment.COLUMN_CUSIP} = %s"
    )
    bind = (_anchor(), deployment.reported_period(), _dominant_cusip(dsn)[0][0])
    with psycopg.connect(dsn) as db, db.cursor() as cursor:
        cursor.execute(
            f"select min({deployment.COLUMN_VALUE}) from {table}{where}",  # noqa: S608
            bind,
        )
        low = int(cursor.fetchone()[0])
        cursor.execute(
            f"select h.{deployment.COLUMN_VALUE} from {table} h"  # noqa: S608
            f"{where.replace(deployment.COLUMN_ISSUER_LEI, 'h.' + deployment.COLUMN_ISSUER_LEI)}"
            f" and exists (select 1 from {table} a{where}"
            f" and a.{deployment.COLUMN_VALUE} > h.{deployment.COLUMN_VALUE})"
            f" and exists (select 1 from {table} b{where}"
            f" and b.{deployment.COLUMN_VALUE} < h.{deployment.COLUMN_VALUE})"
            f" order by h.{deployment.COLUMN_VALUE} desc limit 1",
            bind + bind + bind,
        )
        exact = int(cursor.fetchone()[0])
    return low, deployment.demonstration_threshold(), exact


# --------------------------------------------------------------------------
# Running the example.
# --------------------------------------------------------------------------
class _Recorder:
    """Holds whatever one assembly produced — the client's own shape."""

    def __init__(self) -> None:
        self.seen: object = None

    def __call__(self, assembled: object) -> None:
        self.seen = assembled


def _assembler(root: pathlib.Path, recorder: _Recorder) -> Any:
    deployment = _load("deployment")
    assembler = _load("assembler")
    # `run.py` hands the assembler a `tempfile.TemporaryDirectory()`, which
    # exists by the time it is passed. A pytest `tmp_path` subdirectory does
    # not, and the sqlite backend does not create parents.
    root.mkdir(parents=True, exist_ok=True)
    return assembler.HoldersAssembler(
        config=deployment.CONFIG,
        root=root,
        connection=deployment.connection(root=root),
        read=deployment.read,
        plan_class=deployment.plan_class(),
        observer=recorder,
    )


def _ask(root: pathlib.Path, parameters: Any, **kwargs: Any) -> tuple[Any, Any]:
    """One assembly through the assembler seam. Returns (outcome, observed)."""
    deployment = _load("deployment")
    recorder = _Recorder()
    outcome = _assembler(root, recorder).assemble(
        request=deployment.request(parameters=parameters, **kwargs),
        perspective=deployment.perspective(),
        tenant_id=deployment.tenant_id(),
    )
    assert isinstance(outcome, AssemblyOutcome)
    return outcome, recorder.seen


def _over(root: pathlib.Path, threshold: int, **kwargs: Any) -> tuple[Any, Any]:
    deployment = _load("deployment")
    return _ask(root, {deployment.THRESHOLD_PARAMETER: threshold}, **kwargs)


# --------------------------------------------------------------------------
# 1 — the threshold selects.
# --------------------------------------------------------------------------
def test_the_resolve_reaches_the_same_security(
    tmp_path: pathlib.Path, seeded: str
) -> None:
    """Step 1's answer, cross-checked against a plain group-and-rank."""
    fanout = _dominant_cusip(seeded)
    assert len(fanout) > 1, f"the fixture fans out to {len(fanout)} security"
    assert fanout[0][1] > fanout[1][1], (
        f"the top two candidate counts are {fanout[0][1]} and {fanout[1][1]};"
        " a tie would make the oracle's tie-break load-bearing and it is not"
        " the operator's"
    )
    low, _high, _exact = _thresholds(seeded)
    _outcome, observed = _over(tmp_path / "resolve", low)
    resolved = observed.product.payload["resolved_security"]
    assert resolved["cusip"] == fanout[0][0]
    assert resolved["candidates_considered"] == len(fanout)


def test_the_threshold_selects(tmp_path: pathlib.Path, seeded: str) -> None:
    """The payload equals the SELECT oracle, row for row."""
    deployment = _load("deployment")
    low, high, _exact = _thresholds(seeded)
    assert low < high, f"the fixture does not separate {low} from {high}"

    _outcome, observed = _over(tmp_path / "low", low)
    payload = observed.product.payload
    expected = _oracle(seeded, low, comparison=deployment.COMPARISON)
    assert payload["count"] == len(expected)
    assert [
        (entry["manager_cik"], entry["value_usd"]) for entry in payload["holders"]
    ] == expected

    _served, above = _over(tmp_path / "high", high)
    assert above.product.payload["count"] == len(
        _oracle(seeded, high, comparison=deployment.COMPARISON)
    )
    assert above.product.payload["count"] < payload["count"], (
        "a fixture where every row passes the threshold proves the threshold"
        " exists, not that it does anything"
    )


def test_a_row_exactly_at_the_threshold_is_served(
    tmp_path: pathlib.Path, seeded: str
) -> None:
    """`>=`, not `>` — §F marker 14 and product gate `IH-G04`.

    The value is read out of the seeded table, not written down here, and the
    control is the SAME oracle asked with the strict comparison: it must return
    strictly fewer rows, or the fixture holds no row at the threshold and the
    assertion above it is vacuous.
    """
    deployment = _load("deployment")
    _low, _high, exact = _thresholds(seeded)
    inclusive = _oracle(seeded, exact, comparison=deployment.COMPARISON)
    strict = _oracle(seeded, exact, comparison=">")
    assert len(inclusive) == len(strict) + 1, (
        f"at {exact} the inclusive read returns {len(inclusive)} and the strict"
        f" read {len(strict)}; the fixture must hold exactly one row AT the"
        " threshold for this gate to be able to fail"
    )
    _outcome, observed = _over(tmp_path / "exact", exact)
    assert observed.product.payload["count"] == len(inclusive)
    assert observed.product.payload["threshold"]["comparison"] == deployment.COMPARISON


def test_the_band_is_carried_and_filtered_nowhere(
    tmp_path: pathlib.Path, seeded: str
) -> None:
    """`D-61`: there is no band filter, and this is what would catch one.

    The fixture seeds ``weak``-band rows on the DOMINANT security. If a band
    filter were ever introduced the served count would fall below the oracle's
    and this assertion would go red — which is the whole reason those rows are
    in the fixture.
    """
    deployment = _load("deployment")
    low, _high, _exact = _thresholds(seeded)
    _outcome, observed = _over(tmp_path / "band", low)
    bands = {entry["issuer_match_band"] for entry in observed.product.payload["holders"]}
    assert len(bands) > 1, (
        f"only the band(s) {sorted(bands)} reached the payload; either the"
        " fixture lost its weak rows or something is filtering on the band"
    )
    assert observed.product.payload["count"] == len(
        _oracle(seeded, low, comparison=deployment.COMPARISON)
    )


# --------------------------------------------------------------------------
# 2, 3 — identity, not content.
# --------------------------------------------------------------------------
def test_two_thresholds_are_two_products(
    tmp_path: pathlib.Path, seeded: str
) -> None:
    """THE test. A Context Product is not a precalculated static object.

    The caller's number is part of the question, so it is part of the product's
    content address. Two thresholds, two addresses.
    """
    low, high, _exact = _thresholds(seeded)
    _a, first = _over(tmp_path / "low", low)
    _b, second = _over(tmp_path / "high", high)
    assert content_hash(first.product) != content_hash(second.product)


def test_the_same_question_is_stable(tmp_path: pathlib.Path, seeded: str) -> None:
    """Identical question, identical address — determinism, not coincidence."""
    low, _high, _exact = _thresholds(seeded)
    _a, first = _over(tmp_path / "first", low)
    _b, second = _over(tmp_path / "second", low)
    assert content_hash(first.product) == content_hash(second.product)


# --------------------------------------------------------------------------
# 4 — refused at the door.
# --------------------------------------------------------------------------
def test_a_missing_threshold_is_refused_not_defaulted(
    tmp_path: pathlib.Path, seeded: str
) -> None:
    """Refused as DATA, before anything is assembled.

    Asserted at the SPINE, where the verdict is a returned value:
    ``produce.assemble_and_serve`` returns the
    ``src/ccf/products/request.py::ProductRequestViolation`` rather than raising
    it, and it carries no product.

    The assembler seam then has to RAISE, and that is the SDK finding Wave 5
    recorded rather than a property of this deployment: `24-CONTEXT.md` `D-60`
    — ``ContextAssemblerProtocol.assemble`` is typed to return an
    ``AssemblyOutcome`` and nothing else, so a conforming assembler holding a
    governed refusal has exactly one channel. Recorded, deliberately not closed
    in this phase, and asserted here in both shapes so that closing it later
    changes an assertion rather than passing silently.
    """
    deployment = _load("deployment")
    produce = _load("produce")
    root = tmp_path / "none"
    root.mkdir(parents=True, exist_ok=True)
    violation = produce.assemble_and_serve(
        config=deployment.CONFIG,
        connection=deployment.connection(root=root),
        read=deployment.read,
        plan_class=deployment.plan_class(),
        request=deployment.request(parameters={}),
        root=root,
    )
    assert isinstance(violation, ProductRequestViolation)
    assert violation.reason == "missing-required-parameter"
    assert violation.key == deployment.THRESHOLD_PARAMETER
    assert not hasattr(violation, "product")

    # D-60 CLOSED (24.1.1-03). This leg used to assert `pytest.raises` and then
    # reach around the exception into the observer for the typed value; its own
    # docstring said it was written in both shapes "so that closing it later
    # changes an assertion rather than passing silently." This is that change.
    # The seam now RETURNS the governed refusal, so the client branches on a
    # value and the observer reach-around is gone.
    recorder = _Recorder()
    returned = _assembler(tmp_path / "seam", recorder).assemble(
        request=deployment.request(parameters={}),
        perspective=deployment.perspective(),
        tenant_id=deployment.tenant_id(),
    )
    assert isinstance(returned, ProductRequestViolation), type(returned)
    assert returned.key == deployment.THRESHOLD_PARAMETER
    assert returned.reason == "missing-required-parameter"


# --------------------------------------------------------------------------
# 5 — the assembler seam is the path.
# --------------------------------------------------------------------------
def test_the_assembler_seam_is_the_path(
    tmp_path: pathlib.Path, seeded: str
) -> None:
    """The run goes through ``ContextAssemblerProtocol``, and conforms to it."""
    deployment = _load("deployment")
    low, _high, _exact = _thresholds(seeded)
    recorder = _Recorder()
    seam = _assembler(tmp_path / "seam", recorder)
    assert isinstance(seam, ContextAssemblerProtocol)

    outcome = seam.assemble(
        request=deployment.request(
            parameters={deployment.THRESHOLD_PARAMETER: low}
        ),
        perspective=deployment.perspective(),
        tenant_id=deployment.tenant_id(),
    )
    # D-60: the seam returns a union now. The branch is redundant for the
    # type-checker here (the receiver's type is concrete) and is written
    # anyway, because criterion 8 says EVERY call site and a site that does
    # not branch reads as one written before the widening.
    assert isinstance(outcome, AssemblyOutcome)
    assembler = _load("assembler")
    assert isinstance(outcome, AssemblyOutcome)
    assert outcome.assembler_id == assembler.ASSEMBLER_ID
    assert outcome.assembler_version == assembler.ASSEMBLER_VERSION
    # Named claims, not a forgotten record: this assembly reached for nothing
    # outside itself, acquired nothing at decision time and bound no skill.
    assert outcome.consultations == NO_CONSULTATIONS
    assert outcome.acquisitions == ()
    assert outcome.skill_set_in_force == ()

    # Keyword-only, because the Protocol declares it so and says why: the cost
    # of a transposition would be an assembly attributed to the wrong tenant.
    with pytest.raises(TypeError):
        seam.assemble(  # type: ignore[misc]
            deployment.request(parameters={deployment.THRESHOLD_PARAMETER: low}),
            deployment.perspective(),
            deployment.tenant_id(),
        )


# --------------------------------------------------------------------------
# 6 — the gate result is RECORDED, not assumed.
# --------------------------------------------------------------------------
def test_the_gate_result_is_recorded_not_assumed(
    tmp_path: pathlib.Path, seeded: str
) -> None:
    """Holding a ``ServableProduct`` is evidence only if a refusal can happen.

    ``ServableProduct`` is not constructible outside ``run_gates`` — the
    metaclass refuses with ``GateBypassError`` (INV-CH7-52) — so the run
    holding one IS the evidence the three gates ran. That is worth nothing
    unless the alternative branch is REACHABLE, so the same call is issued a
    second time over a candidate whose DECLARED lineage carries an operator the
    engine did not resolve, and gate 2's strict equality must return a
    ``LineageMismatchRefusal`` rather than a ``ServableProduct``.
    """
    low, _high, _exact = _thresholds(seeded)
    _outcome, observed = _over(tmp_path / "gate", low)
    assert isinstance(observed.gated, ServableProduct)

    scenario = observed.scenario
    declared = scenario.product_class
    registry = ControlPlaneRegistry()
    max_ttl_version = registry.register(
        declared.max_ttl_key, MaxTTL(seconds=scenario.max_ttl_seconds)
    )
    request_contract_version = registry.register(
        scenario.request_contract_key, scenario.request_contract
    )
    product_class = register_product_class(
        registry=registry,
        schema_name=declared.schema_name,
        schema_version=declared.schema_version,
        ttl_anchor=declared.ttl_anchor,
        assembly_mode=declared.assembly_mode,
        max_ttl_key=declared.max_ttl_key,
        max_ttl_version=max_ttl_version,
        request_contract_key=scenario.request_contract_key,
        request_contract_version=request_contract_version,
    )

    # CONTROL FIRST: the unmodified candidate must still pass, or a refusal
    # below would be evidence of the re-registration rather than of the gate.
    passing = run_gates(
        observed.product,
        engine_resolved=observed.operators_invoked,
        now=scenario.now,
        registry=registry,
        product_class=product_class,
    )
    assert isinstance(passing, ServableProduct)

    lineage = observed.product.lineage
    candidate = observed.product.model_copy(
        update={
            "lineage": ProductLineage(
                operators_invoked=lineage.operators_invoked
                | frozenset({"traversal.an-operator-that-did-not-run"}),
                policy_bundle_versions=lineage.policy_bundle_versions,
                graph_snapshot_at=lineage.graph_snapshot_at,
            )
        }
    )
    refusal = run_gates(
        candidate,
        engine_resolved=observed.operators_invoked,
        now=scenario.now,
        registry=registry,
        product_class=product_class,
    )
    assert isinstance(refusal, LineageMismatchRefusal), (
        f"gate 2 returned {type(refusal).__name__} for a candidate declaring an"
        " operator the engine never resolved; the refusal branch is not"
        " reachable and holding a ServableProduct therefore proves nothing"
    )


# --------------------------------------------------------------------------
# 7 — the payload validates against the DECLARED contract.
# --------------------------------------------------------------------------
def _declared_shape() -> dict[str, Any]:
    """``artifacts/expected.yaml``'s declaration — which derives nothing from a run."""
    deployment = _load("deployment")
    document = yaml.safe_load(
        (deployment.ARTIFACTS / "expected.yaml").read_text(encoding="utf-8")
    )
    return dict(document[deployment.DECLARATION])


def payload_shape_violations(payload: Any, declared: dict[str, Any]) -> list[str]:
    """Every way ``payload`` departs from what ``expected.yaml`` declares.

    A predicate over its subject, so :func:`test_the_printed_specification_and_json_are_non_empty_and_the_json_validates`
    can feed it the printed bytes with one key removed and watch it name the
    key. A checker that has never refused anything is a checker nobody tested.
    """
    problems: list[str] = []
    if set(payload) != set(declared["payload_keys"]):
        problems += [
            f"payload is missing {key}"
            for key in sorted(set(declared["payload_keys"]) - set(payload))
        ]
        problems += [
            f"payload carries undeclared {key}"
            for key in sorted(set(payload) - set(declared["payload_keys"]))
        ]
    for key in declared["payload_keys_forbidden"]:
        if key in payload:
            problems.append(f"payload carries forbidden {key}")

    nested = {
        "issuer": "issuer_keys",
        "resolved_security": "resolved_security_keys",
        "threshold": "threshold_keys",
    }
    for block, declaration in nested.items():
        if block in payload and set(payload[block]) != set(declared[declaration]):
            problems.append(
                f"{block} keys {sorted(payload[block])} !="
                f" {sorted(declared[declaration])}"
            )
    for index, entry in enumerate(payload.get("holders", ())):
        if set(entry) != set(declared["holder_keys"]):
            problems.append(
                f"holders[{index}] keys {sorted(entry)} !="
                f" {sorted(declared['holder_keys'])}"
            )
    return problems


def test_the_payload_validates_against_the_declared_contract(
    tmp_path: pathlib.Path, seeded: str
) -> None:
    """The IN-PROCESS vessel: a typed contract, shaped as the artifact declares."""
    declared = _declared_shape()
    low, _high, _exact = _thresholds(seeded)
    _outcome, observed = _over(tmp_path / "shape", low)
    assert isinstance(observed.product, ContextProductContract)
    assert observed.product.plan_id == declared["plan_id"]
    assert observed.product.schema_name == declared["schema_name"]
    assert observed.product.lineage.operators_invoked == frozenset(
        declared["operator_keys"]
    )
    assert payload_shape_violations(observed.product.payload, declared) == []


# --------------------------------------------------------------------------
# 8 — the PRINTED bytes: non-empty specification, valid JSON, valid SHAPE.
# --------------------------------------------------------------------------
def _is_rule(line: str) -> bool:
    """A blank line or one of ``run.py``'s separator rules."""
    stripped = line.strip()
    return not stripped or set(stripped) == {"="}


def _sections(printed: str) -> tuple[str, str]:
    """Split what ``run.py`` printed into (specification, json).

    Split on the banners the driver writes rather than on line offsets, so the
    specification growing a section leaves this parser alone. The rules around
    the banner are walked off from both sides: an EMPTY specification prints as
    a blank line above the same rule, and the walk has to reach zero for
    :func:`specification_problems` to be able to see it.
    """
    lines = printed.splitlines()
    banner = next(i for i, line in enumerate(lines) if DATASET_BANNER in line)
    head = banner
    while head > 0 and _is_rule(lines[head - 1]):
        head -= 1
    body = banner + 1
    while body < len(lines) and _is_rule(lines[body]):
        body += 1
    tail = next(
        (i for i, line in enumerate(lines) if REPORT_BANNER in line), len(lines)
    )
    return "\n".join(lines[:head]), "\n".join(lines[body:tail])


def specification_section(printed: str) -> str:
    """Everything ``run.py`` printed above the dataset banner."""
    return _sections(printed)[0]


def json_section(printed: str) -> str:
    """The bytes between the dataset banner and the governance report."""
    return _sections(printed)[1]


def specification_problems(section: str) -> list[str]:
    """Why ``section`` is not a printed specification."""
    problems: list[str] = []
    if not section.strip():
        problems.append("the specification section is empty")
    problems += [
        f"no Section {letter} heading"
        for letter in SECTION_LETTERS
        if f"## Section {letter} " not in section
    ]
    return problems


@pytest.fixture(scope="module")
def printed(seeded: str) -> str:
    """One run of ``run.py``'s own ``main``, with stdout captured.

    In process rather than in a subprocess, so the specification path can be
    repointed for the control below without a second copy of the tree.
    """
    run = _load("run")
    buffer = io.StringIO()
    argv = sys.argv
    sys.argv = [str(EXAMPLE / "run.py")]
    try:
        with contextlib.redirect_stdout(buffer):
            assert run.main() == 0
    finally:
        sys.argv = argv
    return buffer.getvalue()


def test_the_client_returns_a_non_zero_exit_code_on_a_governed_refusal(
    seeded: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The client's D-60 branch, gated.

    This test exists because deleting that branch from ``run.py`` was watched
    to leave the whole cp-00 suite GREEN: both existing ``run.main()``
    invocations assert ``== 0``, so nothing exercised the refusal path through
    the client and the branch could have been removed unnoticed. A happy-path
    assertion is not a gate on the unhappy path.

    The refusal is provoked the way the specification control above provokes an
    empty spec — by repointing a deployment value — because ``run.py`` always
    supplies the declared threshold and can never refuse on its own arguments.
    """
    run = _load("run")
    deployment = _load("deployment")
    original = deployment.request

    def _without_the_threshold(**kwargs: Any) -> Any:
        # The parameters the client supplies are dropped, so the question
        # reaching the seam is the one the tripwire above uses: missing the
        # required threshold. Patching `THRESHOLD_PARAMETER` itself does not
        # work — the deployment reads that key directly and raises a KeyError
        # long before the request is built.
        kwargs["parameters"] = {}
        return original(**kwargs)

    monkeypatch.setattr(deployment, "request", _without_the_threshold)

    buffer = io.StringIO()
    argv = sys.argv
    sys.argv = [str(EXAMPLE / "run.py")]
    try:
        with contextlib.redirect_stdout(buffer):
            code = run.main()
    finally:
        sys.argv = argv
    monkeypatch.undo()

    assert code == 1, code
    assert "refused:" in buffer.getvalue(), buffer.getvalue()[:200]


def test_the_printed_specification_and_json_are_non_empty_and_the_json_validates(
    printed: str, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Criterion 5, both clauses, against the bytes the example actually prints.

    (c) is NOT redundant with the in-process assertion above, and the reason is
    the whole point. That test validates the in-process
    ``ContextProductContract``. This one without (c) would only assert that the
    printed text parses and is non-empty — and **a serializer that dropped a
    field, renamed one or stringified a nested object would pass BOTH**, while
    the thing a reader actually receives is wrong. Criterion 5's *"the JSON
    validates against the declared contract"* is about the printed JSON.
    """
    # (a) the specification is there, whole.
    assert specification_problems(specification_section(printed)) == []

    # (b) the JSON parses and is non-empty.
    payload = json.loads(json_section(printed))
    assert payload

    # (c) and it is the declared shape.
    declared = _declared_shape()
    assert payload_shape_violations(payload, declared) == []

    # CONTROL 1 — the non-emptiness check is not vacuous. Repoint the spec at
    # an empty file, re-run, and (a) must FAIL.
    empty = tmp_path / "empty.md"
    empty.write_text("", encoding="utf-8")
    run = _load("run")
    deployment = _load("deployment")
    monkeypatch.setattr(deployment, "SPEC", empty)
    buffer = io.StringIO()
    argv = sys.argv
    sys.argv = [str(EXAMPLE / "run.py")]
    try:
        with contextlib.redirect_stdout(buffer):
            assert run.main() == 0
    finally:
        sys.argv = argv
    monkeypatch.undo()
    assert specification_problems(specification_section(buffer.getvalue())) != []

    # CONTROL 2 — (c) is not a `json.loads` in a costume. Drop one key from the
    # PRINTED payload (patch the captured text, never the code) and (c) must
    # FAIL naming the missing key.
    dropped = sorted(payload)[0]
    wounded = dict(payload)
    del wounded[dropped]
    problems = payload_shape_violations(wounded, declared)
    assert problems and any(dropped in problem for problem in problems), (
        f"removing {dropped!r} from the printed payload changed nothing the"
        f" shape check reports: {problems}"
    )


# --------------------------------------------------------------------------
# 9 — debt reads the SOURCE instant.
# --------------------------------------------------------------------------
def _alternate_period(dsn: str) -> str:
    """A reported period the fixture seeds OTHER than the pinned one.

    Derived from the seeded table rather than written down, so the fixture and
    this test cannot drift.
    """
    deployment = _load("deployment")
    with psycopg.connect(dsn) as db, db.cursor() as cursor:
        cursor.execute(
            f"select {deployment.COLUMN_PERIOD} from"  # noqa: S608
            f" {deployment.SOURCE_SCHEMA}.{deployment.TABLE_HOLDINGS}"
            f" where {deployment.COLUMN_ISSUER_LEI} = %s"
            f" and {deployment.COLUMN_PERIOD} <> %s"
            f" group by 1"
            f" order by to_date({deployment.COLUMN_PERIOD},"
            f" '{deployment.PERIOD_FORMAT}') desc limit 1",
            (_anchor(), deployment.reported_period()),
        )
        return str(cursor.fetchone()[0])


def test_debt_is_driven_by_the_declared_freshness_anchor(
    tmp_path: pathlib.Path, seeded: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two movements, and only the second one distinguishes the two clocks.

    Movement 1 — hold the source period, move the caller's instant later.
    Freshness falls. That proves decay happens at all, and nothing more: it
    would look the same if the scorer read the RUN's clock.

    Movement 2 — hold the caller's instant, move the SEEDED period earlier by
    repointing the question ARTIFACT (which is where the pin is declared) at a
    copy naming a period the fixture also seeds. Freshness falls again while
    ``asked_at`` is byte-identical. **Only a scorer reading the source's own
    instant can move here**, which is the assertion §E.2 rests on: scoring
    ``observed_at`` would measure the age of this run, and a two-year-old
    filing re-read a moment ago would score as perfectly fresh.
    """
    deployment = _load("deployment")
    low, _high, _exact = _thresholds(seeded)

    _a, early = _over(tmp_path / "early", low)
    # HALF THE REMAINING TTL, not a round year. `ttl_anchor` is
    # `from_entity_freshness`, so `expires_at` is anchored on the REPORTED
    # quarter end and not on the request: a year forward lands past it and gate
    # 3 refuses. That is `24-CONTEXT.md` `D-43` and spec §E.5 — the gate
    # working — and it is asserted below rather than merely avoided.
    forward = (early.product.expires_at - early.scenario.request.asked_at) / 2
    _b, late = _over(
        tmp_path / "late", low, asked_at=early.scenario.request.asked_at + forward
    )
    assert late.product.debt.factors.freshness < early.product.debt.factors.freshness
    assert late.product.debt.debt > early.product.debt.debt

    with pytest.raises(RuntimeError, match="ttl-bounds"):
        _over(
            tmp_path / "expired",
            low,
            asked_at=early.product.expires_at + timedelta(days=1),
        )

    document = yaml.safe_load(deployment.QUESTION.read_text(encoding="utf-8"))
    document[deployment.DECLARATION][deployment.COLUMN_PERIOD] = _alternate_period(
        seeded
    )
    older = tmp_path / "question-older.yaml"
    older.write_text(yaml.safe_dump(document), encoding="utf-8")
    monkeypatch.setattr(deployment, "QUESTION", older)
    _c, shifted = _over(tmp_path / "older", low)
    monkeypatch.undo()

    assert shifted.scenario.request.asked_at == early.scenario.request.asked_at, (
        "the two runs must share one caller instant, or the comparison below"
        " cannot tell the source's clock from the run's"
    )
    assert shifted.scenario.report_period != early.scenario.report_period
    assert (
        shifted.product.debt.factors.freshness
        < early.product.debt.factors.freshness
    ), (
        "the same question, asked at the same instant against an OLDER seeded"
        " period, scored no less fresh — the half-life is reading something"
        " other than the source's own instant"
    )


# --------------------------------------------------------------------------
# 10 — the record is written before delivery.
# --------------------------------------------------------------------------
def test_the_record_is_written_before_delivery(
    tmp_path: pathlib.Path, seeded: str
) -> None:
    """The replay record resolves, and it round-trips the caller's question.

    The threshold is an ``int`` because ``ccf_config.yaml`` declares the
    parameter ``integer``, and this asserts the artifact says so — a
    ``Decimal`` does not survive the round trip (it returns as ``str`` and the
    replayed request is then refused ``type-mismatch`` against the contract
    that admitted the original). Asserting the DECLARATION here means a later
    edit of the artifact breaks loudly at this line instead of surfacing as a
    confusing refusal inside the replay path. `24-CONTEXT.md` `D-07`/`D-53`:
    the finding is already recorded and is not reopened as a new gap.
    """
    deployment = _load("deployment")
    declared = yaml.safe_load(deployment.CONFIG.read_text(encoding="utf-8"))
    parameter = declared[deployment.KEY_REQUEST_CONTRACT]["arguments"]["properties"][
        deployment.THRESHOLD_PARAMETER
    ]
    assert parameter["type"] == "integer"

    low, _high, _exact = _thresholds(seeded)
    _outcome, observed = _over(tmp_path / "record", low)
    address = observed.served.replay_ref.content_address
    assert observed.store.exists(content_address=address)
    restored = DecisionReplayRecord.model_validate_json(
        observed.store.get(content_address=address)
    )
    assert restored == observed.record
    recorded = restored.content_generation_path.request
    assert recorded.parameters[deployment.THRESHOLD_PARAMETER] == low
