"""cp-04's sixteen declared product gates are DATA, closed, complete and not comment-only.

`D-IMPL-224` makes a product's gates **a declared artifact plus CI coverage**:
no `ProductGate` Protocol, no serve path, and the SDK's universal gates stay
the only serve-time gates. This module is the first half of that on the ladder
— the artifact half. **The COVERAGE half — asserting each declared id has an
EXECUTING test rather than a matching string somewhere — is Phase 24.5's
checker and is deliberately not built here** (`D-24`).

What is asserted, and what each assertion closes
------------------------------------------------

(a) **The roster validates against a CLOSED schema**,
    ``docs/schemas/product-gates/cp.product-gates.json``, with a negative
    control that adds an undeclared key and watches validation fail. A closure
    nobody has watched refuse is a closure that may not be closed.

(b) **The declared id set is exactly the sixteen**, ``CFT-G01`` … ``CFT-G16``,
    asserted as a **ROSTER and never as a count** — a right count with a wrong
    member audits clean forever — and the withdrawn seventeenth id is asserted
    **ABSENT by name, on a code line**. See "The withdrawal" below for why the
    code line matters.

(c) **No gate id appears anywhere as a comment only.** Criterion 43 says
    *anywhere*, and a sweep globbing ``**/*.yaml`` alone would miss an id that
    appears only in a ``#`` comment inside a ``.py`` file — so the scan covers
    **two globs and every extension**.

(d) **Criteria 25 through 40 map one-to-one onto the sixteen gates**, and
    criterion 41 is claimed by no gate.

The withdrawal, and why it is named on a CODE line
---------------------------------------------------

Ontology role 1 — *the walk stops when the neighbor's class is outside the
admitted set* — was STRUCK from this rung on 2026-08-31 (Dave), and the gate
that carried it was WITHDRAWN with it, for two independently measured reasons:
the estate cannot exhibit the stop (`D-32`) and the SDK has no expression for
it (`D-33`). It was **deliberately not replaced by a positive-property
restatement**, which was refused by name as a tautology over a
class-homogeneous population.

Check (c) collects every ``CFT-G`` token found on a **comment line** and
requires each collected id to be **declared**. So writing the withdrawn id into
a comment — here, or in any artifact, or in any sibling test module — would
make this module demand the declaration of the very id the withdrawal forbids.
:data:`WITHDRAWN_ID` is therefore a **code-level constant**, and the one
comment in this file that discusses it does not spell it.

Scope of the comment scan
--------------------------

Two globs, because the modules that execute these gates live **outside** the
example tree:

* ``examples/cp-04-corporate-family-tree/**/*`` — every extension.
* ``tests/examples/test_cp_04_*.py`` — including this module.

Comment syntax is resolved per extension, and the resolution is exact where it
can be:

* ``.py`` — real ``COMMENT`` tokens from :mod:`tokenize`, so a ``#`` inside a
  string literal is not mistaken for a comment. That matters directly: this
  module holds gate ids inside string constants.
* ``.yaml`` / ``.yml`` — a quote-aware line scan, so a ``#`` inside a quoted
  scalar is likewise not a comment.
* ``.md`` / ``.html`` — HTML comment blocks, per the plan's rule. **Markdown
  PROSE is not a comment**, which is why the specification's own withdrawal
  note — which names the withdrawn id five times, in prose — is correctly not
  collected.
* Anything else — **no comment syntax, so nothing is collected**. Stated rather
  than left implicit: in a file with no comment syntax the whole file is
  content, and "appears only as a comment" is not a property such a file can
  have.

The declared side is read by **parsing the YAML**, so comments are stripped by
the parser before the comparison. The check cannot be satisfied by the comment
it is measuring.

Controls
--------

A check nobody has watched fail is a check that may be scanning nothing. Four
run below: the closed schema is shown refusing an undeclared key; the
comment-only rule is shown refusing an id moved out of the declaration and into
a comment; the scan is shown reaching a ``.py`` file **by name**; and the
scan's own non-vacuity is asserted, because a scanner that collected nothing
would satisfy (c) trivially forever.

No substrate marker: this module reads files and needs no container.
"""

from __future__ import annotations

import io
import json
import pathlib
import re
import tokenize

import jsonschema
import pytest
import yaml

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

#: The declaring example.
EXAMPLE_ROOT = REPO_ROOT / "examples" / "cp-04-corporate-family-tree"

#: The roster under test.
GATES_PATH = EXAMPLE_ROOT / "artifacts" / "gates.yaml"

#: The CLOSED schema the roster validates against.
#:
#: **It sits in a SUBDIRECTORY on purpose.** ``tools/dump_schemas.py`` walks the
#: top-level ``docs/schemas/*.json`` glob (`:335`) against the SDK's artifact
#: classes and ``unlink()``s anything that population does not emit (`:399`);
#: ``tests/cli/test_schema_export.py::test_an_orphan_schema_is_drift`` asserts that behavior. The glob is
#: not recursive, so a hand-authored file one level down is outside it and is
#: never destroyed as an orphan. Ruled at Gate 1 (`D-IMPL-225` amendment 3),
#: and it is what stops criterion 43 and criterion 49 contradicting each other.
SCHEMA_PATH = REPO_ROOT / "docs" / "schemas" / "product-gates" / "cp.product-gates.json"

#: The roster, as a roster. Sixteen ids, written out rather than generated from
#: a range, so a reader can see the set this module holds the artifact to
#: without evaluating anything.
EXPECTED_IDS: frozenset[str] = frozenset(
    {
        "CFT-G01",
        "CFT-G02",
        "CFT-G03",
        "CFT-G04",
        "CFT-G05",
        "CFT-G06",
        "CFT-G07",
        "CFT-G08",
        "CFT-G09",
        "CFT-G10",
        "CFT-G11",
        "CFT-G12",
        "CFT-G13",
        "CFT-G14",
        "CFT-G15",
        "CFT-G16",
    }
)

#: The id WITHDRAWN with ontology role 1 on 2026-08-31 (Dave). A code-level
#: constant, never a comment — see this module's docstring.
WITHDRAWN_ID = "CFT-G17"

#: The locked ROADMAP criteria the sixteen gates discharge, one-for-one.
#: Criterion 41 is WITHDRAWN IN PLACE and is claimed by no gate.
EXPECTED_CRITERIA: frozenset[int] = frozenset(range(25, 41))

#: The criterion no gate may claim.
WITHDRAWN_CRITERION = 41

#: Every tree the comment scan reaches. **A root absent from here is a tree
#: this check reports clean over without reading it**, so the second member is
#: not optional: the modules that EXECUTE these gates live outside the example.
SCANNED_GLOBS: tuple[str, ...] = (
    "examples/cp-04-corporate-family-tree/**/*",
    "tests/examples/test_cp_04_*.py",
)

#: Any ``CFT-G``-shaped token, including ones that are not declared — the point
#: is to notice an id that exists ONLY in a comment, so the pattern cannot be
#: narrowed to the declared set.
GATE_TOKEN = re.compile(r"\bCFT-G[0-9]{2}\b")

#: HTML comment blocks, for Markdown and HTML.
HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def load_roster(path: pathlib.Path = GATES_PATH) -> dict:
    """Parse the roster. YAML parsing strips comments, which is the point."""
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_schema(path: pathlib.Path = SCHEMA_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def declared_ids(document: dict) -> set[str]:
    return {gate["id"] for gate in document["declaration"]["gates"]}


# ---------------------------------------------------------------------------
# The comment scan
# ---------------------------------------------------------------------------


def _python_comments(text: str) -> list[str]:
    """Real ``COMMENT`` tokens, so a ``#`` inside a string is not a comment.

    A tokenize failure on a syntactically broken file is not a reason to
    report the file clean, so the fallback is the raw text — which
    over-collects rather than under-collects, and over-collecting only ever
    makes this check stricter.
    """
    try:
        return [
            token.string
            for token in tokenize.generate_tokens(io.StringIO(text).readline)
            if token.type == tokenize.COMMENT
        ]
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return [text]


def _yaml_comments(text: str) -> list[str]:
    """Quote-aware: an unquoted ``#`` starts a comment, a quoted one does not."""
    comments: list[str] = []
    for line in text.splitlines():
        quote: str | None = None
        for index, char in enumerate(line):
            if quote is not None:
                if char == quote:
                    quote = None
            elif char in "'\"":
                quote = char
            elif char == "#":
                comments.append(line[index:])
                break
    return comments


def comments_in(path: pathlib.Path) -> list[str]:
    """Every comment in ``path``, resolved by extension. See the docstring."""
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []

    suffix = path.suffix.lower()
    if suffix == ".py":
        return _python_comments(text)
    if suffix in {".yaml", ".yml"}:
        return _yaml_comments(text)
    if suffix in {".md", ".html", ".htm"}:
        return HTML_COMMENT.findall(text)
    return []


def scanned_files(root: pathlib.Path = REPO_ROOT) -> list[pathlib.Path]:
    found: set[pathlib.Path] = set()
    for pattern in SCANNED_GLOBS:
        found |= {path for path in root.glob(pattern) if path.is_file()}
    return sorted(found)


def comment_borne_ids(root: pathlib.Path = REPO_ROOT) -> dict[str, set[str]]:
    """Map each ``CFT-G`` id found in a comment to the files it was found in.

    The file names travel with the ids so a failure NAMES the file, rather
    than reporting that something somewhere mentions an id.
    """
    found: dict[str, set[str]] = {}
    for path in scanned_files(root):
        for comment in comments_in(path):
            for token in GATE_TOKEN.findall(comment):
                found.setdefault(token, set()).add(
                    str(path.relative_to(root))
                    if path.is_relative_to(root)
                    else str(path)
                )
    return found


# ---------------------------------------------------------------------------
# (a) The closed schema
# ---------------------------------------------------------------------------


def test_the_roster_validates_against_the_closed_schema() -> None:
    jsonschema.validate(instance=load_roster(), schema=load_schema())


def test_the_schema_closes_every_object_level() -> None:
    """`additionalProperties: false` at the root, the declaration, each gate,
    and the `observed_red` record — asserted structurally, because a schema
    that is closed at the root and open two levels down reads as closed."""
    schema = load_schema()
    declaration = schema["properties"]["declaration"]
    gate = declaration["properties"]["gates"]["items"]
    observed = next(
        option
        for option in gate["properties"]["observed_red"]["oneOf"]
        if option.get("type") == "object"
    )
    for level, document in (
        ("root", schema),
        ("declaration", declaration),
        ("gate", gate),
        ("observed_red", observed),
    ):
        assert document.get("additionalProperties") is False, (
            f"the {level} object level is not closed — a schema closed at the"
            " root and open below it reads as closed while accepting anything"
        )


def test_the_schema_requires_the_six_gate_fields() -> None:
    gate = load_schema()["properties"]["declaration"]["properties"]["gates"]["items"]
    assert set(gate["required"]) == {
        "id",
        "statement",
        "criterion",
        "test",
        "sabotage",
        "observed_red",
    }


def test_observed_red_is_required_as_a_key_and_may_be_null() -> None:
    """A gate that has never been sabotaged must be VISIBLY unsabotaged.

    Required-and-nullable rather than optional: an omitted key looks like a
    gate with nothing left to do, where an explicit `null` says the obligation
    is outstanding. Fourteen declared gates once sat idle on this ladder behind
    exactly that ambiguity.
    """
    gate = load_schema()["properties"]["declaration"]["properties"]["gates"]["items"]
    assert "observed_red" in gate["required"]
    assert {option.get("type") for option in gate["properties"]["observed_red"]["oneOf"]} == {
        "null",
        "object",
    }


# --- Control: the closure is proven able to refuse. ------------------------


@pytest.mark.parametrize(
    ("where", "mutate"),
    [
        (
            "the root",
            lambda d: d.update({"undeclared_root_key": "x"}),
        ),
        (
            "the declaration",
            lambda d: d["declaration"].update({"undeclared_declaration_key": "x"}),
        ),
        (
            "a gate",
            lambda d: d["declaration"]["gates"][0].update({"undeclared_gate_key": "x"}),
        ),
        (
            "an observed_red record",
            lambda d: d["declaration"]["gates"][0].update(
                {
                    "observed_red": {
                        "result": "RED",
                        "date": "2026-08-31",
                        "commit": "0000000",
                        "undeclared_observation_key": "x",
                    }
                }
            ),
        ),
    ],
)
def test_an_undeclared_key_is_refused(where: str, mutate) -> None:
    """The negative control, at every closed level rather than only the root."""
    document = load_roster()
    mutate(document)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=document, schema=load_schema())
    assert where  # named in the parametrization so a failure says which level


def test_a_gate_missing_its_observed_red_key_is_refused() -> None:
    document = load_roster()
    del document["declaration"]["gates"][0]["observed_red"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=document, schema=load_schema())


def test_a_test_reference_without_a_function_is_refused() -> None:
    """A path with no `::` names a module, not a test."""
    document = load_roster()
    document["declaration"]["gates"][0]["test"] = "tests/examples/test_cp_04_traversal.py"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=document, schema=load_schema())


# ---------------------------------------------------------------------------
# (b) The roster, and the withdrawal
# ---------------------------------------------------------------------------


def test_the_declared_ids_are_exactly_the_sixteen() -> None:
    """A ROSTER, not a count. A right count with a wrong member audits clean."""
    declared = declared_ids(load_roster())
    assert declared == EXPECTED_IDS, (
        f"missing: {sorted(EXPECTED_IDS - declared)};"
        f" unexpected: {sorted(declared - EXPECTED_IDS)}"
    )


def test_no_id_is_declared_twice() -> None:
    ids = [gate["id"] for gate in load_roster()["declaration"]["gates"]]
    assert len(ids) == len(set(ids)), f"duplicate ids: {sorted(ids)}"


def test_the_withdrawn_id_is_not_declared() -> None:
    """Asserted BY NAME, on a code line. See this module's docstring."""
    assert WITHDRAWN_ID not in declared_ids(load_roster())


def test_the_withdrawn_id_appears_nowhere_in_the_roster_document() -> None:
    """Not as a gate, not as a comment, not as prose inside the artifact.

    Stronger than the parsed-side check above and deliberately so: the
    withdrawal is *"not declared, not as a gate and not as a comment"*, and the
    parsed side cannot see a comment at all.
    """
    assert WITHDRAWN_ID not in GATES_PATH.read_text(encoding="utf-8")


def test_every_gate_carries_a_statement_and_a_sabotage() -> None:
    """A gate with no named sabotage is a gate nobody can watch fail."""
    for gate in load_roster()["declaration"]["gates"]:
        assert gate["statement"].strip(), gate["id"]
        assert gate["sabotage"].strip(), gate["id"]


def test_no_gate_is_yet_recorded_as_observed_red() -> None:
    """The state plan `24.4-03` leaves the roster in, asserted rather than assumed.

    Plans `24.4-10`, `24.4-11` and `24.4-12` fill these in as they apply each
    sabotage and watch the failure. **This assertion is expected to be EDITED by
    those plans, not deleted** — it is the wave-3 boundary written down, so a
    later reader can tell an unsabotaged roster from a roster whose records were
    lost.
    """
    unfilled = [
        gate["id"]
        for gate in load_roster()["declaration"]["gates"]
        if gate["observed_red"] is None
    ]
    assert sorted(unfilled) == sorted(EXPECTED_IDS)


# ---------------------------------------------------------------------------
# (c) No id is comment-only
# ---------------------------------------------------------------------------


def test_the_comment_scan_reads_something() -> None:
    """Non-vacuity. A scanner that collected nothing satisfies (c) forever."""
    files = scanned_files()
    assert files, f"the globs {SCANNED_GLOBS} matched no files"
    collected = comment_borne_ids()
    assert collected, (
        "no gate id was found in any comment across"
        f" {len(files)} scanned files — the scan is reading nothing"
    )


def test_the_comment_scan_reaches_both_globs() -> None:
    """Each glob contributes files, asserted separately.

    The second glob is the one that would go silent unnoticed: the modules
    executing these gates live outside the example tree, so a scan narrowed to
    ``examples/`` would report clean over every one of them.
    """
    for pattern in SCANNED_GLOBS:
        matched = [path for path in REPO_ROOT.glob(pattern) if path.is_file()]
        assert matched, f"the glob {pattern!r} matched no files"


def test_the_comment_scan_is_not_restricted_to_yaml() -> None:
    """More than one extension is actually read, not merely permitted."""
    extensions = {
        path.suffix.lower() for path in scanned_files() if comments_in(path)
    }
    assert {".yaml", ".py"} <= extensions, (
        f"the scan drew comments from {sorted(extensions)} only —"
        " criterion 43 says ANYWHERE, and an id in a `.py` comment counts"
    )


def test_no_gate_id_appears_only_as_a_comment() -> None:
    declared = declared_ids(load_roster())
    stray = {
        token: sorted(files)
        for token, files in comment_borne_ids().items()
        if token not in declared
    }
    assert not stray, (
        "these gate ids appear in a comment but are declared nowhere: "
        + "; ".join(f"{token} in {files}" for token, files in sorted(stray.items()))
    )


# --- Control: the comment-only rule is proven able to refuse. --------------


def test_an_id_moved_into_a_comment_and_out_of_the_declaration_is_caught(
    tmp_path: pathlib.Path,
) -> None:
    """The control the acceptance criteria name, run over a synthetic tree.

    A copy of the real roster with one gate REMOVED, and that gate's id written
    into a ``#`` comment in a sibling file — which is exactly the state
    criterion 43 forbids: an id that looks covered because it is mentioned, and
    is declared nowhere.
    """
    tree = tmp_path / "examples" / "cp-04-corporate-family-tree" / "artifacts"
    tree.mkdir(parents=True)

    document = load_roster()
    removed = document["declaration"]["gates"].pop()
    (tree / "gates.yaml").write_text(yaml.safe_dump(document), encoding="utf-8")
    (tree / "notes.yaml").write_text(
        f"# this file mentions {removed['id']} and declares nothing\nkey: value\n",
        encoding="utf-8",
    )

    collected = comment_borne_ids(tmp_path)
    declared = declared_ids(yaml.safe_load((tree / "gates.yaml").read_text("utf-8")))
    stray = {token for token in collected if token not in declared}
    assert stray == {removed["id"]}, (
        f"expected the comment-only rule to name {removed['id']}, got {stray}"
    )


def test_the_scan_names_the_python_file_a_planted_id_hides_in(
    tmp_path: pathlib.Path,
) -> None:
    """Scope control: a ``.py`` comment is reached, and the FILE is named.

    Two halves, and the second is the one worth having. The id is planted in a
    ``#`` comment in a ``.py`` file and also, as a decoy, inside a STRING in the
    same file. If the scan reported the file for the string it would be reading
    text rather than comments — and this module itself holds gate ids in
    strings, so that distinction is not hypothetical.
    """
    tests = tmp_path / "tests" / "examples"
    tests.mkdir(parents=True)
    planted = "CFT-G99"
    decoy = "CFT-G98"
    (tests / "test_cp_04_planted.py").write_text(
        f'# a comment naming {planted}\nNAME = "{decoy} lives in a string"\n',
        encoding="utf-8",
    )

    collected = comment_borne_ids(tmp_path)
    assert planted in collected, f"the `.py` comment was not read: {collected}"
    assert collected[planted] == {"tests/examples/test_cp_04_planted.py"}
    assert decoy not in collected, (
        f"{decoy} was collected from a STRING literal — the scan is reading"
        " text, not comments"
    )


def test_markdown_prose_is_not_a_comment(tmp_path: pathlib.Path) -> None:
    """Why the specification's own withdrawal note is correctly not collected.

    The withdrawn id appears five times in ``CP-SPEC-004``, in PROSE. Markdown
    prose is content, so it is not collected — and if it were, this module would
    be demanding the declaration of an id whose withdrawal is the thing that
    prose explains.
    """
    tree = tmp_path / "examples" / "cp-04-corporate-family-tree"
    tree.mkdir(parents=True)
    (tree / "spec.md").write_text(
        f"{WITHDRAWN_ID} is withdrawn.\n\n<!-- CFT-G97 sits in an HTML comment -->\n",
        encoding="utf-8",
    )
    collected = comment_borne_ids(tmp_path)
    assert WITHDRAWN_ID not in collected, "Markdown prose was read as a comment"
    assert "CFT-G97" in collected, "an HTML comment block was not read"


# ---------------------------------------------------------------------------
# (d) The criteria bijection
# ---------------------------------------------------------------------------


def test_the_criteria_map_one_to_one_onto_the_gates() -> None:
    claimed = [gate["criterion"] for gate in load_roster()["declaration"]["gates"]]
    assert set(claimed) == EXPECTED_CRITERIA, (
        f"unclaimed: {sorted(EXPECTED_CRITERIA - set(claimed))};"
        f" out of range: {sorted(set(claimed) - EXPECTED_CRITERIA)}"
    )
    assert len(claimed) == len(set(claimed)), (
        f"a criterion is claimed by more than one gate: {sorted(claimed)}"
    )


def test_the_withdrawn_criterion_is_claimed_by_no_gate() -> None:
    """Criterion 41 is WITHDRAWN IN PLACE with ontology role 1."""
    claimed = {gate["criterion"] for gate in load_roster()["declaration"]["gates"]}
    assert WITHDRAWN_CRITERION not in claimed
