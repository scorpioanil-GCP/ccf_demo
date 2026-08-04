"""Every Phase D diagram is published by exactly one Concepts page.

This is a test rather than a manual check because the strict build only catches
ONE of the two failure directions. A Concepts page that includes a diagram
which does not exist fails the build immediately: `pymdownx.snippets` runs with
`check_paths: true`, so the missing file is an error rather than a silently
empty block. Nothing anywhere catches the opposite direction — a `.mmd` that
exists, is version-controlled, was reviewed at the Phase D gate, and is
referenced by nobody. That diagram simply stops being published, the site still
builds green, and the loss is invisible until someone goes looking for a figure
that used to be there.

The duplicate direction matters for a different reason. A diagram embedded on
two pages has two places to drift out of context, and the reader gets no signal
about which page is the canonical home of that figure. One diagram, one home.

The assertion is therefore a bijection: `public/diagrams/*.mmd` maps
one-to-one onto snippet-include directives under `public/concepts/`. Both
sides of the failure are reported by name, because "coverage failed" without
the names is a message that sends the reader back to a shell.

Paths resolve from this file's location, never from the process CWD, so the
module behaves identically under `pytest tools/docs_tests` at the repo root and
under a direct invocation from anywhere else.
"""

from __future__ import annotations

import collections
import pathlib
import re

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

#: The Phase D diagram sources — the artifacts whose publication is at stake.
DIAGRAM_DIR = REPO_ROOT / "public" / "diagrams"

#: The tree that is expected to embed them.
CONCEPTS_DIR = REPO_ROOT / "public" / "concepts"

#: A `pymdownx.snippets` include naming a diagram, e.g.
#: `--8<-- "public/diagrams/pillar-hitl.mmd"`. The capture is the bare
#: filename, which is what both sides of the bijection are keyed on.
INCLUDE_RE = re.compile(r'-{2,}8<-{2,}\s*"[^"]*?/diagrams/([A-Za-z0-9_.-]+\.mmd)"')


def diagram_names() -> set[str]:
    """Every `.mmd` filename under `public/diagrams/`."""
    return {path.name for path in DIAGRAM_DIR.glob("*.mmd")}


def embeds_by_diagram() -> dict[str, list[str]]:
    """Map each embedded diagram filename to the Concepts pages embedding it.

    A page embedding the same diagram twice is counted twice, deliberately: two
    renders of one figure on one page is the same drift hazard as two pages.
    """
    found: dict[str, list[str]] = collections.defaultdict(list)
    for page in sorted(CONCEPTS_DIR.rglob("*.md")):
        relative = page.relative_to(REPO_ROOT).as_posix()
        for name in INCLUDE_RE.findall(page.read_text(encoding="utf-8")):
            found[name].append(relative)
    return dict(found)


# --------------------------------------------------------------------------
# Preconditions — a vacuous pass is the failure this module exists to prevent.
# --------------------------------------------------------------------------


def test_fixture_trees_are_populated() -> None:
    """Both sides of the bijection are non-empty.

    Without this, a renamed `public/diagrams/` would make every assertion below
    pass over empty sets.
    """
    assert DIAGRAM_DIR.is_dir(), f"missing diagram tree: {DIAGRAM_DIR}"
    assert CONCEPTS_DIR.is_dir(), f"missing concepts tree: {CONCEPTS_DIR}"
    assert diagram_names(), f"no .mmd sources under {DIAGRAM_DIR}"
    assert embeds_by_diagram(), f"no diagram includes found under {CONCEPTS_DIR}"


# --------------------------------------------------------------------------
# The bijection.
# --------------------------------------------------------------------------


def test_no_diagram_is_orphaned() -> None:
    """Every diagram is embedded by at least one Concepts page."""
    orphans = sorted(diagram_names() - set(embeds_by_diagram()))
    assert not orphans, (
        "Phase D diagrams exist but are published by no Concepts page — they "
        "have silently stopped being part of the documentation: "
        + ", ".join(orphans)
    )


def test_no_diagram_is_embedded_twice() -> None:
    """No diagram is embedded more than once across the Concepts tree."""
    duplicated = {
        name: pages for name, pages in embeds_by_diagram().items() if len(pages) > 1
    }
    assert not duplicated, "diagrams embedded more than once: " + "; ".join(
        f"{name} on {', '.join(pages)}" for name, pages in sorted(duplicated.items())
    )


def test_every_embed_names_an_existing_diagram() -> None:
    """No Concepts page references a diagram that is not in the tree.

    The strict build already catches this, and that is the point: the two gates
    should agree. If this assertion ever fires while `make docs` is green, the
    snippet path check has regressed.
    """
    dangling = sorted(set(embeds_by_diagram()) - diagram_names())
    assert not dangling, (
        "Concepts pages reference diagrams that do not exist: " + ", ".join(dangling)
    )
