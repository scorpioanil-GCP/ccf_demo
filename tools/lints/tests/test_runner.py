"""Unit tests for the `python -m tools.lints` gate runner (D-07)."""

from __future__ import annotations

import pathlib
import subprocess
import sys

from tools.lints import backend_imports, substrate_names
from tools.lints.__main__ import (
    CHECKERS,
    RULE_TREE_SCOPE,
    WHOLE_TREE_CHECKERS,
    build_parser,
    main,
    module_name_for,
    run,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]

#: A substrate name that exists nowhere in this repository, planted in a
#: synthetic adapter package so the scope tests below derive their forbidden
#: word the same way the checker does — from disk — without depending on the
#: real adapter set or on the process's working directory.
FAKE_SUBSTRATE = "zzquux"


def _write(base: pathlib.Path, relpath: str, source: str) -> pathlib.Path:
    path = base / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


def _plant_adapter_package(base: pathlib.Path) -> None:
    """A one-adapter `src/ccf/graph/backends/` under `base`.

    `substrate_names.repo_base_for` walks a checked file's ancestors for the
    directory holding this package, so planting it makes the tmp tree
    self-describing: the vocabulary is `{FAKE_SUBSTRATE}` and nothing else, and
    the test does not inherit the real repo's adapter set through the
    working-directory fallback.
    """
    _write(base, "src/ccf/graph/backends/__init__.py", "")
    _write(base, f"src/ccf/graph/backends/{FAKE_SUBSTRATE}.py", "")


def _paths(findings: list[str]) -> set[str]:
    return {finding.split(":", 1)[0] for finding in findings}


def test_module_names_are_derived_from_the_tree_root(tmp_path: pathlib.Path) -> None:
    root = tmp_path / "src"
    assert module_name_for(root / "ccf" / "ops" / "t.py", root) == "ccf.ops.t"
    assert module_name_for(root / "ccf" / "__init__.py", root) == "ccf"


def test_clean_tree_yields_no_findings(tmp_path: pathlib.Path) -> None:
    _write(tmp_path, "src/ccf/ops/traversal.py", "import pathlib\n")
    assert run(tmp_path, list(("no-hardcoding", "harness-imports", "algorithmic"))) == []


def test_harness_import_under_src_is_caught_by_the_runner(
    tmp_path: pathlib.Path,
) -> None:
    _write(tmp_path, "src/ccf/ops/traversal.py", "import langgraph\n")
    findings = run(tmp_path, ["harness-imports"])
    assert len(findings) == 1
    assert "langgraph" in findings[0]


def test_main_exits_nonzero_on_a_violating_tree(tmp_path: pathlib.Path) -> None:
    _write(tmp_path, "src/ccf/ops/traversal.py", "import langgraph\n")
    assert main(["--all", "--base", str(tmp_path)]) == 1


def test_main_exits_zero_on_a_clean_tree(tmp_path: pathlib.Path) -> None:
    _write(tmp_path, "src/ccf/ops/traversal.py", "import pathlib\n")
    assert main(["--all", "--base", str(tmp_path)]) == 0


def test_missing_trees_are_skipped_not_errors(tmp_path: pathlib.Path) -> None:
    assert main(["--all", "--base", str(tmp_path)]) == 0


def test_examples_and_runtime_trees_are_linted(tmp_path: pathlib.Path) -> None:
    """Runtime is in CINV-02 scope; examples is not (plan 08-01 posture).

    CLAUDE.md §7.3 scopes "zero harness imports" to core, and example 03
    necessarily imports harness SDKs — RULE_TREE_SCOPE exempts the examples
    tree from `harness-imports` while `no-hardcoding` still covers it (see
    tests/lints/test_examples_scope.py for the full posture suite).
    """
    _write(tmp_path, "runtime/ccf_runtime/x.py", "import langgraph\n")
    _write(tmp_path, "examples/00/run.py", "import google.adk\n")
    assert len(run(tmp_path, ["harness-imports"])) == 1


def test_the_real_repo_tree_passes_the_gate() -> None:
    """The CI invocation itself, run as a subprocess exactly as ci.yml does."""
    result = subprocess.run(
        [sys.executable, "-m", "tools.lints", "--all"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


# --- the D-IMPL-93 rules, registered by plan 15.4-07 -------------------------


def test_the_registered_rule_set_is_exactly_these_seven() -> None:
    """A tripwire, not a tautology — nine rules now; the name is plan 15.4-07's.

    The set is spelled out so that adding a rule is a decision someone makes on
    purpose — the same discipline `SUBSTRATE_NAME_EXEMPT_PACKAGES` uses for its
    two entries. `--all` runs the union of both maps (see `main`), so this is
    also the assertion that every registered rule actually runs in CI rather
    than merely existing behind a flag. The closed set has widened twice since
    the name was chosen: `hash-transparent-key` (`cdfe6b9a`) and then
    `guarded-provenance` (`c676603f`, D-IMPL-337) — the second registration
    never touched this test, and the release qualification of `f0656746`
    found it red. The name stays because records cite it by node id; the
    count in it is history, the set below is the contract.
    """
    assert set(CHECKERS) == {
        "no-hardcoding",
        "harness-imports",
        "algorithmic",
        "orchestration-imports",
        "backend-imports",
        "substrate-names",
    }
    assert set(WHOLE_TREE_CHECKERS) == {
        "citations",
        "hash-transparent-key",
        "guarded-provenance",
    }


# --- the D-IMPL-337 rule, registered by c676603f without a runner test -------


_TOKEN_GUARDED = (
    "_MINT = object()\n"
    "\n"
    "class Sealed:\n"
    "    def __init__(self, *, token: object = None) -> None:\n"
    "        if token is not _MINT:\n"
    "            raise TypeError('sealed')\n"
)

_REGISTRY_NAMING_A_GHOST = (
    "from __future__ import annotations\n"
    "from dataclasses import dataclass\n"
    "\n"
    "@dataclass(frozen=True)\n"
    "class GuardedTypeDeclaration:\n"
    "    type_path: str\n"
    "    verifier: str | None = None\n"
    "    boundaries: tuple[str, ...] = ()\n"
    "    verifier_aliases: tuple[str, ...] = ()\n"
    "\n"
    "GUARDED_TYPES = (GuardedTypeDeclaration(type_path='ccf.gone:Ghost'),)\n"
)


def test_guarded_provenance_reads_the_registry_under_base(tmp_path: pathlib.Path) -> None:
    """The rule reads `--base`, like every other rule; the census still bites.

    Until the release qualification of `f0656746` the rule imported its
    registry from the installed `ccf` while its census walked `--base`, so on
    every fixture all nine real declarations fired as *names a module that
    does not exist* and the two clean-tree tests above were red. Negative
    control: a fixture with no registry declares nothing. Positive control:
    an undeclared token-guarded class under the fixture is still reported.
    """
    assert run(tmp_path, ["guarded-provenance"]) == []
    _write(tmp_path, "src/ccf/ops/sealed.py", _TOKEN_GUARDED)
    findings = run(tmp_path, ["guarded-provenance"])
    assert len(findings) == 1, findings
    assert "'Sealed' is token-guarded and undeclared" in findings[0]


def test_guarded_provenance_still_catches_a_registry_naming_a_ghost(
    tmp_path: pathlib.Path,
) -> None:
    """Reading the registry from the tree did not weaken the drift class the
    rule exists for: a declaration naming an absent module is still a finding."""
    _write(tmp_path, "src/ccf/contracts/guarded.py", _REGISTRY_NAMING_A_GHOST)
    findings = run(tmp_path, ["guarded-provenance"])
    assert len(findings) == 1, findings
    assert "'ccf.gone:Ghost' names a module that does not exist" in findings[0]


def test_an_unloadable_registry_is_a_finding_not_a_skip(tmp_path: pathlib.Path) -> None:
    """A registry that is present but will not load is reported, never
    skipped: skipping it would hide every declaration it carries."""
    _write(tmp_path, "src/ccf/contracts/guarded.py", "GUARDED_TYPES = (\n")
    findings = run(tmp_path, ["guarded-provenance"])
    assert len(findings) == 1, findings
    assert "registry failed to load (SyntaxError" in findings[0]


def test_both_new_rules_are_scoped_in_config_not_by_accident() -> None:
    """T-15.4-26: a rule absent from RULE_TREE_SCOPE runs over every tree.

    Both entries are explicit, so a narrowing is an edit someone has to make
    rather than something that happens by omission. The scopes differ, and the
    difference is the point: `backend-imports` is worded over core *code* and
    covers the runtime; `substrate-names` is worded over the core alone,
    because everything outside `src` may legitimately name the substrate a
    deployment asked for.
    """
    assert RULE_TREE_SCOPE["backend-imports"] == ("src", "runtime")
    assert RULE_TREE_SCOPE["substrate-names"] == ("src",)


def test_each_new_rule_has_its_own_flag() -> None:
    parser = build_parser()
    assert parser.parse_args(["--backend-imports"]).selected == ["backend-imports"]
    assert parser.parse_args(["--substrate-names"]).selected == ["substrate-names"]


def test_backend_imports_covers_src_and_runtime_but_not_tests(
    tmp_path: pathlib.Path,
) -> None:
    """The same violating import in four trees; exactly two are reported.

    `tests/` is out of scope deliberately: a per-backend unit suite importing
    the backend it is a unit suite for is the suite doing its job. `examples/`
    follows the other import rules.
    """
    _plant_adapter_package(tmp_path)
    violation = f"from ccf.graph.backends import {FAKE_SUBSTRATE}\n"
    _write(tmp_path, "src/ccf/boot.py", violation)
    _write(tmp_path, "runtime/ccf_runtime/wiring.py", violation)
    _write(tmp_path, "tests/graph/test_zzquux_backend.py", violation)
    _write(tmp_path, "examples/00/run.py", violation)

    findings = run(tmp_path, ["backend-imports"])
    assert _paths(findings) == {
        str(tmp_path / "src" / "ccf" / "boot.py"),
        str(tmp_path / "runtime" / "ccf_runtime" / "wiring.py"),
    }
    assert all("cinv02-backend-import" in finding for finding in findings)


def test_substrate_names_covers_src_alone(tmp_path: pathlib.Path) -> None:
    """The same substrate-naming parameter in four trees; only `src` reports.

    The forbidden word is derived from the adapter package planted in this tmp
    tree, so the assertion exercises the checker's own derivation rather than
    a word typed into the test.
    """
    _plant_adapter_package(tmp_path)
    violation = f"def open_store({FAKE_SUBSTRATE}_dsn: str) -> None: ...\n"
    _write(tmp_path, "src/ccf/deployment/manifest.py", violation)
    _write(tmp_path, "runtime/ccf_runtime/cli.py", violation)
    _write(tmp_path, "tests/graph/test_zzquux_backend.py", violation)
    _write(tmp_path, "examples/00/run.py", violation)

    findings = run(tmp_path, ["substrate-names"])
    assert _paths(findings) == {
        str(tmp_path / "src" / "ccf" / "deployment" / "manifest.py")
    }
    assert all("cinv04-substrate-name" in finding for finding in findings)


def test_the_adapter_package_is_not_reported_by_either_rule(
    tmp_path: pathlib.Path,
) -> None:
    """Inside the adapter package both rules are silent, by construction.

    An adapter names its own substrate and imports its siblings; that is the
    module's whole subject. If this ever went red the exemptions would have
    stopped covering the one place they exist for.
    """
    _plant_adapter_package(tmp_path)
    _write(
        tmp_path,
        f"src/ccf/graph/backends/{FAKE_SUBSTRATE}_write.py",
        f"from ccf.graph.backends import {FAKE_SUBSTRATE}\n"
        f"{FAKE_SUBSTRATE}_dsn: str = ''\n",
    )
    assert run(tmp_path, ["backend-imports", "substrate-names"]) == []


def test_neither_new_rule_can_reach_the_allowlist() -> None:
    """D-13: the allowlist path is structurally unreachable, not merely unused.

    `run()` offers findings to `apply_allowlist` for `no-hardcoding` and for
    nothing else, and neither checker imports anything from
    `tools.lints.no_hardcoding` — so there is no second route to it either.
    This deviates from D-IMPL-93's own wording, which says `allowlist.yaml`
    governs exceptions to these two rules; Dave ruled the stricter reading, and
    the reasons are in `tools/lints/allowlist.yaml`'s header.
    """
    for module in (backend_imports, substrate_names):
        source = pathlib.Path(module.__file__ or "").read_text(encoding="utf-8")
        assert "no_hardcoding" not in source, (
            f"{module.__name__} must not be able to reach apply_allowlist (D-13)"
        )
