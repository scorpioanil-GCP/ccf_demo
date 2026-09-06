"""`D_c` MOVES WHEN ITS INPUTS MOVE — the gate `D-IMPL-230` requires, and never an equality.

**WHAT THIS MODULE IS FOR, in Dave's words.** *"The assertion is that `D_c` MOVES
WHEN THE BOUNDARY MOVES, together with the 20-member roster — NOT `D_c ==
0.0909` forever. A frozen scalar is a constant that agrees with itself; a debt
score that does not move when its inputs move is the idle-gate class arriving
through a float."*

So nothing here asserts `D_c == 0.090909…`. The measured factor table lives in
the specification (§E.2.1), where a reader can check it; what a **test** can add
is the property a table cannot state — that the number is a function of the
estate rather than a constant sitting beside one.

**NO NEW GATE ID IS MINTED.** The roster's home is `CFT-G09`, which already
governs *"a node carrying no LEI stays in the tree AND in the roster"*, and the
movement assertion is a test. The roster stays **sixteen**, `CFT-G01`…`CFT-G16`.

## The three boundaries, and which of them `D_c` is a function of

`D_c = 1 − (F · C · S)`. On this estate `F` is 1 (no family node or edge carries
an assertion date of any kind, so every observation is dated at the read instant)
and `C` is 1 (the elements §E.2 marks *required* are fail-closed conditions
reached before the scorer). **`S` is the whole of the variation**, and `S` is the
fraction of the members THE PAYLOAD SERVED whose IDENTITY no finding disputes —
served, and not source-read, since the 2026-09-01 close panel.

| Boundary moved | What moves with it | `D_c` |
|---|---|---|
| **identity** — how many members a duplicate finding disputes | `S`'s numerator | **MOVES**, and in the direction the change implies |
| **depth** — how many members the payload serves | `S`'s DENOMINATOR | **MOVES** — held by `CFT-G05`, not here |
| **attribute resolution** — how many members hold a `ccf_v2.legal_entity` row | the `unresolved_jurisdiction` **roster** | **does NOT move** |

**THE DEPTH ROW IS NOT THIS MODULE'S, AND THE REASON IS A FINDING RATHER THAN A
DIVISION OF LABOR.** Every perturbation below moves the identity boundary at a
FIXED depth — the declared default, where the payload's served roster and the
deployment's source read coincide on all 22. So when
``examples/cp-04-corporate-family-tree/produce.py::_agreement`` took its
denominator from ``scenario.facts`` instead of from what was served, **nothing in
this module could see it**: `D_c` still moved with every identity perturbation,
in the right direction, by the right amount. Measured on 2026-09-01 with that
denominator restored as a sabotage, all six tests here passed and exactly one
test in the 216-test cp-04 suite went red — `CFT-G05`, whose subject is depth.
**A movement gate over one boundary says nothing about a second**, and the depth
pair lives where depth is the subject, pinned as data at
``examples/cp-04-corporate-family-tree/artifacts/expected.yaml::debt_by_depth``.

**THE ATTRIBUTE ROW IS A GATE, NOT A GAP.** `D-IMPL-230` ruled **SERVE**: the
attribute shortfall reaches the consumer as the roster finding and as
`attributes: null` on each member, and is deliberately **not** folded into `S`.
Folding it in gives `S = 2/22` and `D_c ≈ 0.909`. Since `24.5-L-14` the SDK
enforces a class-DECLARED debt ceiling (`D-IMPL-240` (3); the helper that
resolved it was deleted in `24.6-03`, when the fold moved into the Authority
layer) and a request's `debt_tolerance` may only TIGHTEN it; cp-04 declares no ceiling, so
`0.909` would not `409` here — it would be SERVED, a false debt figure riding
the tree criteria 12 and 33 exist to protect. That is why this assertion
exists, and the reason is unchanged. Dave: *"Don't raise tolerance to 0.95 and
don't pretend 0.909 is the whitepaper number."* So a test that watched `D_c` move when a
Postgres row appeared would be watching the forbidden change happen, and the
assertion here is the opposite one — **the roster moves and the debt does not**.

## The two twenties are different populations

They agree on a number and disagree on a membership, which is exactly the
coincidence a reader resolves the wrong way. Measured: `S`'s numerator is the
**twenty undisputed members**, the roster is the **twenty row-less members**,
they **overlap in nineteen**, `SubSuperMicroComputerBV` is in the roster and not
in `S`'s numerator, the anchor is in `S`'s numerator and not in the roster, and
`SuperMicroComputerBV` is in neither. This module asserts both as **rosters**,
never as cardinalities (`D-13`).

## Every perturbation is an ESTATE perturbation, through the shipped code

Nothing below patches a factor, a scorer or a threshold to make a number move.
Each case seeds a **different ledger** — a label that no longer folds, a label
that folds where none did, an LEI where there was none — and runs the shipped
assembler over it. A test that moved `D_c` by monkeypatching `DebtFactors` would
be asserting that assignment works.

**AND THE CONTROL HAS A CONTROL.** `test_pinning_the_debt_to_a_constant_breaks_the_movement_assertion`
performs the sabotage `D-IMPL-230` names — it pins `produce.measure_debt` to a
constant — re-runs the same two estates, and asserts the movement predicate
**fails**. Without it the movement assertion would be a claim about this module
rather than about the product.

## Isolation

Per-module ledger and schema names, from `tests/examples/cp_04_seed.py`, for the
reason that module records: `fluree_url` and `postgres_dsn` are session-scoped,
six cp-04 modules transact one fixture, and a fixed name puts them in one
append-only ledger where a sibling's deliberate sabotage leaks into this
module's numbers. This module seeds **four** ledgers of its own and every one of
them carries a mutation, so a shared name would be actively destructive here.
"""

from __future__ import annotations

import copy
import importlib
import json
import pathlib
import sys
import tempfile
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Iterator, Mapping

import httpx
import psycopg
import pytest

from .cp_04_seed import (
    ATTRIBUTE_TABLE,
    FLUREE_FIXTURE,
    _family_triples,
    _stable,
    expected_counts,
    ledger_for,
    schema_for,
    seed,
)

REPO = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE = REPO / "examples" / "cp-04-corporate-family-tree"

#: Both stores. `.github/workflows/ci.yml` exports both legs' variables at JOB
#: level and runs `leg-postgres` and `leg-fluree` as two steps of that one job,
#: so a doubly-marked module is selected twice and runs whole both times.
pytestmark = [pytest.mark.fluree, pytest.mark.postgres]

#: The RDF predicates this module mutates. Read from the fixture's own shape
#: rather than composed from a prefix authored here.
LABEL_PREDICATE = "http://www.w3.org/2000/01/rdf-schema#label"
LEI_PREDICATE = "http://example.org/fibo/lei"

#: The nodes each perturbation touches, by IRI. These are ADDRESSES in the
#: committed fixture, not figures: every NUMBER in this module is measured at
#: run time from the two estates and none is written down.
DUPLICATE_MEMBER = "http://example.org/fibo/SubSuperMicroComputerBV"
COLLIDING_TARGET = "http://example.org/fibo/SubSuperMicroComputerGmbh"
ROW_LESS_MEMBER = "http://example.org/fibo/SubSupermicroKk"

#: A label nothing in the estate folds to. Its content does not matter; that it
#: is unique does, and the test asserts the dispute count it produces rather
#: than trusting the string.
DISTINCT_LABEL = "Vandermeer Holdings Cooperatief U.A."

#: A jurisdiction the family already serves, so the closed-world assertion
#: (`D-IMPL-228`) is untouched by the attribute perturbation. Introducing a
#: THIRD jurisdiction would move a different boundary and confound the test.
IN_FAMILY_JURISDICTION = "NL"


def _load(name: str) -> Any:
    """Load one of the example's modules under its own bare name.

    The example is a directory of modules rather than a package and its modules
    import each other by bare name, while one pytest session runs over a tree
    holding several `deployment`/`produce`/`run` triples. So the cache is
    checked against THIS example's directory and the whole family is evicted
    together when it holds somebody else's — evicting one name at a time would
    rebuild the split-identity problem the eviction prevents. The shape is
    `tests/examples/test_cp_04_census.py::_load`.
    """
    if sys.path[:1] != [str(EXAMPLE)]:
        while str(EXAMPLE) in sys.path:
            sys.path.remove(str(EXAMPLE))
        sys.path.insert(0, str(EXAMPLE))
    family = (
        "deployment",
        "produce",
        "projection",
        "assembler",
        "transport",
        "run",
        "compose",
        "serve",
    )
    for cached_name in family:
        cached = sys.modules.get(cached_name)
        if cached is None:
            continue
        if not str(getattr(cached, "__file__", "")).startswith(str(EXAMPLE)):
            for sibling in family:
                sys.modules.pop(sibling, None)
            break
    return importlib.import_module(name)


# ---------------------------------------------------------------------------
# Perturbed estates — every one a real store, seeded and read back.
# ---------------------------------------------------------------------------


def _transact(url: str, ledger: str, body: Mapping[str, Any]) -> None:
    """Create one ledger, transact ``body`` into it, and verify the readback.

    A 200 is not evidence: measured against `fluree/server:4.1.4`, a transaction
    body carrying an unrecognized top-level key is accepted with HTTP 200 and a
    real commit receipt, so a misspelled `insert` key would report success
    having written nothing. The readback polls until two CONSECUTIVE reads agree
    — stability, not correctness — and compares once afterwards, because a loop
    that stopped when the number matched the expectation is a check that cannot
    fail.
    """
    expected = expected_counts()["family_triples"]
    with httpx.Client(timeout=180) as client:
        created = client.post(
            f"{url}/v1/fluree/create",
            headers={"Content-Type": "application/json"},
            content=json.dumps({"ledger": ledger}),
        )
        if created.status_code != 201:
            raise RuntimeError(
                f"could not create ledger {ledger!r}:"
                f" {created.status_code} {created.text[:200]}"
            )
        client.post(
            f"{url}/v1/fluree/update/{ledger}",
            headers={"Content-Type": "application/json"},
            content=json.dumps(body),
        ).raise_for_status()
        triples = _stable(lambda: _family_triples(client, url, ledger))
    if triples != expected:
        raise RuntimeError(
            f"ledger {ledger!r} holds {triples} family triples and the fixture"
            f" carries {expected}. Every perturbation in this module edits a"
            " LABEL or an LEI, and neither is a family predicate, so the family"
            " triple count must be unchanged — a difference means the mutation"
            " touched the graph rather than the node facts"
        )


def _fixture_body() -> dict[str, Any]:
    """A deep copy of the committed fixture, safe to mutate."""
    return copy.deepcopy(json.loads(FLUREE_FIXTURE.read_text(encoding="utf-8")))


def _document(body: Mapping[str, Any], iri: str) -> dict[str, Any]:
    """The one fixture document for ``iri``, or a failure naming it.

    Refuses a miss rather than returning ``None``: a perturbation applied to no
    node would leave every assertion below true of an UNPERTURBED estate, which
    is the shape of a test that cannot fail.
    """
    for document in body["insert"]:
        if document.get("@id") == iri:
            return dict(document)
    raise AssertionError(
        f"the committed fixture holds no document for {iri!r}; this module's"
        " perturbation would have applied to nothing"
    )


def _perturbed_ledger(url: str, mutate: Any) -> str:
    """Seed one ledger from a mutated copy of the fixture and return its name."""
    body = _fixture_body()
    mutate(body)
    ledger = f"ccf:cp04-debt-{uuid.uuid4().hex[:12]}"
    _transact(url, ledger, body)
    return ledger


def _set_label(body: dict[str, Any], iri: str, label: str) -> None:
    for index, document in enumerate(body["insert"]):
        if document.get("@id") == iri:
            document[LABEL_PREDICATE] = [label]
            body["insert"][index] = document
            return
    raise AssertionError(f"no fixture document for {iri!r}")


def _set_lei(body: dict[str, Any], iri: str, lei: str) -> None:
    for index, document in enumerate(body["insert"]):
        if document.get("@id") == iri:
            document[LEI_PREDICATE] = [lei]
            body["insert"][index] = document
            return
    raise AssertionError(f"no fixture document for {iri!r}")


# ---------------------------------------------------------------------------
# One assembly, and what this module reads off it.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Answer:
    """What one whole assembly produced, reduced to what this module asserts."""

    debt: Decimal
    signal: str
    freshness: Decimal
    completeness: Decimal
    agreement: Decimal
    members: frozenset[str]
    disputed: frozenset[str]
    roster: frozenset[str]
    jurisdictions: tuple[str, ...]


def _assemble(
    *,
    fluree_url: str,
    ledger: str,
    dsn: str,
    schema: str,
    monkeypatch: pytest.MonkeyPatch,
) -> Answer:
    """Run the SHIPPED assembler end to end against one estate.

    Through `assembler.FamilyTreeAssembler`, the same seam `run.py` and the MCP
    door reach — not through a reimplementation that could disagree with either.
    The connection material arrives the way the deployment declares it, through
    the environment variable names `backends.yaml` holds, so this function names
    no host, port, path or credential.
    """
    for variable, value in (
        ("CCF_CP_04_FLUREE_URL", fluree_url.rstrip("/")),
        ("CCF_CP_04_FLUREE_LEDGER", ledger),
        ("CCF_CP_04_POSTGRES_DSN", dsn),
        ("CCF_CP_04_POSTGRES_SCHEMA", schema),
    ):
        monkeypatch.setenv(variable, value)

    deployment = _load("deployment")
    projection = _load("projection")
    assembler = _load("assembler")

    state: dict[str, Any] = {}

    def read(booted: Any, asked: Any, **kwargs: Any) -> Any:
        scenario = deployment.read(booted, asked, **kwargs)
        state["scenario"] = scenario
        state["booted"] = booted
        return scenario

    def claims(*, minted: Mapping[str, str]) -> Any:
        scenario = state["scenario"]
        return deployment.relationship_claims(
            tenant=state["booted"].tenant_id,
            at=scenario.request.asked_at,
            edges=scenario.edges,
            nodes=sorted(scenario.facts),
            minted=minted,
            envelopes_by_node=scenario.envelopes_by_node,
        )

    seen: list[Any] = []
    with tempfile.TemporaryDirectory(prefix="cp04-debt-") as tmp:
        root = pathlib.Path(tmp)
        product = assembler.FamilyTreeAssembler(
            config=deployment.CONFIG,
            root=root,
            connection=deployment.connection(root=root),
            read=read,
            plan_class=projection.plan_class(),
            claims=claims,
            observer=seen.append,
        )
        product.assemble(
            request=deployment.demonstration_request(),
            perspective=deployment.perspective(),
            tenant_id=deployment.tenant_id(),
        )
    assert seen, "the assembly produced nothing to observe"
    assembled = seen[-1]
    scenario = assembled.scenario
    debt = assembled.product.debt
    disputed = {
        uri
        for finding in scenario.findings
        if finding.type == scenario.duplicate_finding_type
        for uri in finding.members
    }
    return Answer(
        debt=Decimal(debt.debt),
        signal=str(debt.signal),
        freshness=Decimal(debt.factors.freshness),
        completeness=Decimal(debt.factors.completeness),
        agreement=Decimal(debt.factors.semantic_consistency),
        members=frozenset(scenario.facts),
        disputed=frozenset(disputed),
        roster=frozenset(scenario.unresolved),
        jurisdictions=tuple(sorted(scenario.observed_jurisdictions)),
    )


# ---------------------------------------------------------------------------
# Fixtures — one baseline estate and three perturbations of it.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def baseline(fluree_url: str, postgres_dsn: str) -> Iterator[tuple[str, str]]:
    """The committed fixture pair, unperturbed, under names nobody else holds."""
    ledger = ledger_for(__name__)
    schema = schema_for(__name__)
    seed(fluree_url, ledger, postgres_dsn, schema)
    yield ledger, schema


@pytest.fixture(scope="module")
def ledger_without_the_dispute(fluree_url: str) -> str:
    """The duplicate pair's labels no longer fold together.

    The identity boundary moves toward AGREEMENT: one node that a finding
    disputed no longer is, so `S` rises and `D_c` must fall.
    """
    return _perturbed_ledger(
        fluree_url,
        lambda body: _set_label(body, DUPLICATE_MEMBER, DISTINCT_LABEL),
    )


@pytest.fixture(scope="module")
def ledger_with_a_third_collision(fluree_url: str) -> str:
    """A third node's label folds onto the duplicate pair's.

    The identity boundary moves toward DISAGREEMENT: a member no finding
    disputed now is, so `S` falls and `D_c` must rise. Both directions are
    exercised, because a check that only ever watched a number fall could be
    satisfied by a function that only ever falls.
    """

    def mutate(body: dict[str, Any]) -> None:
        label = _document(body, DUPLICATE_MEMBER)[LABEL_PREDICATE][0]
        _set_label(body, COLLIDING_TARGET, label)

    return _perturbed_ledger(fluree_url, mutate)


@pytest.fixture(scope="module")
def resolving_estate(
    fluree_url: str, postgres_dsn: str, baseline: tuple[str, str]
) -> tuple[str, str]:
    """One row-less member acquires an LEI and a matching attribute row.

    **The ATTRIBUTE boundary, moved in the direction that keeps the closed
    jurisdiction world intact.** Deleting a row instead would drop `NL` or
    `US-DE` out of the served set and trip `refuse_open_jurisdiction_world`
    (`D-IMPL-228`), so the assembly would refuse and the test would be measuring
    a different guard. The new row carries a jurisdiction the family already
    serves, so the served set is unchanged and the only thing that moves is who
    resolves.
    """
    _, base_schema = baseline
    lei = f"CP04DEBT{uuid.uuid4().hex[:12].upper()}"
    ledger = _perturbed_ledger(
        fluree_url, lambda body: _set_lei(body, ROW_LESS_MEMBER, lei)
    )
    schema = schema_for(f"{__name__}_resolving")
    with psycopg.connect(postgres_dsn, autocommit=True) as connection:
        connection.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')
        connection.execute(
            f'CREATE TABLE "{schema}".{ATTRIBUTE_TABLE} AS'
            f' SELECT * FROM "{base_schema}".{ATTRIBUTE_TABLE}'
        )
        connection.execute(
            f'INSERT INTO "{schema}".{ATTRIBUTE_TABLE}'
            " (lei, legal_name, legal_jurisdiction, is_anchor, provenance,"
            " source, retrieved_at)"
            " VALUES (%s, %s, %s, FALSE, 'test', 'test', DATE '2026-08-31')",
            (lei, "Supermicro K.K.", IN_FAMILY_JURISDICTION),
        )
    return ledger, schema


# ---------------------------------------------------------------------------
# The movement predicate, in one place so the sabotage exercises the same one.
# ---------------------------------------------------------------------------


def moves_down(before: Decimal, after: Decimal) -> bool:
    """``after`` is strictly less than ``before``. Strictly — equal is frozen."""
    return after < before


def moves_up(before: Decimal, after: Decimal) -> bool:
    """``after`` is strictly greater than ``before``."""
    return after > before


# ---------------------------------------------------------------------------
# The assertions.
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    strict=True,
    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
)
def test_the_two_twenties_are_different_populations(
    baseline: tuple[str, str],
    fluree_url: str,
    postgres_dsn: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`S`'s numerator and the roster agree on a number and not on a membership.

    Asserted as ROSTERS. Two sets of equal size compared by size would let one
    of them be entirely the wrong members and still pass forever (`D-13`).
    """
    ledger, schema = baseline
    answer = _assemble(
        fluree_url=fluree_url,
        ledger=ledger,
        dsn=postgres_dsn,
        schema=schema,
        monkeypatch=monkeypatch,
    )
    undisputed = answer.members - answer.disputed
    assert len(undisputed) == len(answer.roster), (
        "the two populations no longer have the same size, so the coincidence"
        " this test exists to disentangle is not present on this estate and the"
        " assertions below would be proving something easier than intended"
    )
    assert undisputed != answer.roster, (
        "S's numerator and the unresolved roster came out as the SAME set of"
        " members. They are two different populations that happen to have the"
        " same size on this estate, and a build in which they coincide has"
        " folded attribute coverage into S — the 0.909 reading D-IMPL-230"
        " refused"
    )
    assert answer.roster - undisputed, (
        "every row-less member is also undisputed, so no member distinguishes"
        " the attribute boundary from the identity boundary on this estate"
    )
    assert undisputed - answer.roster, (
        "every undisputed member is also row-less, so the two boundaries cannot"
        " be told apart by membership"
    )


#: The one line `D-IMPL-231` part 2 requires §E.2 to carry, so a reader meeting
#: `D_c ≈ 0.0909` and the twenty-member roster together cannot read the first as
#: the second. Compared as a SUBSTRING of the whitespace-collapsed document,
#: because the source is hard-wrapped and a `grep -F` against wrapped prose
#: reports a sentence missing while it sits plainly on the page — the measured
#: defect plan `24.4-08`'s Gate 1 pass recorded against its own check.
TWO_TWENTIES_DISCLOSURE = (
    "`D_c ≈ 0.0909` IS NOT \"20 MISSING JURISDICTIONS.\""
)

#: The overlap the same line must state. Denying the misreading without saying
#: how far apart the two sets are would leave a reader knowing only that
#: something is wrong.
TWO_TWENTIES_OVERLAP = "the two sets overlap in **nineteen**"

#: The document both assertions read.
SPEC = EXAMPLE / "spec" / "CP-SPEC-004_Corporate_Family_Tree.md"


def _unwrapped(path: pathlib.Path) -> str:
    """One document with its hard wraps collapsed to single spaces."""
    return " ".join(path.read_text(encoding="utf-8").split())


def test_the_spec_denies_the_misreading_the_two_twenties_invite() -> None:
    """`D-IMPL-231` part 2. §E.2 says the number is not the roster, in one line.

    A prose requirement with no check is a sitting instruction rather than a
    gate, and this repository has already shipped one. So the sentence Dave
    asked for is compared against the document, and the comparison is against
    the UNWRAPPED text because the source is hard-wrapped.
    """
    document = _unwrapped(SPEC)
    assert TWO_TWENTIES_DISCLOSURE in document, (
        f"{SPEC} no longer denies the misreading in as many words. Expected the"
        f" line {TWO_TWENTIES_DISCLOSURE!r} — without it a reader meeting"
        " `D_c ≈ 0.0909` beside a twenty-member roster reads the first as the"
        " second, which is exactly what `D-IMPL-231` part 2 exists to prevent"
    )
    assert TWO_TWENTIES_OVERLAP in document, (
        f"the disclosure no longer states the overlap ({TWO_TWENTIES_OVERLAP!r})."
        " Denying that the two twenties are one, without saying how far apart"
        " they are, leaves a reader knowing only that something is wrong"
    )


def test_the_disclosure_check_refuses_a_document_that_dropped_it(
    tmp_path: pathlib.Path,
) -> None:
    """**Sabotage control.** The line removed must make the check RED.

    Applied to a COPY: a control that edited `examples/` and reverted would
    leave the repository dirty the moment it failed.
    """
    subject = tmp_path / SPEC.name
    subject.write_text(
        SPEC.read_text(encoding="utf-8").replace(
            'IS NOT "20 MISSING JURISDICTIONS."', "is a debt score."
        ),
        encoding="utf-8",
    )
    assert subject.read_text(encoding="utf-8") != SPEC.read_text(encoding="utf-8"), (
        "the disclosure control did not change anything"
    )
    assert TWO_TWENTIES_DISCLOSURE not in _unwrapped(subject), (
        "the check still finds the disclosure in a document that dropped it"
    )


@pytest.mark.xfail(
    strict=True,
    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
)
def test_d_c_moves_when_the_identity_boundary_moves(
    baseline: tuple[str, str],
    ledger_without_the_dispute: str,
    ledger_with_a_third_collision: str,
    fluree_url: str,
    postgres_dsn: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The load-bearing assertion: `D_c` is a function of the estate.

    Three estates differing only in a LABEL, run through the shipped assembler,
    and `D_c` moves in the direction each change implies — down when one fewer
    member's identity is disputed, up when one more is. **No equality on
    `0.090909…` anywhere**: a frozen scalar is a constant agreeing with itself.
    """
    ledger, schema = baseline
    base = _assemble(
        fluree_url=fluree_url, ledger=ledger, dsn=postgres_dsn, schema=schema,
        monkeypatch=monkeypatch,
    )
    agreeing = _assemble(
        fluree_url=fluree_url, ledger=ledger_without_the_dispute,
        dsn=postgres_dsn, schema=schema, monkeypatch=monkeypatch,
    )
    disagreeing = _assemble(
        fluree_url=fluree_url, ledger=ledger_with_a_third_collision,
        dsn=postgres_dsn, schema=schema, monkeypatch=monkeypatch,
    )

    # THE INPUT MOVED, AND IT MOVED AS INTENDED — asserted before the output, so
    # a perturbation that silently applied to nothing fails here rather than
    # leaving the movement assertion to pass vacuously against one estate.
    assert len(agreeing.disputed) < len(base.disputed) < len(disagreeing.disputed), (
        "the identity boundary did not move as the perturbations intended:"
        f" disputed members were {sorted(agreeing.disputed)} /"
        f" {sorted(base.disputed)} / {sorted(disagreeing.disputed)}"
    )

    assert moves_down(base.debt, agreeing.debt), (
        f"one FEWER disputed identity left D_c at {base.debt} -> {agreeing.debt}."
        " A debt score that does not move when its inputs move is the idle-gate"
        " class arriving through a float (D-IMPL-230)"
    )
    assert moves_up(base.debt, disagreeing.debt), (
        f"one MORE disputed identity left D_c at {base.debt} ->"
        f" {disagreeing.debt}. The score must move in the direction the change"
        " implies, not merely change"
    )
    # THE ROSTER TRAVELS WITH IT, AND IS ASSERTED BESIDE IT (`D-IMPL-230`), so
    # neither can be read as standing in for the other.
    assert agreeing.roster == base.roster == disagreeing.roster, (
        "a LABEL edit moved the unresolved roster, which reads off PostgreSQL"
        " rows and cannot be a function of a label"
    )
    assert base.freshness == agreeing.freshness == disagreeing.freshness, (
        "F moved under a label edit, so the movement above is not attributable"
        " to the boundary this test moved"
    )
    assert base.completeness == agreeing.completeness == disagreeing.completeness, (
        "C moved under a label edit, so the movement above is not attributable"
        " to the boundary this test moved"
    )


@pytest.mark.xfail(
    strict=True,
    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
)
def test_the_attribute_boundary_moves_the_roster_and_not_the_debt(
    baseline: tuple[str, str],
    resolving_estate: tuple[str, str],
    fluree_url: str,
    postgres_dsn: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`D-IMPL-230`'s SERVE ruling, pinned so it cannot be quietly reversed.

    One row-less member acquires an LEI and an attribute row. The roster loses
    that member **by name**, and `D_c` does **not** move — because the shortfall
    is served as data (`D-IMPL-229`'s roster finding and `attributes: null`) and
    is deliberately not folded into `S`. A build that folded it in would move
    `D_c` here and serve `0.909` on the demonstration question — cp-04 declares
    no class ceiling (`24.5-L-14`; the resolution moved into the Authority
    layer at `24.6-03`), so nothing would `409`; the false figure would simply reach
    the consumer where the product is supposed to answer.
    """
    ledger, schema = baseline
    base = _assemble(
        fluree_url=fluree_url, ledger=ledger, dsn=postgres_dsn, schema=schema,
        monkeypatch=monkeypatch,
    )
    perturbed_ledger, perturbed_schema = resolving_estate
    resolving = _assemble(
        fluree_url=fluree_url, ledger=perturbed_ledger, dsn=postgres_dsn,
        schema=perturbed_schema, monkeypatch=monkeypatch,
    )

    assert ROW_LESS_MEMBER in base.roster, (
        f"{ROW_LESS_MEMBER} is not in the baseline roster, so this test's"
        " perturbation has nothing to remove from it"
    )
    assert resolving.roster == base.roster - {ROW_LESS_MEMBER}, (
        "the roster did not lose exactly the member that acquired a row."
        f" Baseline minus perturbed: {sorted(base.roster - resolving.roster)};"
        f" perturbed minus baseline: {sorted(resolving.roster - base.roster)}"
    )
    assert resolving.jurisdictions == base.jurisdictions, (
        "the served jurisdiction set moved, so this perturbation disturbed the"
        " closed-world assertion rather than only the attribute boundary"
    )
    assert resolving.debt == base.debt, (
        f"D_c moved from {base.debt} to {resolving.debt} when an attribute row"
        " appeared. D-IMPL-230 ruled SERVE: the attribute shortfall reaches the"
        " consumer as the roster finding and as `attributes: null`, and is NOT"
        " folded into S. Folding it in gives S = 2/22 and D_c ~ 0.909 — SERVED,"
        " not 409ed: cp-04 declares no class ceiling (24.5-L-14), so the false"
        " figure would reach the consumer"
    )


@pytest.mark.xfail(
    strict=True,
    reason="D-IMPL-264 am.1 (D-08 paired outcome): frozen cp-04 assembler.py isinstance over the retired resolve_effective_request union — quarantined evidence, D-IMPL-263/D-IMPL-261; un-quarantine and rerun unchanged after D-GATE-24.7",
)
def test_pinning_the_debt_to_a_constant_breaks_the_movement_assertion(
    baseline: tuple[str, str],
    ledger_without_the_dispute: str,
    fluree_url: str,
    postgres_dsn: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The sabotage `D-IMPL-230` names, run as a test rather than reported once.

    `produce.measure_debt` is pinned to whatever it answered the FIRST time —
    the frozen scalar the ruling refuses — and the movement predicate is
    asserted to fail. A movement assertion nobody has watched fail is not
    evidence that it runs, which is the discipline the sixteen product gates are
    held to.

    **It pins the shipped function rather than a copy**, and it asserts the same
    `moves_down` the real assertion calls, so a future edit that made the
    predicate vacuous would turn this test red as well.
    """
    ledger, schema = baseline
    produce = _load("produce")
    real = produce.measure_debt
    frozen: list[Any] = []

    def pinned(scenario: Any, **kwargs: Any) -> Any:
        # `**kwargs` rather than a named `served`: the pin stands in for the
        # shipped function and must keep standing in for it if its keyword
        # arguments change, or this control quietly stops being applied and
        # reports a TypeError as a failure of the thing it is measuring.
        if not frozen:
            frozen.append(real(scenario, **kwargs))
        return frozen[0]

    monkeypatch.setattr(produce, "measure_debt", pinned)
    base = _assemble(
        fluree_url=fluree_url, ledger=ledger, dsn=postgres_dsn, schema=schema,
        monkeypatch=monkeypatch,
    )
    agreeing = _assemble(
        fluree_url=fluree_url, ledger=ledger_without_the_dispute,
        dsn=postgres_dsn, schema=schema, monkeypatch=monkeypatch,
    )

    assert len(agreeing.disputed) < len(base.disputed), (
        "the sabotage was applied to an estate pair whose identity boundary did"
        " not move, so the movement assertion would have had nothing to detect"
        " even unsabotaged"
    )
    assert base.debt == agreeing.debt, (
        "the pin did not take: with measure_debt frozen the two estates still"
        f" reported different debts, {base.debt} and {agreeing.debt}"
    )
    assert not moves_down(base.debt, agreeing.debt), (
        "the movement assertion still held with D_c pinned to a constant, so it"
        " is not measuring movement"
    )


# ---------------------------------------------------------------------------
# CR-02 — the request contract claims no `409` that nothing fires.
# ---------------------------------------------------------------------------


def test_the_debt_tolerance_contract_claims_no_unenforced_409() -> None:
    """**CR-02 (2026-09-01).** `debt_tolerance` is advisory, not a live 409.

    Dave: *"There is no `D_c` vs `debt_tolerance` comparison in this tree, and
    wiring a real 409 is almost certainly `src/`. Do not leave the lie in
    `ccf_config.yaml`."* Route (a): the parameter is marked ADVISORY / a
    demonstration pin in the same voice `as_of` uses — the surface stays
    discoverable and the text says what it actually does. It is NOT refused,
    because the demonstration sends it and must be served.

    Sabotage: restoring the `refuses with 409` sentence turns the first
    assertion RED; moving the key into `unsupported_arguments` turns the third.

    The same sentence lived in two sibling artifacts — `question.yaml`'s
    comment on the `debt_tolerance` key and the recipe's L6 `failure` field
    ("409 on a debt breach") — so the last two assertions read those too. A
    counterfactual ("folding coverage into `S` *would* `409`") is not a claim
    of shipped behavior and is left alone.

    **2026-09-03 (Phase 24.5.1), the history above dated.** Phase 24.5 wired
    it: `24.5-L-14` added the class-declared ceiling fold (deleted at
    `24.6-03`, when the resolution moved into the Authority layer) and
    `DeclaredObligationRefusal`, which
    `runtime/ccf_runtime/http_api/routes/product.py::retrieve` maps to HTTP
    `409`.

    **2026-09-04 (Phase 24.6, plan `24.6-04`), re-cited.** The ceiling is now
    a class's `default_debt_tolerance` — informative, and applied only when the
    caller states no tolerance (`D-IMPL-251` C1=A). cp-04 declares none, so
    nothing about it is bounded by its class; a caller's own `debt_tolerance`
    would be enforced as requested and, if exceeded, answered by the
    `tolerance-exceeded` shell rather than by the `409` family. The artifact
    prose this test reads stays advisory and every assertion below is
    unchanged.
    """
    import dataclasses

    import yaml

    config = yaml.safe_load((EXAMPLE / "ccf_config.yaml").read_text(encoding="utf-8"))
    props = config["request_contract"]["arguments"]["properties"]
    description = props["debt_tolerance"]["description"]

    assert "409" not in description, (
        "ccf_config.yaml's debt_tolerance description still promises a `409`"
        " refusal that no code fires — a live-looking ceiling that cannot fire:"
        f" {description!r}"
    )
    assert "advisory" in description.lower(), (
        "debt_tolerance must be marked advisory / a demonstration pin so a"
        f" caller reads what it actually does: {description!r}"
    )

    # Route (a), NOT the `as_of` refusal path: a caller sending debt_tolerance is
    # SERVED (the demonstration sends it), so it is not an unsupported argument.
    unsupported = config["request_contract"].get("unsupported_arguments", {}) or {}
    assert "debt_tolerance" not in unsupported, (
        "debt_tolerance was moved to unsupported_arguments — but the"
        " demonstration sends it and must be SERVED, so route (a) keeps it an"
        " advisory served pin, not a refused parameter"
    )

    # The write-once, read-nowhere FamilyScenario field is gone (CR-02 point 2/3):
    # it was pinned to the ARTIFACT's copy rather than the caller's and fed no
    # comparison.
    deployment = _load("deployment")
    fields = {f.name for f in dataclasses.fields(deployment.FamilyScenario)}
    assert "debt_tolerance" not in fields, (
        "FamilyScenario still carries the dead debt_tolerance field pinned to"
        " the artifact's copy"
    )

    # The sibling artifacts: the comment beside the declared pin, and the
    # recipe's L6 failure contract. Neither may assert a 409 this tier fires.
    question_text = (EXAMPLE / "artifacts" / "question.yaml").read_text(encoding="utf-8")
    key_at = question_text.index("debt_tolerance:")
    comment_window = question_text[max(0, key_at - 700) : key_at]
    assert "refuses with `409`" not in comment_window, (
        "question.yaml's comment on debt_tolerance still says assembly"
        " `refuses with 409` — the same unfired claim ccf_config.yaml lost"
    )
    assert "advisory" in comment_window.lower(), (
        "question.yaml's debt_tolerance comment must say the pin is advisory"
    )

    recipe = yaml.safe_load(
        (EXAMPLE / "artifacts" / "assembly-recipe.yaml").read_text(encoding="utf-8")
    )
    failures = [
        step.get("failure", "")
        for step in recipe["declaration"]["steps"]
        if isinstance(step, dict) and step.get("layer") == "L6"
    ]
    assert failures, "the recipe no longer declares an L6 step — the check is idle"
    for failure in failures:
        assert "409 on a debt breach" not in failure, (
            "the recipe's L6 failure field still claims `409 on a debt breach`"
            f" as shipped behavior: {failure!r}"
        )
        assert "advisory" in failure.lower(), (
            f"the recipe's L6 failure field must say debt_tolerance is advisory: {failure!r}"
        )
