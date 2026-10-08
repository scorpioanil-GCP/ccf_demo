"""EX-01 — a request value placed into SPARQL never changes the query's structure.

Security review 2026-09-23, row EX-01 (regraded by ruling C6 of
``docs/superpowers/specs/2026-09-25-v1-0-2-security-remediation-design.md``),
fixed under ``D-IMPL-376`` ruling (7): *"SDK input rejection is useful defense,
but leaves fragile example code for adopters to copy."* Three trees placed a
request value into a SPARQL string built by f-string:

- ``examples/cp-17-mnpi-wall-enforcement/acquisition.py`` — the subject LEI,
  and the verified principal, into ``FILTER`` string literals in
  ``::_over_wall``, ``::_reg_fd`` and ``::_family``;
- ``examples/cp-16-abs-securitization-surveillance/acquisition.py`` — the deal
  id into an IRI position through ``::_Graph.triggers``, which ``::acquire``
  reaches BEFORE the deal-existence check (so the splice fired whether or not
  the deal exists) and ``::_triggers`` reaches after it;
- ``examples/cp-04-canonical-corporate-family-tree/acquisition.py`` — the
  anchor LEI into a string literal in ``::acquire``, the request's first read.

**Driven in-process, below the SDK's request floor.** ``D-IMPL-357`` C1/C1a
refuses many of these shapes at the door; an adopter who copies an acquisition
module copies it without the door, so every builder here is called directly,
with a fake graph leg that records the text it would have sent. Nothing here
reads an estate, opens a socket or writes anything.

**Every hostile value ends one of exactly two ways:**

1. **REFUSED by the tree's own placement guard** — the innermost frame of the
   ``ValueError`` is that guard (``_literal`` for a string literal, ``_iri`` for
   an IRI position) in that tree's ``acquisition.py`` — and NO query reaches
   the graph leg; or
2. **PLACED ONLY AS A VALUE** — the query sent has exactly the token structure
   the benign question produces, and the hostile text is the value of the very
   literal or IRI the benign value occupied, and nowhere else.

**Structure is read by a SPARQL 1.1 lexer in this module**, which applies the
codepoint-escape pre-pass of SPARQL 1.1 §19.2 before tokenizing — so
``\\u0022`` is a quote here exactly as it is to an engine that implements the
pre-pass — and decodes ``ECHAR`` escapes when it reads a literal's value. The
lexer's own controls are the last tests in the module: a lexer that saw no
breakout would make every assertion above it vacuous.
"""

from __future__ import annotations

import importlib.util
import pathlib
import re
import sys
import traceback
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime
from types import ModuleType
from typing import Any

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLES = REPO_ROOT / "examples"

CP_17 = "cp-17-mnpi-wall-enforcement"
CP_16 = "cp-16-abs-securitization-surveillance"
CP_04C = "cp-04-canonical-corporate-family-tree"

#: Benign values in each identifier's own shape. Test fixtures, not estate
#: values: the fake graph leg answers nothing, so no real subject is needed.
BENIGN_LEI = "EX01BENIGN0000000001"
BENIGN_OTHER_LEI = "EX01BENIGN0000000002"
BENIGN_PRINCIPAL = "PRIN-EX01-001"
BENIGN_DEAL = "EX01-BENIGN-2026-1"

#: Each suffix tries to LEAVE the position it is placed in. The brief's five
#: classes — a quote, ``>``, ``}``, a newline, a SPARQL keyword — plus the two
#: escape routes SPARQL itself offers: an ``ECHAR`` backslash, and a ``\\u``
#: codepoint escape that §19.2 decodes before the grammar ever runs. Each is
#: appended to the benign value, so a builder that let it through would send
#: the real question with a second one attached.
HOSTILE_SUFFIXES: Mapping[str, str] = {
    "quote": '" || "a" = "a',
    "angle": "> ?p ?o . ?s ?q <urn:ex01:elsewhere",
    "brace": " } UNION { ?s ?p ?o",
    "newline": "\n} UNION { ?s ?p ?o . FILTER(true",
    "keyword": " UNION SERVICE <urn:ex01:remote>",
    "backslash": '\\" || "a" = "a',
    "codepoint": "\\u0022 || \\u0022a\\u0022 = \\u0022a",
}


# =========================================================================
# Loading a tree's acquisition module — under a UNIQUE name
# =========================================================================


def _acquisition(tree: str) -> ModuleType:
    """``examples/<tree>/acquisition.py``, loaded by path under a name no tree uses.

    Every product tree occupies the bare name ``acquisition`` (``AIA-F-07``);
    loading by exact path under a unique name sidesteps that collision class
    entirely and touches no resident module.
    """
    path = EXAMPLES / tree / "acquisition.py"
    unique = "_ex01_" + re.sub(r"\W", "_", tree)
    resident = sys.modules.get(unique)
    if resident is not None:
        return resident
    spec = importlib.util.spec_from_file_location(unique, path)
    assert spec is not None and spec.loader is not None, path
    module = importlib.util.module_from_spec(spec)
    sys.modules[unique] = module
    spec.loader.exec_module(module)
    assert pathlib.Path(module.__file__ or "").resolve() == path.resolve()
    return module


# =========================================================================
# The fakes — they record the SPARQL text and answer nothing
# =========================================================================


class _RecordingGraph:
    """cp-17's graph leg: ``select(query)`` records and returns no rows."""

    def __init__(self, sink: list[str]) -> None:
        self._sink = sink

    def select(self, query: str) -> list[Mapping[str, str]]:
        self._sink.append(query)
        return []


class _NoDocuments:
    """cp-16's document leg, holding nothing."""

    def anchors(self, *, collection: str, deal_id: str) -> list[Mapping[str, Any]]:
        return []

    def passage_hashes(self, *, collection: str, passage_ids: Any) -> Mapping[str, str]:
        return {}


def _record_cp16_graph(module: ModuleType, monkeypatch: pytest.MonkeyPatch, sink: list[str]) -> None:
    def _query(self: Any, sparql: str) -> tuple[list[Mapping[str, str]], str]:
        sink.append(sparql)
        return [], "unreported"

    monkeypatch.setattr(module._Graph, "_query", _query)


# =========================================================================
# The builders under test — each returns nothing; the sink holds what was sent
# =========================================================================


@dataclass(frozen=True)
class Builder:
    """One query builder, the argument the value reaches, and its guard."""

    label: str
    tree: str
    #: The tree's placement guard that must be the refusing frame.
    guard: str
    #: The token kind the value occupies: ``literal`` or ``iri``.
    kind: str
    #: Call the builder with ``value``; queries land in the sink.
    drive: Callable[[ModuleType, str, pytest.MonkeyPatch, list[str]], None]
    #: The value as it appears in its token (an IRI carries the prefix).
    placed: Callable[[ModuleType, str], str]


def _same(_module: ModuleType, value: str) -> str:
    return value


def _cp16_deal_iri(module: ModuleType, value: str) -> str:
    return f"{module.vocabulary()['graph']['deal_uri_prefix']}{value}"


def _cp17_family(module: ModuleType, value: str, _mp: pytest.MonkeyPatch, sink: list[str]) -> None:
    module._family(_RecordingGraph(sink), module.vocabulary(), lei=value)


def _cp17_reg_fd(module: ModuleType, value: str, _mp: pytest.MonkeyPatch, sink: list[str]) -> None:
    module._reg_fd(_RecordingGraph(sink), module.vocabulary(), lei=value, at=date(2026, 1, 15))


def _cp17_over_wall_lei(module: ModuleType, value: str, _mp: pytest.MonkeyPatch, sink: list[str]) -> None:
    module._over_wall(_RecordingGraph(sink), module.vocabulary(), principal_id=BENIGN_PRINCIPAL, lei=value,
                      valid_at=date(2026, 1, 15), known_by=date(2026, 1, 15))


def _cp17_over_wall_principal(module: ModuleType, value: str, _mp: pytest.MonkeyPatch, sink: list[str]) -> None:
    module._over_wall(_RecordingGraph(sink), module.vocabulary(), principal_id=value, lei=BENIGN_OTHER_LEI,
                      valid_at=date(2026, 1, 15), known_by=date(2026, 1, 15))


def _cp16_graph_triggers(module: ModuleType, value: str, mp: pytest.MonkeyPatch, sink: list[str]) -> None:
    _record_cp16_graph(module, mp, sink)
    graph = module._Graph(url="http://127.0.0.1:9", ledger="urn:ex01:ledger")
    graph.triggers(deal_uri=_cp16_deal_iri(module, value))


def _cp16_triggers(module: ModuleType, value: str, mp: pytest.MonkeyPatch, sink: list[str]) -> None:
    _record_cp16_graph(module, mp, sink)
    graph = module._Graph(url="http://127.0.0.1:9", ledger="urn:ex01:ledger")
    module._triggers(graph, _NoDocuments(), deal_id=value,
                     as_of=datetime(2026, 1, 15, tzinfo=UTC), terms=module.vocabulary())


def _cp16_acquire(module: ModuleType, value: str, mp: pytest.MonkeyPatch, sink: list[str]) -> None:
    """``acquire`` over a relational leg holding NO deal — the watermark read still runs."""
    _record_cp16_graph(module, mp, sink)

    class _NoDealRelational:
        def __init__(self, *, dsn: str, schema: str) -> None:
            del dsn, schema

        def rows(self, sql: str, args: tuple[Any, ...] = ()) -> list[Mapping[str, Any]]:
            return []

        def rows_and_cost(self, *, leg: str, sql: str, args: tuple[Any, ...] = ()) -> tuple[list[Any], Any]:
            return [], module.Scan(leg=leg, records_scanned=0, records_materialized=0, blocks_scanned=0)

    mp.setattr(module, "_Relational", _NoDealRelational)
    role = next(iter(module.perspectives()["perspectives"]))
    estate = module.acquire(
        deal_id=value, asked_at=datetime(2026, 1, 15, tzinfo=UTC), as_of=datetime(2026, 1, 15, tzinfo=UTC),
        intent="trigger-monitoring", perspective=role, requested_granularity=module.granularity_order()[0],
        cohorts=(), loan_sample=0,
        relational_settings={"dsn": "postgresql://ex01.invalid/none", "schema": "ex01"},
        graph_settings={"url": "http://127.0.0.1:9", "ledger": "urn:ex01:ledger"},
        document_settings={"uri": "mongodb://ex01.invalid", "db": "ex01"},
    )
    assert estate.empty, "the fake relational leg holds no deal; acquire must return the empty estate"


def _cp04c_acquire(module: ModuleType, value: str, mp: pytest.MonkeyPatch, sink: list[str]) -> None:
    def _query(self: Any, body: str) -> list[Mapping[str, Any]]:
        sink.append(body)
        return []

    mp.setattr(module._GraphLeg, "query", _query)
    try:
        module.acquire(anchor_lei=value, depth=1,
                       graph={"url": "http://127.0.0.1:9", "ledger": "urn:ex01:ledger"},
                       attributes={"dsn": "postgresql://ex01.invalid/none", "schema": "ex01"})
    except LookupError:
        pass  # the fake ledger carries no node for any LEI: the tree's own no-anchor refusal


BUILDERS: tuple[Builder, ...] = (
    Builder("cp17-family-lei", CP_17, "_literal", "literal", _cp17_family, _same),
    Builder("cp17-reg_fd-lei", CP_17, "_literal", "literal", _cp17_reg_fd, _same),
    Builder("cp17-over_wall-lei", CP_17, "_literal", "literal", _cp17_over_wall_lei, _same),
    Builder("cp17-over_wall-principal", CP_17, "_literal", "literal", _cp17_over_wall_principal, _same),
    Builder("cp16-Graph.triggers-deal_uri", CP_16, "_iri", "iri", _cp16_graph_triggers, _cp16_deal_iri),
    Builder("cp16-triggers-deal_id", CP_16, "_iri", "iri", _cp16_triggers, _cp16_deal_iri),
    Builder("cp16-acquire-deal_id-no-such-deal", CP_16, "_iri", "iri", _cp16_acquire, _cp16_deal_iri),
    Builder("cp04c-acquire-anchor_lei", CP_04C, "_literal", "literal", _cp04c_acquire, _same),
)

BENIGN_BY_LABEL: Mapping[str, str] = {
    builder.label: (BENIGN_DEAL if builder.tree == CP_16 else
                    BENIGN_PRINCIPAL if "principal" in builder.label else BENIGN_LEI)
    for builder in BUILDERS
}


@dataclass(frozen=True)
class Outcome:
    queries: list[str]
    refusal: traceback.FrameSummary | None


def _run(builder: Builder, value: str, monkeypatch: pytest.MonkeyPatch) -> Outcome:
    module = _acquisition(builder.tree)
    sink: list[str] = []
    with monkeypatch.context() as scoped:
        try:
            builder.drive(module, value, scoped, sink)
        except ValueError as refused:
            return Outcome(queries=sink, refusal=traceback.extract_tb(refused.__traceback__)[-1])
    return Outcome(queries=sink, refusal=None)


# =========================================================================
# A SPARQL 1.1 lexer — enough grammar to see a value leave its token
# =========================================================================


class LexicalBreak(AssertionError):
    """The text is not SPARQL a conforming lexer can tokenize at all."""


#: SPARQL 1.1 §19.2: codepoint escapes are decoded BEFORE parsing, anywhere.
_CODEPOINT = re.compile(r"\\u([0-9A-Fa-f]{4})|\\U([0-9A-Fa-f]{8})")
_TOKEN = re.compile(
    r"""
    (?P<space>\s+)
  | (?P<comment>\#[^\n\r]*)
  | (?P<iri><[^<>"{}|^`\\\x00-\x20]*>)
  | (?P<literal>"(?:[^"\\\n\r]|\\[tbnrf"'\\])*"|'(?:[^'\\\n\r]|\\[tbnrf"'\\])*')
  | (?P<variable>[?$][A-Za-z0-9_]+)
  | (?P<operator>&&|\|\||!=|<=|>=|\^\^|[{}()\[\].;,=!<>*/+-])
  | (?P<name>[A-Za-z_][A-Za-z0-9_:-]*)
  | (?P<number>[0-9]+)
    """,
    re.VERBOSE,
)
_ECHAR = {"t": "\t", "b": "\b", "n": "\n", "r": "\r", "f": "\f", '"': '"', "'": "'", "\\": "\\"}


def _tokens(query: str) -> list[tuple[str, str]]:
    text = _CODEPOINT.sub(lambda m: chr(int(m.group(1) or m.group(2), 16)), query)
    found: list[tuple[str, str]] = []
    at = 0
    while at < len(text):
        match = _TOKEN.match(text, at)
        if match is None:
            raise LexicalBreak(f"no SPARQL token at offset {at}: {text[at:at + 40]!r}")
        if match.lastgroup not in ("space", "comment"):
            found.append((str(match.lastgroup), match.group()))
        at = match.end()
    return found


def _value_of(kind: str, token: str) -> str:
    if kind == "literal":
        return re.sub(r"\\(.)", lambda m: _ECHAR[m.group(1)], token[1:-1])
    return token[1:-1]


def _assert_placed_only_as_value(benign_query: str, hostile_query: str, *,
                                 benign: str, hostile: str, kind: str) -> None:
    """Same token structure; the hostile text only where the benign value stood."""
    expected = _tokens(benign_query)
    actual = _tokens(hostile_query)
    assert [k for k, _ in actual] == [k for k, _ in expected], (
        f"the value changed the query's token structure:\n  benign:  {benign_query!r}\n  hostile: {hostile_query!r}"
    )
    slots = 0
    for (k, wanted), (_, got) in zip(expected, actual, strict=True):
        if k == kind and _value_of(k, wanted) == benign:
            slots += 1
            assert _value_of(k, got) == hostile, f"the {kind} the value occupies reads {got!r}"
        else:
            assert got == wanted, f"a token outside the value moved: {wanted!r} -> {got!r}"
    assert slots, f"the benign value {benign!r} is in no {kind} token — this builder never placed it"


# =========================================================================
# The tests
# =========================================================================


@pytest.mark.parametrize("builder", BUILDERS, ids=[b.label for b in BUILDERS])
def test_ex_01_the_benign_question_reaches_the_fake_graph_with_the_value_in_place(
    builder: Builder, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Positive control: the fake is ON the path, and the builder places the value.

    Without this, a builder that never sent a query — or never placed the value
    — would pass every hostile case below by doing nothing.
    """
    module = _acquisition(builder.tree)
    benign = BENIGN_BY_LABEL[builder.label]
    outcome = _run(builder, benign, monkeypatch)
    assert outcome.refusal is None, f"the benign value was refused at {outcome.refusal}"
    assert outcome.queries, "no query reached the fake graph leg"
    for query in outcome.queries:
        _assert_placed_only_as_value(query, query, benign=builder.placed(module, benign),
                                     hostile=builder.placed(module, benign), kind=builder.kind)


@pytest.mark.parametrize("hostile", sorted(HOSTILE_SUFFIXES))
@pytest.mark.parametrize("builder", BUILDERS, ids=[b.label for b in BUILDERS])
def test_ex_01_a_hostile_value_cannot_change_the_query_structure(
    builder: Builder, hostile: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Refused by the tree's own guard with nothing sent, or placed only as a value."""
    module = _acquisition(builder.tree)
    benign = BENIGN_BY_LABEL[builder.label]
    value = benign + HOSTILE_SUFFIXES[hostile]
    baseline = _run(builder, benign, monkeypatch)
    outcome = _run(builder, value, monkeypatch)

    if outcome.refusal is not None:
        assert outcome.refusal.name == builder.guard, (
            f"refused, but by {outcome.refusal.name!r} at {outcome.refusal.filename}, not the tree's"
            f" placement guard {builder.guard!r}"
        )
        assert pathlib.Path(outcome.refusal.filename).resolve() == (EXAMPLES / builder.tree / "acquisition.py").resolve()
        assert outcome.queries == [], "the guard refused only after a query had already been sent"
        return

    assert len(outcome.queries) == len(baseline.queries), "the value changed how many queries were sent"
    for benign_query, hostile_query in zip(baseline.queries, outcome.queries, strict=True):
        _assert_placed_only_as_value(benign_query, hostile_query, benign=builder.placed(module, benign),
                                     hostile=builder.placed(module, value), kind=builder.kind)


def test_ex_01_cp_16s_watermark_read_runs_for_a_deal_that_does_not_exist(monkeypatch: pytest.MonkeyPatch) -> None:
    """Why ``acquire`` is its own row: the graph read precedes the existence check.

    The fake relational leg holds no deal, and the benign question still sends
    exactly one graph query — the watermark read — carrying the deal's IRI. So
    the guard on that IRI is the only thing between a hostile deal id and the
    ledger; the deal-existence check cannot be.
    """
    builder = next(b for b in BUILDERS if b.label.startswith("cp16-acquire"))
    outcome = _run(builder, BENIGN_DEAL, monkeypatch)
    assert outcome.refusal is None and len(outcome.queries) == 1, outcome


def test_ex_01_the_lexer_sees_a_literal_breakout() -> None:
    """Control: the structure comparison FAILS when a quote closes the literal."""
    template = 'SELECT ?s WHERE {{ ?s <urn:p> ?o . FILTER(STR(?o) = "{}") }}'
    with pytest.raises(AssertionError):
        _assert_placed_only_as_value(template.format("X"), template.format('X" || "a" = "a'),
                                     benign="X", hostile='X" || "a" = "a', kind="literal")


def test_ex_01_the_lexer_applies_the_codepoint_pre_pass() -> None:
    """Control: ``\\u0022`` closes a literal, exactly as §19.2 says it does."""
    assert _tokens('"X\\u0022 }') == [("literal", '"X"'), ("operator", "}")]


def test_ex_01_the_lexer_sees_an_iri_breakout_and_a_raw_newline() -> None:
    """Control: ``>`` ends an IRI early, and a raw newline is no literal at all."""
    template = "SELECT ?t WHERE {{ <{}> <urn:p> ?t }}"
    with pytest.raises(AssertionError):
        _assert_placed_only_as_value(template.format("urn:x"), template.format("urn:x> ?a ?b . <urn:y"),
                                     benign="urn:x", hostile="urn:x> ?a ?b . <urn:y", kind="iri")
    with pytest.raises(LexicalBreak):
        _tokens('FILTER(STR(?o) = "X\n")')


def test_ex_01_the_lexer_admits_what_a_literal_may_hold() -> None:
    """Control: ``>``, ``}`` and keywords INSIDE a literal are one literal token."""
    tokens = _tokens('FILTER(STR(?o) = "X> } UNION SERVICE <urn:z>")')
    assert ("literal", '"X> } UNION SERVICE <urn:z>"') in tokens
    assert [k for k, _ in tokens].count("literal") == 1
