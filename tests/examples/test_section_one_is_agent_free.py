"""Section 1 is agent-free by construction, and this is what makes it true.

Phase 16 CONTEXT `D-12` answers UAT gap G-01: readers arrived at the SDK with an
agent-first mental model because the documentation and the examples suite put an
agent in front of the fabric. The fix is structural rather than editorial —
Section 1 of the suite reaches no agent surface at all — and a structural claim
that nothing enforces is an editorial claim wearing better clothes.

So this module is the gate. Every Python module under every ``examples/s1-*``
directory is parsed and its imports are read; if any of them reaches the agent,
skill, workflow, HITL or harness-adapter surface, the build fails. The scan is a
**glob, not a list**, so plan 16-08's second Section-1 example arms this gate on
the day it lands rather than on the day someone remembers to add it here.

**Why AST rather than grep.** A grep for ``ccf.agents`` matches a docstring, a
comment and a URL as readily as an import, and misses ``from ccf import
agents``. The import graph is a syntactic fact, so it is read syntactically.

**Why both ``tools.lints`` helpers, and why no local copy.**
:func:`imported_module_names` reports ``ccf`` for ``from ccf import agents`` —
correctly, since it cannot tell a submodule from an attribute without importing,
which a lint must not do. :func:`submodule_import_names` supplements it with
``ccf.agents``. Phase 15.4's review finding CR-02 was exactly this hole: a local
``_ccf_imports`` helper (the one still in
``tests/agents/test_consumption_discipline.py``) is blind to that spelling, and
copying it here would reproduce the blindness. The shared helpers live in
``tools/lints`` because, in their own docstring, *"a helper imported from a
sibling checker is how one rule's edit silently changes another's."*

The negative control below carries the CR-02 spelling deliberately: remove
:func:`submodule_import_names` from :func:`reached_modules` and
``from ccf import agents`` walks straight through the guard, which is the
failure mode this module is shaped around.
"""

from __future__ import annotations

import ast
import pathlib
import shutil
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

if str(REPO_ROOT) not in sys.path:  # the tools/ package is not installed
    sys.path.insert(0, str(REPO_ROOT))

from tools.lints import (  # noqa: E402
    imported_module_names,
    submodule_import_names,
)

#: The tree the scan walks. Passed as an argument everywhere below so the
#: negative control can repoint it at a copy and exercise the real predicate.
EXAMPLES_ROOT = REPO_ROOT / "examples"

#: Section 1 by directory-name convention, and a glob rather than a list so a
#: second Section-1 example arms this gate by existing. ``**`` matches this
#: directory and all subdirectories, so a module nested under an example is in
#: scope too.
SECTION_ONE_GLOB = "s1-*/**/*.py"

#: What a Section-1 module may not reach. Each entry carries the criterion and
#: the decision that put it there, so the list stays reviewable rather than
#: accreted — a deny list nobody can justify entry by entry is a deny list that
#: grows by cargo cult.
DENIED_PACKAGES: tuple[tuple[str, str], ...] = (
    # The Agent Specialization Framework itself (CLAUDE.md §6). Section 1 shows
    # the fabric producing a Context Product; an agent consuming one is
    # Section 3's subject.
    ("ccf.agents", "criterion 2 / D-12 — Section 1 declares no agent"),
    # Skilling is channel 2 of specialization (CLAUDE.md §6.2) and has no
    # meaning without an agent to bind a skill to.
    ("ccf.skills", "criterion 2 / D-12 — no skill catalog before an agent"),
    # Orchestration (CLAUDE.md §8.1). A workflow composes agent nodes.
    ("ccf.workflow", "criterion 2 / D-12 — no workflow in the fabric section"),
    # HITL primitives (CLAUDE.md §8.2) gate workflow steps.
    ("ccf.hitl", "criterion 2 / D-12 — no approval gate in the fabric section"),
    # Harness adapters (CLAUDE.md §7.3) bind an agent definition to a loop.
    # Section 1 has no loop to bind.
    (
        "ccf_runtime.adapters",
        "criterion 2 / D-12 — the fabric section binds no harness",
    ),
)


# ---------------------------------------------------------------------------
# The scan.
# ---------------------------------------------------------------------------


def section_one_modules(root: pathlib.Path) -> list[pathlib.Path]:
    """Every Python module under every Section-1 example directory in `root`."""
    return sorted(root.glob(SECTION_ONE_GLOB))


def reached_modules(source: str) -> set[str]:
    """Every module name the source's import statements bring into scope.

    The union of the two ``tools.lints`` helpers. Over-reaching costs nothing —
    a name that is an attribute rather than a submodule simply never matches a
    deny entry — and under-reaching is CR-02.
    """
    reached: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        reached.update(imported_module_names(node))
        reached.update(submodule_import_names(node))
    return reached


def denied_imports(path: pathlib.Path) -> list[str]:
    """The denied package names one module reaches, sorted, deduplicated."""
    reached = reached_modules(path.read_text(encoding="utf-8"))
    return sorted(
        {
            package
            for package, _reason in DENIED_PACKAGES
            for name in reached
            if name == package or name.startswith(f"{package}.")
        }
    )


def offenders(root: pathlib.Path) -> dict[str, list[str]]:
    """``module path -> denied packages it reaches``, for every offender."""
    found: dict[str, list[str]] = {}
    for module in section_one_modules(root):
        denied = denied_imports(module)
        if denied:
            found[module.relative_to(root).as_posix()] = denied
    return found


# ---------------------------------------------------------------------------
# Preconditions — a vacuous pass is the failure this module exists to prevent.
# ---------------------------------------------------------------------------


def test_the_section_one_tree_is_populated() -> None:
    """Without this, a renamed ``examples/s1-*`` makes every check below pass
    over an empty set, and the agent-free claim becomes a claim about nothing.
    """
    assert EXAMPLES_ROOT.is_dir(), f"missing examples tree: {EXAMPLES_ROOT}"
    directories = sorted(
        path for path in EXAMPLES_ROOT.glob("s1-*") if path.is_dir()
    )
    assert directories, (
        f"no Section-1 example directories under {EXAMPLES_ROOT} — the"
        " agent-free gate is scanning nothing"
    )
    assert section_one_modules(EXAMPLES_ROOT), (
        f"Section-1 directories exist under {EXAMPLES_ROOT} but contain no"
        f" Python modules matching {SECTION_ONE_GLOB!r}"
    )


def test_the_deny_list_documents_every_entry() -> None:
    """Each denied package carries the criterion that put it there."""
    for package, reason in DENIED_PACKAGES:
        assert reason.strip(), f"{package} has no recorded reason"


# ---------------------------------------------------------------------------
# The gate.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "module",
    section_one_modules(EXAMPLES_ROOT),
    ids=lambda path: path.relative_to(EXAMPLES_ROOT).as_posix(),
)
def test_no_section_one_module_reaches_an_agent_surface(
    module: pathlib.Path,
) -> None:
    """Criterion 2, per module, named in the failure.

    Parametrized rather than aggregated so the failing module is the test id
    rather than a name buried in an assertion message.
    """
    denied = denied_imports(module)
    assert not denied, (
        f"{module.relative_to(REPO_ROOT).as_posix()} imports {denied} —"
        " Section 1 of the examples suite is agent-free by construction"
        " (phase 16 CONTEXT D-12, criterion 2; CLAUDE.md §§6, 7.3, 8.1, 8.2)."
        " If this example needs an agent, it belongs in Section 3."
    )


def test_the_shipped_tree_has_no_offender() -> None:
    """The same claim once more, aggregated — so a failure names every
    offending module at once rather than one per run."""
    found = offenders(EXAMPLES_ROOT)
    assert not found, found


# ---------------------------------------------------------------------------
# The negative control — a guard that has never refused anything is a guard
# nobody has tested.
# ---------------------------------------------------------------------------


def _copied_section_one(tmp_path: pathlib.Path) -> pathlib.Path:
    """The shipped Section-1 modules, copied under a fresh scan root.

    Copied rather than synthesized so the control exercises the real files, the
    real glob and the real AST walk.
    """
    for module in section_one_modules(EXAMPLES_ROOT):
        destination = tmp_path / module.relative_to(EXAMPLES_ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(module, destination)
    return sorted(section_one_modules(tmp_path))[0]


@pytest.mark.parametrize(
    "injected",
    [
        pytest.param(
            "from ccf.agents import AgentFactory\n",
            id="from-ccf.agents-import-name",
        ),
        pytest.param(
            "from ccf import agents\n",
            id="from-ccf-import-agents (CR-02 spelling)",
        ),
        pytest.param("import ccf.skills\n", id="import-ccf.skills"),
    ],
)
def test_the_guard_refuses_an_injected_agent_import(
    tmp_path: pathlib.Path, injected: str
) -> None:
    """The guard is verified to REFUSE, not merely to pass.

    ``from ccf import agents`` is the spelling that passes
    :func:`imported_module_names` alone — it reports ``ccf``, which matches no
    deny entry. It is caught only because :func:`reached_modules` also asks
    :func:`submodule_import_names`, and it is parametrized here so that
    dropping that call turns this case red rather than turning the whole suite
    quietly permissive (review finding CR-02).

    The import is APPENDED rather than prepended. Section-1 modules open with a
    docstring followed by ``from __future__ import annotations``, and only a
    docstring and comments may precede a ``__future__`` import — a prepended
    line would make the copy unparseable, which is a syntax error masquerading
    as a caught violation.
    """
    target = _copied_section_one(tmp_path)

    # The copies alone still pass — so the refusal below is the injection.
    assert not offenders(tmp_path)

    target.write_text(target.read_text(encoding="utf-8") + injected, "utf-8")

    found = offenders(tmp_path)
    assert found, (
        f"the guard admitted {injected.strip()!r} — it is not reading the"
        " import graph it claims to read"
    )
    assert target.relative_to(tmp_path).as_posix() in found, found


def test_the_guard_ignores_the_denied_names_in_prose(
    tmp_path: pathlib.Path,
) -> None:
    """A comment or a docstring naming a denied package is not an import.

    This is why the scan is an AST walk: a grep-shaped gate would fail on the
    deny list in this module's own header, and a gate that cries wolf gets
    switched off.
    """
    target = _copied_section_one(tmp_path)
    prose = '\n# Mentions ccf.agents, ccf.skills and ccf_runtime.adapters.\n'
    target.write_text(target.read_text(encoding="utf-8") + prose, "utf-8")

    assert not offenders(tmp_path)
