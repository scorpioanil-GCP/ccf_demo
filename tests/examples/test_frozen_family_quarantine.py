# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""The frozen-family reds are quarantined by name (D-IMPL-378 C4) — and s1-00's are released.

**Amended 2026-10-11 (Dave's ruling 6, 16:23 MST; `examples/AMENDMENTS-2026-10-11.md`).**
s1-00 was repaired (its deployment reads the placed keys) and its nine
`xfail(strict, raises=KeyError)` marks were REMOVED, not relabeled: *"remove the
obsolete missing-key expected-failure marks once the example is repaired … Do not
replace the old expected-failure label with an expiry label."* The roster below
is therefore three (cp-00 and cp-01), and
:func:`test_the_released_s1_00_tests_carry_no_expected_failure_mark` asserts
the released nine still exist and carry no xfail mark of any kind — so a
re-quarantine under a new label goes red here rather than passing silently.

**Amended again 2026-10-11 (Dave's ruling 3 and ruling 6, 16:23 MST; integration
of `r2-frozen` at `cebfb1d5`).** The frozen cp-00 and cp-01 specimens received
their authorized compatibility repairs (they read tenant-placed keys and serve
through the governed resolver; `examples/AMENDMENTS-2026-10-11.md`, R2-F-05 and
CP01/02-R2), and their quarantines were REMOVED — cp-00's two
`UnpinnedArtifactError` marks and cp-01's one `KeyError` mark, by name below.
The strict-xfail roster is therefore EMPTY, and every one of the twelve tests
it once named is on :data:`RELEASED`, checked by name to still exist and to
carry no xfail mark. The two meta-checks keep their positive controls (a
synthetic strict quarantine is read as one; a synthetic mark citing the cause
is caught), so an empty roster cannot make them vacuous.

Dave's D-IMPL-355 (Option A) keeps s1-00, cp-00 and cp-01 out of the repair.
Their deployments read bare Control Plane keys that the placed-key Control
Plane no longer serves (SEC353-G-07). D-IMPL-261's route is a STRICT expected
failure: the tests keep running in the Postgres leg, and the day one passes CI
goes red. Each mark names the exception class measured on hosted run
37732648612, so a failure of any other class is reported rather than absorbed;
a different failure of the same class still is not, because ``raises=`` checks
the class only. The modules are read
statically, because they run only in the Postgres leg and this check must run
in the quick suite.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

_S1_00 = (
    "test_the_threshold_selects",
    "test_two_thresholds_are_two_products",
    "test_the_same_question_is_stable",
    "test_a_missing_threshold_is_refused_not_defaulted",
    "test_debt_is_driven_by_last_updated",
    "test_debt_rides_the_product",
    "test_one_operator_and_the_gates_agree",
    "test_the_record_is_written_before_delivery",
    "test_the_answer_is_the_select_plus_four_things_it_cannot_return",
)

#: module path -> {test name: the class name of the exception its quarantine expects}
#:
#: EMPTY since the 2026-10-11 compatibility repairs (ruling 3). Released, by name:
#: cp-00 ``test_a_missing_threshold_is_refused_not_defaulted`` and
#: ``test_the_client_returns_a_non_zero_exit_code_on_a_governed_refusal``
#: (both ``UnpinnedArtifactError``); cp-01 ``test_an_unresolvable_anchor_fails_closed``
#: (``KeyError``). A new frozen-family quarantine joins here by an edit.
QUARANTINED: dict[str, dict[str, str]] = {}

_CASES = [
    (module, name, expected)
    for module, names in QUARANTINED.items()
    for name, expected in names.items()
]


def _xfail_keywords(function: ast.FunctionDef) -> dict[str, ast.expr] | None:
    for decorator in function.decorator_list:
        if isinstance(decorator, ast.Call) and ast.unparse(decorator.func) == "pytest.mark.xfail":
            return {keyword.arg: keyword.value for keyword in decorator.keywords if keyword.arg}
    return None


#: Released by ruling 6 (2026-10-11): the nine s1-00 tests, repaired; and the
#: three frozen cp-00/cp-01 tests, released by the ruling-3 compatibility repairs.
RELEASED: dict[str, tuple[str, ...]] = {
    "tests/examples/test_s1_00_output.py": _S1_00,
    "tests/examples/test_cp_00_output.py": (
        "test_a_missing_threshold_is_refused_not_defaulted",
        "test_the_client_returns_a_non_zero_exit_code_on_a_governed_refusal",
    ),
    "tests/examples/test_cp_01_output.py": ("test_an_unresolvable_anchor_fails_closed",),
}


def test_the_roster_is_empty_and_every_former_member_is_released_by_name() -> None:
    """Twelve were measured on hosted run 37732648612; all twelve are released, by name."""
    assert QUARANTINED == {}
    released = {(module, name) for module, names in RELEASED.items() for name in names}
    assert released == {("tests/examples/test_s1_00_output.py", name) for name in _S1_00} | {
        ("tests/examples/test_cp_00_output.py", "test_a_missing_threshold_is_refused_not_defaulted"),
        (
            "tests/examples/test_cp_00_output.py",
            "test_the_client_returns_a_non_zero_exit_code_on_a_governed_refusal",
        ),
        ("tests/examples/test_cp_01_output.py", "test_an_unresolvable_anchor_fails_closed"),
    }


@pytest.mark.parametrize(
    ("module", "name"),
    [(module, name) for module, names in RELEASED.items() for name in names],
    ids=[f"{module.rsplit('/', 1)[-1]}::{name}" for module, names in RELEASED.items() for name in names],
)
def test_the_released_tests_carry_no_expected_failure_mark(module: str, name: str) -> None:
    """Each released test still exists and carries NO xfail mark — not a relabeled one."""
    tree = ast.parse((REPO_ROOT / module).read_text(encoding="utf-8"))
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    assert name in functions, f"{module} no longer defines {name}: the release follows a rename"
    assert _xfail_keywords(functions[name]) is None, (
        f"{module}::{name} carries an xfail mark again; ruling 6 released it"
    )


def _strict_quarantine_problem(tree: ast.Module, name: str, expected: str) -> str | None:
    """Why ``name`` in ``tree`` is NOT a strict xfail naming ``expected``; ``None`` when it is."""
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    if name not in functions:
        return f"no longer defines {name}: the roster follows a rename"
    keywords = _xfail_keywords(functions[name])
    if keywords is None:
        return f"{name} carries no xfail mark"
    strict = keywords.get("strict")
    if not (isinstance(strict, ast.Constant) and strict.value is True):
        return f"{name} is not strict"
    if "raises" not in keywords:
        return f"{name} names no exception, so it would absorb any failure"
    if ast.unparse(keywords["raises"]).rsplit(".", 1)[-1] != expected:
        return f"{name} expects {ast.unparse(keywords['raises'])}, not {expected}"
    return None


@pytest.mark.parametrize(
    ("module", "name", "expected"),
    _CASES,
    ids=[f"{module.rsplit('/', 1)[-1]}::{name}" for module, name, _ in _CASES],
)
def test_each_frozen_family_red_is_a_strict_expected_failure_naming_its_exception(
    module: str, name: str, expected: str
) -> None:
    """Every rostered quarantine is strict and names its class. Empty roster: no cases run."""
    tree = ast.parse((REPO_ROOT / module).read_text(encoding="utf-8"))
    problem = _strict_quarantine_problem(tree, name, expected)
    assert problem is None, f"{module}: {problem}"


def test_the_strict_quarantine_check_still_reads_a_mark() -> None:
    """Positive control: with the roster empty, the checker above must still discriminate."""
    good = ast.parse(
        "import pytest\n"
        "@pytest.mark.xfail(strict=True, raises=KeyError, reason='SEC353-G-07')\n"
        "def test_x():\n    pass\n"
    )
    assert _strict_quarantine_problem(good, "test_x", "KeyError") is None
    assert "not strict" in str(
        _strict_quarantine_problem(
            ast.parse("import pytest\n@pytest.mark.xfail(raises=KeyError)\ndef test_x():\n    pass\n"),
            "test_x",
            "KeyError",
        )
    )
    assert "names no exception" in str(
        _strict_quarantine_problem(
            ast.parse("import pytest\n@pytest.mark.xfail(strict=True)\ndef test_x():\n    pass\n"),
            "test_x",
            "KeyError",
        )
    )
    assert "carries no xfail mark" in str(
        _strict_quarantine_problem(ast.parse("def test_x():\n    pass\n"), "test_x", "KeyError")
    )
    assert "expects" in str(_strict_quarantine_problem(good, "test_x", "UnpinnedArtifactError"))


#: A quarantine in these modules that cites the frozen-family cause joins the
#: roster by an edit here; outside it, nothing checks its `raises=` (final
#: review of D-IMPL-378 C4).
_QUARANTINE_MARKERS = ("SEC353-G-07", "D-IMPL-378 C4")


def _module_strings(tree: ast.Module) -> dict[str, str]:
    """Module-level names bound to a string constant: a mark's reason may be one."""
    strings: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    strings[target.id] = node.value.value
    return strings


def _citing_the_cause(tree: ast.Module) -> set[str]:
    """Names of the tests in ``tree`` whose xfail reason cites the frozen-family cause."""
    strings = _module_strings(tree)
    cited = set()
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        keywords = _xfail_keywords(node)
        if keywords is None or "reason" not in keywords:
            continue
        reason = keywords["reason"]
        text = reason.value if isinstance(reason, ast.Constant) else strings.get(ast.unparse(reason), "")
        if any(marker in str(text) for marker in _QUARANTINE_MARKERS):
            cited.add(node.name)
    return cited


@pytest.mark.parametrize(
    "module", sorted(set(QUARANTINED) | set(RELEASED)), ids=lambda module: module.rsplit("/", 1)[-1]
)
def test_no_other_frozen_family_quarantine_escapes_the_roster(module: str) -> None:
    """The roster is two-directional: every mark citing the frozen-family cause is on it."""
    tree = ast.parse((REPO_ROOT / module).read_text(encoding="utf-8"))
    cited = _citing_the_cause(tree)
    assert cited == set(QUARANTINED.get(module, {})), sorted(cited ^ set(QUARANTINED.get(module, {})))


def test_the_escape_scan_still_catches_a_mark_citing_the_cause() -> None:
    """Positive control: a mark citing the cause (inline or via a module constant) is caught."""
    source = (
        "import pytest\n"
        "WHY = 'frozen family, D-IMPL-378 C4'\n"
        "@pytest.mark.xfail(strict=True, raises=KeyError, reason='bare key SEC353-G-07')\n"
        "def test_inline():\n    pass\n"
        "@pytest.mark.xfail(strict=True, raises=KeyError, reason=WHY)\n"
        "def test_constant():\n    pass\n"
        "@pytest.mark.xfail(strict=True, raises=KeyError, reason='an unrelated cause')\n"
        "def test_unrelated():\n    pass\n"
    )
    assert _citing_the_cause(ast.parse(source)) == {"test_inline", "test_constant"}
