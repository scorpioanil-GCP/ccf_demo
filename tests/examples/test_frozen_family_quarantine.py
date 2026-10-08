"""The 12 frozen-family reds are quarantined by name (D-IMPL-378 C4).

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
QUARANTINED: dict[str, dict[str, str]] = {
    "tests/examples/test_s1_00_output.py": {name: "KeyError" for name in _S1_00},
    "tests/examples/test_cp_00_output.py": {
        "test_a_missing_threshold_is_refused_not_defaulted": "UnpinnedArtifactError",
        "test_the_client_returns_a_non_zero_exit_code_on_a_governed_refusal": "UnpinnedArtifactError",
    },
    "tests/examples/test_cp_01_output.py": {
        "test_an_unresolvable_anchor_fails_closed": "KeyError",
    },
}

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


def test_the_roster_is_the_twelve_the_hosted_runs_measured() -> None:
    assert len(_CASES) == 12


@pytest.mark.parametrize(
    ("module", "name", "expected"),
    _CASES,
    ids=[f"{module.rsplit('/', 1)[-1]}::{name}" for module, name, _ in _CASES],
)
def test_each_frozen_family_red_is_a_strict_expected_failure_naming_its_exception(
    module: str, name: str, expected: str
) -> None:
    tree = ast.parse((REPO_ROOT / module).read_text(encoding="utf-8"))
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    assert name in functions, f"{module} no longer defines {name}: the roster follows a rename"
    keywords = _xfail_keywords(functions[name])
    assert keywords is not None, f"{module}::{name} carries no xfail mark"
    strict = keywords.get("strict")
    assert isinstance(strict, ast.Constant) and strict.value is True, f"{module}::{name} is not strict"
    assert "raises" in keywords, f"{module}::{name} names no exception, so it would absorb any failure"
    assert ast.unparse(keywords["raises"]).rsplit(".", 1)[-1] == expected


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


@pytest.mark.parametrize("module", sorted(QUARANTINED), ids=lambda module: module.rsplit("/", 1)[-1])
def test_no_other_frozen_family_quarantine_escapes_the_roster(module: str) -> None:
    """The roster is two-directional: every mark citing the frozen-family cause is on it."""
    tree = ast.parse((REPO_ROOT / module).read_text(encoding="utf-8"))
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
    assert cited == set(QUARANTINED[module]), sorted(cited ^ set(QUARANTINED[module]))
