"""`D-IMPL-141` (RESOLVED) — the binding document, and the refusals it owes.

`binding.yaml` is **data**, with exactly one permitted `<module>:<attribute>`
reference: `plan:`, the projection. Amendment A.3 of
``docs/superpowers/specs/2026-08-16-reference-plan-factory-and-debt-scorer.md``
grants that exception; A.4 requires a mechanism that keeps it from widening, and
the sentence the amendment rests on is *"an exception with no mechanism holding
it narrow is not an exception; it is a precedent."*

**This module is that mechanism's test, and it is built to the phase's hard-won
shape.** Every assertion is a module-level function taking its subject as a
**parameter**, so a sabotage control can hand the *shipped* assertion a
deliberately divergent subject and be watched failing. An assertion re-written
inside a control proves nothing about the assertion that ships.

**Every refusal here is asserted on its message, not just on its type.** A
binding document is deployment wiring authored by hand, and the failures below
are the ones an adopter will actually hit — a key that was ruled out, a
reference smuggled into a data position, a module that does not import. A
refusal that says only "BindingError" costs the reader the diagnosis the loader
already performed.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import pytest
import yaml

from ccf.client.adapters.binding_document import (
    BINDING_DOCUMENT_NAME,
    DATA_KEYS,
    OPTIONAL_KEYS,
    REFERENCE_KEYS,
    RULED_OUT_KEYS,
    conforming_plan_factory,
    load_binding_document,
    load_reference,
    looks_like_a_reference,
)
from ccf.client.errors import BindingError, TransportError

from tests.client.conftest import FIXTURE_DEPLOYMENT
from tests.client.fixtures import STDIO_SERVER

#: The shipped example's deployment root and its server program, reached from
#: this file rather than from a constant in the examples suite, because the
#: claim under test is the **loader's** and this is where the loader is tested.
HW1 = Path(__file__).resolve().parents[2] / "examples" / "hw1-companies-over-revenue"

#: Every key a valid document must state. Derived from the module's own
#: constants rather than copied, so a new key cannot arrive without the
#: absence-refusal test below covering it.
REQUIRED_KEYS: tuple[str, ...] = (*DATA_KEYS, *REFERENCE_KEYS)


def _document(root: Path) -> dict[str, Any]:
    return dict(
        yaml.safe_load((root / BINDING_DOCUMENT_NAME).read_text(encoding="utf-8"))
    )


def _rewrite(root: Path, body: dict[str, Any]) -> None:
    (root / BINDING_DOCUMENT_NAME).write_text(yaml.safe_dump(body), encoding="utf-8")


# ---------------------------------------------------------------------------
# THE NARROWING GATE — Amendment A.4 criterion 3'.
#
# Shipped as two functions taking the deployment root as a parameter, because
# the controls below feed each of them a divergent root. A gate that could only
# be run against the one committed fixture would be a gate nobody could prove
# fires.
# ---------------------------------------------------------------------------


def assert_one_python_module(root: Path) -> None:
    """The deployment holds **exactly one** Python module.

    Criterion 3′: *"`ccf_config.yaml`, a data-only `binding.yaml`, and exactly
    one Python module — the projection."*

    ``!= 1`` rather than ``> 1``, deliberately. A count check written as *"no
    more than one"* passes on **zero**, which is this phase's signature defect —
    a check that stops checking without going red. Zero modules means the
    ``plan:`` reference resolves to nothing, which is a broken deployment, not a
    purer one.
    """
    modules = sorted(path.name for path in root.glob("*.py"))
    if len(modules) != 1:
        raise AssertionError(
            f"the deployment at {root} holds {len(modules)} Python modules"
            f" {modules}, not exactly one — Amendment A.3 grants this deployment"
            " one module, the projection, and grants it nothing else"
        )


def assert_the_module_defines_only_the_named_reference(root: Path) -> None:
    """That one module's public surface is **exactly** what ``plan:`` names.

    This is the half of criterion 3′ a file count cannot reach. One module doing
    five things is the 295-line ``resolver.py`` this ruling replaced, and it
    would satisfy a count of one perfectly.

    Read by :mod:`ast` rather than by import: importing would execute the
    deployment's Python to measure it, and a gate that runs its subject to check
    it is a gate that a subject can influence.

    The comparison is against a **list**, so an empty module fails as loudly as
    a crowded one — ``[] != ["build_projection"]``.
    """
    document = load_binding_document(root)
    module_path, _, attribute = document.plan.partition(":")
    tree = ast.parse((root / module_path.strip()).read_text(encoding="utf-8"))
    public = sorted(
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)
        and not node.name.startswith("_")
    )
    if public != [attribute.strip()]:
        raise AssertionError(
            f"{root / module_path.strip()} defines the public names {public},"
            f" not exactly [{attribute.strip()!r}] — the one module a deployment"
            " may write exposes exactly the one attribute `plan:` names: no"
            " fewer, no more, and no other. A second public name is a second"
            " responsibility arriving where the ruling granted one; none at all"
            " is a `plan:` reference that resolves to nothing"
        )


def test_the_committed_fixture_satisfies_every_gate(deployment_root: Path) -> None:
    """The honest subject passes both assertions.

    First, and not a formality: without it, every control below could be
    satisfied by assertions that refuse everything.
    """
    assert_one_python_module(deployment_root)
    assert_the_module_defines_only_the_named_reference(deployment_root)


def test_the_one_module_gate_fires_on_a_second_module(deployment_root: Path) -> None:
    """CONTROL — a second module appears. The exception has widened."""
    (deployment_root / "resolver.py").write_text(
        "def build_resolver() -> None: ...\n", encoding="utf-8"
    )

    with pytest.raises(AssertionError) as fired:
        assert_one_python_module(deployment_root)

    message = str(fired.value)
    assert "2 Python modules" in message
    assert "projection.py" in message and "resolver.py" in message


def test_the_one_module_gate_fires_on_zero_modules(tmp_path: Path) -> None:
    """CONTROL — **the empty case**, which a ``> 1`` check would pass.

    This is the control that matters most. Four defects in this phase were a
    discovery primitive matching nothing and reporting success; a count gate
    written the lenient way would join them.
    """
    empty = tmp_path / "no-modules"
    empty.mkdir()

    with pytest.raises(AssertionError) as fired:
        assert_one_python_module(empty)

    assert "0 Python modules" in str(fired.value)


def test_the_responsibility_gate_fires_on_a_second_public_name(
    deployment_root: Path,
) -> None:
    """CONTROL — one module, two responsibilities. The count gate cannot see it."""
    module = deployment_root / "projection.py"
    module.write_text(
        module.read_text(encoding="utf-8")
        + "\n\ndef build_resolver() -> None:\n    \"\"\"A second job.\"\"\"\n",
        encoding="utf-8",
    )

    assert_one_python_module(deployment_root)  # still one file — the point

    with pytest.raises(AssertionError) as fired:
        assert_the_module_defines_only_the_named_reference(deployment_root)

    message = str(fired.value)
    assert "build_resolver" in message
    assert "second responsibility" in message


def test_the_responsibility_gate_fires_on_an_empty_module(
    deployment_root: Path,
) -> None:
    """CONTROL — **the empty case** for the responsibility half.

    A module defining nothing has no public names at all, and a gate comparing
    against a subset rather than an equality would pass it.
    """
    (deployment_root / "projection.py").write_text("", encoding="utf-8")

    with pytest.raises(AssertionError) as fired:
        assert_the_module_defines_only_the_named_reference(deployment_root)

    assert "defines the public names []" in str(fired.value)


def test_the_responsibility_gate_fires_when_the_reference_is_renamed(
    deployment_root: Path,
) -> None:
    """CONTROL — the module and the document disagree about the one name."""
    body = _document(deployment_root)
    body["plan"] = "projection.py:build_something_else"
    _rewrite(deployment_root, body)

    with pytest.raises(AssertionError) as fired:
        assert_the_module_defines_only_the_named_reference(deployment_root)

    assert "build_something_else" in str(fired.value)


# ---------------------------------------------------------------------------
# The committed fixture is a valid document — asserted first, because every
# refusal below mutates it.
# ---------------------------------------------------------------------------


def test_binding_document_loads_the_committed_fixture(deployment_root: Path) -> None:
    """The fixture deployment states a document this loader accepts.

    A precondition, not a formality: every refusal test below mutates this
    document, so if the unmutated form did not load, each of them would be
    asserting that a broken document is broken.
    """
    document = load_binding_document(deployment_root)

    assert document.root == deployment_root.resolve()
    assert document.config == (deployment_root / "ccf_config.yaml").resolve()
    assert document.plan == "projection.py:build_projection"
    assert document.question.subject == "fixture-widgets"
    assert document.perspective.role == "fixture-role"
    assert document.artifact_store == (deployment_root / "artifact-store").resolve()
    assert document.connection == {
        "database_path": str((deployment_root / "graph.sqlite3").resolve())
    }


def test_the_document_carries_exactly_one_reference(deployment_root: Path) -> None:
    """Measured on the document, not asserted about it.

    Amendment A.3 grants **one** ``module:attribute`` reference. This walks
    every value the committed fixture states and counts the reference-shaped
    ones through the shipped predicate.
    """
    body = _document(deployment_root)

    def references(value: Any, position: str) -> list[str]:
        if isinstance(value, dict):
            return [
                found
                for key, nested in value.items()
                for found in references(nested, f"{position}.{key}")
            ]
        if isinstance(value, list):
            return [
                found
                for index, nested in enumerate(value)
                for found in references(nested, f"{position}[{index}]")
            ]
        return [position] if looks_like_a_reference(value) else []

    found = [
        position
        for key, value in body.items()
        for position in references(value, str(key))
    ]

    assert found == list(REFERENCE_KEYS)
    assert len(REFERENCE_KEYS) == 1, "widening this is a decision, not an edit"


def test_binding_document_resolves_a_relative_root_to_an_absolute_one(
    deployment_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``./deployment`` and its absolute spelling parse to one root.

    This is the property the in-process boot cache keys on (``D-30``), asserted
    here at the loader because this is where the resolution happens.
    """
    monkeypatch.chdir(deployment_root.parent)

    relative = load_binding_document("./deployment")
    absolute = load_binding_document(deployment_root)

    assert relative.root == absolute.root == deployment_root.resolve()


# ---------------------------------------------------------------------------
# The refusals that keep the exception narrow.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("ruled_out", sorted(RULED_OUT_KEYS))
def test_binding_document_refuses_a_ruled_out_key_by_name(
    deployment_root: Path, ruled_out: str
) -> None:
    """A key `D-IMPL-141` **ruled out** is refused as such, not as unknown.

    The two are different mistakes with different remedies. Told *"not a
    binding-document key"*, an author of the rejected shape re-spells it; told
    *"ruled out"* with the spec named, they read the ruling.
    """
    body = _document(deployment_root)
    body[ruled_out] = "resolver.py:build_resolver"
    _rewrite(deployment_root, body)

    with pytest.raises(BindingError) as refused:
        load_binding_document(deployment_root)

    message = str(refused.value)
    assert f"`{ruled_out}`" in message
    assert "ruled out" in message
    assert "2026-08-16-reference-plan-factory" in message, "and points at the ruling"


@pytest.mark.parametrize(
    "position",
    [
        "product_class_key",
        "question.subject",
        "perspective.role",
        "operator_parameter_keys[0]",
        "connection.database_path",
    ],
)
def test_binding_document_refuses_a_reference_in_a_data_position(
    deployment_root: Path, position: str
) -> None:
    """**The narrowing.** A reference under a permitted key is still refused.

    Refusing unknown *keys* cannot see this: every position below is a key the
    schema permits. Without this check the exception widens through the
    schema's own vocabulary and no decision is ever recorded.
    """
    body = _document(deployment_root)
    smuggled = "sneaky.py:build_resolver"
    if position == "product_class_key":
        body["product_class_key"] = smuggled
    elif position == "question.subject":
        body["question"]["subject"] = smuggled
    elif position == "perspective.role":
        body["perspective"]["role"] = smuggled
    elif position == "operator_parameter_keys[0]":
        body["operator_parameter_keys"] = [smuggled]
    else:
        body["connection"]["database_path"] = smuggled
    _rewrite(deployment_root, body)

    with pytest.raises(BindingError) as refused:
        load_binding_document(deployment_root)

    message = str(refused.value)
    assert f"`{position}: {smuggled}`" in message, "the refusal names the position"
    assert "data** position" in message
    assert "`plan`" in message, "and names the one key a reference may sit under"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("projection.py:build_projection", True),
        ("nested/dir/plan.py:factory", True),
        ("projection.py:", False),
        (":build_projection", False),
        ("projection.py", False),
        ("fixture-widgets", False),
        ("2026-03-02T12:00:00+00:00", False),
        ("temporal.as-of-boundary", False),
        (3600, False),
        (None, False),
    ],
)
def test_looks_like_a_reference_is_narrow_enough_to_be_usable(
    value: object, expected: bool
) -> None:
    """The predicate's own table, including the case that would break it.

    ``asked_at`` carries three colons and is **data**. A predicate written as
    *"contains a colon"* would refuse every declared instant in the document, so
    the shape checked is *names a Python file* — which is the property that
    makes a value executable and therefore the property worth refusing.
    """
    assert looks_like_a_reference(value) is expected


def test_binding_document_refuses_an_unknown_key_by_name(
    deployment_root: Path,
) -> None:
    """An unknown top-level key is refused, and the refusal names it."""
    body = _document(deployment_root)
    body["plans"] = "projection.py:build_projection"
    _rewrite(deployment_root, body)

    with pytest.raises(BindingError) as refused:
        load_binding_document(deployment_root)

    message = str(refused.value)
    assert "`plans`" in message, "the refusal names the offending key itself"
    for key in (*DATA_KEYS, *REFERENCE_KEYS, *OPTIONAL_KEYS):
        assert f"`{key}`" in message, "and enumerates what the keys actually are"


@pytest.mark.parametrize("omitted", REQUIRED_KEYS)
def test_binding_document_refuses_a_missing_required_key(
    deployment_root: Path, omitted: str
) -> None:
    """A required key is absent, and the refusal names *which*.

    Parameterized over the module's own constants rather than over a copy, so a
    new required key cannot arrive without a test for its absence.
    """
    body = _document(deployment_root)
    del body[omitted]
    _rewrite(deployment_root, body)

    with pytest.raises(BindingError) as refused:
        load_binding_document(deployment_root)

    message = str(refused.value)
    assert f"`{omitted}`" in message
    assert BINDING_DOCUMENT_NAME in message


def test_binding_document_refuses_an_empty_required_value(
    deployment_root: Path,
) -> None:
    """A key stated with no value is as absent as a key never stated."""
    body = _document(deployment_root)
    body["plan"] = "   "
    _rewrite(deployment_root, body)

    with pytest.raises(BindingError) as refused:
        load_binding_document(deployment_root)

    assert "`plan`" in str(refused.value)


# `asked_at` left this list on 2026-08-16: it became OPTIONAL when `BL-02`
# stopped any code path reading it (Dave's ruling, the narrow amendment to
# `D-IMPL-141`'s data shape). The three that remain are still required, and
# `test_binding_document_refuses_a_zone_less_asked_at` below still holds a
# DECLARED instant to the same standard — optional is not unvalidated.
@pytest.mark.parametrize("field", ["subject", "intent", "freshness"])
def test_binding_document_refuses_an_incomplete_question(
    deployment_root: Path, field: str
) -> None:
    """The declared question is refused field by field, not as a blob."""
    body = _document(deployment_root)
    del body["question"][field]
    _rewrite(deployment_root, body)

    with pytest.raises(BindingError) as refused:
        load_binding_document(deployment_root)

    assert f"`{field}`" in str(refused.value)


def test_binding_document_refuses_a_zone_less_asked_at(deployment_root: Path) -> None:
    """A zone-less instant is a silent default (``D-IMPL-38``), so it is refused.

    Which zone it silently meant is the difference between two different
    answers, and a fabric that guessed would serve one of them with a content
    address nobody could reproduce.
    """
    body = _document(deployment_root)
    body["question"]["asked_at"] = "2026-03-02T12:00:00"
    _rewrite(deployment_root, body)

    with pytest.raises(BindingError) as refused:
        load_binding_document(deployment_root)

    assert "no time" in str(refused.value)


def test_binding_document_accepts_a_question_that_omits_asked_at(
    deployment_root: Path,
) -> None:
    """``asked_at`` is OPTIONAL, and a document omitting it loads.

    It was required until 2026-08-16 and stopped being read when ``BL-02`` made
    ``as_of=None`` resolve to the server's clock rather than to this literal.
    Dave ruled the same day that a required field no code path reads is a latent
    defect, so the requirement was dropped — the narrow amendment to
    ``D-IMPL-141``'s data shape.

    This asserts the *absence* path specifically. The optionality is otherwise
    invisible: every fixture in the tree declares the field, so a loader that
    had gone on requiring it would pass the whole suite, and the change Dave
    ruled would have been recorded in prose and not in behaviour.
    """
    body = _document(deployment_root)
    removed = body["question"].pop("asked_at")
    assert removed, "the fixture must declare it, or this proves nothing"
    _rewrite(deployment_root, body)

    document = load_binding_document(deployment_root)

    assert document.question.asked_at is None
    assert document.question.subject, "the rest of the question still loads"


def test_binding_document_refuses_a_float_ttl(deployment_root: Path) -> None:
    """A TTL silently rounded is a governance figure nobody authored."""
    body = _document(deployment_root)
    body["max_ttl_seconds"] = 3600.5
    _rewrite(deployment_root, body)

    with pytest.raises(BindingError) as refused:
        load_binding_document(deployment_root)

    assert "whole number of seconds" in str(refused.value)


def test_binding_document_refuses_a_root_with_no_document(tmp_path: Path) -> None:
    """No ``binding.yaml`` at the root the address named."""
    empty = tmp_path / "not-a-deployment"
    empty.mkdir()

    with pytest.raises(BindingError) as refused:
        load_binding_document(empty)

    message = str(refused.value)
    assert BINDING_DOCUMENT_NAME in message
    assert str(empty) in message
    for key in REQUIRED_KEYS:
        assert key in message, "the refusal names what to state, not just what is absent"


def test_binding_document_refuses_a_root_that_is_not_a_directory(
    tmp_path: Path,
) -> None:
    """An address naming a file, or nothing at all, is not a deployment root."""
    with pytest.raises(BindingError) as refused:
        load_binding_document(tmp_path / "nowhere")

    assert "not a deployment root" in str(refused.value)


def test_binding_document_refuses_a_document_that_is_not_a_mapping(
    deployment_root: Path,
) -> None:
    """A document that parsed to a scalar or a list has no keys to read."""
    (deployment_root / BINDING_DOCUMENT_NAME).write_text(
        "- config\n- plan\n", encoding="utf-8"
    )

    with pytest.raises(BindingError) as refused:
        load_binding_document(deployment_root)

    assert "not a mapping" in str(refused.value)


def test_binding_document_refuses_a_config_path_that_does_not_exist(
    deployment_root: Path,
) -> None:
    """``config:`` naming nothing is caught here, not at boot."""
    body = _document(deployment_root)
    body["config"] = "absent.yaml"
    _rewrite(deployment_root, body)

    with pytest.raises(BindingError) as refused:
        load_binding_document(deployment_root)

    message = str(refused.value)
    assert "absent.yaml" in message
    assert "does not exist" in message


def test_binding_document_refuses_a_malformed_connection_setting(
    deployment_root: Path,
) -> None:
    """A connection value is a scalar or ``{path: …}``, and nothing else."""
    body = _document(deployment_root)
    body["connection"]["database_path"] = {"host": "somewhere"}
    _rewrite(deployment_root, body)

    with pytest.raises(BindingError) as refused:
        load_binding_document(deployment_root)

    assert "`host`" in str(refused.value)


# ---------------------------------------------------------------------------
# Containment — the rule a manifest already lives under.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "escaping", ["../outside.yaml", "/etc/passwd", "nested/../../outside.yaml"]
)
@pytest.mark.parametrize("key", ["config", "artifact_store"])
def test_binding_document_refuses_a_path_leaving_the_deployment(
    deployment_root: Path, escaping: str, key: str
) -> None:
    """Containment: a binding document is trusted no further than a manifest.

    ``T-17-19`` accepts that loading the one reference runs the deployment's
    Python — the deployment root is its own trust boundary. What is *not*
    accepted is a document reaching outside the deployment it describes.

    Parameterized across both keys rooted at the deployment, because a rule
    enforced on one of two paths is a rule with a way around it. There is now a
    **third** path-valued key, `server:`, and it is not a limb here: it resolves
    against the deployment root's parent and its refusal must say so, which is
    the one assertion below it cannot share. Its limbs are the sibling test
    further down, and the rule still has no way around it.
    """
    body = _document(deployment_root)
    body[key] = escaping
    _rewrite(deployment_root, body)

    with pytest.raises(BindingError) as refused:
        load_binding_document(deployment_root)

    assert "outside the deployment root" in str(refused.value)


def test_binding_document_refuses_a_connection_path_leaving_the_deployment(
    deployment_root: Path,
) -> None:
    """The rooted connection form is contained too, or it is a way out."""
    body = _document(deployment_root)
    body["connection"]["database_path"] = {"path": "../elsewhere.sqlite3"}
    _rewrite(deployment_root, body)

    with pytest.raises(BindingError) as refused:
        load_binding_document(deployment_root)

    assert "outside the deployment root" in str(refused.value)


def test_binding_document_refuses_a_symlink_out_of_the_deployment(
    deployment_root: Path, tmp_path: Path
) -> None:
    """The second containment check, which the first cannot cover.

    A plain name with no ``..`` and no leading ``/`` passes the string check and
    still lands outside once resolved. Both checks exist because neither covers
    the other — and this is the one a reader is most likely to think redundant.
    """
    outside = tmp_path / "outside.yaml"
    outside.write_text("semver: '1.0.0'\n", encoding="utf-8")
    (deployment_root / "sneaky.yaml").symlink_to(outside)
    body = _document(deployment_root)
    body["config"] = "sneaky.yaml"
    _rewrite(deployment_root, body)

    with pytest.raises(BindingError) as refused:
        load_binding_document(deployment_root)

    assert "outside the deployment root" in str(refused.value)


# ---------------------------------------------------------------------------
# `server:` — the one key whose base is the deployment root's PARENT.
#
# `D-10` (Dave, 2026-08-18). A deployment's server program is not deployment
# content: the ordinary deployment is reached by an endpoint and declares no
# `server:` at all, and a rule forcing the program inside the root would teach
# that a server belongs in a deployment, which is false.
#
# Containment keeps every rule it had — only the base moved. The limbs below
# therefore assert the base the loader ACTUALLY used, and assert that the
# refusal does NOT say `the deployment root`: a `server:` limb passing on that
# string would prove the base description was never threaded through, which is
# the `B0b` report-quality defect wearing a green tick.
# ---------------------------------------------------------------------------

#: What a `server:` refusal must say, and what it must not. Written once,
#: because the whole point of the pair is that they are checked together.
SERVER_BASE_DESCRIPTION = "the directory holding this deployment"
ROOT_BASE_DESCRIPTION = "the deployment root"


def assert_the_refusal_named_the_parent_as_the_base(message: str) -> None:
    """A `server:` containment refusal describes the base it actually used.

    Both halves are load-bearing and neither covers the other. The positive
    half catches a call site that passed no description; the negative half
    catches one that passed the *default* — which is the failure mode that
    reads as a pass, because `_contained`'s default is exactly the wrong
    sentence for this key.
    """
    assert SERVER_BASE_DESCRIPTION in message, (
        "a `server:` refusal names the directory holding the deployment,"
        " because that is the base the loader resolved against"
    )
    assert ROOT_BASE_DESCRIPTION not in message, (
        "and never the deployment root — `server:` is not resolved against it,"
        " and a message saying so sends an adopter to the wrong directory"
    )


def test_a_server_declaration_resolves_against_the_deployments_parent(
    deployment_root: Path,
) -> None:
    """`V-04` — the positive case, and the one that fixes the base.

    The program sits beside the deployment, not inside it, so the value is read
    relative to the directory holding the deployment.
    """
    program = deployment_root.parent / "stdio_server.py"
    program.write_text("", encoding="utf-8")
    body = _document(deployment_root)
    body["server"] = "stdio_server.py"
    _rewrite(deployment_root, body)

    document = load_binding_document(deployment_root)

    assert document.server == program.resolve()
    assert document.server.parent == deployment_root.parent.resolve(), (
        "the base is the deployment root's parent, not the deployment root"
    )


def test_a_deployment_declaring_no_server_loads_and_carries_none(
    deployment_root: Path,
) -> None:
    """Omission is legal, and it is the ORDINARY case.

    Most deployments are reached by an endpoint and never launch a program.
    A loader requiring this key would refuse every one of them.
    """
    body = _document(deployment_root)
    assert "server" not in body, "the fixture under test here declares none"

    assert load_binding_document(deployment_root).server is None


@pytest.mark.parametrize(
    "escaping", ["/etc/passwd", "../outside/serve.py", "nested/../../outside/serve.py"]
)
def test_binding_document_refuses_a_server_leaving_the_holding_directory(
    deployment_root: Path, escaping: str
) -> None:
    """`V-01`/`V-02` — moving the base out one level opened no hole.

    A sibling of the two-key containment test above rather than a third limb of
    it, because this key resolves against a different base and its refusal says
    so — the parameterized test's assertion string is the one thing a `server:`
    limb must not share.
    """
    body = _document(deployment_root)
    body["server"] = escaping
    _rewrite(deployment_root, body)

    with pytest.raises(BindingError) as refused:
        load_binding_document(deployment_root)

    assert_the_refusal_named_the_parent_as_the_base(str(refused.value))


def test_binding_document_refuses_a_server_symlink_out_of_the_holding_directory(
    deployment_root: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """`V-03` — the check the string form cannot make.

    A plain name, no `..`, no leading `/`, landing outside once resolved. The
    target is minted by ``tmp_path_factory`` so it is genuinely outside the
    directory holding the deployment rather than a sibling of it.
    """
    outside = tmp_path_factory.mktemp("elsewhere") / "serve.py"
    outside.write_text("", encoding="utf-8")
    (deployment_root.parent / "sneaky.py").symlink_to(outside)
    body = _document(deployment_root)
    body["server"] = "sneaky.py"
    _rewrite(deployment_root, body)

    with pytest.raises(BindingError) as refused:
        load_binding_document(deployment_root)

    assert_the_refusal_named_the_parent_as_the_base(str(refused.value))


def test_binding_document_refuses_a_server_reaching_back_inside_the_deployment(
    deployment_root: Path,
) -> None:
    """`D-18` (Dave, 2026-08-18) — the hole the wider base opened, closed by name.

    Containment passes this value: it is relative, carries no `..` and resolves
    under the parent. It nonetheless gives the deployment root a **second**
    Python module where Amendment A.3 grants one, its projection. Refused in
    the `RULED_OUT_KEYS` register — the author of such a document has not made
    a typo, so *"unknown key"* would invite a re-spelling of the very thing
    that was declined.
    """
    body = _document(deployment_root)
    body["server"] = f"{deployment_root.name}/projection.py"
    _rewrite(deployment_root, body)

    with pytest.raises(BindingError) as refused:
        load_binding_document(deployment_root)

    message = str(refused.value)
    assert "`server`" in message, "the refusal names the offending key"
    assert "Amendment A.3" in message, "and the rule the value broke"
    assert "2026-08-16-reference-plan-factory-and-debt-scorer" in message, (
        "and points at the ruling rather than restating it"
    )


def test_a_contained_server_that_does_not_exist_still_loads(
    deployment_root: Path,
) -> None:
    """Existence is the TRANSPORT's question, not the loader's.

    An in-process deployment never launches the program and an unpopulated
    checkout may legitimately lack it, so the loader contains the value and
    stops. `mcp_stdio` asks whether the file is there, where the transport is
    known and the refusal can name it.
    """
    body = _document(deployment_root)
    body["server"] = "nowhere.py"
    _rewrite(deployment_root, body)

    document = load_binding_document(deployment_root)

    assert document.server == (deployment_root.parent / "nowhere.py").resolve()
    assert not document.server.exists(), "which is precisely what is not refused"


def test_a_reference_shaped_server_is_refused_as_a_reference(
    deployment_root: Path,
) -> None:
    """`T-18.1-04` — no second executable reference smuggled through this key.

    Refused by machinery this key did not need to add: the reference sweep runs
    over every data position, and `server:` joined it by being one. `D-04`'s
    single-path form is what keeps it in bounds, and it is asserted rather than
    assumed.
    """
    body = _document(deployment_root)
    body["server"] = "serve.py:main"
    _rewrite(deployment_root, body)

    with pytest.raises(BindingError) as refused:
        load_binding_document(deployment_root)

    message = str(refused.value)
    assert "`server: serve.py:main`" in message, "the refusal names the position"
    assert "reference in a **data** position" in message, (
        "and says WHICH mistake — this assertion is why the test cannot pass"
        " through the unknown-key branch, which is how it passed before"
        " `server` joined `OPTIONAL_KEYS`"
    )


def test_the_committed_fixture_deployment_declares_the_committed_program() -> None:
    """The COMMITTED fixture, not a copy — so the layout is proven, not assumed.

    Every other test in this section writes its own `server:` into a `tmp_path`
    copy, which measures the loader and says nothing about whether the two
    files this suite actually ships are in the relationship the key describes.
    `T-18.1-05` is precisely a value that resolves *somewhere*, making a later
    refusal fire for the wrong reason and read as a pass.
    """
    assert load_binding_document(FIXTURE_DEPLOYMENT).server == STDIO_SERVER.resolve()


def test_the_committed_hw1_deployment_declares_the_committed_program() -> None:
    """The same claim for the shipped example, which is the adoption contract.

    An example whose `server:` resolved nowhere would still load — the loader
    does not existence-check (Ruling 3) — and would fail only when a transport
    tried to launch it. Asserted here, where it is cheap.
    """
    document = load_binding_document(HW1 / "deployment")

    assert document.server == (HW1 / "server" / "serve.py").resolve()
    assert document.server.is_file()
    assert document.server.parent != document.root, (
        "the program sits BESIDE the deployment, never inside it — `D-09`"
    )


def test_the_server_key_is_optional_and_never_ruled_out_by_name(deployment_root: Path) -> None:
    """Ruling 2 — asserted on the objects, because the grep form measured nothing.

    A `RULED_OUT_KEYS` entry refuses a key *unconditionally*; `server:` is a
    legitimate optional key whose refusal is about a **value**. Listing it there
    would refuse every deployment that declares one, hw1's included — so the
    positive leg stands beside the negative and both are asserted here.
    """
    assert "server" in OPTIONAL_KEYS
    assert "server" not in RULED_OUT_KEYS

    program = deployment_root.parent / "stdio_server.py"
    program.write_text("", encoding="utf-8")
    body = _document(deployment_root)
    body["server"] = "stdio_server.py"
    _rewrite(deployment_root, body)

    assert load_binding_document(deployment_root).server is not None, (
        "a deployment declaring an outward `server:` LOADS"
    )


# ---------------------------------------------------------------------------
# The reference loader — reached for `plan:` and nothing else.
# ---------------------------------------------------------------------------


def test_load_reference_resolves_the_fixture_projection(
    deployment_root: Path,
) -> None:
    """The positive case, so the refusals below are not the only measurement."""
    document = load_binding_document(deployment_root)

    factory = load_reference(document.plan, root=document.root, key="plan")

    assert callable(factory)


@pytest.mark.parametrize("malformed", ["projection.py", ":build", "projection.py:"])
def test_load_reference_refuses_a_reference_with_no_attribute(
    deployment_root: Path, malformed: str
) -> None:
    """A reference is a module path, a colon and an attribute — all three."""
    with pytest.raises(BindingError) as refused:
        load_reference(malformed, root=deployment_root.resolve(), key="plan")

    assert "`<module-path>:<attribute>`" in str(refused.value)


def test_load_reference_refuses_an_unresolvable_module(deployment_root: Path) -> None:
    """The module the reference names is not there."""
    with pytest.raises(BindingError) as refused:
        load_reference(
            "absent.py:build_projection", root=deployment_root.resolve(), key="plan"
        )

    message = str(refused.value)
    assert "`plan: absent.py:build_projection`" in message
    assert "does not exist" in message


def test_load_reference_refuses_a_module_that_raises_on_import(
    deployment_root: Path,
) -> None:
    """A module that exists but does not import is named, with its own error."""
    (deployment_root / "broken.py").write_text(
        "raise ValueError('deployment module is broken')\n", encoding="utf-8"
    )

    with pytest.raises(BindingError) as refused:
        load_reference("broken.py:anything", root=deployment_root.resolve(), key="plan")

    message = str(refused.value)
    assert "raised while importing" in message
    assert "deployment module is broken" in message


def test_load_reference_refuses_a_missing_attribute(deployment_root: Path) -> None:
    """The module imports, but holds no such attribute."""
    with pytest.raises(BindingError) as refused:
        load_reference(
            "projection.py:build_nothing", root=deployment_root.resolve(), key="plan"
        )

    message = str(refused.value)
    assert "`build_nothing`" in message
    assert "does not define" in message


def test_load_reference_loads_two_roots_as_two_modules(
    deployment_root: Path, tmp_path: Path
) -> None:
    """Two deployments carrying a ``projection.py`` each are two modules.

    A bare module name would be a real collision, not a theoretical one: the
    conformance suite boots more than one deployment in a process and
    ``sys.modules`` is process-wide, so the second root would silently get the
    first root's code.
    """
    import shutil

    second = tmp_path / "second"
    shutil.copytree(deployment_root, second)
    (second / "projection.py").write_text(
        (second / "projection.py").read_text(encoding="utf-8")
        + "\n\nMARKER = 'second-deployment'\n",
        encoding="utf-8",
    )

    first_module = load_reference(
        "projection.py:build_projection", root=deployment_root.resolve(), key="plan"
    )
    second_marker = load_reference(
        "projection.py:MARKER", root=second.resolve(), key="plan"
    )

    assert second_marker == "second-deployment"
    assert first_module.__module__ != second_marker


def test_conforming_plan_factory_accepts_the_fixture_projection(
    deployment_root: Path,
) -> None:
    """The Protocol check passes on a real plan factory.

    Asserted before the negative case below, because a check that refused
    everything would pass that case while being useless.
    """
    document = load_binding_document(deployment_root)

    factory = conforming_plan_factory(
        load_reference(document.plan, root=document.root, key="plan"),
        reference=document.plan,
        root=document.root,
    )

    assert callable(factory)


def test_conforming_plan_factory_refuses_a_non_factory(deployment_root: Path) -> None:
    """The one reference a deployment may hand over is verified to be code.

    ``ProjectionPlanFactoryProtocol`` is ``@runtime_checkable``, which is what
    makes this a real structural check rather than a comment.
    """
    with pytest.raises(BindingError) as refused:
        conforming_plan_factory(
            object(), reference="projection.py:build_projection", root=deployment_root
        )

    message = str(refused.value)
    assert "ProjectionPlanFactoryProtocol" in message
    assert "object" in message


def test_every_binding_refusal_is_a_transport_error() -> None:
    """``except TransportError`` stays the one clause for *the wire never spoke*.

    :class:`~ccf.client.errors.BindingError` inherits it, so a caller that
    branched on the transport case does not acquire a second except clause when
    a deployment's wiring is the thing that is wrong.
    """
    assert issubclass(BindingError, TransportError)
