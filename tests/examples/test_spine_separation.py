"""Criterion 6's structural half — the spine and the deployment stay apart.

Phase 16 CONTEXT `D-11` answers a reader's complaint in the reader's own words:
*"I can't tell from looking at the code which code is example code and which
code is required by the CCF."* The answer is a split between the module that
carries the fabric's call spine and everything else the adopter writes, with
the seven Phase 14 `D-07` marker regions naming the spine's steps. The split
is discovered from content, not declared by a filename: the spine is
whichever module opens the seven canonical regions, a property a rename
cannot break. `D-11`'s complaint and the seven `D-07` names are unchanged by
that — this module changed how the spine is *found*, not what it *is*.

**TWO VALID SHAPES SINCE `D-IMPL-306`.** The seven regions describe an example
that composes the governed spine BY HAND. `D-IMPL-298` migrated cp-05 onto
`ccf.products.resolver::GovernedResolver`, and three of the seven — `gate`,
`record`, `serve` — are exactly what the resolver then owns. So this module
recognizes two architectures and refuses a third:

* **spine** — the seven `D-07` regions, in order. Unchanged, and still what
  most of the ladder is.
* **canonical** — `CANONICAL_PATH_MARKERS` (`boot`, `acquire`, `govern`), the
  governed seam handed to `ccf.products.resolver`, and NONE of `gate`,
  `record` or `serve` performed or published by the example itself.
* **half-migrated** — resolver ownership and hand-rolled governance side by
  side. **Refused, and named as half-migration rather than as a shape
  mismatch**, because the fault is not a missing marker: such a tree gives a
  reader two contradictory accounts of who decides and publishes snippets of a
  spine the SDK already owns.

**The shape is READ OFF THE TREE, never declared.** There is no list of
canonical examples in this module and none may be added. An example is
canonical because `shape_of` can prove from its AST that it delegates — which
means a newly migrated example arms these assertions by existing, exactly as
`SPINE_GLOBS` intends. `CANONICAL_SHAPE_FLOOR` is a regression floor and
authorizes nothing; see its own note.

**What this module proves, and what it cannot.** It proves the markers are
present, canonical, ordered, closed, and confined to one module. It does not
prove a reader can *see* which code is CCF's and which is theirs — that is a
human read, it is the plan's blocking checkpoint, and no assertion substitutes
for it. Stating the boundary here keeps the structural check from being mistaken
for the whole of criterion 6.

**Scope: ``examples/s1-*`` AND ``examples/cp-*``, by glob** (`SPINE_GLOBS`).
Section 1 is where the fabric is shown without an agent in front of it, and the
split is Section 1's shape — every Section-1 example carries it, so plan
16-08's second example arms these assertions by existing rather than by being
listed.

**Why ``cp-*`` joined the scan** (`24-CONTEXT.md` `D-21`/`D-23`, criterion 15).
The split this module enforces is not really a Section-1 property; it is a
property of any example whose code is PUBLISHED. The site's ``--8<--``
includes address the seven canonical regions by name, so a tree that publishes
snippets must carry the same shape or the page has nothing to include — and a
region that straddles two modules, or a ``print`` inside one, is snippet
surface an adopter would never write, whichever section the tree belongs to.
Context Product examples publish, so they are in.

**Section 2 and 3 examples do not exist and never will** (`24-CONTEXT.md`
`D-20`: the `sN-` scheme is not revived). ``archive/examples/00-quickstart/run.py``
carries the same seven marker names in a single module, which is the pre-`D-11`
shape this one replaces. It was never inside the globs these checks scan, so it
is not a carve-out from a rule this module enforces — the checks below simply
never see it.

**What ``cp-*`` does NOT inherit.** There are two ``s1-*`` globs in this suite
and they enforce different things.
``tests/examples/test_section_one_is_agent_free.py`` is the other one, and it
is **deliberately not widened** — a Context Product tree implements
``ccf.agents.assembler::ContextAssemblerProtocol``, which that gate's deny list
bans. The reason is written into that file (`D-24`) so a reader arriving here
and widening for consistency finds it before doing so.

**`D-11` adds no marker vocabulary.** The seven names below are Phase 14's, and
the closure check is as load-bearing as the ordering one: a suite that grows an
eighth marker per example has gone back to an editorial answer.

**P5/P6 — the printing properties.** Which modules print and which stay
silent is a separate contract from P1–P4, scoped to fabric-facing modules
only (see `CCF_IMPORT_RE`): exactly one fabric-facing module prints, the
module carrying the canonical regions is not it, and the scope exclusion is
itself controlled so it cannot silently swallow the whole check.
"""

from __future__ import annotations

import ast
import pathlib
import re
import shutil

import pytest
import yaml

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

#: The tree the scan walks. An argument everywhere below, so the negative
#: controls can repoint it at a copy and exercise the real predicates.
EXAMPLES_ROOT = REPO_ROOT / "examples"

#: The trees this gate scans, by directory-name convention, as globs rather
#: than a list — so a second Section-1 or Context Product example arms these
#: assertions by existing rather than by being added here.
#:
#: **Renamed from `SECTION_ONE_GLOB` when `cp-*` joined it** (`24-CONTEXT.md`
#: `D-21`/`D-23`, criterion 15). The gate no longer scans Section 1, and a
#: constant whose name says otherwise is the next reader's wrong premise —
#: which is the same failure mode `D-24` guards against in
#: `tests/examples/test_section_one_is_agent_free.py`.
SPINE_GLOBS: tuple[str, ...] = ("s1-*", "cp-*")

#: The Context Product tree criterion 15's control selects. **By NAME, never by
#: index.** `split_examples(...)[0]` is a moving target — widening the glob
#: changed which tree it resolves to — and a control written against `[0]` can
#: silently drift onto a tree it was not written for while staying green, which
#: leaves the criterion unproven and looking proven.
CONTEXT_PRODUCT_EXAMPLE = "cp-00-institutional-holders"

#: The tree that ships a printing module importing no `ccf`
#: (`scenario/provision.py`). The fabric-facing scope control needs THAT file
#: and no other, so it too selects by name — the same reason.
PROVISIONING_EXAMPLE = "s1-00-companies-over-revenue"

#: How a module writes to the terminal, in the two forms this repository uses.
PRINT_RE = re.compile(r"print\(|sys\.stdout\.write")

#: How a module declares itself part of the fabric. The taxonomy applies to
#: modules that make CCF calls, because this gate is about how fabric calls
#: separate from adopter code — a module making none is not party to that
#: separation. `examples/s1-00/scenario/provision.py` fabricates a Postgres
#: source system, imports no `ccf`, prints, and says `THIS IS NOT CCF` in its
#: own docstring; it is out of scope by that principle rather than by name.
#:
#: **This governs the PRINTING properties only.** The region properties scan
#: every module: a `--8<--` region in a module importing no `ccf` is still
#: published-snippet surface, and scoping it would make such a marker invisible.
CCF_IMPORT_RE = re.compile(r"^[ \t]*(?:from|import)[ \t]+ccf\b", re.MULTILINE)

#: The seven `D-07` names, in the order the fabric is called in. Ordered, so
#: this is a sequence rather than a set: a spine that gates before it projects
#: is not a spine a beginner can read.
CANONICAL_MARKERS: tuple[str, ...] = (
    "boot",
    "ingest",
    "operators",
    "project",
    "gate",
    "record",
    "serve",
)

#: The pymdownx.snippets marker form, as the published site reads it.
MARKER_RE = re.compile(r"--8<--\s*\[(?P<kind>start|end):(?P<name>[^\]]+)\]")


# ---------------------------------------------------------------------------
# Two valid shapes, and one refusal — `D-IMPL-306`.
# ---------------------------------------------------------------------------
#
# The seven regions above describe an example that COMPOSES the governed spine
# by hand. `D-IMPL-298` migrated cp-05 onto `ccf.products.resolver`, and three
# of those seven — `gate`, `record`, `serve` — are precisely what
# `GovernedResolver` then owns. cp-05 failed this gate for the reason it had
# succeeded at its own migration, which is a defect in the CONTRACT rather than
# in the tree: a check that encodes the legacy architecture as the only legal
# one refuses the architecture the SDK now ships.
#
# So the contract has two valid shapes and one named refusal:
#
#   spine          seven regions in order                            valid
#   canonical      canonical regions, resolver owns the seam,        valid
#                  and NO hand-rolled gate / record / serve
#   half-migrated  resolver ownership and legacy governance          REFUSED
#                  coexist
#
# **Canonical is a STRUCTURAL STATE, not membership in an allowlist.** There is
# no roster of canonical examples anywhere in this module and none may be added.
# An example is canonical because the tree PROVES it delegates the governed
# seam — it imports the resolver from `ccf.products.resolver`, calls it, and
# performs none of the three seams itself. A new canonical example arms these
# assertions by existing, exactly as `SPINE_GLOBS` intends. A permission list
# would make the gate answer "is this tree approved?" when the question is "does
# this tree delegate?", and those two come apart the first time somebody adds an
# example without editing a test.
#
# **Half-migrated is refused for its OWN reason, not as a failure to match.**
# An example that both delegates to the resolver and rebuilds governance beside
# it is the most dangerous of the three states: it reads as migrated, publishes
# snippets of a spine the SDK already owns, and gives a reader two contradictory
# accounts of who decides. Reporting that as "does not satisfy the canonical
# shape" would hide the actual fault behind a shape mismatch.

#: The canonical-path region names, in the order a resolver-adopting example
#: performs them. cp-05's own docstring states the same decomposition in prose:
#: *"boot, assemble the domain truth, hand the SDK its extension points, and
#: call it."*
#:
#: `boot` is shared with the seven, deliberately — booting a fabric from
#: declared artifacts is the same act in both shapes, and renaming it here would
#: assert a difference that does not exist.
CANONICAL_PATH_MARKERS: tuple[str, ...] = ("boot", "acquire", "govern")

#: The three of the seven that `GovernedResolver` owns. A canonical example
#: opening one of these is publishing a snippet of a spine it does not have.
LEGACY_GOVERNANCE_MARKERS: frozenset[str] = frozenset({"gate", "record", "serve"})

#: Performing a governed seam, by the FULLY QUALIFIED name the module imported
#: it under — never by bare name.
#:
#: Import-qualification is what makes this a measurement rather than a word
#: search, and the tree already contains the case that proves the difference:
#: `examples/cp-05-credit-exposure-rollup/server/serve.py` defines its own
#: `def serve()` (the MCP stdio entry point) and imports nothing from
#: `ccf.replay.serve`. A bare-name check would read that door as a hand-rolled
#: serve seam and classify the ladder's one canonical example as half-migrated.
GOVERNED_SEAM_CALLS: dict[str, str] = {
    "ccf.products.gates.run_gates": "gate",
    "ccf.replay.record.build_replay_record": "record",
    "ccf.replay.serve.serve": "serve",
}

#: Handing the governed seam to the SDK. Either name counts: `D-IMPL-301` ruled
#: that SDK-supplied ownership is an ARCHITECTURAL condition with more than one
#: wiring, so a deployment that constructs `GovernedResolver` directly is as
#: owned as one that calls the builder.
RESOLVER_OWNERSHIP_CALLS: frozenset[str] = frozenset(
    {
        "ccf.products.resolver.build_governed_resolver",
        "ccf.products.resolver.GovernedResolver",
    }
)

# ---------------------------------------------------------------------------
# A fourth shape, and a second named refusal — `D-IMPL-343` R-1.
# ---------------------------------------------------------------------------
#
# `D-IMPL-343` put ONE facade over the governed resolver: a paved tree hands
# its three verbs to `ccf.products.product.open_product` and never reaches
# `build_governed_resolver` itself — the facade does, on its behalf. Read by
# the vocabulary above, such a tree has NO resolver ownership and would be
# judged a hand-composed spine against the seven regions it does not perform.
# So the contract gains a fourth valid shape and a second refusal:
#
#   paved          paved entry present, no resolver ownership, and NO       valid
#                  hand-rolled gate / record / serve
#   double-spined  paved entry AND resolver ownership in one tree           REFUSED
#
# **Paved is a STRUCTURAL STATE, not membership in a roster** — the same
# discipline canonical is held to. And double-spined is refused for its OWN
# reason: a tree that both opens the product on the paved road and composes
# the resolver beside it gives a reader two accounts of who boots and who
# serves, and publishes snippets of a spine the facade already owns.

# A fifth shape, and it answers the gate's own question — `AIA-F-08`, ruled by
# Dave 2026-09-22.
#
# The gate asks DOES THIS TREE PRODUCE A CONTEXT PRODUCT, OR CONSUME ONE? Every
# shape above answers it one way: each is a producer, differing only in how it
# reaches the governed seam. A tree that produces nothing had no answer, and
# fell to the `"spine"` default — which then asked it for the seven regions of a
# producer spine it does not own.
#
#   consumer   declares no product class of its own AND reaches an        valid
#              existing paved entry belonging to ANOTHER product tree
#
# **Consumer is a STRUCTURAL STATE, not membership in a roster** — the same
# discipline canonical and paved are held to, and the reason the ruling of
# 2026-09-22 refused an allowlist: a permission list would make the gate answer
# "is this tree approved?", which is the question this module exists not to ask.
# Both limbs are read off the tree, and both are required: the first says the
# tree is not a producer, the second says it is a consumer rather than merely
# empty.

#: How a tree declares a Context Product class OF ITS OWN. The deployment
#: document is the Control Plane artifact that names the class, so a tree
#: carrying one is a producer whatever its code does.
DEPLOYMENT_CONFIG: str = "ccf_config.yaml"
PRODUCT_CLASS_KEY: str = "product_class"

#: A consumer owes NO producer regions. It publishes no spine because it has
#: none: the spine it consumes is the other tree's, already published there.
CONSUMER_MARKERS: tuple[str, ...] = ()

#: Handing the whole governed seam to the paved road's ONE entrypoint.
PAVED_ENTRY_CALLS: frozenset[str] = frozenset({"ccf.products.product.open_product"})

#: The paved-road region names, in order. `boot` is shared with the seven and
#: with the canonical three, deliberately — `region_modules` finds a carrier by
#: that shared name, and opening a product IS booting it: the one call binds the
#: deployment's verbs to its documents. `answer` is the one governed question.
PAVED_PATH_MARKERS: tuple[str, ...] = ("boot", "answer")

#: The number of paved examples in the tree when the shape was measured
#: (`D-IMPL-343` dogfood A, 2026-09-15: cp-03-canonical alone). A FLOOR, and
#: only a floor, on `CANONICAL_SHAPE_FLOOR`'s reasoning: never raised to paper
#: over a predicate that stopped recognizing a tree.
PAVED_SHAPE_FLOOR: int = 1

#: The number of canonical examples in the tree when the shape was measured
#: (`D-IMPL-306`, 2026-09-09: cp-05 alone).
#:
#: **A FLOOR, AND ONLY A FLOOR.** It exists to catch a silent regression — an
#: example quietly losing its resolver adoption while every other assertion
#: stays green, because a tree with no canonical examples satisfies every
#: canonical rule vacuously. It authorizes nothing: adding a canonical example
#: requires no edit here, and the gate never consults this number to decide
#: whether a particular tree may be canonical.
#:
#: **Never raise it to paper over an incomplete predicate.** If a tree that
#: plainly delegates is not being counted, the fault is in
#: `shape_of`, and moving this number would convert a detector bug into a
#: permanently green assertion.
CANONICAL_SHAPE_FLOOR: int = 1


# ---------------------------------------------------------------------------
# Reading the tree.
# ---------------------------------------------------------------------------


def is_pre_build(directory: pathlib.Path) -> bool:
    """Is this tree an authored specification with no implementation yet?

    `spec_generation.md` §2 makes a Context Product spec **step one of the
    example project**, authored at `examples/cp-NN-<slug>/spec/` and approved by
    Dave **before any implementation exists**. So a tree carrying a `spec/` and
    no Python at all is a legitimate, intended state — Gate 1 — and it has no
    spine because nothing has been built for a spine to live in.

    **The exclusion is deliberately narrow: `spec/` present AND zero `.py` files
    at any depth.** One module anywhere puts the tree back in scope. The
    dangerous direction here is a rule that skips whatever it cannot parse — a
    shipped example that lost its spine would then leave the scan silently, and
    this gate would report green over the defect it exists to catch. Requiring
    *total* absence of code is what keeps the exclusion unable to do that, and
    `test_the_pre_build_exclusion_releases_a_tree_that_has_any_code` is the
    control that proves it.
    """
    return (directory / "spec").is_dir() and not modules_in(directory)


def split_examples(root: pathlib.Path) -> list[pathlib.Path]:
    """Every example directory under `root` that this gate scans.

    The union of `SPINE_GLOBS`, de-duplicated: a tree matching two globs is one
    tree, and a directory appearing twice would run every parametrized check
    twice and report a copy of each failure.

    **Pre-build trees are excluded** — see `is_pre_build`. A Gate-1 spec is not
    an example that publishes snippets, and the seven canonical regions cannot
    be asserted against code nobody has written.
    """
    return sorted(
        {
            path
            for glob in SPINE_GLOBS
            for path in root.glob(glob)
            if path.is_dir() and not is_pre_build(path)
        }
    )


def modules_in(directory: pathlib.Path) -> list[pathlib.Path]:
    """Every Python module in one example directory, at any depth."""
    return sorted(directory.rglob("*.py"))


def fabric_facing(directory: pathlib.Path) -> list[pathlib.Path]:
    """Every module in the example that makes CCF calls."""
    return [
        module
        for module in modules_in(directory)
        if CCF_IMPORT_RE.search(module.read_text(encoding="utf-8"))
    ]


def region_modules(directory: pathlib.Path) -> list[pathlib.Path]:
    """Every module opening at least one of the seven canonical regions.

    Over ALL modules, not the fabric-facing ones — see `CCF_IMPORT_RE`.
    """
    return [
        module
        for module in modules_in(directory)
        if set(opened(module)) & set(CANONICAL_MARKERS)
    ]


def ccf_import_map(module: pathlib.Path) -> dict[str, str]:
    """Local name -> fully qualified `ccf` name, for every `from ccf... import`.

    The map is what turns a bare call into a measurement. `serve(...)` is either
    `ccf.replay.serve::serve` or a function the example defined itself, and only
    the import says which — see `GOVERNED_SEAM_CALLS` for the shipped case that
    proves the difference matters.

    A module that fails to parse contributes nothing rather than raising: this
    gate reads every `.py` under an example, and a deliberately broken fixture
    is not this module's failure to report.
    """
    try:
        tree = ast.parse(module.read_text(encoding="utf-8"))
    except SyntaxError:  # pragma: no cover - defensive; no shipped module hits it
        return {}
    names: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("ccf"):
            for alias in node.names:
                names[alias.asname or alias.name] = f"{node.module}.{alias.name}"
    return names


def _qualified_calls(module: pathlib.Path) -> list[tuple[str, int]]:
    """Every call in the module whose callee resolves to an imported `ccf` name.

    Calls only — never mentions. `refuse_over_tolerance` and `RefusalEnvelope`
    appear in cp-05's `produce.py` inside comments explaining what the SDK now
    does instead, and a check that read those would report the example as
    rebuilding the governance it had just finished deleting. Reading the AST
    makes prose structurally invisible.
    """
    try:
        tree = ast.parse(module.read_text(encoding="utf-8"))
    except SyntaxError:  # pragma: no cover - defensive
        return []
    imports = ccf_import_map(module)
    found: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        local = func.id if isinstance(func, ast.Name) else None
        if local is not None and local in imports:
            found.append((imports[local], node.lineno))
    return found


def governed_seam_calls(directory: pathlib.Path) -> dict[str, list[str]]:
    """Which of `gate` / `record` / `serve` the example performs ITSELF."""
    performed: dict[str, list[str]] = {}
    for module in modules_in(directory):
        for qualified, lineno in _qualified_calls(module):
            seam = GOVERNED_SEAM_CALLS.get(qualified)
            if seam is not None:
                performed.setdefault(seam, []).append(f"{module.name}:{lineno}")
    return {seam: sorted(sites) for seam, sites in sorted(performed.items())}


def resolver_ownership(directory: pathlib.Path) -> list[str]:
    """Where the example hands the governed seam to `ccf.products.resolver`."""
    sites = [
        f"{module.name}:{lineno}"
        for module in modules_in(directory)
        for qualified, lineno in _qualified_calls(module)
        if qualified in RESOLVER_OWNERSHIP_CALLS
    ]
    return sorted(sites)


def legacy_governance_regions(directory: pathlib.Path) -> list[str]:
    """Where the example still publishes a `gate`, `record` or `serve` region."""
    return sorted(
        f"{module.name}:{name}"
        for module in modules_in(directory)
        for name in opened(module)
        if name in LEGACY_GOVERNANCE_MARKERS
    )


def paved_entry(directory: pathlib.Path) -> list[str]:
    """Where the example opens its product on the paved road (`D-IMPL-343`)."""
    sites = [
        f"{module.name}:{lineno}"
        for module in modules_in(directory)
        for qualified, lineno in _qualified_calls(module)
        if qualified in PAVED_ENTRY_CALLS
    ]
    return sorted(sites)


def declares_product_class(directory: pathlib.Path) -> bool:
    """Does this tree declare a Context Product class of its OWN?

    Read from the deployment document rather than from code, because the class
    is a Control Plane artifact and that is where a producer names it. A tree
    with no `ccf_config.yaml`, or one that names no `product_class`, declares
    no class — which is the first limb of `consumer`.
    """
    document = directory / DEPLOYMENT_CONFIG
    if not document.is_file():
        return False
    try:
        declared = yaml.safe_load(document.read_text(encoding="utf-8"))
    except yaml.YAMLError:  # pragma: no cover - defensive
        return False
    return isinstance(declared, dict) and PRODUCT_CLASS_KEY in declared


def _attribute_calls(module: pathlib.Path) -> list[tuple[str, str, int]]:
    """`(name, attribute, lineno)` for every `name.attribute(...)` call.

    Deliberately separate from `_qualified_calls`, which resolves `ccf` imports
    only. A consumer reaches ANOTHER TREE's module, and that module is imported
    by bare name off `sys.path` rather than from a package.
    """
    try:
        tree = ast.parse(module.read_text(encoding="utf-8"))
    except SyntaxError:  # pragma: no cover - defensive
        return []
    found: list[tuple[str, str, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
            found.append((func.value.id, func.attr, node.lineno))
    return found


def paved_entry_symbols(directory: pathlib.Path) -> set[tuple[str, str]]:
    """`(module stem, function name)` for every paved entry this tree PUBLISHES.

    A paved entry is a function whose body calls `open_product`. `cp-21`'s
    `produce.py::product` is one, so this tree publishes `("produce",
    "product")` — the pair another tree's code would call to reach it.
    """
    published: set[tuple[str, str]] = set()
    for module in modules_in(directory):
        try:
            tree = ast.parse(module.read_text(encoding="utf-8"))
        except SyntaxError:  # pragma: no cover - defensive
            continue
        imports = ccf_import_map(module)
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            for inner in ast.walk(node):
                if not isinstance(inner, ast.Call):
                    continue
                callee = inner.func
                local = callee.id if isinstance(callee, ast.Name) else None
                if local is not None and imports.get(local) in PAVED_ENTRY_CALLS:
                    published.add((module.stem, node.name))
    return published


def foreign_paved_reach(directory: pathlib.Path) -> list[str]:
    """Where this tree reaches a paved entry belonging to ANOTHER product tree.

    Structural on both ends. The call site is read from this tree's AST; the
    target is read from the other trees' ASTs, so a reach counts only when the
    symbol it names really is a paved entry somewhere else. A tree calling its
    own `produce.product` matches nothing here — the module is its own.
    """
    own_modules = {module.stem for module in modules_in(directory)}
    foreign: dict[tuple[str, str], str] = {}
    for tree_root in split_examples(EXAMPLES_ROOT):
        if tree_root == directory:
            continue
        for symbol in paved_entry_symbols(tree_root):
            foreign.setdefault(symbol, tree_root.name)

    sites = [
        f"{module.name}:{lineno} -> {name}.{attribute} ({foreign[(name, attribute)]})"
        for module in modules_in(directory)
        for name, attribute, lineno in _attribute_calls(module)
        if name not in own_modules and (name, attribute) in foreign
    ]
    return sorted(sites)


def shape_of(directory: pathlib.Path) -> str:
    """`"paved"`, `"canonical"`, `"half-migrated"`, `"double-spined"` or `"spine"` — read off the tree.

    **Structural, never a roster.** The classifier asks three questions of the
    code: does anything here open the product on the paved road, does anything
    here hand the seam to `GovernedResolver` itself, and does anything here
    perform `gate`, `record` or `serve` itself? Nothing consults a list of
    approved directories, because the property being checked is delegation and
    a list would check approval instead.

    `"spine"` is the default rather than a detected state: an example with no
    paved entry and no resolver ownership is judged against the seven regions,
    which is what every example was judged against before `D-IMPL-306`.
    """
    paved = paved_entry(directory)
    owned = resolver_ownership(directory)
    if paved and owned:
        return "double-spined"
    if not paved and not owned:
        # BOTH LIMBS, AND BOTH REQUIRED (`AIA-F-08`, ruled 2026-09-22). The
        # first says this tree is not a producer; the second says it is a
        # consumer rather than merely empty. A tree with neither does not
        # become a consumer by accident — it is still judged against the seven.
        if not declares_product_class(directory) and foreign_paved_reach(directory):
            return "consumer"
        return "spine"
    if governed_seam_calls(directory) or legacy_governance_regions(directory):
        return "half-migrated"
    return "paved" if paved else "canonical"


def printing_modules(directory: pathlib.Path) -> list[pathlib.Path]:
    """Every fabric-facing module that writes to the terminal."""
    return [
        module
        for module in fabric_facing(directory)
        if PRINT_RE.search(module.read_text(encoding="utf-8"))
    ]


def print_problems(directory: pathlib.Path) -> list[str]:
    """P5 and P6 — which side of the split writes to a terminal.

    Always-on and substrate-free by construction: it reads files. Both
    directions are needed. Without P5, printing creeps back into the spine and
    the published snippets grow lines an adopter would never write; without
    P6's lower bound, this passes just as happily against the silent example
    the ruling of 2026-08-13 rejected.

    Scoped to fabric-facing modules, which is what keeps a per-example
    provisioning utility — printing, importing no `ccf`, and explicitly not CCF
    — from counting as a second driver.
    """
    problems: list[str] = []
    facing = fabric_facing(directory)
    if not facing:
        return [
            f"{directory.name}: no module imports `ccf`, so the printing"
            " properties would pass over an empty set"
        ]

    if shape_of(directory) == "consumer":
        return consumer_print_problems(directory, facing)

    carriers = region_modules(directory)
    if carriers and PRINT_RE.search(carriers[0].read_text(encoding="utf-8")):
        problems.append(
            f"{directory.name}/{carriers[0].name} carries the regions and"
            " prints. Presentation belongs in the module that drives the run;"
            " a printed line inside a published region is snippet surface an"
            " adopter would never write."
        )

    printers = printing_modules(directory)
    if not printers:
        problems.append(
            f"{directory.name} prints nothing — the example runs and shows a"
            " reader nothing (Dave's ruling, 2026-08-13)"
        )
    elif len(printers) > 1:
        problems.append(
            f"{directory.name}: more than one fabric-facing module prints"
            f" ({[module.name for module in printers]}). Exactly one drives"
            " the run."
        )
    return problems


def consumer_print_problems(
    directory: pathlib.Path, facing: list[pathlib.Path]
) -> list[str]:
    """P5 and P6 for a consumer — the same two intents, over the right modules.

    P5 says presentation does not belong in the CCF-facing code; for a
    consumer that is its fabric-facing module rather than a region carrier,
    since it carries no regions. P6 says the example shows a reader something,
    and for a consumer the module that does so is legitimately NOT
    fabric-facing — the client half of an agent pair imports no `ccf` at all,
    which is the property that half exists to demonstrate.
    """
    problems: list[str] = []
    noisy = sorted(
        module.name for module in facing
        if PRINT_RE.search(module.read_text(encoding="utf-8"))
    )
    if noisy:
        problems.append(
            f"{directory.name}: {noisy} reach the fabric AND print. A consumer's"
            " fabric-facing module assembles and extracts; presentation belongs"
            " in the module that drives the run."
        )
    if not any(
        PRINT_RE.search(module.read_text(encoding="utf-8"))
        for module in modules_in(directory)
    ):
        problems.append(
            f"{directory.name} prints nothing — the example runs and shows a"
            " reader nothing (Dave's ruling, 2026-08-13)"
        )
    return problems


def markers(path: pathlib.Path) -> list[tuple[str, str]]:
    """``(kind, name)`` for every marker in the file, in file order."""
    text = path.read_text(encoding="utf-8")
    return [
        (match.group("kind"), match.group("name").strip())
        for match in MARKER_RE.finditer(text)
    ]


def opened(path: pathlib.Path) -> tuple[str, ...]:
    """The names the file opens a region for, in the order it opens them."""
    return tuple(name for kind, name in markers(path) if kind == "start")


def unbalanced(path: pathlib.Path) -> list[str]:
    """Why the file's markers do not pair up, if they do not.

    Regions must open, close, and not interleave — a region left open by the
    end of the file, or closed without being opened, or opened while another is
    still open, publishes a snippet whose extent nobody authored.
    """
    problems: list[str] = []
    open_name: str | None = None
    for kind, name in markers(path):
        if kind == "start":
            if open_name is not None:
                problems.append(
                    f"[start:{name}] opens while [start:{open_name}] is still open"
                )
            open_name = name
        elif open_name is None:
            problems.append(f"[end:{name}] closes a region that was never opened")
        elif open_name != name:
            problems.append(f"[end:{name}] closes [start:{open_name}]")
            open_name = None
        else:
            open_name = None
    if open_name is not None:
        problems.append(f"[start:{open_name}] is never closed")
    return problems


def expected_markers(directory: pathlib.Path) -> tuple[str, ...]:
    """The region vocabulary this example's shape is judged against."""
    shape = shape_of(directory)
    if shape == "paved":
        return PAVED_PATH_MARKERS
    if shape == "canonical":
        return CANONICAL_PATH_MARKERS
    if shape == "consumer":
        return CONSUMER_MARKERS
    return CANONICAL_MARKERS


def region_report(
    spine: pathlib.Path, expected: tuple[str, ...] = CANONICAL_MARKERS
) -> tuple[tuple[str, ...], list[str], list[str]]:
    """What the spine opens, and how it differs from the names its shape owes.

    One derivation, two readers: `spine_problems` reports it as part of the
    aggregate, and the P2 test reports each direction separately. Written twice
    it drifted in wording before it shipped, which is the argument for a
    predicate rather than a repetition — the same argument `opened`,
    `unbalanced` and `spine_problems` already make in this module.

    `expected` defaults to the seven so every existing caller keeps its
    meaning; a canonical example passes `CANONICAL_PATH_MARKERS`.
    """
    found = opened(spine)
    return (
        found,
        [name for name in expected if name not in found],
        [name for name in found if name not in expected],
    )


def half_migrated_refusal(directory: pathlib.Path) -> list[str]:
    """The named refusal, reported for ITS OWN reason.

    A half-migrated example is not "a tree that failed to match the canonical
    shape" — it is a tree making two contradictory claims about who governs.
    Both halves are named, with line numbers, because the repair is to delete
    one of them and the reader has to be told which two are in conflict.
    """
    owned = resolver_ownership(directory) or paved_entry(directory)
    performed = governed_seam_calls(directory)
    regions = legacy_governance_regions(directory)
    detail = []
    if performed:
        detail.append(
            "performs "
            + ", ".join(f"{seam} at {sites}" for seam, sites in performed.items())
        )
    if regions:
        detail.append(f"publishes legacy governance regions {regions}")
    return [
        f"{directory.name}: HALF-MIGRATED. It hands the governed seam to"
        f" the SDK at {owned} and simultaneously "
        + "; and ".join(detail)
        + ". An example that both delegates and rebuilds governance gives a"
        " reader two accounts of who decides, and publishes snippets of a"
        " spine the SDK already owns. Delete the hand-rolled half, or the"
        " SDK adoption — not both, and not neither (`D-IMPL-306`)."
    ]


def double_spined_refusal(directory: pathlib.Path) -> list[str]:
    """The second named refusal (`D-IMPL-343` R-1), reported for ITS OWN reason.

    A double-spined example is not "a tree that failed to match the paved
    shape" — it is a tree that opens its product on the paved road AND
    composes the governed resolver beside it, so a reader gets two accounts of
    who boots and who serves. Both sites are named, because the repair is to
    delete one of them.
    """
    return [
        f"{directory.name}: DOUBLE-SPINED. It opens its product on the paved"
        f" road at {paved_entry(directory)} and simultaneously hands the"
        f" governed seam to `ccf.products.resolver` itself at"
        f" {resolver_ownership(directory)}. The facade already composes the"
        " resolver on the tree's behalf; a tree that does both publishes two"
        " spines. Delete the direct composition, or the paved entry — not"
        " both, and not neither (`D-IMPL-343`)."
    ]


def consumer_problems(directory: pathlib.Path) -> list[str]:
    """What a CONSUMER tree is held to — which is not nothing.

    A consumer owes no producer regions because it owns no producer spine, and
    that is the whole of the relief the shape grants. It is still refused for
    publishing a spine it does not have: a tree that opens `gate`, `record` or
    `serve` regions while producing nothing is offering an adopter snippets of
    steps it never performs, which is the same defect `half-migrated` is
    refused for, arriving from the other direction.
    """
    published = sorted(
        f"{module.name} opens {list(opened(module))}"
        for module in modules_in(directory)
        if opened(module)
    )
    if published:
        return [
            f"{directory.name}: CONSUMER, and it opens producer regions"
            f" ({'; '.join(published)}). A consumer declares no product class"
            " of its own and reaches another tree's paved entry; the spine it"
            " consumes is published THERE. Regions here would be snippets of"
            " steps this tree does not perform (`AIA-F-08`, ruled 2026-09-22)."
        ]
    return []


def spine_problems(directory: pathlib.Path) -> list[str]:
    """Every way one example directory fails the separation contract.

    A single predicate over a directory, so the shipped tree and the injected
    copies below are judged by the same code rather than by two descriptions of
    the same intent.

    **Three outcomes, one predicate** (`D-IMPL-306`). The shape is read off the
    tree by `shape_of` before any region is compared, because the region
    vocabulary an example owes depends on which architecture it implements.
    The properties, and which modules each scans:

    * P0 — the tree is not half-migrated (ALL modules, by AST)
    * P1/P4 — exactly one module opens canonical regions (ALL modules)
    * P2 — that module opens its shape's names, in order (that module)
    * P3 — every region it opens, it closes; none interleave (ALL modules)

    P5 and P6 are the printing properties and live in `print_problems`.
    """
    shape = shape_of(directory)
    if shape == "half-migrated":
        return half_migrated_refusal(directory)
    if shape == "double-spined":
        return double_spined_refusal(directory)
    if shape == "consumer":
        return consumer_problems(directory)

    expected = expected_markers(directory)
    problems: list[str] = []
    carriers = region_modules(directory)
    if not carriers:
        return [
            f"{directory.name}: no module opens any of the {shape} regions"
            f" {expected}. The split is the CCF call spine in one module and"
            " the adopter's own code in another (phase 16 CONTEXT D-11,"
            " criterion 6) — the spine is whichever module carries the"
            " regions, and this example has none."
        ]
    if len(carriers) > 1:
        problems.append(
            f"{directory.name}: more than one module opens canonical regions"
            f" ({[module.name for module in carriers]}). A canonical region"
            " belongs to exactly one module; a region spanning two publishes a"
            " snippet straddling the boundary this example exists to draw."
        )

    spine = carriers[0]
    found, missing, extra = region_report(spine, expected)
    if missing:
        problems.append(f"{spine.name} opens no region for {missing}")
    if extra:
        problems.append(
            f"{spine.name} opens {extra}, which is marker vocabulary outside"
            f" the {shape} names {expected} — D-11 adds none"
        )
    if not missing and not extra and found != expected:
        problems.append(
            f"{spine.name} opens the regions in order {found},"
            f" expected {expected}"
        )

    for module in modules_in(directory):
        problems.extend(f"{module.name}: {problem}" for problem in unbalanced(module))
    return problems


# ---------------------------------------------------------------------------
# Preconditions — a vacuous pass is the failure this module exists to prevent.
# ---------------------------------------------------------------------------


def test_the_section_one_tree_is_populated() -> None:
    """Without this, a renamed ``examples/s1-*`` makes every check below pass
    over an empty set of directories."""
    assert EXAMPLES_ROOT.is_dir(), f"missing examples tree: {EXAMPLES_ROOT}"
    assert split_examples(EXAMPLES_ROOT), (
        f"no Section-1 example directories under {EXAMPLES_ROOT} — the"
        " separation gate is scanning nothing"
    )
    for directory in split_examples(EXAMPLES_ROOT):
        assert modules_in(directory), f"{directory.name} contains no Python module"
        assert fabric_facing(directory), (
            f"{directory.name} has no module importing `ccf` — the printing"
            " properties would pass over an empty set"
        )


def test_the_marker_pattern_matches_the_shipped_form() -> None:
    """The regex is checked against a marker the suite actually ships.

    A pattern that matched nothing would make every assertion below vacuous,
    and the probe form is the one ``tools/docs_tests/test_snippet_gate.py``
    uses: look for the literal a source file contains.
    """
    spine = region_modules(split_examples(EXAMPLES_ROOT)[0])[0]
    assert f"[start:{CANONICAL_MARKERS[0]}]" in spine.read_text(encoding="utf-8")
    assert markers(spine), f"{spine} contains markers the pattern does not match"


# ---------------------------------------------------------------------------
# The separation.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "directory",
    split_examples(EXAMPLES_ROOT),
    ids=lambda path: path.name,
)
def test_exactly_one_module_carries_the_canonical_regions(
    directory: pathlib.Path,
) -> None:
    """P1 and P4, stated from both ends.

    The spine is whichever module carries the seven regions — a property a
    reader can check by opening the files, and one a rename cannot break. The
    previous form named `spine.py`, which made `D-IMPL-127`'s `produce.py` a
    failure while every property it claimed to prove held.
    """
    carriers = region_modules(directory)
    if shape_of(directory) == "consumer":
        # A consumer owns no producer spine, so it carries no regions — and
        # `consumer_problems` refuses it if it publishes any (`AIA-F-08`).
        assert not carriers, (
            f"{directory.name}: CONSUMER, yet {[m.name for m in carriers]} open"
            " producer regions"
        )
        return
    assert carriers, (
        f"{directory.name}: no module opens any canonical region"
    )
    assert len(carriers) == 1, (
        f"{directory.name}: {[module.name for module in carriers]} each open"
        " canonical regions; exactly one module must"
    )


@pytest.mark.parametrize(
    "directory",
    split_examples(EXAMPLES_ROOT),
    ids=lambda path: path.name,
)
def test_the_spine_opens_the_regions_its_shape_owes_in_order(
    directory: pathlib.Path,
) -> None:
    """P2 — both directions reported by name: what is missing and what is extra.

    Ordering is asserted as well as membership. The names are a decomposition a
    beginner is meant to be able to follow top to bottom, and a spine that
    records before it gates reads as a different story.

    **Which names are owed depends on the shape** (`D-IMPL-306`), and the shape
    is read off the tree rather than declared: a hand-composed example owes the
    seven, a resolver-adopting one owes `CANONICAL_PATH_MARKERS`. Judging a
    canonical example against the seven asks it to publish snippets of three
    steps it does not perform.
    """
    shape = shape_of(directory)
    expected = expected_markers(directory)
    if shape == "consumer":
        assert expected == (), "a consumer owes no producer regions"
        assert not region_modules(directory), (
            f"{directory.name}: CONSUMER, yet a module opens producer regions"
        )
        return
    spine = region_modules(directory)[0]
    found, missing, extra = region_report(spine, expected)
    assert not missing, (
        f"{directory.name}/{spine.name} ({shape}) opens no region for {missing}"
    )
    assert not extra, (
        f"{directory.name}/{spine.name} ({shape}) opens {extra}, which is"
        f" marker vocabulary outside the {shape} names {expected} — D-11 adds"
        " none"
    )
    assert found == expected, (
        f"{directory.name}/{spine.name} ({shape}) opens the regions in order"
        f" {found}, expected {expected}"
    )


@pytest.mark.parametrize(
    "directory",
    split_examples(EXAMPLES_ROOT),
    ids=lambda path: path.name,
)
def test_every_region_opened_anywhere_is_closed(directory: pathlib.Path) -> None:
    """P3 — opened, closed, and never interleaved, in every module."""
    for module in modules_in(directory):
        problems = unbalanced(module)
        assert not problems, f"{directory.name}/{module.name}: " + "; ".join(problems)


@pytest.mark.parametrize(
    "directory",
    split_examples(EXAMPLES_ROOT),
    ids=lambda path: path.name,
)
def test_the_shipped_example_satisfies_the_whole_contract(
    directory: pathlib.Path,
) -> None:
    """The aggregate predicate, over the shipped tree.

    Same code path the negative controls exercise, so a control that passed
    against a predicate this tree does not satisfy is impossible.
    """
    problems = spine_problems(directory)
    assert not problems, f"{directory.name}: " + "; ".join(problems)


@pytest.mark.parametrize(
    "directory",
    split_examples(EXAMPLES_ROOT),
    ids=lambda path: path.name,
)
def test_the_spine_is_silent_and_exactly_one_module_prints(
    directory: pathlib.Path,
) -> None:
    """P5 and P6, over the shipped tree, through the controls' own predicate."""
    problems = print_problems(directory)
    assert not problems, f"{directory.name}: " + "; ".join(problems)


def test_discovery_is_independent_of_the_working_directory(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every path is resolved from ``__file__``, never from the CWD.

    ``pytest`` is run from the repository root, from ``tests/``, and from a
    worktree by different people and by CI. A gate that only finds its tree
    from one of those is a gate that silently scans nothing from the others.
    """
    before = [path.name for path in split_examples(EXAMPLES_ROOT)]
    monkeypatch.chdir(tmp_path)
    after = [path.name for path in split_examples(EXAMPLES_ROOT)]
    assert before == after and before

    for directory in split_examples(EXAMPLES_ROOT):
        assert not spine_problems(directory), directory.name


# ---------------------------------------------------------------------------
# Negative controls — a structural check that has never refused anything is a
# structural check nobody has tested.
# ---------------------------------------------------------------------------


def _copied_named(tmp_path: pathlib.Path, name: str) -> pathlib.Path:
    """One shipped example, chosen BY NAME, copied under a fresh root.

    Copied rather than synthesized so the controls run against the real spine,
    the real markers and the real predicate. By name rather than by index for
    the controls that need a specific tree's contents — see
    `CONTEXT_PRODUCT_EXAMPLE` and `PROVISIONING_EXAMPLE`.
    """
    source = EXAMPLES_ROOT / name
    assert source.is_dir(), (
        f"{source} is gone — the control that selected it by name must be"
        " re-pointed rather than quietly falling back to whichever tree sorts"
        " first"
    )
    destination = tmp_path / source.name
    shutil.copytree(source, destination)
    assert not spine_problems(destination), "the unmodified copy must pass"
    return destination


def _copied_example(tmp_path: pathlib.Path) -> pathlib.Path:
    """The first shipped example in the scan, copied under a fresh root.

    For the controls whose subject is any conforming tree. The ones that need a
    PARTICULAR tree call `_copied_named` instead.
    """
    return _copied_named(tmp_path, split_examples(EXAMPLES_ROOT)[0].name)


def _canonical_subject(tmp_path: pathlib.Path) -> pathlib.Path:
    """A copy of a tree the PREDICATE calls canonical — never one named here.

    Selected by `shape_of` rather than by a constant, and that is the whole
    point: a control that named its canonical subject would be the roster
    `D-IMPL-306` forbids, wearing a different hat. Selecting by predicate also
    means these controls follow the tree — when a second example adopts the
    resolver, they keep working with no edit, and if the last one regresses
    they fail loudly instead of testing a shape nothing has.
    """
    canonical = [
        directory
        for directory in split_examples(EXAMPLES_ROOT)
        if shape_of(directory) == "canonical"
    ]
    assert canonical, (
        "no example in the tree is canonical, so every canonical assertion"
        " below would pass over an empty set. Either the predicate stopped"
        " recognizing resolver adoption or the last canonical example"
        " regressed — both are failures, and neither is fixed here."
    )
    return _copied_named(tmp_path, canonical[0].name)


def _spine_subject(tmp_path: pathlib.Path) -> pathlib.Path:
    """A copy of a tree the predicate calls hand-composed. Same discipline."""
    spines = [
        directory
        for directory in split_examples(EXAMPLES_ROOT)
        if shape_of(directory) == "spine"
    ]
    assert spines, "no hand-composed example remains to exercise the seven"
    return _copied_named(tmp_path, spines[0].name)


def test_the_canonical_population_has_not_silently_dropped() -> None:
    """A measured FLOOR, and never authorization (`D-IMPL-306`).

    A tree with no canonical examples satisfies every canonical rule vacuously,
    so the regression this catches is an example quietly losing its resolver
    adoption while the rest of the suite stays green.

    Read what it does NOT do. It does not decide which trees may be canonical —
    `shape_of` does that, from the code. It does not need editing when an
    example is migrated; the count rises on its own. And it must never be
    raised to make a green suite out of a predicate that stopped recognizing a
    tree, because that converts a detector bug into a permanent pass.
    """
    canonical = [
        directory.name
        for directory in split_examples(EXAMPLES_ROOT)
        if shape_of(directory) == "canonical"
    ]
    assert len(canonical) >= CANONICAL_SHAPE_FLOOR, (
        f"{len(canonical)} canonical examples ({canonical}) against a measured"
        f" floor of {CANONICAL_SHAPE_FLOOR}. An example that delegated the"
        " governed seam has stopped doing so, or `shape_of` has stopped"
        " seeing it. Do not raise the floor."
    )


def test_the_gate_refuses_a_spine_missing_one_required_region(
    tmp_path: pathlib.Path,
) -> None:
    """Sabotage 1 — delete one of the seven and the shape must go red BY NAME.

    The region deleted is `record`, chosen because it is one of the three a
    canonical example legitimately lacks: if the shape classifier ever leaked,
    and judged a hand-composed tree by the canonical vocabulary, this control
    would be the one that stopped refusing.
    """
    copied = _spine_subject(tmp_path)
    spine = region_modules(copied)[0]
    text = spine.read_text(encoding="utf-8")
    stripped = "\n".join(
        line for line in text.splitlines() if "[start:record]" not in line
        and "[end:record]" not in line
    )
    assert stripped != text, "the subject never opened a `record` region"
    spine.write_text(stripped + "\n", encoding="utf-8")

    problems = spine_problems(copied)
    assert problems, "a spine missing a required region must be refused"
    assert any("record" in problem for problem in problems), problems


def test_the_gate_refuses_a_canonical_example_that_rebuilds_a_governed_seam(
    tmp_path: pathlib.Path,
) -> None:
    """Sabotage 2a — a hand-rolled `gate` CALL beside resolver adoption.

    The refusal must name half-migration for its own reason. A tree that both
    delegates and rebuilds is not "a canonical example with a problem"; it is
    an example making two contradictory claims about who governs, and a reader
    told only that it "does not match the canonical shape" would go looking for
    a missing marker.
    """
    copied = _canonical_subject(tmp_path)
    assert shape_of(copied) == "canonical", "the unmodified copy must be canonical"

    spine = region_modules(copied)[0]
    spine.write_text(
        spine.read_text(encoding="utf-8")
        + "\n\nfrom ccf.products.gates import run_gates\n\n\n"
        "def _hand_rolled_gate(product, declared):\n"
        "    return run_gates(product=product, declared=declared)\n",
        encoding="utf-8",
    )

    assert shape_of(copied) == "half-migrated", governed_seam_calls(copied)
    problems = spine_problems(copied)
    assert problems, "a half-migrated example must be refused"
    assert "HALF-MIGRATED" in problems[0], problems
    assert "gate" in problems[0], problems


def test_the_gate_refuses_a_canonical_example_publishing_a_legacy_region(
    tmp_path: pathlib.Path,
) -> None:
    """Sabotage 2b — the REGION half of the same refusal.

    Calls and regions are independently sufficient, because they fail
    independently: a tree can publish a `serve` snippet of code the resolver
    now runs without calling anything, and the published page is then teaching
    a spine the example does not have.
    """
    copied = _canonical_subject(tmp_path)
    spine = region_modules(copied)[0]
    spine.write_text(
        spine.read_text(encoding="utf-8")
        + "\n\n# --8<-- [start:serve]\n_SERVED = None\n# --8<-- [end:serve]\n",
        encoding="utf-8",
    )

    assert shape_of(copied) == "half-migrated", legacy_governance_regions(copied)
    problems = spine_problems(copied)
    assert "HALF-MIGRATED" in problems[0], problems
    assert "serve" in problems[0], problems


def test_the_gate_refuses_a_canonical_example_that_loses_resolver_ownership(
    tmp_path: pathlib.Path,
) -> None:
    """Sabotage 3 — take the delegation away and the tree must not stay valid.

    This is the direction the floor cannot cover on its own. Removing the
    resolver call leaves an example that still opens `boot`/`acquire`/`govern`
    and performs no governance at all — neither shape — and the contract has to
    refuse it rather than fall back to whichever vocabulary it happens to match.
    """
    copied = _canonical_subject(tmp_path)
    ownership = resolver_ownership(copied)
    assert ownership, "the unmodified copy must own the seam"

    for module in modules_in(copied):
        text = module.read_text(encoding="utf-8")
        if "build_governed_resolver" in text:
            module.write_text(
                text.replace("build_governed_resolver", "_no_resolver_here"),
                encoding="utf-8",
            )

    assert not resolver_ownership(copied), "the sabotage did not remove ownership"
    assert shape_of(copied) != "canonical"
    problems = spine_problems(copied)
    assert problems, (
        "an example that publishes canonical regions while delegating nothing"
        " must be refused, not silently re-judged"
    )


def test_the_gate_refuses_an_example_with_no_region_carrying_module(
    tmp_path: pathlib.Path,
) -> None:
    """Zero carriers is a refusal, not a vacuous pass.

    This is the direction the deleted rename control used to cover. Renaming a
    module is now legal by design, so the property that replaces it is that
    SOME module carries the seven regions — which a rename cannot break and a
    deletion can.
    """
    example = _copied_example(tmp_path)
    spine = region_modules(example)[0]
    text = spine.read_text(encoding="utf-8")
    for name in CANONICAL_MARKERS:
        text = text.replace(f"[start:{name}]", "").replace(f"[end:{name}]", "")
    spine.write_text(text, "utf-8")

    problems = spine_problems(example)
    assert any("no module opens" in problem for problem in problems), problems


def test_the_gate_refuses_a_second_module_carrying_canonical_regions(
    tmp_path: pathlib.Path,
) -> None:
    """A canonical region belongs to exactly one module, whatever it is called.

    Injected into a module that is NOT fabric-facing, because the region
    properties scan every module: a marker in a module importing no `ccf` still
    publishes a snippet, and scoping the region check would make it invisible.
    """
    example = _copied_example(tmp_path)
    carrier = region_modules(example)[0]
    outsiders = [
        module for module in modules_in(example) if module not in fabric_facing(example)
    ]
    # A non-fabric-facing module when the example has one, because that is the
    # case the scope rule could hide; any sibling otherwise.
    sibling = outsiders[0] if outsiders else next(
        module for module in modules_in(example) if module != carrier
    )
    name = CANONICAL_MARKERS[-1]
    sibling.write_text(
        sibling.read_text(encoding="utf-8")
        + f"\n# --8<-- [start:{name}]\n# --8<-- [end:{name}]\n",
        "utf-8",
    )

    problems = spine_problems(example)
    assert any("more than one module" in problem for problem in problems), problems


def test_the_gate_refuses_a_spine_whose_regions_are_out_of_order(
    tmp_path: pathlib.Path,
) -> None:
    """Membership alone is not the contract; the reading order is."""
    example = _copied_example(tmp_path)
    spine = region_modules(example)[0]
    text = spine.read_text(encoding="utf-8")
    first, last = CANONICAL_MARKERS[0], CANONICAL_MARKERS[-1]
    swapped = (
        text.replace(f"[start:{first}]", "[start:__SWAP__]")
        .replace(f"[start:{last}]", f"[start:{first}]")
        .replace("[start:__SWAP__]", f"[start:{last}]")
        .replace(f"[end:{first}]", "[end:__SWAP__]")
        .replace(f"[end:{last}]", f"[end:{first}]")
        .replace("[end:__SWAP__]", f"[end:{last}]")
    )
    spine.write_text(swapped, "utf-8")

    assert spine_problems(example)


def test_the_gate_refuses_an_unclosed_region(tmp_path: pathlib.Path) -> None:
    """A region left open publishes a snippet whose extent nobody authored.

    The LAST region's close is the one removed. Removing an earlier one is also
    refused, but as an interleaving — the next ``start`` arrives while the
    previous region is still open — and this control is aimed at the case with
    nothing after it to notice.
    """
    example = _copied_example(tmp_path)
    spine = region_modules(example)[0]
    text = spine.read_text(encoding="utf-8")
    spine.write_text(text.replace(f"[end:{CANONICAL_MARKERS[-1]}]", "", 1), "utf-8")

    assert any("never closed" in problem for problem in spine_problems(example)), (
        spine_problems(example)
    )


def test_the_gate_refuses_marker_vocabulary_outside_the_seven(
    tmp_path: pathlib.Path,
) -> None:
    """`D-11` adds no marker names, and an eighth is how that erodes."""
    example = _copied_example(tmp_path)
    spine = region_modules(example)[0]
    text = spine.read_text(encoding="utf-8")
    spine.write_text(
        text + "\n# --8<-- [start:extra]\n# --8<-- [end:extra]\n", "utf-8"
    )

    assert spine_problems(example)


def test_the_gate_refuses_a_region_carrying_module_that_prints(
    tmp_path: pathlib.Path,
) -> None:
    """P5 — this is what `D-11` is actually about.

    The published snippets are the spine's regions. A print inside them is a
    line an adopter would never write, inflating the example's apparent
    integration cost — the Phase 14.1 finding, restated as a property of
    whichever module carries the regions rather than of a module named
    `spine.py`.
    """
    example = _copied_example(tmp_path)
    spine = region_modules(example)[0]
    spine.write_text(
        spine.read_text(encoding="utf-8") + '\nprint("noise")\n', "utf-8"
    )

    problems = print_problems(example)
    assert any("carries the regions and prints" in p for p in problems), problems


def test_the_gate_refuses_an_example_that_prints_nothing(
    tmp_path: pathlib.Path,
) -> None:
    """P6, zero direction — the shape Dave's ruling of 2026-08-13 rejected.

    Without this the printing check passes just as happily against a silent
    example: one that runs and shows a reader nothing.
    """
    example = _copied_example(tmp_path)
    for module in printing_modules(example):
        module.write_text(
            PRINT_RE.sub("_muted(", module.read_text(encoding="utf-8")), "utf-8"
        )

    problems = print_problems(example)
    assert any("prints nothing" in problem for problem in problems), problems


def test_the_gate_refuses_two_fabric_facing_printers(
    tmp_path: pathlib.Path,
) -> None:
    """P6, two direction — printing must not creep back across the split."""
    example = _copied_example(tmp_path)
    silent = next(
        module
        for module in fabric_facing(example)
        if not PRINT_RE.search(module.read_text(encoding="utf-8"))
    )
    silent.write_text(
        silent.read_text(encoding="utf-8") + '\nprint("noise")\n', "utf-8"
    )

    problems = print_problems(example)
    assert any("more than one" in problem for problem in problems), problems


def test_the_fabric_facing_scope_admits_and_excludes_on_the_import(
    tmp_path: pathlib.Path,
) -> None:
    """The control for the one new convention, both halves.

    HW-1's `scenario/provision.py` prints and imports no `ccf`. If the scope
    predicate did not exclude it, P6 would be false for a correct example; if
    the predicate excluded everything, P5 and P6 would pass over an empty set.
    One test asserts both directions against the same file.
    """
    # BY NAME. This control's whole subject is one specific file, and after
    # the glob widened, `split_examples(...)[0]` is a `cp-` tree that does not
    # ship it. Selecting by index here would have turned a correct control into
    # a failure about the wrong tree.
    example = _copied_named(tmp_path, PROVISIONING_EXAMPLE)
    outsider = example / "scenario" / "provision.py"
    # Asserted, not skipped. A skip here would silently disable the only
    # control of the one convention this rewrite introduces, on the day
    # somebody moved the file.
    assert outsider.is_file(), (
        f"{example.name} no longer ships scenario/provision.py — repoint this"
        " control at whichever module prints and imports no `ccf`"
    )

    # (a) it prints, imports no `ccf`, and the example is still compliant.
    assert PRINT_RE.search(outsider.read_text(encoding="utf-8"))
    assert not CCF_IMPORT_RE.search(outsider.read_text(encoding="utf-8"))
    assert not print_problems(example), print_problems(example)

    # (b) the same file, now importing `ccf`, is a second printer and refused.
    outsider.write_text(
        "import ccf.deployment\n" + outsider.read_text(encoding="utf-8"), "utf-8"
    )
    problems = print_problems(example)
    assert any("more than one" in problem for problem in problems), problems


# ---------------------------------------------------------------------------
# Criterion 15 — the widened glob, proven to SCAN rather than merely to have
# been widened.
# ---------------------------------------------------------------------------


def test_the_widened_glob_actually_scans_the_context_product_tree(
    tmp_path: pathlib.Path,
) -> None:
    """Widening a string and re-running a green suite proves nothing.

    That is the whole point of criterion 15. A glob that matched nothing would
    pass every assertion in this module forever, and "the suite is still green
    after the widening" is exactly what it would look like. So this control
    asserts the widened scan REACHES the Context Product tree and then watches
    the real predicate REFUSE a broken copy of THAT tree, discovered through
    the real glob rather than handed to the predicate by hand.

    Both directions of the union are asserted. Dropping `cp-*` leaves the first
    half red; dropping `s1-*` leaves the second half red — so neither glob can
    be removed on the grounds that the suite still passes.

    The copy subject is `CONTEXT_PRODUCT_EXAMPLE`, selected by NAME. Written
    against `split_examples(...)[0]` it could silently drift back onto an `s1-`
    tree and leave the criterion unproven while this test stayed green.
    """
    scanned = [path.name for path in split_examples(EXAMPLES_ROOT)]

    assert CONTEXT_PRODUCT_EXAMPLE in scanned, (
        f"{SPINE_GLOBS} does not reach {CONTEXT_PRODUCT_EXAMPLE}; the scan"
        f" covers {scanned}. The published page's `--8<--` includes depend on"
        " the canonical regions, so a Context Product tree that publishes"
        " snippets must be inside this gate (24-CONTEXT.md D-21/D-23)."
    )
    assert any(name.startswith("s1-") for name in scanned), (
        f"the widening dropped Section 1; the scan covers {scanned}"
    )

    # A copy of THAT tree, stripped of its canonical markers.
    example = _copied_named(tmp_path, CONTEXT_PRODUCT_EXAMPLE)
    spine = region_modules(example)[0]
    text = spine.read_text(encoding="utf-8")
    for name in CANONICAL_MARKERS:
        text = text.replace(f"[start:{name}]", "").replace(f"[end:{name}]", "")
    spine.write_text(text, "utf-8")

    # Rediscovered through the real glob, so the chain under test is
    # glob -> discovery -> predicate, not predicate alone.
    discovered = split_examples(tmp_path)
    assert [path.name for path in discovered] == [CONTEXT_PRODUCT_EXAMPLE], (
        f"the glob did not rediscover the mutated copy: {discovered}"
    )

    problems = spine_problems(discovered[0])
    assert any("no module opens" in problem for problem in problems), problems


def test_the_pre_build_exclusion_releases_a_tree_that_has_any_code(
    tmp_path: pathlib.Path,
) -> None:
    """The narrow half of `is_pre_build`, and the half that can go wrong.

    An exclusion that skipped whatever it could not parse would let a shipped
    example that lost its spine leave the scan silently — this gate would then
    report green over exactly the defect it exists to catch. So the control
    takes a real, conforming tree, gives it a `spec/` directory, and asserts it
    is **still scanned**: carrying a spec is not what releases a tree, carrying
    no code at all is.
    """
    example = _copied_example(tmp_path)
    (example / "spec").mkdir(exist_ok=True)
    (example / "spec" / "CP-SPEC-999_Control.md").write_text("# a spec\n", "utf-8")

    assert not is_pre_build(example), (
        f"{example.name} has {len(modules_in(example))} modules and was still"
        " classified pre-build — the exclusion is releasing trees that carry"
        " code, which is how a spineless shipped example would leave the scan"
    )
    assert [path.name for path in split_examples(tmp_path)] == [example.name], (
        "a tree with code and a spec must stay in the scan"
    )


def test_the_pre_build_exclusion_releases_a_spec_only_tree(
    tmp_path: pathlib.Path,
) -> None:
    """The Gate-1 case: an authored spec, approved, with nothing built yet.

    `spec_generation.md` §2 requires exactly this state to exist — the spec is
    step one of the example project and Dave approves it *before* any
    implementation. `cp-02-facility-terms-snapshot` sat in it on 2026-08-29 and
    took five parametrized failures, because the gate read a directory with no
    code as an example whose spine had gone missing.
    """
    example = tmp_path / "cp-99-gate-one-only"
    (example / "spec").mkdir(parents=True)
    (example / "spec" / "CP-SPEC-999_Gate_One.md").write_text("# authored\n", "utf-8")

    assert is_pre_build(example)
    assert split_examples(tmp_path) == [], (
        "a spec-only tree must not be scanned for a spine it cannot have;"
        f" got {split_examples(tmp_path)}"
    )


# ---------------------------------------------------------------------------
# The paved shape — `D-IMPL-343` R-1: a witness, a floor, and two refusals.
# ---------------------------------------------------------------------------


def _paved_subject(tmp_path: pathlib.Path) -> pathlib.Path:
    """A copy of a tree the PREDICATE calls paved — never one named here.

    `_canonical_subject`'s discipline, applied to the fourth shape: selected
    by `shape_of`, so the controls below follow the tree and fail loudly if
    the last paved example regresses or the predicate stops seeing it.
    """
    paved = [
        directory
        for directory in split_examples(EXAMPLES_ROOT)
        if shape_of(directory) == "paved"
    ]
    assert paved, (
        "no example in the tree is paved, so every paved assertion below would"
        " pass over an empty set. Either the predicate stopped recognizing"
        " `open_product` or the last paved example regressed — both are"
        " failures, and neither is fixed here."
    )
    return _copied_named(tmp_path, paved[0].name)


def test_the_paved_population_has_not_silently_dropped() -> None:
    """A measured FLOOR on the fourth shape, and never authorization."""
    paved = [
        directory.name
        for directory in split_examples(EXAMPLES_ROOT)
        if shape_of(directory) == "paved"
    ]
    assert len(paved) >= PAVED_SHAPE_FLOOR, (
        f"{len(paved)} paved examples ({paved}) against a measured floor of"
        f" {PAVED_SHAPE_FLOOR}. An example that opened its product on the paved"
        " road has stopped doing so, or `shape_of` has stopped seeing it. Do"
        " not raise the floor."
    )


def test_a_paved_tree_is_read_as_paved_and_owes_the_paved_regions(
    tmp_path: pathlib.Path,
) -> None:
    """The positive control: the predicate has a witness before it refuses anything.

    The copy is paved, problem-free, opens exactly `PAVED_PATH_MARKERS` in
    order, hands the seam to nothing in `ccf.products.resolver` itself, and
    performs no governed seam of its own.
    """
    copied = _paved_subject(tmp_path)
    assert shape_of(copied) == "paved"
    assert paved_entry(copied) and not resolver_ownership(copied)
    assert expected_markers(copied) == PAVED_PATH_MARKERS
    assert spine_problems(copied) == []
    spine = region_modules(copied)[0]
    assert opened(spine) == PAVED_PATH_MARKERS


def test_a_paved_tree_that_also_composes_the_resolver_is_refused_double_spined(
    tmp_path: pathlib.Path,
) -> None:
    """Sabotage — add a direct `build_governed_resolver` call beside `open_product`.

    Refused BY NAME as double-spined, for its own reason, and not as a failure
    to match either shape.
    """
    copied = _paved_subject(tmp_path)
    spine = region_modules(copied)[0]
    spine.write_text(
        spine.read_text(encoding="utf-8")
        + "\nfrom ccf.products.resolver import build_governed_resolver\n"
        "\n\ndef _second_spine() -> None:\n    build_governed_resolver()\n",
        encoding="utf-8",
    )
    assert shape_of(copied) == "double-spined"
    problems = spine_problems(copied)
    assert len(problems) == 1 and "DOUBLE-SPINED" in problems[0], problems


def test_a_paved_tree_that_hand_rolls_a_governed_seam_is_refused_half_migrated(
    tmp_path: pathlib.Path,
) -> None:
    """Sabotage — a paved tree calling `run_gates` itself is half-migrated, by name."""
    copied = _paved_subject(tmp_path)
    spine = region_modules(copied)[0]
    spine.write_text(
        spine.read_text(encoding="utf-8")
        + "\nfrom ccf.products.gates import run_gates\n"
        "\n\ndef _hand_rolled() -> None:\n    run_gates()\n",
        encoding="utf-8",
    )
    assert shape_of(copied) == "half-migrated"
    problems = spine_problems(copied)
    assert len(problems) == 1 and "HALF-MIGRATED" in problems[0], problems


def test_a_paved_tree_missing_its_boot_region_is_refused_by_name(
    tmp_path: pathlib.Path,
) -> None:
    """Sabotage — drop the shared `boot` region and the carrier disappears.

    `boot` is the name `region_modules` finds a carrier by, deliberately
    shared with the seven and the canonical three; a paved spine that opens
    only `answer` publishes a region nothing reads, and P1 says so.
    """
    copied = _paved_subject(tmp_path)
    spine = region_modules(copied)[0]
    text = spine.read_text(encoding="utf-8")
    stripped = "\n".join(
        line for line in text.splitlines()
        if "[start:boot]" not in line and "[end:boot]" not in line
    )
    assert stripped != text, "the subject never opened a `boot` region"
    spine.write_text(stripped + "\n", encoding="utf-8")
    assert shape_of(copied) == "paved"
    problems = spine_problems(copied)
    assert problems and "no module opens any of the paved regions" in problems[0], problems


# ---------------------------------------------------------------------------
# The consumer shape — `AIA-F-08`, ruled by Dave 2026-09-22.
#
# Every control below is STRUCTURAL: each builds or perturbs a tree and asks
# the shipped predicate. None names an approved directory, because the ruling
# that created this shape refused an allowlist — the gate answers "does this
# tree produce a Context Product, or consume one?", never "is this tree
# approved?".
# ---------------------------------------------------------------------------


def _consumer_subject(tmp_path: pathlib.Path) -> pathlib.Path:
    """A copy of a tree the PREDICATE calls a consumer — never one named here.

    The same discipline `_paved_subject` and `_canonical_subject` are held to:
    selected by `shape_of`, so these controls follow the tree and fail loudly
    if the last consumer regresses or the predicate stops seeing it.
    """
    found = [
        directory for directory in split_examples(EXAMPLES_ROOT)
        if shape_of(directory) == "consumer"
    ]
    assert found, (
        "no shipped example classifies as `consumer`; the controls below would"
        " prove nothing about a shape nothing has"
    )
    subject = tmp_path / found[0].name
    shutil.copytree(found[0], subject)
    return subject


def test_a_consumer_tree_classifies_as_consumer_and_satisfies_the_contract() -> None:
    """CONTROL 1 — the shipped consumer, through the shipped predicates.

    The shape exists, a tree has it, and that tree passes the aggregate
    contract and the printing properties without owing producer regions.
    """
    subjects = [
        directory for directory in split_examples(EXAMPLES_ROOT)
        if shape_of(directory) == "consumer"
    ]
    assert subjects, "no shipped example classifies as `consumer`"
    for subject in subjects:
        assert not declares_product_class(subject), subject.name
        assert foreign_paved_reach(subject), subject.name
        assert expected_markers(subject) == ()
        assert not spine_problems(subject), subject.name
        assert not print_problems(subject), subject.name


def test_a_paved_producer_is_not_swept_into_the_consumer_shape() -> None:
    """CONTROL 2 — a producer calling its OWN `open_product` stays `paved`.

    The reach must be FOREIGN. A tree that calls its own `produce.product`
    matches nothing in `foreign_paved_reach`, because the module is its own —
    and that is what keeps every shipped producer out of this shape.
    """
    paved = [
        directory for directory in split_examples(EXAMPLES_ROOT)
        if shape_of(directory) == "paved"
    ]
    assert paved, "no shipped example is paved; control 2 would prove nothing"
    for directory in paved:
        assert shape_of(directory) != "consumer"
        assert foreign_paved_reach(directory) == [], (
            f"{directory.name} reaches a foreign paved entry: "
            f"{foreign_paved_reach(directory)}"
        )


def test_a_declared_product_class_removes_the_consumer_shape(
    tmp_path: pathlib.Path,
) -> None:
    """CONTROL 3 — Dave's sabotage, both limbs broken at once.

    Give the consumer a product-class declaration of its own AND remove its
    foreign paved-entry reach: it must not classify `consumer`. A tree that
    declares a class is a producer, whatever else it does.
    """
    subject = _consumer_subject(tmp_path)
    assert shape_of(subject) == "consumer", "the copy did not carry the shape"

    (subject / DEPLOYMENT_CONFIG).write_text(
        "semver: '1.0.0'\nproduct_class:\n  schema_name: fake.not-a-product\n", "utf-8")
    for module in modules_in(subject):
        text = module.read_text(encoding="utf-8")
        module.write_text(text.replace("produce.product(", "_severed.product("), "utf-8")

    assert shape_of(subject) != "consumer", (
        "a tree declaring its own product class and reaching no foreign paved"
        " entry still classified as a consumer"
    )


def test_each_limb_alone_is_not_enough_to_be_a_consumer(
    tmp_path: pathlib.Path,
) -> None:
    """THE `AND` IS REAL — each limb broken on its own.

    Control 3 breaks both at once, which cannot tell a conjunction from a
    disjunction. These two do it one at a time, so a predicate that had
    silently become `or` fails here.
    """
    only_class = _consumer_subject(tmp_path / "declared")
    (only_class / DEPLOYMENT_CONFIG).write_text(
        "semver: '1.0.0'\nproduct_class:\n  schema_name: fake.not-a-product\n", "utf-8")
    assert foreign_paved_reach(only_class), "the reach limb was disturbed too"
    assert shape_of(only_class) != "consumer", (
        "declaring a product class of its own did not remove the shape"
    )

    only_reach = _consumer_subject(tmp_path / "severed")
    for module in modules_in(only_reach):
        text = module.read_text(encoding="utf-8")
        module.write_text(text.replace("produce.product(", "_severed.product("), "utf-8")
    assert not declares_product_class(only_reach), "the class limb was disturbed too"
    assert shape_of(only_reach) != "consumer", (
        "severing the foreign paved reach did not remove the shape"
    )


def test_an_empty_tree_does_not_become_a_consumer_by_accident(
    tmp_path: pathlib.Path,
) -> None:
    """CONTROL 4 — neither limb, and it must NOT be a consumer.

    This is the failure mode the shape could most easily have introduced: a
    tree that declares no class is not thereby a consumer, or every incomplete
    example would be excused from the contract it is failing. Absence of a
    producer is not presence of a consumer.
    """
    example = tmp_path / "cp-98-neither"
    (example / "spec").mkdir(parents=True)
    (example / "spec" / "CP-SPEC-998_Neither.md").write_text("# authored\n", "utf-8")
    (example / "solo.py").write_text(
        "import ccf.products.product as _p\n\n\ndef go() -> None:\n    print(_p)\n", "utf-8")

    assert not declares_product_class(example)
    assert foreign_paved_reach(example) == []
    assert shape_of(example) != "consumer", (
        "a tree with no product class and no foreign paved reach became a"
        " consumer by accident; absence of a producer is not presence of a"
        " consumer"
    )
    assert shape_of(example) == "spine", shape_of(example)


def test_a_consumer_that_publishes_producer_regions_is_refused(
    tmp_path: pathlib.Path,
) -> None:
    """The relief the shape grants is bounded.

    A consumer owes no producer regions — it may not publish them either. A
    tree producing nothing while opening `gate` or `serve` offers an adopter
    snippets of steps it never performs.
    """
    subject = _consumer_subject(tmp_path)
    assert not spine_problems(subject), "the copy did not start clean"

    facing = fabric_facing(subject)[0]
    facing.write_text(
        "# --8<-- [start:gate]\n" + facing.read_text(encoding="utf-8")
        + "\n# --8<-- [end:gate]\n", "utf-8")

    problems = spine_problems(subject)
    assert problems and "CONSUMER" in problems[0], problems
