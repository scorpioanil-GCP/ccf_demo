"""The product-gate coverage checker `D-IMPL-224` ordered (ledger rows `24.5-L-10`, `24.5-L-18`).

`D-IMPL-224` (Dave, 2026-08-31) makes a Context Product example's gates a
DECLARED ARTIFACT plus a CI coverage check, and names five properties the
check must have. Each is a function or a rule in this module:

(1) **Gates are declared in an artifact, one place, closed keys.** Every
    ``examples/cp-*`` tree is expected to carry ``artifacts/gates.yaml``;
    :func:`check_tree` validates it against the closed schema
    ``docs/schemas/product-gates/cp.product-gates.json`` before any id is
    read, and a tree with no roster is a problem rather than a skip.
(2) **A declared id with no EXECUTING test is red, and a test naming an
    UNDECLARED id is red.** "Executing" is resolved against a REAL
    ``pytest --collect-only -q`` over ``tests/examples/``
    (:func:`collect_node_ids`) — never ``hasattr``, never a substring.
    "Names" is read by :func:`named_ids` over the AST of the product's own
    test modules, and ONLY in the form the roster declares (see below).
(3) **Non-vacuity.** A ``cp-*`` roster declaring zero ids is red, a missing
    roster is red, and a failed collection is "cannot be judged", never clean.
(4) **Scope is the ``cp-*`` ladder only.** :func:`product_trees` globs
    ``examples/cp-*``; ``hw1-*`` and ``s1-*`` are outside it by construction,
    not by an allowlist.
(5) **No serve path, no ``_GATE_TOKEN``, no metaclass.** This is a ``tools/``
    script of pure functions with a CLI. It imports nothing from
    ``ccf.products.gates`` and touches nothing at serve time.

Why the naming convention is DECLARED and never inferred
--------------------------------------------------------

Coverage across this ladder was measured twice before this checker existed,
and both instruments were wrong: one keyed on function names and reported
``cp-00`` 0/8, ``cp-01`` 0/9, ``cp-02`` 0/9; the other keyed on ``id in
file`` and reported an upper bound nobody may quote as coverage. Three
products used three conventions. The schema's own words on
``test_naming_convention``: *"the convention is DECLARED here rather than
inferred by a checker."*

So :func:`declared_convention` recognizes exactly two canonical phrases —
:data:`CONVENTION_DOCSTRING_FORM` and :data:`CONVENTION_NAME_FORM` — and
requires the roster's field to CONTAIN exactly one of them verbatim. That
form, and only that form, is applied to that tree. A field containing
neither, or both, is a problem naming the roster; nothing is defaulted.

The measured reason this matters: ``tests/examples/test_cp_04_seams.py``
carries meta-tests whose function DOCSTRINGS name ``CFT-G99`` (a
side-observation control) and ``CFT-G17`` (the withdrawn id). Under
``cp-04``'s declared name form neither is an observation, so the real
``cp-04`` tree measures clean. A checker that inferred "both forms" would
call both undeclared — a false red on a file this phase may not edit.

What is never read
------------------

Module docstrings (``cp-03``'s retired ``OFS-G14`` lives in one), comments,
and whole-file substrings. Under the name form a function docstring is not
scanned; under the docstring form a function name is not parsed. And the
recipe witness string in ``artifacts/assembly-recipe.yaml`` is never opened
(``24.5-L-18``): the executing test named by ``test:`` is the evidence, so it
must itself claim the id in the declared form, or the declaration is
pointing at an unrelated test and :func:`check_tree` says so.

Rosters, never counts (CLAUDE.md §3.1, ``D-65``): every problem names the
tree, the roster or the module, and the id. A right count with a wrong
member audits clean forever; a named member does not.

Usage
-----

``python tools/check_product_gates.py [--root DIR] [--python EXE]`` — exit 1
with one problem per line on stderr, or exit 0 with a one-line count. Plan
``24.5-09`` wires it into the Makefile after the four missing rosters exist,
so ``ci-core`` is never red at a commit boundary.
"""

from __future__ import annotations

import argparse
import ast
import json
import pathlib
import re
import subprocess
import sys
from typing import Literal

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

#: The closed schema every roster validates against, relative to the root.
SCHEMA_RELATIVE = "docs/schemas/product-gates/cp.product-gates.json"

#: Where a product tree keeps its roster, relative to the tree.
ROSTER_RELATIVE = "artifacts/gates.yaml"

#: Where a product tree keeps its own specification, relative to the tree. A
#: tree carrying one but no roster is at **Gate 1** — specified, not yet shipped.
SPEC_RELATIVE = "spec"

#: The schema's own id pattern, generalized from cp-04's ``\bCFT-G[0-9]{2}\b``.
#: A DIGIT is allowed after the first letter (``D-IMPL-326``): cp-07 declares
#: ``C36-G01``..``C36-G08`` in its own specification, and a letters-only prefix
#: would have required renaming a shipped spec to suit this checker. Kept in
#: step with the schema's ``id`` pattern by
#: ``test_the_token_and_the_schema_pattern_agree_on_what_an_id_is``.
GATE_ID_TOKEN = re.compile(r"\b[A-Z][A-Z0-9]{1,3}-G[0-9]{2}\b")

#: The name form: ``test_cft_g01_...`` claims ``CFT-G01``. Anchored at the
#: start of the function name; the id must be followed by ``_`` or end the name.
NAME_FORM_TOKEN = re.compile(r"^test_([a-z][a-z0-9]{1,3})_g([0-9]{2})(?:_|$)")

#: An ATX Markdown heading: its level, then its text. A specification clause is
#: found by this and never by a bare substring — ``G.2`` appears in prose all
#: over a document, and a citation that resolved against prose would report a
#: clause the specification does not have (``D-IMPL-326``).
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*$")

#: The canonical phrase a roster carries to declare the docstring form.
CONVENTION_DOCSTRING_FORM = "the gate id appears in the executing test's docstring"

#: The canonical phrase a roster carries to declare the name form. cp-04's
#: existing words, verbatim, backticks included.
CONVENTION_NAME_FORM = (
    "the gate id lower-cased with its hyphen dropped, prefixed `test_`"
)

Convention = Literal["name", "docstring"]

#: Where node ids are collected from, relative to the root, and the argument
#: handed to pytest — the same command
#: ``tests/examples/test_cp_04_seams.py::collected_node_ids`` runs.
COLLECTION_TARGET = "tests/examples/"


def _display(path: pathlib.Path, root: pathlib.Path) -> str:
    """Root-relative for readability, absolute when outside the root."""
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


def product_trees(root: pathlib.Path) -> list[pathlib.Path]:
    """Every ``examples/cp-*`` directory under ``root``, sorted.

    ``hw1-*`` and ``s1-*`` are outside the glob, which is `D-IMPL-224` (4)
    realized by construction rather than by a list of exemptions.
    """
    return sorted(path for path in root.glob("examples/cp-*") if path.is_dir())


def _discriminator(name: str) -> str | None:
    """The token after ``cp-NN-`` that tells two trees of ONE rung apart.

    ``cp-04-canonical-corporate-family-tree`` → ``canonical``. ``None`` when the
    tree name carries no rung number at all.
    """
    match = re.match(r"^cp-([0-9]{2})-([a-z0-9]+)", name)
    return match.group(2) if match else None


def test_modules_for(root: pathlib.Path, tree: pathlib.Path) -> list[pathlib.Path]:
    """The test modules that belong to one TREE — not merely to one rung.

    ``NN`` is the two-digit rung number in the tree name ``cp-NN-…``, and a tree
    whose name carries no rung number has no modules of its own.

    **Two trees can share a rung, and rung 4 does** (``D-IMPL-327``).
    ``examples/cp-04-corporate-family-tree`` is the frozen specimen and
    ``examples/cp-04-canonical-corporate-family-tree`` is the current pattern
    (``D-IMPL-319``); a bare ``test_cp_04_*.py`` glob hands each of them the
    OTHER's modules, so the canonical roster was held against the specimen's
    ``CFT-G19``/``CFT-G99`` and reported them undeclared. Measured when the
    canonical tree was first rostered — the two had never both carried one
    before, so nothing had exercised the collision.

    The rule: a tree whose discriminator token has modules of its own
    (``test_cp_04_canonical_*.py``) takes exactly those; a tree with none takes
    the rung's modules **minus** every module another same-rung tree claims. So
    the specimen keeps every module it always had, and neither tree can see the
    other's ids.

    This is a partition, not an allowlist: nothing here names a tree or a
    module, and a third rung-4 tree would be separated by the same rule.
    """
    match = re.match(r"^cp-([0-9]{2})(?:-|$)", tree.name)
    if match is None:
        return []
    rung = match.group(1)
    candidates = sorted(root.glob(f"tests/examples/test_cp_{rung}_*.py"))

    siblings = [
        other
        for other in product_trees(root)
        if other != tree and re.match(rf"^cp-{rung}(?:-|$)", other.name)
    ]

    def claimed_by(name: str) -> str | None:
        token = _discriminator(name)
        return f"test_cp_{rung}_{token}_" if token else None

    own = claimed_by(tree.name)
    if own is not None:
        mine = [path for path in candidates if path.name.startswith(own)]
        if mine:
            return mine

    theirs = {
        prefix
        for prefix in (claimed_by(other.name) for other in siblings)
        if prefix is not None
    }
    return [
        path
        for path in candidates
        if not any(path.name.startswith(prefix) for prefix in theirs)
    ]


# ---------------------------------------------------------------------------
# The artifact
# ---------------------------------------------------------------------------


def is_gate_one(tree: pathlib.Path) -> bool:
    """Is ``tree`` SPECIFIED but not yet shipped (`D-IMPL-329` follow-on)?

    Dave, 2026-09-11: *"if an example tree has `spec/` but no `gates.yaml`,
    treat it as Gate 1 / not yet shipped ... do not add a fake `gates.yaml` ...
    once `gates.yaml` appears, normal product-gate enforcement resumes."*

    cp-08 made the case: `CP-SPEC-008` was authored and approved with no
    implementation, no tests and — correctly — no roster, and its mere
    existence under ``examples/cp-*`` turned this checker red. A rung at Gate 1
    has nothing to declare gates about yet.

    **The test is the SPECIFICATION's presence, never the roster's absence.**
    Keying on "no roster" alone would let every shipped rung shed its gates and
    pass; a tree with neither is still reported
    (``test_a_tree_with_NEITHER_a_spec_NOR_a_roster_is_still_a_problem``). And
    the exemption ends the moment a roster appears, on the same directory, with
    no flag to clear
    (``test_a_gate_one_tree_gains_full_enforcement_the_moment_a_roster_appears``).

    There is no allowlist and none may be added: a tree arms full enforcement by
    shipping a roster, and reaches Gate 1 by carrying a specification. Both are
    facts about the tree rather than entries in this file (CINV-01).
    """
    if (tree / ROSTER_RELATIVE).is_file():
        return False
    spec = tree / SPEC_RELATIVE
    return spec.is_dir() and any(spec.glob("*.md"))


def gate_one_trees(root: pathlib.Path) -> list[pathlib.Path]:
    """Every product tree currently at Gate 1, in :func:`product_trees` order.

    Read by :func:`main` so a Gate-1 tree is **named in the summary** rather
    than silently skipped — Dave's *"without teaching people to ignore the
    target."* A tree that vanishes from the output is a tree nobody revisits.
    """
    return [tree for tree in product_trees(root) if is_gate_one(tree)]


def load_roster(path: pathlib.Path) -> dict:
    """Parse a roster. YAML parsing strips comments, which is the point."""
    import yaml

    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    return document if isinstance(document, dict) else {}


def load_schema(root: pathlib.Path) -> dict:
    """The closed schema, read from the tree under ``root``."""
    document = json.loads((root / SCHEMA_RELATIVE).read_text(encoding="utf-8"))
    return document if isinstance(document, dict) else {}


def declared_ids(document: dict) -> dict[str, str]:
    """``id -> test`` for every gate the roster declares.

    A duplicated id keeps its LAST ``test:``; :func:`check_tree` reports the
    duplicate separately so the collapse is never silent.
    """
    gates = _gates(document)
    return {str(gate["id"]): str(gate["test"]) for gate in gates}


def _gates(document: dict) -> list[dict]:
    declaration = document.get("declaration")
    if not isinstance(declaration, dict):
        return []
    gates = declaration.get("gates")
    if not isinstance(gates, list):
        return []
    return [gate for gate in gates if isinstance(gate, dict)]


def clause_body(text: str, clause: str) -> str | None:
    """The body of ``clause`` in ``text``, or ``None`` if it has no such heading.

    ``D-IMPL-326``. A clause is matched against the document's ATX HEADINGS —
    never a bare substring — because a clause label like ``G.2`` appears in
    prose and in cross-references throughout a specification, and a citation
    that resolved against one of those would report authority from a sentence
    rather than from a section.

    **The body ends at the next heading of the same level or higher**, so a
    clause carries its own text and not the remainder of the file. That bound
    is what gives the id check below its bite: without it every clause would
    appear to carry every id the document mentions, and the check would pass
    for any heading a roster happened to name
    (``test_the_clause_body_ends_at_the_next_heading``).

    The heading matches when its text STARTS WITH the cited label — ``### G.2
    Product gates`` answers a citation of ``G.2`` — because a specification
    titles its clauses and a roster cites them by number. The label must be
    followed by a boundary, so ``G.2`` does not answer for ``G.21``.
    """
    lines = text.splitlines()
    for index, line in enumerate(lines):
        match = HEADING.match(line)
        if match is None:
            continue
        level, title = len(match.group(1)), match.group(2)
        rest = title[len(clause):]
        if not title.startswith(clause) or (rest and rest[0].isalnum()):
            continue
        body: list[str] = []
        for following in lines[index + 1:]:
            nested = HEADING.match(following)
            if nested is not None and len(nested.group(1)) <= level:
                break
            body.append(following)
        return "\n".join(body)
    return None


def spec_clause_problems(
    root: pathlib.Path, tree: pathlib.Path, gate: dict, roster: str
) -> list[str]:
    """Whether one gate's cited acceptance authority actually resolves.

    ``D-IMPL-326`` (Dave, 2026-09-10): a product may be gated by a numbered
    ROADMAP criterion **or** by a cited clause of its own ``CP-SPEC``, because
    *"no rung built since cp-04 has one"* and fabricating an integer to satisfy
    the tool would answer the gate's real question falsely. The question the
    gate asks is *"what approved acceptance authority says this product is
    done?"*, and a citation answers it only if it can be followed.

    So all three links are walked, each with its own message naming the tree,
    the gate and what failed:

    1. the specification exists, at the path the roster gives (tree-relative —
       a product's authority is its OWN specification);
    2. the clause exists in it, as a heading;
    3. the gate's own ``id`` appears inside that clause's body.

    Link 3 is the one a coarser check would skip, and it is what stops a roster
    citing any real heading and reading as governed.

    Returns an empty list for a gate carrying no ``spec_clause`` — the legacy
    ``criterion`` form, which this function has nothing to say about. Which of
    the two a gate carries, and that it carries exactly one, is the schema's
    ``oneOf`` and is judged before this runs.
    """
    citation = gate.get("spec_clause")
    if not isinstance(citation, dict):
        return []
    gate_id = str(gate.get("id", "<unnamed>"))
    relative = str(citation.get("document", ""))
    clause = str(citation.get("clause", ""))

    document = tree / relative
    if not document.is_file():
        return [
            f"{roster}: {gate_id} cites {relative} which does not exist under"
            f" {_display(tree, root)} — a gate's acceptance authority is a"
            " clause of its own product's specification (D-IMPL-326)"
        ]
    body = clause_body(document.read_text(encoding="utf-8"), clause)
    if body is None:
        return [
            f"{roster}: {gate_id} cites clause {clause} of {relative}, which"
            " has no such heading — the citation resolves to nothing"
            " (D-IMPL-326)"
        ]
    if gate_id not in body:
        return [
            f"{roster}: {gate_id} cites clause {clause} of {relative}, and that"
            f" clause does not name {gate_id} — a citation pointing at a real"
            " heading that says nothing about this gate is not authority for it"
            " (D-IMPL-326)"
        ]
    return []


def declared_convention(document: dict) -> Convention | None:
    """The form the roster DECLARES for how a test claims a gate id.

    The ``test_naming_convention`` field is normalized (whitespace runs to
    one space, so a ``>-`` folded block reads as one line) and must CONTAIN
    exactly one of the two canonical phrases verbatim:

    * :data:`CONVENTION_DOCSTRING_FORM` → ``"docstring"``
    * :data:`CONVENTION_NAME_FORM` → ``"name"``

    Neither, or both, is ``None`` — the caller reports that as a problem
    naming the roster. Nothing is ever defaulted, because a default is an
    inference, and inference is the instrument that measured 0/8, 0/9, 0/9.
    """
    declaration = document.get("declaration")
    if not isinstance(declaration, dict):
        return None
    field = declaration.get("test_naming_convention")
    if not isinstance(field, str):
        return None
    text = " ".join(field.split())
    has_docstring = CONVENTION_DOCSTRING_FORM in text
    has_name = CONVENTION_NAME_FORM in text
    if has_docstring and not has_name:
        return "docstring"
    if has_name and not has_docstring:
        return "name"
    return None


# ---------------------------------------------------------------------------
# What the tests claim
# ---------------------------------------------------------------------------


def _test_functions(
    module: ast.Module,
) -> list[tuple[str, ast.FunctionDef | ast.AsyncFunctionDef]]:
    """``(qualname, node)`` for every ``test_*`` function pytest would collect.

    Module-level functions and methods of module-level classes (``Class::test``
    in a node id). Functions nested inside functions are not collected by
    pytest and are not visited.
    """
    found: list[tuple[str, ast.FunctionDef | ast.AsyncFunctionDef]] = []
    for node in module.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("test_"):
                found.append((node.name, node))
        elif isinstance(node, ast.ClassDef):
            for inner in node.body:
                if isinstance(inner, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if inner.name.startswith("test_"):
                        found.append((f"{node.name}::{inner.name}", inner))
    return found


def named_ids(
    module: pathlib.Path,
    *,
    convention: Convention,
    root: pathlib.Path | None = None,
) -> dict[str, set[str]]:
    """``id -> {node ids}`` for every gate id a test function CLAIMS in ``module``.

    ONLY the declared form is read:

    * ``"name"`` — the function NAME matches :data:`NAME_FORM_TOKEN`
      (``test_cft_g01_…`` claims ``CFT-G01``). Docstrings are not scanned.
    * ``"docstring"`` — the function DOCSTRING (``ast.get_docstring``)
      contains :data:`GATE_ID_TOKEN` matches. Names are not parsed.

    Never read, under either form: the module docstring, comments, string
    literals in the body, or the file as text. Node ids are root-relative
    when ``root`` is given, so they compare whole against a collection run
    from ``root``.
    """
    source = module.read_text(encoding="utf-8")
    parsed = ast.parse(source, filename=str(module))
    prefix = _display(module, root) if root is not None else module.as_posix()
    claims: dict[str, set[str]] = {}
    for qualname, node in _test_functions(parsed):
        node_id = f"{prefix}::{qualname}"
        if convention == "name":
            match = NAME_FORM_TOKEN.match(node.name)
            if match is None:
                continue
            gate_id = f"{match.group(1).upper()}-G{match.group(2)}"
            claims.setdefault(gate_id, set()).add(node_id)
        else:
            docstring = ast.get_docstring(node) or ""
            for gate_id in set(GATE_ID_TOKEN.findall(docstring)):
                claims.setdefault(gate_id, set()).add(node_id)
    return claims


# ---------------------------------------------------------------------------
# What pytest executes
# ---------------------------------------------------------------------------


def _collection(
    root: pathlib.Path, *, python: str = sys.executable
) -> tuple[frozenset[str] | None, str]:
    """One ``pytest --collect-only -q`` over ``tests/examples/``; ``(ids, tail)``.

    ``ids`` is ``None`` when the run exited non-zero — a broken tree yields
    no verdict, not a clean one. ``tail`` is the last of stdout for the
    problem line.
    """
    completed = subprocess.run(
        [
            python,
            "-m",
            "pytest",
            COLLECTION_TARGET,
            "--collect-only",
            "-q",
            "-p",
            "no:cacheprovider",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    tail = (completed.stdout or "")[-3000:]
    if completed.returncode != 0:
        return None, tail
    ids = frozenset(
        line.strip() for line in completed.stdout.splitlines() if "::" in line
    )
    return ids, tail


def collect_node_ids(
    root: pathlib.Path, *, python: str = sys.executable
) -> frozenset[str] | None:
    """Every node id pytest collects under ``tests/examples/``, or ``None``.

    ``None`` means the collection failed and NOTHING can be decided — the
    caller must report that, never treat it as an empty (and so trivially
    clean) tree.
    """
    ids, _tail = _collection(root, python=python)
    return ids


def _resolvable(collected: frozenset[str]) -> frozenset[str]:
    """Collected node ids plus the bracket-free base of each parametrized one.

    ``path::name[param]`` is what pytest prints; a roster's ``test:`` names
    ``path::name`` (the schema forbids ``[``), and that is still a reference
    to something that runs. The WHOLE path stays in the comparison — the
    basename-matching defect the 24.4 close panel found is not repeated.
    """
    resolvable: set[str] = set()
    for node in collected:
        resolvable.add(node)
        module, sep, function = node.rpartition("::")
        if sep:
            base, bracket, _params = function.partition("[")
            if bracket:
                resolvable.add(f"{module}::{base}")
    return frozenset(resolvable)


# ---------------------------------------------------------------------------
# Judgment
# ---------------------------------------------------------------------------


def _schema_problems(roster: str, document: dict, schema: dict) -> list[str]:
    import jsonschema

    if not isinstance(schema, dict) or not schema:
        # Phase 24.5 close panel (2026-09-03): a corrupted or non-object schema
        # file used to fold to ``{}``, and an empty schema validates every
        # roster — the closed-keys guarantee vanished silently. Fail CLOSED.
        return [
            f"{roster}: the closed schema at {SCHEMA_RELATIVE} is empty or not an"
            " object, so no roster can be judged against it"
        ]
    validator = jsonschema.Draft202012Validator(schema)
    problems: list[str] = []
    for error in sorted(validator.iter_errors(document), key=lambda e: list(e.absolute_path)):
        where = "/".join(str(part) for part in error.absolute_path) or "<document>"
        problems.append(f"{roster}: {where}: {error.message}")
    return problems


def check_tree(
    root: pathlib.Path,
    tree: pathlib.Path,
    *,
    collected: frozenset[str],
    schema: dict,
) -> list[str]:
    """Every problem in one product tree, each naming the tree and the id.

    In order, stopping where nothing further can be read:

    0. a tree carrying a ``spec/`` and no roster is at **Gate 1** and yields
       nothing — specified, not yet shipped (:func:`is_gate_one`);
    1. otherwise, no ``artifacts/gates.yaml`` → one problem (`D-IMPL-224` (1));
    2. schema violations, and a roster declaring ZERO gates (`D-IMPL-224` (3));
    3. an unrecognized ``test_naming_convention`` → one problem, and judgment
       STOPS for this tree — no form is defaulted;
    4. a duplicated id, and a ``spec_clause`` whose cited authority does not
       resolve — the document, the clause, or the id inside it (`D-IMPL-326`);
    5. a declared id whose ``test:`` pytest did not collect (no executing test);
    6. a test naming an id the roster does not declare, in the declared form;
    7. a declared ``test:`` whose function does not itself claim the id in the
       declared form — a declaration pointing at an unrelated test, which is
       the `L-18` witness class of defect.
    """
    tree_name = _display(tree, root)
    roster_path = tree / ROSTER_RELATIVE
    roster = _display(roster_path, root)
    if is_gate_one(tree):
        # Specified, not yet shipped. Named in the summary by `main`, never
        # silently dropped (`D-IMPL-329` follow-on).
        return []
    if not roster_path.is_file():
        return [
            f"{tree_name}: {ROSTER_RELATIVE} is missing — a shipped cp-* rung"
            " declares its gates as data (D-IMPL-224 (1))"
        ]

    document = load_roster(roster_path)
    problems = _schema_problems(roster, document, schema)
    declaration = document.get("declaration")
    if isinstance(declaration, dict) and declaration.get("gates") == []:
        problems.append(f"{roster}: declares ZERO gates (D-IMPL-224 (3))")
    if problems:
        return problems

    convention = declared_convention(document)
    if convention is None:
        return [
            f"{roster}: test_naming_convention is not recognized — it must"
            f" contain exactly one of {CONVENTION_DOCSTRING_FORM!r} /"
            f" {CONVENTION_NAME_FORM!r} verbatim (the convention is declared,"
            " never inferred)"
        ]

    gates = _gates(document)
    seen: set[str] = set()
    for gate in gates:
        gate_id = str(gate["id"])
        if gate_id in seen:
            problems.append(f"{roster}: {gate_id} is declared more than once")
        seen.add(gate_id)
        # The second acceptance-authority form (`D-IMPL-326`). Walked here,
        # beside the duplicate check, because both are facts about the ROSTER
        # rather than about the test tree — and because a gate whose authority
        # resolves to nothing should be reported whether or not its test runs.
        problems.extend(spec_clause_problems(root, tree, gate, roster))

    declared = declared_ids(document)
    resolvable = _resolvable(collected)
    executing: dict[str, str] = {}
    for gate_id, node in sorted(declared.items()):
        if node in resolvable:
            executing[gate_id] = node
        else:
            problems.append(
                f"{tree_name}: {gate_id} declares test {node} which pytest did"
                " not collect — no executing test"
            )

    # What the rung's own modules claim, in the declared form only.
    claims_by_module: dict[pathlib.Path, dict[str, set[str]]] = {}
    observed: dict[str, set[str]] = {}
    for module in test_modules_for(root, tree):
        claims = named_ids(module, convention=convention, root=root)
        claims_by_module[module.resolve()] = claims
        for gate_id, nodes in claims.items():
            observed.setdefault(gate_id, set()).update(nodes)
    for gate_id in sorted(observed):
        if gate_id in declared:
            continue
        for node in sorted(observed[gate_id]):
            problems.append(f"{node} names {gate_id} which {roster} does not declare")

    # The executing test is the evidence, so it must claim the id itself.
    for gate_id, node in sorted(executing.items()):
        module_part, _sep, _function = node.partition("::")
        module_path = (root / module_part).resolve()
        if not module_path.is_file():
            # Phase 24.5 close panel (2026-09-03): this branch used to
            # ``continue``, so a declaration pointing at a collected node whose
            # module is not a file under ``root`` was never judged. Fail CLOSED.
            problems.append(
                f"{tree_name}: {gate_id} declares test {node} but {module_part} is"
                f" not a file under {root} — the executing test cannot be read,"
                " so its claim cannot be judged"
            )
            continue
        if module_path not in claims_by_module:
            claims_by_module[module_path] = named_ids(
                module_path, convention=convention, root=root
            )
        if node not in claims_by_module[module_path].get(gate_id, set()):
            problems.append(
                f"{tree_name}: {gate_id} declares test {node} but that function"
                f" does not name {gate_id} under the declared {convention} form"
                " — the executing test is the evidence and must claim the id"
            )

    return problems


def _collection_problem(tail: str) -> str:
    return (
        f"collection over {COLLECTION_TARGET} failed, so no roster can be"
        f" judged:\n{tail}"
    )


def _check_trees(root: pathlib.Path, *, collected: frozenset[str]) -> list[str]:
    """Every tree under ``root`` judged against one already-run collection."""
    trees = product_trees(root)
    if not trees:
        return [f"{root}: no examples/cp-* tree found — nothing was checked"]
    schema = load_schema(root)
    problems: list[str] = []
    for tree in trees:
        problems.extend(check_tree(root, tree, collected=collected, schema=schema))
    return problems


def check(root: pathlib.Path, *, python: str = sys.executable) -> list[str]:
    """Every problem across every ``examples/cp-*`` tree under ``root``.

    Collection runs ONCE. A failed collection is the single problem "cannot
    be judged"; a root with no ``cp-*`` tree at all is a problem too, so a
    wrong ``--root`` cannot read clean.
    """
    collected, tail = _collection(root, python=python)
    if collected is None:
        return [_collection_problem(tail)]
    return _check_trees(root, collected=collected)


def _summary(root: pathlib.Path, *, collected: frozenset[str]) -> tuple[int, int, int]:
    """``(trees, declared gates, executing)`` for the success line.

    Only meaningful after the trees were judged clean against this same
    ``collected`` set; read from the tree rather than restated from a count,
    so the line reports what is there.
    """
    resolvable = _resolvable(collected)
    trees = product_trees(root)
    declared_total = 0
    executing_total = 0
    for tree in trees:
        roster_path = tree / ROSTER_RELATIVE
        if not roster_path.is_file():
            continue
        declared = declared_ids(load_roster(roster_path))
        declared_total += len(declared)
        executing_total += sum(1 for node in declared.values() if node in resolvable)
    return len(trees), declared_total, executing_total


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Check every examples/cp-* gate roster: closed keys, a declared"
            " naming convention, an EXECUTING test per declared id, no test"
            " naming an undeclared id, never zero (D-IMPL-224)."
        )
    )
    parser.add_argument(
        "--root",
        type=pathlib.Path,
        default=REPO_ROOT,
        help="repository root to check (default: this checkout)",
    )
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="interpreter that runs `pytest --collect-only` (default: this one)",
    )
    args = parser.parse_args(argv)
    root = args.root.resolve()

    # ONE collection per invocation; the verdict and the count read the same set.
    collected, tail = _collection(root, python=args.python)
    if collected is None:
        problems = [_collection_problem(tail)]
    else:
        problems = _check_trees(root, collected=collected)
    if problems:
        for problem in problems:
            print(problem, file=sys.stderr)
        print(
            "Fix the rosters above. Run `make product-gates` to re-check.",
            file=sys.stderr,
        )
        return 1

    assert collected is not None
    trees, declared, executing = _summary(root, collected=collected)
    # A Gate-1 tree is NAMED, never silently skipped: a tree that vanishes from
    # this output is a tree nobody revisits (`D-IMPL-329` follow-on).
    pending = [_display(tree, root) for tree in gate_one_trees(root)]
    shipped = trees - len(pending)
    line = (
        f"checked {shipped} shipped product trees,"
        f" {declared} declared gates, {executing} executing"
    )
    if pending:
        line += (
            f"; {len(pending)} at Gate 1 — specified, not yet shipped,"
            f" enforcement resumes when a roster appears: {', '.join(pending)}"
        )
    print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
