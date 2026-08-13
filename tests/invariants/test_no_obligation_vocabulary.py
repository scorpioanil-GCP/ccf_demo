"""The SDK declares no obligation vocabulary, and this is what makes it true.

``D-IMPL-117`` (Dave, 2026-08-11) scopes Phase 15.6 Track B to **carrying
mechanism, not judgement**: the SDK ships *"a signal-to-obligation binding that
survives replay, and owes no obligation vocabulary (that is user configuration —
CLAUDE.md §11, and the same posture ``D-IMPL-101`` took on salience)."* Gap 3
binds an opaque obligation reference per :class:`~ccf.halflife.assessment.DebtSignal`
through the Control Plane. The mechanism is the SDK's; the words are the
deployment's.

**The hole this module exists to close, measured rather than asserted.**
``15.6-RESEARCH.md`` § B4 read the two shipped CINV-01 checkers and found that
neither sees this defect. ``tools/lints/no_hardcoding.py`` catches a module-level
*numeric* table under ``cinv01b-numeric-table`` (its ``PARAM_SCHEMA_MARKERS`` are
``params``/``parameters``/``thresholds``), and ``cinv01a-prompt-shape`` scores
*prose* — length, sentence count, template-brace density, role-preamble openers,
against ``MIN_PROMPT_CHARS = 40``. A three-member ``StrEnum`` of obligation names
is neither numeric nor prose. **It would pass every lint in this tree and still
be the CLAUDE.md §11 defect** ``D-IMPL-117`` says the SDK owes nothing of.
``15.6-RESEARCH.md`` rates that the single highest-risk item in Track B.

This module is armed **before** the work it guards, so it is a gate rather than a
post-mortem.

**The hole the guard itself had, measured the same way.** Phase 15.6's
close-time cross-AI panel (CLAUDE.md §3.1) injected
``_OBLIGATION_TABLE: tuple[str, ...] = ("re-pull", "escalate", "fail-closed")``
into ``src/ccf/halflife/debt.py`` — inside this guard's own scan root — and the
module stayed **green at 14 passed**. A tuple is the most natural alternative
spelling of the exact thing this module refuses, and it costs a plan nothing to
reach for instead of a ``StrEnum``. :func:`_string_table_members` closes it, and
the injection is now a parametrized control below so a future re-narrowing turns
red rather than quietly permissive. (The full ``make ci`` did not go green on
that injection —
``tests/halflife/test_debt_delivery.py::test_no_module_level_collection_of_string_literals_exists``
caught it — but that sibling reads two module *bodies* in one package, while
this guard reads five modules plus class scope plus ``artifacts.py``. The
narrower check catching one case is not the wider claim being true.)

Why this lives in ``tests/invariants/`` and not in ``tools/lints/``
------------------------------------------------------------------

The tree draws that line by **scope**, not by taste.
``tools/lints/__main__.py::RULE_TREE_SCOPE`` maps every registered checker to a
*whole-tree* scope — ``("src", "runtime")`` or wider — and every checker there
runs over every file on every ``make lint``. This rule is not general over a
tree: it names **two specific paths** and **four specific exemptions**.
Registering it as a checker would either over-apply it, making every ``StrEnum``
in ``src/`` suspect, or require a path allowlist inside a checker — and
``tools/lints/__init__.py``'s own header states the allowlist posture, that only
``no_hardcoding`` findings are ever offered to the allowlist (D-13). A targeted
structural claim with no checker half is what
``tests/examples/test_section_one_is_agent_free.py`` already is, and
``tests/invariants/`` is where this project keeps named structural properties
that are neither lints nor unit tests. The placement is recorded here so it is a
decision rather than a preference.

**Why no ``tools.lints`` helper is reused.** The shared helpers there read the
*import* graph. This rule reads *declarations*, so there is nothing to share and
no sibling checker whose edit could silently change this one.

What this check does NOT claim
------------------------------

* It does **not** claim that every domain value in ``src/`` is caught. It reads
  two named roots and three syntactic shapes — an ``Enum``-family class, a
  ``Literal`` over strings, and a closed table of string constants in
  tuple/list/set/``frozenset`` form.
* It does **not** catch a closed table of **fewer than
  :data:`MINIMUM_TABLE_MEMBERS`** strings. A one-member collection is a default,
  not a choice among alternatives, and this scan root contains two legitimate
  ones. The threshold and its cost are stated at that constant rather than left
  for a reader to discover.
* It does **not** read function bodies for tables. A tuple of strings inside a
  function is a local; ``Literal`` keeps its wider walk.
* It does **not** replace CINV-01. ``cinv01a``/``cinv01b``/``cinv01c`` keep their
  jobs; this is the shape they were measured not to reach.
* It makes **no** statement about ``runtime/``, about ``examples/``, or about any
  tree outside :data:`SCAN_ROOTS`. An obligation vocabulary in an example
  artifact is where ``D-IMPL-117`` puts it, and is not a finding here.
* It does **not** judge what an obligation string *means*. Validation of meaning
  is exactly the judgement ``D-IMPL-117`` assigns to the context product creator.
"""

from __future__ import annotations

import ast
import pathlib
import shutil

import pytest

#: Anchored on this file rather than on ``Path.cwd()`` — a check whose scan root
#: depends on the working directory passes or fails for reasons that have nothing
#: to do with the tree. ``parents[2]`` is the repo root from
#: ``tests/invariants/<module>.py``.
REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

#: The two roots, each with the reason it is in scope. A **mixed list** — one
#: directory and one file — rather than a glob, because the rule's scope is two
#: named places and widening it to a glob would widen the rule.
SCAN_ROOTS: tuple[tuple[str, str], ...] = (
    # Where the debt signal is produced and assessed. ``15.6-RESEARCH.md`` § B4:
    # ``assess_debt`` is the one site that sets ``DebtSignal.FORCED_LLM``, so an
    # obligation vocabulary written by hand lands here first.
    (
        "src/ccf/halflife",
        "D-IMPL-117 gap 3 — the debt signal's home; the likeliest site",
    ),
    # Where ``DebtProfile`` lives. ``15.6-RESEARCH.md`` § B4 names it as the slot
    # the obligation binding attaches to, which makes it the second likeliest
    # place for the vocabulary to arrive alongside the mechanism.
    (
        "src/ccf/controlplane/artifacts.py",
        "D-IMPL-117 gap 3 — DebtProfile is the binding's slot",
    ),
)

#: Names exempted from the absence claim, each with the reason it is SDK
#: structure rather than deployment vocabulary. This list is the **review seam**:
#: a new closed set of strings in either scan root fails until someone adds it
#: here with a justification, which is a reviewable event rather than a silent
#: one. In the ``DENIED_PACKAGES`` reason-column shape of
#: ``tests/examples/test_section_one_is_agent_free.py`` — a list nobody can
#: justify entry by entry is a list that grows by cargo cult.
EXEMPT_DECLARATIONS: tuple[tuple[str, str], ...] = (
    # The routing state an assessed D_c falls into (whitepaper §7.7 CAR). This is
    # the type the obligation mapping's KEYS are validated against — the SDK owns
    # it, ships it, and branches on two of its three members today. Removing this
    # exemption would ban the very enum the binding mechanism needs.
    (
        "DebtSignal",
        "whitepaper §7.7 CAR routing state; the key type of the binding itself",
    ),
    # The three factors of the extended form — F, C, S. Whitepaper §7.7 names
    # them; the SDK computes them. Its own comment states the distinction this
    # module enforces: "the names are the SDK's own structure, never deployment
    # vocabulary."
    (
        "DebtFactorName",
        "whitepaper §7.7 F/C/S; SDK-computed structure, not deployment values",
    ),
    # What a manifest entry declares about the artifact it names (D-IMPL-80):
    # register into the Control Plane registry, or load-and-hand-back. Both are
    # SDK code paths, so the set is closed by the SDK's own shape.
    (
        "ArtifactRole",
        "D-IMPL-80 — names two SDK code paths, not two deployment values",
    ),
    # Which of the Control Plane's two registration paths an entry travels
    # (D-IMPL-85, ERGO-18). Same reason: the members name SDK methods.
    (
        "RegistrationMode",
        "D-IMPL-85 — names two SDK registration paths, not deployment values",
    ),
    # The three characters that make a path a glob rather than a name, used by
    # `ManifestEntry._path_is_a_name_not_a_pattern`. Added when the table shape
    # was brought into scope at Phase 15.6's close; it is the **only** finding
    # the widening produced in either scan root, and it is not a vocabulary at
    # all: the set is closed by `fnmatch`'s syntax — Python's, not any
    # deployment's — and no deployment can add a fourth member to it. Removing
    # this exemption would ban a syntax check, not protect gap 3.
    (
        "_GLOB_CHARACTERS",
        "fnmatch's own metacharacters; closed by Python's syntax, not by a"
        " deployment's values",
    ),
)

#: The exempted names alone, for the membership test.
EXEMPT_NAMES: frozenset[str] = frozenset(
    name for name, _reason in EXEMPT_DECLARATIONS
)

#: Base names that make a class a closed vocabulary. ``StrEnum`` is the spelling
#: ``15.6-RESEARCH.md`` Pitfall 4 warns about; ``Enum`` and ``IntEnum`` are the
#: same defect in different clothes, and ``str, Enum`` is the pre-3.11 spelling
#: that still parses.
ENUM_BASE_NAMES: frozenset[str] = frozenset({"Enum", "StrEnum", "IntEnum"})

#: Builders that turn a literal collection into a closed one. ``frozenset({…})``
#: is a ``Call``, not a collection literal, so without these the most idiomatic
#: spelling of an immutable table would walk straight past the AST predicate.
COLLECTION_BUILDERS: frozenset[str] = frozenset(
    {"frozenset", "set", "tuple", "list"}
)

#: How many string members make a *table* rather than a value.
#:
#: Two. A vocabulary is a **choice among alternatives**; a one-member collection
#: is a default, and this scan root contains two of those —
#: ``ProductClassDeclaration``'s ``accepted_policy_binding_modes`` and
#: ``accepted_lineage_modes``, each a ``frozenset`` of one mode carried as a
#: field default. Exempting them by name would put two entries on the review
#: seam that are not vocabularies at all and would teach the next reader that
#: the seam is where inconvenient findings go.
#:
#: **Stated as a limitation rather than elided** (this module's "What this check
#: does NOT claim" contract): a deliberately-written one-member obligation table
#: passes. That shape is not what ``15.6-RESEARCH.md`` § B4 measured as the risk,
#: and the cost of catching it is a seam that stops meaning anything.
MINIMUM_TABLE_MEMBERS = 2

#: The remedy, stated in every failure message so the reader is not left to infer
#: it. ``src/ccf/skills/catalog.py::SkillRequirements`` is the shipped precedent
#: ``D-IMPL-101`` already cited for salience: ``frozenset[str]`` members that are
#: "Opaque to the SDK; declared by the deployment", compared structurally and
#: never interpreted.
REMEDY = (
    "the obligation reference is an opaque `str`, or a small contract of opaque"
    " strings in the `src/ccf/skills/catalog.py::SkillRequirements` shape —"
    " declared by the deployment, validated structurally (key type, uniqueness),"
    " and never enumerated by the SDK. The vocabulary ships in an example"
    " artifact"
)

#: The rulings and rules a failure must name, so a reader who has never seen this
#: module can find the authority without a search.
AUTHORITY = (
    "D-IMPL-117 (the SDK owes the binding mechanism and no obligation"
    " vocabulary), CLAUDE.md §11 (mechanism, not values) and §6.4 (the"
    " No-Hardcoding Rule), and the posture D-IMPL-101 took on salience"
)


class ObligationVocabularyFound(AssertionError):
    """Raised when a scan root declares a closed vocabulary of strings.

    An ``AssertionError`` subclass so pytest reports it as an ordinary failure,
    and a distinct type so the negative controls can assert that *this* guard
    refused rather than that something, somewhere, raised.
    """


# ---------------------------------------------------------------------------
# The scan.
# ---------------------------------------------------------------------------


def scanned_modules(base: pathlib.Path) -> list[pathlib.Path]:
    """Every Python module under :data:`SCAN_ROOTS`, resolved against `base`.

    Takes `base` as an argument so the negative controls can repoint the whole
    scan at a copy and exercise the real enumerator, the real walk and the real
    predicate rather than a reimplementation of them.

    Handles a directory root and a file root, because :data:`SCAN_ROOTS` is one
    of each and collapsing them into a glob would widen the rule's scope.
    """
    modules: set[pathlib.Path] = set()
    for relative, _reason in SCAN_ROOTS:
        root = base / relative
        if root.is_dir():
            modules.update(root.rglob("*.py"))
        elif root.is_file():
            modules.add(root)
    return sorted(modules)


def _base_names(node: ast.ClassDef) -> set[str]:
    """The bare names of a class's bases, for `Enum` and `enum.Enum` alike."""
    names: set[str] = set()
    for base in node.bases:
        if isinstance(base, ast.Name):
            names.add(base.id)
        elif isinstance(base, ast.Attribute):
            names.add(base.attr)
    return names


def _is_string_literal_subscript(node: ast.AST) -> bool:
    """True for a ``Literal[...]`` subscript whose members are all strings.

    ``Literal["a", "b"]``, ``typing.Literal["a"]`` and the single-member form are
    all the same declaration. A ``Literal`` over non-strings — ``Literal[0, 1]``
    — is not an obligation vocabulary and is left alone; a numeric table is
    ``cinv01b-numeric-table``'s job, and duplicating its claim here would give
    the tree two definitions of one rule.
    """
    if not isinstance(node, ast.Subscript):
        return False
    origin = node.value
    named = (
        origin.id
        if isinstance(origin, ast.Name)
        else origin.attr
        if isinstance(origin, ast.Attribute)
        else ""
    )
    if named != "Literal":
        return False
    inner = node.slice
    members = inner.elts if isinstance(inner, ast.Tuple) else [inner]
    return bool(members) and all(
        isinstance(member, ast.Constant) and isinstance(member.value, str)
        for member in members
    )


def _string_table_members(node: ast.AST) -> list[str] | None:
    """The members of a closed table of string constants, or ``None``.

    The shape the guard could not see until Phase 15.6's close-time cross-AI
    panel injected it. ``_OBLIGATION_TABLE: tuple[str, ...] = ("re-pull",
    "escalate", "fail-closed")`` in ``src/ccf/halflife/debt.py`` — inside this
    guard's own scan root — left the module at **14 passed**. A tuple is the
    most natural alternative spelling of the exact thing this module exists to
    refuse, and it costs a plan nothing to reach for instead of a ``StrEnum``.

    Both the literal forms (``(…)``, ``[…]``, ``{…}``) and the builder form
    (``frozenset({…})`` and friends, which parse as a ``Call`` and not as a
    collection) are read, because an immutable table is the one a plan is most
    likely to write and ``frozenset`` is how it would write it.

    A table of **non-strings** is left alone, on
    :func:`_is_string_literal_subscript`'s reasoning: a numeric table is
    ``cinv01b-numeric-table``'s job and two definitions of one rule is worse
    than one.
    """
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        elements = node.elts
    elif isinstance(node, ast.Call):
        origin = node.func
        named = (
            origin.id
            if isinstance(origin, ast.Name)
            else origin.attr
            if isinstance(origin, ast.Attribute)
            else ""
        )
        if named not in COLLECTION_BUILDERS or len(node.args) != 1:
            return None
        inner = node.args[0]
        if not isinstance(inner, (ast.Tuple, ast.List, ast.Set)):
            return None
        elements = inner.elts
    else:
        return None

    if len(elements) < MINIMUM_TABLE_MEMBERS:
        return None
    if not all(
        isinstance(element, ast.Constant) and isinstance(element.value, str)
        for element in elements
    ):
        return None
    return [str(element.value) for element in elements]  # type: ignore[attr-defined]


def _bound_name(node: ast.AST, qualifier: str) -> str | None:
    """The name a statement binds, qualified by its enclosing class if any.

    A class attribute is reported as ``DebtProfile.obligations`` rather than as
    the bare ``obligations``, so an exemption cannot accidentally cover a
    same-named attribute in a different class.
    """
    bound: str | None = None
    if isinstance(node, ast.Assign) and node.targets:
        target = node.targets[0]
        bound = target.id if isinstance(target, ast.Name) else None
    elif isinstance(node, ast.AnnAssign):
        bound = node.target.id if isinstance(node.target, ast.Name) else None
    elif isinstance(node, ast.TypeAlias):  # PEP 695 `type X = Literal[...]`
        bound = node.name.id if isinstance(node.name, ast.Name) else None
    if bound is None:
        return None
    return f"{qualifier}.{bound}" if qualifier else bound


def _is_dunder(name: str) -> bool:
    """True for ``__all__`` and its kin — a language construct, not a table.

    ``__all__`` is a list of string constants in every scanned module, and it
    names the module's own **exports**, which are code. Skipping it structurally
    rather than exempting it by name keeps :data:`EXEMPT_DECLARATIONS` a list of
    *judgements* — the shape
    ``tests/halflife/test_debt_delivery.py::test_no_module_level_collection_of_string_literals_exists``
    already takes for the same construct, in the same package, for the same
    reason.
    """
    final = name.rsplit(".", 1)[-1]
    return final.startswith("__") and final.endswith("__")


def _declarations(
    node: ast.AST, qualifier: str, *, inside_function: bool = False
) -> list[tuple[str, str, int]]:
    """``(name, kind, lineno)`` for every closed vocabulary under `node`.

    Recursive rather than a flat :func:`ast.walk` because the name a
    ``Literal[...]`` belongs to is a fact about its *enclosing* statement, and a
    flat walk throws that away — leaving a finding that says a vocabulary exists
    without saying which one.

    Both the alias form (``X = Literal["a", "b"]``) and the annotation form
    (``obligations: dict[DebtSignal, Literal["a", "b"]]``) are read. The
    annotation form is deliberately in scope even though it is the less obvious
    one: the most natural way to write this defect is a field on ``DebtProfile``,
    where the strings live in the annotation and never in a value.

    **Closed string tables** (:func:`_string_table_members`) are read in the same
    two-reading style, because the statement — annotation and value together —
    is what gets walked. They are read at **module and class scope only**. A
    tuple of strings inside a function body is a local, not a declaration, and
    scanning function bodies for them would flood the guard with findings that
    are not the defect and get it switched off. ``Literal`` keeps its wider walk
    unchanged, so no existing coverage narrows.
    """
    found: list[tuple[str, str, int]] = []
    for child in ast.iter_child_nodes(node):
        if isinstance(child, ast.ClassDef):
            if _base_names(child) & ENUM_BASE_NAMES:
                name = f"{qualifier}.{child.name}" if qualifier else child.name
                found.append((name, "enum", child.lineno))
            found.extend(
                _declarations(
                    child, child.name, inside_function=inside_function
                )
            )
            continue
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            found.extend(
                _declarations(child, qualifier, inside_function=True)
            )
            continue
        bound = _bound_name(child, qualifier)
        for descendant in ast.walk(child):
            if _is_string_literal_subscript(descendant):
                found.append(
                    (bound or "<unbound Literal>", "literal", descendant.lineno)
                )
            if inside_function or bound is None or _is_dunder(bound):
                continue
            if _string_table_members(descendant) is not None:
                found.append((bound, "table", descendant.lineno))
    return found


def declared_vocabularies(path: pathlib.Path) -> list[tuple[str, str, int]]:
    """Every closed string vocabulary one module declares, exemptions removed."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [
        finding
        for finding in _declarations(tree, "")
        if finding[0] not in EXEMPT_NAMES
    ]


def offenders(base: pathlib.Path) -> dict[str, list[str]]:
    """``module path -> the vocabularies it declares``, for every offender."""
    found: dict[str, list[str]] = {}
    for module in scanned_modules(base):
        declared = declared_vocabularies(module)
        if declared:
            found[module.relative_to(base).as_posix()] = [
                f"{name} ({kind}, line {lineno})"
                for name, kind, lineno in declared
            ]
    return found


def refuse_obligation_vocabulary(base: pathlib.Path) -> None:
    """Raise :class:`ObligationVocabularyFound` if any scan root declares one.

    The single refusal every assertion below routes through, so the negative
    controls prove the guard the shipped-tree test uses rather than a parallel
    one written for the control.
    """
    found = offenders(base)
    if found:
        raise ObligationVocabularyFound(
            f"a closed vocabulary of strings is declared in {sorted(found)}:"
            f" {found}. The SDK enumerates no obligation vocabulary —"
            f" {AUTHORITY}. Remedy: {REMEDY}. If this declaration is SDK"
            " structure rather than deployment values, add it to"
            " EXEMPT_DECLARATIONS with the reason, which is the reviewable"
            " event this guard exists to force."
        )


# ---------------------------------------------------------------------------
# Preconditions — a vacuous pass is the failure this module exists to prevent.
# ---------------------------------------------------------------------------


def test_both_scan_roots_exist_and_the_walk_found_modules() -> None:
    """Without this, a renamed package makes every check below pass over an
    empty set and the absence claim becomes a claim about nothing.

    The same posture ``tools/publish_scan.py::require_populated`` already takes
    for a scanned tree: fail closed on an empty root rather than report clean.
    """
    for relative, reason in SCAN_ROOTS:
        root = REPO_ROOT / relative
        assert root.exists(), (
            f"missing scan root {relative} ({reason}) — the obligation"
            " vocabulary guard is scanning nothing. If the package moved,"
            " move SCAN_ROOTS with it rather than dropping the entry."
        )

    modules = scanned_modules(REPO_ROOT)
    assert modules, (
        f"both roots in {[r for r, _ in SCAN_ROOTS]} exist but the walk found"
        " no Python modules — the guard is vacuous"
    )
    covered = {
        module.relative_to(REPO_ROOT).as_posix().split("/")[2]
        for module in modules
    }
    assert {"halflife", "controlplane"} <= covered, (
        f"the walk reached {sorted(covered)} — both named roots must"
        " contribute at least one module"
    )


def test_every_exemption_documents_its_reason() -> None:
    """An exemption without a justification is a hole with a name on it."""
    for name, reason in EXEMPT_DECLARATIONS:
        assert reason.strip(), f"{name} is exempted with no recorded reason"


def test_every_exemption_still_names_something_in_the_tree() -> None:
    """A stale exemption is the same repudiation defect as a vacuous scan.

    If ``DebtFactorName`` were renamed, its exemption would silently become a
    permanent hole waiting for a future declaration to reuse the name. Asserting
    each exemption is *live* keeps the list honest against the tree rather than
    against its own history.
    """
    declared: set[str] = set()
    for module in scanned_modules(REPO_ROOT):
        tree = ast.parse(module.read_text(encoding="utf-8"))
        declared.update(name for name, _kind, _line in _declarations(tree, ""))

    stale = sorted(EXEMPT_NAMES - declared)
    assert not stale, (
        f"{stale} are exempted but no longer declared in the scan roots —"
        " remove the entries rather than leaving named holes"
    )


# ---------------------------------------------------------------------------
# The gate.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "module",
    scanned_modules(REPO_ROOT),
    ids=lambda path: path.relative_to(REPO_ROOT).as_posix(),
)
def test_no_scanned_module_declares_an_obligation_vocabulary(
    module: pathlib.Path,
) -> None:
    """One test per scanned module, named in the failure.

    Parametrized rather than aggregated so the failing module is the test id
    rather than a name buried in an assertion message.
    """
    declared = declared_vocabularies(module)
    assert not declared, (
        f"{module.relative_to(REPO_ROOT).as_posix()} declares {declared} — the"
        f" SDK enumerates no obligation vocabulary. {AUTHORITY}."
        f" Remedy: {REMEDY}."
    )


def test_the_shipped_tree_declares_no_obligation_vocabulary() -> None:
    """The same claim once more, aggregated — so one run names every offender
    at once rather than one per run."""
    refuse_obligation_vocabulary(REPO_ROOT)


# ---------------------------------------------------------------------------
# The negative controls — a guard that has never refused anything is a guard
# nobody has tested.
# ---------------------------------------------------------------------------


def _copied_roots(tmp_path: pathlib.Path) -> pathlib.Path:
    """The real scan roots, copied under a fresh base.

    Copied rather than synthesized so the controls exercise the real files, the
    real enumerator and the real predicate — a synthetic module would prove the
    predicate works on something this guard never reads.
    """
    for relative, _reason in SCAN_ROOTS:
        source = REPO_ROOT / relative
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, destination)
        else:
            shutil.copy(source, destination)
    return tmp_path


@pytest.mark.parametrize(
    "injected",
    [
        pytest.param(
            '\n\nclass ForcedLlmObligation(StrEnum):\n'
            '    REPULL = "re-pull"\n'
            '    ESCALATE = "escalate"\n'
            '    SUPERVISED = "accept-supervised-synthesis"\n',
            id="strenum-of-obligation-names (Pitfall 4)",
        ),
        pytest.param(
            '\n\nObligationName = Literal["re-pull", "escalate"]\n',
            id="literal-alias-of-obligation-names",
        ),
        pytest.param(
            '\n\nclass _Binding:\n'
            '    obligation: Literal["re-pull", "escalate"] = "re-pull"\n',
            id="literal-in-a-field-annotation (the DebtProfile spelling)",
        ),
        pytest.param(
            '\n\n_OBLIGATION_TABLE: tuple[str, ...] = '
            '("re-pull", "escalate", "fail-closed")\n',
            id="tuple-table (the close-panel injection, verbatim)",
        ),
        pytest.param(
            '\n\n_OBLIGATION_TABLE = ["re-pull", "escalate", "fail-closed"]\n',
            id="list-table",
        ),
        pytest.param(
            '\n\n_OBLIGATION_TABLE = frozenset({"re-pull", "escalate"})\n',
            id="frozenset-builder-table",
        ),
        pytest.param(
            '\n\nclass _Binding:\n'
            '    obligations = ("re-pull", "escalate", "fail-closed")\n',
            id="table-as-a-class-attribute",
        ),
    ],
)
def test_the_guard_refuses_an_injected_obligation_vocabulary(
    tmp_path: pathlib.Path, injected: str
) -> None:
    """The guard is verified to REFUSE, not merely to pass.

    The three cases are the three spellings ``15.6-RESEARCH.md`` § B4 and
    Pitfall 4 name between them. The third is the one a plan is most likely to
    write by accident — a field on ``DebtProfile`` whose strings live in the
    *annotation* and never in a value — and it is parametrized separately so
    that narrowing the walk to alias values turns this case red rather than
    turning the whole guard quietly permissive.

    The text is APPENDED rather than prepended: the scanned modules open with a
    docstring followed by ``from __future__ import annotations``, and only a
    docstring and comments may precede a ``__future__`` import, so a prepended
    line would be a syntax error masquerading as a caught violation.
    """
    base = _copied_roots(tmp_path)

    # The copies alone still pass — so the refusal below is the injection.
    refuse_obligation_vocabulary(base)

    target = base / "src/ccf/halflife/assessment.py"
    target.write_text(target.read_text(encoding="utf-8") + injected, "utf-8")

    with pytest.raises(ObligationVocabularyFound) as refusal:
        refuse_obligation_vocabulary(base)

    message = str(refusal.value)
    assert "src/ccf/halflife/assessment.py" in message
    assert "D-IMPL-117" in message, "the failure must name its ruling"
    assert "CLAUDE.md §11" in message, "the failure must name the rule"
    assert "opaque" in message, "the failure must state the remedy"


def test_the_guard_ignores_obligation_words_in_prose(
    tmp_path: pathlib.Path,
) -> None:
    """A docstring or a comment naming an obligation is not a declaration.

    This is why the scan is an AST walk. A grep-shaped gate would fail on
    ``D-IMPL-112``'s own quoted words — which appear in this module's docstring
    and in ``docs/DECISIONS.md`` — and a gate that cries wolf gets switched off.
    """
    base = _copied_roots(tmp_path)
    target = base / "src/ccf/halflife/assessment.py"
    prose = (
        '\n\n# An analyst asks whether forced_llm means re-pull, escalate, or\n'
        '# accept-supervised-synthesis. The SDK does not answer (D-IMPL-117).\n'
        'OBLIGATION_NOTE = "re-pull, escalate, accept-supervised-synthesis"\n'
    )
    target.write_text(target.read_text(encoding="utf-8") + prose, "utf-8")

    refuse_obligation_vocabulary(base)


# ---------------------------------------------------------------------------
# The widening control — the opposite direction, in the shape
# tests/lints/test_deployment_gates_ban.py's third test takes.
# ---------------------------------------------------------------------------


def test_the_guard_did_not_widen_into_a_ban_on_debt_signal() -> None:
    """``DebtSignal`` in its real, unmodified form must still pass.

    A rule that had quietly widened into a general ban on ``StrEnum`` in
    ``src/ccf/halflife/`` would pass every test above and fail this one. The
    widening is not hypothetical: ``DebtSignal`` is a three-member ``StrEnum``
    of lowercase strings in the exact syntactic shape the injected control
    above is refused for, and the only thing separating them is the exemption.

    It must survive because the binding mechanism needs it: ``DebtSignal`` is
    the **key** type an obligation mapping is validated against, so banning it
    would ban gap 3 rather than protect it.
    """
    from ccf.halflife.assessment import DebtSignal

    assert "DebtSignal" in EXEMPT_NAMES

    source = (REPO_ROOT / "src/ccf/halflife/assessment.py").read_text("utf-8")
    raw = _declarations(ast.parse(source), "")
    assert any(name == "DebtSignal" and kind == "enum" for name, kind, _ in raw), (
        "the walk no longer sees DebtSignal as an enum at all — the exemption"
        " is not what is keeping it alive, so this control is not testing"
        " what it claims to test"
    )

    assert not declared_vocabularies(
        REPO_ROOT / "src/ccf/halflife/assessment.py"
    ), "the exemption stopped covering DebtSignal — the rule has widened"

    assert [member.value for member in DebtSignal] == [
        "ok",
        "forced_llm",
        "fail_closed",
    ], "DebtSignal's members changed; the exemption's reason needs re-reading"


@pytest.mark.parametrize(
    "benign",
    [
        pytest.param(
            '\n\n__all__ = ["re_pull", "escalate", "fail_closed"]\n',
            id="__all__ names exports, which are code",
        ),
        pytest.param(
            '\n\nclass _Default:\n'
            '    accepted: frozenset[str] = frozenset({"assembly-stamped"})\n',
            id="a one-member field default is a default, not a choice",
        ),
        pytest.param(
            '\n\ndef _local() -> str:\n'
            '    order = ("freshness", "completeness", "semantic_consistency")\n'
            '    return order[0]\n',
            id="a local inside a function body is not a declaration",
        ),
        pytest.param(
            '\n\n_LIMITS = (1, 2, 3)\n',
            id="a numeric table is cinv01b-numeric-table's job",
        ),
        pytest.param(
            '\n\n_MIXED = ("re-pull", 3)\n',
            id="a mixed table is not a closed string vocabulary",
        ),
    ],
)
def test_the_table_shape_did_not_widen_into_a_ban_on_every_collection(
    tmp_path: pathlib.Path, benign: str
) -> None:
    """The opposite direction, for the shape added at Phase 15.6's close.

    Widening a structural invariant is only an improvement if it refuses more of
    the defect and none of the tree. Each case here is a collection of constants
    that is emphatically **not** an obligation vocabulary, and each corresponds
    to a real shape in the scan roots: ``__all__`` in all five modules,
    ``ProductClassDeclaration``'s one-member ``frozenset`` field defaults, and
    the numeric-table boundary this module has always deferred to
    ``cinv01b-numeric-table``. A guard that had widened into a ban on tuples
    would pass every refusal test and fail here.
    """
    base = _copied_roots(tmp_path)
    target = base / "src/ccf/halflife/assessment.py"
    target.write_text(target.read_text(encoding="utf-8") + benign, "utf-8")

    refuse_obligation_vocabulary(base)


def test_the_walk_sees_the_glob_table_the_exemption_covers() -> None:
    """``_GLOB_CHARACTERS`` must be alive, or its exemption is a named hole.

    :func:`test_the_guard_did_not_widen_into_a_ban_on_debt_signal`'s argument,
    applied to the one exemption the table widening added. The point of asserting
    the walk *does* see it is that the exemption — not a gap in the predicate —
    is what keeps it green. If the predicate later stopped recognizing tuple
    tables, every test above would still pass and the widening would be
    silently undone; this is the case that would not.
    """
    assert "_GLOB_CHARACTERS" in EXEMPT_NAMES

    source = (REPO_ROOT / "src/ccf/controlplane/artifacts.py").read_text("utf-8")
    raw = _declarations(ast.parse(source), "")
    assert any(
        name == "_GLOB_CHARACTERS" and kind == "table" for name, kind, _ in raw
    ), (
        "the walk no longer sees _GLOB_CHARACTERS as a table — the exemption is"
        " not what is keeping it green, so the tuple-shape widening has been"
        " undone and the close-panel B4 injection would pass again"
    )

    assert not declared_vocabularies(
        REPO_ROOT / "src/ccf/controlplane/artifacts.py"
    ), "the exemption stopped covering _GLOB_CHARACTERS — the rule has widened"
