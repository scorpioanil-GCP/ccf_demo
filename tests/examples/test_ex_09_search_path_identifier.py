"""EX-09 — an example's ``search_path`` names its schema as ONE quoted identifier.

Security review 2026-09-23, row EX-09: *"Unquoted ``SET search_path TO
{schema}``; only cp-14 uses ``sql.Identifier``"*, fixed under ``D-IMPL-376``
ruling (7) — *"the literal splices removed and SQL identifiers quoted
correctly"*. Measured on ``main`` @ ``d9305603``: **16 sites in 15 modules**
built the statement by f-string, cp-08's wrapping the name in double quotes
without escaping an embedded quote. The repair composes it with the driver's
own ``psycopg.sql`` — ``SQL("SET search_path TO {}").format(Identifier(schema))``
— so the schema reaches PostgreSQL as one identifier whatever it contains.

**Two instruments, because each can miss what the other sees.**

- A STATIC check over every ``examples/**/*.py``: no ``search_path`` statement
  is built by string formatting (f-string, ``str.format``, ``%`` or ``+``). Its
  own controls prove it flags all four shapes, passes the composed one, and
  reads at least the 16 sites the census measured.
- A BEHAVIORAL check at every site the static scan finds: a fake
  ``psycopg.connect`` captures the first statement the site sends for a hostile
  schema name, which must be a ``psycopg.sql.Composable`` rendering to exactly
  ``SET search_path TO "<name, quotes doubled>"``.

**Frozen specimens are held apart, not skipped.** A tree pinned "ZERO files
changed by this work" by its successor's test (``D-IMPL-261``) cannot be edited
by this lane. ``examples/cp-13-covenant-cross-reference`` is one (its pin is
``tests/examples/test_cp_13_canonical_output.py::test_the_specimen_is_untouched_and_no_identity_is_reused``)
and holds one of the 16 sites. Its checks are STRICT expected failures: they
stay executable evidence, and the day the specimen is repaired under a ruling
they XPASS and go red until the marker is removed. The pinned set is derived
from the pins themselves, not listed here.

Offline: no estate, no database, no writes.
"""

from __future__ import annotations

import ast
import importlib.util
import pathlib
import re
import sys
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from types import ModuleType
from typing import Any

import psycopg
import psycopg.sql
import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLES = REPO_ROOT / "examples"

#: The census floor on ``main`` @ ``d9305603``: 16 ``search_path`` statements.
MINIMUM_SEARCH_PATH_SITES = 16

#: Schema names that end the statement and start another if spliced: the first
#: escapes a double-quoted splice (cp-08's form), the second an unquoted one.
HOSTILE_SCHEMAS: Mapping[str, str] = {
    "closes-a-quoted-name": 'ccf_v2"; DROP SCHEMA ccf_v2 CASCADE; --',
    "ends-an-unquoted-name": "ccf_v2; DROP SCHEMA ccf_v2 CASCADE",
}


def _expected(schema: str) -> str:
    """The one statement a correctly quoted identifier renders to."""
    return 'SET search_path TO "' + schema.replace('"', '""') + '"'

_MENTIONS = re.compile(r"search_path", re.IGNORECASE)


# =========================================================================
# The static scan
# =========================================================================


@dataclass(frozen=True, order=True)
class Site:
    """One ``search_path`` statement: where it is, and how it is built."""

    path: str
    symbol: str
    shape: str

    @property
    def tree(self) -> str:
        return self.path.split("/")[1]

    @property
    def string_built(self) -> bool:
        return self.shape != "composed"

    def __str__(self) -> str:
        return f"{self.path}::{self.symbol} ({self.shape})"


def _mentions(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) and isinstance(node.value, str) and bool(_MENTIONS.search(node.value))


def _is_sql_composer(func: ast.AST) -> bool:
    """``SQL(...)`` or ``<module>.SQL(...)`` — the driver's composable statement."""
    return (isinstance(func, ast.Name) and func.id == "SQL") or (isinstance(func, ast.Attribute) and func.attr == "SQL")


class _Scanner(ast.NodeVisitor):
    def __init__(self, path: str) -> None:
        self.path = path
        self.scope: list[str] = []
        self.sites: list[Site] = []

    def _add(self, shape: str) -> None:
        self.sites.append(Site(self.path, ".".join(self.scope) or "<module>", shape))

    def _scoped(self, node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    visit_ClassDef = _scoped
    visit_FunctionDef = _scoped
    visit_AsyncFunctionDef = _scoped

    def visit_JoinedStr(self, node: ast.JoinedStr) -> None:
        if any(_mentions(part) for part in node.values) and any(
            isinstance(part, ast.FormattedValue) for part in node.values
        ):
            self._add("f-string")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr == "format":
            target = func.value
            if _mentions(target):
                self._add("str.format")
            elif (isinstance(target, ast.Call) and _is_sql_composer(target.func)
                  and target.args and _mentions(target.args[0])):
                self._add("composed")
        self.generic_visit(node)

    def visit_BinOp(self, node: ast.BinOp) -> None:
        if isinstance(node.op, ast.Mod) and _mentions(node.left):
            self._add("%-format")
        elif isinstance(node.op, ast.Add) and (
            (_mentions(node.left) and not isinstance(node.right, ast.Constant))
            or (_mentions(node.right) and not isinstance(node.left, ast.Constant))
        ):
            self._add("concatenation")
        self.generic_visit(node)


def _scan_source(source: str, path: str) -> list[Site]:
    scanner = _Scanner(path)
    scanner.visit(ast.parse(source))
    return scanner.sites


def _example_modules() -> Iterator[pathlib.Path]:
    for path in sorted(EXAMPLES.rglob("*.py")):
        relative = path.relative_to(EXAMPLES).parts
        if "__pycache__" in relative or any(part.startswith(".") for part in relative):
            continue
        yield path


def _scan_examples() -> list[Site]:
    sites: list[Site] = []
    for path in _example_modules():
        sites += _scan_source(path.read_text(encoding="utf-8"), path.relative_to(REPO_ROOT).as_posix())
    return sorted(sites)


# =========================================================================
# Frozen specimens — derived from the pins that freeze them
# =========================================================================

_SPECIMEN_PIN = re.compile(r'^SPECIMEN\s*=\s*REPO_ROOT\s*/\s*"examples"\s*/\s*"([^"]+)"', re.MULTILINE)


def _pinned_specimens() -> Mapping[str, str]:
    """``tree -> pinning test module`` for every tree pinned "ZERO files changed".

    A tree counts only when the module that names it as ``SPECIMEN`` also runs
    the ``git diff --name-only`` pin over it — the pin, not the name, is what
    freezes it.
    """
    pinned: dict[str, str] = {}
    for test in sorted((REPO_ROOT / "tests" / "examples").glob("test_*.py")):
        text = test.read_text(encoding="utf-8")
        if '"--name-only"' not in text:
            continue
        for tree in _SPECIMEN_PIN.findall(text):
            pinned[tree] = test.name
    return pinned


PINNED = _pinned_specimens()
FROZEN_REASON = (
    "frozen specimen under D-IMPL-261 (pinned ZERO-files-changed by its successor's test); the"
    " EX-09 brief says both 'fix every site' and 'do not touch any frozen specimen' — raised by"
    " lane EX-01/EX-09 for a ruling, not edited"
)


# =========================================================================
# The static tests
# =========================================================================


def test_ex_09_no_search_path_statement_in_examples_is_built_by_string_formatting() -> None:
    sites = _scan_examples()
    open_sites = [site for site in sites if site.string_built and site.tree not in PINNED]
    held = [site for site in sites if site.string_built and site.tree in PINNED]
    assert open_sites == [], (
        f"{len(open_sites)} search_path statement(s) built by string formatting"
        f" (plus {len(held)} in frozen specimens, held by the strict expected failure):\n  "
        + "\n  ".join(map(str, open_sites))
    )


@pytest.mark.xfail(strict=True, reason=FROZEN_REASON)
def test_ex_09_frozen_specimens_build_no_search_path_by_string_formatting() -> None:
    held = [site for site in _scan_examples() if site.string_built and site.tree in PINNED]
    assert held == [], "\n  ".join(map(str, held))


def test_ex_09_the_scanner_tells_string_formatting_from_composition() -> None:
    """Control: all four string-built shapes are flagged; the composed one is not."""
    # One literal per line: a single multi-line block of code reads as a
    # template to the No-Hardcoding lint (CINV-01a), which it is not.
    source = "\n".join([
        "def f(cursor, schema, other):",
        '    cursor.execute(f"SET search_path TO {schema}")',
        '    cursor.execute("SET search_path TO {}".format(schema))',
        '    cursor.execute("SET search_path TO %s" % schema)',
        '    cursor.execute("SET search_path TO " + schema)',
        '    cursor.execute(SQL("SET search_path TO {}").format(Identifier(schema)))',
        '    cursor.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))',
        '    cursor.execute(f"SELECT {other} FROM t")',
    ])
    shapes = [site.shape for site in _scan_source(source, "examples/control/acquisition.py")]
    assert sorted(shapes) == sorted(["f-string", "str.format", "%-format", "concatenation", "composed", "composed"])


def test_ex_09_the_scan_reads_every_search_path_site() -> None:
    """Control: the scan is not vacuous — it reads at least the census's 16 sites."""
    sites = _scan_examples()
    assert len(sites) >= MINIMUM_SEARCH_PATH_SITES, "\n  ".join(map(str, sites))


def test_ex_09_the_frozen_set_is_read_from_the_pins() -> None:
    """Control: the derivation finds the pins the brief names and the one it did not."""
    assert "cp-04-corporate-family-tree" in PINNED, PINNED
    assert "cp-13-covenant-cross-reference" in PINNED, PINNED


# =========================================================================
# The behavioral check — a fake connection captures the composed statement
# =========================================================================


class _Captured(Exception):
    """Raised by the fake on the first statement, so nothing after it runs."""


class _FakeCursor:
    def __init__(self, sink: list[Any]) -> None:
        self._sink = sink

    def __enter__(self) -> _FakeCursor:
        return self

    def __exit__(self, *exc: object) -> bool:
        return False

    def execute(self, statement: Any, params: Any = None) -> Any:
        self._sink.append(statement)
        raise _Captured


class _FakeConnection(_FakeCursor):
    def __enter__(self) -> _FakeConnection:
        return self

    def cursor(self, *args: Any, **kwargs: Any) -> _FakeCursor:
        return _FakeCursor(self._sink)


def _module(path: str) -> ModuleType:
    """``path`` loaded under a unique name — no tree's bare ``acquisition`` is touched."""
    unique = "_ex09_" + re.sub(r"\W", "_", path)
    resident = sys.modules.get(unique)
    if resident is not None:
        return resident
    spec = importlib.util.spec_from_file_location(unique, REPO_ROOT / path)
    assert spec is not None and spec.loader is not None, path
    module = importlib.util.module_from_spec(spec)
    sys.modules[unique] = module
    spec.loader.exec_module(module)
    return module


_DSN = "postgresql://ex09.invalid/none"


def _rows(module: ModuleType, schema: str) -> None:
    module._Relational(dsn=_DSN, schema=schema).rows("SELECT 1")


def _rows_and_cost(module: ModuleType, schema: str) -> None:
    module._Relational(dsn=_DSN, schema=schema).rows_and_cost(leg="ex09", sql="SELECT 1")


def _cp08_acquire(module: ModuleType, schema: str) -> None:
    module.acquire(facility_id="FAC-EX09", as_of="2026-01-15", graph_url="http://127.0.0.1:9",
                   graph_ledger="urn:ex09:ledger", postgres_dsn=_DSN, postgres_schema=schema,
                   vocabulary={"graph_leg": {"node_namespace": "urn:ex09:"}, "attribute_leg": {}})


_ACQ = "examples/{}/acquisition.py"
SITE_DRIVERS: Mapping[tuple[str, str], Callable[[ModuleType, str], None]] = {
    (_ACQ.format("cp-08-covenant-in-force-as-of"), "acquire"): _cp08_acquire,
    (_ACQ.format("cp-09-treasury-liquidity-position"), "_Relational.rows"): _rows,
    (_ACQ.format("cp-10-rating-and-spread-migration"), "_Relational.rows"): _rows,
    (_ACQ.format("cp-11-credit-surveillance-early-warning"), "_Relational.rows"): _rows,
    (_ACQ.format("cp-12-fx-post-trade-reconciliation"), "_Relational.rows"): _rows,
    (_ACQ.format("cp-13-canonical-covenant-cross-reference"), "_Relational.rows"): _rows,
    (_ACQ.format("cp-13-covenant-cross-reference"), "_Relational.rows"): _rows,
    (_ACQ.format("cp-15-kyc-refresh-beneficial-ownership"), "_Relational.rows"): _rows,
    (_ACQ.format("cp-16-abs-securitization-surveillance"), "_Relational.rows"): _rows,
    (_ACQ.format("cp-16-abs-securitization-surveillance"), "_Relational.rows_and_cost"): _rows_and_cost,
    (_ACQ.format("cp-17-mnpi-wall-enforcement"), "_Relational.rows"): _rows,
    (_ACQ.format("cp-18-ib-opportunity-synthesis"), "_Relational.rows"): _rows,
    (_ACQ.format("cp-19-aml-typology-match"), "_Relational.rows"): _rows,
    (_ACQ.format("cp-21-large-exposure"), "_Relational.rows"): _rows,
    (_ACQ.format("cp-23-portfolio-early-warning"), "_Relational.rows"): _rows,
    (_ACQ.format("cp-24-portfolio-what-if"), "_Relational.rows"): _rows,
}


def _site_params() -> list[Any]:
    params = []
    for path, symbol in SITE_DRIVERS:
        tree = path.split("/")[1]
        marks = [pytest.mark.xfail(strict=True, reason=FROZEN_REASON)] if tree in PINNED else []
        params.append(pytest.param(path, symbol, id=f"{tree}::{symbol}", marks=marks))
    return params


def test_ex_09_every_scanned_site_has_a_behavioral_driver() -> None:
    """Control: the behavioral check covers exactly the sites the static scan finds."""
    scanned = {(site.path, site.symbol) for site in _scan_examples()}
    assert scanned == set(SITE_DRIVERS), (
        f"scanned but not driven: {sorted(scanned - set(SITE_DRIVERS))};"
        f" driven but not scanned: {sorted(set(SITE_DRIVERS) - scanned)}"
    )


@pytest.mark.parametrize("hostile", sorted(HOSTILE_SCHEMAS))
@pytest.mark.parametrize(("path", "symbol"), _site_params())
def test_ex_09_the_schema_reaches_postgres_as_one_quoted_identifier(
    path: str, symbol: str, hostile: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    schema = HOSTILE_SCHEMAS[hostile]
    sink: list[Any] = []
    monkeypatch.setattr(psycopg, "connect", lambda *args, **kwargs: _FakeConnection(sink))
    with pytest.raises(_Captured):
        SITE_DRIVERS[(path, symbol)](_module(path), schema)
    assert len(sink) == 1, sink
    statement = sink[0]
    assert isinstance(statement, psycopg.sql.Composable), (
        f"{path}::{symbol} sent its search_path as a {type(statement).__name__}, not a composed"
        f" psycopg.sql statement: {statement!r}"
    )
    assert statement.as_string() == _expected(schema)
