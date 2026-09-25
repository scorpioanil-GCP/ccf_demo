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
    count in it is history, the set below is the contract. Widened a third
    time by `authorization-invariant` (D-IMPL-353 §4), on purpose and here.
    """
    assert set(CHECKERS) == {
        "no-hardcoding",
        "harness-imports",
        "algorithmic",
        "orchestration-imports",
        "backend-imports",
        "substrate-names",
        "authorization-invariant",
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

def _registry(*declarations: str, prelude: str = "") -> str:
    """A registry module mirroring the real class's field set: six required
    fields, three optional — so the reader's required-field check is exercised
    against the same shape `src/ccf/contracts/guarded.py` declares."""
    return (
        prelude
        + "from __future__ import annotations\n"
        "from dataclasses import dataclass, field\n"
        "\n"
        "@dataclass(frozen=True)\n"
        "class GuardedTypeDeclaration:\n"
        "    type_path: str\n"
        "    authority: str\n"
        "    mint: str\n"
        "    verifier: str | None\n"
        "    boundaries: tuple[str, ...]\n"
        "    propagation: str\n"
        "    residual: str | None = None\n"
        "    verifier_aliases: tuple[str, ...] = ()\n"
        "    notes: tuple[str, ...] = field(default_factory=tuple)\n"
        "\n"
        "GUARDED_TYPES = (\n" + "".join(f"    {d},\n" for d in declarations) + ")\n"
    )


_GHOST = (
    "GuardedTypeDeclaration(type_path='ccf.gone:Ghost', authority='a', mint='ccf.gone:mint',"
    " verifier=None, boundaries=(), propagation='p')"
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
    _write(tmp_path, "src/ccf/contracts/guarded.py", _registry(_GHOST))
    findings = run(tmp_path, ["guarded-provenance"])
    assert len(findings) == 1, findings
    assert "'ccf.gone:Ghost' names a module that does not exist" in findings[0]


def test_an_unreadable_registry_is_a_finding_not_a_skip(tmp_path: pathlib.Path) -> None:
    """A registry that is present but cannot be read is reported, never
    skipped: skipping it would hide every declaration it carries."""
    _write(tmp_path, "src/ccf/contracts/guarded.py", "GUARDED_TYPES = (\n")
    findings = run(tmp_path, ["guarded-provenance"])
    assert len(findings) == 1, findings
    assert "registry could not be read (SyntaxError" in findings[0]


def test_the_registry_is_read_as_literals_and_never_executed(tmp_path: pathlib.Path) -> None:
    """The rule parses the registry; it does not import or run it.

    A registry whose module body would raise if executed still yields its
    declaration, and a declaration whose consulted field is not a literal is a
    finding rather than something resolved by evaluation.
    """
    _write(tmp_path, "src/ccf/contracts/guarded.py", _registry(_GHOST, prelude="raise SystemExit('executed')\n"))
    findings = run(tmp_path, ["guarded-provenance"])
    assert len(findings) == 1, findings
    assert "'ccf.gone:Ghost' names a module that does not exist" in findings[0]
    bound = _GHOST.replace("boundaries=()", "boundaries=_B")
    _write(tmp_path, "src/ccf/contracts/guarded.py", _registry(bound, prelude="_B = ('ccf.x:y',)\n"))
    findings = run(tmp_path, ["guarded-provenance"])
    assert len(findings) == 1, findings
    assert "could not be read" in findings[0] and "is not a string, None or tuple of strings" in findings[0]


def test_every_registry_shape_execution_would_reject_is_a_finding(tmp_path: pathlib.Path) -> None:
    """What the executed dataclass refused, the reader refuses — as ONE
    finding naming the cause, never a silent acceptance and never a traceback.
    Each fixture was a shape the parse-only reader first accepted silently
    (adversarial review of the f0656746 correction group)."""
    cases = [
        ("rebound (lines 19)", _registry(_GHOST) + "GUARDED_TYPES += ()\n"),
        ("rebound (lines 19)", _registry(_GHOST) + "GUARDED_TYPES = ()\n"),
        ("rebound (lines 20)", _registry(_GHOST) + "if True:\n    GUARDED_TYPES += ()\n"),
        ("rebound (lines 19)", _registry(_GHOST) + "for GUARDED_TYPES in ():\n    pass\n"),
        ("rebound (lines 20)", _registry(_GHOST) + "def _extend():\n    global GUARDED_TYPES\n"),
        ("rebound (lines 21)", _registry(_GHOST) + "try:\n    pass\nexcept ValueError as GUARDED_TYPES:\n    pass\n"),
        ("rebound (lines 20)", _registry(_GHOST) + "match ():\n    case GUARDED_TYPES:\n        pass\n"),
        ("rebound (lines 19)", _registry(_GHOST) + "type GUARDED_TYPES = int\n"),
        ("rebound (lines 19)", _registry(_GHOST) + "from os import *\n"),
        ("carries no type_path", _registry(_GHOST.replace("type_path='ccf.gone:Ghost', ", "")).replace("    type_path: str\n", "    type_path: str = ''\n")),
        ("a ** splat", _registry(_GHOST.replace("propagation='p'", "propagation='p', **{}"))),
        ("is repeated", _registry(_GHOST.replace("propagation='p'", "propagation='p', mint='x'"))),
        ("missing required field(s) ['propagation']", _registry(_GHOST.replace(", propagation='p'", ""))),
        ("unknown field 'boundries'", _registry(_GHOST.replace("boundaries=()", "boundries=()"))),
        ("positional arguments", _registry(_GHOST.replace("type_path='ccf.gone:Ghost', ", "'ccf.gone:Ghost', ").replace("(type_path", "("))),
        ("boundaries must be a tuple of strings", _registry(_GHOST.replace("boundaries=()", "boundaries='ccf.x:y'"))),
        ("verifier must be a string or None", _registry(_GHOST.replace("verifier=None", "verifier=('a', 'b')"))),
        ("not a tuple literal", _registry().replace("GUARDED_TYPES = (\n)\n", "GUARDED_TYPES = []\n")),
        ("no GuardedTypeDeclaration class", "GUARDED_TYPES = ()\n"),
        ("not a regular file", None),
    ]
    for expected, source in cases:
        target = tmp_path / "src/ccf/contracts/guarded.py"
        if target.exists() and target.is_dir():
            target.rmdir()
        if source is None:
            target.unlink(missing_ok=True)
            target.mkdir(parents=True)
        else:
            _write(tmp_path, "src/ccf/contracts/guarded.py", source)
        findings = run(tmp_path, ["guarded-provenance"])
        assert len(findings) == 1, (expected, findings)
        assert "could not be read" in findings[0] and expected in findings[0], (expected, findings[0])


def test_the_required_field_rule_is_the_dataclass_rule(tmp_path: pathlib.Path) -> None:
    """`field()` without a default is required; `ClassVar` and `KW_ONLY`
    annotations are not init fields — exactly what dataclasses does, read
    from the class body in the registry file."""
    strict = _registry(_GHOST).replace(
        "    notes: tuple[str, ...] = field(default_factory=tuple)\n",
        "    notes: tuple[str, ...] = field(metadata={})\n"
        "    _: KW_ONLY\n"
        "    kind: ClassVar[str] = 'guarded'\n",
    )
    _write(tmp_path, "src/ccf/contracts/guarded.py", strict)
    findings = run(tmp_path, ["guarded-provenance"])
    assert len(findings) == 1 and "missing required field(s) ['notes']" in findings[0], findings
    _write(tmp_path, "src/ccf/contracts/guarded.py", strict.replace("propagation='p')", "propagation='p', notes=())"))
    findings = run(tmp_path, ["guarded-provenance"])
    assert len(findings) == 1 and "'ccf.gone:Ghost' names a module that does not exist" in findings[0], findings
    for spelling in ("field(default=MISSING)", "dataclasses.field()", "field(default=dataclasses.MISSING)"):
        _write(
            tmp_path,
            "src/ccf/contracts/guarded.py",
            _registry(_GHOST, prelude="import dataclasses\nfrom dataclasses import MISSING\n").replace(
                "field(default_factory=tuple)", spelling
            ),
        )
        findings = run(tmp_path, ["guarded-provenance"])
        assert len(findings) == 1 and "missing required field(s) ['notes']" in findings[0], (spelling, findings)


def test_a_dangling_symlink_at_the_registry_is_a_finding(tmp_path: pathlib.Path) -> None:
    target = tmp_path / "src/ccf/contracts/guarded.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.symlink_to(tmp_path / "nowhere.py")
    findings = run(tmp_path, ["guarded-provenance"])
    assert len(findings) == 1 and "could not be read" in findings[0], findings


def test_a_bom_and_an_annotation_restatement_still_read(tmp_path: pathlib.Path) -> None:
    """Two shapes Python's import accepts must read too: a UTF-8 BOM, and a
    bare annotation of the name after its assignment."""
    source = _registry(_GHOST) + "GUARDED_TYPES: tuple[GuardedTypeDeclaration, ...]\n"
    target = tmp_path / "src/ccf/contracts/guarded.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"\xef\xbb\xbf" + source.encode("utf-8"))
    findings = run(tmp_path, ["guarded-provenance"])
    assert len(findings) == 1, findings
    assert "'ccf.gone:Ghost' names a module that does not exist" in findings[0]


def test_the_parsed_real_registry_equals_the_executed_one() -> None:
    """The reader and the dataclass agree on the tree that matters: every
    declaration in `src/ccf/contracts/guarded.py`, in order, on the four
    consulted fields."""
    from ccf.contracts.guarded import GUARDED_TYPES

    from tools.lints.guarded_provenance import _load_registry

    parsed = _load_registry(REPO_ROOT)
    assert not isinstance(parsed, str), parsed
    assert [d.type_path for d in parsed] == [d.type_path for d in GUARDED_TYPES]
    for read, executed in zip(parsed, GUARDED_TYPES, strict=True):
        assert (read.verifier, read.boundaries, read.verifier_aliases) == (
            executed.verifier,
            tuple(executed.boundaries),
            tuple(executed.verifier_aliases),
        ), read.type_path


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
